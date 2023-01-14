from ..hookspecs import hookimpl
from datetime import datetime
import base64
import re
import hashlib
import httpx
import json
from ..zstd import get_decompressor, get_compressor
from urllib.parse import urlparse

FETCH_CACHE = 'fetch-cache'

_re = {}

def request_hash(url, request_headers):
    return base64.b85encode(hashlib.sha1((url + ':' + json.dumps(request_headers)).encode('utf-8')).digest()).decode()

@hookimpl(trylast=True)
def fetch_cached_url(conn, config, url, depth, request_headers):
    if not FETCH_CACHE in config or not config[FETCH_CACHE]:
        return

    max_age = None
    for option in config[FETCH_CACHE]:
        regex = option['url-regex']
        if regex in _re:
            compiled = _re[regex]
        else:
            compiled = re.compile(regex)
            _re[regex] = compiled

        if compiled.search(url) or compiled.search('depth:{}'.format(depth)):
            if max_age is None or max_age > option['max-age']:
                max_age = option['max-age']

    if max_age is None:
        return None

    hash = request_hash(url, request_headers)

    row = conn.execute("SELECT object, dict_id FROM dss_fetch_cache WHERE request_hash = ? AND fetched_at >= strftime('%Y-%m-%d %H:%M:%f', 'now', ?)", [hash, '-{} seconds'.format(max_age)]).fetchone()

    if not row:
        return None

    # TODO: consider batching these in a txn to reduce write lock contention
    with conn:
        conn.execute("UPDATE dss_fetch_cache SET read_at = strftime('%Y-%m-%d %H:%M:%f') WHERE request_hash = ?", [hash]).fetchone()


    object, dict_id = row

    object = get_decompressor(conn, dict_id).decompress(object)

    return json.loads(object.decode('utf-8'))

@hookimpl()
def after_fetch_url(conn, config, url, request_headers, response, fresh, fetch_duration):
    if not fresh:
        return

    # Don't store entries if we're disabled.
    if not FETCH_CACHE in config or not config[FETCH_CACHE]:
        return

    fetched_at = response['fetched_at']

    host = urlparse(url).hostname
    hash = request_hash(url, request_headers)
    response['_request_hash'] = hash

    dict_id = conn.execute('SELECT id FROM dss_zstd_dict WHERE host = ? AND active = 1 ORDER BY id DESC LIMIT 1', [host]).fetchone()

    if dict_id:
        dict_id = dict_id[0]

    compressor = get_compressor(conn, dict_id)

    object = json.dumps(response).encode('utf-8')
    object = compressor.compress(object)
    with conn:
        conn.execute('INSERT OR REPLACE INTO dss_fetch_cache(request_hash, host, url, fetched_at, read_at, object, dict_id) VALUES(?, ?, ?, ?, ?, ?, ?)', [hash, host, url, fetched_at, fetched_at, object, dict_id])


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
            'required': ['url-regex', 'max-age']
        }
    }

    return ConfigSchema(
        schema = array_object,
        uischema = {
            "type": "Control",
            "scope": "#/properties/{}".format(FETCH_CACHE),
            "label": "Re-use previously downloaded pages"
        },

        key = FETCH_CACHE,
        group = 'Caching',
    )

@hookimpl
def config_default_value():
    return [
            {
                'url-regex': '.*',
                'max-age': 604800
            }
        ]
