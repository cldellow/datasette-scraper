from ..hookspecs import hookimpl
from datetime import datetime
import time
import math
import httpx

@hookimpl(trylast=True)
def fetch_url(url, request_headers):
    start = time.time()
    fetched_at = datetime.utcnow().isoformat(sep=' ')
    response = httpx.get(url, headers=request_headers)
    duration = math.ceil(1000 * (time.time() - start))

    headers = []
    for k, v in response.headers.items():
        headers.append([k, v])
    return {
        'fresh': True,
        'fetched_at': fetched_at,
        'headers': headers,
        'status_code': response.status_code,
        'text': response.text,
        'duration': duration
    }
