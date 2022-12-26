import sqlite3
from .migrator import DBMigrator
from .schema import current_schema_version, schema
from .errors import ScraperError

# TODO: this should look for a configurable database
def get_database(datasette):
    print('get_database called')
    return datasette.get_database()

async def get_db_version(db):
    results = await db.execute('pragma user_version')
    for row in results:
        return row['user_version']

def ensure_schema_internal(conn):
    v, = conn.execute("PRAGMA user_version").fetchone()

    if not v:
        print('Installing datasette-scraper schema')
        #conn.execute('create table foo(version int)')
        with DBMigrator(conn, schema, allow_deletions=True) as migrator:
            migrator.migrate()
    elif v == current_schema_version:
        pass
    else:
        raise ScraperError('unexpected schema version: {}'.format(v))

async def ensure_schema(db):
    version = await get_db_version(db)
    names = await db.table_names()
    await db.execute_write_fn(ensure_schema_internal, block=True)
    version = await get_db_version(db)

    if version != current_schema_version:
        raise ScraperError('unable to ensure schema in database {} (version={}; desired={}); please check that the database is mutable and not the _memory database'.format(db.name, version, current_schema_version))

    names = await db.table_names()

