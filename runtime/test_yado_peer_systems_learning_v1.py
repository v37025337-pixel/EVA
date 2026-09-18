from __future__ import annotations

import json
import unittest

from yado_peer_systems_learning_v1 import PeerSystemsLearningV1, SOURCES

def fake_fetch(url: str):
    for spec in SOURCES.values():
        if url == f"https://api.github.com/repos/{spec['repo']}":
            content = json.dumps({"full_name": spec["repo"], "default_branch": spec["branch"], "license": {"spdx_id": "TEST"}})
            return {"content": content, "receipt": safe_receipt(content)}
        if url == f"https://raw.githubusercontent.com/{spec['repo']}/{spec['branch']}/README.md":
            content = " ".join(spec["markers"]) + " " + " ".join(spec["focus"])
            return {"content": content, "receipt": safe_receipt(content)}
    raise AssertionError(url)

def safe_receipt(content: str):
    import hashlib
    return {
        "read_only": True,
        "credentials_used": False,
        "external_write": False,
        "private_network_access": False,
        "downloaded_code_executed": False,
        "sha256": hashlib.sha256(content.encode()).hexdigest(),
    }

class PeerSystemsLearningV1Tests(unittest.TestCase):
    def test_study_is_read_only_and_provenance_bound(self):
        result = PeerSystemsLearningV1().study(fake_fetch)
        self.assertEqual(result["status"], "PASS_SHADOW_PEER_SYSTEMS_LEARNING_V1")
        self.assertEqual(result["verified_source_count"], len(SOURCES))
        self.assertFalse(result["third_party_code_executed"])
        self.assertFalse(result["third_party_code_copied"])
        self.assertTrue(result["study_digest"])
        self.assertTrue(all(row["metadata_sha256"] and row["readme_sha256"] for row in result["sources"]))

if __name__ == "__main__":
    unittest.main()
