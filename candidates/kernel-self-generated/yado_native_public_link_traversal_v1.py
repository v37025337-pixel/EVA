import re
from urllib.parse import urljoin, urlparse

def extract_public_links(parent_url, html, max_links=64):
    if not (isinstance(parent_url, str) and isinstance(html, str)):
        return []
    seen = set()
    out = []
    limit = max(1, int(max_links))
    for raw in re.findall('href\\s*=\\s*[\\"\']([^\\"\']+)[\\"\']', html, flags=re.I):
        raw = raw.strip()
        if not raw:
            continue
        absolute = urljoin(parent_url, raw)
        parsed = urlparse(absolute)
        if parsed.scheme not in ('http', 'https') or not parsed.netloc:
            continue
        normalized = parsed._replace(fragment='').geturl()
        if normalized in seen:
            continue
        seen.add(normalized)
        out.append({'parent_url': parent_url, 'url': normalized, 'scheme': parsed.scheme, 'host': parsed.hostname or '', 'source': 'HTML_HREF'})
        if len(out) >= limit:
            break
    return out
