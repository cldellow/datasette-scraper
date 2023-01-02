import re
import json
from ..hookspecs import hookimpl
from ..utils import get_html_parser
from urllib.parse import urljoin

EXTRACT_JSON_LD = 'extract-json-ld'

_re = {}

@hookimpl
def extract_from_response(config, url, response):
    if not EXTRACT_JSON_LD in config:
        return {}

    rv = {}

    for options in config[EXTRACT_JSON_LD]:
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
        table.append({'url@': url, '__delete': True})
        for script in parsed.css('script[type="application/ld+json"]'):
            try:
                parsed = json.dumps(json.loads(script.text()))
                table.append({'url@': url, 'json': parsed})
            except:
                pass

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
            "scope": '#/properties/{}'.format(EXTRACT_JSON_LD),
            'label': 'Extract JSON+LD entries'
        },
        key = EXTRACT_JSON_LD,
        sort = 2000,
        group = 'Extracting',
    )

@hookimpl
def config_default_value():
    return []
