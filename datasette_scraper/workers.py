from multiprocessing import Process, SimpleQueue
import sys
import os
from datasette_scraper import ipc
from .config import get_database
from .seeder import entrypoint_seeder
from .worker import entrypoint_worker

processes = []
seeder_inbox = SimpleQueue()

# TODO: this should be configurable / use a sane default
NUM_WORKERS = 1

def seed_crawl(job_id):
    seeder_inbox.put({ 'type': ipc.SEED_CRAWL, 'job-id': job_id })

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

    p = Process(target=entrypoint_seeder, args=(dss_db_name, db_map, seeder_inbox), daemon=True)
    p.start()
    processes.append(('seeder', p))

    for i in range(NUM_WORKERS):
        p = Process(target=entrypoint_worker, args=(dss_db_name, db_map), daemon=True)
        p.start()
        processes.append(('worker', p))
