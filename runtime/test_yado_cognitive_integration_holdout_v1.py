from __future__ import annotations

import unittest

from yado_cognitive_integration_holdout_v1 import (
    GATES,
    VERIFIED_PARENT_POLICIES,
    build_g3,
    build_split,
    load_corpus,
    run,
)


class CognitiveIntegrationHoldoutV1Tests(unittest.TestCase):
    def test_verified_parent_policies_are_loaded(self):
        self.assertEqual(VERIFIED_PARENT_POLICIES["thinking"], "BOUNDED_STREAM_CONTEXT_MAP")
        self.assertEqual(VERIFIED_PARENT_POLICIES["intelligence"], "G4_TRANSFER_AMBIGUITY_GUARD")
        self.assertEqual(set(GATES), {"MEMORY_EXPERIENCE", "LOGIC", "THINKING", "INTELLIGENCE"})

    def test_all_pass_family_activates_all_four_real_signals(self):
        corpus, _ = load_corpus()
        _, trained = build_g3()
        rows = [
            row for row in build_split(corpus, trained, 2026091841, 2)
            if row["family"] == "all_pass"
        ]
        self.assertTrue(rows)
        self.assertTrue(all(all(row["signals"].values()) for row in rows))

    def test_each_single_failure_family_is_isolated(self):
        corpus, _ = load_corpus()
        _, trained = build_g3()
        rows = build_split(corpus, trained, 2026091842, 2)
        mapping = {
            "memory_fail": "MEMORY_EXPERIENCE",
            "logic_fail": "LOGIC",
            "thinking_fail": "THINKING",
            "intelligence_fail": "INTELLIGENCE",
        }
        for family, gate in mapping.items():
            family_rows = [row for row in rows if row["family"] == family]
            self.assertTrue(family_rows)
            for row in family_rows:
                self.assertFalse(row["signals"][gate])
                self.assertTrue(all(value for name, value in row["signals"].items() if name != gate))

    def test_fresh_split_is_distinct(self):
        corpus, _ = load_corpus()
        _, trained = build_g3()
        self.assertNotEqual(
            build_split(corpus, trained, 2026091842, 2),
            build_split(corpus, trained, 2026091843, 2),
        )

    def test_all_four_integration_beats_partial_baseline_and_each_ablation(self):
        receipt = run()
        self.assertEqual(receipt["status"], "PASS_SHADOW_COGNITIVE_INTEGRATION_HOLDOUT_V1")
        self.assertEqual(receipt["selected_policy"], "ALL_FOUR")
        self.assertGreaterEqual(receipt["selected_scores"]["fresh"]["accuracy"], 0.95)
        self.assertGreater(
            receipt["selected_scores"]["fresh"]["accuracy"],
            receipt["baseline_scores"]["fresh"]["accuracy"],
        )
        self.assertTrue(all(v >= 0.90 for v in receipt["selected_scores"]["fresh"]["by_family"].values()))
        self.assertTrue(all(drop >= 0.15 for drop in receipt["fresh_ablation_drops"].values()))
        self.assertFalse(receipt["canonical_mutation"])


if __name__ == "__main__":
    unittest.main()
