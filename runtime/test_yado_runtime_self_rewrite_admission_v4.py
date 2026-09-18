from __future__ import annotations
import hashlib
import unittest
from yado_runtime_self_rewrite_admission_v4 import ROOT,TARGET,analyze,run

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

class RuntimeSelfRewriteAdmissionV4Tests(unittest.TestCase):
    def test_probe_accepts_outer_or_isolated_state(self):
        d=analyze()
        self.assertEqual(d["status"],"PASS_SHADOW_RUNTIME_SELF_REWRITE_ADMISSION_V4_PROBE")
        self.assertIn(d["runtime_state"],{"PARENT_RUNTIME_PENDING_SHADOW_APPLY","V4_CANDIDATE_APPLIED_IN_ISOLATED_WORKTREE"})
        self.assertTrue(d["checks"]["candidate_sha_matches_v4_receipt"])
        self.assertTrue(d["checks"]["candidate_ranking_matches_v4_receipt"])

    def test_probe_does_not_mutate_target(self):
        target=ROOT/TARGET
        before=sha(target)
        d=run()
        self.assertEqual(sha(target),before)
        self.assertFalse(d["checks"]["probe_mutated_runtime"])

    def test_shadow_applied_state_requires_exact_binding(self):
        d=analyze()
        if d["runtime_state"]=="V4_CANDIDATE_APPLIED_IN_ISOLATED_WORKTREE":
            self.assertTrue(d["checks"]["target_matches_candidate_when_shadow_applied"])
            self.assertEqual(d["next_required_capability"],"PHYSICAL_RUNTIME_PROMOTION_V4_REQUIRES_SEPARATE_GATE")

if __name__=="__main__":
    unittest.main()
