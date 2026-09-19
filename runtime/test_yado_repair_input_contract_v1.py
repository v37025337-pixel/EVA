import unittest
from unittest.mock import patch

import yado_bounded_compositional_program_repair_v3 as base
from yado_ambiguity_aware_program_repair_v11 import AmbiguityAwareProgramRepairV11


class RepairInputContractTests(unittest.TestCase):
    CLASSES = (base.BoundedCompositionalProgramRepairV3, AmbiguityAwareProgramRepairV11)

    def test_oversized_source_is_rejected_before_host_ast_parsing(self):
        for cls in self.CLASSES:
            for suffix in ('a' * base.MAX_SOURCE_BYTES, 'я' * (base.MAX_SOURCE_BYTES // 2)):
                source = 'def f(x):\n    return x+1\n#' + suffix
                with self.subTest(cls=cls.__name__, unicode=suffix[0]), \
                        patch.object(base.ast, 'parse', wraps=base.ast.parse) as parse:
                    with self.assertRaisesRegex(ValueError, 'PROGRAM_SOURCE_BUDGET'):
                        cls.repair(source, 'f', [((0,), 2), ((1,), 3)], max_candidates=100)
                    parse.assert_not_called()

    def test_empty_training_cannot_return_an_unexecuted_candidate(self):
        for cls in self.CLASSES:
            for source in ('def f(x):\n    return x\n', '@abs\ndef f(x):\n    return x\n'):
                with self.subTest(cls=cls.__name__, source=source):
                    with self.assertRaisesRegex(ValueError, 'REPAIR_TRAINING_EXAMPLES_REQUIRED'):
                        cls.repair(source, 'f', [], max_candidates=10)

    def test_verification_with_no_observations_is_false(self):
        for cls in self.CLASSES:
            self.assertFalse(cls._passes('def f():\n    return 1 / 0\n', 'f', []))
            self.assertFalse(cls._passes('def f():\n    return 1 / 0\n', 'f', iter(())))

    def test_one_shot_or_malformed_training_is_rejected(self):
        values = (iter([((0,), 1)]), None, [()], [((0,),)], [(0, 1)], 'examples')
        for cls in self.CLASSES:
            for examples in values:
                with self.subTest(cls=cls.__name__, examples=repr(examples)):
                    with self.assertRaisesRegex(ValueError, 'REPAIR_TRAINING_'):
                        cls.repair('def f(x):\n    return x + 1\n', 'f', examples, max_candidates=5)

    def test_requested_function_must_exist_before_search(self):
        for cls in self.CLASSES:
            with self.subTest(cls=cls.__name__), self.assertRaisesRegex(ValueError, 'FUNCTION_NAME_MISMATCH'):
                cls.repair('def other(x):\n    return x\n', 'f', [((1,), 1)], max_candidates=1)

    def test_nonempty_examples_preserve_no_change_and_real_repair(self):
        source = 'def f(x):\n    return x + 1\n'
        for cls in self.CLASSES:
            with self.subTest(cls=cls.__name__):
                unchanged = cls.repair(source, 'f', [((0,), 1), ((1,), 2)], max_candidates=100)
                self.assertEqual(unchanged['source'], source)
                self.assertEqual(unchanged['tried'], 0)
                repaired = cls.repair(source, 'f', (((0,), 2), ((1,), 3)), max_candidates=100)
                self.assertIsNotNone(repaired['source'])
                self.assertEqual(cls.execute(repaired['source'], 'f', (41,)), 43)


if __name__ == '__main__':
    unittest.main()
