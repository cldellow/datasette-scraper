from multiprocessing import Process
import sys
import os
import json
from datasette_scraper import ipc
from .config import get_database
from .seeder import entrypoint_seeder
from .worker import entrypoint_worker

processes = []

# TODO: this should be configurable / use a sane default
NUM_WORKERS = 16

async def seed_crawl(db, job_id):
    await db.execute_write(
        'INSERT INTO dss_ops(type, config) VALUES (?, ?)',
        [ipc.SEED_CRAWL, json.dumps({'job-id': job_id})],
        block=True
    )

def start_workers(datasette):
    # Don't start background workers if we're being tested under pytest.
    if "pytest" in sys.modules:
        return

    print('start_workers pid={}'.format(os.getpid()))
    dss_db_name = get_database(datasette).name
    db_map = {}
    for k, v in datasette.databases.items():
        if v.is_memory or not v.is_mutable:
            continue
        db_map[k] = v.path

    p = Process(target=entrypoint_seeder, args=(dss_db_name, db_map), daemon=True)
    p.start()
    processes.append(('seeder', p))

    for i in range(NUM_WORKERS):
        p = Process(target=entrypoint_worker, args=(dss_db_name, db_map), daemon=True)
        p.start()
        processes.append(('worker', p))
