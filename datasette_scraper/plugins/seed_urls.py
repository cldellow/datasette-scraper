from ..hookspecs import hookimpl

@hookimpl
def get_seed_urls(config):
    if 'seed-urls' in config:
        return config['seed-urls']

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
        key = 'seed-urls',
        group = 'Crawls',
    )

@hookimpl
def config_default_value():
    return ['https://cldellow.com/']
