from ..hookspecs import hookimpl

MAX_PAGES = 'max-pages'

@hookimpl
def canonicalize_url(conn, config, job_id):
    if MAX_PAGES in config:
        max_pages = config[MAX_PAGES]

        fetched, = conn.execute('SELECT COALESCE(SUM(fetched), 0) FROM dss_job_stats WHERE job_id = ?', [job_id]).fetchone()
        if fetched > max_pages:
            return 'max-pages {} is less than fetched pages ({})'.format(max_pages, fetched)

@hookimpl
def config_schema():
    from .. import ConfigSchema
    return ConfigSchema(
        schema = {
          'type': 'number',
        },
        uischema = {
            "type": "Control",
            "scope": '#/properties/{}'.format(MAX_PAGES)
        },
        key = MAX_PAGES,
        group = 'Links',
        sort = 110,
    )

@hookimpl
def config_default_value():
    return 1000
