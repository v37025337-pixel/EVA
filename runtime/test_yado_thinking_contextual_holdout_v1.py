from __future__ import annotations

import unittest

from yado_g2_contextual_stream_capability_adapter_v1 import (
    CAP_BUD,
    CAP_REL,
    ContextualStreamCapabilityAdapterV1,
)
from yado_thinking_contextual_holdout_v1 import (
    build_split,
    run,
    run_scenario,
)


class ThinkingContextualHoldoutV1Tests(unittest.TestCase):
    def test_real_adapter_limits_are_bounded(self):
        self.assertEqual(ContextualStreamCapabilityAdapterV1.MAX_LOOKBACK, 128)
        self.assertEqual(ContextualStreamCapabilityAdapterV1.MAX_STREAM_CONTEXTS, 1024)

    def test_stream_map_survives_long_gap(self):
        scenarios = [x for x in build_split(2026091821, 2) if x["family"] == "long_gap"]
        self.assertTrue(scenarios)
        self.assertTrue(all(run_scenario("BOUNDED_STREAM_CONTEXT_MAP", x) for x in scenarios))
        self.assertTrue(any(not run_scenario("LAST_STREAM_CAPABILITY", x) for x in scenarios))

    def test_cross_stream_isolation(self):
        scenarios = [x for x in build_split(2026091822, 2) if x["family"] == "cross_stream_isolation"]
        self.assertTrue(all(run_scenario("BOUNDED_STREAM_CONTEXT_MAP", x) for x in scenarios))
        self.assertTrue(any(not run_scenario("GLOBAL_LAST_CAPABILITY", x) for x in scenarios))

    def test_fresh_split_is_distinct(self):
        self.assertNotEqual(build_split(2026091822, 2), build_split(2026091823, 2))

    def test_selected_context_strategy_beats_baseline(self):
        receipt = run()
        self.assertEqual(receipt["status"], "PASS_SHADOW_THINKING_CONTEXTUAL_HOLDOUT_V1")
        self.assertEqual(receipt["selected_strategy"], "BOUNDED_STREAM_CONTEXT_MAP")
        self.assertGreater(
            receipt["selected_scores"]["fresh"]["accuracy"],
            receipt["baseline_scores"]["fresh"]["accuracy"],
        )
        self.assertGreaterEqual(receipt["selected_scores"]["fresh"]["accuracy"], 0.95)
        self.assertTrue(all(v >= 0.90 for v in receipt["selected_scores"]["fresh"]["by_family"].values()))
        self.assertTrue(receipt["real_yado_context_adapter_used"])
        self.assertFalse(receipt["canonical_mutation"])


if __name__ == "__main__":
    unittest.main()
