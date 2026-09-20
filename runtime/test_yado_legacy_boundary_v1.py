import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "runtime"), str(ROOT / "runtime/yado_rc8_v36")]

from yado_core_v2 import AbsoluteCodeSystem
from yado_evolution_archive_runtime_v1 import EvolutionVariant
from yado_g2_experience_conditioned_cognitive_layer_v4 import G2ExperienceConditionedCognitiveLayerV4
from yado_legacy_data_boundary_v1 import (
    CheckedAbsoluteCodeSystem, CheckedEvolutionArchiveRuntime, CheckedTransferMemoryRuntime,
)
from yado_legacy_planning_boundary_v1 import plan_multicontext, plan_with_edges
from yado_transfer_memory_runtime_v1 import TransferExperience


class LegacyDataBoundaryTests(unittest.TestCase):
    def test_codec_preserves_text_and_inherited_envelopes(self):
        for text in ("", "AB", "Привет\x00"):
            for writer in (AbsoluteCodeSystem, CheckedAbsoluteCodeSystem):
                with self.subTest(text=text, writer=writer.__name__):
                    self.assertEqual(CheckedAbsoluteCodeSystem.decompress_text(writer.compress_text(text)),
                                     (True, text))

    def test_codec_rejects_truncated_length(self):
        for writer in (AbsoluteCodeSystem, CheckedAbsoluteCodeSystem):
            payload = writer.compress_text("AB")
            payload["binary_length"] = 8
            self.assertEqual(CheckedAbsoluteCodeSystem.decompress_text(payload), (False, ""))

    def test_new_bit_envelopes_bind_length_and_padding(self):
        codec = CheckedAbsoluteCodeSystem(3)
        for bits in ("", "0", "1", "100", "101001", "111111111"):
            self.assertEqual(codec.decompress_data(codec.compress_data(bits)), (True, bits))
        payload = codec.compress_data("100")
        payload.update(binary_length=2, pad_bits=6)
        self.assertEqual(codec.decompress_data(payload), (False, ""))
        payload = codec.compress_data("100")
        payload.pop("envelope_sha256")
        self.assertEqual(codec.decompress_data(payload), (False, ""))

    @staticmethod
    def experience(identity, domain, score=1.0):
        return TransferExperience(identity, domain, ["verify"], ["VERIFY"], score, True)

    def test_transfer_requires_unique_experience_support(self):
        first, second = self.experience("one", "a"), self.experience("two", "b")
        runtime = CheckedTransferMemoryRuntime()
        self.assertEqual(runtime.consolidate([first, first, second])["memory_count"], 0)
        third = self.experience("three", "c")
        result = runtime.consolidate([first, second, third, first])
        self.assertEqual(result["memory_count"], 1)
        self.assertEqual(result["memories"][0].support, 3)

    def test_transfer_rejects_contradictory_identity(self):
        with self.assertRaisesRegex(ValueError, "EXPERIENCE_ID_COLLISION"):
            CheckedTransferMemoryRuntime().consolidate([
                self.experience("same", "a"), self.experience("same", "b")])

    def test_transfer_rejects_nonfinite_outcomes(self):
        for invalid in (float("nan"), float("inf"), float("-inf"), sys.float_info.max):
            with self.subTest(score=invalid), self.assertRaisesRegex(ValueError, "NONFINITE_MEMORY_SCORE"):
                CheckedTransferMemoryRuntime().consolidate([
                    self.experience(str(index), str(index), invalid) for index in range(3)])

    def test_archive_never_treats_string_false_as_pass(self):
        constraints = {key: "false" for key in CheckedEvolutionArchiveRuntime.REQUIRED_CONSTRAINTS}
        variant = EvolutionVariant("bad", None, "L", "digest", {"task": 1.0}, constraints)
        self.assertFalse(CheckedEvolutionArchiveRuntime().admitted(variant))
        with self.assertRaisesRegex(ValueError, "CONSTRAINT_NOT_BOOLEAN"):
            CheckedEvolutionArchiveRuntime([variant])

    def test_archive_retains_failed_candidates_without_selecting_them(self):
        constraints = {key: True for key in CheckedEvolutionArchiveRuntime.REQUIRED_CONSTRAINTS}
        good = EvolutionVariant("good", None, "L", "g", {"task": 0.8}, constraints)
        bad = EvolutionVariant("bad", None, "L", "b", {"task": 1.0},
                               {**constraints, "regression_pass": False})
        archive = CheckedEvolutionArchiveRuntime([good, bad])
        self.assertEqual(archive.select_parent("task")["variant_id"], "good")
        self.assertEqual(archive.snapshot()["variant_count"], 2)


class LegacyPlanningBoundaryTests(unittest.TestCase):
    ACTIONS = [{"id": "A", "role": "a"}, {"id": "B", "role": "b"}]
    CYCLE = [{"before": "a", "after": "b"}, {"before": "b", "after": "a"}]

    def test_precedence_cycle_has_no_executable_order(self):
        for edges in (self.CYCLE, [{"before": "a", "after": "a"}]):
            with self.assertRaisesRegex(ValueError, "PRECEDENCE_CYCLE"):
                plan_with_edges(self.ACTIONS, edges)

    def test_acyclic_order_is_preserved(self):
        self.assertEqual(plan_with_edges(self.ACTIONS, [{"before": "b", "after": "a"}]), ["B", "A"])

    def test_multicontext_checks_selected_graph(self):
        model = {"kind": "MULTICONTEXT_PRECEDENCE", "context_keys": ["reverse"],
                 "graphs": {"1": [{"before": "b", "after": "a"}], "0": self.CYCLE}}
        self.assertEqual(plan_multicontext(model, {"reverse": True}, self.ACTIONS), ["B", "A"])
        with self.assertRaisesRegex(ValueError, "PRECEDENCE_CYCLE"):
            plan_multicontext(model, {"reverse": False}, self.ACTIONS)

    def test_active_cognitive_api_withholds_cyclic_learned_plan(self):
        artifact = json.loads((ROOT / "canonical/yado-g2-experience-conditioned-cognitive-layer-v4.json").read_text())
        task = artifact["multidomain_genes"]["THINKING"]["task_models"][0]
        task["model"] = copy.deepcopy(self.CYCLE)
        layer = G2ExperienceConditionedCognitiveLayerV4(artifact)
        result = layer.decide("THINKING", {"task_id": task["task_id"], "context": {}, "actions": self.ACTIONS})
        self.assertEqual(result["decision"], "WITHHOLD")
        self.assertEqual(result["route_cardinality"], "ZERO")


if __name__ == "__main__":
    unittest.main()
