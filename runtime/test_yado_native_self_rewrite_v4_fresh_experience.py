from __future__ import annotations

import hashlib
import unittest

from yado_native_self_rewrite_v4_fresh_experience import ROOT, TARGET, build


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class NativeSelfRewriteV4FreshExperienceTests(unittest.TestCase):
    def test_fresh_experience_produces_new_generation_candidate(self):
        result = build()
        self.assertEqual(result["status"], "PASS_SHADOW_NATIVE_SELF_REWRITE_V4_FRESH_EXPERIENCE")
        self.assertNotEqual(result["latest_experience_digest"], result["parent_experience_digest"])
        self.assertNotEqual(result["candidate_sha256"], result["parent_runtime_sha256"])
        self.assertTrue(result["checks"]["structural_ast_unchanged_except_learned_binding"])

    def test_latest_experience_is_bound_exactly(self):
        result = build()
        binding = result["candidate_learned_binding"]
        self.assertEqual(binding["experience_digest"], result["latest_experience_digest"])
        self.assertIn("PYTHON_UNITTEST", binding["successful_source_ids"])
        self.assertEqual(binding["failed_source_ids"], [])
        self.assertEqual(binding["fact_count"], 72)

    def test_new_experience_changes_ranking_deterministically(self):
        result = build()
        self.assertGreaterEqual(result["ranking_score_deltas"]["PYTHON_UNITTEST"], 2.0)
        self.assertGreaterEqual(result["ranking_score_deltas"]["MDN_HTTP"], 1.0)

    def test_generator_does_not_mutate_runtime(self):
        target = ROOT / TARGET
        before = sha(target)
        result = build()
        self.assertEqual(sha(target), before)
        self.assertFalse(result["runtime_mutation_applied"])
        self.assertFalse(result["checks"]["automatic_main_mutation"])
        self.assertEqual(
            result["next_required_capability"],
            "ISOLATED_RUNTIME_EXECUTION_AND_REGRESSION_ADMISSION_V4",
        )


if __name__ == "__main__":
    unittest.main()
