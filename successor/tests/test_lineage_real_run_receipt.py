import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
RECEIPT = ROOT / "receipts/yado-consecutive-runtime-lineage-real-run-20260916.json"
HEX64 = re.compile(r"[0-9a-f]{64}")


class ConsecutiveLineageRealRunReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))

    def test_receipt_records_the_successful_three_generation_run(self):
        receipt = self.receipt
        self.assertEqual(receipt["schema"], "yado.consecutive-runtime-lineage.canonical-receipt.v1")
        self.assertEqual(receipt["workflow"]["run_id"], 35077139787)
        self.assertEqual(receipt["workflow"]["run_number"], 2)
        self.assertEqual(receipt["workflow"]["conclusion"], "success")
        self.assertEqual(receipt["workflow"]["head_commit"], receipt["tested_source"]["commit"])
        self.assertTrue(receipt["pr45_canonical_merge"]["same_tested_tree"])
        self.assertEqual(receipt["tested_source"]["tree"], receipt["pr45_canonical_merge"]["tree"])

        initial = receipt["initial_deficit"]
        self.assertEqual(initial["status"], "WITHHOLD")
        self.assertEqual(initial["budget"], 30)
        self.assertEqual(initial["state_verification"]["status"], "PASS")

        terminal = receipt["terminal_lineage"]
        self.assertEqual(terminal["status"], "COMPLETE")
        self.assertEqual(terminal["phase"], "DONE")
        self.assertEqual(terminal["generation_count"], 3)
        self.assertEqual(terminal["finish"]["reason"], "TARGET_REACHED")
        self.assertEqual(terminal["finish"]["generations"], 3)
        self.assertEqual(terminal["finish"]["status"], "COMPLETE")
        self.assertEqual(terminal["reopen_state_verification"]["status"], "PASS")
        self.assertEqual(terminal["finish"]["tick"], terminal["reopen_state_verification"]["tick"])
        self.assertEqual(terminal["finish"]["event_hash"], terminal["reopen_state_verification"]["event_hash"])

    def test_generation_and_artifact_hashes_are_complete_and_bound(self):
        receipt = self.receipt
        terminal = receipt["terminal_lineage"]
        candidates = terminal["generation_candidate_sha256"]
        programs = terminal["generation_program_sha256"]
        self.assertEqual(len(candidates), 3)
        self.assertEqual(len(programs), 3)
        self.assertEqual(len(set(candidates)), 3)
        self.assertEqual(len(set(programs)), 3)
        self.assertEqual(candidates[0], receipt["initial_deficit"]["selected_candidate_sha256"])
        for digest in candidates + programs + [
            terminal["finish"]["event_hash"],
            receipt["initial_deficit"]["state_verification"]["event_hash"],
            receipt["artifact"]["sha256"],
        ]:
            self.assertRegex(digest, HEX64)
        self.assertEqual(receipt["artifact"]["id"], 10438909904)
        self.assertGreater(receipt["artifact"]["size_in_bytes"], 0)

    def test_workflow_contract_enforces_the_recorded_terminal_conditions(self):
        workflow = ROOT / self.receipt["workflow"]["path"]
        text = workflow.read_text(encoding="utf-8")
        required = (
            "assert session['status'] == 'COMPLETE'",
            "assert session['phase'] == 'DONE'",
            "assert len(session['generations']) == 3",
            "assert session['finish']['reason'] == 'TARGET_REACHED'",
            "assert session['finish']['generations'] == 3",
            "assert verified['status'] == 'PASS'",
        )
        for clause in required:
            self.assertIn(clause, text)

    def test_receipt_preserves_the_bounded_semantic_boundary(self):
        boundary = self.receipt["semantic_boundary"]
        self.assertEqual(boundary["classification"], "BOUNDED_POLYNOMIAL_RUNTIME_CAPACITY_EXTENSIONS")
        excluded = set(boundary["does_not_establish"])
        self.assertTrue({"open-ended architecture invention", "G3", "consciousness"} <= excluded)
        self.assertEqual(boundary["inherited_algorithm"], "exact polynomial fitter")


if __name__ == "__main__":
    unittest.main()
