import json

def get_crawl_config_for_job_id(conn, job_id):
    res = conn.execute('SELECT _dss_crawl.config FROM _dss_crawl JOIN _dss_job ON _dss_job.crawl_id = _dss_crawl.id WHERE _dss_job.id = ?', [job_id])
    config, = res.fetchone()
    config = json.loads(config)
    return config

def reject_crawl_queue_item(conn, id, reason):
    with conn:
        conn.execute("INSERT INTO _dss_crawl_queue_history(job_id, host, url, depth, processed_at, fetched_fresh, skipped_reason) SELECT job_id, host, url, depth, strftime('%Y-%m-%d %H:%M:%f'), 0, ? FROM _dss_crawl_queue WHERE id = ?", [reason, id])
        conn.execute("DELETE FROM _dss_crawl_queue WHERE id = ?", [id])

def finish_crawl_queue_item(conn, id, response):
    content_type = 'application/octet-stream'
    status_code = response['status_code']
    fetched_fresh = response['fresh']

    # just an approximation -- not, e.g., the Content-Length header
    size = len(response['text'])

    for header in response['headers']:
        if header[0] == 'content-type':
            content_type = header[1].split(';')[0]

    with conn:
        conn.execute("INSERT INTO _dss_crawl_queue_history(job_id, host, url, depth, processed_at, fetched_fresh, status_code, content_type, size) SELECT job_id, host, url, depth, strftime('%Y-%m-%d %H:%M:%f'), ?, ?, ?, ? FROM _dss_crawl_queue WHERE id = ?", [fetched_fresh, status_code, content_type, size, id])
        conn.execute("DELETE FROM _dss_crawl_queue WHERE id = ?", [id])


def check_for_job_complete(conn, job_id):
    with conn:
        more_to_do, = conn.execute('SELECT EXISTS(SELECT * FROM _dss_crawl_queue WHERE job_id = ?)', [job_id]).fetchone()

        if not more_to_do:
            conn.execute("UPDATE _dss_job SET status = 'done', finished_at = strftime('%Y-%m-%d %H:%M:%f') WHERE id = ?", [job_id])

