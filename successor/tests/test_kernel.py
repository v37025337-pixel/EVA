from fractions import Fraction
import json
import os
from pathlib import Path
import random
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from successor.kernel import SuccessorKernel, encode, decode, fingerprint
from successor.archive import canonical, sha

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(os.environ.get("YADO_SUCCESSOR_TEST_MANIFEST", ROOT / "successor/state/birth-v2/manifest.json"))


class SuccessorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not MANIFEST.exists():
            raise unittest.SkipTest("Build the actual YADO archive before integration tests")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = Path(self.tmp.name) / "memory.sqlite"
        self.kernel = SuccessorKernel(MANIFEST, self.state)

    def tearDown(self):
        self.kernel.close()
        self.tmp.cleanup()

    def test_fresh_relations_match_independent_reachability(self):
        rng = random.Random(20260909)
        for case in range(30):
            n = rng.randint(4, 14)
            edges = [(a, b) for a in range(n) for b in range(n) if rng.random() < .12]
            start = rng.randrange(n)
            reachable, pending = {start}, [start]
            while pending:
                current = pending.pop(0)
                for a, b in edges:
                    if a == current and b not in reachable:
                        reachable.add(b)
                        pending.append(b)
            task = {"kind": "logic", "payload": {"relation": edges, "start": start},
                    "expect": {"path": ["result"], "equals": sorted(reachable, key=str)}}
            event = self.kernel.execute(task)
            self.assertEqual(event["status"], "VERIFIED", (case, event.get("error")))
            self.assertEqual(set(event["result"]["result"]), reachable)

    def test_false_logical_answer_can_be_a_verified_correct_result(self):
        event = self.kernel.execute({"kind": "thinking", "payload": {"events": [["R", "unopened"]]},
                                     "expect": {"path": ["result"], "equals": False}})
        self.assertEqual(event["status"], "VERIFIED")
        self.assertIs(event["result"]["result"], False)

    def test_failure_changes_next_attempt_and_survives_restart(self):
        task = {"kind": "logic", "payload": {"relation": [[1, 2]], "start": 1},
                "expect": {"path": ["result"], "equals": [1]}}
        first = self.kernel.execute(task)
        self.assertEqual(first["status"], "FAIL")
        self.kernel.close()
        self.kernel = SuccessorKernel(MANIFEST, self.state)
        repeat = self.kernel.execute(dict(reversed(list(task.items()))))
        self.assertEqual(repeat["reason"], "UNCHANGED_FAILED_ATTEMPT")
        self.assertFalse(repeat["execution_attempted"])
        task["expect"]["equals"] = [1, 2]
        self.assertEqual(self.kernel.execute(task)["status"], "VERIFIED")
        self.assertEqual(self.kernel.verify_state()["tick"], 3)

    def test_execution_without_oracle_does_not_claim_verification(self):
        event = self.kernel.execute({"kind": "logic", "payload": {"relation": [], "start": "a"}})
        self.assertEqual(event["status"], "EXECUTED_UNVERIFIED")
        self.assertEqual(event["next_action"], "SEEK_EVIDENCE")

    def test_unknown_task_is_recorded_without_execution_claim(self):
        event = self.kernel.execute({"kind": "unimplemented_task"})
        self.assertEqual(event["status"], "WITHHOLD")
        self.assertEqual(event["result"]["status"], "WITHHOLD_UNSUPPORTED_TASK")

    def test_native_runtime_error_is_retained(self):
        event = self.kernel.execute({"kind": "logic", "payload": {"relation": [[1, 2, 3]], "start": 1}})
        self.assertEqual(event["status"], "ERROR")
        self.assertIn("RELATION_EDGE_ARITY", event["error"])
        self.assertEqual(self.kernel.recent(1)[0]["error"], event["error"])

    def test_queue_resumes_in_a_separate_process(self):
        task = {"kind": "thinking", "payload": {"events": [["Q", "a"], ["R", "a"]]},
                "expect": {"path": ["result"], "equals": True}}
        self.kernel.submit("persist two tasks", [task, task])
        self.assertEqual(len(self.kernel.resume(1)), 1)
        result = subprocess.run([sys.executable, "-m", "successor", "resume", "--manifest", str(MANIFEST),
                                 "--state", str(self.state), "--max-steps", "10"], cwd=ROOT,
                                capture_output=True, text=True, timeout=45, check=True)
        events = json.loads(result.stdout)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["status"], "VERIFIED")
        self.assertEqual(self.kernel.snapshot()["jobs"], {"VERIFIED": 2})

    def test_history_tampering_fails_on_restart(self):
        self.kernel.execute({"kind": "audit"})
        with sqlite3.connect(self.state) as db:
            db.execute("UPDATE events SET body='{}' WHERE tick=1")
        with self.assertRaisesRegex(ValueError, "CAUSAL_HISTORY_INTEGRITY_FAILURE"):
            SuccessorKernel(MANIFEST, self.state)

    def test_pending_task_tampering_is_detected(self):
        self.kernel.submit("test", [{"kind": "audit"}])
        with sqlite3.connect(self.state) as db:
            db.execute("UPDATE jobs SET task=?", (encode({"kind": "logic"}),))
        with self.assertRaisesRegex(ValueError, "GOAL_TASK_CONTENT_INTEGRITY_FAILURE"):
            self.kernel.verify_state()

    def test_archive_content_is_used_as_attributed_native_advice(self):
        event = self.kernel.execute({"kind": "audit", "history_query": "PASS_SHADOW receipt"})
        self.assertTrue(event["historical_sources"])
        self.assertTrue(event["historical_meta_advice"])
        digests = {x["digest"] for x in event["historical_sources"]}
        self.assertTrue(all(x["source_digest"] in digests for x in event["historical_meta_advice"]))
        self.assertEqual(event["status"], "EXECUTED_UNVERIFIED")

    def test_typed_memory_preserves_model_keys_tuples_and_fractions(self):
        original = {2: (Fraction(5, 6), True), "list": [1, None]}
        self.assertEqual(decode(encode(original)), original)
        self.assertIsInstance(decode(encode(original))[2], tuple)
        self.assertEqual(fingerprint(original), fingerprint(dict(reversed(list(original.items())))))

    def test_wrong_boolean_oracle_does_not_equal_numeric_one(self):
        event = self.kernel.execute({"kind": "thinking", "payload": {"events": []},
                                     "expect": {"path": ["result"], "equals": 1}})
        self.assertEqual(event["status"], "FAIL")

    def test_native_bounded_repair_compiles_and_passes_unseen_inputs(self):
        event = self.kernel.execute({"kind": "repair", "payload": {
            "source": "def f(x):\n    return x + 1\n", "function_name": "f",
            "train_examples": [[[0], 2], [[1], 3], [[2], 4], [[3], 5]], "max_candidates": 1000}})
        self.assertEqual(event["status"], "EXECUTED_UNVERIFIED")
        source = event["result"]["source"]
        compile(source, "native-repair-candidate", "exec")
        for value in (-91, 17, 103):
            self.assertEqual(self.kernel.parent.execute_program_task(source, "f", (value,)), value + 2)

    def test_interrupted_task_rolls_back_queue_claim_and_event(self):
        task = {"kind": "audit"}
        self.kernel.submit("interruption", [task])
        original = self.kernel._dispatch
        def interrupt(_):
            raise KeyboardInterrupt()
        self.kernel._dispatch = interrupt
        with self.assertRaises(KeyboardInterrupt):
            self.kernel.resume(1)
        self.kernel._dispatch = original
        self.assertEqual(self.kernel.snapshot()["jobs"], {"PENDING": 1})
        self.assertEqual(self.kernel.verify_state()["tick"], 1)
        self.assertEqual(len(self.kernel.resume(1)), 1)

    def test_changed_parent_source_is_rejected_before_native_import(self):
        manifest = json.loads(MANIFEST.read_text())
        manifest["inherited_files"]["runtime/yado_unified_core_v1.py"] = "0" * 64
        manifest.pop("identity_digest")
        manifest["identity_digest"] = sha(canonical(manifest).encode())
        forged = Path(self.tmp.name) / "manifest.json"
        forged.write_text(json.dumps(manifest))
        code = """import sys
from successor.kernel import SuccessorKernel
assert 'yado_unified_core_v1' not in sys.modules
try:
    SuccessorKernel(sys.argv[1], sys.argv[2])
except ValueError as error:
    assert 'INHERITED_SOURCE_DRIFT' in str(error)
else:
    raise AssertionError('modified source was accepted')
assert 'yado_unified_core_v1' not in sys.modules
"""
        subprocess.run([sys.executable, "-c", code, str(forged), str(self.state)],
                       cwd=ROOT, check=True, capture_output=True, text=True, timeout=10)


if __name__ == "__main__":
    unittest.main()
