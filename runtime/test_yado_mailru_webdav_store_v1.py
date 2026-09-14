from __future__ import annotations

import base64
import os
import pathlib
import tempfile
import unittest
from unittest import mock

from yado_mailru_webdav_store_v1 import (
    MailRuConfig,
    basic_auth_header,
    build_manifest,
    normalize_remote_path,
    readiness_report,
)


class MailRuWebDAVStoreV1Tests(unittest.TestCase):
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
