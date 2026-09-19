import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from successor.moltbook import (
    API_PREFIX,
    HOST,
    EncryptedCredentialStore,
    MoltbookClient,
    MoltbookError,
)


class FakeResponse:
    def __init__(self, status, payload):
        self.status = status
        self._raw = json.dumps(payload).encode("utf-8")

    def read(self, _limit):
        return self._raw


class FakeConnection:
    calls = []
    responses = []

    def __init__(self, host, timeout=20.0):
        self.host = host
        self.timeout = timeout

    def request(self, method, path, body=None, headers=None):
        self.__class__.calls.append(
            {
                "host": self.host,
                "method": method,
                "path": path,
                "body": body,
                "headers": dict(headers or {}),
            }
        )

    def getresponse(self):
        if not self.__class__.responses:
            raise AssertionError("no fake response queued")
        status, payload = self.__class__.responses.pop(0)
        return FakeResponse(status, payload)

    def close(self):
        return None


class MoltbookBridgeTests(unittest.TestCase):
    def setUp(self):
        FakeConnection.calls = []
        FakeConnection.responses = []
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "state.sqlite3")
        self.store = EncryptedCredentialStore(self.db, master_key="unit-test-master-key")
        self.client = MoltbookClient(self.store, connection_factory=FakeConnection)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_registration_encrypts_key_and_never_returns_it(self):
        FakeConnection.responses.append(
            (
                200,
                {
                    "status": "pending_claim",
                    "agent": {
                        "id": "agent-1",
                        "name": "YADO",
                        "api_key": "moltbook_secret_value",
                        "claim_url": "https://www.moltbook.com/claim/test",
                        "verification_code": "reef-TEST",
                    },
                },
            )
        )
        result = self.client.register("YADO", "test")
        self.assertEqual(result.agent_name, "YADO")
        self.assertTrue(result.api_key_stored)
        self.assertNotIn("api_key", result.__dict__)
        self.assertEqual(self.store.get_secret("moltbook"), "moltbook_secret_value")

        raw = Path(self.db).read_bytes()
        self.assertNotIn(b"moltbook_secret_value", raw)
        self.assertNotIn(b"Authorization", raw)

    def test_authenticated_request_is_host_pinned(self):
        self.store.put("moltbook", "moltbook_secret_value", {"agent_name": "YADO"})
        FakeConnection.responses.append((200, {"status": "claimed"}))
        result = self.client.status()
        self.assertEqual(result["status"], "claimed")
        call = FakeConnection.calls[-1]
        self.assertEqual(call["host"], HOST)
        self.assertEqual(call["path"], f"{API_PREFIX}/agents/status")
        self.assertEqual(call["headers"]["Authorization"], "Bearer moltbook_secret_value")

    def test_registration_request_has_no_authorization_header(self):
        FakeConnection.responses.append(
            (
                200,
                {
                    "agent": {
                        "name": "YADO",
                        "api_key": "moltbook_secret_value",
                        "claim_url": "https://www.moltbook.com/claim/test",
                        "verification_code": "reef-TEST",
                    }
                },
            )
        )
        self.client.register("YADO", "test")
        self.assertNotIn("Authorization", FakeConnection.calls[0]["headers"])

    def test_rejects_non_api_path_before_network(self):
        with self.assertRaises(MoltbookError):
            self.client._request("GET", "https://evil.example/api/v1/feed", authenticated=False)
        self.assertEqual(FakeConnection.calls, [])

    def test_post_uses_stored_key(self):
        self.store.put("moltbook", "moltbook_secret_value", {"agent_name": "YADO"})
        FakeConnection.responses.append((201, {"success": True, "post": {"id": "p1"}}))
        result = self.client.create_post("hello", "world")
        self.assertTrue(result["success"])
        call = FakeConnection.calls[-1]
        body = json.loads(call["body"].decode("utf-8"))
        self.assertEqual(body["submolt_name"], "general")
        self.assertEqual(call["headers"]["Authorization"], "Bearer moltbook_secret_value")

    def test_requires_persistent_master_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(MoltbookError):
                EncryptedCredentialStore(str(Path(self.tmp.name) / "other.sqlite3"))


if __name__ == "__main__":
    unittest.main()
