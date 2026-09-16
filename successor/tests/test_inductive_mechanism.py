import copy
import hashlib
import inspect
import unittest

from successor import inductive_mechanism as mechanism
from successor import native_mechanism as polynomial
from yado_active_native_learning_v1 import execute_source


def rows(function, *, key="x", xs=range(-5, 6)):
    return [{"input": {key: x}, "expected": function(x)} for x in xs]


class InductiveMechanismTests(unittest.TestCase):
    def test_nonpolynomial_deficit_derives_a_conditional_primitive_profile(self):
        training = rows(abs)
        self.assertIsNone(polynomial.inferred_degree(training, max_degree=5))
        candidate = mechanism.build_candidate(training)
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate["profile"], {
            "grammar_version": "YADO_TYPED_SEMANTIC_PROGRAM_INDUCTION_V1",
            "primitive_set": ["var", "const", "neg", "lt", "if"],
            "max_nodes": 7,
            "constants": [0, 1, -1, 2, -2],
        })
        result = mechanism.synthesize(candidate, training)
        self.assertEqual(result["status"], "SOURCE_CANDIDATE")
        self.assertEqual(result["selected"]["primitives"], ["var", "const", "neg", "lt", "if"])
        self.assertEqual(result["selected"]["nodes"], 7)
        self.assertEqual(execute_source(result, [{"x": x} for x in (-19, -8, -1, 0, 4, 17)]),
                         [19, 8, 1, 0, 4, 17])

    def test_same_generic_harness_derives_a_different_modular_boolean_profile(self):
        training = rows(lambda x: x % 2 == 0)
        candidate = mechanism.build_candidate(training)
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate["profile"]["primitive_set"], ["var", "const", "mod", "eq"])
        self.assertEqual(candidate["profile"]["max_nodes"], 5)
        result = mechanism.synthesize(candidate, training)
        self.assertEqual(result["selected"]["expression"], "(0 == (inputs['x'] % 2))")
        self.assertEqual(execute_source(result, [{"x": x} for x in (-13, -8, 7, 22)]),
                         [False, True, False, True])

    def test_frozen_profile_transfers_to_new_conditional_programs(self):
        candidate = mechanism.build_candidate(rows(abs))
        frozen = copy.deepcopy(candidate)
        functions = (
            lambda x: abs(x),
            lambda x: -abs(x),
            lambda x: -x if x < -1 else x,
            lambda x: 2 if x < 0 else x,
        )
        probes = (-17, -8, -2, -1, 0, 1, 9, 14)
        program_hashes = []
        for index, function in enumerate(functions):
            with self.subTest(index=index):
                training = rows(function, key="fresh_value")
                result = mechanism.synthesize(candidate, training)
                self.assertTrue(result["compiled"])
                self.assertEqual(result["mechanism_source_sha256"], candidate["source_sha256"])
                self.assertEqual(execute_source(result, [{"fresh_value": x} for x in probes]),
                                 [function(x) for x in probes])
                program_hashes.append(result["source_sha256"])
        self.assertGreaterEqual(len(set(program_hashes)), 3)
        self.assertEqual(candidate, frozen)

    def test_candidate_contains_profile_not_observed_labels_or_a_named_target_family(self):
        training = rows(abs)
        candidate = mechanism.build_candidate(training)
        self.assertNotIn("abs", candidate["source"].lower())
        self.assertNotIn("absolute", candidate["source"].lower())
        self.assertNotIn("expected", candidate["source"].lower())
        self.assertEqual(candidate["source"], mechanism.emit(candidate["profile"]))
        self.assertEqual(candidate["source_sha256"], hashlib.sha256(candidate["source"].encode()).hexdigest())
        self.assertEqual(tuple(inspect.signature(mechanism.build_candidate).parameters), ("training",))

    def test_selection_is_deterministic_and_training_only(self):
        training = rows(abs)
        before = copy.deepcopy(training)
        first = mechanism.build_candidate(training)
        second = mechanism.build_candidate(copy.deepcopy(training))
        self.assertEqual(first, second)
        self.assertEqual(training, before)
        result = mechanism.synthesize(first, training)
        self.assertEqual(result["synthesis_inputs"], "TRAINING_ONLY")
        self.assertFalse(result["automatic_canonical_promotion"])

    def test_profile_and_source_tampering_are_rejected_before_use(self):
        original = mechanism.build_candidate(rows(abs))
        mutations = []
        changed = copy.deepcopy(original)
        changed["profile"]["primitive_set"].append("mul")
        mutations.append(changed)
        changed = copy.deepcopy(original)
        changed["profile"]["max_nodes"] = 6
        mutations.append(changed)
        changed = copy.deepcopy(original)
        changed["source"] += "raise AssertionError('untrusted')\n"
        changed["source_sha256"] = hashlib.sha256(changed["source"].encode()).hexdigest()
        mutations.append(changed)
        changed = copy.deepcopy(original)
        changed["source_sha256"] = "0" * 64
        mutations.append(changed)
        changed = copy.deepcopy(original)
        changed["schema"] = "forged"
        mutations.append(changed)
        for candidate in mutations:
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                mechanism.synthesize(candidate, rows(abs))

    def test_invalid_or_out_of_profile_training_withholds_without_source(self):
        candidate = mechanism.build_candidate(rows(abs))
        invalid = [
            rows(abs)[:2],
            rows(abs) + [copy.deepcopy(rows(abs)[0])],
            [{"input": {"x": x, "y": 1}, "expected": x} for x in range(5)],
            [{"input": {"x": str(x)}, "expected": x} for x in range(5)],
        ]
        for training in invalid:
            with self.subTest(training=training):
                result = mechanism.synthesize(candidate, training)
                self.assertEqual(result["status"], "WITHHOLD")
                self.assertIsNone(result["source"])
                self.assertFalse(result["compiled"])
        modular = rows(lambda x: x % 2 == 0)
        result = mechanism.synthesize(candidate, modular)
        self.assertEqual(result["status"], "WITHHOLD")
        self.assertIsNone(result["source"])


if __name__ == "__main__":
    unittest.main()
