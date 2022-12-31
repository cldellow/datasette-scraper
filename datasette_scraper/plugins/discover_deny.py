from ..hookspecs import hookimpl
import re

DISCOVER_DENY = 'discover-deny'

_re = {}

@hookimpl
def canonicalize_url(config, from_url, to_url, to_url_depth):
    if not DISCOVER_DENY in config:
        return

    reject_res = config[DISCOVER_DENY]

    for reject_re in reject_res:
        if reject_re in _re:
            compiled = _re[reject_re]
        else:
            compiled = re.compile(reject_re)
            _re[reject_re] = compiled

        if compiled.search(to_url):
            return False

@hookimpl
def config_schema():
    from .. import ConfigSchema
    return ConfigSchema(
        schema = {
          'type': 'array',
          'items': {
              'type': 'string',
          }
        },
        uischema = {
            "type": "Control",
            "scope": '#/properties/{}'.format(DISCOVER_DENY),
            'label': "Never crawl URLs matching these regexes"
        },
        key = DISCOVER_DENY,
        sort = 3000,
        group = 'Links',
    )

@hookimpl
def config_default_value():
    return [
        # Try to avoid binary file types
        '(?i)[.](bmp|gif|gz|jpg|jpeg|m4a|m4v|mov|mpg|mpeg|mp3|mp4|pdf|png|tar|webp|wma|wmv|xls|xlsx|xz|zip)'
    ]
