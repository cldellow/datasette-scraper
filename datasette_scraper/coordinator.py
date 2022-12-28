from multiprocessing import Process, SimpleQueue
import os
from datasette_scraper import ipc
from .config import get_database
from .seeder import entrypoint_seeder
from .worker import entrypoint_worker

coordinator_inbox = SimpleQueue()

# TODO: this should be configurable / use a sane default
NUM_WORKERS = 1

def seed_crawl(job_id):
    coordinator_inbox.put({ 'type': ipc.SEED_CRAWL, 'job-id': job_id })

def ensure_workers(inbox, dss_db_name, db_map, workers):
    # Prune dead workers
    living_workers = [p for p in workers if p.is_alive()]
    workers.clear()
    workers.extend(living_workers)

    for x in range(NUM_WORKERS - len(workers)):
        worker = Process(target=entrypoint_worker, args=(inbox, dss_db_name, db_map), daemon=True)
        workers.append(worker)
        worker.start()

def entrypoint_coordinator(inbox, dss_db_name, db_map):
    print('started coordinator pid={} db_map={}'.format(os.getpid(), db_map))
    workers = []

    while True:
        print('coordinator waiting for message...')
        message = inbox.get()

        if message['type'] == ipc.SEED_CRAWL:
            job_id = message['job-id']
            print('coordinator spawning seeder for job {}'.format(job_id))
            p = Process(target=entrypoint_seeder, args=(coordinator_inbox, dss_db_name, db_map, job_id), daemon=True)
            p.start()
        elif message['type'] == ipc.SEED_CRAWL_COMPLETE:
            ensure_workers(inbox, dss_db_name, db_map, workers)
        elif message['type'] == ipc.ENSURE_WORKERS:
            ensure_workers(inbox, dss_db_name, db_map, workers)
        else:
            print('coordinator received unknown message: {}'.format(message))

def start_coordinator(datasette):
    print('starting coordinator mypid={}'.format(os.getpid()))
    dss_db_name = get_database(datasette).name
    db_map = {}
    for k, v in datasette.databases.items():
        if v.is_memory or not v.is_mutable:
            continue
        db_map[k] = v.path
    p = Process(target=entrypoint_coordinator, args=(coordinator_inbox, dss_db_name, db_map))
    p.start()

    coordinator_inbox.put({'type': ipc.ENSURE_WORKERS})
