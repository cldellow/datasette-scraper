import sqlite3
from urllib.parse import urlparse
import time
import json
from datasette_scraper import ipc
from datasette_scraper.plugin import pm
from datasette_scraper.utils import lazy_connection_factory, get_crawl_config_for_job_id

def entrypoint_seeder(dss_db_name, db_map):
    factory = lazy_connection_factory(dss_db_name, db_map)

    conn = factory(None)
    while True:
        time.sleep(0.1)

        next_op = conn.execute('SELECT id, type, config FROM dss_ops WHERE finished_at IS NULL ORDER BY id LIMIT 1').fetchone()

        if not next_op:
            continue

        op_id, type, config = next_op
        config = json.loads(config)
        print('dss_op: id={} type={} config={}'.format(op_id, type, config))

        if type == ipc.SEED_CRAWL:
            seed_crawl(factory, config['job-id'])
        else:
            print('unknown dss_op: id={} type={} config={}'.format(op_id, type, config))

        with conn:
            conn.execute("UPDATE dss_op SET finished_at = strftime('%Y-%m-%d %H:%M:%f') WHERE id = ?", [op_id])


def seed_crawl(factory, job_id):
    conn = factory(None)
    config = get_crawl_config_for_job_id(conn, job_id)
    seeds = [url for urls in pm.hook.get_seed_urls(config=config) for url in urls]

    hosts = []
    with conn:
        for seed in seeds:
            url = urlparse(seed)
            hostname = url.hostname
            hosts.append(hostname)
            conn.execute('INSERT INTO dss_crawl_queue(job_id, host, url, depth) VALUES (?, ?, ?, 0)', [job_id, hostname, seed])

        for host in set(hosts):
            conn.execute('INSERT INTO dss_host_rate_limit(host) SELECT ? WHERE NOT EXISTS(SELECT * FROM dss_host_rate_limit WHERE host = ?)', [host, host])

        conn.execute("UPDATE dss_job SET status = 'running' WHERE id = ?", [job_id])
