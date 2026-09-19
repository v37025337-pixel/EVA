"""Independent behavior and execution-boundary tests for compositional source."""
import ast
import copy
import difflib
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import subprocess
import unittest
from unittest.mock import patch

from successor import compositional_source as engine


ROOT = Path(__file__).resolve().parents[2]


def examples(values, function, key='text'):
    return [{'input': {key: x}, 'expected': function(x)} for x in values]


def json_text(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


class CompositionalSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / 'experiments/native-gap-repair-20260919/run.py'
        spec = importlib.util.spec_from_file_location('recorded_gap_fixtures', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls.recorded = module.fixtures()
        cls.candidates = {task['name']: engine.synthesize(task['spec']['training']) for task in cls.recorded}

    def candidate(self, name='mcp_comment_serialization'):
        return copy.deepcopy(self.candidates[name])

    def test_recorded_failures_pass_unchanged_holdout_and_queries(self):
        for task in self.recorded:
            with self.subTest(task=task['name']):
                candidate = self.candidate(task['name'])
                engine.validate(candidate)
                validation = task['spec']['validation']
                self.assertEqual(engine.execute(candidate, [r['input'] for r in validation]),
                                 [r['expected'] for r in validation])
                self.assertEqual(engine.execute(candidate, [r['input'] for r in task['spec']['queries']]),
                                 task['observer_query_expected'])

    def test_json_shape_is_inferred_for_unrelated_protocol_and_nested_lists(self):
        def oracle(text):
            return json_text({'api': 'example/v9', 'jobs': [{'value': text, 'enabled': True}], 'unused': None})
        candidate = engine.synthesize(examples(['one', 'two', 'three'], oracle))
        fresh = ['', 'a"b\\c\n\x00', 'Україна 😀', ' __import__("os").system("false") ']
        self.assertEqual(engine.execute(candidate, [{'text': x} for x in fresh]), [oracle(x) for x in fresh])
        self.assertNotIn('hive', candidate['source'])

    def test_unicode_and_ascii_serialization_are_distinct_candidates(self):
        for ensure_ascii in (False, True):
            def oracle(text):
                return json.dumps({'payload': text}, ensure_ascii=ensure_ascii, separators=(',', ':'))
            candidate = engine.synthesize(examples(['один', 'два', 'три'], oracle))
            self.assertEqual(engine.execute(candidate, [{'text': '😀 "новое"'}]), [oracle('😀 "новое"')])

    def test_structured_inputs_outputs_and_field_projection(self):
        training = [{'input': {'payload': {'name': x, 'count': n}},
                     'expected': {'clean': x.strip().lower(), 'count': n, 'flags': [True, None]}}
                    for x, n in [('  ALPHA ', 2), ('BETA ', 7), (' gamma', 11)]]
        candidate = engine.synthesize(training)
        self.assertEqual(engine.execute(candidate, [{'payload': {'name': ' ДЕЛЬТА ', 'count': 19}}]),
                         [{'clean': 'дельта', 'count': 19, 'flags': [True, None]}])

    def test_json_decoding_can_feed_string_normalization(self):
        candidate = engine.synthesize(examples(['" A "', '"B "', '" c"'], lambda x: json.loads(x).strip().lower()))
        self.assertEqual(engine.execute(candidate, [{'text': '" ДАННЫЕ "'}]), ['данные'])

    def test_diff_uses_inferred_paths_and_patch_really_applies(self):
        old, new = 'a/module.py', 'b/module.py'
        def oracle(before, after):
            return ''.join(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True),
                                              fromfile=old, tofile=new))
        training = [{'input': {'before': a, 'after': b}, 'expected': oracle(a, b)} for a, b in
                    [('x=1\n', 'x=2\n'), ('foo=4\nbar=5\n', 'foo=4\n'), ('print(1)\n', 'print(2)\n')]]
        candidate = engine.synthesize(training)
        before, after = 'title = "старое"\nx = 9\n', 'title = "новое"\nx = 9\ny = 10\n'
        patch_text = engine.execute(candidate, [{'before': before, 'after': after}])[0]
        self.assertEqual(patch_text, oracle(before, after))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / 'module.py').write_text(before)
            subprocess.run(['git', 'apply', '--check', '-'], input=patch_text, text=True, cwd=path, check=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(['git', 'apply', '-'], input=patch_text, text=True, cwd=path, check=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual((path / 'module.py').read_text(), after)

    def test_diff_identity_insertion_deletion_and_no_final_newline_follow_declared_library_contract(self):
        candidate = self.candidate('unified_patch_emission')
        for before, after in [('', 'new\n'), ('old\n', ''), ('same\n', 'same\n'), ('old', 'new')]:
            expected = ''.join(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True),
                                                  fromfile='a/target.py', tofile='b/target.py'))
            self.assertEqual(engine.execute(candidate, [{'before': before, 'after': after}]), [expected])

    def test_ast_projection_ignores_metadata_and_formatting_but_detects_function_changes(self):
        candidate = self.candidate('function_ast_change_detection')
        cases = [
            ('PACK_DIGEST="a"\ndef f(x):\n return x+1\n', 'PACK_DIGEST="b"\ndef f(x):\n    return x + 1\n', False),
            ('x=1\n', 'x=9\n', False),
            ('async def f(x):\n return x\n', 'async def f(x):\n return x+1\n', True),
            ('def f(x):\n return x\n', '@decorator\ndef f(x):\n return x\n', True),
            ('def f(x):\n return x\n', 'def f(x):\n "doc"\n return x\n', True),
        ]
        for before, after, expected in cases:
            self.assertEqual(engine.execute(candidate, [{'before': before, 'after': after}]), [expected])
        with self.assertRaises(SyntaxError):
            engine.execute(candidate, [{'before': 'invalid python @ !', 'after': 'x=1'}])

    def test_memory_is_inlined_renamed_and_composed_with_new_structure(self):
        parent = engine.synthesize(examples(['  ALPHA  ', ' beta ', '\tGaMmA\n'], lambda x: x.strip().lower()))
        def oracle(x):
            return json_text({'kind': 'echo', 'result': x.strip().lower()})
        training = examples(['  Delta ', '\nEPSILON\t', 'ZETA '], oracle, 'payload')
        child = engine.synthesize(training, memories=[parent])
        self.assertEqual(child['parent_source_sha256'], [parent['source_sha256']])
        self.assertEqual(engine.execute(child, [{'payload': ' НОВОЕ 😀\n'}]), [oracle(' НОВОЕ 😀\n')])
        self.assertIn('lower', child['source'])
        self.assertNotIn("inputs, 'text'", child['source'])
        self.assertEqual(child, engine.synthesize(training, memories=[parent]))
        no_memory = engine.synthesize(training)
        self.assertEqual(no_memory['parent_source_sha256'], [])

    def test_memory_can_cross_output_type_without_false_parent_claims(self):
        parent = self.candidate()
        values = ['plain', '"quoted"', '\nnewline']
        training = [{'input': {'message': x}, 'expected': len(engine.execute(parent, [{'message': x}])[0])}
                    for x in values]
        child = engine.synthesize(training, memories=[parent])
        self.assertEqual(child['parent_source_sha256'], [parent['source_sha256']])
        self.assertEqual(engine.execute(child, [{'message': '\\新\t😀'}]),
                         [len(engine.execute(parent, [{'message': '\\新\t😀'}])[0])])
        unrelated = engine.synthesize(examples([' A ', 'B ', ' C'], lambda x: x.strip().lower()), memories=[parent])
        self.assertEqual(unrelated['parent_source_sha256'], [])

    def test_source_spoofing_with_updated_digest_is_rejected(self):
        candidate = self.candidate()
        candidate['source'] = 'import os\n' + candidate['source']
        candidate['source_sha256'] = hashlib.sha256(candidate['source'].encode()).hexdigest()
        with self.assertRaisesRegex(ValueError, 'REEMISSION'):
            engine.execute(candidate, [{'message': 'safe'}])

    def test_unknown_primitive_and_malformed_ir_are_rejected(self):
        invalid = [
            {'op': 'call', 'name': '__import__', 'args': [{'op': 'literal', 'value': 'os'}]},
            {'op': 'input', 'key': "x'); __import__('os'); #"},
            {'op': 'literal', 'value': {'source': 'bad'}},
            {'op': 'object', 'items': [['x', {'op': 'literal', 'value': 1}], ['x', {'op': 'literal', 'value': 2}]]},
            {'op': 'call', 'name': 'lower', 'args': []},
            {'op': 'call', 'name': 'lower', 'args': [{'op': 'literal', 'value': 1}]},
        ]
        for program in invalid:
            with self.subTest(program=program):
                candidate = self.candidate()
                candidate['program'] = program
                with self.assertRaises(ValueError):
                    engine.validate(candidate)

    def test_invalid_memory_never_becomes_an_execution_seed(self):
        parent = self.candidate()
        parent['source'] = "raise RuntimeError('should not execute')\n"
        parent['source_sha256'] = hashlib.sha256(parent['source'].encode()).hexdigest()
        with self.assertRaisesRegex(ValueError, 'REEMISSION'):
            engine.synthesize(examples(['a', 'b', 'c'], str.upper), memories=[parent])

    def test_global_value_and_program_budgets_reject_cycles_and_shared_large_trees(self):
        cycle = []
        cycle.append(cycle)
        huge = [[0] * 128] * 128
        for value in (cycle, huge, 'x' * (engine.MAX_TEXT + 1), 1.2, float('nan'), '\ud800'):
            with self.subTest(value_type=type(value).__name__):
                result = engine.synthesize([{'input': {'x': value}, 'expected': n} for n in (1, 2, 3)])
                self.assertEqual(result['status'], 'WITHHOLD')
        candidate = self.candidate()
        program = {'op': 'input', 'key': 'message'}
        for _ in range(engine.MAX_DEPTH + 1):
            program = {'op': 'call', 'name': 'strip', 'args': [program]}
        candidate['program'] = program
        with self.assertRaisesRegex(ValueError, 'PROGRAM_BUDGET'):
            engine.validate(candidate)

    def test_search_budget_is_a_withhold_not_a_solution(self):
        with patch.object(engine, 'MAX_ATTEMPTS', 1):
            result = engine.synthesize(examples(['a', 'b', 'c'], str.upper))
        self.assertEqual(result['status'], 'WITHHOLD')
        self.assertEqual(result['reason'], 'COMPOSITION_SEARCH_BUDGET')
        self.assertIsNone(result['source'])

    def test_candidate_selection_does_not_accept_holdout_or_source_fields(self):
        rows = examples(['a', 'b', 'c'], str.upper)
        rows[0]['source'] = 'not accepted'
        self.assertEqual(engine.synthesize(rows)['status'], 'WITHHOLD')
        with self.assertRaises(TypeError):
            engine.synthesize(examples(['a', 'b', 'c'], str.upper), validation=[])

    def test_type_boundaries_distinguish_bool_and_int_and_reject_wrong_execution_inputs(self):
        candidate = self.candidate()
        for row in ({'message': 1}, {'message': 'a', 'extra': 'b'}, {}):
            with self.assertRaises(ValueError):
                engine.execute(candidate, [row])
        self.assertNotEqual(engine._freeze(True), engine._freeze(1))

    def test_catalog_is_detached_and_describes_limits_without_mutating_registry(self):
        first = engine.catalog()
        first['operators'][0]['name'] = 'tampered'
        self.assertNotEqual(first, engine.catalog())
        self.assertFalse(engine.catalog()['new_primitive_invention'])


if __name__ == '__main__':
    unittest.main()
