import copy
from fractions import Fraction
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from successor.development_run import tasks
from successor.kernel import SuccessorKernel, fingerprint

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(os.environ.get('YADO_SUCCESSOR_TEST_MANIFEST', ROOT / 'successor/state/birth-v2/manifest.json'))


def finite_difference_answers(spec):
    """Independent cubic extrapolation from four observed points per query."""
    answers = []
    for query in spec['queries']:
        values = [next(r['expected'] for r in spec['rows'] if r['x'] == x and r['y'] == query['y'])
                  for x in (-3, -2, -1, 0)]
        n, factor, answer = query['x'] + 3, Fraction(1), Fraction(0)
        for degree in range(4):
            answer += factor * values[0]
            values = [b - a for a, b in zip(values, values[1:])]
            factor *= Fraction(n - degree, degree + 1)
        answers.append(answer)
    return answers


class AutonomyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = Path(self.tmp.name) / 'state.sqlite'
        self.kernel = SuccessorKernel(MANIFEST, self.state)

    def tearDown(self):
        self.kernel.close()
        self.tmp.cleanup()

    def run_goal(self, spec, budget=3, mode='full'):
        gid = self.kernel.open_goal(spec, budget=budget, mode=mode)
        self.kernel.think(100)
        return self.kernel.cognitive_snapshot()['goals'][str(gid)]

    def session(self, identifier):
        return self.kernel.autonomy_snapshot()['sessions'][identifier]

    def seed_simple_experience(self):
        self.run_goal({'domain': 'relation', 'relation': [[1, 2]], 'start': 1})
        self.run_goal({'domain': 'events', 'events': [['Q', 'a'], ['R', 'a']]})

    def test_self_generated_failure_drives_retry_then_fresh_transfer(self):
        self.seed_simple_experience()
        sid = self.kernel.start_autonomy(budget=60, max_cycles=8)
        self.kernel.run_autonomy(300)
        session = self.session(sid)
        self.assertEqual(session['status'], 'COMPLETE')
        self.assertEqual(len(session['outcomes']), 8)
        self.assertEqual(session['selections'][0]['route'], 'EXPLORE')
        self.assertEqual(session['selections'][0]['spec']['domain'], 'numeric')
        self.assertEqual(session['outcomes'][0]['status'], 'WITHHOLD')
        self.assertEqual(session['selections'][1]['route'], 'RETRY_FAILURE')
        self.assertEqual(session['selections'][1]['evidence']['parent_goal_id'], session['outcomes'][0]['goal_id'])
        self.assertEqual(session['outcomes'][1]['status'], 'VALIDATED_ON_HOLDOUT')
        self.assertLessEqual(sum(c['budget'] for c in session['selections']), 60)
        fresh = [c['spec'] for c in session['selections'][2:]
                 if c['route'] == 'EXPLORE' and c['spec']['domain'] == 'numeric']
        self.assertTrue(fresh)
        full = self.run_goal(fresh[-1], budget=3)
        ablated = self.run_goal(fresh[-1], budget=3, mode='no_memory')
        self.assertEqual(full['attempted'], ['polynomial_3'])
        self.assertEqual(full['result']['predictions'], finite_difference_answers(fresh[-1]))
        self.assertEqual(ablated['status'], 'WITHHOLD')

    def test_restart_after_source_freeze_resumes_without_duplicate_execution(self):
        failed = self.run_goal(tasks()[0]['spec'], budget=1)
        self.assertEqual(failed['status'], 'WITHHOLD')
        sid = self.kernel.start_autonomy(budget=12, max_cycles=2)
        frozen = self.kernel.run_autonomy(3)[-1]
        self.assertEqual(frozen['kind'], 'COG_EXECUTE')
        child = self.session(sid)['child_goal_id']
        self.kernel.close()
        subprocess.run([sys.executable, '-m', 'successor', 'autonomy-run', '--manifest', str(MANIFEST),
                        '--state', str(self.state), '--max-steps', '100'], cwd=ROOT,
                       check=True, capture_output=True, text=True, timeout=90)
        self.kernel = SuccessorKernel(MANIFEST, self.state)
        executions = [r for r in self.kernel.recent(200) if r['kind'] == 'COG_EXECUTE' and r['goal_id'] == child]
        self.assertEqual(len(executions), 1)
        self.assertEqual(self.session(sid)['outcomes'][0]['source_sha256'], frozen['result']['source_sha256'])
        self.assertEqual(self.session(sid)['status'], 'COMPLETE')

    def test_atomic_goal_selection_rolls_back_an_interruption(self):
        self.kernel.start_autonomy()
        before = self.kernel.verify_state()
        append = self.kernel._append
        def interrupt(body):
            if body['kind'] == 'COG_GOAL' and 'autonomy_id' in body:
                raise KeyboardInterrupt()
            return append(body)
        with patch.object(self.kernel, '_append', side_effect=interrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.kernel.run_autonomy(1)
        self.assertEqual(self.kernel.verify_state(), before)
        self.assertEqual([r['kind'] for r in self.kernel.run_autonomy(1)], ['AUTO_SELECT', 'COG_GOAL'])

    def test_stop_is_durable_and_does_not_execute_pending_action(self):
        sid = self.kernel.start_autonomy()
        self.kernel.run_autonomy(2)
        child = self.session(sid)['child_goal_id']
        self.kernel.stop_autonomy(sid)
        self.kernel.close()
        self.kernel = SuccessorKernel(MANIFEST, self.state)
        before = self.kernel.verify_state()
        self.assertEqual(self.kernel.run_autonomy(100), [])
        self.assertEqual(self.kernel.verify_state(), before)
        self.assertEqual(self.session(sid)['status'], 'STOPPED')
        self.assertEqual(self.kernel.cognitive_snapshot()['goals'][str(child)]['status'], 'STOPPED')
        self.assertFalse(any(r['kind'] == 'COG_EXECUTE' and r['goal_id'] == child for r in self.kernel.recent(100)))

    def test_foreign_work_pauses_autonomy_until_handled(self):
        sid = self.kernel.start_autonomy(max_cycles=1)
        self.kernel.run_autonomy(1)
        foreign = self.kernel.open_goal(tasks()[0]['spec'])
        before = self.kernel.verify_state()
        self.assertEqual(self.kernel.run_autonomy(20), [])
        self.assertEqual(self.kernel.verify_state(), before)
        self.kernel.stop_goal(foreign)
        self.kernel.run_autonomy(100)
        self.assertEqual(self.session(sid)['status'], 'COMPLETE')

    def test_limits_and_overlapping_sessions_fail_without_partial_state(self):
        before = self.kernel.verify_state()
        for budget, count in [(0, 1), (513, 1), (True, 1), (6, 0), (6, 65), (6, True)]:
            with self.assertRaises(ValueError):
                self.kernel.start_autonomy(budget=budget, max_cycles=count)
        self.assertEqual(self.kernel.verify_state(), before)
        sid = self.kernel.start_autonomy(budget=1)
        with self.assertRaisesRegex(ValueError, 'REQUIRES_IDLE'):
            self.kernel.start_autonomy()
        self.kernel.run_autonomy(20)
        self.assertEqual(self.session(sid)['selections'], [])
        self.assertEqual(self.session(sid)['reason'], 'BUDGET_EXHAUSTED')

    def test_forged_selection_is_rejected(self):
        sid = self.kernel.start_autonomy()
        self.kernel._append({'kind': 'AUTO_SELECT', 'autonomy_id': sid, 'choice': {'route': 'forged'}})
        with self.assertRaisesRegex(ValueError, 'AUTONOMY_SELECTION_EVIDENCE'):
            self.kernel.verify_state()

    def test_unregistered_autonomous_goal_is_rejected(self):
        spec = tasks()[0]['spec']
        self.kernel._append({'kind': 'COG_GOAL', 'spec': spec, 'spec_digest': fingerprint(spec),
                             'budget': 1, 'mode': 'full', 'autonomy_id': 999, 'selection_tick': 998})
        with self.assertRaisesRegex(ValueError, 'AUTONOMY_GOAL_PROVENANCE'):
            self.kernel.verify_state()

    def test_outcome_cannot_claim_success_before_verification(self):
        sid = self.kernel.start_autonomy()
        self.kernel.run_autonomy(1)
        child = self.session(sid)['child_goal_id']
        self.kernel._append({'kind': 'AUTO_OUTCOME', 'autonomy_id': sid, 'goal_id': child,
                             'status': 'VERIFIED', 'spent': 0, 'terminal_tick': child,
                             'result_digest': fingerprint(None), 'source_sha256': None})
        with self.assertRaisesRegex(ValueError, 'AUTONOMY_OUTCOME_PROVENANCE'):
            self.kernel.verify_state()

    def test_failed_retry_is_not_repeated_in_later_sessions(self):
        bad = copy.deepcopy(tasks()[0]['spec'])
        bad['validation'][0]['expected'] = 'incorrect'
        self.run_goal(bad, budget=1)
        first = self.kernel.start_autonomy(budget=9, max_cycles=2)
        self.kernel.run_autonomy(100)
        self.assertEqual(self.session(first)['selections'][0]['route'], 'RETRY_FAILURE')
        self.assertEqual(self.session(first)['outcomes'][0]['status'], 'WITHHOLD')
        second = self.kernel.start_autonomy(budget=9, max_cycles=1)
        self.kernel.run_autonomy(100)
        self.assertNotEqual(self.session(second)['selections'][0]['spec'], bad)
