import time
import os
import json
import math
from urllib.parse import urljoin
from datasette_scraper.plugin import pm
from datasette_scraper import utils, inserts

def entrypoint_worker(dss_db_name, db_map):
    factory = utils.lazy_connection_factory(dss_db_name, db_map)

    conn = factory(None)

    try:
        while True:
            crawl_loop(dss_db_name, factory, conn)
    finally:
        conn.close()

def get_next_crawl_queue_row(conn):
    row = conn.execute("SELECT id, job_id, host, queued_at, url, depth, claimed_at FROM dss_crawl_queue WHERE host IN (SELECT host FROM dss_host_rate_limit WHERE next_fetch_at < strftime('%Y-%m-%d %H:%M:%f')) AND (claimed_at IS NULL OR claimed_at < datetime('now', '-5 minutes')) ORDER BY depth, queued_at LIMIT 1").fetchone()

    if not row:
        time.sleep(0.05)
        return None

    id, job_id, host, queued_at, url, depth, claimed_at = row

    #print('...attempting to claim item id={}'.format(id))
    # Try to claim the row -- note that another worker may have claimed it while we were waiting.
    with conn:
        if claimed_at:
            claim_row = conn.execute("UPDATE dss_crawl_queue SET claimed_at = strftime('%Y-%m-%d %H:%M:%f') WHERE id = ? AND claimed_at = ?", [id, claimed_at])
        else:
            claim_row = conn.execute("UPDATE dss_crawl_queue SET claimed_at = strftime('%Y-%m-%d %H:%M:%f') WHERE id = ? AND claimed_at IS NULL", [id])

        if claim_row.rowcount != 1:
            #print('...failed to claim crawl item job_id={} id={} url={}'.format(job_id, id, url))
            return None

    return row

def absolutize_urls(base_url, new_url):
    try:
        rv = urljoin(base_url, new_url)
        hash_idx = rv.find('#')

        if hash_idx == -1:
            return rv

        return rv[0:hash_idx]
    except:
        return None

def update_crawl_stats(conn, job_id, host, response, fresh):
    with conn:
        conn.execute("INSERT OR IGNORE INTO dss_job_stats(job_id, host) VALUES (?, ?)", [job_id, host])
        xx_column = 'fetched_5xx'
        status_code = response['status_code']

        if status_code >= 200 and status_code <= 299:
            xx_column = 'fetched_2xx'
        elif status_code >= 300 and status_code <= 399:
            xx_column = 'fetched_3xx'
        elif status_code >= 400 and status_code <= 499:
            xx_column = 'fetched_4xx'

        maybe_fetched_fresh = ''
        if fresh:
            maybe_fetched_fresh = ', fetched_fresh = fetched_fresh + 1'

        # TODO: this seems to undercount sometimes when run under high concurrency,
        #       which likely means my mental model is wrong. Hmm.
        conn.execute("UPDATE dss_job_stats SET fetched = fetched + 1, {} = {} + 1{} WHERE job_id = ? AND host = ?".format(xx_column, xx_column, maybe_fetched_fresh), [job_id, host])

def discover_urls(config, from_url, from_depth, response):
    urls = [new_url for urls in pm.hook.discover_urls(config=config, url=from_url, response=response) for new_url in urls]

    # Normalize URLs into (url, depth) form
    urls = [new_url if isinstance(new_url, tuple) else (new_url, from_depth + 1) for new_url in urls]

    # Resolve relative paths
    urls = [(absolutize_urls(from_url, new_url), new_depth) for (new_url, new_depth) in urls]
    urls = [x for x in urls if x]

    # Reject non HTTP/HTTPS URLs
    urls = [new_url for new_url in urls if new_url[0].startswith('https:') or new_url[0].startswith('http:')]

    new_urls = []
    for (to_url, to_url_depth) in urls:
        attempts = 0
        while attempts < 10:
            # We do max 10 canonicalization attempts to prevent infinite loops from broken
            # plugins.
            attempts += 1
            results = pm.hook.canonicalize_url(config=config, from_url=from_url, to_url=to_url, to_url_depth=to_url_depth)

            rewritten = False
            for x in results:
                if isinstance(x, str):
                    to_url = x
                    rewritten = True
                    break
                if isinstance(x, tuple):
                    to_url = x[0]
                    to_url_depth = x[1]
                    rewritten = True
                    break

            if rewritten:
                continue

            if False in results:
                # Someone rejected the URL; this wins.
                break

            new_urls.append((to_url, to_url_depth))
            break

    return set(list(new_urls))


