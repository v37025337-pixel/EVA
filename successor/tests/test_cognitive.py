import json
import os
from pathlib import Path
import random
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from successor.kernel import SuccessorKernel, encode, decode
from successor.cognitive import split_examples

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(os.environ.get('YADO_SUCCESSOR_TEST_MANIFEST', ROOT / 'successor/state/birth-v2/manifest.json'))


def numeric_goal(degree=3, offset=0):
    return {'domain': 'numeric', 'rows': [
        {'x': x, 'y': y, 'expected': x ** degree + 2 * y + offset}
        for x in range(-3, 4) for y in range(-2, 3)],
        'queries': [{'x': 9, 'y': -4}, {'x': -8, 'y': 3}]}


class CognitiveTests(unittest.TestCase):
    def setUp(self):
        if not MANIFEST.exists():
            self.skipTest('Build the pinned successor before integration tests')
        self.tmp = tempfile.TemporaryDirectory()
        self.state = Path(self.tmp.name) / 'cognitive.sqlite'
        self.kernel = SuccessorKernel(MANIFEST, self.state)

    def tearDown(self):
        if hasattr(self, 'kernel'):
            self.kernel.close()
            self.tmp.cleanup()

    def test_goal_selects_its_steps_without_a_supplied_task_list(self):
        goal = self.kernel.open_goal(numeric_goal(), budget=6)
        self.kernel.think(40)
        completed = self.kernel.cognitive_snapshot()['goals'][str(goal)]
        self.assertEqual(completed['status'], 'VALIDATED_ON_HOLDOUT')
        self.assertEqual(completed['result']['predictions'], [721, -506])
        self.assertEqual(completed['attempted'], ['polynomial_1', 'polynomial_2', 'polynomial_3'])

    def run_goal(self, spec, budget=6, mode='full'):
        goal = self.kernel.open_goal(spec, budget=budget, mode=mode)
        self.kernel.think(40)
        return self.kernel.cognitive_snapshot()['goals'][str(goal)]

    def test_learned_choice_survives_restart_and_beats_ablations_at_equal_budget(self):
        self.run_goal(numeric_goal(), budget=6)
        self.kernel.close()
        self.kernel = SuccessorKernel(MANIFEST, self.state)
        adapted = self.run_goal(numeric_goal(offset=17), budget=3)
        no_memory = self.run_goal(numeric_goal(offset=23), budget=3, mode='no_memory')
        no_model = self.run_goal(numeric_goal(offset=-19), budget=3, mode='no_self_model')
        self.assertEqual(adapted['attempted'], ['polynomial_3'])
        self.assertEqual(adapted['status'], 'VALIDATED_ON_HOLDOUT')
        self.assertEqual(adapted['result']['predictions'], [738, -489])
        for ablation in (no_memory, no_model):
            self.assertEqual(ablation['status'], 'WITHHOLD')
            self.assertEqual(ablation['attempted'], ['polynomial_1', 'polynomial_2'])
            self.assertEqual(ablation['remaining'], 0)

    def test_forecast_commits_before_execution_and_is_consumed_by_each_stage(self):
        goal = self.kernel.open_goal(numeric_goal(), budget=6)
        first = self.kernel.think(1)[0]
        self.assertEqual(first['kind'], 'COG_DECIDE')
        self.assertEqual(self.kernel.cognitive_snapshot()['goals'][str(goal)]['attempted'], [])
        events = self.kernel.think(3)
        self.assertEqual([x['kind'] for x in events], ['COG_EXECUTE', 'COG_VERIFY', 'COG_REFLECT'])
        self.assertTrue(all(e['workspace_digest'] == first['workspace_digest'] for e in events))
        self.assertFalse(events[2]['success'])
        self.assertLess(events[2]['prediction_error'], 0)
        second = self.kernel.think(1)[0]
        self.assertNotEqual(second['choice']['strategy'], first['choice']['strategy'])
        self.assertIn(events[2]['tick'], second['workspace']['evidence']['recent_reflection_ticks'])

    def test_stronger_fixed_capacity_baseline_can_solve_without_learning(self):
        result = self.run_goal(numeric_goal(), budget=3, mode='fixed_max')
        self.assertEqual(result['status'], 'VALIDATED_ON_HOLDOUT')
        self.assertEqual(result['attempted'], ['polynomial_3'])

    def test_fit_never_receives_holdout_labels_or_query_answers(self):
        spec = numeric_goal()
        train, holdout = split_examples(spec['rows'])
        observed = []
        original = self.kernel.parent.fit_polynomial_logic
        def inspect(rows, max_degree):
            observed.extend(rows)
            return original(rows, max_degree=max_degree)
        self.kernel.parent.fit_polynomial_logic = inspect
        self.run_goal(spec)
        forbidden = {(r['x'], r['y']) for r in holdout}
        self.assertTrue(observed)
        self.assertTrue(all((r['x'], r['y']) not in forbidden for r in observed))
        self.assertEqual({(r['x'], r['y']) for r in observed}, {(r['x'], r['y']) for r in train})

    def test_bad_holdout_is_rejected_despite_a_fitted_model(self):
        spec = numeric_goal()
        _, holdout = split_examples(spec['rows'])
        damaged = holdout[0]
        for row in spec['rows']:
            if (row['x'], row['y']) == (damaged['x'], damaged['y']):
                row['expected'] += 1
        result = self.run_goal(spec)
        self.assertEqual(result['status'], 'WITHHOLD')
        checks = [r for r in self.kernel.recent(50) if r.get('kind') == 'COG_VERIFY' and r['checks']]
        self.assertEqual(len(checks), 1)
        self.assertFalse(checks[0]['passed'])

    def test_interrupt_leaves_committed_decision_and_unspent_budget(self):
        goal = self.kernel.open_goal(numeric_goal(), budget=6)
        decision = self.kernel.think(1)[0]
        original = self.kernel.parent.fit_polynomial_logic
        def interrupt(*args, **kwargs):
            raise KeyboardInterrupt()
        self.kernel.parent.fit_polynomial_logic = interrupt
        with self.assertRaises(KeyboardInterrupt):
            self.kernel.think(1)
        self.kernel.parent.fit_polynomial_logic = original
        state = self.kernel.cognitive_snapshot()['goals'][str(goal)]
        self.assertEqual(state['remaining'], 6)
        self.assertEqual(state['phase'], 'EXECUTE')
        self.assertEqual(self.kernel.think(1)[0]['decision_tick'], decision['tick'])
        self.kernel.think(40)
        self.assertEqual(self.kernel.cognitive_snapshot()['goals'][str(goal)]['status'], 'VALIDATED_ON_HOLDOUT')

    def test_runtime_exception_is_recorded_and_changes_strategy(self):
        original = self.kernel.parent.fit_polynomial_logic
        def fail_first(rows, max_degree):
            if max_degree == 1:
                raise RuntimeError('injected execution fault')
            return original(rows, max_degree=max_degree)
        self.kernel.parent.fit_polynomial_logic = fail_first
        result = self.run_goal(numeric_goal(degree=2), budget=3)
        self.assertEqual(result['attempted'], ['polynomial_1', 'polynomial_2'])
        self.assertEqual(result['status'], 'VALIDATED_ON_HOLDOUT')
        executions = [r for r in self.kernel.recent(50) if r.get('kind') == 'COG_EXECUTE']
        self.assertEqual(executions[-1]['result']['error_type'], 'RuntimeError')

    def test_stop_is_durable_and_prevents_the_pending_action(self):
        goal = self.kernel.open_goal(numeric_goal(), budget=6)
        self.kernel.think(1)
        self.kernel.stop_goal(goal)
        self.kernel.close()
        self.kernel = SuccessorKernel(MANIFEST, self.state)
        self.assertEqual(self.kernel.think(30), [])
        self.assertEqual(self.kernel.cognitive_snapshot()['goals'][str(goal)]['status'], 'STOPPED')

    def test_resumes_in_a_second_process_after_a_committed_forecast(self):
        goal = self.kernel.open_goal({'domain': 'relation', 'relation': [[1, 2], [2, 3]], 'start': 1})
        self.kernel.think(1)
        subprocess.run([sys.executable, '-m', 'successor', 'think', '--manifest', str(MANIFEST),
            '--state', str(self.state), '--max-steps', '20'], cwd=ROOT, check=True,
            capture_output=True, text=True, timeout=45)
        result = self.kernel.cognitive_snapshot()['goals'][str(goal)]
        self.assertEqual(result['status'], 'VERIFIED')
        self.assertEqual(set(result['result']['answer']), {1, 2, 3})

    def test_consolidation_preserves_experience_beyond_recent_attention(self):
        self.run_goal(numeric_goal(), budget=6)
        for i in range(17):
            self.run_goal({'domain': 'relation', 'relation': [[i, i + 1]], 'start': i}, mode='no_consolidation')
        fork = Path(self.tmp.name) / 'without-consolidation.sqlite'
        with sqlite3.connect(fork) as destination:
            self.kernel.db.backup(destination)
        old_knowledge = self.run_goal(numeric_goal(offset=55), budget=3)
        self.assertEqual(old_knowledge['attempted'], ['polynomial_3'])
        other = SuccessorKernel(MANIFEST, fork)
        try:
            goal = other.open_goal(numeric_goal(offset=55), budget=3, mode='no_consolidation')
            other.think(40)
            forgotten = other.cognitive_snapshot()['goals'][str(goal)]
            self.assertEqual(forgotten['status'], 'WITHHOLD')
            self.assertEqual(forgotten['attempted'], ['polynomial_1', 'polynomial_2'])
        finally:
            other.close()

    def test_idle_consolidation_is_idempotent_and_preserves_raw_history(self):
        self.run_goal(numeric_goal())
        before = self.kernel.verify_state()
        self.assertEqual(self.kernel.think(100), [])
        self.assertEqual(self.kernel.verify_state(), before)
        self.assertTrue(any(r.get('kind') == 'COG_CONSOLIDATE' for r in self.kernel.recent(50)))
        self.assertEqual(len([r for r in self.kernel.recent(50) if r.get('kind') == 'COG_REFLECT']), 3)

    def test_invalid_inputs_leave_no_goal_or_partial_event(self):
        duplicate = numeric_goal()
        duplicate['rows'].append(dict(duplicate['rows'][0]))
        leaked = numeric_goal()
        leaked['queries'][0]['expected'] = 721
        for spec in (duplicate, leaked, {'domain': 'arbitrary_network_action'}):
            with self.assertRaises(ValueError):
                self.kernel.open_goal(spec)
        for budget in (0, 31, True):
            with self.assertRaises(ValueError):
                self.kernel.open_goal(numeric_goal(), budget=budget)
        self.assertEqual(self.kernel.verify_state()['tick'], 0)

    def test_causal_model_rejects_forged_consolidation_even_with_valid_hash_chain(self):
        self.run_goal(numeric_goal())
        self.kernel._append({'kind': 'COG_CONSOLIDATE', 'through_tick': 0,
                             'stats': {}, 'model_digest': 'forged'})
        with self.assertRaisesRegex(ValueError, 'COGNITIVE_CONSOLIDATION_INTEGRITY'):
            self.kernel.verify_state()

    def test_relation_and_event_answers_pass_independent_checks(self):
        rng = random.Random(81023)
        for case in range(8):
            edges = [[a, b] for a in range(7) for b in range(7) if rng.random() < .2]
            result = self.run_goal({'domain': 'relation', 'relation': edges, 'start': case % 7})
            self.assertEqual(result['status'], 'VERIFIED')
        for events, expected in (([], True), ([['R', 'x']], False),
            ([['Q', 'a'], ['Q', 'b'], ['R', 'b'], ['R', 'a']], True),
            ([['Q', 'a'], ['Q', 'b'], ['R', 'a'], ['R', 'b']], False)):
            result = self.run_goal({'domain': 'events', 'events': events})
            self.assertEqual(result['status'], 'VERIFIED')
            self.assertIs(result['result']['answer'], expected)

    def test_unverified_legacy_execution_is_not_passed_to_controller_as_success(self):
        evidence = []
        original = self.kernel.parent.global_experience_meta_decide_evidence
        def inspect(item):
            if 'domain' in item:
                evidence.append(item)
            return original(item)
        self.kernel.parent.global_experience_meta_decide_evidence = inspect
        self.kernel.execute({'kind': 'audit'})
        self.assertEqual(evidence[-1]['outcome'], 'WITHHOLD')
        self.assertEqual(evidence[-1]['next_required_capability'], 'VERIFY_TASK')


if __name__ == '__main__':
    unittest.main()
