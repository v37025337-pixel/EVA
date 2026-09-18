from __future__ import annotations

import unittest

from yado_external_project_training_v1 import STATUS_PASS, STATUS_WITHHOLD
from yado_external_project_transfer_v3 import STATUS_AMBIGUOUS
from yado_intelligence_transfer_holdout_v1 import (
    build_g3,
    build_split,
    execute,
    run,
)


class IntelligenceTransferHoldoutV1Tests(unittest.TestCase):
    def test_parent_three_generation_training_is_real_and_passed(self):
        parent, trained = build_g3()
        self.assertEqual(parent["status"], "PASS_SHADOW_THREE_STATE_DERIVED_GENERATIONS_V2")
        self.assertTrue(trained["profiles"]["LOGIC"])
        self.assertTrue(trained["profiles"]["THINKING"])
        self.assertTrue(trained["profiles"]["INTELLIGENCE"])

    def test_guard_rejects_fresh_ambiguous_pair(self):
        _, trained = build_g3()
        tasks = [
            task for task in build_split(trained, 2026091832, 2)
            if task.family.startswith("ambiguous_")
        ]
        self.assertTrue(tasks)
        task = tasks[0]
        base = execute("BASE_ROUTE", task, trained)
        guarded = execute("G4_TRANSFER_AMBIGUITY_GUARD", task, trained)
        self.assertEqual(base["status"], STATUS_PASS)
        self.assertEqual(guarded["status"], STATUS_AMBIGUOUS)
        self.assertIsNone(guarded.get("capability"))

    def test_unknown_domain_withholds(self):
        _, trained = build_g3()
        task = next(
            task for task in build_split(trained, 2026091833, 2)
            if task.family == "unknown_domain"
        )
        guarded = execute("G4_TRANSFER_AMBIGUITY_GUARD", task, trained)
        self.assertEqual(guarded["status"], STATUS_WITHHOLD)
        self.assertIsNone(guarded.get("capability"))

    def test_fresh_split_is_distinct(self):
        _, trained = build_g3()
        self.assertNotEqual(
            build_split(trained, 2026091832, 2),
            build_split(trained, 2026091833, 2),
        )

    def test_selected_transfer_guard_beats_baseline(self):
        receipt = run()
        self.assertEqual(receipt["status"], "PASS_SHADOW_INTELLIGENCE_TRANSFER_HOLDOUT_V1")
        self.assertEqual(receipt["selected_strategy"], "G4_TRANSFER_AMBIGUITY_GUARD")
        self.assertGreaterEqual(receipt["selected_scores"]["fresh"]["accuracy"], 0.95)
        self.assertGreaterEqual(receipt["fresh_absolute_gain"], 0.20)
        self.assertTrue(all(v >= 0.90 for v in receipt["selected_scores"]["fresh"]["by_family"].values()))
        self.assertTrue(receipt["real_yado_transfer_router_used"])
        self.assertFalse(receipt["canonical_mutation"])


if __name__ == "__main__":
    unittest.main()
