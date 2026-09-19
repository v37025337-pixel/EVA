from __future__ import annotations

from fractions import Fraction
import os
import signal
import time
import unittest
from unittest.mock import patch

from yado_bounded_compositional_program_repair_v3 import BoundedCompositionalProgramRepairV3 as Repair
from yado_ambiguity_aware_program_repair_v11 import AmbiguityAwareProgramRepairV11
import yado_isolated_program_executor_v1 as executor


class ProgramRepairIsolationTests(unittest.TestCase):
    def test_boolean_oracle_rejects_numeric_one_and_nested_aliases(self):
        for source, expected in (("return 1", True), ("return [1]", [True]),
                                 ("return {'answer': (1,)}", {"answer": [True]}),
                                 ("return {1: 'x'}", {True: 'x'})):
            with self.subTest(source=source):
                self.assertFalse(Repair._passes("def f():\n    " + source + "\n", "f", [((), expected)]))

    def test_supported_sequence_equivalence_and_actual_booleans(self):
        self.assertTrue(Repair._passes("def f():\n    return {'answer': (True, 2)}\n", "f",
                                       [((), {"answer": [True, 2]})]))

    def test_unchanged_boolean_alias_is_not_admitted_as_repair(self):
        result = Repair.repair("def f(x):\n    return 1\n", "f", [((0,), True)],
                               max_candidates=1, enabled=())
        self.assertIsNone(result["source"])
        result = AmbiguityAwareProgramRepairV11.repair(
            "def f(x):\n    return 1\n", "f", [((0,), True), ((1,), True)], max_candidates=1)
        if result.get("source"):
            self.assertIs(Repair.execute(result["source"], "f", (99,)), True)

    def test_real_cpu_limit_and_recovery(self):
        source = "def f(xs):\n    return sum(a * b for a in xs for b in xs for c in xs)\n"
        start = time.monotonic()
        with self.assertRaises((TimeoutError, RuntimeError)):
            Repair.execute(source, "f", (list(range(1000)),))
        self.assertLess(time.monotonic() - start, 3.0)
        self.assertEqual(Repair.execute("def f(x):\n    return x + 2\n", "f", (40,)), 42)

    def test_real_memory_limit_and_recovery(self):
        start = time.monotonic()
        with self.assertRaises((MemoryError, RuntimeError, TimeoutError)):
            Repair.execute("def f():\n    return [0] * 1000000000\n", "f", ())
        self.assertLess(time.monotonic() - start, 3.0)
        self.assertEqual(Repair.execute("def f():\n    return 7\n", "f", ()), 7)

    def test_wall_deadline_kills_a_stalled_process_without_threads(self):
        self.assertEqual(Repair.execute("def f():\n    return 1\n", "f", ()), 1)
        process = executor._EXECUTOR.process
        os.kill(process.pid, signal.SIGSTOP)
        with patch.object(executor, "WALL_SECONDS", 0.1):
            with self.assertRaisesRegex(TimeoutError, "WALL_LIMIT"):
                Repair.execute("def f():\n    return 2\n", "f", ())
        self.assertIsNotNone(process.returncode)
        self.assertEqual(Repair.execute("def f():\n    return 3\n", "f", ()), 3)

    def test_existing_builtin_extension_is_preserved(self):
        class Extended(Repair):
            SAFE_CALLS = dict(Repair.SAFE_CALLS, int=int, float=float, str=str)
        self.assertEqual(Extended.execute("def f(x):\n    return int(x)\n", "f", ("42",)), 42)
        self.assertNotIn("int", Repair.SAFE_CALLS)

    def test_argument_objects_and_mutation_do_not_cross_process_boundary(self):
        class CallerObject:
            def __add__(self, other):
                raise AssertionError("caller object executed")
        with self.assertRaisesRegex(ValueError, "VALUE_TYPE_NOT_ALLOWED"):
            Repair.execute("def f(x):\n    return x + 1\n", "f", (CallerObject(),))
        data = [1, 2]
        result = Repair.execute("def f(xs):\n    xs[0] = 99\n    return xs\n", "f", (data,))
        self.assertEqual(result, [99, 2])
        self.assertEqual(data, [1, 2])

    def test_worker_reuse_has_no_globals_or_mutable_default_leak(self):
        source = "def f(xs=[0]):\n    xs[0] += 1\n    return xs[0]\n"
        self.assertEqual(Repair.execute(source, "f", ()), 1)
        worker = executor._EXECUTOR.process.pid
        for _ in range(100):
            self.assertEqual(Repair.execute(source, "f", ()), 1)
        self.assertEqual(executor._EXECUTOR.process.pid, worker)

    def test_typed_values_survive_and_errors_remain_errors(self):
        original = {2: (Fraction(3, 4), True), "values": [b"bytes", {3, 4}], "number": 2 + 3j}
        actual = Repair.execute("def f(x):\n    return x\n", "f", (original,))
        self.assertEqual(actual, original)
        self.assertIsInstance(actual[2], tuple)
        with self.assertRaises(ZeroDivisionError):
            Repair.execute("def f(x):\n    return 1 / x\n", "f", (0,))

    def test_positive_repair_still_transfers_to_unseen_values(self):
        result = Repair.repair("def f(x):\n    return x + 1\n", "f",
                               [((0,), 2), ((1,), 3), ((2,), 4)], max_candidates=200)
        self.assertIsNotNone(result["source"])
        for value in (-91, 17, 103):
            self.assertEqual(Repair.execute(result["source"], "f", (value,)), value + 2)

    def test_unsupported_source_output_and_cycles_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "SOURCE_BUDGET"):
            Repair.execute(" " * (executor.MAX_SOURCE_BYTES + 1), "f", ())
        with self.assertRaisesRegex(ValueError, "SCALAR_BUDGET"):
            Repair.execute("def f():\n    return 'x' * 300000\n", "f", ())
        cyclic = []
        cyclic.append(cyclic)
        with self.assertRaisesRegex(ValueError, "VALUE_BUDGET"):
            Repair.execute("def f(x):\n    return x\n", "f", (cyclic,))
        with self.assertRaisesRegex(ValueError, "VALUE_BUDGET"):
            Repair.execute("def f(x):\n    return x\n", "f", (["x" * 100000] * 1000,))


if __name__ == "__main__":
    unittest.main()
