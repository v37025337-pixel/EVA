from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

from yado_runtime_self_rewrite_admission_v3 import (
    CANDIDATE,
    ROOT,
    TARGET,
    analyze_committed,
)
from yado_runtime_self_rewrite_admission_v4 import analyze as analyze_v4

V4_CANDIDATE = Path("candidates/autonomous/yado_bounded_autonomous_learning_runtime_candidate_v4.py")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generation_state(result: dict) -> str:
    target_sha = str(result["target_sha256"])
    v3_sha = sha(ROOT / CANDIDATE)
    v4_sha = sha(ROOT / V4_CANDIDATE)
    if target_sha == v3_sha:
        return "V3"
    if target_sha == v4_sha:
        return "V4"
    raise AssertionError("UNRECOGNIZED_RUNTIME_GENERATION:" + target_sha)


class RuntimeSelfRewriteAdmissionV3Tests(unittest.TestCase):
    def test_runtime_is_v3_or_exact_verified_v4_successor(self):
        result = analyze_committed()
        state = generation_state(result)
        self.assertTrue(result["checks"]["candidate_sha_matches_receipt"])
        self.assertTrue(result["checks"]["target_differs_from_recorded_parent"])
        if state == "V3":
            self.assertEqual(result["admission_mode"], "ALREADY_PHYSICALLY_PRESENT_IDENTICAL_BYTES")
            self.assertTrue(result["checks"]["target_sha_matches_candidate"])
            self.assertTrue(result["checks"]["candidate_target_ast_identical"])
            self.assertEqual(result["status"], "PASS_SHADOW_RUNTIME_SELF_REWRITE_ADMISSION_V3")
        else:
            self.assertFalse(result["checks"]["target_sha_matches_candidate"])
            self.assertEqual(result["status"], "WITHHOLD_RUNTIME_SELF_REWRITE_ADMISSION_V3")
            successor = analyze_v4()
            self.assertEqual(successor["status"], "PASS_SHADOW_RUNTIME_SELF_REWRITE_ADMISSION_V4_PROBE")
            self.assertEqual(successor["runtime_state"], "V4_CANDIDATE_APPLIED_IN_ISOLATED_WORKTREE")
            self.assertTrue(successor["checks"]["target_matches_candidate_when_shadow_applied"])

    def test_experience_binding_tracks_active_generation(self):
        result = analyze_committed()
        state = generation_state(result)
        if state == "V3":
            self.assertTrue(result["checks"]["runtime_learned_binding_exact"])
            self.assertTrue(result["checks"]["successful_source_affinity_observed"])
            self.assertTrue(result["checks"]["successful_host_affinity_observed"])
        else:
            self.assertFalse(result["checks"]["runtime_learned_binding_exact"])
            successor = analyze_v4()
            self.assertTrue(successor["checks"]["candidate_binding_matches_v4_receipt"])
            self.assertTrue(successor["checks"]["candidate_binds_latest_experience"])
            self.assertTrue(successor["checks"]["candidate_ranking_matches_v4_receipt"])

    def test_gate_does_not_rewrite_runtime(self):
        target = ROOT / TARGET
        candidate = ROOT / CANDIDATE
        before_target = sha(target)
        before_candidate = sha(candidate)
        result = analyze_committed()
        state = generation_state(result)
        expected = (
            "PASS_SHADOW_RUNTIME_SELF_REWRITE_ADMISSION_V3"
            if state == "V3"
            else "WITHHOLD_RUNTIME_SELF_REWRITE_ADMISSION_V3"
        )
        self.assertEqual(result["status"], expected)
        self.assertEqual(sha(target), before_target)
        self.assertEqual(sha(candidate), before_candidate)
        self.assertFalse(result["checks"]["runtime_rewrite_performed_by_gate"])
        self.assertFalse(result["checks"]["automatic_main_mutation"])
        self.assertEqual(result["repository_view"], "COMMITTED_HEAD")

    def test_frontier_is_next_generation_or_verified_v4_successor(self):
        result = analyze_committed()
        state = generation_state(result)
        if state == "V3":
            self.assertEqual(
                result["next_required_capability"],
                "NEXT_GENERATION_NATIVE_SELF_REWRITE_FROM_FRESH_EXPERIENCE_V1",
            )
        else:
            self.assertEqual(result["next_required_capability"], "REPAIR_RUNTIME_SELF_REWRITE_ADMISSION_V3")
            successor = analyze_v4()
            self.assertEqual(
                successor["next_required_capability"],
                "PHYSICAL_RUNTIME_PROMOTION_V4_REQUIRES_SEPARATE_GATE",
            )


if __name__ == "__main__":
    unittest.main()
