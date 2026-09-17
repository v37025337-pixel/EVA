from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from yado_autonomous_deep_development_v1 import build_plan


def _touch(root: Path, relative: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("pass\n", encoding="utf-8")


class TestAutonomousDeepDevelopmentController(unittest.TestCase):
    def test_selects_verification_when_regression_is_dirty(self):
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            for relative in (
                "runtime/core.py",
                "successor/agent.py",
                "architecture/core.json",
                "canonical/head.json",
                "experience/receipt.json",
                "receipts/run.json",
                "runtime/causal_logic.py",
                "runtime/thinking_context.py",
                "runtime/intelligence_agent.py",
                "candidates/candidate.py",
            ):
                _touch(tmp_path, relative)
            audit = tmp_path / "audits/yado-full-kernel-audit-v1-report.json"
            audit.parent.mkdir(parents=True, exist_ok=True)
            audit.write_text('{"status":"PASS","findings":[]}\n', encoding="utf-8")
            regression = tmp_path / "audits/yado-full-regression-v1-report.json"
            regression.write_text('{"status":"FAIL_REGRESSION","failures":[{"test":"x"}]}\n', encoding="utf-8")
            plan = build_plan(tmp_path)
            self.assertEqual(plan["status"], "PASS_SHADOW_AUTONOMOUS_DEEP_DEVELOPMENT_PLAN_V1")
            self.assertEqual(plan["selected_target"], "VERIFICATION")
            self.assertFalse(plan["boundaries"]["automatic_main_mutation"])
            self.assertEqual(len(plan["development_sequence"]), 7)

    def test_withholds_when_a_layer_has_no_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            tmp_path = Path(directory)
            _touch(tmp_path, "runtime/core.py")
            plan = build_plan(tmp_path)
            self.assertEqual(plan["status"], "WITHHOLD_AUTONOMOUS_DEEP_DEVELOPMENT_LAYER_COVERAGE_V1")
            self.assertIn(plan["selected_target"], {"INTEGRITY", "VERIFICATION", "LAYERS", "MODULES", "MEMORY_EXPERIENCE"})


if __name__ == "__main__":
    unittest.main()
