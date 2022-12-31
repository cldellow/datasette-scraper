import sqlite3
from urllib.parse import urlparse
import json
from datasette_scraper import ipc
from datasette_scraper.plugin import pm
from datasette_scraper.utils import get_crawl_config_for_job_id

def get_crawl_config_for_job(fname, job_id):
    conn = sqlite3.connect(fname)
    try:
        return get_crawl_config_for_job_id(conn, job_id)
    finally:
        conn.close()

def entrypoint_seeder(dss_db_name, db_map, seeder_inbox):
    dss_db_fname = db_map[dss_db_name]

    while True:
        msg = seeder_inbox.get()

        if msg['type'] != ipc.SEED_CRAWL:
            continue

        job_id = msg['job-id']

        config = get_crawl_config_for_job(dss_db_fname, job_id)
        seeds = [url for urls in pm.hook.get_seed_urls(config=config) for url in urls]

        con = sqlite3.connect(dss_db_fname)
        con.isolation_level = None

        hosts = []
        try:
            with con:
                con.execute('BEGIN')
                for seed in seeds:
                    url = urlparse(seed)
                    hostname = url.hostname
                    hosts.append(hostname)
                    con.execute('INSERT INTO dss_crawl_queue(job_id, host, url, depth) VALUES (?, ?, ?, 0)', [job_id, hostname, seed])

                for host in set(hosts):
                    con.execute('INSERT INTO dss_host_rate_limit(host) SELECT ? WHERE NOT EXISTS(SELECT * FROM dss_host_rate_limit WHERE host = ?)', [host, host])

                con.execute("UPDATE dss_job SET status = 'running' WHERE id = ?", [job_id])
        finally:
            con.close()
