from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from yado_external_dev_experience_router_self_repair_v2 import (
    DEFAULT_HISTORY_RECEIPT,
    ExternalDevExperienceRouterSelfRepairV2,
    load_candidate,
)


class ExperienceRouterSelfRepairV2Tests(unittest.TestCase):
    def test_retained_experience_repairs_contamination_and_transfers(self):
        out = ExternalDevExperienceRouterSelfRepairV2().run()
        self.assertEqual(out["status"], "PASS_SHADOW_EXPERIENCE_ROUTER_SELF_REPAIR_V2")
        self.assertEqual(out["history_event_count"], 7)
        self.assertTrue(all(row["pass"] for row in out["retained_history_replay"]))
        self.assertTrue(all(row["pass"] for row in out["bootstrap_retention"]))
        self.assertTrue(out["reproduced_defect"]["base_failed"])
        self.assertTrue(out["reproduced_defect"]["candidate_passed"])
        self.assertTrue(out["fresh_contamination_holdout"]["base_failed"])
        self.assertTrue(out["fresh_contamination_holdout"]["candidate_passed"])
        self.assertEqual(out["fresh_contamination_holdout"]["gain_over_base"], 1)
        self.assertTrue(out["unknown_withhold"])
        self.assertFalse(out["automatic_main_mutation"])
        self.assertFalse(out["g3_genesis_performed"])

    def test_materialized_candidate_compiles_and_is_restricted(self):
        with tempfile.TemporaryDirectory() as tmp:
            candidate = Path(tmp) / "router_v2.py"
            receipt = Path(tmp) / "receipt.json"
            out = ExternalDevExperienceRouterSelfRepairV2().run(
                candidate_path=candidate,
                receipt_path=receipt,
            )
            source = candidate.read_text(encoding="utf-8")
            compile(source, str(candidate), "exec")
            route, snapshot = load_candidate(source)
            self.assertEqual(
                route("evaluate an unclassified quantum biology hypothesis")["status"],
                "WITHHOLD_ROUTER_NO_MATCH",
            )
            self.assertFalse(snapshot()["automatic_main_mutation"])
            self.assertEqual(json.loads(receipt.read_text(encoding="utf-8"))["receipt_sha256"], out["receipt_sha256"])

    def test_tampered_history_is_rejected(self):
        original = json.loads(DEFAULT_HISTORY_RECEIPT.read_text(encoding="utf-8"))
        original["events"][3]["goal"] += " tampered"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tampered.json"
            path.write_text(json.dumps(original), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "EVENT_DIGEST_MISMATCH"):
                ExternalDevExperienceRouterSelfRepairV2(history_receipt_path=path).run()


if __name__ == "__main__":
    unittest.main()
