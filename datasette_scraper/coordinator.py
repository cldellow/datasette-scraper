from multiprocessing import Process, SimpleQueue
import os
from datasette_scraper import ipc
from .config import get_database
from .seeder import entrypoint_seeder

coordinator_inbox = SimpleQueue()

def seed_crawl(job_id):
    coordinator_inbox.put({ 'type': ipc.SEED_CRAWL, 'job-id': job_id })

def entrypoint_coordinator(inbox, dss_db_name, db_map):
    print('started coordinator pid={} db_map={}'.format(os.getpid(), db_map))

    while True:
        print('coordinator waiting for message...')
        message = inbox.get()

        if message['type'] == ipc.SEED_CRAWL:
            job_id = message['job-id']
            print('coordinator spawning seeder for job {}'.format(job_id))
            p = Process(target=entrypoint_seeder, args=(coordinator_inbox, dss_db_name, db_map, job_id))
            p.start()
        else:
            print('coordinator received unknown message: {}'.format(message))

def start_coordinator(datasette):
    print('starting coordinator')
    dss_db_name = get_database(datasette).name
    db_map = {}
    for k, v in datasette.databases.items():
        if v.is_memory or not v.is_mutable:
            continue
        db_map[k] = v.path
    p = Process(target=entrypoint_coordinator, args=(coordinator_inbox, dss_db_name, db_map))
    p.start()
