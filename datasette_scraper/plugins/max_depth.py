from ..hookspecs import hookimpl

@hookimpl
def before_fetch_url(config, depth):
    if 'max-depth' in config:
        max_depth = config['max-depth']

        if depth > max_depth:
            return 'max-depth {} exceeds depth {}'.format(max_depth, depth)

@hookimpl
def config_schema():
    from .. import ConfigSchema
    return ConfigSchema(
        schema = {
          'type': 'number',
        },
        uischema = {},
        key = 'max-depth',
        group = 'Limits',
    )

@hookimpl
def config_default_value():
    return 3
