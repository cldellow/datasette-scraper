from ..hookspecs import hookimpl
from datetime import datetime
import httpx

@hookimpl(trylast=True)
def fetch_url(url, request_headers):
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
