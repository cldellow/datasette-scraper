from datasette_scraper.config import ensure_wal_mode
import sqlite3
import json
import types
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
    res = conn.execute('SELECT dss_crawl.config FROM dss_crawl JOIN dss_job ON dss_job.crawl_id = dss_crawl.id WHERE dss_job.id = ?', [job_id])
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
    with conn:
        conn.execute('BEGIN TRANSACTION')
        for batch in batched_urls:
            cur = conn.execute(
                'SELECT url FROM dss_crawl_queue WHERE job_id = {} AND url IN ({})'.format(job_id, ','.join(['?'] * len(batch))),
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
                'SELECT url FROM dss_crawl_queue_history WHERE job_id = {} AND url IN ({})'.format(job_id, ','.join(['?'] * len(batch))),
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
        parsed = urlparse(url)
        host = parsed.hostname

        #print('insert dss_host_rate_limit host={}'.format(host))
        conn.execute('BEGIN TRANSACTION')
        conn.execute('INSERT INTO dss_host_rate_limit(host) SELECT ? WHERE NOT EXISTS(SELECT * FROM dss_host_rate_limit WHERE host = ?)', [host, host])


        cur = conn.execute('INSERT INTO dss_crawl_queue(job_id, host, url, depth) SELECT ?, ?, ?, ? WHERE NOT EXISTS(SELECT * FROM dss_crawl_queue WHERE job_id = ? AND url = ?) AND NOT EXISTS(SELECT * FROM dss_crawl_queue_history WHERE job_id = ? AND url = ?)', [job_id, host, url, depth, job_id, url, job_id, url])

        return cur.rowcount


def reject_crawl_queue_item(conn, id, reason):
    with conn:
        conn.execute('BEGIN TRANSACTION')
        conn.execute("INSERT INTO dss_crawl_queue_history(job_id, host, url, depth, processed_at, fetched_fresh, skipped_reason) SELECT job_id, host, url, depth, strftime('%Y-%m-%d %H:%M:%f'), 0, ? FROM dss_crawl_queue WHERE id = ?", [reason, id])
        conn.execute("DELETE FROM dss_crawl_queue WHERE id = ?", [id])

def finish_crawl_queue_item(conn, id, response, fresh, fetch_duration):
    content_type = 'application/octet-stream'
    status_code = response['status_code']

    # just an approximation -- not, e.g., the Content-Length header
    size = len(response['text'])

    for header in response['headers']:
        if header[0] == 'content-type':
            content_type = header[1].split(';')[0]

    with conn:
        conn.execute('BEGIN TRANSACTION')
        conn.execute("INSERT INTO dss_crawl_queue_history(job_id, host, url, depth, processed_at, fetched_fresh, status_code, content_type, size, duration, request_hash) SELECT job_id, host, url, depth, strftime('%Y-%m-%d %H:%M:%f'), ?, ?, ?, ?, ?, ? FROM dss_crawl_queue WHERE id = ?", [fresh, status_code, content_type, size, fetch_duration, response['_request_hash'] if '_request_hash' in response else None, id])
        conn.execute("DELETE FROM dss_crawl_queue WHERE id = ?", [id])

def check_for_job_complete(conn, job_id):
    more_to_do, = conn.execute("SELECT EXISTS(SELECT * FROM dss_crawl_queue WHERE job_id = ?) AND EXISTS(SELECT * FROM dss_job WHERE id = ? AND status != 'cancelled' AND status != 'done')", [job_id, job_id]).fetchone()
    if not more_to_do:
        with conn:
            conn.execute('BEGIN TRANSACTION')
            conn.execute("UPDATE dss_job SET status = 'done', finished_at = strftime('%Y-%m-%d %H:%M:%f') WHERE id = ? AND finished_at IS NULL", [job_id])
            conn.execute("DELETE FROM dss_crawl_queue WHERE job_id = ?", [job_id])

def lazy_connection_factory(db_map):
    conns = {}

    def get_db(name):
        if not name in db_map:
            raise Exception('unknown database name: {}'.format(name))

        if name in conns:
            return conns[name]

        conn = sqlite3.connect(db_map[name])
        conn.isolation_level = None
        ensure_wal_mode(conn)

        # See https://www.sqlite.org/pragma.html#pragma_synchronous; this is much faster,
        # at the expense of durability in the event of an unplanned shutdown.
        conn.execute('pragma synchronous = normal;')
        conns[name] = conn
        return conn

    return get_db

def lazy_connection_factory_with_default(factory, default):
    def get_db(name):
        if not name:
            return factory(default)

        return factory(name)

    return get_db

def module_from_path(path, name):
    # Stolen from https://github.com/simonw/datasette/blob/013496862f4d4b441ab61255242b838b24287607/datasette/utils/__init__.py#L741
    # Adapted from http://sayspy.blogspot.com/2011/07/how-to-import-module-from-just-file.html
    mod = types.ModuleType(name)
    mod.__file__ = path
    with open(path, "r") as file:
        code = compile(file.read(), path, "exec", dont_inherit=True)
    exec(code, mod.__dict__)
    return mod
