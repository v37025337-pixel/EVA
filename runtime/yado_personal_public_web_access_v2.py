from __future__ import annotations

"""Broad public-HTTPS read-only access for YADO.

The capability is intentionally broad by hostname and narrow by authority:
public HTTPS GET/HEAD only, no credentials, no proxies, no private-network
addresses, no downloaded-code execution, and no external writes. DNS answers
are validated before each request and the TLS socket is pinned to one of those
validated public IP addresses to avoid a validate-then-re-resolve gap.
"""

import hashlib
import http.client
import ipaddress
import json
import socket
import ssl
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, urlunsplit

SCHEMA = "yado.personal_public_web_access.v2"
POLICY = "PUBLIC_HTTPS_READ_ONLY_DNS_PINNED_V2"
USER_AGENT = "YADO-Personal-Public-Web-Access/2.0"
MAX_BYTES = 2_000_000
MAX_REDIRECTS = 5
MAX_DISCOVERED_LINKS = 64
ALLOWED_METHODS = frozenset({"GET", "HEAD"})
REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
DENIED_HOSTS = frozenset({
    "localhost",
    "localhost.localdomain",
    "metadata.google.internal",
    "instance-data",
    "instance-data.ec2.internal",
})
DENIED_SUFFIXES = (".localhost", ".local", ".internal", ".lan", ".home", ".invalid", ".test")
TEXT_CONTENT_TYPES = frozenset({
    "application/json",
    "application/ld+json",
    "application/xml",
    "application/xhtml+xml",
    "application/rss+xml",
    "application/atom+xml",
})


class PublicWebAccessError(ValueError):
    pass


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _public_ip(value: str) -> str:
    try:
        address = ipaddress.ip_address(value)
    except ValueError as exc:
        raise PublicWebAccessError("INVALID_RESOLVED_IP") from exc
    if not address.is_global:
        raise PublicWebAccessError("NON_PUBLIC_IP_REJECTED")
    return address.compressed


def _hostname(value: str) -> str:
    raw = value.rstrip(".")
    if not raw:
        raise PublicWebAccessError("HOST_REQUIRED")
    try:
        ipaddress.ip_address(raw)
        return raw.lower()
    except ValueError:
        pass
    try:
        host = raw.encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise PublicWebAccessError("INVALID_HOSTNAME") from exc
    if host in DENIED_HOSTS or any(host.endswith(suffix) for suffix in DENIED_SUFFIXES):
        raise PublicWebAccessError("LOCAL_OR_METADATA_HOST_REJECTED")
    return host


def _normalized_url(parsed, host: str) -> str:
    try:
        (parsed.path or "/").encode("ascii")
        parsed.query.encode("ascii")
    except UnicodeEncodeError as exc:
        raise PublicWebAccessError("NON_ASCII_URL_MUST_BE_PERCENT_ENCODED") from exc
    netloc = f"[{host}]" if ":" in host else host
    return urlunsplit(("https", netloc, parsed.path or "/", parsed.query, ""))


def validate_public_https_url(url: str, resolver=socket.getaddrinfo) -> dict:
    if not isinstance(url, str) or not url or len(url) > 4096:
        raise PublicWebAccessError("INVALID_URL")
    parsed = urlsplit(url)
    if parsed.scheme.lower() != "https":
        raise PublicWebAccessError("HTTPS_REQUIRED")
    if parsed.username is not None or parsed.password is not None:
        raise PublicWebAccessError("URL_CREDENTIALS_REJECTED")
    try:
        port = parsed.port
    except ValueError as exc:
        raise PublicWebAccessError("INVALID_PORT") from exc
    if port not in (None, 443):
        raise PublicWebAccessError("PORT_443_REQUIRED")
    if parsed.hostname is None:
        raise PublicWebAccessError("HOST_REQUIRED")
    host = _hostname(parsed.hostname)

    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None

    if literal is not None:
        addresses = [_public_ip(host)]
    else:
        try:
            infos = resolver(host, 443, type=socket.SOCK_STREAM)
        except OSError as exc:
            raise PublicWebAccessError("DNS_RESOLUTION_FAILED") from exc
        raw_addresses = []
        for item in infos:
            if len(item) < 5 or not item[4]:
                continue
            raw_addresses.append(str(item[4][0]))
        if not raw_addresses:
            raise PublicWebAccessError("DNS_NO_ADDRESSES")
        # Reject the entire name if *any* answer is non-public. A mixed public/private
        # answer must never become an SSRF ambiguity.
        addresses = [_public_ip(address) for address in raw_addresses]

    # Prefer IPv4 only for connection ordering; IPv6 remains fully supported.
    addresses = sorted(set(addresses), key=lambda x: (":" in x, x))
    return {
        "url": _normalized_url(parsed, host),
        "host": host,
        "port": 443,
        "approved_ips": addresses,
        "dns_answer_count": len(addresses),
        "policy": POLICY,
    }


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host: str, pinned_ip: str, timeout: float):
        self._pinned_ip = pinned_ip
        context = ssl.create_default_context()
        super().__init__(host, port=443, timeout=timeout, context=context)

    def connect(self):
        sock = socket.create_connection((self._pinned_ip, 443), self.timeout, self.source_address)
        try:
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except Exception:
            sock.close()
            raise


