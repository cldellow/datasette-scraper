import sqlite3
from .migrator import DBMigrator
from .schema import current_schema_version, schema
from .errors import ScraperError

_plugin_name = 'datasette-scraper'

_enabled_databases = None

def enabled_databases(datasette, empty_if_not_initialized=False):
    global _enabled_databases

    if not _enabled_databases is None:
        return _enabled_databases

    if empty_if_not_initialized:
        return []

    global_config = datasette.plugin_config(_plugin_name)

    rv = []

    for db_name in datasette.databases:
        local_config = datasette.plugin_config(_plugin_name, db_name)

        if local_config is None:
            continue

        rv.append(db_name)

    _enabled_databases = rv
    return _enabled_databases

async def get_db_version(db):
    results = await db.execute('pragma user_version')
    for row in results:
        return row['user_version']

def ensure_wal_mode(conn):
    old_level = conn.isolation_level
    try:
        conn.isolation_level = None
        mode, = conn.execute('PRAGMA journal_mode=WAL').fetchone()
        if mode != 'wal':
            raise Exception('unable to set PRAGMA journal_mode=WAL on connection, got {}'.format(mode))
    finally:
        conn.isolation_level = old_level

async def ensure_schema(db):
    def ensure_schema_internal(conn):
        ensure_wal_mode(conn)

        v, = conn.execute("PRAGMA user_version").fetchone()

        if not v:
            print('Installing datasette-scraper schema into db {}'.format(db.name))
            #conn.execute('create table foo(version int)')
            with DBMigrator(conn, schema, allow_deletions=True) as migrator:
                migrator.migrate()
        elif v == current_schema_version:
            pass
        elif v == 1000000 or v == 1000001 or v == 1000002:
            # Nothing special required - these just added tables/columns/indexes
            with DBMigrator(conn, schema, allow_deletions=True) as migrator:
                migrator.migrate()
        else:
            raise ScraperError('unsupported schema version in db {}: {} -- you may need to give datasette-scraper its own database'.format(db.name, v))


    await db.execute_write_fn(ensure_schema_internal, block=True)
    version = await get_db_version(db)

    if version != current_schema_version:
        raise ScraperError('unable to ensure schema in database {} (version={}; desired={}); please check that the database is mutable and not the _memory database'.format(db.name, version, current_schema_version))

    names = await db.table_names()
    # TODO: We should loop over our configs and enable WAL mode in any target database.
    #       Maybe there's a way to do that lazily, once?

