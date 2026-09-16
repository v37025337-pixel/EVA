import unittest

from test_yado_external_dev_capability_pack_v1 import fake_fetch
from yado_unified_core_external_dev_capability_pack_v1 import UnifiedYADOCoreExternalDevCapabilityPackV1


class UnifiedCoreExternalDevCapabilityPackTests(unittest.TestCase):
    def setUp(self):
        self.core = UnifiedYADOCoreExternalDevCapabilityPackV1()

    def test_core_audit_binds_pack_without_generation_change(self):
        audit = self.core.audit()
        self.assertTrue(audit["pass"], audit)
        snap = self.core.snapshot()
        self.assertEqual(snap["generation"], "G2_CANDIDATE_TRCG_V1")
        self.assertEqual(snap["external_dev_capability_pack"]["source_count"], 5)
        self.assertFalse(snap["external_dev_capability_pack"]["automatic_canonical_mutation"])

    def test_core_refresh_and_use_all_five_patterns(self):
        refreshed = self.core.refresh_external_dev_capabilities(fetch_override=fake_fetch)
        self.assertEqual(refreshed["status"], "PASS_EXTERNAL_DEV_CAPABILITY_PACK_V1")
        self.assertEqual(refreshed["core_route"], self.core.EXTERNAL_DEV_LAYER_ID)
        self.assertEqual(self.core.external_dev_task_contract("x", ["a"])["source_pattern"], "dip497/hivemind")
        self.assertEqual(self.core.external_dev_api_probe("https://api.example.com/status", must_contain="ok", fetch_override=fake_fetch)["status"], "PASS_READ_ONLY_API_ASSERTION")
        self.assertEqual(self.core.external_dev_app_build_plan("x", "python", ["tests"])["source_pattern"], "dyad-sh/dyad")
        self.assertTrue(self.core.external_dev_utility("json_format", '{"x":1}')["local_only"])
        self.assertGreater(self.core.external_dev_free_resource_candidates(["serverless"], fetch_override=fake_fetch)["result_count"], 0)


if __name__ == "__main__":
    unittest.main()
