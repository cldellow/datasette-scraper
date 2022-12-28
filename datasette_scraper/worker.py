import sqlite3
import time
import os

def entrypoint_worker(dss_db_name, db_map):
    # Need to open the datasette-scraper db, find the config for the crawl associated with
    # the job, then run the get_seed_urls hooks, then insert those into the
    # _dss_crawl_queue table

    dss_db_fname = db_map[dss_db_name]

    conn = sqlite3.connect(dss_db_fname)

    try:
        while True:
            crawl_loop(conn)
    finally:
        conn.close()

def get_next_crawl_queue_row(conn):
    row = conn.execute("SELECT id, job_id, host, queued_at, url, depth, claimed_at FROM _dss_crawl_queue WHERE host IN (SELECT host FROM _dss_host_rate_limit WHERE next_fetch_at < datetime()) AND (claimed_at IS NULL OR claimed_at < datetime('now', '-5 minutes')) LIMIT 1").fetchone()

    if not row:
        # TODO: are there any rows available? If not, we should shut down.
        has_more, = conn.execute("SELECT EXISTS(SELECT * FROM _dss_crawl_queue)").fetchone()

        if has_more:
            time.sleep(0.1)
            return None

        time.sleep(1)
        return None

    id, job_id, host, queued_at, url, depth, claimed_at = row

    print('...attempting to claim item id={}'.format(id))
    # Try to claim the row -- note that another worker may have claimed it while we were waiting.
    with conn:
        if claimed_at:
            claim_row = conn.execute("UPDATE _dss_crawl_queue SET claimed_at = strftime('%Y-%m-%d %H:%M:%f') WHERE id = ? AND claimed_at = ?", [id, claimed_at])
        else:
            claim_row = conn.execute("UPDATE _dss_crawl_queue SET claimed_at = strftime('%Y-%m-%d %H:%M:%f') WHERE id = ? AND claimed_at IS NULL", [id])

        if claim_row.rowcount != 1:
            print('...failed to claim crawl item job_id={} id={} url={}'.format(job_id, id, url))
            return None

        # Try to update _dss_host_rate_limit
        claim_rate_limit = conn.execute("UPDATE _dss_host_rate_limit SET next_fetch_at = strftime('%Y-%m-%d %H:%M:%f', 'now', delay_seconds || ' seconds') WHERE host = ? AND next_fetch_at < strftime('%Y-%m-%d %H:%M:%f')", [host])

        if claim_rate_limit.rowcount != 1:
            # ...we failed to get rate limit, so release the row
            print('...failed to claim host rate limit for job_id={} host={}'.format(job_id, host))
            conn.rollback()
            return None

    return row

def crawl_loop(conn):
    # Warning: This is super naive! As we get experience operating at higher volumes,
    # may need to tweak it.

    # Try to find a URL to crawl that (a) isn't host rate limited and (b) hasn't been
    # recently claimed by another worker.

    row = get_next_crawl_queue_row(conn)

    if not row:
        return

    print('! found work item {}'.format(row))

