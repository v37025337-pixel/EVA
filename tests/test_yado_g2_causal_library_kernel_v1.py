import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
MOD = ROOT / "runtime/yado_g2_causal_library_kernel_v1.py"
spec = importlib.util.spec_from_file_location("yado_g2_causal_library_kernel_v1", MOD)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class TestG2CausalLibraryKernelV1(unittest.TestCase):
    def setUp(self):
        self.kernel = module.G2CausalLibraryKernelV1(ROOT)

    def test_library_and_genetics_validate(self):
        result = self.kernel.validate()
        self.assertEqual(result["status"], "PASS_CAUSAL_LIBRARY_KERNEL_V1")
        self.assertEqual(result["normal_dispatch_count"], 26)
        self.assertEqual(result["compatibility_fallback_count"], 5)
        self.assertEqual(result["layer_count"], 8)
        self.assertFalse(result["g3_genesis"])
        self.assertEqual(result["training_source_count"], 141)
        self.assertEqual(result["training_fetched_count"], 130)
        self.assertEqual(result["dynamic_memory_branch_count"], 20)
        self.assertEqual(result["dynamic_memory_raw_lineage_count"], 0)
        self.assertEqual(result["dynamic_memory_rederived_count"], 6)
        self.assertEqual(result["latest_applied_experience_id"], "OPEN_DEVELOPER_RESOURCE_SELF_STUDY_V1")
        self.assertEqual(result["latest_applied_experience_digest"], "619e576184ee84b0a28d2fc14d6fc465ae36e9039320c1625c64996397fe14c2")
        self.assertEqual(result["current_dns_preferred_provider"], "OpenDNS")
        self.assertTrue(result["current_dns_remeasure_before_reuse"])

    def test_tri_organ_contracts_have_single_owner(self):
        logic = self.kernel.route_contract("RELATION_START_TO_STATE")
        thinking = self.kernel.route_contract("EVENT_SEQUENCE_TO_BOOLEAN")
        self.assertEqual(logic["status"], "PRIMARY_TRI_ORGAN")
        self.assertEqual(thinking["status"], "PRIMARY_TRI_ORGAN")
        self.assertNotEqual(logic["component_id"], thinking["component_id"])

    def test_training_is_bound_to_memory_conditioning_without_promotion(self):
        snap = self.kernel.training_snapshot()
        self.assertEqual(snap["status"], "ACTIVE_DEVELOPMENT_SHADOW_TRAINED_AND_CYCLE_CONSOLIDATED")
        self.assertEqual(snap["experience_digest"], "619e576184ee84b0a28d2fc14d6fc465ae36e9039320c1625c64996397fe14c2")
        self.assertEqual(snap["causal_binding"]["source_layer"], "L1_MEMORY_EXPERIENCE")
        self.assertEqual(snap["causal_binding"]["conditioning_layer"], "L2_EXPERIENCE_CONDITIONING")
        self.assertFalse(snap["automatic_promotion"])

    def test_learning_cycle_retains_failure_and_repair_causally(self):
        snap = self.kernel.learning_cycle_snapshot()
        self.assertEqual(snap["status"], "PASS_SHADOW_LEARNING_CYCLE_V1")
        self.assertEqual(snap["stage_count"], 5)
        self.assertGreaterEqual(snap["causal_lesson_count"], 4)
        self.assertIn("LEGACY_EXPERIENCE_SUMMARY_PROVENANCE", snap["unresolved_deficits"])
        self.assertIn("CODING_UNSUPPORTED_PROGRAM_FAMILIES", snap["unresolved_deficits"])
        self.assertEqual(snap["latest_experience_digest"], "ef1e633fd19f530e465c2f497255d78443d5c51bcee0bb16b76a5da483a092bf")
        self.assertFalse(snap["automatic_promotion"])

    def test_dynamic_memory_applies_branch_inventory_without_semantic_overclaim(self):
        snap = self.kernel.dynamic_memory_snapshot()
        self.assertEqual(snap["status"], "PASS_SHADOW_G2_DYNAMIC_EXPERIENCE_MEMORY_V1")
        self.assertEqual(snap["remote_branch_count"], 20)
        self.assertEqual(snap["canonical_registry_branch_count"], 14)
        self.assertEqual(snap["raw_lineage_count"], 0)
        self.assertEqual(snap["dynamic_rederived_count"], 6)
        self.assertEqual(snap["next_required_capability"], None)
        self.assertTrue(snap["raw_branch_inventory_is_not_semantic_knowledge"])
        self.assertFalse(snap["automatic_promotion"])

    def test_dns_screenshot_result_is_applied_as_future_research_guard(self):
        snap = self.kernel.dns_screenshot_application_snapshot()
        self.assertEqual(snap["status"], "ACTIVE_DEVELOPMENT_SHADOW_APPLIED")
        self.assertEqual(snap["source_run_id"], 34115677305)
        self.assertIn("DNS-L1-SOURCE-001", snap["lesson_ids"])
        self.assertIn("DNS-L1-VARIANT-002", snap["lesson_ids"])
        self.assertIn("DNS-L1-PERF-005", snap["lesson_ids"])
        self.assertEqual(snap["future_task_guard"], "EXTERNAL_TECHNICAL_CLAIM_SOURCE_VARIANT_CONFIGURATION_AND_MEASUREMENT_GUARD")
        self.assertEqual(snap["retained_first_withhold"], "WITHHOLD_G2_DNS_SCREENSHOT_RESEARCH_STRESS_V2")
        self.assertFalse(snap["thresholds_lowered"])
        self.assertFalse(snap["automatic_promotion"])

    def test_direct_dns_probe_is_applied_as_contextual_execution_policy(self):
        snap = self.kernel.public_dns_direct_application_snapshot()
        self.assertEqual(snap["status"], "ACTIVE_DEVELOPMENT_SHADOW_APPLIED")
        self.assertEqual(snap["source_run_id"], 34118066517)
        self.assertEqual(snap["preferred_provider_for_current_runner"], "OpenDNS")
        self.assertEqual(snap["fallbacks"][0], "Quad9 Secure")
        self.assertTrue(snap["remeasure_before_reuse"])
        self.assertTrue(snap["do_not_apply_as_user_network_ranking"])
        self.assertEqual(snap["future_task_guard"], "LIVE_DNS_RESOLVER_SELECTION_REQUIRES_CONTEXTUAL_REPROBE_AND_FAILOVER")
        self.assertFalse(snap["automatic_promotion"])

    def test_gcp_direct_endpoint_probe_is_applied_as_live_endpoint_guard(self):
        snap = self.kernel.gcp_direct_endpoint_application_snapshot()
        self.assertEqual(snap["status"], "ACTIVE_DEVELOPMENT_SHADOW_APPLIED")
        self.assertEqual(snap["source_run_id"], 34120259476)
        self.assertEqual(snap["concrete_live_endpoint_count"], 15)
        self.assertEqual(snap["unresolved_symbolic_template"], "sqladmin.{region}.rep.googleapis.com")
        self.assertIn("GCP-DIRECT-002", snap["lesson_ids"])
        self.assertIn("GCP-DIRECT-003", snap["lesson_ids"])
        self.assertEqual(snap["future_task_guard"], "GCP_ENDPOINT_USE_REQUIRES_CONCRETE_HOST_LIVE_REPROBE_AND_SERVICE_PATH_CONTEXT")
        self.assertFalse(snap["automatic_promotion"])

    def test_open_developer_resource_self_study_is_applied_to_coding_priority(self):
        snap = self.kernel.open_developer_resource_application_snapshot()
        self.assertEqual(snap["status"], "ACTIVE_DEVELOPMENT_SHADOW_APPLIED")
        self.assertEqual(snap["source_run_id"], 34128129602)
        self.assertEqual(snap["target_priority"], "CODING_UNSUPPORTED_PROGRAM_FAMILIES")
        self.assertEqual(snap["source_count"], 141)
        self.assertEqual(snap["fetched_count"], 130)
        self.assertIn("DEV-RESOURCE-001", snap["lesson_ids"])
        self.assertIn("DEV-RESOURCE-004", snap["lesson_ids"])
        self.assertFalse(snap["automatic_promotion"])

    def test_unknown_contract_falls_back_without_self_promotion(self):
        route = self.kernel.route_contract("UNKNOWN_CONTRACT")
        self.assertEqual(route["status"], "FALLBACK_REQUIRED")
        trace = self.kernel.causal_trace("UNKNOWN_CONTRACT")
        self.assertFalse(trace["automatic_promotion"])
        self.assertEqual(trace["layers"][0], "L0_INPUT_GROUNDING")
        self.assertEqual(trace["layers"][-1], "L7_CONTINUITY_TIME")

if __name__ == "__main__":
    unittest.main()
