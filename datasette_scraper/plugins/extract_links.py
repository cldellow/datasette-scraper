import re
from ..hookspecs import hookimpl
from ..utils import get_html_parser
from urllib.parse import urljoin

EXTRACT_LINKS = 'extract-links'

_re = {}

@hookimpl
def extract_from_response(config, url, response):
    if not EXTRACT_LINKS in config:
        return {}

    rv = {}

    for options in config[EXTRACT_LINKS]:
        if 'url-regex' in options:
            regex = options['url-regex']
            if regex in _re:
                compiled = _re[regex]
            else:
                compiled = re.compile(regex)
                _re[regex] = compiled

            if not compiled.search(url):
                continue

        dbname = options['database']
        tablename = options['table']

        if dbname in rv:
            database = rv[dbname]
        else:
            database = rv[dbname] = {}

        if tablename in database:
            table = database[tablename]
        else:
            table = database[tablename] = []

        # Get all the links
        parsed = get_html_parser(response)
        for a in parsed.css('a'):
            attrs = a.attributes
            dofollow = 1

            if 'rel' in attrs and attrs['rel'] and 'nofollow' in attrs['rel']:
                dofollow = 0


            if 'href' in attrs:
                table.append({'from!': url, 'to!': urljoin(url, attrs['href']), 'text!': a.text().strip(), 'dofollow!': dofollow})

    return rv

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
                    },
                    'database': {
                        'type': 'string',
                    },
                    'table': {
                        'type': 'string',
                    },
                },
                'required': ['database', 'table']
            }
        },
        uischema = {
            "type": "Control",
            "scope": '#/properties/{}'.format(EXTRACT_LINKS),
            'label': 'Extract link graph'
        },
        key = EXTRACT_LINKS,
        group = 'Extracting',
    )

@hookimpl
def config_default_value():
    return []