def _request_once(target: dict, method: str, timeout: float, max_bytes: int) -> dict:
    parsed = urlsplit(target["url"])
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query
    last_error = None
    for ip in target["approved_ips"]:
        conn = _PinnedHTTPSConnection(target["host"], ip, timeout)
        try:
            conn.request(
                method,
                path,
                headers={
                    "Host": target["host"],
                    "User-Agent": USER_AGENT,
                    "Accept": "text/html,text/plain,application/json,application/xml,application/xhtml+xml;q=0.9,*/*;q=0.1",
                    "Connection": "close",
                },
            )
            response = conn.getresponse()
            headers = {str(k).lower(): str(v) for k, v in response.getheaders()}
            declared = headers.get("content-length")
            if declared and declared.isdigit() and int(declared) > max_bytes:
                raise PublicWebAccessError("RESPONSE_TOO_LARGE")
            body = b"" if method == "HEAD" else response.read(max_bytes + 1)
            if len(body) > max_bytes:
                raise PublicWebAccessError("RESPONSE_TOO_LARGE")
            return {
                "status": int(response.status),
                "headers": headers,
                "body": body,
                "connected_ip": ip,
            }
        except PublicWebAccessError:
            raise
        except (OSError, ssl.SSLError, http.client.HTTPException) as exc:
            last_error = exc
        finally:
            conn.close()
    raise PublicWebAccessError("PUBLIC_HTTPS_TRANSPORT_FAILED") from last_error


def _textual(content_type: str) -> bool:
    media = content_type.split(";", 1)[0].strip().lower()
    return media.startswith("text/") or media in TEXT_CONTENT_TYPES


def _decode(body: bytes, content_type: str) -> str:
    charset = "utf-8"
    for part in content_type.split(";")[1:]:
        key, sep, value = part.strip().partition("=")
        if sep and key.lower() == "charset" and value.strip():
            charset = value.strip().strip('"\'')
            break
    try:
        return body.decode(charset, errors="replace")
    except LookupError:
        return body.decode("utf-8", errors="replace")


