from ..hookspecs import hookimpl
from urllib.parse import urlparse

MAX_PAGES_PER_DOMAIN = 'max-pages-per-domain'

@hookimpl
def canonicalize_url(conn, config, job_id, to_url):
    if MAX_PAGES_PER_DOMAIN in config:
        max_pages = config[MAX_PAGES_PER_DOMAIN]

        parsed = urlparse(to_url)
        host = parsed.hostname

        fetched, = conn.execute('SELECT COALESCE(SUM(fetched), 0) FROM dss_job_stats WHERE job_id = ? AND host = ?', [job_id, host]).fetchone()
        if fetched > max_pages:
            return 'max-pages-per-domain {} is less than fetched pages for domain {} ({})'.format(max_pages, host, fetched)

@hookimpl
def config_schema():
    from .. import ConfigSchema
    return ConfigSchema(
        schema = {
          'type': 'number',
        },
        uischema = {
            "type": "Control",
            "scope": '#/properties/{}'.format(MAX_PAGES_PER_DOMAIN)
        },
        key = MAX_PAGES_PER_DOMAIN,
        group = 'Links',
        sort = 120,
    )

@hookimpl
def config_default_value():
    return 1000