def crawl_loop(dss_db_name, factory, conn):
    #print('crawl_loop running pid={}'.format(os.getpid()))
    # Warning: This is super naive! As we get experience operating at higher volumes,
    # may need to tweak it.

    # Try to find a URL to crawl that (a) isn't host rate limited and (b) hasn't been
    # recently claimed by another worker.

    row = get_next_crawl_queue_row(conn)

    if not row:
        return

    id, job_id, host, queued_at, url, depth, claimed_at = row
    #print('! found work item {}'.format(row))
    config = utils.get_crawl_config_for_job_id(conn, job_id)

    # before_fetch_url: Give plugins a chance to reject this URL / add
    #  request headers.
    request_headers = {}
    rejected_reason = pm.hook.before_fetch_url(conn=conn, config=config, job_id=job_id, url=url, depth=depth, request_headers=request_headers)

    if rejected_reason:
        utils.reject_crawl_queue_item(conn, id, rejected_reason)
        utils.check_for_job_complete(conn, job_id)
        return

    fresh = False
    start = time.time()
    # fetch_cached_url: Fetch a previously cached URL.
    response = pm.hook.fetch_cached_url(conn=conn, config=config, url=url, depth=depth, request_headers=request_headers)
    fetch_duration = math.ceil(1000 * (time.time() - start))

    if not response:
        # Try to update dss_host_rate_limit
        with conn:
            claim_rate_limit = conn.execute("UPDATE dss_host_rate_limit SET next_fetch_at = strftime('%Y-%m-%d %H:%M:%f', 'now', delay_seconds || ' seconds') WHERE host = ? AND next_fetch_at < strftime('%Y-%m-%d %H:%M:%f')", [host])

            if claim_rate_limit.rowcount != 1:
                # ...we failed to get rate limit, so release the row
                print('...failed to claim host rate limit for job_id={} host={}'.format(job_id, host))
                # Release the row we were working on
                conn.execute('UPDATE dss_crawl_queue SET claimed_at = NULL WHERE id = ?', [id])
                return None


        fresh = True
        start = time.time()
        # fetch_url: Fetch the actual URL.
        response = pm.hook.fetch_url(url=url, request_headers=request_headers)

        if not response:
            # Weird, this should be impossible.
            utils.reject_crawl_queue_item(conn, id, 'fetch_url failed')
            utils.check_for_job_complete(conn, job_id)
            return

        if isinstance(response, Exception):
            utils.reject_crawl_queue_item(conn, id, repr(response))
            utils.check_for_job_complete(conn, job_id)
            return

        fetch_duration = math.ceil(1000 * (time.time() - start))

    update_crawl_stats(conn, job_id, host, response, fresh)

    pm.hook.after_fetch_url(conn=conn, config=config, url=url, request_headers=request_headers, response=response, fresh=fresh, fetch_duration=fetch_duration)

    urls = discover_urls(config, url, depth, response)
    # Try to insert these URLs into dss_crawl_queue; skipping entries that are already
    # present, or present in dss_crawl_queue_history with a lower or equal depth.
    now = time.time()
    enqueued = utils.add_crawl_queue_items(conn, job_id, urls)
    #print('enqueued {}/{} urls in {} sec'.format(enqueued, len(urls), time.time() - now))

    for insert in pm.hook.extract_from_response(config=config, url=url, response=response):
        if insert:
            rv = inserts.handle_insert(factory, insert)

            for ((dbname, tablename), (inserted, updated)) in rv.items():
                conn.execute('INSERT INTO dss_extract_stats(job_id, database, tbl, inserted, updated) VALUES (?, ?, ?, ?, ?) ON CONFLICT(job_id, database, tbl) DO UPDATE SET inserted = inserted + ?, updated = updated + ?', [job_id, dbname or dss_db_name, tablename, inserted, updated, inserted, updated])


    utils.finish_crawl_queue_item(conn, id, response, fresh, fetch_duration)
    utils.check_for_job_complete(conn, job_id)
