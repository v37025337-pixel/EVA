import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from successor.continuity import prepare_upgrade
from successor.kernel import SuccessorKernel, decode

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(os.environ.get('YADO_SUCCESSOR_TEST_MANIFEST', ROOT / 'successor/state/birth-v2/manifest.json'))


class ContinuityTests(unittest.TestCase):
    def setUp(self):
        if not MANIFEST.exists():
            self.skipTest('Build the pinned successor before integration tests')
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.state = self.root / 'parent.sqlite'
        with_kernel = SuccessorKernel(MANIFEST, self.state)
        with_kernel.db.execute('PRAGMA journal_mode=DELETE')
        try:
            goal = with_kernel.open_goal({'domain': 'relation', 'relation': [[1, 2], [2, 3]], 'start': 1})
            with_kernel.think(20)
            sid = with_kernel.start_autonomy(budget=3, max_cycles=1)
            with_kernel.run_autonomy(30)
            self.assertEqual(with_kernel.autonomy_snapshot()['sessions'][sid]['status'], 'COMPLETE')
            self.before = with_kernel.verify_state()
            self.identity = with_kernel.identity
            self.goals = with_kernel.cognitive_snapshot()['goals']
        finally:
            with_kernel.close()

    def tearDown(self):
        if hasattr(self, 'tmp'):
            self.tmp.cleanup()

    def test_upgrade_preserves_history_identity_and_autonomous_choices(self):
        result = prepare_upgrade(MANIFEST, self.state, self.root / 'upgrade')
        k = SuccessorKernel(result['manifest'], result['state'])
        k.db.execute('PRAGMA journal_mode=DELETE')
        try:
            self.assertEqual(k.identity, self.identity)
            self.assertNotEqual(k.implementation_identity, self.identity)
            self.assertEqual(k.verify_state()['tick'], self.before['tick'] + 1)
            self.assertEqual(k.cognitive_snapshot()['goals'], self.goals)
            k.activate_native_synthesis()
            self.assertEqual(k.verify_state()['status'], 'PASS')
        finally:
            k.close()
        with sqlite3.connect(self.state) as old:
            self.assertEqual(old.execute('SELECT MAX(tick) FROM events').fetchone()[0], self.before['tick'])

    def test_changed_predecessor_or_missing_upgrade_event_is_rejected(self):
        result = prepare_upgrade(MANIFEST, self.state, self.root / 'upgrade')
        with sqlite3.connect(result['state']) as db:
            db.execute('DELETE FROM events WHERE tick=?', (self.before['tick'] + 1,))
        with self.assertRaisesRegex(ValueError, 'UPGRADE_EVENT'):
            SuccessorKernel(result['manifest'], result['state'])
        with self.assertRaisesRegex(ValueError, 'UPGRADE_EVENT'):
            prepare_upgrade(result['manifest'], result['state'], self.root / 'invalid-second-upgrade')
        result = prepare_upgrade(MANIFEST, self.state, self.root / 'another')
        predecessor = self.root / 'another/predecessor-state.sqlite'
        with sqlite3.connect(predecessor) as db:
            db.execute("UPDATE identity SET digest='changed' WHERE id=1")
        with self.assertRaisesRegex(ValueError, 'PREDECESSOR_STATE_CHANGED'):
            SuccessorKernel(result['manifest'], result['state'])

    def test_upgrade_command_works_in_a_clean_process_and_can_continue(self):
        command = [sys.executable, '-m', 'successor.continuity', '--parent-manifest', str(MANIFEST),
                   '--parent-state', str(self.state), '--output', str(self.root / 'standalone')]
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=60)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        second = prepare_upgrade(result['manifest'], result['state'], self.root / 'second')
        k = SuccessorKernel(second['manifest'], second['state'])
        try:
            self.assertEqual(k.identity, self.identity)
            self.assertEqual(k.cognitive_snapshot()['goals'], self.goals)
            self.assertEqual(k.verify_state()['tick'], self.before['tick'] + 2)
        finally:
            k.close()


if __name__ == '__main__':
    unittest.main()
