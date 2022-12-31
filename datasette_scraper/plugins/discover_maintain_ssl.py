from ..hookspecs import hookimpl
from urllib.parse import urlparse

DISCOVER_MAINTAIN_SSL = 'discover-maintain-ssl'

@hookimpl
def canonicalize_url(config, from_url, to_url, to_url_depth):
    if not DISCOVER_MAINTAIN_SSL in config or not config[DISCOVER_MAINTAIN_SSL]:
        return

    from_ = urlparse(from_url)
    to_ = urlparse(to_url)

    return from_.scheme == 'http' or to_.scheme == 'https'

@hookimpl
def config_schema():
    from .. import ConfigSchema
    return ConfigSchema(
        schema = {
          'type': 'boolean',
          'title': 'Ignore links to http:// sites from https:// sites',
        },
        uischema = {
            "type": "Control",
            "scope": '#/properties/{}'.format(DISCOVER_MAINTAIN_SSL)
        },
        key = DISCOVER_MAINTAIN_SSL,
        group = 'Links',
        sort = 20
    )

@hookimpl
def config_default_value():
    return True
