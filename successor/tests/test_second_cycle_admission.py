import tempfile
from pathlib import Path
import unittest

from successor.second_cycle_self_improvement_v2 import discover_transfer_tasks, synthesis_probe
from successor.generalized_boolean_v2 import synthesize_boolean_candidate_v2
from successor.generalized_source_v2 import synthesize_candidate_v2
from yado_active_native_learning_v1 import execute_source


class SecondCycleAdmissionTests(unittest.TestCase):
    def test_sparse_source_still_fails_six_task_floor(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'small').mkdir()
            (root / 'small' / 'code.py').write_text('def square(n):\n    return n ** 2\ndef cube(n):\n    return n ** 3\n')
            with self.assertRaisesRegex(RuntimeError, 'INSUFFICIENT_EXTENDED_REAL_CODE_TASKS:2<6'):
                discover_transfer_tasks(root, {'small': {'repository': 'first', 'head_sha': 'a' * 40}})

    def test_combined_corpus_keeps_provenance_and_removes_duplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ('first', 'second'):
                (root / name).mkdir()
            (root / 'first' / 'code.py').write_text('def square(n):\n    return n ** 2\ndef cube(n):\n    return n ** 3\n')
            (root / 'second' / 'code.py').write_text('def duplicate(n):\n    return n ** 2\n' + ''.join(
                f'def mod_{m}(n):\n    return n % {m}\n' for m in (2, 3, 5, 7)))
            sources = {name: {'repository': 'https://example.invalid/' + name, 'head_sha': name[0] * 40}
                       for name in ('first', 'second')}
            rows = discover_transfer_tasks(root, sources)
            self.assertEqual(len(rows), 6)
            self.assertEqual(len({r['target_expression_sha256'] for r in rows}), 6)
            self.assertEqual({r['source_repository'] for r in rows}, {s['repository'] for s in sources.values()})
            self.assertTrue(all(r['path'] == 'code.py' for r in rows))
            for row in rows:
                source = next(v for v in sources.values() if v['repository'] == row['source_repository'])
                self.assertEqual(row['source_head_sha'], source['head_sha'])

    def test_partial_prediction_vector_cannot_pass_holdout(self):
        class IncompleteKernel:
            def execute(self, task):
                return {'status': 'PASS', 'result': {'source': 'candidate', 'source_sha256': 'f' * 64}}
            def execute_synthesized(self, candidate, inputs):
                return [16]  # The first of three required predictions is correct.
        task = {'path': 'square.py', 'function': 'square', 'args': ['n'],
                'rows': [((n,), n * n) for n in range(1, 7)],
                'source_sha256': 'a' * 64, 'target_expression_sha256': 'b' * 64}
        row = synthesis_probe(IncompleteKernel(), task, 'c' * 40, training_count=3)
        self.assertEqual(row['holdout_passed'], 1)
        self.assertEqual(row['holdout_total'], 3)
        self.assertEqual(row['status'], 'DEFICIT')

    def test_boolean_grammar_requires_identifying_classes(self):
        training = [{'input': {'x': n}, 'expected': False} for n in (2, 4, 6)]
        with self.assertRaisesRegex(ValueError, 'REQUIRES_BOTH_TRAINING_CLASSES'):
            synthesize_boolean_candidate_v2(training)

    def test_bit_predicate_retains_behavior_after_grammar_extension(self):
        # These examples fit both bit extraction and an unrelated AND predicate.
        # Expanding the grammar must preserve the original program's behavior.
        for value_key, offset_key in (("word", "offset"), ("a", "b")):
            with self.subTest(keys=(value_key, offset_key)):
                training = [{'input': {value_key: n, offset_key: p},
                             'expected': bool((n >> p) & 1)}
                            for n, p in ((1, 0), (3, 0), (2, 1), (6, 1),
                                         (1, 1), (5, 1), (4, 2), (7, 2))]
                candidate = synthesize_candidate_v2(training)
                cases = [{value_key: n, offset_key: p}
                         for n, p in ((0, 0), (8, 3), (8, 0), (5, 2), (-2, 0), (-2, 4))]
                self.assertEqual(execute_source(candidate, cases),
                                 [False, True, False, True, False, True])

    def test_bitwise_relational_program_generalizes_to_other_inputs(self):
        # Exhaust a small sign/order grid. Four examples alone also fit unrelated
        # predicates and cannot identify the intended sign contract.
        training = [{'input': {'a': a, 'b': b}, 'expected': (a < 0) != (b < 0)}
                    for a in (-4, -1, 0, 2, 5) for b in (-4, -1, 0, 2, 5)]
        candidate = synthesize_candidate_v2(training)
        actual = execute_source(candidate, [{'a': -21, 'b': 8}, {'a': 12, 'b': 7}, {'a': -8, 'b': -3}])
        self.assertEqual(actual, [True, False, False])
