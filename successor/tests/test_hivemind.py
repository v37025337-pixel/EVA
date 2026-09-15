import copy
import json
import os
from pathlib import Path
import tempfile
import unittest

from successor.hivemind import CRITERIA, SCHEMA, run_issue
from successor.continuity import prepare_upgrade
from successor.kernel import SuccessorKernel
from successor.tests.test_native_binding import product_goal

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(os.environ.get('YADO_SUCCESSOR_TEST_MANIFEST', ROOT / 'successor/state/birth-v2/manifest.json'))


class Tracker:
    """In-memory fake at the external MCP boundary; the kernel stays real."""
    def __init__(self, spec):
        self.issue = {'id': 'YADO-1.1', 'state': 'todo',
                      'description': json.dumps({'schema': SCHEMA, 'spec': spec, 'budget': 6}),
                      'acceptanceCriteria': [{'text': text, 'done': False} for text in CRITERIA],
                      'activity': []}
        self.fail_comment = False
        self.lose_comment = False

    def call(self, name, arguments):
        if name == 'hive_get_issue':
            value = copy.deepcopy(self.issue)
            if self.lose_comment and value['state'] == 'done':
                value['activity'] = []
            return value
        if name == 'hive_add_comment':
            if self.fail_comment:
                self.fail_comment = False
                raise RuntimeError('transport lost before result publication')
            self.issue['activity'].append({'message': arguments['message']})
        elif name == 'hive_mark_acceptance':
            self.issue['acceptanceCriteria'][arguments['index']]['done'] = arguments['done']
        elif name == 'hive_set_state':
            self.issue['state'] = arguments['state']
            if arguments.get('note'):
                self.issue['activity'].append({'message': arguments['note']})
        else:
            raise AssertionError(name)
        return copy.deepcopy(self.issue)


class HivemindBridgeTests(unittest.TestCase):
    def setUp(self):
        if not MANIFEST.exists():
            self.skipTest('Build the pinned successor before integration tests')
        self.tmp = tempfile.TemporaryDirectory()
        self.state = Path(self.tmp.name) / 'kernel.sqlite'
        self.kernel = SuccessorKernel(MANIFEST, self.state)
        self.kernel.db.execute('PRAGMA journal_mode=DELETE')
        self.tracker = Tracker({'domain': 'relation', 'relation': [[1, 2], [2, 3]], 'start': 1})

    def tearDown(self):
        if hasattr(self, 'kernel'):
            self.kernel.close()
            self.tmp.cleanup()

    def run_issue(self, **kwargs):
        return run_issue(self.kernel, self.tracker, 'test-workspace', 'YADO-1.1', **kwargs)

    def test_transport_retry_preserves_one_goal_and_idempotent_publication(self):
        self.tracker.fail_comment = True
        with self.assertRaisesRegex(RuntimeError, 'transport'):
            self.run_issue()
        before = self.kernel.verify_state()
        result = self.run_issue()
        self.assertTrue(result['passed'])
        self.assertEqual(self.tracker.issue['state'], 'done')
        self.assertEqual(len(self.kernel.cognitive_snapshot()['goals']), 1)
        self.assertEqual(self.kernel.verify_state(), before)
        saved = copy.deepcopy(self.tracker.issue)
        self.assertEqual(self.run_issue(), result)
        self.assertEqual(self.tracker.issue, saved)

    def test_withhold_is_reviewable_and_never_marked_done(self):
        self.tracker = Tracker(product_goal())
        result = self.run_issue()
        self.assertEqual(result['status'], 'WITHHOLD')
        self.assertEqual(self.tracker.issue['state'], 'in_review')
        self.assertFalse(self.tracker.issue['acceptanceCriteria'][0]['done'])
        self.assertTrue(self.tracker.issue['acceptanceCriteria'][1]['done'])

    def test_cancel_stops_pending_goal_even_if_description_was_removed(self):
        first = self.run_issue(max_steps=1)
        self.assertEqual(first['status'], 'ACTIVE')
        self.assertFalse(first['result_recorded'])
        self.assertFalse(self.tracker.issue['acceptanceCriteria'][1]['done'])
        self.tracker.issue.update(state='cancelled', description='', acceptanceCriteria=[])
        result = self.run_issue()
        self.assertEqual(result['status'], 'CANCELLED')
        self.assertEqual(self.kernel.cognitive_snapshot()['goals'][str(first['goal_id'])]['status'], 'STOPPED')

    def test_changed_request_cannot_reuse_an_old_success(self):
        self.run_issue()
        before = self.kernel.verify_state()
        value = json.loads(self.tracker.issue['description'])
        value['spec']['start'] = 2
        self.tracker.issue['description'] = json.dumps(value)
        with self.assertRaisesRegex(ValueError, 'REQUEST_CHANGED'):
            self.run_issue()
        self.assertEqual(self.kernel.verify_state(), before)

    def test_untyped_description_is_rejected_before_intake(self):
        self.tracker.issue['description'] = json.dumps({'schema': SCHEMA, 'shell': 'arbitrary command'})
        with self.assertRaisesRegex(ValueError, 'TYPED_GOAL'):
            self.run_issue()
        self.assertEqual(self.kernel.verify_state()['tick'], 0)

    def test_missing_tracker_receipt_is_not_reported_as_published(self):
        self.tracker.lose_comment = True
        with self.assertRaisesRegex(ValueError, 'READBACK_FAILED'):
            self.run_issue()
        self.assertEqual(len(self.kernel.cognitive_snapshot()['goals']), 1)

    def test_publication_after_upgrade_keeps_execution_provenance(self):
        first = self.run_issue()
        self.kernel.close()
        upgraded = prepare_upgrade(MANIFEST, self.state, Path(self.tmp.name) / 'upgrade')
        self.kernel = SuccessorKernel(upgraded['manifest'], upgraded['state'])
        self.kernel.db.execute('PRAGMA journal_mode=DELETE')
        second = self.run_issue()
        self.assertEqual(second['goal_id'], first['goal_id'])
        self.assertEqual(second['execution_implementation_identity'], first['execution_implementation_identity'])
        self.assertNotEqual(second['publisher_implementation_identity'], first['publisher_implementation_identity'])
        self.assertEqual(second['result_digest'], first['result_digest'])


if __name__ == '__main__':
    unittest.main()
