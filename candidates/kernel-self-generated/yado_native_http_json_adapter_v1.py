import hashlib
import json
from urllib.parse import urlparse
from urllib.request import Request, urlopen

def _validate_url(url, allowed_hosts):
    if not isinstance(url, str):
        raise ValueError('URL_TYPE')
    parsed = urlparse(url)
    host = (parsed.hostname or '').lower()
    allowed = {str(x).lower() for x in allowed_hosts}
    if parsed.scheme not in ('http', 'https'):
        raise ValueError('SCHEME_NOT_ALLOWED')
    if not host or host not in allowed:
        raise ValueError('HOST_NOT_ALLOWED')
    return host

def _summarize(payload):
    if isinstance(payload, dict):
        return {'type': 'dict', 'size': len(payload), 'keys': sorted((str(k) for k in payload))[:32]}
    if isinstance(payload, list):
        return {'type': 'list', 'size': len(payload), 'item_types': sorted({type(x).__name__ for x in payload})[:16]}
    return {'type': type(payload).__name__, 'size': None}

def fetch_json(url, allowed_hosts, timeout=10.0, max_bytes=262144):
    _validate_url(url, allowed_hosts)
    timeout = max(1.0, min(float(timeout), 15.0))
    max_bytes = max(1024, min(int(max_bytes), 1048576))
    request = Request(url, headers={'User-Agent': 'YADO-Bounded-Integration/1.0', 'Accept': 'application/json'}, method='GET')
    with urlopen(request, timeout=timeout) as response:
        final_url = response.geturl()
        _validate_url(final_url, allowed_hosts)
        status = int(getattr(response, 'status', 200))
        content_type = str(response.headers.get('Content-Type', ''))
        raw = response.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise ValueError('RESPONSE_TOO_LARGE')
    if status < 200 or status >= 300:
        raise ValueError('HTTP_STATUS_' + str(status))
    text = raw.decode('utf-8', errors='strict')
    payload = json.loads(text)
    return {'url': url, 'final_url': final_url, 'status': status, 'content_type': content_type, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'summary': _summarize(payload), 'payload': payload}
