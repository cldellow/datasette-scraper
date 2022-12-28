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
    return ConfigSchema(
        schema = {
            'type': 'object',
            'properties': {
                'rules': {
                    'type': 'array',
                    'items': {
                        'type': 'object',
                        'properties': {
                            'url-regex': {
                                'type': 'string',
                            },
                            'max-age': {
                                'type': 'integer',
                            }
                        },
                        'required': ['max-age']
                    }
                }
            },
            'required': ['rules']
        },
        uischema = {},
        key = FETCH_CACHE,
        group = 'Crawls',
    )

@hookimpl
def config_default_value():
    return {
        'rules': [
            {
                'url-regex': '.*',
                'max-age': 3600
            }
        ]
    }
