from ..hookspecs import hookimpl

MAX_DEPTH = 'max-depth'

@hookimpl
def canonicalize_url(config, to_url_depth):
    if MAX_DEPTH in config:
        max_depth = config[MAX_DEPTH]

        if to_url_depth > max_depth:
            return False

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
