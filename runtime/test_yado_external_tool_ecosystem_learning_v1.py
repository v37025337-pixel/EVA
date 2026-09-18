from __future__ import annotations

import hashlib
import json
import unittest

from yado_external_tool_ecosystem_learning_v1 import (
    ExternalToolEcosystemLearningV1,
    SOURCES,
    existing_component_bindings,
    validate_evidence_records,
)


def safe_receipt(content: str):
    return {
        "read_only": True,
        "credentials_used": False,
        "external_write": False,
        "private_network_access": False,
        "downloaded_code_executed": False,
        "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
    }


def fake_fetch(url: str):
    for spec in SOURCES.values():
        if url == f"https://api.github.com/repos/{spec['repo']}":
            content = json.dumps(
                {
                    "full_name": spec["repo"],
                    "default_branch": spec["branch"],
                }
            )
            return {"content": content, "receipt": safe_receipt(content)}
        if url == (
            f"https://raw.githubusercontent.com/"
            f"{spec['repo']}/{spec['branch']}/README.md"
        ):
            content = " ".join(spec["markers"])
            return {"content": content, "receipt": safe_receipt(content)}
    raise AssertionError(url)


class ExternalToolEcosystemLearningV1Tests(unittest.TestCase):
    def test_existing_components_are_reused(self):
        bindings = existing_component_bindings(".")
        self.assertEqual(bindings["status"], "PASS")
        self.assertEqual(bindings["new_third_party_adapter_count"], 0)
        self.assertEqual(
            bindings["bindings"]["hivemind"]["capability"],
            "TASK_CONTRACT_AND_AGENT_SUPERVISION_PATTERN",
        )
        self.assertEqual(
            bindings["bindings"]["free_for_dev"]["capability"],
            "FREE_TIER_RESOURCE_DISCOVERY",
        )
        self.assertIn(
            "web_search_exa",
            bindings["bindings"]["exa_mcp"]["tools"],
        )
        self.assertIn(
            "artifact_structure_extraction",
            bindings["bindings"]["ghidra"]["capabilities"],
        )

    def test_complete_aggregate_passes(self):
        result = ExternalToolEcosystemLearningV1().study(fake_fetch, repo_root=".")
        self.assertEqual(
            result["status"],
            "PASS_SHADOW_EXTERNAL_TOOL_ECOSYSTEM_AGGREGATION_V1",
        )
        self.assertEqual(result["verified_source_count"], 4)
        self.assertEqual(result["evidence_gate"]["status"], "PASS")
        self.assertTrue(result["reuses_existing_components"])
        self.assertEqual(result["new_third_party_adapter_count"], 0)
        self.assertFalse(result["third_party_code_executed"])
        self.assertFalse(result["automatic_canonical_mutation"])

    def test_weak_source_withholds_aggregate(self):
        target = SOURCES["ghidra"]

        def weak_fetch(url: str):
            if url == (
                f"https://raw.githubusercontent.com/"
                f"{target['repo']}/{target['branch']}/README.md"
            ):
                content = "generic repository text"
                return {"content": content, "receipt": safe_receipt(content)}
            return fake_fetch(url)

        result = ExternalToolEcosystemLearningV1().study(weak_fetch, repo_root=".")
        self.assertEqual(
            result["status"],
            "WITHHOLD_EXTERNAL_TOOL_ECOSYSTEM_AGGREGATION_V1",
        )
        self.assertIn("ghidra", result["withheld_sources"])

    def test_unsafe_receipt_withholds_aggregate(self):
        target = SOURCES["exa_mcp"]

        def unsafe_fetch(url: str):
            result = fake_fetch(url)
            if url == f"https://api.github.com/repos/{target['repo']}":
                result["receipt"]["external_write"] = True
            return result

        result = ExternalToolEcosystemLearningV1().study(unsafe_fetch, repo_root=".")
        self.assertEqual(
            result["status"],
            "WITHHOLD_EXTERNAL_TOOL_ECOSYSTEM_AGGREGATION_V1",
        )
        self.assertIn("exa_mcp", result["withheld_sources"])

    def test_gate_rejects_duplicate_and_non_https(self):
        records = [
            {
                "source_id": "A",
                "domain": "web_research",
                "url": "https://example.com/a",
                "provenance": {"sha256": "x"},
                "claims": ["ONE"],
            },
            {
                "source_id": "A",
                "domain": "web_research",
                "url": "http://example.com/b",
                "provenance": {"sha256": "y"},
                "claims": ["TWO"],
            },
        ]
        gate = validate_evidence_records(records)
        self.assertEqual(gate["status"], "WITHHOLD")
        self.assertTrue(any("duplicate_source_id" in item for item in gate["errors"]))
        self.assertTrue(any("https_url_required" in item for item in gate["errors"]))

    def test_digest_is_deterministic(self):
        first = ExternalToolEcosystemLearningV1().study(fake_fetch, repo_root=".")
        second = ExternalToolEcosystemLearningV1().study(fake_fetch, repo_root=".")
        self.assertEqual(first["study_digest"], second["study_digest"])


if __name__ == "__main__":
    unittest.main()
