from ..hookspecs import hookimpl
from urllib.parse import urlparse

DISCOVER_ONLY_SAME_ORIGIN = 'discover-only-same-origin'

@hookimpl
def canonicalize_url(config, from_url, to_url, to_url_depth):
    if not DISCOVER_ONLY_SAME_ORIGIN in config or not config[DISCOVER_ONLY_SAME_ORIGIN]:
        return

    from_ = urlparse(from_url)
    to_ = urlparse(to_url)

    return from_.hostname == to_.hostname

@hookimpl
def config_schema():
    from .. import ConfigSchema
    return ConfigSchema(
        schema = {
          'type': 'boolean',
          'title': 'Stay on same domain',
        },
        uischema = {
            "type": "Control",
            "scope": '#/properties/{}'.format(DISCOVER_ONLY_SAME_ORIGIN)
        },
        key = DISCOVER_ONLY_SAME_ORIGIN,
        group = 'Links',
        sort = 0
    )

@hookimpl
def config_default_value():
    return True
