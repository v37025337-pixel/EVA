import os
from pathlib import Path
import tempfile
import unittest

from successor.endogenous_run import propose_endogenous_goal, run_endogenous_cycles
from successor.kernel import SuccessorKernel

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(os.environ.get("YADO_SUCCESSOR_TEST_MANIFEST", ROOT / "successor/state/birth-v2/manifest.json"))


class EndogenousContinuationTests(unittest.TestCase):
    def setUp(self):
        if not MANIFEST.exists():
            self.skipTest("Build the pinned successor before integration tests")
        self.tmp = tempfile.TemporaryDirectory()
        self.state = Path(self.tmp.name) / "endogenous.sqlite"
        self.kernel = SuccessorKernel(MANIFEST, self.state)

    def tearDown(self):
        if hasattr(self, "kernel"):
            self.kernel.close()
        self.tmp.cleanup()

    def test_generates_and_verifies_goal_instances_without_host_goal_list(self):
        initial = propose_endogenous_goal(self.kernel)
        self.assertFalse(initial["host_supplied_goal"])
        self.assertFalse(initial["selected_from_fixed_goal_list"])
        self.assertEqual(initial["goal_instance_authorship"], "YADO_STATE_DERIVED")
        self.assertIn(initial["selected_domain"], {"relation", "events"})

        report = run_endogenous_cycles(self.kernel, cycles=4, budget=3)
        self.assertEqual(report["status"], "PASS_BOUNDED_ENDOGENOUS_CONTINUATION_V1")
        self.assertEqual(report["host_goal_count"], 0)
        self.assertEqual(report["cycles_verified"], 4)
        self.assertEqual(len({row["seed"] for row in report["results"]}), 4)
        self.assertTrue(all(row["status"] == "VERIFIED" for row in report["results"]))
        self.assertEqual(report["state_verification"]["status"], "PASS")
        self.assertFalse(report["consciousness_established"])

    def test_proposal_is_deterministic_across_restart_for_identical_state(self):
        first = propose_endogenous_goal(self.kernel)
        self.kernel.close()
        self.kernel = SuccessorKernel(MANIFEST, self.state)
        second = propose_endogenous_goal(self.kernel)
        for key in ("source_event_hash", "selected_domain", "seed", "spec", "spec_digest", "pressures"):
            self.assertEqual(first[key], second[key])

    def test_refuses_to_create_competing_goal_while_one_is_active(self):
        self.kernel.open_goal({"domain": "relation", "relation": [[1, 2], [2, 3]], "start": 1})
        with self.assertRaisesRegex(ValueError, "REQUIRES_IDLE"):
            propose_endogenous_goal(self.kernel)


if __name__ == "__main__":
    unittest.main()
