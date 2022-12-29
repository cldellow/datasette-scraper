import json
from more_itertools import batched
from selectolax.parser import HTMLParser
from urllib.parse import urlparse

_last_html = None
_last_html_parser = None

def get_html_parser(response):
    global _last_html
    global _last_html_parser

    text = response['text']
    if text == _last_html:
        return _last_html_parser

    _last_html_parser = HTMLParser(text)
    _last_html = text
    return _last_html_parser


def get_crawl_config_for_job_id(conn, job_id):
    res = conn.execute('SELECT _dss_crawl.config FROM _dss_crawl JOIN _dss_job ON _dss_job.crawl_id = _dss_crawl.id WHERE _dss_job.id = ?', [job_id])
    config, = res.fetchone()
    config = json.loads(config)
    return config

def add_crawl_queue_items(conn, job_id, urls):
    enqueued = 0

    batch_size = 100
    # Try to efficiently prune URLs we've already queued 
    all_urls = [url[0] for url in urls]
    batched_urls = batched(all_urls, batch_size)

    already_queued = {}
    for batch in batched_urls:
        cur = conn.execute(
            'SELECT url FROM _dss_crawl_queue WHERE job_id = {} AND url IN ({})'.format(job_id, ','.join(['?'] * len(batch))),
            batch
        )
        cur.arraysize = 100
        rv = cur.fetchmany()
        for (fetched_url, ) in rv:
            already_queued[fetched_url] = True

    all_urls = [url for url in all_urls if not url in already_queued]
    batched_urls = batched(all_urls, batch_size)
    for batch in batched_urls:
        cur = conn.execute(
            'SELECT url FROM _dss_crawl_queue_history WHERE job_id = {} AND url IN ({})'.format(job_id, ','.join(['?'] * len(batch))),
            batch
        )
        cur.arraysize = 100
        rv = cur.fetchmany()
        for (fetched_url, ) in rv:
            already_queued[fetched_url] = True

    urls = [url for url in urls if not url[0] in already_queued]

    for (new_url, new_depth) in urls:
        enqueued += add_crawl_queue_item(conn, job_id, new_url, new_depth)

    return enqueued

def add_crawl_queue_item(conn, job_id, url, depth):
    with conn:
        crawled, = conn.execute('SELECT EXISTS(SELECT * FROM _dss_crawl_queue_history WHERE job_id = ? AND url = ?)', [job_id, url]).fetchone()

        if crawled:
            return 0

        pending, = conn.execute('SELECT EXISTS(SELECT * FROM _dss_crawl_queue WHERE job_id = ? AND url = ?)', [job_id, url]).fetchone()

        if pending:
            return 0


        parsed = urlparse(url)
        host = parsed.hostname

        conn.execute('INSERT INTO _dss_host_rate_limit(host) SELECT ? WHERE NOT EXISTS(SELECT * FROM _dss_host_rate_limit WHERE host = ?)', [host, host])


        conn.execute('INSERT INTO _dss_crawl_queue(job_id, host, url, depth) VALUES (?, ?, ?, ?)', [job_id, host, url, depth])

        return 1


def reject_crawl_queue_item(conn, id, reason):
    with conn:
        conn.execute("INSERT INTO _dss_crawl_queue_history(job_id, host, url, depth, processed_at, fetched_fresh, skipped_reason) SELECT job_id, host, url, depth, strftime('%Y-%m-%d %H:%M:%f'), 0, ? FROM _dss_crawl_queue WHERE id = ?", [reason, id])
        conn.execute("DELETE FROM _dss_crawl_queue WHERE id = ?", [id])

def finish_crawl_queue_item(conn, id, response, fresh, fetch_duration):
    content_type = 'application/octet-stream'
    status_code = response['status_code']

    # just an approximation -- not, e.g., the Content-Length header
    size = len(response['text'])

    for header in response['headers']:
        if header[0] == 'content-type':
            content_type = header[1].split(';')[0]

    with conn:
        conn.execute("INSERT INTO _dss_crawl_queue_history(job_id, host, url, depth, processed_at, fetched_fresh, status_code, content_type, size, duration) SELECT job_id, host, url, depth, strftime('%Y-%m-%d %H:%M:%f'), ?, ?, ?, ?, ? FROM _dss_crawl_queue WHERE id = ?", [fresh, status_code, content_type, size, fetch_duration, id])
        conn.execute("DELETE FROM _dss_crawl_queue WHERE id = ?", [id])

def check_for_job_complete(conn, job_id):
    with conn:
        more_to_do, = conn.execute('SELECT EXISTS(SELECT * FROM _dss_crawl_queue WHERE job_id = ?)', [job_id]).fetchone()

        if not more_to_do:
            conn.execute("UPDATE _dss_job SET status = 'done', finished_at = strftime('%Y-%m-%d %H:%M:%f') WHERE id = ?", [job_id])

