"""Public-loop regression for versioned synthesis, memory, and old evidence."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

from successor.cognitive import replay
from successor.kernel import SuccessorKernel, decode, encode


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(os.environ.get('YADO_SUCCESSOR_TEST_MANIFEST',
                              ROOT / 'successor/state/birth-v2/manifest.json'))
STRATEGY = 'native_compositional_v1'


def gap_tasks():
    path = ROOT / 'experiments/native-gap-repair-20260919/run.py'
    spec = importlib.util.spec_from_file_location('compositional_gap_fixtures', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.fixtures()


def rehash(records):
    """A changed journal body must still fail after all advertised hashes agree."""
    previous = '0' * 64
    for record in records:
        body = {key: value for key, value in record.items()
                if key not in {'tick', 'event_hash'}}
        previous = hashlib.sha256((previous + '\n' + str(record['tick']) + '\n'
                                   + encode(body)).encode()).hexdigest()
        record['event_hash'] = previous
    return records


class HistoricalGapJournalTests(unittest.TestCase):
    def test_exact_111_event_predecessor_remains_replayable(self):
        from successor.development import replay as replay_development
        path = ROOT / 'experience/development/20260919-native-gap-repair/kernel_journal.json'
        raw = path.read_bytes()
        journal = json.loads(raw)
        self.assertEqual(len(journal['rows']), 111)
        records, previous = [], '0' * 64
        for index, row in enumerate(journal['rows'], start=1):
            digest = hashlib.sha256((previous + '\n' + str(index) + '\n'
                                     + row['body']).encode()).hexdigest()
            self.assertEqual((row['tick'], row['previous_hash'], row['event_hash']),
                             (index, previous, digest))
            records.append({**decode(row['body']), 'tick': index, 'event_hash': digest})
            previous = digest
        self.assertEqual(previous, 'af650bacf902bcf15725cc03d65a10674d305702e995596038b23a86cc1e6bb2')
        cognitive = [r for r in records if r['kind'].startswith('COG_')]
        goals = replay(cognitive)
        self.assertEqual(len(goals), 6)
        self.assertTrue(all(g['status'] == 'WITHHOLD' for g in goals.values()))
        sessions = replay_development([r for r in records
                                       if r['kind'].startswith(('COG_', 'DEV_'))])
        self.assertEqual(len(sessions), 2)
        self.assertTrue(all(s['status'] == 'COMPLETE' for s in sessions.values()))
        self.assertEqual(path.read_bytes(), raw)


class CompositionalBindingTests(unittest.TestCase):
    def setUp(self):
        if not MANIFEST.exists():
            self.skipTest('Build the pinned successor before integration tests')
        self.tmp = tempfile.TemporaryDirectory()
        self.state = Path(self.tmp.name) / 'kernel.sqlite'
        self.kernel = SuccessorKernel(MANIFEST, self.state)
        self.kernel.db.execute('PRAGMA journal_mode=DELETE')

    def tearDown(self):
        if hasattr(self, 'kernel'):
            self.kernel.close()
            self.tmp.cleanup()

    def records(self):
        return [{**decode(row['body']), 'tick': row['tick'], 'event_hash': row['event_hash']}
                for row in self.kernel.db.execute('SELECT tick,event_hash,body FROM events ORDER BY tick')
                if decode(row['body'])['kind'].startswith('COG_')]

    def solve(self, spec, *, budget=20, mode='full'):
        goal_id = self.kernel.open_goal(spec, budget=budget, mode=mode)
        self.kernel.think(100)
        return self.kernel.cognitive_snapshot()['goals'][str(goal_id)]

    def test_recorded_failures_select_own_retries_and_survive_restart(self):
        tasks = gap_tasks()
        old_goals = [self.solve(task['spec'], budget=7) for task in tasks]
        self.assertTrue(all(goal['status'] == 'WITHHOLD' for goal in old_goals))
        self.kernel.set_compositional_synthesis()
        selections = []
        for _ in range(2):
            session_id = self.kernel.start_development(budget=30, max_goals=3)
            self.kernel.develop(200)
            session = self.kernel.development_snapshot()['sessions'][session_id]
            self.assertEqual(session['status'], 'COMPLETE')
            selections.extend(session['selections'])
        self.assertEqual({choice['parent_goal_id'] for choice in selections},
                         {goal['id'] for goal in old_goals})
        goals = self.kernel.cognitive_snapshot()['goals']
        complete_goals = replay(self.records())
        for task, old in zip(tasks, old_goals):
            self.assertEqual(goals[str(old['id'])], old)
            solved = [g for g in complete_goals.values() if g['spec'] == task['spec']
                      and g['status'] == 'VALIDATED_ON_HOLDOUT']
            self.assertEqual(len(solved), 1, task['name'])
            self.assertIn(STRATEGY, solved[0]['attempted'])
            self.assertEqual(solved[0]['result']['predictions'], task['observer_query_expected'])
        before = self.kernel.verify_state()
        journal = list(self.kernel.db.execute('SELECT tick,body,event_hash FROM events ORDER BY tick'))
        journal = [tuple(row) for row in journal]
        self.kernel.close()
        self.kernel = SuccessorKernel(MANIFEST, self.state)
        self.assertEqual(self.kernel.verify_state(), before)
        self.assertEqual(self.kernel.cognitive_snapshot()['goals'], goals)
        self.assertEqual([tuple(row) for row in self.kernel.db.execute(
            'SELECT tick,body,event_hash FROM events ORDER BY tick')], journal)
        from successor.generation import retained_memory
        self.assertTrue(retained_memory(self.kernel)['passed'])

    def test_bad_validation_does_not_change_training_selected_program(self):
        task = gap_tasks()[0]
        self.kernel.set_compositional_synthesis()
        bad = copy.deepcopy(task['spec'])
        bad['validation'][0]['expected'] = 'WRONG_HELD_OUT_LABEL'
        rejected = self.solve(bad)
        self.assertEqual(rejected['status'], 'WITHHOLD')
        self.assertIn(STRATEGY, rejected['attempted'])
        rejected_source = next(r['result']['source'] for r in self.records()
                               if r['kind'] == 'COG_EXECUTE' and r['goal_id'] == rejected['id']
                               and r['result'].get('schema') == 'yado.compositional_source.v1')
        good = self.solve(task['spec'])
        self.assertEqual(good['status'], 'VALIDATED_ON_HOLDOUT')
        self.assertEqual(good['result']['source'], rejected_source)
        self.assertEqual(good['result']['predictions'], task['observer_query_expected'])

    def test_activation_is_typed_idempotent_and_requires_idle_sessions(self):
        spec = gap_tasks()[0]['spec']
        before = self.kernel.verify_state()
        for value in (0, 1, 'yes', None):
            with self.subTest(enabled=value), self.assertRaisesRegex(ValueError, 'BOOLEAN'):
                self.kernel.set_compositional_synthesis(value)
        self.assertEqual(self.kernel.verify_state(), before)
        pending = self.kernel.open_goal(spec)
        with self.assertRaisesRegex(ValueError, 'IDLE'):
            self.kernel.set_compositional_synthesis()
        self.kernel.stop_goal(pending)
        first = self.kernel.set_compositional_synthesis()
        before = self.kernel.verify_state()
        self.assertEqual(self.kernel.set_compositional_synthesis(), first)
        self.assertEqual(self.kernel.verify_state(), before)
        development_id = self.kernel.start_development()
        with self.assertRaisesRegex(ValueError, 'IDLE'):
            self.kernel.set_compositional_synthesis(False)
        self.kernel.stop_development(development_id)
        autonomy_id = self.kernel.start_autonomy(budget=3, max_cycles=1)
        with self.assertRaisesRegex(ValueError, 'IDLE'):
            self.kernel.set_compositional_synthesis(False)
        self.kernel.stop_autonomy(autonomy_id)
        self.kernel.set_compositional_synthesis(False)
        self.assertEqual(self.kernel.verify_state()['status'], 'PASS')

    def test_rehashed_activation_rejects_numeric_aliases_of_typed_fields(self):
        self.kernel.set_compositional_synthesis()
        baseline = self.records()
        self.assertEqual(replay(baseline), {})
        for key, replacement in (('cost', 4.0), ('canonical_promotion', 0)):
            with self.subTest(field=key):
                forged = copy.deepcopy(baseline)
                activation = next(r for r in forged
                                  if r['kind'] == 'COG_ACTIVATE_COMPOSITIONAL_SYNTHESIS')
                activation[key] = replacement
                with self.assertRaisesRegex(ValueError, 'COMPOSITIONAL_BINDING_PROVENANCE'):
                    replay(rehash(forged))

    def test_deactivation_and_reactivation_preserve_historical_results(self):
        from successor.cognitive import available_strategies
        from successor.compositional_binding import active
        task = gap_tasks()[0]
        self.kernel.set_compositional_synthesis()
        learned = self.solve(task['spec'])
        self.assertEqual(learned['status'], 'VALIDATED_ON_HOLDOUT')
        disabled = self.kernel.set_compositional_synthesis(False)
        before = self.kernel.verify_state()
        self.assertEqual(self.kernel.set_compositional_synthesis(False), disabled)
        self.assertEqual(self.kernel.verify_state(), before)
        self.assertFalse(active(self.records()))
        full_goal = replay(self.records())[learned['id']]
        self.assertNotIn(STRATEGY, dict(available_strategies(full_goal, self.records())))
        # Rollback disables generation, while already verified knowledge stays.
        recalled = self.solve(task['spec'], budget=1)
        self.assertEqual(recalled['status'], 'VALIDATED_ON_HOLDOUT')
        self.assertEqual(recalled['attempted'], ['reuse_verified_source'])
        self.kernel.set_compositional_synthesis()
        self.assertTrue(active(self.records()))
        self.assertIn(STRATEGY, dict(available_strategies(full_goal, self.records())))
        self.assertEqual(self.kernel.cognitive_snapshot()['goals'][str(learned['id'])], learned)

    def test_verified_program_memory_executes_on_new_inputs(self):
        task = gap_tasks()[0]
        self.kernel.set_compositional_synthesis()
        learned = self.solve(task['spec'])
        self.assertEqual(learned['status'], 'VALIDATED_ON_HOLDOUT')
        spec = copy.deepcopy(task['spec'])
        # A byte-different dataset must use the learned serializer, including
        # values absent from its original training, holdout, and query rows.
        for partition in ('training', 'validation', 'queries'):
            for row in spec[partition]:
                value = 'fresh:' + row['input']['message']
                row['input']['message'] = value
                if 'expected' in row:
                    envelope = json.loads(row['expected'])
                    envelope['params']['arguments']['message'] = value
                    row['expected'] = json.dumps(envelope, separators=(',', ':'), ensure_ascii=False)
        expected = []
        for old, row in zip(task['observer_query_expected'], spec['queries']):
            envelope = json.loads(old)
            envelope['params']['arguments']['message'] = row['input']['message']
            expected.append(json.dumps(envelope, separators=(',', ':'), ensure_ascii=False))
        recalled = self.solve(spec, budget=1)
        self.assertEqual(recalled['status'], 'VALIDATED_ON_HOLDOUT')
        self.assertEqual(recalled['attempted'], ['reuse_verified_source'])
        self.assertEqual(recalled['result']['source_sha256'], learned['result']['source_sha256'])
        self.assertEqual(recalled['result']['predictions'], expected)
        from successor.generation import retained_memory
        self.assertTrue(retained_memory(self.kernel)['passed'])

    def test_structured_goal_extracts_nested_json_and_survives_restart(self):
        from successor.program_goals import SCHEMA
        values = ['Ada', 'Богдан', 'quoted "name"', 'line\nname', '雪', 'tab\tname', 'last\\name']
        rows = [{'input': {'payload': {'record': {'name': name}, 'sequence': index}},
                 'expected': name} for index, name in enumerate(values)]
        spec = {'schema': SCHEMA, 'domain': 'native_source',
                'training': rows[:3], 'validation': rows[3:5],
                'queries': [{'input': row['input']} for row in rows[5:]]}
        self.kernel.set_compositional_synthesis()
        goal = self.solve(spec)
        self.assertEqual(goal['status'], 'VALIDATED_ON_HOLDOUT')
        self.assertEqual(goal['attempted'], [STRATEGY])
        self.assertEqual(goal['result']['predictions'], values[5:])
        status = self.kernel.native_program_status()
        self.assertTrue(status['synthesis_active'])
        self.assertEqual(status['unresolved_goal_ids'], [])
        self.assertIn(goal['result']['source_sha256'],
                      [item['source_sha256'] for item in status['verified_programs']])
        before = self.kernel.verify_state()
        self.kernel.close()
        self.kernel = SuccessorKernel(MANIFEST, self.state)
        self.assertEqual(self.kernel.verify_state(), before)
        self.assertEqual(self.kernel.native_program_status(), status)

    def test_structured_goal_before_activation_is_rejected_without_journal_change(self):
        from successor.program_goals import SCHEMA
        spec = {'schema': SCHEMA, **gap_tasks()[0]['spec']}
        before = self.kernel.verify_state()
        journal = [tuple(row) for row in self.kernel.db.execute(
            'SELECT tick,previous_hash,body,event_hash FROM events ORDER BY tick')]
        with self.assertRaisesRegex(ValueError, 'PROGRAM_GOAL_REQUIRES_COMPOSITIONAL_ACTIVATION'):
            self.kernel.open_goal(spec)
        self.assertEqual(self.kernel.verify_state(), before)
        self.assertEqual([tuple(row) for row in self.kernel.db.execute(
            'SELECT tick,previous_hash,body,event_hash FROM events ORDER BY tick')], journal)
        self.assertEqual(self.kernel.cognitive_snapshot()['goals'], {})

    def test_bounded_public_continuation_uses_durable_failures_and_stops(self):
        task = gap_tasks()[0]
        old = self.solve(task['spec'], budget=7)
        self.assertEqual(old['status'], 'WITHHOLD')
        before = self.kernel.verify_state()
        for rounds in (0, 9, True, '3'):
            with self.subTest(rounds=rounds), self.assertRaisesRegex(ValueError, 'ROUND_BUDGET'):
                self.kernel.develop_native_programs(rounds=rounds)
        self.assertEqual(self.kernel.verify_state(), before)
        status = self.kernel.develop_native_programs(rounds=3)
        self.assertTrue(status['synthesis_active'])
        self.assertFalse(status['background_process_running'])
        self.assertFalse(status['general_intelligence_established'])
        self.assertLessEqual(len(status['sessions']), 3)
        self.assertTrue(all(s['status'] == 'COMPLETE' for s in status['sessions']))
        choices = [choice for session in status['sessions'] for choice in session['selections']]
        self.assertEqual([choice['parent_goal_id'] for choice in choices], [old['id']])
        self.assertEqual(status['unresolved_goal_ids'], [])
        self.assertEqual(self.kernel.cognitive_snapshot()['goals'][str(old['id'])], old)
        continued = self.kernel.develop_native_programs(rounds=3)
        self.assertEqual(len(continued['sessions']), 1)
        self.assertEqual(continued['sessions'][0]['selections'], [])
        self.assertEqual(continued['verified_programs'], status['verified_programs'])

    def test_rehashed_execution_or_source_forgery_is_rejected(self):
        self.kernel.set_compositional_synthesis()
        goal = self.solve(gap_tasks()[0]['spec'])
        self.assertEqual(goal['status'], 'VALIDATED_ON_HOLDOUT')
        baseline = self.records()
        self.assertEqual(replay(baseline)[goal['id']]['status'], 'VALIDATED_ON_HOLDOUT')
        for field in ('training_predictions', 'validation_predictions', 'predictions', 'source'):
            with self.subTest(field=field):
                forged = copy.deepcopy(baseline)
                execution = next(r for r in forged if r['kind'] == 'COG_EXECUTE'
                                 and r.get('goal_id') == goal['id']
                                 and r['result'].get('schema') == 'yado.compositional_source.v1')
                result = execution['result']
                if field == 'source':
                    result['source'] += '\n# forged source\n'
                    result['source_sha256'] = hashlib.sha256(result['source'].encode()).hexdigest()
                else:
                    result[field][0] = 'FORGED_PREDICTION'
                for row in forged:
                    if row.get('goal_id') != goal['id']:
                        continue
                    if row['kind'] == 'COG_FINISH':
                        row['result'] = copy.deepcopy(result)
                    elif row['kind'] == 'COG_VERIFY':
                        row['evidence']['source_sha256'] = result['source_sha256']
                with self.assertRaisesRegex(ValueError, 'PROVENANCE|INTEGRITY|MISMATCH'):
                    replay(rehash(forged))

    def test_child_composes_verified_parent_and_rejects_forged_lineage(self):
        task = gap_tasks()[0]
        self.kernel.set_compositional_synthesis()
        parent = self.solve(task['spec'])
        self.assertEqual(parent['status'], 'VALIDATED_ON_HOLDOUT')
        spec = copy.deepcopy(task['spec'])
        for partition in ('training', 'validation'):
            for row in spec[partition]:
                row['expected'] = len(row['expected'])
        child = self.solve(spec)
        self.assertEqual(child['status'], 'VALIDATED_ON_HOLDOUT')
        self.assertEqual(child['result']['predictions'],
                         [len(value) for value in task['observer_query_expected']])
        self.assertEqual(child['result']['parent_source_sha256'],
                         [parent['result']['source_sha256']])
        self.assertNotEqual(child['result']['source_sha256'], parent['result']['source_sha256'])
        baseline = self.records()
        for parents in ([], ['0' * 64]):
            with self.subTest(parents=parents):
                forged = copy.deepcopy(baseline)
                for row in forged:
                    if row.get('goal_id') == child['id'] and row['kind'] in {'COG_EXECUTE', 'COG_FINISH'}:
                        result = row.get('result') or {}
                        if result.get('schema') == 'yado.compositional_source.v1':
                            result['parent_source_sha256'] = parents
                with self.assertRaisesRegex(ValueError, 'PROVENANCE'):
                    replay(rehash(forged))
        from successor.generation import retained_memory
        self.assertTrue(retained_memory(self.kernel)['passed'])

    def test_generated_and_reused_metadata_reject_boolean_to_integer_forgery(self):
        task = gap_tasks()[0]
        self.kernel.set_compositional_synthesis()
        learned = self.solve(task['spec'])
        self.assertEqual(learned['status'], 'VALIDATED_ON_HOLDOUT')
        reused = self.solve(task['spec'], budget=1)
        self.assertEqual(reused['attempted'], ['reuse_verified_source'])
        self.assertEqual(reused['status'], 'VALIDATED_ON_HOLDOUT')
        baseline = self.records()
        replay(baseline)
        for goal in (learned, reused):
            for key, replacement in (('compiled', 1), ('automatic_canonical_promotion', 0)):
                with self.subTest(goal_id=goal['id'], field=key):
                    self.assertIs(type(goal['result'][key]), bool)
                    forged = copy.deepcopy(baseline)
                    for row in forged:
                        if row.get('goal_id') == goal['id'] and row['kind'] in {'COG_EXECUTE', 'COG_FINISH'}:
                            result = row.get('result') or {}
                            if result.get('schema') == 'yado.compositional_source.v1':
                                result[key] = replacement
                    with self.assertRaisesRegex(ValueError, 'PROVENANCE'):
                        replay(rehash(forged))
