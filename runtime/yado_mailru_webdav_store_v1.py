from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import pathlib
import posixpath
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Iterable

DEFAULT_ENDPOINT = "https://webdav.cloud.mail.ru"
DEFAULT_ROOT = "/YADO"
USER_ENV = "YADO_MAILRU_USER"
PASSWORD_ENV = "YADO_MAILRU_APP_PASSWORD"


class MailRuWebDAVError(RuntimeError):
    pass


def _normalize_path(path: str) -> str:
    """Normalize a decoded application path; percent signs remain literal."""
    if not path:
        return "/"
    raw = path.replace("\\", "/")
    if any(ord(ch) < 32 for ch in raw):
        raise ValueError("control characters are not allowed in remote paths")
    parts = [p for p in raw.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        raise ValueError("parent traversal is not allowed")
    return "/" + "/".join(parts)


def normalize_remote_path(path: str) -> str:
    """Encode a decoded remote path for transport, exactly once."""
    return "/".join(urllib.parse.quote(p, safe="@._-()[]{}") for p in _normalize_path(path).split("/"))


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Authenticated WebDAV requests must never forward credentials to a redirect.
        return None


def basic_auth_header(user: str, password: str) -> str:
    token = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass(frozen=True)
class MailRuConfig:
    endpoint: str = DEFAULT_ENDPOINT
    root: str = DEFAULT_ROOT
    user: str | None = None
    app_password: str | None = None
    timeout: int = 30

    def __post_init__(self):
        endpoint = self.endpoint
        if any(ord(ch) <= 32 or ord(ch) == 127 for ch in endpoint):
            raise ValueError("control characters and whitespace are not allowed in WebDAV endpoints")
        parsed = urllib.parse.urlsplit(endpoint)
        if (parsed.scheme != "https" or not parsed.hostname
                or parsed.username is not None or parsed.password is not None
                or "?" in endpoint or "#" in endpoint):
            raise ValueError("WebDAV endpoint must use HTTPS without credentials, query or fragment")
        if parsed.port is not None and parsed.port == 0:
            raise ValueError("invalid WebDAV endpoint port")
        object.__setattr__(self, "endpoint", endpoint.rstrip("/"))
        object.__setattr__(self, "root", _normalize_path(self.root))

    @classmethod
    def from_env(cls) -> "MailRuConfig":
        return cls(
            endpoint=os.environ.get("YADO_MAILRU_WEBDAV_ENDPOINT", DEFAULT_ENDPOINT).rstrip("/"),
            root=os.environ.get("YADO_MAILRU_ROOT", DEFAULT_ROOT),
            user=os.environ.get(USER_ENV),
            app_password=os.environ.get(PASSWORD_ENV),
            timeout=int(os.environ.get("YADO_MAILRU_TIMEOUT", "30")),
        )

    @property
    def ready(self) -> bool:
        return bool(self.user and self.app_password)


class MailRuWebDAVStore:
    def __init__(self, config: MailRuConfig | None = None):
        self.config = config or MailRuConfig.from_env()
        self._opener = urllib.request.build_opener(_NoRedirect())

    def _url(self, remote_path: str) -> str:
        path = normalize_remote_path(remote_path)
        return self.config.endpoint + path

    def _request(
        self,
        method: str,
        remote_path: str,
        *,
        data: bytes | None = None,
        headers: dict[str, str] | None = None,
        accepted: Iterable[int] = (200, 201, 204, 207),
    ) -> tuple[int, bytes]:
        if not self.config.ready:
            raise MailRuWebDAVError(
                f"missing credentials: configure {USER_ENV} and {PASSWORD_ENV} as protected secrets"
            )
        request_headers = {
            "Authorization": basic_auth_header(self.config.user or "", self.config.app_password or ""),
            "User-Agent": "YADO-MailRu-WebDAV/1",
        }
        if headers:
            request_headers.update(headers)
        req = urllib.request.Request(
            self._url(remote_path), data=data, method=method, headers=request_headers
        )
        try:
            with self._opener.open(req, timeout=self.config.timeout) as response:
                body = response.read()
                status = int(response.status)
        except urllib.error.HTTPError as exc:
            status = int(exc.code)
            body = exc.read()
            if status not in set(accepted):
                raise MailRuWebDAVError(f"WebDAV {method} failed with HTTP {status}") from exc
        except urllib.error.URLError as exc:
            raise MailRuWebDAVError(f"WebDAV {method} transport error: {exc.reason}") from exc
        if status not in set(accepted):
            raise MailRuWebDAVError(f"WebDAV {method} unexpected HTTP {status}")
        return status, body

    def ensure_directory(self, remote_dir: str) -> None:
        path = _normalize_path(remote_dir)
        current = ""
        for part in [p for p in path.split("/") if p]:
            current += "/" + part
            self._request("MKCOL", current, accepted=(201, 405))

    def upload_bytes(self, data: bytes, remote_path: str, *, content_type: str = "application/octet-stream") -> dict:
        target = _normalize_path(remote_path)
        parent = posixpath.dirname(target) or "/"
        self.ensure_directory(parent)
        status, _ = self._request(
            "PUT",
            target,
            data=data,
            headers={"Content-Type": content_type, "Content-Length": str(len(data))},
            accepted=(200, 201, 204),
        )
        return {
            "status": "PASS_MAILRU_WEBDAV_UPLOAD_V1",
            "remote_path": target,
            "bytes": len(data),
            "sha256": sha256_bytes(data),
            "http_status": status,
        }

    def upload_file(self, local_path: pathlib.Path, remote_path: str | None = None) -> dict:
        local_path = pathlib.Path(local_path)
        data = local_path.read_bytes()
        remote = remote_path or posixpath.join(self.config.root, local_path.name)
        return self.upload_bytes(data, remote)

    def download_bytes(self, remote_path: str) -> bytes:
        _, body = self._request("GET", remote_path, accepted=(200, 206))
        return body


def build_manifest(paths: Iterable[pathlib.Path]) -> dict:
    items = []
    for path in paths:
        p = pathlib.Path(path)
        items.append({"path": str(p), "bytes": p.stat().st_size, "sha256": sha256_file(p)})
    return {"schema": "yado.mailru_webdav_manifest.v1", "files": items}


def readiness_report(config: MailRuConfig | None = None) -> dict:
    cfg = config or MailRuConfig.from_env()
    return {
        "schema": "yado.mailru_webdav_store.v1",
        "endpoint": cfg.endpoint,
        "root": cfg.root,
        "credentials_configured": cfg.ready,
        "secret_values_exposed": False,
        "role": "EXTERNAL_PERSISTENT_STORAGE_ONLY",
        "remote_code_execution": False,
        "status": "READY_FOR_LIVE_WEBDAV" if cfg.ready else "READY_REQUIRES_PROTECTED_CREDENTIALS",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--upload", type=pathlib.Path)
    parser.add_argument("--remote")
    args = parser.parse_args()
    store = MailRuWebDAVStore()
    if args.upload:
        result = store.upload_file(args.upload, args.remote)
    else:
        result = readiness_report(store.config)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
