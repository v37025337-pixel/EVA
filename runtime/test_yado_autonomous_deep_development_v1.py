from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from yado_autonomous_deep_development_v1 import build_plan


def _touch(root: Path, relative: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("pass\n", encoding="utf-8")


def _json(root: Path, relative: str, value: dict) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")


def _complete_layers(root: Path) -> None:
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
        _touch(root, relative)


def _clean_gates(root: Path) -> None:
    _json(root, "audits/yado-full-kernel-audit-v1-report.json", {"status": "PASS", "findings": []})
    _json(root, "audits/yado-full-regression-v1-report.json", {"status": "PASS", "failures": []})


class TestAutonomousDeepDevelopmentController(unittest.TestCase):
    def test_selects_verification_when_regression_is_dirty(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _complete_layers(root)
            _json(root, "audits/yado-full-kernel-audit-v1-report.json", {"status": "PASS", "findings": []})
            _json(root, "audits/yado-full-regression-v1-report.json", {"status": "FAIL_REGRESSION", "failures": [{"test": "x"}]})
            plan = build_plan(root)
            self.assertEqual(plan["status"], "PASS_SHADOW_AUTONOMOUS_DEEP_DEVELOPMENT_PLAN_V1")
            self.assertEqual(plan["selected_target"], "VERIFICATION")
            self.assertFalse(plan["boundaries"]["automatic_main_mutation"])
            self.assertEqual(len(plan["development_sequence"]), 7)

    def test_withholds_when_a_layer_has_no_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _touch(root, "runtime/core.py")
            plan = build_plan(root)
            self.assertEqual(plan["status"], "WITHHOLD_AUTONOMOUS_DEEP_DEVELOPMENT_LAYER_COVERAGE_V1")
            self.assertIn(plan["selected_target"], {"INTEGRITY", "VERIFICATION", "LAYERS", "MODULES", "MEMORY_EXPERIENCE"})

    def test_measured_logic_does_not_repeat_when_memory_is_unmeasured(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _complete_layers(root)
            _clean_gates(root)
            _json(
                root,
                "candidates/cognitive/yado-relational-causal-logic-holdout-v1.json",
                {
                    "status": "PASS_SHADOW_RELATIONAL_CAUSAL_LOGIC_HOLDOUT_V1",
                    "selected_scores": {"fresh": {"accuracy": 1.0}},
                },
            )
            _json(
                root,
                "candidates/cognitive/yado-cognitive-tri-organ-evolution-v2.json",
                {
                    "status": "PASS_SHADOW_BOUNDED_TRI_ORGAN_COGNITIVE_EVOLUTION_V2",
                    "selected_hidden": {"thinking": 0.95, "intelligence": 1.0},
                },
            )
            _json(
                root,
                "experience/branch-lifecycle/yado-branch-memory-index-v1.json",
                {"status": "PASS_MEMORY_INDEX", "memory_ref_count": 13},
            )
            plan = build_plan(root)
            self.assertEqual(plan["selector_version"], "EVIDENCE_AWARE_DEFICIT_SELECTOR_V2")
            self.assertEqual(plan["selected_target"], "MEMORY_EXPERIENCE")
            self.assertEqual(plan["cognitive_evidence"]["LOGIC"]["score"], 1.0)
            self.assertIsNone(plan["cognitive_evidence"]["MEMORY_EXPERIENCE"]["score"])

    def test_after_memory_measurement_selects_weakest_measured_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _complete_layers(root)
            _clean_gates(root)
            _json(
                root,
                "candidates/cognitive/yado-relational-causal-logic-holdout-v1.json",
                {
                    "status": "PASS_SHADOW_RELATIONAL_CAUSAL_LOGIC_HOLDOUT_V1",
                    "selected_scores": {"fresh": {"accuracy": 1.0}},
                },
            )
            _json(
                root,
                "candidates/cognitive/yado-cognitive-tri-organ-evolution-v2.json",
                {
                    "status": "PASS_SHADOW_BOUNDED_TRI_ORGAN_COGNITIVE_EVOLUTION_V2",
                    "selected_hidden": {"thinking": 0.95, "intelligence": 1.0},
                },
            )
            _json(
                root,
                "candidates/cognitive/yado-memory-experience-holdout-v1.json",
                {
                    "status": "PASS_SHADOW_MEMORY_EXPERIENCE_HOLDOUT_V1",
                    "selected_scores": {"fresh": {"accuracy": 0.99}},
                },
            )
            plan = build_plan(root)
            self.assertEqual(plan["selected_target"], "THINKING")
            self.assertIn("0.950000", plan["selection_reason"])

    def test_after_fresh_thinking_measurement_selects_intelligence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _complete_layers(root)
            _clean_gates(root)
            _json(
                root,
                "candidates/cognitive/yado-relational-causal-logic-holdout-v1.json",
                {
                    "status": "PASS_SHADOW_RELATIONAL_CAUSAL_LOGIC_HOLDOUT_V1",
                    "selected_scores": {"fresh": {"accuracy": 1.0}},
                },
            )
            _json(
                root,
                "candidates/cognitive/yado-cognitive-tri-organ-evolution-v2.json",
                {
                    "status": "PASS_SHADOW_BOUNDED_TRI_ORGAN_COGNITIVE_EVOLUTION_V2",
                    "selected_hidden": {"thinking": 0.95, "intelligence": 1.0},
                },
            )
            _json(
                root,
                "candidates/cognitive/yado-memory-experience-holdout-v1.json",
                {
                    "status": "PASS_SHADOW_MEMORY_EXPERIENCE_HOLDOUT_V1",
                    "selected_scores": {"fresh": {"accuracy": 1.0}},
                },
            )
            _json(
                root,
                "candidates/cognitive/yado-thinking-contextual-holdout-v1.json",
                {
                    "status": "PASS_SHADOW_THINKING_CONTEXTUAL_HOLDOUT_V1",
                    "selected_scores": {"fresh": {"accuracy": 1.0}},
                },
            )
            plan = build_plan(root)
            self.assertEqual(plan["selected_target"], "INTELLIGENCE")
            self.assertEqual(plan["cognitive_evidence"]["THINKING"]["evidence_kind"], "FRESH_HOLDOUT")
            self.assertEqual(plan["cognitive_evidence"]["INTELLIGENCE"]["evidence_kind"], "HIDDEN_HOLDOUT")


if __name__ == "__main__":
    unittest.main()
