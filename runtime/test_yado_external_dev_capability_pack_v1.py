import hashlib
import json
import unittest
from urllib.parse import urlsplit

from yado_external_dev_capability_pack_v1 import ExternalDevCapabilityPackV1, SOURCES


README = {
    "hivemind": "AI agent worktree acceptance criteria MCP canvas",
    "hoppscotch": "GraphQL WebSocket Collections Post-Request tests API",
    "dyad": "local open-source AI app builder bring your own keys",
    "nexustools": "100% client-side JSON Formatter JWT Decoder Diff Checker",
    "free_for_dev": "free tier Major Cloud Providers CI and CD Web Hosting\n* [Cloud Example](https://cloud.example.com) - serverless cloud compute free tier\n* [API Example](https://api.example.com) - APIs testing free tier",
}


def result(url, content):
    return {
        "content": content,
        "receipt": {
            "final_url": url,
            "final_host": urlsplit(url).hostname,
            "http_status": 200,
            "content_type": "application/json" if "api.github.com" in url else "text/plain",
            "sha256": hashlib.sha256(content.encode()).hexdigest(),
            "bytes": len(content.encode()),
            "read_only": True,
            "credentials_used": False,
            "external_write": False,
            "private_network_access": False,
        },
    }


def fake_fetch(url):
    for key, spec in SOURCES.items():
        if url == spec["metadata"]:
            return result(url, json.dumps({"full_name": spec["repo"], "default_branch": spec["branch"], "visibility": "public"}))
        if url == spec["readme"]:
            return result(url, README[key])
        if spec["license"] and url == spec["license"]:
            text = "Apache License Version 2.0" if key == "dyad" else "MIT License"
            return result(url, text)
    if url == "https://api.example.com/status":
        return result(url, '{"status":"ok"}')
    raise AssertionError(url)


class ExternalDevCapabilityPackTests(unittest.TestCase):
    def setUp(self):
        self.pack = ExternalDevCapabilityPackV1()

    def test_refresh_binds_five_verified_sources_without_copy_or_execution(self):
        out = self.pack.refresh(fake_fetch)
        self.assertEqual(out["status"], "PASS_EXTERNAL_DEV_CAPABILITY_PACK_V1")
        self.assertEqual(out["source_count"], 5)
        self.assertEqual(len(out["capabilities"]), 5)
        self.assertFalse(out["code_copy_performed"])
        self.assertFalse(out["third_party_code_executed"])
        dyad = next(x for x in out["sources"] if x["key"] == "dyad")
        self.assertIn("src/pro", dyad["restricted_paths"])
        free = next(x for x in out["sources"] if x["key"] == "free_for_dev")
        self.assertIn("NO_CODE_COPY", free["license_mode"])

    def test_each_source_pattern_has_an_exercisable_native_capability(self):
        task = self.pack.task_contract("repair api", ["tests pass", "audit pass"])
        self.assertEqual(task["source_pattern"], "dip497/hivemind")
        probe = self.pack.api_probe(fake_fetch, "https://api.example.com/status", must_contain="ok")
        self.assertEqual(probe["status"], "PASS_READ_ONLY_API_ASSERTION")
        plan = self.pack.app_build_plan("build dashboard", "python+web", ["unit", "regression"])
        self.assertIn("ADMISSION", plan["phases"])
        utility = self.pack.utility("json_minify", '{"b":2,"a":1}')
        self.assertEqual(utility["output"], '{"b":2,"a":1}')
        resources = self.pack.free_resource_candidates(fake_fetch, ["serverless", "compute"])
        self.assertEqual(resources["status"], "PASS_FREE_TIER_RESOURCE_DISCOVERY")
        self.assertEqual(resources["results"][0]["name"], "Cloud Example")

    def test_local_utilities_are_network_free(self):
        encoded = self.pack.utility("base64_encode", "YADO")
        decoded = self.pack.utility("base64_decode", encoded["output"])
        self.assertEqual(decoded["output"], "YADO")
        digest = self.pack.utility("sha256", "YADO")
        self.assertEqual(len(digest["output"]), 64)
        self.assertTrue(digest["local_only"])


if __name__ == "__main__":
    unittest.main()
