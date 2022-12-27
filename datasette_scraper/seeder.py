import sqlite3
from urllib.parse import urlparse
import json
from datasette_scraper import ipc
from datasette_scraper.plugin import pm

def get_crawl_config_for_job(fname, job_id):
    con = sqlite3.connect(fname)
    try:
        res = con.execute('SELECT _dss_crawl.config FROM _dss_crawl JOIN _dss_job ON _dss_job.crawl_id = _dss_crawl.id WHERE _dss_job.id = ?', [job_id])
        config, = res.fetchone()
        config = json.loads(config)
        return config
    finally:
        con.close()

def entrypoint_seeder(coordinator_inbox, dss_db_name, db_map, job_id):
    # Need to open the datasette-scraper db, find the config for the crawl associated with
    # the job, then run the get_seed_urls hooks, then insert those into the
    # _dss_crawl_queue table

    dss_db_fname = db_map[dss_db_name]

    config = get_crawl_config_for_job(dss_db_fname, job_id)
    seeds = [url for urls in pm.hook.get_seed_urls(config=config) for url in urls]

    con = sqlite3.connect(dss_db_fname)
    con.isolation_level = None
    try:
        with con:
            con.execute('BEGIN')
            for seed in seeds:
                url = urlparse(seed)
                hostname = url.hostname
                con.execute('INSERT INTO _dss_crawl_queue(job_id, host, url, depth) VALUES (?, ?, ?, 0)', [job_id, hostname, seed])
    finally:
        con.close()

    coordinator_inbox.put({ 'type': ipc.SEED_CRAWL_COMPLETE, 'job-id': job_id })

