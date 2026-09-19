import tempfile
import unittest
from pathlib import Path

from test_yado_external_dev_capability_pack_v1 import fake_fetch
from yado_external_dev_self_development_v1 import ExternalDevSelfDevelopmentV1, FRESH_CASES
from yado_unified_core_external_dev_self_development_v1 import UnifiedYADOCoreExternalDevSelfDevelopmentV1


class ExternalDevSelfDevelopmentTests(unittest.TestCase):
    def router_source(self):
        core = UnifiedYADOCoreExternalDevSelfDevelopmentV1()
        refresh = core.refresh_external_dev_capabilities(fetch_override=fake_fetch)
        return ExternalDevSelfDevelopmentV1.render_router_source(
            ExternalDevSelfDevelopmentV1.derive_router_policy(refresh))

    def test_router_rejects_top_level_execution_before_side_effect(self):
        source = self.router_source()
        with tempfile.TemporaryDirectory() as td:
            sentinel = Path(td) / 'executed'
            injected = source + f"\n__import__('pathlib').Path({str(sentinel)!r}).write_text('bad')\n"
            with self.assertRaisesRegex(ValueError, 'ROUTER_SOURCE_INVALID'):
                ExternalDevSelfDevelopmentV1.load_router(injected)
            self.assertFalse(sentinel.exists())

    def test_router_rejects_replaced_function_even_with_original_digests(self):
        source = self.router_source().replace('    tokens = _tokens(deficit)', '    while True: pass')
        with self.assertRaisesRegex(ValueError, 'ROUTER_TEMPLATE_MISMATCH'):
            ExternalDevSelfDevelopmentV1.load_router(source)

    def test_router_rejects_expressions_in_literal_slots(self):
        source = self.router_source()
        source = 'PACK_DIGEST = str(123)\n' + source.split('\n', 1)[1]
        with self.assertRaisesRegex(ValueError, 'ROUTER_SOURCE_INVALID'):
            ExternalDevSelfDevelopmentV1.load_router(source)

    def test_router_rejects_unbounded_and_unknown_policy_data(self):
        source = self.router_source()
        with self.assertRaisesRegex(ValueError, 'ROUTER_SOURCE_BUDGET'):
            ExternalDevSelfDevelopmentV1.load_router(source + ' ' * 65536)
        source = source.replace('TASK_CONTRACT_AND_AGENT_SUPERVISION_PATTERN', 'UNADMITTED_CAPABILITY')
        with self.assertRaisesRegex(ValueError, 'ROUTER_POLICY_SHAPE'):
            ExternalDevSelfDevelopmentV1.load_router(source)

    def test_router_is_derived_and_beats_fixed_baseline(self):
        core = UnifiedYADOCoreExternalDevSelfDevelopmentV1()
        with tempfile.TemporaryDirectory() as td:
            candidate = Path(td) / "router.py"
            receipt = Path(td) / "receipt.json"
            out = core.external_dev_self_develop(
                "Improve YADO external development capability selection",
                candidate_path=candidate,
                receipt_path=receipt,
                fetch_override=fake_fetch,
            )
            self.assertEqual(out["status"], "PASS_SHADOW_EXTERNAL_DEV_SELF_DEVELOPMENT_V1")
            self.assertTrue(candidate.exists())
            self.assertTrue(receipt.exists())
            self.assertEqual(out["fresh_evaluation"]["tests_run"], len(FRESH_CASES))
            self.assertEqual(out["fresh_evaluation"]["accuracy"], 1.0)
            self.assertGreater(out["fresh_evaluation"]["gain"], 0.0)
            self.assertTrue(out["fresh_evaluation"]["unknown_withhold"])
            self.assertEqual(len(out["development_generations"]), 5)
            self.assertEqual(len(set(out["used_source_patterns"])), 5)
            self.assertFalse(out["automatic_main_mutation"])

    def test_generated_router_routes_each_fresh_deficit_and_withholds_unknown(self):
        core = UnifiedYADOCoreExternalDevSelfDevelopmentV1()
        refresh = core.refresh_external_dev_capabilities(fetch_override=fake_fetch)
        controller = ExternalDevSelfDevelopmentV1()
        policy = controller.derive_router_policy(refresh)
        source = controller.render_router_source(policy)
        route, snapshot = controller.load_router(source)
        self.assertEqual(snapshot()["capability_count"], 5)
        for deficit, expected in FRESH_CASES:
            self.assertEqual(route(deficit)["capability"], expected)
        self.assertEqual(route("unclassified novel semantic dimension")["status"], "WITHHOLD_ROUTER_NO_MATCH")

    def test_core_audit_preserves_g2_and_shadow_boundary(self):
        core = UnifiedYADOCoreExternalDevSelfDevelopmentV1()
        audit = core.audit()
        self.assertTrue(audit["pass"], audit)
        snap = core.snapshot()
        self.assertEqual(snap["generation"], "G2_CANDIDATE_TRCG_V1")
        self.assertFalse(snap["external_dev_self_development"]["automatic_main_mutation"])
        self.assertFalse(snap["external_dev_self_development"]["g3_genesis_performed"])


if __name__ == "__main__":
    unittest.main()
