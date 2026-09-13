import copy
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from successor.development_run import tasks
from successor.kernel import SuccessorKernel

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(os.environ.get('YADO_SUCCESSOR_TEST_MANIFEST', ROOT / 'successor/state/birth-v2/manifest.json'))


class DevelopmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = Path(self.tmp.name) / 'state.sqlite'
        self.kernel = SuccessorKernel(MANIFEST, self.state)

    def tearDown(self):
        self.kernel.close()
        self.tmp.cleanup()

    def fail_goal(self, task=None, budget=1, mode='full'):
        spec = (task or tasks()[0])['spec']
        goal = self.kernel.open_goal(spec, budget=budget, mode=mode)
        self.kernel.think(40)
        self.assertEqual(self.kernel.cognitive_snapshot()['goals'][str(goal)]['status'], 'WITHHOLD')
        return goal

    def session(self, identifier):
        return self.kernel.development_snapshot()['sessions'][identifier]

    def test_kernel_selects_two_failures_and_transfer_depends_on_learned_memory(self):
        parents = {self.fail_goal(t) for t in tasks()}
        identifier = self.kernel.start_development()
        self.kernel.develop(100)
        session = self.session(identifier)
        self.assertEqual(session['status'], 'COMPLETE')
        self.assertEqual({p['parent_goal_id'] for p in session['selections']}, parents)
        self.assertEqual(len(session['outcomes']), 2)
        self.assertTrue(all(r['status'] == 'VALIDATED_ON_HOLDOUT' for r in session['outcomes']))
        self.assertLessEqual(sum(r['spent'] for r in session['outcomes']), session['budget'])
        for task in tasks(True):
            for mode, expected in [('full', 'VALIDATED_ON_HOLDOUT'), ('no_memory', 'WITHHOLD')]:
                goal = self.kernel.open_goal(task['spec'], budget=1, mode=mode)
                self.kernel.think(40)
                result = self.kernel.cognitive_snapshot()['goals'][str(goal)]
                self.assertEqual(result['status'], expected)
                if mode == 'full':
                    self.assertEqual(result['attempted'], ['reuse_verified_source'])
                    self.assertEqual(result['result']['predictions'], task['expected_queries'])

    def test_restart_after_source_freeze_continues_in_separate_process(self):
        self.fail_goal()
        identifier = self.kernel.start_development(budget=6, max_goals=1)
        frozen = self.kernel.develop(3)[-1]
        self.assertEqual(frozen['kind'], 'COG_EXECUTE')
        self.kernel.close()
        subprocess.run([sys.executable, '-m', 'successor', 'develop', '--manifest', str(MANIFEST),
                        '--state', str(self.state), '--max-steps', '30'], cwd=ROOT, check=True,
                       capture_output=True, text=True, timeout=60)
        self.kernel = SuccessorKernel(MANIFEST, self.state)
        outcome = self.session(identifier)['outcomes'][0]
        self.assertEqual(outcome['source_sha256'], frozen['result']['source_sha256'])
        executions = [r for r in self.kernel.recent(100) if r['kind'] == 'COG_EXECUTE'
                      and r['goal_id'] == outcome['goal_id']]
        self.assertEqual(len(executions), 1)

    def test_stop_prevents_pending_execution_and_survives_restart(self):
        self.fail_goal()
        identifier = self.kernel.start_development(budget=6, max_goals=1)
        self.kernel.develop(2)
        child = self.session(identifier)['child_goal_id']
        self.kernel.stop_development(identifier)
        self.kernel.close()
        self.kernel = SuccessorKernel(MANIFEST, self.state)
        before = self.kernel.verify_state()
        self.assertEqual(self.kernel.develop(100), [])
        self.assertEqual(self.kernel.verify_state(), before)
        self.assertEqual(self.session(identifier)['status'], 'STOPPED')
        self.assertEqual(self.kernel.cognitive_snapshot()['goals'][str(child)]['status'], 'STOPPED')
        self.assertFalse(any(r['kind'] == 'COG_EXECUTE' and r['goal_id'] == child for r in self.kernel.recent(100)))

    def test_budget_and_goal_cap_persist_without_repeated_retry_loops(self):
        for task in tasks():
            self.fail_goal(task)
        first = self.kernel.start_development(budget=6, max_goals=1)
        self.kernel.develop(100)
        self.assertEqual(len(self.session(first)['selections']), 1)
        second = self.kernel.start_development(budget=6, max_goals=1)
        self.kernel.develop(100)
        self.assertEqual(len(self.session(second)['selections']), 1)
        self.assertNotEqual(self.session(first)['selections'][0]['parent_goal_id'],
                            self.session(second)['selections'][0]['parent_goal_id'])
        third = self.kernel.start_development()
        self.kernel.develop(100)
        self.assertEqual(self.session(third)['selections'], [])
        self.assertEqual(self.kernel.develop(100), [])

    def test_insufficient_budget_and_ablated_history_create_no_retry(self):
        self.fail_goal()
        low = self.kernel.start_development(budget=1)
        self.kernel.develop(30)
        self.assertEqual(self.session(low)['selections'], [])
        self.fail_goal(tasks()[1], mode='no_memory')
        enough = self.kernel.start_development(budget=12)
        self.kernel.develop(100)
        self.assertEqual(len(self.session(enough)['selections']), 1)

    def test_fully_tested_failed_source_is_not_retried_or_admitted(self):
        task = copy.deepcopy(tasks()[0])
        task['spec']['validation'][0]['expected'] = 'wrong'
        self.fail_goal(task, budget=6)
        identifier = self.kernel.start_development()
        self.kernel.develop(40)
        self.assertEqual(self.session(identifier)['selections'], [])
        goal = self.kernel.open_goal(tasks(True)[0]['spec'], budget=1)
        self.kernel.think(40)
        self.assertEqual(self.kernel.cognitive_snapshot()['goals'][str(goal)]['status'], 'WITHHOLD')

    def test_interruption_rolls_back_execution_without_extra_spend(self):
        self.fail_goal()
        identifier = self.kernel.start_development(budget=6)
        self.kernel.develop(2)
        before = self.kernel.verify_state()
        with patch.object(self.kernel.parent, 'native_source_candidate', side_effect=KeyboardInterrupt()):
            with self.assertRaises(KeyboardInterrupt):
                self.kernel.develop(1)
        self.assertEqual(self.kernel.verify_state(), before)
        self.kernel.develop(40)
        self.assertEqual(self.session(identifier)['outcomes'][0]['status'], 'VALIDATED_ON_HOLDOUT')

    def test_invalid_limits_and_overlapping_sessions_leave_no_partial_events(self):
        before = self.kernel.verify_state()
        for budget, count in [(0, 1), (31, 1), (True, 1), (6, 0), (6, 9), (6, True)]:
            with self.assertRaises(ValueError):
                self.kernel.start_development(budget=budget, max_goals=count)
        self.assertEqual(self.kernel.verify_state(), before)
        goal = self.kernel.open_goal(tasks()[0]['spec'], budget=1)
        with self.assertRaisesRegex(ValueError, 'REQUIRES_IDLE'):
            self.kernel.start_development()
        self.kernel.stop_goal(goal)
        self.kernel.start_development()
        with self.assertRaisesRegex(ValueError, 'REQUIRES_IDLE'):
            self.kernel.start_development()
        external = self.kernel.open_goal(tasks()[1]['spec'], budget=1)
        before = self.kernel.verify_state()
        self.assertEqual(self.kernel.develop(20), [])
        self.assertEqual(self.kernel.verify_state(), before)
        self.kernel.stop_goal(external)
        self.assertTrue(self.kernel.develop(20))

    def test_forged_selection_is_rejected_even_with_a_valid_hash_chain(self):
        self.fail_goal()
        identifier = self.kernel.start_development()
        self.kernel._append({'kind': 'DEV_SELECT', 'development_id': identifier,
                             'choice': {'parent_goal_id': 999, 'budget': 1}})
        with self.assertRaisesRegex(ValueError, 'DEVELOPMENT_SELECTION_EVIDENCE'):
            self.kernel.verify_state()

    def test_orphan_subgoal_and_unverified_outcome_are_rejected(self):
        self.kernel.open_goal(tasks()[0]['spec'], budget=1)
        original = self.kernel.recent(1)[0]
        original.pop('tick')
        original.pop('event_hash')
        original['development_id'] = 999
        self.kernel._append(original)
        with self.assertRaisesRegex(ValueError, 'DEVELOPMENT_SUBGOAL_PROVENANCE'):
            self.kernel.verify_state()
        self.kernel.close()
        self.kernel = SuccessorKernel(MANIFEST, Path(self.tmp.name) / 'second.sqlite')
        self.fail_goal()
        identifier = self.kernel.start_development()
        self.kernel.develop(1)
        self.kernel._append({'kind': 'DEV_OUTCOME', 'development_id': identifier, 'status': 'VALIDATED_ON_HOLDOUT'})
        with self.assertRaisesRegex(ValueError, 'DEVELOPMENT_OUTCOME_PROVENANCE'):
            self.kernel.verify_state()
