import tempfile
from pathlib import Path
import unittest

from successor.cognitive import validate_goal
from successor.real_coding_intelligence_run import discover_real_code_tasks
from yado_generic_relational_meta_language_v1 import GenericRelationalMetaLanguageV1


class ExternalTaskCoverageTests(unittest.TestCase):
    def test_valid_maximum_length_relation_reaches_its_last_node(self):
        spec = {'domain': 'relation', 'relation': [[i, i+1] for i in range(127)], 'start': 0}
        validate_goal(spec)
        program = {'seed': 'START', 'direction': 'FORWARD', 'merge': 'UNION', 'iteration': 'UNTIL_STABLE'}
        self.assertEqual(set(GenericRelationalMetaLanguageV1.execute(program, spec['relation'], 0)), set(range(128)))

    def test_valid_dense_relation_accepts_the_public_edge_budget(self):
        edges = [[a, b] for a in range(32) for b in range(32)]
        validate_goal({'domain': 'relation', 'relation': edges, 'start': 0})
        program = {'seed': 'START', 'direction': 'FORWARD', 'merge': 'UNION', 'iteration': 'UNTIL_STABLE'}
        self.assertEqual(set(GenericRelationalMetaLanguageV1.execute(program, edges, 0)), set(range(32)))
        with self.assertRaisesRegex(ValueError, 'RELATION_EDGE_BUDGET'):
            GenericRelationalMetaLanguageV1.execute(program, edges + [[0, 1]], 0)

    def test_oscillation_remains_bounded(self):
        program = {'seed': 'START', 'direction': 'FORWARD', 'merge': 'REPLACE', 'iteration': 'UNTIL_STABLE'}
        with self.assertRaisesRegex(RuntimeError, 'STABLE_ITERATION_BUDGET'):
            GenericRelationalMetaLanguageV1.execute(program, [[0, 1], [1, 0]], 0)

    def test_boolean_function_is_included_with_both_outcomes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'example.py').write_text('def positive(value):\n    return value > 0\n')
            rows = discover_real_code_tasks(root, limit=1)
        self.assertEqual(rows[0]['function'], 'positive')
        self.assertEqual({value for _, value in rows[0]['rows']}, {True, False})
        self.assertGreaterEqual(len(rows[0]['rows']), 14)


if __name__ == '__main__':
    unittest.main()
