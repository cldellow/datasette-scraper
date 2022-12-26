from .. import hookimpl

@hookimpl
def get_seed_urls(config):
    if 'seed-urls' in config:
        return config['seed-urls']

    return []

@hookimpl
def config_schema():
    return {
      'type': 'array',
      'items': {
        'type': 'string'
      }
    }

@hookimpl
def config_default_value():
    return []
