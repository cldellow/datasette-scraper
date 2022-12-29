from ..hookspecs import hookimpl
from urllib.parse import urlparse

FOLLOW_REDIRECTS = 'follow-redirects'

@hookimpl
def discover_urls(config, url, response):
    if not FOLLOW_REDIRECTS in config or not config[FOLLOW_REDIRECTS]:
        return []

    for (k, v) in response['headers']:
        if k == 'location':
            return [v]

    return []


@hookimpl
def config_schema():
    from .. import ConfigSchema
    return ConfigSchema(
        schema = {
          'type': 'boolean',
          'title': 'Follow HTTP 3xx redirects',
        },
        uischema = {
            "type": "Control",
            "scope": '#/properties/{}'.format(FOLLOW_REDIRECTS)
        },
        key = FOLLOW_REDIRECTS,
        group = 'Links',
        sort = -1
    )

@hookimpl
def config_default_value():
    return True
