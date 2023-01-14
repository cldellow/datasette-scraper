from ..hookspecs import hookimpl
import re

DISCOVER_ALLOW = 'discover-allow'

_re = {}

@hookimpl
def canonicalize_url(config, from_url, to_url, to_url_depth):
    if not DISCOVER_ALLOW in config or not config[DISCOVER_ALLOW]:
        return

    allows = config[DISCOVER_ALLOW]

    desired_depth = None
    permitted = False

    for allow in allows:
        from_compiled = None
        to_compiled = None

        if 'from-url-regex' in allow:
            from_re = allow['from-url-regex']
            if from_re in _re:
                from_compiled = _re[from_re]
            else:
                from_compiled = re.compile(from_re)
                _re[from_re] = from_compiled

        if 'to-url-regex' in allow:
            to_re = allow['to-url-regex']
            if to_re in _re:
                to_compiled = _re[to_re]
            else:
                to_compiled = re.compile(to_re)
                _re[to_re] = to_compiled

        if (not from_compiled or from_compiled.search(from_url)) and (not to_compiled or to_compiled.search(to_url)):
            permitted = True

            if 'depth' in allow:
                depth = int(allow['depth'])

                if desired_depth == None or desired_depth > depth:
                    desired_depth = depth

    if not permitted:
        return False

    # Allowed, use default depth
    if desired_depth == None:
        return True

    return (to_url, desired_depth)

@hookimpl
def config_schema():
    from .. import ConfigSchema
    return ConfigSchema(
        schema = {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'from-url-regex': {
                        'type': 'string',
                    },
                    'to-url-regex': {
                        'type': 'string',
                    },
                    'depth': {
                        'type': 'integer',
                    },
                },
            }
        },
        uischema = {
            "type": "Control",
            "scope": '#/properties/{}'.format(DISCOVER_ALLOW),
            'label': "Only crawl URLs matching these regexes"
        },
        key = DISCOVER_ALLOW,
        sort = 2900,
        group = 'Links',
    )

@hookimpl
def config_default_value():
    return []
