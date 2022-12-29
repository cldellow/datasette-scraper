from ..hookspecs import hookimpl
from ..utils import get_html_parser
import re

DISCOVER_HTML_LINKS = 'discover-html-links'

_re = {}

def discover(response, url, options):
    # Only scan for links if url-regex is absent, or matches url
    if 'url-regex' in options:
        regex = options['url-regex']
        if regex in _re:
            compiled = _re[regex]
        else:
            compiled = re.compile(regex)
            _re[regex] = compiled

        if not compiled.search(url):
            return []

    parsed = get_html_parser(response)
    els = parsed.css(options['selector'])
    attribute = None
    if 'attribute' in options:
        attribute = options['attribute']

    depth = None
    if 'depth' in options:
        depth = options['depth']

    rv = []
    for p in els:
        needle = ''
        if attribute:
            attrs = p.attributes
            if attribute in attrs:
                needle = attrs[attribute]
        else:
            needle = p.text()


        if needle and needle.strip():
            if depth == None:
                rv.append(needle.strip())
            else:
                rv.append((needle.strip(), depth))

    return rv

@hookimpl
def discover_urls(config, url, response):
    if not DISCOVER_HTML_LINKS in config:
        return []

    sources = config[DISCOVER_HTML_LINKS]

    rv = []

    for source in sources:
        rv.extend(discover(response, url, source))

    return list(set(rv))

@hookimpl
def config_schema():
    from .. import ConfigSchema
    return ConfigSchema(
        schema = {
          'type': 'array',
          'items': {
              'type': 'object',
              'properties': {
                  'url-regex': {
                      'type': 'string',
                      'title': 'On pages with URLs matching...',
                  },
                  'selector': {
                      'type': 'string',
                      'default': 'a',
                      'title': 'CSS Selector',
                      'description': 'description',
                      'examples': ['example']
                  },
                  'attribute': {
                      'type': 'string',
                      'title': 'HTML Attribute',
                  },
                  'depth': {
                      'type': 'integer',
                      'title': 'Depth',
                  }
              },
              'required': ['selector']
          }
        },
        uischema = {
            "type": "Control",
            "scope": '#/properties/{}'.format(DISCOVER_HTML_LINKS),
            'label': 'Find links in HTML content',
        },
        key = DISCOVER_HTML_LINKS,
        sort = 2000,
        group = 'Links',
    )

@hookimpl
def config_default_value():
    return [{
        'selector': 'a',
        'attribute': 'href',
    }]
