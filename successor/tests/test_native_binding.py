import os
from pathlib import Path
import tempfile
import unittest

from successor.kernel import SuccessorKernel

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(os.environ.get('YADO_SUCCESSOR_TEST_MANIFEST', ROOT / 'successor/state/birth-v2/manifest.json'))


def product_goal():
    def row(x, y):
        return {'input': {'x': x, 'y': y}, 'expected': x * y + x}
    return {'domain': 'native_source',
            'training': [row(-3, 2), row(-2, -1), row(-1, 4), row(0, 0),
                         row(1, -3), row(2, 5), row(3, 1)],
            'validation': [row(7, -2), row(-8, 3), row(11, 4)],
            'queries': [{'input': {'x': 19, 'y': -7}}, {'input': {'x': -13, 'y': 9}}]}


class NativeBindingTests(unittest.TestCase):
    def setUp(self):
        if not MANIFEST.exists():
            self.skipTest('Build the pinned successor before integration tests')
        self.tmp = tempfile.TemporaryDirectory()
        self.state = Path(self.tmp.name) / 'state.sqlite'
        self.kernel = SuccessorKernel(MANIFEST, self.state)
        self.kernel.db.execute('PRAGMA journal_mode=DELETE')

    def tearDown(self):
        if hasattr(self, 'kernel'):
            self.kernel.close()
            self.tmp.cleanup()

    def test_activation_makes_an_old_failure_eligible_for_its_own_retry(self):
        old_id = self.kernel.open_goal(product_goal(), budget=6)
        self.kernel.think(40)
        old = self.kernel.cognitive_snapshot()['goals'][str(old_id)]
        self.assertEqual(old['status'], 'WITHHOLD')
        self.kernel.activate_native_synthesis()
        sid = self.kernel.start_autonomy(budget=20, max_cycles=1)
        self.kernel.run_autonomy(40)
        session = self.kernel.autonomy_snapshot()['sessions'][sid]
        self.assertEqual(session['status'], 'COMPLETE')
        self.assertEqual(session['selections'][0]['route'], 'RETRY_FAILURE')
        self.assertEqual(session['selections'][0]['evidence']['parent_goal_id'], old_id)
        goal_id = session['outcomes'][0]['goal_id']
        goal = self.kernel.cognitive_snapshot()['goals'][str(goal_id)]
        self.assertEqual(goal['status'], 'VALIDATED_ON_HOLDOUT')
        self.assertIn('native_evolved_v2', goal['attempted'])
        self.assertEqual(goal['result']['predictions'], [-114, -130])
        self.assertEqual(self.kernel.cognitive_snapshot()['goals'][str(old_id)], old)
        self.kernel.close()
        self.kernel = SuccessorKernel(MANIFEST, self.state)
        self.kernel.db.execute('PRAGMA journal_mode=DELETE')
        self.assertEqual(self.kernel.cognitive_snapshot()['goals'][str(goal_id)], goal)

    def test_bad_validation_cannot_select_a_different_program(self):
        self.kernel.activate_native_synthesis()
        spec = product_goal()
        spec['validation'][0]['expected'] += 1
        goal_id = self.kernel.open_goal(spec, budget=10)
        self.kernel.think(50)
        goal = self.kernel.cognitive_snapshot()['goals'][str(goal_id)]
        self.assertEqual(goal['status'], 'WITHHOLD')
        self.assertIn('native_evolved_v2', goal['attempted'])

    def test_activation_is_idempotent_and_rejects_a_pending_goal(self):
        goal_id = self.kernel.open_goal(product_goal())
        with self.assertRaisesRegex(ValueError, 'IDLE'):
            self.kernel.activate_native_synthesis()
        self.kernel.stop_goal(goal_id)
        first = self.kernel.activate_native_synthesis()
        before = self.kernel.verify_state()
        self.assertEqual(self.kernel.activate_native_synthesis(), first)
        self.assertEqual(self.kernel.verify_state(), before)


if __name__ == '__main__':
    unittest.main()
