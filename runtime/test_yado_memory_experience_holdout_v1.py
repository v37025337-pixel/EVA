from __future__ import annotations

import unittest

from yado_memory_experience_holdout_v1 import Policy, build_split, load_corpus, retrieve, run


class MemoryExperienceHoldoutV1Tests(unittest.TestCase):
    def test_real_corpus_has_branch_and_external_memory(self):
        corpus, meta = load_corpus()
        self.assertGreaterEqual(meta["branch_record_count"], 8)
        self.assertGreaterEqual(meta["source_record_count"], 2)
        self.assertGreaterEqual(len(corpus), 10)

    def test_provenance_mismatch_is_rejected(self):
        row = {
            "record_id": "real",
            "kind": "BRANCH_MEMORY",
            "identity": "branch-a",
            "provenance": "abc",
            "payload": "memory",
        }
        query = {"identity": "branch-a", "kind": "BRANCH_MEMORY", "provenance": "wrong"}
        self.assertIsNone(retrieve(Policy(True, True, True), query, [row]))

    def test_ambiguous_record_without_provenance_is_rejected(self):
        rows = [
            {"record_id": "a", "kind": "BRANCH_MEMORY", "identity": "x", "provenance": "1", "payload": "p"},
            {"record_id": "b", "kind": "BRANCH_MEMORY", "identity": "x", "provenance": "2", "payload": "p"},
        ]
        query = {"identity": "x", "kind": "BRANCH_MEMORY", "provenance": None}
        self.assertIsNone(retrieve(Policy(True, True, True), query, rows))

    def test_fresh_split_is_distinct(self):
        corpus, _ = load_corpus()
        self.assertNotEqual(build_split(corpus, 2026091812), build_split(corpus, 2026091813))

    def test_selected_policy_beats_baseline_on_real_memory_holdout(self):
        receipt = run()
        self.assertEqual(receipt["status"], "PASS_SHADOW_MEMORY_EXPERIENCE_HOLDOUT_V1")
        self.assertGreater(
            receipt["selected_scores"]["fresh"]["accuracy"],
            receipt["baseline_scores"]["fresh"]["accuracy"],
        )
        self.assertGreaterEqual(receipt["selected_scores"]["fresh"]["accuracy"], 0.95)
        self.assertTrue(receipt["selected_policy"]["require_provenance"])
        self.assertTrue(receipt["selected_policy"]["exact_kind"])
        self.assertTrue(receipt["selected_policy"]["reject_ambiguous"])
        self.assertFalse(receipt["canonical_mutation"])


if __name__ == "__main__":
    unittest.main()
