from __future__ import annotations

import argparse
import base64
import hashlib
import http.client
import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Optional

from cryptography.fernet import Fernet


HOST = "www.moltbook.com"
API_PREFIX = "/api/v1"
PROVIDER = "moltbook"


class MoltbookError(RuntimeError):
    pass


class MoltbookHTTPError(MoltbookError):
    def __init__(self, status: int, message: str):
        super().__init__(f"Moltbook HTTP {status}: {message}")
        self.status = status


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class EncryptedCredentialStore:
    """Store external credentials encrypted inside YADO's SQLite state.

    The encryption key is derived from YADO_MASTER_KEY. Unlike the older
    access-key bootstrap path, this store refuses to persist credentials when
    YADO_MASTER_KEY is absent, because the Moltbook key must survive restart.
    """

    def __init__(self, db_path: Optional[str] = None, master_key: Optional[str] = None):
        self.db_path = Path(db_path or os.getenv("YADO_DB_PATH", "cognitive_system_v2.db"))
        master = master_key if master_key is not None else os.getenv("YADO_MASTER_KEY")
        if not master:
            raise MoltbookError("YADO_MASTER_KEY is required for persistent external credentials")
        digest = hashlib.sha256(master.encode("utf-8")).digest()
        self._cipher = Fernet(base64.urlsafe_b64encode(digest))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS external_credentials (
                provider TEXT PRIMARY KEY,
                encrypted_secret BLOB NOT NULL,
                metadata_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "EncryptedCredentialStore":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def put(self, provider: str, secret: str, metadata: Optional[Mapping[str, Any]] = None) -> None:
        if not provider.strip() or not secret:
            raise ValueError("provider and secret are required")
        encrypted = self._cipher.encrypt(secret.encode("utf-8"))
        now = _utc_now()
        row = self.conn.execute(
            "SELECT created_at FROM external_credentials WHERE provider=?", (provider,)
        ).fetchone()
        created_at = row["created_at"] if row else now
        self.conn.execute(
            """
            INSERT OR REPLACE INTO external_credentials
            (provider, encrypted_secret, metadata_json, created_at, updated_at)
            VALUES(?,?,?,?,?)
            """,
            (provider, encrypted, _canonical_json(dict(metadata or {})), created_at, now),
        )
        self.conn.commit()

    def get_secret(self, provider: str) -> str:
        row = self.conn.execute(
            "SELECT encrypted_secret FROM external_credentials WHERE provider=?", (provider,)
        ).fetchone()
        if row is None:
            raise MoltbookError(f"no credential stored for provider {provider!r}")
        return self._cipher.decrypt(row["encrypted_secret"]).decode("utf-8")

    def metadata(self, provider: str) -> Dict[str, Any]:
        row = self.conn.execute(
            "SELECT metadata_json, created_at, updated_at FROM external_credentials WHERE provider=?",
            (provider,),
        ).fetchone()
        if row is None:
            raise MoltbookError(f"no credential stored for provider {provider!r}")
        return {
            **json.loads(row["metadata_json"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }


@dataclass(frozen=True)
class MoltbookRegistration:
    agent_name: str
    claim_url: str
    verification_code: str
    status: str
    api_key_stored: bool = True


class MoltbookClient:
    """Minimal Moltbook client with a hard host boundary.

    The API key can only be attached to requests sent directly to
    www.moltbook.com under /api/v1/. Redirects are not followed.
    """

    def __init__(
        self,
        store: EncryptedCredentialStore,
        timeout: float = 20.0,
        connection_factory: Optional[Callable[..., Any]] = None,
    ):
        self.store = store
        self.timeout = float(timeout)
        self._connection_factory = connection_factory or http.client.HTTPSConnection

    @staticmethod
    def _validate_path(path: str) -> str:
        if not path.startswith(API_PREFIX + "/"):
            raise MoltbookError("Moltbook API path must stay under /api/v1/")
        if "://" in path or "\r" in path or "\n" in path:
            raise MoltbookError("invalid Moltbook API path")
        return path

    def _request(
        self,
        method: str,
        path: str,
        payload: Optional[Mapping[str, Any]] = None,
        *,
        authenticated: bool,
    ) -> Dict[str, Any]:
        path = self._validate_path(path)
        headers = {
            "Accept": "application/json",
            "User-Agent": "YADO-Moltbook/1.0",
        }
        body: Optional[bytes] = None
        if payload is not None:
            body = _canonical_json(dict(payload)).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if authenticated:
            headers["Authorization"] = f"Bearer {self.store.get_secret(PROVIDER)}"

        conn = self._connection_factory(HOST, timeout=self.timeout)
        try:
            conn.request(method.upper(), path, body=body, headers=headers)
            response = conn.getresponse()
            raw = response.read(1_000_001)
        finally:
            conn.close()

        if len(raw) > 1_000_000:
            raise MoltbookError("Moltbook response exceeded 1 MB")
        text = raw.decode("utf-8", errors="replace")
        try:
            data = json.loads(text) if text else {}
        except json.JSONDecodeError as exc:
            raise MoltbookHTTPError(response.status, "non-JSON response") from exc
        if not 200 <= response.status < 300:
            message = str(data.get("error") or data.get("message") or "request failed")[:300]
            raise MoltbookHTTPError(response.status, message)
        if not isinstance(data, dict):
            raise MoltbookError("unexpected Moltbook response shape")
        return data

    def register(self, name: str, description: str) -> MoltbookRegistration:
        # The store is initialized before this call, so a durable encryption key
        # already exists before Moltbook issues a credential.
        data = self._request(
            "POST",
            f"{API_PREFIX}/agents/register",
            {"name": name, "description": description},
            authenticated=False,
        )
        agent = data.get("agent")
        if not isinstance(agent, dict):
            raise MoltbookError("registration response did not contain agent data")
        api_key = str(agent.get("api_key") or "")
        claim_url = str(agent.get("claim_url") or "")
        verification_code = str(agent.get("verification_code") or "")
        if not api_key or not claim_url or not verification_code:
            raise MoltbookError("registration response is missing required fields")

        self.store.put(
            PROVIDER,
            api_key,
            {
                "agent_name": str(agent.get("name") or name),
                "agent_id": agent.get("id"),
                "claim_url": claim_url,
                "verification_code": verification_code,
                "status": str(data.get("status") or "pending_claim"),
            },
        )
        # Never return or print the API key.
        return MoltbookRegistration(
            agent_name=str(agent.get("name") or name),
            claim_url=claim_url,
            verification_code=verification_code,
            status=str(data.get("status") or "pending_claim"),
        )

    def status(self) -> Dict[str, Any]:
        return self._request("GET", f"{API_PREFIX}/agents/status", authenticated=True)

    def me(self) -> Dict[str, Any]:
        return self._request("GET", f"{API_PREFIX}/agents/me", authenticated=True)

    def feed(self, sort: str = "new", limit: int = 25) -> Dict[str, Any]:
        safe_sort = sort if sort in {"new", "hot", "top"} else "new"
        safe_limit = max(1, min(int(limit), 50))
        return self._request(
            "GET",
            f"{API_PREFIX}/feed?sort={safe_sort}&limit={safe_limit}",
            authenticated=True,
        )

    def create_post(self, title: str, content: str, submolt: str = "general") -> Dict[str, Any]:
        return self._request(
            "POST",
            f"{API_PREFIX}/posts",
            {"submolt_name": submolt, "title": title, "content": content},
            authenticated=True,
        )

    def comment(self, post_id: str, content: str) -> Dict[str, Any]:
        if not post_id or "/" in post_id:
            raise ValueError("invalid post_id")
        return self._request(
            "POST",
            f"{API_PREFIX}/posts/{post_id}/comments",
            {"content": content},
            authenticated=True,
        )


def build_client(db_path: Optional[str] = None) -> MoltbookClient:
    return MoltbookClient(EncryptedCredentialStore(db_path=db_path))


def _main() -> int:
    parser = argparse.ArgumentParser(description="YADO Moltbook bridge")
    parser.add_argument("--db", default=None, help="YADO SQLite state path")
    sub = parser.add_subparsers(dest="command", required=True)

    p_register = sub.add_parser("register", help="register YADO and store the API key encrypted")
    p_register.add_argument("--name", default="YADO")
    p_register.add_argument(
        "--description",
        default="YADO digital-reasoning research agent: bounded learning, verification and reproducible development.",
    )
    sub.add_parser("status")
    sub.add_parser("me")

    p_feed = sub.add_parser("feed")
    p_feed.add_argument("--sort", default="new")
    p_feed.add_argument("--limit", type=int, default=25)

    p_post = sub.add_parser("post")
    p_post.add_argument("--submolt", default="general")
    p_post.add_argument("--title", required=True)
    p_post.add_argument("--content", required=True)

    p_comment = sub.add_parser("comment")
    p_comment.add_argument("--post-id", required=True)
    p_comment.add_argument("--content", required=True)

    args = parser.parse_args()
    with EncryptedCredentialStore(db_path=args.db) as store:
        client = MoltbookClient(store)
        if args.command == "register":
            result = client.register(args.name, args.description)
            print(_canonical_json(result.__dict__))
        elif args.command == "status":
            print(_canonical_json(client.status()))
        elif args.command == "me":
            print(_canonical_json(client.me()))
        elif args.command == "feed":
            print(_canonical_json(client.feed(args.sort, args.limit)))
        elif args.command == "post":
            print(_canonical_json(client.create_post(args.title, args.content, args.submolt)))
        elif args.command == "comment":
            print(_canonical_json(client.comment(args.post_id, args.content)))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
