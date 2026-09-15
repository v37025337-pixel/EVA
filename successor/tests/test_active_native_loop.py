import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from successor.kernel import SuccessorKernel
from successor.cognitive import (CognitiveLoop, SOURCE_MEMORY_CAPACITY, goal_context,
                                 learned_sources, replay, validate_goal)
from successor.kernel import fingerprint

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


def reverse_goal():
    return {'domain': 'native_source',
            'training': [{'input': {'text': a}, 'expected': b}
                         for a, b in [('abc', 'cba'), ('def', 'fed'), ('gh', 'hg')]],
            'validation': [{'input': {'text': a}, 'expected': b}
                           for a, b in [('ijk', 'kji'), ('lm', 'ml')]],
            'queries': [{'input': {'text': 'nop'}}]}


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

    def test_older_program_survives_same_context_interference_and_restart(self):
        learned = self.run_goal(sequence_goal())
        unrelated = self.run_goal(reverse_goal(), budget=3)
        self.assertEqual(unrelated['status'], 'VALIDATED_ON_HOLDOUT')
        self.assertNotEqual(learned['result']['source_sha256'], unrelated['result']['source_sha256'])
        self.kernel.close()
        self.kernel = SuccessorKernel(MANIFEST, self.state)
        recalled = self.run_goal(sequence_goal(1), budget=1)
        self.assertEqual(recalled['status'], 'VALIDATED_ON_HOLDOUT')
        self.assertEqual(recalled['attempted'], ['reuse_verified_source'])
        self.assertEqual(recalled['result']['source_sha256'], learned['result']['source_sha256'])
        self.assertEqual(recalled['result']['predictions'], ['3O2P'])
        self.assertEqual(self.run_goal(sequence_goal(1), budget=1, mode='no_memory')['status'], 'WITHHOLD')

    def test_ambiguous_training_does_not_select_memory_using_holdout_labels(self):
        self.run_goal(sequence_goal())
        latest = self.run_goal(reverse_goal(), budget=3)
        ambiguous = sequence_goal(1)
        ambiguous['training'] = [{'input': {'text': x}, 'expected': x} for x in ['a', 'b', 'c']]
        result = self.run_goal(ambiguous, budget=1)
        self.assertEqual(result['status'], 'WITHHOLD')
        execution = next(r for r in self.kernel.recent(20)
                         if r['kind'] == 'COG_EXECUTE' and r['goal_id'] == result['id'])
        self.assertEqual(execution['result']['source_sha256'], latest['result']['source_sha256'])

    def test_recalled_source_provenance_rejects_tampered_search_and_unadmitted_links(self):
        self.run_goal(sequence_goal())
        self.run_goal(reverse_goal(), budget=3)
        recalled = self.run_goal(sequence_goal(1), budget=1)
        records = CognitiveLoop(self.kernel)._records()
        self.assertEqual(replay(records)[recalled['id']]['status'], 'VALIDATED_ON_HOLDOUT')
        mutations = [
            lambda r: r.update(reused_finish_tick=0),
            lambda r: r.update(reused_finish_tick=recalled['id']),
            lambda r: r.pop('memory_retrieval'),  # Legacy records can only reuse the newest source.
            lambda r: r['memory_retrieval'].update(version=3),
            lambda r: r['memory_retrieval'].update(training_digest='forged'),
            lambda r: r['memory_retrieval'].update(probes=[]),
            lambda r: r['memory_retrieval']['probes'].reverse(),
            lambda r: r['memory_retrieval']['probes'][0].update(finish_tick=recalled['id']),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(mutation=index):
                damaged = copy.deepcopy(records)
                execution = next(r for r in damaged if r['kind'] == 'COG_EXECUTE'
                                 and r['goal_id'] == recalled['id'])
                mutate(execution['result'])
                with self.assertRaisesRegex(ValueError, 'REUSE_PROVENANCE'):
                    replay(damaged)

    def test_legacy_newest_source_journal_remains_replayable(self):
        self.run_goal(sequence_goal())
        recalled = self.run_goal(sequence_goal(1), budget=1)
        records = CognitiveLoop(self.kernel)._records()
        for record in records:
            if record['kind'] in {'COG_EXECUTE', 'COG_FINISH'} and record.get('result'):
                record['result'].pop('memory_retrieval', None)
        self.assertEqual(replay(records)[recalled['id']]['result']['predictions'], ['3O2P'])

    def test_one_unusable_memory_does_not_hide_an_older_executable_program(self):
        self.run_goal(sequence_goal())
        latest = self.run_goal(reverse_goal(), budget=3)
        spec = sequence_goal(1)
        execute = self.kernel.parent.execute_native_source
        def fail_latest(candidate, inputs):
            if candidate['source_sha256'] == latest['result']['source_sha256']:
                raise ValueError('injected incompatible program')
            return execute(candidate, inputs)
        with patch.object(self.kernel.parent, 'execute_native_source', side_effect=fail_latest):
            result = self.run_goal(spec, budget=1)
        self.assertEqual(result['status'], 'VALIDATED_ON_HOLDOUT')
        self.assertEqual(result['result']['predictions'], ['3O2P'])
        self.assertEqual(result['result']['memory_retrieval']['probes'][0]['error_type'], 'ValueError')

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


class SourceMemoryBoundaryTests(unittest.TestCase):
    def test_search_is_bounded_deduplicated_and_excludes_other_contexts_and_failures(self):
        goal = {'spec': sequence_goal(), 'mode': 'full'}
        records = [{'kind': 'COG_FINISH', 'tick': i + 1, 'status': 'VALIDATED_ON_HOLDOUT',
                    'result': {'source': str(i), 'source_sha256': fingerprint(i),
                               'source_context': goal_context(goal['spec'])}}
                   for i in range(SOURCE_MEMORY_CAPACITY + 2)]
        records.append({**records[-1], 'tick': 100})
        records.append({**records[-2], 'tick': 101, 'status': 'WITHHOLD'})
        records.append({**records[0], 'tick': 102,
                        'result': {**records[0]['result'], 'source_context': 'other'}})
        pool = learned_sources(records, goal)
        self.assertEqual(len(pool), SOURCE_MEMORY_CAPACITY)
        self.assertEqual(pool[0]['tick'], 100)
        self.assertEqual(len({r['result']['source_sha256'] for r in pool}), SOURCE_MEMORY_CAPACITY)
        self.assertTrue(all(r['tick'] not in {1, 2, 101, 102} for r in pool))
        self.assertEqual(learned_sources(records, {**goal, 'mode': 'no_memory'}), [])
