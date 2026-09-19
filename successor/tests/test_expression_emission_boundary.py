"""The two eval sites consume fixed templates with quoted JSON input keys."""
import unittest

from successor.generalized_boolean_v2 import synthesize_boolean_candidate_v2
from successor.generalized_source_v2 import synthesize_candidate_v2
from yado_active_native_learning_v1 import execute_source


class ExpressionEmissionBoundaryTests(unittest.TestCase):
    def test_boolean_eval_quotes_input_names_and_enforces_integer_budget(self):
        key = "x']; 1 / 0; #"
        rows = [{'input': {key: x}, 'expected': x < 0} for x in (-2, 0, 3)]
        candidate = synthesize_boolean_candidate_v2(rows)
        self.assertEqual(execute_source(candidate, [row['input'] for row in rows]), [True, False, False])
        for value in (True, '1', 1000001):
            rows[0]['input'][key] = value
            with self.assertRaisesRegex(ValueError, 'INTEGER_INPUTS_ONLY'):
                synthesize_boolean_candidate_v2(rows)

    def test_generalized_eval_quotes_input_names_and_enforces_integer_budget(self):
        key = "x']; 1 / 0; #"
        rows = [{'input': {key: x}, 'expected': x ^ 1} for x in (-2, 0, 3)]
        candidate = synthesize_candidate_v2(rows)
        self.assertEqual(execute_source(candidate, [row['input'] for row in rows]), [-1, 1, 2])
        for value in (True, '1', 1000001):
            rows[0]['input'][key] = value
            with self.assertRaisesRegex(ValueError, 'INTEGER_INPUTS_ONLY'):
                synthesize_candidate_v2(rows)


if __name__ == '__main__':
    unittest.main()
