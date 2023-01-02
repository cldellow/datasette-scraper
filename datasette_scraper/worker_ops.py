import sqlite3
from urllib.parse import urlparse
import time
import json
from datasette_scraper import ipc
from datasette_scraper.plugin import pm
from datasette_scraper.zstd import train_zstd_dict, get_active_dict_id, get_compressor, get_decompressor
from datasette_scraper.utils import lazy_connection_factory, get_crawl_config_for_job_id

def queue_discover_missing_dictionaries(conn):
    with conn:
        conn.execute('INSERT INTO dss_ops(type) VALUES (?)', [ipc.DISCOVER_MISSING_DICTIONARIES])

def entrypoint_ops(enabled_dbs, db_map):
    raw_factory = lazy_connection_factory(db_map)

    for db in enabled_dbs:
        conn = raw_factory(db)
        queue_discover_missing_dictionaries(conn)

    while True:
        for db in enabled_dbs:
            conn = raw_factory(db)
            next_op = conn.execute('SELECT id, type, config FROM dss_ops WHERE finished_at IS NULL ORDER BY id LIMIT 1').fetchone()

            if not next_op:
                time.sleep(0.1)
                continue

            op_id, type, config = next_op
            config = json.loads(config)
            print('dss_ops: db={} id={} type={} config={}'.format(db, op_id, type, config))

            if type == ipc.SEED_CRAWL:
                seed_crawl(conn, config['job-id'])
            elif type == ipc.DISCOVER_MISSING_DICTIONARIES:
                discover_missing_dictionaries(conn)
            elif type == ipc.TRAIN_DICTIONARY:
                train_dictionary(conn, config['host'])
            elif type == ipc.RECOMPRESS_ALL:
                recompress_all(conn)
            elif type == ipc.RECOMPRESS_HOST:
                recompress_host(conn, config['host'])
            elif type == ipc.RECOMPRESS_HASH:
                recompress_hash(conn, config['request_hash'])
            else:
                print('unknown dss_ops: id={} type={} config={}'.format(op_id, type, config))
            with conn:
                conn.execute("UPDATE dss_ops SET finished_at = strftime('%Y-%m-%d %H:%M:%f') WHERE id = ?", [op_id])

def recompress_all(conn):
    hosts = conn.execute('SELECT host FROM dss_fetch_cache GROUP BY 1').fetchall()

    with conn:
        for host in hosts:
            host = host[0]
            config = json.dumps({'host': host})
            conn.execute(
                'INSERT INTO dss_ops(type, config) SELECT ?, ?',
                [
                    ipc.RECOMPRESS_HOST,
                    config,
                ]
            )

def recompress_host(conn, host):
    hashes = conn.execute('SELECT request_hash FROM dss_fetch_cache WHERE host = ?', [host]).fetchall()

    with conn:
        for request_hash in hashes:
            request_hash = request_hash[0]
            config = json.dumps({'request_hash': request_hash})
            conn.execute(
                'INSERT INTO dss_ops(type, config) VALUES (?, ?)',
                [
                    ipc.RECOMPRESS_HASH,
                    config,
                ]
            )

def recompress_hash(conn, request_hash):
    row = conn.execute('SELECT url, object, dict_id FROM dss_fetch_cache WHERE request_hash = ?', [request_hash]).fetchone()

    if not row:
        return

    url, obj, old_dict_id = row

    host = urlparse(url).hostname

    dict_id = get_active_dict_id(conn, host)

    if dict_id == old_dict_id:
        return

    decompressed = get_decompressor(conn, old_dict_id).decompress(obj)

    compressed = get_compressor(conn, dict_id).compress(decompressed)

    with conn:
        conn.execute('UPDATE dss_fetch_cache SET object = ?, dict_id = ? WHERE request_hash = ?', [compressed, dict_id, request_hash])

def train_dictionary(conn, host):
    # Confirm that we still lack a dictionary
    exists, = conn.execute('SELECT EXISTS(SELECT * FROM dss_zstd_dict WHERE active AND host = ?)', [host]).fetchone()

    if exists:
         return

    train_zstd_dict(conn, host)
    with conn:
        conn.execute(
            'INSERT INTO dss_ops(type, config) VALUES (?, ?)',
            [ipc.RECOMPRESS_HOST, json.dumps({'host': host})]
        )

def discover_missing_dictionaries(conn):
    hosts = conn.execute('SELECT host FROM dss_fetch_cache GROUP BY 1 HAVING COUNT(*) > 100 EXCEPT SELECT host FROM dss_zstd_dict').fetchall()

    for host in hosts:
        host = host[0]
        with conn:
            config = json.dumps({'host': host})
            conn.execute(
                'INSERT INTO dss_ops(type, config) SELECT ?, ? WHERE NOT EXISTS(SELECT * FROM dss_ops WHERE finished_at IS NULL AND type = ? AND config = ?)',
                [
                    ipc.TRAIN_DICTIONARY,
                    config,
                    ipc.TRAIN_DICTIONARY,
                    config
                ]
            )

def seed_crawl(conn, job_id):
    config = get_crawl_config_for_job_id(conn, job_id)
    seeds = [url for urls in pm.hook.get_seed_urls(conn=conn, config=config, job_id=job_id) for url in urls]

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
