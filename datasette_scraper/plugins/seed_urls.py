from ..hookspecs import hookimpl

SEED_URLS = 'seed-urls'

@hookimpl
def get_seed_urls(config):
    if SEED_URLS in config:
        return config[SEED_URLS]

    return []

@hookimpl
def config_schema():
    from .. import ConfigSchema
    return ConfigSchema(
        schema = {
          'type': 'array',
          'items': {
            'type': 'string',
              'pattern': '^https?://.+'
          }
        },
        uischema = {},
        key = SEED_URLS,
        group = 'Crawls',
    )

@hookimpl
def config_default_value():
    return ['https://cldellow.com/']
