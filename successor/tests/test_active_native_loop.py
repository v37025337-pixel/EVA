import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from successor.kernel import SuccessorKernel
from successor.cognitive import validate_goal

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(os.environ.get('YADO_SUCCESSOR_TEST_MANIFEST', ROOT / 'successor/state/birth-v2/manifest.json'))


def sequence_goal(variant=0):
    # Examples and answers are explicit task requirements, independent of the
    # native implementation's training evaluator.
    pairs = ([('AAA', '3A'), ('BBCC', '2B2C'), ('D', 'D')], [('EEEE', '4E'), ('FFG', '2FG')])
    if variant:
        pairs = ([('HHH', '3H'), ('IIJJ', '2I2J'), ('K', 'K')], [('LLLL', '4L'), ('MMN', '2MN')])
    return {'domain': 'native_source',
            'training': [{'input': {'text': a}, 'expected': b} for a, b in pairs[0]],
            'validation': [{'input': {'text': a}, 'expected': b} for a, b in pairs[1]],
            'queries': [{'input': {'text': 'OOOPP' if variant else 'AABBBBB'}}]}


class ActiveNativeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = Path(self.tmp.name) / 'state.sqlite'
        self.kernel = SuccessorKernel(MANIFEST, self.state)

    def tearDown(self):
        self.kernel.close()
        self.tmp.cleanup()

    def run_goal(self, spec, budget=6, mode='full'):
        goal = self.kernel.open_goal(spec, budget=budget, mode=mode)
        self.kernel.think(40)
        return self.kernel.cognitive_snapshot()['goals'][str(goal)]

    def test_failure_extends_grammar_and_source_is_reused_after_restart(self):
        first = self.run_goal(sequence_goal())
        self.assertEqual(first['attempted'], ['native_v2', 'native_v3'])
        self.assertEqual(first['status'], 'VALIDATED_ON_HOLDOUT')
        self.assertEqual(first['result']['predictions'], ['2A5B'])
        self.kernel.close()
        self.kernel = SuccessorKernel(MANIFEST, self.state)
        second = self.run_goal(sequence_goal(1), budget=1)
        self.assertEqual(second['attempted'], ['reuse_verified_source'])
        self.assertEqual(second['result']['predictions'], ['3O2P'])
        self.assertEqual(second['result']['source_sha256'], first['result']['source_sha256'])
        self.assertEqual(second['result']['reused_finish_tick'], next(
            r['tick'] for r in self.kernel.recent(100) if r['kind'] == 'COG_FINISH' and r['goal_id'] == first['id']))
        ablated = self.run_goal(sequence_goal(1), budget=1, mode='no_memory')
        self.assertEqual(ablated['status'], 'WITHHOLD')

    def test_v4_meta_rule_follows_two_failed_grammar_routes(self):
        spec = {'domain': 'native_source',
                'training': [{'input': {'number': n}, 'expected': a} for n, a in [(2, True), (3, False), (12, True), (11, False)]],
                'validation': [{'input': {'number': n}, 'expected': a} for n, a in [(100, True), (101, False)]],
                'queries': [{'input': {'number': 998}}, {'input': {'number': 999}}]}
        result = self.run_goal(spec)
        self.assertEqual(result['attempted'], ['native_v2', 'native_v3', 'native_v4'])
        self.assertEqual(result['status'], 'VALIDATED_ON_HOLDOUT')
        self.assertEqual(result['result']['predictions'], [True, False])
        self.assertEqual(result['result']['grammar_stage'], 'V4')

    def test_bad_validation_does_not_admit_training_only_success(self):
        spec = sequence_goal()
        spec['validation'][0]['expected'] = 'incorrect'
        result = self.run_goal(spec)
        self.assertEqual(result['status'], 'WITHHOLD')
        self.assertIsNone(result['result'])
        new = self.run_goal(sequence_goal(1), budget=1)
        self.assertNotIn('reuse_verified_source', new['attempted'])

    def test_previous_source_must_fit_new_task_before_reuse_admission(self):
        self.run_goal(sequence_goal())
        spec = {'domain': 'native_source',
                'training': [{'input': {'text': a}, 'expected': b} for a, b in [('abc', 'cba'), ('def', 'fed'), ('gh', 'hg')]],
                'validation': [{'input': {'text': a}, 'expected': b} for a, b in [('ijk', 'kji'), ('lm', 'ml')]],
                'queries': [{'input': {'text': 'nop'}}]}
        result = self.run_goal(spec, budget=3)
        self.assertEqual(result['attempted'], ['reuse_verified_source', 'native_v3'])
        self.assertEqual(result['status'], 'VALIDATED_ON_HOLDOUT')
        self.assertEqual(result['result']['predictions'], ['pon'])

    def test_synthesizer_never_receives_validation_labels(self):
        spec = sequence_goal()
        original = self.kernel.parent.native_source_candidate
        received = []
        def observe(training, strategy):
            received.append(copy.deepcopy(training))
            return original(training, strategy)
        with patch.object(self.kernel.parent, 'native_source_candidate', side_effect=observe):
            self.run_goal(spec)
        self.assertTrue(received)
        self.assertTrue(all(rows == spec['training'] for rows in received))

    def test_restart_between_source_freeze_and_independent_validation(self):
        goal = self.kernel.open_goal(sequence_goal(), mode='fixed_max')
        events = self.kernel.think(2)
        self.assertEqual([e['kind'] for e in events], ['COG_DECIDE', 'COG_EXECUTE'])
        frozen = events[-1]['result']['source_sha256']
        self.kernel.close()
        self.kernel = SuccessorKernel(MANIFEST, self.state)
        rest = self.kernel.think(10)
        self.assertEqual(rest[0]['kind'], 'COG_VERIFY')
        self.assertEqual(rest[0]['evidence']['source_sha256'], frozen)
        self.assertEqual(self.kernel.cognitive_snapshot()['goals'][str(goal)]['status'], 'VALIDATED_ON_HOLDOUT')

    def test_library_network_failure_is_recorded_and_terminates(self):
        with patch.object(self.kernel.parent, 'native_library_candidate', side_effect=OSError('offline')):
            result = self.run_goal({'domain': 'library_discovery', 'objective': 'html_xml_parser'}, budget=4)
        self.assertEqual(result['status'], 'WITHHOLD')
        self.assertEqual(result['attempted'], ['catalog_v6'])
        failures = [r for r in self.kernel.recent(30) if r['kind'] == 'COG_EXECUTE']
        self.assertEqual(failures[0]['result']['error_type'], 'OSError')

    def test_partition_leak_and_code_inputs_are_rejected(self):
        spec = sequence_goal()
        spec['validation'][0] = copy.deepcopy(spec['training'][0])
        with self.assertRaisesRegex(ValueError, 'DISTINCT_INPUTS'):
            validate_goal(spec)
        spec = sequence_goal()
        spec['source'] = 'print(1)'
        with self.assertRaises(ValueError):
            validate_goal(spec)
