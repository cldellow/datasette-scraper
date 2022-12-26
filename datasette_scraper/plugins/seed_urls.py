from .. import hookimpl

@hookimpl
def get_seed_urls(config):
    if 'seed-urls' in config:
        return config['seed-urls']

    return []
