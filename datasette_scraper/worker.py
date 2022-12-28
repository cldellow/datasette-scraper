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

def crawl_loop(conn):
    print('crawl_loop running mypid={}'.format(os.getpid()))

    # Warning: This is super naive! As we get experience operating at higher volumes,
    # may need to tweak it.

    # Try to find a URL to crawl that (a) isn't host rate limited and (b) hasn't been
    # recently claimed by another worker.
    row = conn.execute("SELECT id, job_id, host, queued_at, url, depth, claimed_at FROM _dss_crawl_queue WHERE host IN (SELECT host FROM _dss_host_rate_limit WHERE next_fetch_at < datetime()) AND (claimed_at IS NULL OR claimed_at < datetime('now', '-5 minutes')) LIMIT 1").fetchone()

    if not row:
        # TODO: are there any rows available? If not, we should shut down.
        has_more, = conn.execute("SELECT EXISTS(SELECT * FROM _dss_crawl_queue)").fetchone()

        if has_more:
            time.sleep(0.1)
            return True

        print('no more work items, ending loop')
        return False

    id, job_id, host, queued_at, url, depth, claimed_at = row
    print(row)

    # Try to claim the row -- note that another worker may have claimed it while we were waiting.
    with conn:
        if claimed_at:
            claim_row = conn.execute("UPDATE _dss_crawl_queue SET claimed_at = strftime('%Y-%m-%d %H:%M:%f') WHERE id = ? AND claimed_at = ?", [id, claimed_at])
        else:
            print('...updating where id = {} and claimed_at IS NULL'.format(id))
            claim_row = conn.execute("UPDATE _dss_crawl_queue SET claimed_at = strftime('%Y-%m-%d %H:%M:%f') WHERE id = ? AND claimed_at IS NULL", [id])

        if claim_row.rowcount != 1:
            raise Exception('TODO: handle another worker taking the work item')
        print(claim_row)
        print(claim_row.rowcount)




    # try to claim it as yours (iff it hasn't since been claimed)

    # if you claimed it, try to increment the host rate limiter

    # if you incremented it, actually do the thing

    # otherwise, relinquish claim on URL

    # if no URL, check to see if we should shut down (shut down if crawl_queue is empty)

    pass