def fetch_public(
    url: str,
    *,
    method: str = "GET",
    timeout: float = 15.0,
    max_bytes: int = MAX_BYTES,
    max_redirects: int = MAX_REDIRECTS,
    resolver=socket.getaddrinfo,
    transport=None,
) -> dict:
    method = str(method).upper()
    if method not in ALLOWED_METHODS:
        raise PublicWebAccessError("READ_ONLY_METHOD_REQUIRED")
    if not (1 <= int(max_bytes) <= MAX_BYTES):
        raise PublicWebAccessError("INVALID_BYTE_BUDGET")
    if not (0 <= int(max_redirects) <= MAX_REDIRECTS):
        raise PublicWebAccessError("INVALID_REDIRECT_BUDGET")
    if timeout <= 0 or timeout > 60:
        raise PublicWebAccessError("INVALID_TIMEOUT")

    request_once = transport or _request_once
    current = url
    redirects = []
    visited = set()
    resolution_history = []

    for hop in range(max_redirects + 1):
        target = validate_public_https_url(current, resolver=resolver)
        if target["url"] in visited:
            raise PublicWebAccessError("REDIRECT_LOOP_REJECTED")
        visited.add(target["url"])
        resolution_history.append({
            "host": target["host"],
            "approved_ips": list(target["approved_ips"]),
        })
        response = request_once(target, method, timeout, int(max_bytes))
        status = int(response["status"])
        headers = {str(k).lower(): str(v) for k, v in dict(response.get("headers", {})).items()}
        body = response.get("body", b"")
        if not isinstance(body, (bytes, bytearray)):
            raise PublicWebAccessError("TRANSPORT_BODY_MUST_BE_BYTES")
        body = bytes(body)
        if len(body) > max_bytes:
            raise PublicWebAccessError("RESPONSE_TOO_LARGE")

        if status in REDIRECT_STATUSES:
            if hop >= max_redirects:
                raise PublicWebAccessError("REDIRECT_BUDGET_EXHAUSTED")
            location = headers.get("location")
            if not location:
                raise PublicWebAccessError("REDIRECT_WITHOUT_LOCATION")
            next_url = urljoin(target["url"], location)
            # Validate before another transport call. The next loop validates again
            # immediately before the pinned connection.
            next_target = validate_public_https_url(next_url, resolver=resolver)
            redirects.append({"from": target["url"], "to": next_target["url"], "status": status})
            current = next_target["url"]
            continue

        if not 200 <= status < 300:
            raise PublicWebAccessError("HTTP_STATUS_NOT_SUCCESS")
        content_type = headers.get("content-type", "")
        if method == "GET" and not _textual(content_type):
            raise PublicWebAccessError("NON_TEXT_CONTENT_REJECTED")
        text = "" if method == "HEAD" else _decode(body, content_type)
        receipt = {
            "schema": SCHEMA,
            "status": "PASS_PERSONAL_PUBLIC_WEB_ACCESS_V2",
            "policy": POLICY,
            "method": method,
            "requested_url": url,
            "final_url": target["url"],
            "final_host": target["host"],
            "connected_ip": response.get("connected_ip"),
            "resolution_history": resolution_history,
            "redirects": redirects,
            "http_status": status,
            "content_type": content_type,
            "bytes": len(body),
            "sha256": _sha256(body),
            "read_only": True,
            "credentials_used": False,
            "cookies_used": False,
            "proxy_used": False,
            "external_write": False,
            "downloaded_code_executed": False,
            "private_network_access": False,
            "automatic_canonical_mutation": False,
        }
        return {"content": text, "receipt": receipt}

    raise PublicWebAccessError("UNREACHABLE_REDIRECT_STATE")


class _LinkParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() not in {"a", "link"}:
            return
        for key, value in attrs:
            if key.lower() == "href" and value:
                self.links.append(str(value))


def discover_links(content: str, base_url: str, *, limit: int = 24, resolver=socket.getaddrinfo) -> list[dict]:
    if not isinstance(content, str):
        raise PublicWebAccessError("TEXT_CONTENT_REQUIRED")
    if not 1 <= int(limit) <= MAX_DISCOVERED_LINKS:
        raise PublicWebAccessError("INVALID_DISCOVERY_LIMIT")
    base = validate_public_https_url(base_url, resolver=resolver)
    parser = _LinkParser()
    parser.feed(content[:MAX_BYTES])
    out = []
    seen = set()
    for raw in parser.links:
        candidate = urljoin(base["url"], raw)
        try:
            target = validate_public_https_url(candidate, resolver=resolver)
        except PublicWebAccessError:
            continue
        if target["url"] in seen:
            continue
        seen.add(target["url"])
        out.append({
            "url": target["url"],
            "host": target["host"],
            "approved_ips": target["approved_ips"],
            "policy": POLICY,
        })
        if len(out) >= limit:
            break
    return out


def channel_snapshot() -> dict:
    return {
        "schema": SCHEMA,
        "status": "AVAILABLE_BROAD_PUBLIC_HTTPS_READ_ONLY_V2",
        "authority": "KERNEL_OWNED_PUBLIC_READ_ONLY_TRANSPORT",
        "domain_allowlist_required": False,
        "scheme": "https",
        "methods": sorted(ALLOWED_METHODS),
        "port": 443,
        "dns_public_only": True,
        "dns_pinned_transport": True,
        "redirect_revalidation": True,
        "credentials": False,
        "external_writes": False,
        "private_networks": False,
        "downloaded_code_execution": False,
        "max_bytes": MAX_BYTES,
        "max_redirects": MAX_REDIRECTS,
        "automatic_canonical_mutation": False,
    }


__all__ = [
    "PublicWebAccessError",
    "POLICY",
    "validate_public_https_url",
    "fetch_public",
    "discover_links",
    "channel_snapshot",
]
