import json
import tempfile
import unittest
from pathlib import Path
from yado_blind_deficit_analysis_v1 import analyze

class BlindDeficitAnalysisTest(unittest.TestCase):
    def test_selects_math_as_stable_weakest_domain(self):
        data=json.loads(Path("architecture/yado-blind-deficit-analysis-v1-input.json").read_text())
        report=analyze(data)
        self.assertEqual(report["status"], "PASS_KERNEL_DERIVED_BLIND_DEFICIT_ANALYSIS_V1")
        self.assertEqual(report["selected_domain"], "gsm8k")
        self.assertTrue(report["repeat_consistency"])
        self.assertEqual(report["ranking"][0]["accuracy"], 0.0)

if __name__ == "__main__":
    unittest.main()
