import unittest

from successor.native_binding import STRATEGY, synthesize
from yado_active_native_learning_v1 import execute_source


def rows(function, xs=range(-5, 6)):
    return [{'input': {'x': x}, 'expected': function(x)} for x in xs]


class InductiveNativeBindingTests(unittest.TestCase):
    def test_predecessor_route_still_wins_when_it_has_a_source(self):
        result = synthesize(rows(lambda x: x * x + 2 * x + 3))
        self.assertTrue(result.get('source'))
        self.assertEqual(result['binding_strategy'], STRATEGY)
        self.assertEqual(result['binding_route'], 'EVOLVED_V2')
        self.assertEqual(execute_source(result, [{'x': x} for x in (-11, -4, 7, 13)]),
                         [x * x + 2 * x + 3 for x in (-11, -4, 7, 13)])

    def test_exhausted_predecessor_deficit_flows_into_inductive_route(self):
        training = rows(abs)
        result = synthesize(training)
        self.assertTrue(result.get('source'))
        self.assertEqual(result['binding_strategy'], STRATEGY)
        self.assertEqual(result['binding_route'], 'INDUCTIVE_V1')
        self.assertEqual(result['inductive_profile']['primitive_set'],
                         ['var', 'const', 'neg', 'lt', 'if'])
        self.assertEqual(result['inductive_profile']['max_nodes'], 7)
        self.assertEqual(result['mechanism_source_sha256'], result['inductive_mechanism_sha256'])
        self.assertEqual(execute_source(result, [{'x': x} for x in (-19, -8, -1, 0, 4, 17)]),
                         [19, 8, 1, 0, 4, 17])


if __name__ == '__main__':
    unittest.main()
