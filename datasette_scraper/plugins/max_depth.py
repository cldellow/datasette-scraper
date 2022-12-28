from ..hookspecs import hookimpl

MAX_DEPTH = 'max-depth'

@hookimpl
def before_fetch_url(config, depth):
    if MAX_DEPTH in config:
        max_depth = config[MAX_DEPTH]

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
        key = MAX_DEPTH,
        group = 'Limits',
    )

@hookimpl
def config_default_value():
    return 3
