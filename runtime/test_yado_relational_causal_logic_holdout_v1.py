from __future__ import annotations

import unittest

from yado_relational_causal_logic_holdout_v1 import Policy, build_split, infer, run, score


class RelationalCausalLogicHoldoutV1Tests(unittest.TestCase):
    def test_causal_chain_reaches_across_multiple_hops(self):
        task = {
            "edges": [("a", "b", "CAUSE"), ("b", "c", "CAUSE"), ("a", "c", "ASSOCIATION")],
            "query": ("a", "c"),
            "expected": True,
            "kind": "causal_chain",
        }
        self.assertTrue(infer(Policy(3, True, True), task))

    def test_association_does_not_become_cause(self):
        task = {
            "edges": [("a", "b", "ASSOCIATION"), ("b", "c", "ASSOCIATION")],
            "query": ("a", "c"),
            "expected": False,
            "kind": "association_not_cause",
        }
        self.assertFalse(infer(Policy(4, True, True), task))

    def test_feedback_cycle_is_rejected(self):
        task = {
            "edges": [("a", "b", "CAUSE"), ("b", "c", "CAUSE"), ("c", "a", "CAUSE")],
            "query": ("a", "c"),
            "expected": False,
            "kind": "feedback_contradiction",
        }
        self.assertFalse(infer(Policy(4, True, True), task))

    def test_fresh_split_is_distinct(self):
        hidden = build_split(2026091802)
        fresh = build_split(2026091803)
        self.assertNotEqual(hidden, fresh)

    def test_selected_policy_beats_baseline_on_fresh(self):
        receipt = run()
        self.assertEqual(receipt["status"], "PASS_SHADOW_RELATIONAL_CAUSAL_LOGIC_HOLDOUT_V1")
        self.assertGreater(
            receipt["selected_scores"]["fresh"]["accuracy"],
            receipt["baseline_scores"]["fresh"]["accuracy"],
        )
        self.assertGreaterEqual(receipt["selected_scores"]["fresh"]["accuracy"], 0.95)
        self.assertTrue(all(v >= 0.90 for v in receipt["selected_scores"]["fresh"]["by_kind"].values()))
        self.assertFalse(receipt["canonical_mutation"])
        self.assertFalse(receipt["automatic_main_mutation"])


if __name__ == "__main__":
    unittest.main()
