from ..hookspecs import hookimpl
from datetime import datetime
import httpx

FETCH_CACHE = 'fetch-cache'

@hookimpl(trylast=True)
def fetch_cached_url(url, request_headers):
    fetched_at = datetime.utcnow().isoformat(sep=' ')
    response = httpx.get(url, headers=request_headers)

    headers = []
    for k, v in response.headers.items():
        headers.append([k, v])
    return {
        'fetched_at': fetched_at,
        'headers': headers,
        'status_code': response.status_code,
        'text': response.text,
    }

@hookimpl
def config_schema():
    from .. import ConfigSchema

    array_object = {
        'type': 'array',
        'items': {
            'type': 'object',
            'properties': {
                'url-regex': {
                    'type': 'string',
                    'title': 'URL Regex',
                },
                'max-age': {
                    'type': 'integer',
                    'title': "Max Age (seconds)"
                }
            },
            'required': ['max-age']
        }
    }

    return ConfigSchema(
        schema = array_object,
        uischema = {
            "type": "Control",
            "scope": "#/properties/{}".format(FETCH_CACHE),
            "label": "Cache previously downloaded pages"
        },

        key = FETCH_CACHE,
        group = 'Caching',
    )

@hookimpl
def config_default_value():
    return [
            {
                'url-regex': '.*',
                'max-age': 3600
            }
        ]
