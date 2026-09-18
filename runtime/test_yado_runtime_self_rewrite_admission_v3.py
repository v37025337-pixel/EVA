from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

from yado_runtime_self_rewrite_admission_v3 import (
    CANDIDATE,
    ROOT,
    TARGET,
    analyze,
    run,
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RuntimeSelfRewriteAdmissionV3Tests(unittest.TestCase):
    def test_current_runtime_is_exact_v3_candidate(self):
        result = analyze()
        self.assertEqual(result["admission_mode"], "ALREADY_PHYSICALLY_PRESENT_IDENTICAL_BYTES")
        self.assertTrue(result["checks"]["candidate_sha_matches_receipt"])
        self.assertTrue(result["checks"]["target_sha_matches_candidate"])
        self.assertTrue(result["checks"]["target_differs_from_recorded_parent"])
        self.assertTrue(result["checks"]["candidate_target_ast_identical"])

    def test_experience_binding_has_observable_ranking_effect(self):
        result = analyze()
        self.assertTrue(result["checks"]["runtime_learned_binding_exact"])
        self.assertTrue(result["checks"]["successful_source_affinity_observed"])
        self.assertTrue(result["checks"]["successful_host_affinity_observed"])

    def test_gate_does_not_rewrite_runtime(self):
        target = ROOT / TARGET
        candidate = ROOT / CANDIDATE
        before_target = sha(target)
        before_candidate = sha(candidate)
        result = run()
        self.assertEqual(result["status"], "PASS_SHADOW_RUNTIME_SELF_REWRITE_ADMISSION_V3")
        self.assertEqual(sha(target), before_target)
        self.assertEqual(sha(candidate), before_candidate)
        self.assertFalse(result["checks"]["runtime_rewrite_performed_by_gate"])
        self.assertFalse(result["checks"]["automatic_main_mutation"])

    def test_next_frontier_is_new_generation_self_rewrite(self):
        result = analyze()
        self.assertEqual(
            result["next_required_capability"],
            "NEXT_GENERATION_NATIVE_SELF_REWRITE_FROM_FRESH_EXPERIENCE_V1",
        )


if __name__ == "__main__":
    unittest.main()
