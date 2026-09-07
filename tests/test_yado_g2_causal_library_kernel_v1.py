import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
MOD = ROOT / "runtime/yado_g2_causal_library_kernel_v1.py"
spec = importlib.util.spec_from_file_location("yado_g2_causal_library_kernel_v1", MOD)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class TestG2CausalLibraryKernelV1(unittest.TestCase):
    def setUp(self):
        self.kernel = module.G2CausalLibraryKernelV1(ROOT)

    def test_library_and_genetics_validate(self):
        result = self.kernel.validate()
        self.assertEqual(result["status"], "PASS_CAUSAL_LIBRARY_KERNEL_V1")
        self.assertEqual(result["normal_dispatch_count"], 26)
        self.assertEqual(result["compatibility_fallback_count"], 5)
        self.assertEqual(result["layer_count"], 8)
        self.assertFalse(result["g3_genesis"])

    def test_tri_organ_contracts_have_single_owner(self):
        logic = self.kernel.route_contract("RELATION_START_TO_STATE")
        thinking = self.kernel.route_contract("EVENT_SEQUENCE_TO_BOOLEAN")
        self.assertEqual(logic["status"], "PRIMARY_TRI_ORGAN")
        self.assertEqual(thinking["status"], "PRIMARY_TRI_ORGAN")
        self.assertNotEqual(logic["component_id"], thinking["component_id"])

    def test_unknown_contract_falls_back_without_self_promotion(self):
        route = self.kernel.route_contract("UNKNOWN_CONTRACT")
        self.assertEqual(route["status"], "FALLBACK_REQUIRED")
        trace = self.kernel.causal_trace("UNKNOWN_CONTRACT")
        self.assertFalse(trace["automatic_promotion"])
        self.assertEqual(trace["layers"][0], "L0_INPUT_GROUNDING")
        self.assertEqual(trace["layers"][-1], "L7_CONTINUITY_TIME")

if __name__ == "__main__":
    unittest.main()
