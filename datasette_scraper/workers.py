from multiprocessing import Process, cpu_count
import sys
import os
import json
from datasette_scraper import ipc
from .config import enabled_databases
from .worker_ops import entrypoint_ops
from .worker_crawl import entrypoint_crawl

processes = []

NUM_WORKERS = cpu_count()

async def seed_crawl(db, job_id):
    await db.execute_write(
        'INSERT INTO dss_ops(type, config) VALUES (?, ?)',
        [ipc.SEED_CRAWL, json.dumps({'job-id': job_id})],
        block=True
    )

async def discover_missing_dictionaries(db):
    await db.execute_write(
        'INSERT INTO dss_ops(type) VALUES (?)',
        [ipc.DISCOVER_MISSING_DICTIONARIES],
        block=True
    )

def start_workers(datasette):
    # Don't start background workers if we're being tested under pytest.
    if "pytest" in sys.modules:
        return

    print('start_workers pid={}'.format(os.getpid()))
    db_map = {}
    for k, v in datasette.databases.items():
        if v.is_memory or not v.is_mutable:
            continue
        db_map[k] = v.path

    enabled_dbs = enabled_databases(datasette)

    if not enabled_dbs:
        raise Exception('datasette-scraper: not enabled in any databases, why are we starting workers?')

    p = Process(target=entrypoint_ops, args=(enabled_dbs, db_map), daemon=True)
    p.start()
    processes.append(('worker_ops', p))

    for i in range(NUM_WORKERS):
        p = Process(target=entrypoint_crawl, args=(enabled_dbs, db_map), daemon=True)
        p.start()
        processes.append(('worker_crawl', p))
