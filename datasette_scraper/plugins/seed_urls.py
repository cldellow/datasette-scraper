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
        uischema = {
            "type": "Control",
            "scope": '#/properties/{}'.format(SEED_URLS),
            'label': 'URLs'
        },
        key = SEED_URLS,
        group = 'Seeds',
    )

@hookimpl
def config_default_value():
    return []
