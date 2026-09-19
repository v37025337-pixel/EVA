"""An implementation migration must preserve its inherited memory boundary."""
import copy
import sqlite3
from types import SimpleNamespace
import unittest

from successor.generation import GenerationKernel, LEGACY_SOURCES, sources


class GenerationUpgradeProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.native = sqlite3.connect(':memory:')
        self.native.execute('CREATE TABLE events(tick INTEGER PRIMARY KEY, event_hash TEXT)')
        self.native.executemany('INSERT INTO events VALUES(?, ?)', [(7, 'a' * 64), (9, 'b' * 64)])
        self.generation = GenerationKernel.__new__(GenerationKernel)
        self.generation.kernel = SimpleNamespace(db=self.native, _check_sources=lambda: None)
        self.generation.db = sqlite3.connect(':memory:', isolation_level=None)
        self.generation.db.execute('CREATE TABLE events(tick INTEGER PRIMARY KEY, body TEXT, hash TEXT)')
        self.generation._verified_replays = set()
        self.generation._append({'kind': 'BIRTH', 'sources': copy.deepcopy(LEGACY_SOURCES),
            'parent_state': self.parent_state(7), 'branches': [], 'canonical_generation': 'G2'})
        self.generation.birth = self.generation.records()[0]
        self.generation.pinned_sources = sources()

    def tearDown(self):
        self.generation.db.close()
        self.native.close()

    def parent_state(self, tick):
        return {'tick': tick, 'event_hash': {0: '0' * 64, 7: 'a' * 64, 9: 'b' * 64}[tick],
                'status': 'PASS'}

    def upgrade(self, tick=9, **changes):
        previous = self.generation.records()[-1]
        body = {'kind': 'SOURCE_UPGRADE', 'previous_sources': copy.deepcopy(LEGACY_SOURCES),
                'sources': sources(), 'predecessor_tick': previous['tick'],
                'predecessor_event_hash': previous['event_hash'], 'parent_state': self.parent_state(tick)}
        body.update(changes)
        return self.generation._append(body)

    def test_matching_upgrade_requires_readmission_before_execution(self):
        self.upgrade()
        state = self.generation.snapshot()
        self.assertFalse(state['execution_admitted'])
        self.assertIsNone(state['readmission_passed'])
        with self.assertRaisesRegex(ValueError, 'GENERATION_REQUIRES_READMISSION'):
            self.generation.execute({'organ': 'THINKING'})
        self.assertEqual(self.generation.snapshot(), state)

    def test_upgrade_cannot_move_parent_memory_before_birth(self):
        self.upgrade(tick=0)
        with self.assertRaisesRegex(ValueError, 'GENERATION_SOURCE_UPGRADE_MEMORY_BOUNDARY'):
            self.generation.snapshot()

    def test_upgrade_rejects_unknown_previous_source_pins(self):
        pins = copy.deepcopy(LEGACY_SOURCES)
        pins['successor/generation.py'] = 'c' * 64
        self.upgrade(previous_sources=pins)
        with self.assertRaisesRegex(ValueError, 'GENERATION_SOURCE_UPGRADE_PROVENANCE'):
            self.generation.snapshot()

    def test_upgrade_rejects_wrong_predecessor_hash(self):
        self.upgrade(predecessor_event_hash='d' * 64)
        with self.assertRaisesRegex(ValueError, 'GENERATION_SOURCE_UPGRADE_PROVENANCE'):
            self.generation.snapshot()

    def test_upgrade_rejects_wrong_native_parent_hash(self):
        state = self.parent_state(9)
        state['event_hash'] = 'e' * 64
        self.upgrade(parent_state=state)
        with self.assertRaisesRegex(ValueError, 'GENERATION_PARENT_MEMORY_DRIFT'):
            self.generation.snapshot()

    def test_second_unreviewed_upgrade_is_rejected(self):
        self.upgrade()
        self.upgrade()
        with self.assertRaisesRegex(ValueError, 'GENERATION_SOURCE_UPGRADE_PROVENANCE'):
            self.generation.snapshot()


if __name__ == '__main__':
    unittest.main()
