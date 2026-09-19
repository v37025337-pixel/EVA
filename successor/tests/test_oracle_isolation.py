"""Downloaded expression oracles must stay inside bounded worker execution."""
import time
import unittest
from unittest.mock import patch

import yado_isolated_program_executor_v1 as executor
from successor.real_coding_intelligence_run import _compile_oracle
from successor.second_cycle_baseline_v2 import _compile_extended


class OracleIsolationTests(unittest.TestCase):
    def test_definition_side_effects_are_rejected_before_execution(self):
        sources = (
            "1 / 0\ndef solve(x):\n    return x + 1\n",
            "def solve(x=1 / 0):\n    return x + 1\n",
            "@(1 / 0)\ndef solve(x):\n    return x + 1\n",
            "def solve(x: 1 / 0):\n    return x + 1\n",
            "def solve(x) -> 1 / 0:\n    return x + 1\n",
        )
        for compiler in (_compile_oracle, _compile_extended):
            for source in sources:
                with self.subTest(compiler=compiler.__name__, source=source):
                    with self.assertRaises(ValueError), patch.object(executor, 'execute') as execute:
                        compiler(source)
                    execute.assert_not_called()

    def test_ordinary_oracles_use_worker_and_preserve_values(self):
        with patch.object(executor, 'execute', wraps=executor.execute) as execute:
            self.assertEqual(_compile_oracle('def solve(x):\n    return x * 3 + 1\n')(7), 22)
            self.assertEqual(_compile_extended('def solve(x,y):\n    return max(abs(x), y)\n')(-9, 4), 9)
            self.assertEqual(execute.call_count, 2)

    def test_unbounded_power_is_contained_in_worker_and_recovers(self):
        oracle = _compile_extended('def solve(n):\n    return 2 ** (2 ** n)\n')
        with patch.object(executor, 'execute', wraps=executor.execute) as execute:
            self.assertEqual(oracle(4), 65536)
            # This assertion also keeps the unfixed implementation's red test
            # from ever evaluating the large expression in the parent process.
            self.assertEqual(execute.call_count, 1, 'oracle must use bounded worker')
            start = time.monotonic()
            with self.assertRaises((MemoryError, TimeoutError, RuntimeError, OverflowError, ValueError)):
                oracle(32)
            self.assertLess(time.monotonic() - start, 3.0)
        self.assertEqual(_compile_extended('def solve(x):\n    return x + 1\n')(41), 42)

    def test_unknown_calls_and_attributes_are_rejected(self):
        for source in ("def solve(x):\n    return open(x)\n", "def solve(x):\n    return x.__class__\n"):
            for compiler in (_compile_oracle, _compile_extended):
                with self.subTest(compiler=compiler.__name__, source=source), self.assertRaises(ValueError):
                    compiler(source)


if __name__ == '__main__':
    unittest.main()
