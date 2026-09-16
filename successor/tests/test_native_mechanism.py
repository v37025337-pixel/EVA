"""Behavior and provenance checks for the emitted reusable polynomial fitter."""
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from successor import native_mechanism as mechanism
from yado_active_native_learning_v1 import execute_source


def rows(function, xs=(-3, -2, -1, 0, 1, 2), key='x'):
    return [{'input': {key: x}, 'expected': function(x)} for x in xs]


class NativeMechanismTests(unittest.TestCase):
    def test_regression_uses_the_frozen_runtime_candidate_when_provided(self):
        path = os.environ.get('YADO_RUNTIME_CANDIDATE')
        candidate = json.loads(Path(path).read_text()) if path else mechanism.build_candidate(2)
        mechanism.validate_candidate(candidate)
        expected_digest = os.environ.get('YADO_RUNTIME_CANDIDATE_SHA256')
        if path and expected_digest:
            self.assertEqual(candidate['source_sha256'], expected_digest)
        frozen = copy.deepcopy(candidate)
        functions = [(0, lambda x: 41), (0, lambda x: -73), (0, lambda x: 199),
                     (1, lambda x: 23 * x - 117),
                     (2, lambda x: 13 * x * x + 37 * x - 53),
                     (3, lambda x: 11 * x ** 3 + 17 * x * x - 83 * x + 101),
                     (4, lambda x: 13 * x ** 4 - 19 * x ** 3 + 7 * x - 31),
                     (5, lambda x: 17 * x ** 5 + 11 * x ** 4 - 23 * x * x + 43)]
        for index, (degree, function) in enumerate(functions):
            if degree > candidate['profile']['max_degree']:
                continue
            with self.subTest(degree=degree, function=index):
                key = 'Fresh_Parameter_' + str(index)
                result = mechanism.synthesize(candidate, rows(function, xs=range(-3, 4), key=key))
                self.assertEqual(result['selected']['degree'], degree)
                self.assertEqual(result['mechanism_source_sha256'], candidate['source_sha256'])
                self.assertEqual(execute_source(result, [{key: -9}, {key: 13}]),
                                 [function(-9), function(13)])
        self.assertEqual(candidate, frozen)

    def test_one_frozen_module_recomputes_three_distinct_functions(self):
        candidate = mechanism.build_candidate(3)
        frozen = copy.deepcopy(candidate)
        namespace = {}
        exec(candidate['source'], namespace)
        programs = []
        for function, degree in ((lambda x: 19 * x - 43, 1),
                                 (lambda x: 10 - x * x, 2),
                                 (lambda x: 31 * x ** 3 - 17 * x ** 2 + 90 * x - 111, 3)):
            with self.subTest(degree=degree):
                training = rows(function, key='Unseen_91')
                result = namespace['synthesize'](training)
                self.assertTrue(result['compiled'])
                self.assertEqual(result['selected']['degree'], degree)
                self.assertEqual(execute_source(result, [{'Unseen_91': x} for x in (-11, 8)]),
                                 [function(-11), function(8)])
                self.assertEqual(mechanism.inferred_degree(training), degree)
                programs.append(result['source_sha256'])
        self.assertEqual(len(set(programs)), 3)
        self.assertEqual(candidate, frozen)

    def test_wrapper_returns_native_candidate_and_freezes_training(self):
        candidate = mechanism.build_candidate(2)
        training = rows(lambda x: 1234 - 219 * x + 53 * x * x, key='Amount')
        before = copy.deepcopy(training)
        result = mechanism.synthesize(candidate, training)
        self.assertEqual(result['source_sha256'], hashlib.sha256(result['source'].encode()).hexdigest())
        self.assertEqual(result['mechanism_source_sha256'], candidate['source_sha256'])
        self.assertEqual(result['synthesis_inputs'], 'TRAINING_ONLY')
        self.assertEqual(result['selected']['coefficients'], [1234, -219, 53])
        self.assertEqual(execute_source(result, [{'Amount': -9}, {'Amount': 13}]),
                         [1234 + 219 * 9 + 53 * 81, 1234 - 219 * 13 + 53 * 169])
        self.assertEqual(training, before)

    def test_emission_is_deterministic_and_contains_the_inherited_fit_body(self):
        candidate = mechanism.build_candidate(2)
        self.assertEqual(candidate, mechanism.build_candidate(2))
        self.assertEqual(candidate['source'], mechanism.emit(candidate['profile']))
        self.assertIsNone(mechanism.validate_candidate(candidate))
        root = Path(__file__).resolve().parents[2]
        donor = root / candidate['profile']['donor']['path']
        self.assertEqual(hashlib.sha256(donor.read_bytes()).hexdigest(),
                         candidate['profile']['donor']['sha256'])
        cls = next(n for n in ast.parse(donor.read_text()).body
                   if isinstance(n, ast.ClassDef) and n.name == 'PolynomialCodeLineageGene')
        fit = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'fit')
        emitted = next(n for n in ast.parse(candidate['source']).body
                       if isinstance(n, ast.FunctionDef) and n.name == '_fit')
        self.assertEqual([ast.dump(n) for n in fit.body], [ast.dump(n) for n in emitted.body])
        self.assertEqual([arg.arg for arg in emitted.args.args], ['examples', 'max_degree'])
        self.assertEqual(emitted.decorator_list, [])

    def test_profile_is_bounded_and_changes_the_runtime_budget(self):
        for invalid in (-1, 6, True, '2', 2.0, None):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                mechanism.build_candidate(invalid)
        constant = mechanism.synthesize(mechanism.build_candidate(0), rows(lambda x: 37))
        self.assertEqual(constant['selected']['degree'], 0)
        self.assertEqual(execute_source(constant, [{'x': -1000}]), [37])
        self.assert_withheld(mechanism.build_candidate(1), rows(lambda x: 10 - x * x))

    def test_legacy_profiles_and_emitted_bytes_remain_exact(self):
        digests = (
            'da185d7db9ec0353e08c6f7ca0dc656c99501a79db9066354b5a4170e0aecf1d',
            '89d0c060f565dc3c063410455dfd2e40996db67863be2dae52260e2d9585a81d',
            '5367323ff7ea1c3a659ed781328aca5f19c345ea6cf42ec945f42294164ca6f8',
            '5e26fac2063df650695cae0726cda483216c25c3d9bb7f4191d76ddecaf8d01f',
        )
        for degree, digest in enumerate(digests):
            with self.subTest(degree=degree):
                candidate = mechanism.build_candidate(degree)
                self.assertEqual(candidate['schema'], 'yado.native_mechanism.v1')
                self.assertEqual(candidate['profile'], {
                    'grammar_version': 'YADO_EXACT_POLYNOMIAL_NATIVE_MECHANISM_V1',
                    'donor': {'path': 'runtime/yado_evolutionary_multigeneration_lineage_v1.py',
                        'sha256': 'a471c4a4c53044db94f482ad7d6f2c4758bad3f9d60c68f2252b88759b7a1cc3'},
                    'max_degree': degree})
                self.assertEqual(candidate['source_sha256'], digest)
                self.assertEqual(hashlib.sha256(candidate['source'].encode()).hexdigest(), digest)
                mechanism.validate_candidate(candidate)

    def test_new_version_supports_four_and_five_without_extending_legacy_inference(self):
        for degree in (4, 5):
            with self.subTest(degree=degree):
                function = lambda x: 7 * x ** degree - 11 * x + 23
                training = rows(function, xs=range(-3, 4), key='NewInput')
                candidate = mechanism.build_candidate(degree)
                self.assertEqual(candidate['profile']['grammar_version'],
                                 'YADO_EXACT_POLYNOMIAL_NATIVE_MECHANISM_V2')
                self.assertIsNone(mechanism.inferred_degree(training))
                self.assertEqual(mechanism.inferred_degree(training, max_degree=5), degree)
                result = mechanism.synthesize(candidate, training)
                self.assertEqual(result['selected']['degree'], degree)
                self.assertEqual(result['grammar_stage'], 'EMITTED_EXACT_POLYNOMIAL_NATIVE_MECHANISM_V2')
                self.assertEqual(execute_source(result, [{'NewInput': -9}, {'NewInput': 11}]),
                                 [function(-9), function(11)])
                old_profile = copy.deepcopy(candidate)
                old_profile['profile']['grammar_version'] = 'YADO_EXACT_POLYNOMIAL_NATIVE_MECHANISM_V1'
                with self.assertRaisesRegex(ValueError, 'PROFILE_MISMATCH'):
                    mechanism.validate_candidate(old_profile)

    def test_new_degree_limit_and_training_evidence_remain_bounded(self):
        candidate = mechanism.build_candidate(5)
        overdegree = rows(lambda x: x ** 6, xs=range(-4, 5))
        self.assert_withheld(candidate, overdegree)
        self.assertIsNone(mechanism.inferred_degree(overdegree, max_degree=5))
        for degree in (4, 5):
            with self.subTest(degree=degree):
                training = rows(lambda x: x ** degree, xs=range(degree + 1))
                self.assert_withheld(mechanism.build_candidate(degree), training)
        for invalid in (-1, 6, True, '5', 5.0, None):
            with self.subTest(bound=invalid), self.assertRaises(ValueError):
                mechanism.inferred_degree(rows(lambda x: x), max_degree=invalid)

    def assert_withheld(self, candidate, training):
        result = mechanism.synthesize(candidate, training)
        self.assertEqual(result['status'], 'WITHHOLD')
        self.assertIsNone(result['source'])
        self.assertFalse(result['compiled'])
        self.assertIsInstance(result['reason'], str)
        return result

    def test_nonintegral_coefficients_and_overdegree_withhold(self):
        candidate = mechanism.build_candidate(3)
        nonintegral = rows(lambda x: x * (x - 1) // 2)
        overdegree = rows(lambda x: x ** 4, xs=(-3, -2, -1, 0, 1, 2, 3))
        for training in (nonintegral, overdegree):
            with self.subTest(training=training):
                self.assert_withheld(candidate, training)
                self.assertIsNone(mechanism.inferred_degree(training))

    def test_a_fit_requires_an_extra_distinct_training_point(self):
        candidate = mechanism.build_candidate(3)
        for training in (rows(lambda x: x * x, xs=(0, 1, 2)),
                         rows(lambda x: x ** 3, xs=(0, 1, 2, 3)),
                         rows(lambda x: 7, xs=(0, 1))):
            with self.subTest(training=training):
                self.assert_withheld(candidate, training)
                self.assertIsNone(mechanism.inferred_degree(training))

    def test_invalid_training_is_rejected_without_considering_validation(self):
        good = rows(lambda x: 10 - x * x)
        bad_rows = [
            tuple(good), {'training': good, 'validation': good, 'queries': []}, [],
            good + [copy.deepcopy(good[0])],
            [{'input': {'x': x, 'y': 2}, 'expected': x} for x in range(4)],
            [{'input': {'x': x}, 'expected': True} for x in range(4)],
            [{'input': {'x': str(x)}, 'expected': x} for x in range(4)],
            [{'input': {'x': x}, 'expected': str(x)} for x in range(4)],
            [{'input': {'bad key': x}, 'expected': x} for x in range(4)],
            [{'input': {'x': x}, 'expected': x, 'validation': x} for x in range(4)],
            rows(lambda x: x, xs=range(65)),
        ]
        for field, value in (('input', {'x': True}), ('input', {'y': -3}),
                             ('input', {'x': -1000001}), ('input', {'x': 3.0}),
                             ('expected', 1000001)):
            invalid = copy.deepcopy(good)
            invalid[0][field] = value
            bad_rows.append(invalid)
        for training in bad_rows:
            with self.subTest(training=training):
                self.assert_withheld(mechanism.build_candidate(3), training)
                self.assertIsNone(mechanism.inferred_degree(training))

    def test_native_integer_boundary_and_negative_inputs_are_supported(self):
        training = rows(lambda x: x, xs=(-1000000, -1, 1000000))
        result = mechanism.synthesize(mechanism.build_candidate(1), training)
        self.assertEqual(execute_source(result, [{'x': -999999}, {'x': 999999}]),
                         [-999999, 999999])

    def test_source_or_provenance_tampering_is_rejected_before_execution(self):
        original = mechanism.build_candidate(3)
        mutations = []
        code = copy.deepcopy(original)
        code['source'] += "\nraise AssertionError('arbitrary source executed')\n"
        code['source_sha256'] = hashlib.sha256(code['source'].encode()).hexdigest()
        mutations.append(code)
        for field, value in (('schema', 'forged'), ('source_sha256', '0' * 64)):
            candidate = copy.deepcopy(original)
            candidate[field] = value
            mutations.append(candidate)
        for change in ('donor_path', 'donor_sha', 'grammar', 'degree', 'extra'):
            candidate = copy.deepcopy(original)
            if change == 'donor_path':
                candidate['profile']['donor']['path'] = '/tmp/untrusted.py'
            elif change == 'donor_sha':
                candidate['profile']['donor']['sha256'] = '0' * 64
            elif change == 'grammar':
                candidate['profile']['grammar_version'] = 'new'
            elif change == 'degree':
                candidate['profile']['max_degree'] = 2
            else:
                candidate['profile']['observed_coefficients'] = [10, 0, -1]
            mutations.append(candidate)
        for candidate in mutations:
            with self.subTest(candidate=candidate), patch.object(mechanism, 'exec', create=True) as execute:
                with self.assertRaises(ValueError):
                    mechanism.synthesize(candidate, rows(lambda x: x))
                execute.assert_not_called()

    def test_changed_donor_is_rejected_before_execution(self):
        candidate = mechanism.build_candidate(3)
        with patch.object(Path, 'read_bytes', return_value=b'raise AssertionError("wrong donor")'):
            with patch.object(mechanism, 'exec', create=True) as execute:
                with self.assertRaises(ValueError):
                    mechanism.synthesize(candidate, rows(lambda x: x))
                execute.assert_not_called()


if __name__ == '__main__':
    unittest.main()
