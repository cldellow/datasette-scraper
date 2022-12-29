from ..hookspecs import hookimpl

MAX_DEPTH = 'max-depth'

@hookimpl
def before_fetch_url(config, depth):
    if MAX_DEPTH in config:
        max_depth = config[MAX_DEPTH]

        if depth > max_depth:
            return 'max-depth {} is less than depth {}'.format(max_depth, depth)

@hookimpl
def config_schema():
    from .. import ConfigSchema
    return ConfigSchema(
        schema = {
          'type': 'number',
        },
        uischema = {
            "type": "Control",
            "scope": '#/properties/{}'.format(MAX_DEPTH)
        },
        key = MAX_DEPTH,
        group = 'Links',
        sort = 100,
    )

@hookimpl
def config_default_value():
    return 3
