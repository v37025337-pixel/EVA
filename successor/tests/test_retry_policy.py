"""A newly admitted strategy warrants a retry even with a smaller total budget."""
import os
from pathlib import Path
import tempfile
import unittest

from successor.kernel import SuccessorKernel


MANIFEST = Path(os.environ.get('YADO_SUCCESSOR_TEST_MANIFEST',
    Path(__file__).resolve().parents[2] / 'successor/state/birth-v2/manifest.json'))


class RetryPolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = Path(self.tmp.name) / 'kernel.sqlite'
        self.kernel = SuccessorKernel(MANIFEST, self.state)

    def tearDown(self):
        self.kernel.close()
        self.tmp.cleanup()

    def failed_quadratic(self, budget=15):
        spec = {'domain': 'native_source',
            'training': [{'input': {'x': x}, 'expected': 10-x*x} for x in range(-3, 4)],
            'validation': [{'input': {'x': x}, 'expected': 10-x*x} for x in (10, 11)],
            'queries': [{'input': {'x': 13}}]}
        goal = self.kernel.open_goal(spec, budget=budget)
        self.kernel.think(40)
        self.assertEqual(self.kernel.cognitive_snapshot()['goals'][str(goal)]['status'], 'WITHHOLD')
        return goal

    def test_new_strategy_is_retryable_below_old_budget_but_legacy_history_is_unchanged(self):
        parent = self.failed_quadratic()
        self.kernel.activate_native_synthesis()
        legacy = self.kernel._append({'kind': 'DEV_START', 'budget': 12, 'max_goals': 1})['tick']
        self.kernel.develop(2)
        old = self.kernel.development_snapshot()['sessions'][legacy]
        self.assertEqual(old['selections'], [])
        current = self.kernel.start_development(budget=12, max_goals=1)
        self.kernel.develop(1)
        choice = self.kernel.development_snapshot()['sessions'][current]['selections']
        self.assertEqual(len(choice), 1)
        self.assertEqual(choice[0]['parent_goal_id'], parent)
        self.assertEqual([x['strategy'] for x in choice[0]['untried']], ['native_evolved_v2'])
        self.assertLess(choice[0]['budget'], 15)
        self.kernel.stop_development(current)
        self.kernel.close()
        self.kernel = SuccessorKernel(MANIFEST, self.state)
        self.assertEqual(self.kernel.development_snapshot()['sessions'][legacy], old)

    def test_autonomy_retries_a_previously_developed_failure_only_after_a_new_strategy(self):
        parent = self.failed_quadratic(budget=1)
        first = self.kernel.start_development(budget=6, max_goals=1)
        self.kernel.develop(60)
        previous = self.kernel.development_snapshot()['sessions'][first]
        self.assertEqual(previous['selections'][0]['parent_goal_id'], parent)
        self.assertEqual(previous['outcomes'][0]['status'], 'WITHHOLD')
        duplicate = self.kernel.start_development(budget=12, max_goals=1)
        self.kernel.develop(10)
        self.assertEqual(self.kernel.development_snapshot()['sessions'][duplicate]['selections'], [])
        self.kernel.activate_native_synthesis()
        current = self.kernel.start_autonomy(budget=12, max_cycles=1)
        self.kernel.run_autonomy(4)
        choice = self.kernel.autonomy_snapshot()['sessions'][current]['selections'][0]
        self.assertEqual(choice['route'], 'RETRY_FAILURE')
        self.assertEqual(choice['evidence']['parent_goal_id'], parent)
        self.assertEqual([x['strategy'] for x in choice['evidence']['untried']], ['native_evolved_v2'])
        self.kernel.stop_autonomy(current)

    def test_unknown_retry_policy_cannot_be_replayed(self):
        self.kernel._append({'kind': 'DEV_START', 'budget': 12, 'max_goals': 1,
                             'retry_policy': 'unverified_future_policy'})
        with self.assertRaisesRegex(ValueError, 'DEVELOPMENT_START_CONTRACT'):
            self.kernel.verify_state()


if __name__ == '__main__':
    unittest.main()
