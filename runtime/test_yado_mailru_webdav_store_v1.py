from __future__ import annotations

import base64
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
import pathlib
import tempfile
import threading
import unittest
import urllib.parse
from unittest import mock

from yado_mailru_webdav_store_v1 import (
    MailRuConfig,
    MailRuWebDAVError,
    MailRuWebDAVStore,
    basic_auth_header,
    build_manifest,
    normalize_remote_path,
    readiness_report,
)


@contextmanager
def local_store(config=None):
    """Exercise the real transport using disposable credentials and a local server."""
    requests, files = [], {}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def respond(self, status, body=b"", **headers):
            requests.append((self.command, self.path))
            self.send_response(status)
            self.send_header("Content-Length", str(len(body)))
            for key, value in headers.items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)

        def do_MKCOL(self):
            self.respond(201)

        def do_PUT(self):
            files[self.path] = self.rfile.read(int(self.headers["Content-Length"]))
            self.respond(201)

        def do_GET(self):
            if self.path == "/redirect":
                self.respond(302, Location=f"http://localhost:{self.server.server_port}/destination")
            elif self.path == "/destination":
                self.respond(200, b"redirect followed")
            else:
                self.respond(200 if self.path in files else 404, files.get(self.path, b""))

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            store = MailRuWebDAVStore(config or MailRuConfig(user="test-user", app_password="dummy-only"))
            original_url = store._url

            def local_url(path):
                return f"http://127.0.0.1:{server.server_port}" + urllib.parse.urlsplit(original_url(path)).path

            with mock.patch.object(store, "_url", side_effect=local_url), mock.patch.dict(
                os.environ, {"no_proxy": "127.0.0.1,localhost"}
            ):
                yield store, requests
        finally:
            server.shutdown()
            thread.join(timeout=5)


class MailRuWebDAVStoreV1Tests(unittest.TestCase):
    def test_upload_download_round_trip_encodes_each_path_once(self):
        remote = "/YADO/a b/память 100%25.json"
        with local_store() as (store, requests):
            report = store.upload_bytes(b"verified bytes", remote)
            self.assertEqual(store.download_bytes(remote), b"verified bytes")
            self.assertEqual(store.download_bytes(report["remote_path"]), b"verified bytes")
        self.assertIn(("MKCOL", "/YADO/a%20b"), requests)
        self.assertIn(("PUT", normalize_remote_path(remote)), requests)

    def test_configured_root_is_encoded_once_for_file_upload(self):
        with mock.patch.dict(os.environ, {"YADO_MAILRU_ROOT": "/YADO/root space%", "YADO_MAILRU_USER": "test-user", "YADO_MAILRU_APP_PASSWORD": "dummy-only"}, clear=True):
            config = MailRuConfig.from_env()
        with tempfile.TemporaryDirectory() as td, local_store(config) as (store, requests):
            path = pathlib.Path(td) / "receipt data.json"
            path.write_bytes(b"receipt")
            store.upload_file(path)
            self.assertEqual(store.download_bytes("/YADO/root space%/receipt data.json"), b"receipt")
        self.assertIn(("MKCOL", "/YADO/root%20space%25"), requests)

    def test_authenticated_redirect_does_not_reach_destination(self):
        with local_store() as (store, requests):
            with self.assertRaisesRegex(MailRuWebDAVError, "HTTP 302"):
                store.download_bytes("/redirect")
        self.assertEqual(requests, [("GET", "/redirect")])

    def test_endpoint_rejects_credentials_and_non_https_before_status(self):
        for endpoint in ("http://example.com", "https://", "https://user:dummy@example.com", "https://example.com?token=dummy", "https://example.com#dummy", "https://example.com\n"):
            with self.subTest(endpoint=endpoint), self.assertRaises(ValueError):
                readiness_report(MailRuConfig(endpoint=endpoint))

    def test_normalize_remote_path(self):
        self.assertEqual(normalize_remote_path("YADO/receipts/a b.json"), "/YADO/receipts/a%20b.json")
        self.assertEqual(normalize_remote_path("/YADO//x/./y"), "/YADO/x/y")

    def test_reject_parent_traversal(self):
        with self.assertRaises(ValueError):
            normalize_remote_path("/YADO/../secret")

    def test_basic_auth_header_round_trip(self):
        header = basic_auth_header("user@example.com", "app-pass")
        self.assertTrue(header.startswith("Basic "))
        decoded = base64.b64decode(header.split(" ", 1)[1]).decode("utf-8")
        self.assertEqual(decoded, "user@example.com:app-pass")

    def test_readiness_without_credentials_exposes_no_secret(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            report = readiness_report(MailRuConfig.from_env())
        self.assertFalse(report["credentials_configured"])
        self.assertFalse(report["secret_values_exposed"])
        self.assertEqual(report["role"], "EXTERNAL_PERSISTENT_STORAGE_ONLY")
        self.assertFalse(report["remote_code_execution"])

    def test_manifest_hashes_files(self):
        with tempfile.TemporaryDirectory() as td:
            path = pathlib.Path(td) / "receipt.json"
            path.write_text('{"status":"PASS"}\n', encoding="utf-8")
            manifest = build_manifest([path])
        self.assertEqual(manifest["schema"], "yado.mailru_webdav_manifest.v1")
        self.assertEqual(len(manifest["files"]), 1)
        self.assertEqual(len(manifest["files"][0]["sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
