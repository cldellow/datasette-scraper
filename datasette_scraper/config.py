import sqlite3
from .migrator import DBMigrator
from .schema import current_schema_version, schema
from .errors import ScraperError

# TODO: this should look for a configurable database
def get_database(datasette):
    return datasette.get_database()

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

def ensure_schema_internal(conn):
    ensure_wal_mode(conn)

    v, = conn.execute("PRAGMA user_version").fetchone()

    if not v:
        print('Installing datasette-scraper schema')
        #conn.execute('create table foo(version int)')
        with DBMigrator(conn, schema, allow_deletions=True) as migrator:
            migrator.migrate()
    elif v == current_schema_version:
        pass
    elif v == 1000000:
        # Nothing special required - this just added a table
        with DBMigrator(conn, schema, allow_deletions=True) as migrator:
            migrator.migrate()
    else:
        raise ScraperError('unsupported schema version: {} -- you may need to give datasette-scraper its own database'.format(v))

async def ensure_schema(db):
    await db.execute_write_fn(ensure_schema_internal, block=True)
    version = await get_db_version(db)

    if version != current_schema_version:
        raise ScraperError('unable to ensure schema in database {} (version={}; desired={}); please check that the database is mutable and not the _memory database'.format(db.name, version, current_schema_version))

    names = await db.table_names()
    # TODO: We should loop over our configs and enable WAL mode in any target database.
    #       Maybe there's a way to do that lazily, once?

