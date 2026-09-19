import copy
import unittest

from successor.cognitive import validate_goal, available_strategies
from successor.program_goals import SCHEMA


def structured_goal():
    return {'schema': SCHEMA, 'domain': 'native_source',
            'training': [{'input': {'record': {'label': label, 'items': [index]}},
                          'expected': {'label': label}} for index, label in enumerate(['a', 'b', 'c'])],
            'validation': [{'input': {'record': {'label': label, 'items': [index]}},
                            'expected': {'label': label}} for index, label in enumerate(['d', 'e'])],
            'queries': [{'input': {'record': {'label': 'f', 'items': [9]}}}]}


class ProgramGoalContractTests(unittest.TestCase):
    def test_structured_examples_have_explicit_additive_schema(self):
        goal = structured_goal()
        self.assertEqual(validate_goal(goal), goal)
        self.assertIsNot(validate_goal(goal), goal)
        del goal['schema']
        with self.assertRaises(ValueError):
            validate_goal(goal)

    def test_unlabelled_queries_and_partition_isolation(self):
        value = structured_goal()
        value['queries'][0]['expected'] = {'label': 'f'}
        with self.assertRaises(ValueError):
            validate_goal(value)
        value = structured_goal()
        value['validation'][0]['input'] = copy.deepcopy(value['training'][0]['input'])
        with self.assertRaisesRegex(ValueError, 'DISTINCT'):
            validate_goal(value)

    def test_floats_custom_objects_large_trees_and_cycles_rejected(self):
        cycle = []
        cycle.append(cycle)
        for bad in (float('nan'), 1.2, object(), [list(range(128)) for _ in range(128)], cycle):
            with self.subTest(type=type(bad).__name__):
                value = structured_goal()
                value['training'][0]['input']['record']['items'] = bad
                with self.assertRaises(ValueError):
                    validate_goal(value)

    def test_unsupported_schema_and_type_drift_rejected(self):
        value = structured_goal()
        value['schema'] += '.unknown'
        with self.assertRaises(ValueError):
            validate_goal(value)
        value = structured_goal()
        value['validation'][0]['input']['record'] = 'different type'
        with self.assertRaisesRegex(ValueError, 'SIGNATURE'):
            validate_goal(value)

    def test_structured_goals_require_explicit_generator_activation(self):
        goal = {'spec': structured_goal(), 'mode': 'full'}
        self.assertEqual(available_strategies(goal, []), [])


if __name__ == '__main__':
    unittest.main()
