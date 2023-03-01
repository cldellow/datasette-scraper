import re
from ..hookspecs import hookimpl
from ..utils import get_html_parser
from urllib.parse import urljoin

EXTRACT_SEO = 'extract-seo'

_re = {}

@hookimpl
def extract_from_response(config, url, response):
    if not EXTRACT_SEO in config:
        return {}

    if response['status_code'] != 200:
        return {}

    if url.endswith('.xml') or url.endswith('/robots.txt'):
        return {}

    rv = {}

    for options in config[EXTRACT_SEO]:
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

        table.append({'url!': url, '__delete': True})

        row = {'url!': url}

        parsed = get_html_parser(response)
        title = parsed.css('title')
        if title:
            row['title'] = title[0].text().strip()

        table.append(row)

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
                    'include-article': {
                        'type': 'boolean',
                    },
                },
                'required': ['database', 'table']
            }
        },
        uischema = {
            "type": "Control",
            "scope": '#/properties/{}'.format(EXTRACT_SEO),
            'label': 'Extract basic SEO info (title, metadesc, publish date)'
        },
        key = EXTRACT_SEO,
        group = 'Extracting',
    )

@hookimpl
def config_default_value():
    return []
