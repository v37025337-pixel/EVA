"""Reviewed source maintenance preserves history and remeasures live components.

The predecessor fixture uses the exact reviewed historical source pins while
executing the trusted current adapters. No archived implementation is imported.
"""
import copy
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from successor.archive import sha
from successor.component_binding import EVENT
from successor.continuity import prepare_upgrade
from successor.generation import (GenerationKernel, LEGACY_SOURCES,
    PRE_MAINTENANCE_SOURCES, SOURCE_TRANSITION, sources, upgrade_component_state)
from successor.generation_tasks import challenge
from successor.kernel import SuccessorKernel, decode, encode

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(os.environ.get('YADO_SUCCESSOR_TEST_MANIFEST',
                               ROOT / 'successor/state/birth-v2/manifest.json'))


def rewrite_event(state, tick, change):
    """Rehash a locally copied journal so semantic checks must reject the edit."""
    with sqlite3.connect(state) as db:
        previous = '0' * 64
        for index, raw in db.execute('SELECT tick,body FROM events ORDER BY tick').fetchall():
            if index == tick:
                body = decode(raw)
                change(body)
                raw = encode(body)
            digest = sha((previous + '\n' + str(index) + '\n' + raw).encode())
            db.execute('UPDATE events SET body=?,previous_hash=?,event_hash=? WHERE tick=?',
                       (raw, previous, digest, index))
            previous = digest


class ComponentSourceMaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.predecessor = self.root / 'predecessor.sqlite'
        kernel = SuccessorKernel(MANIFEST, self.predecessor)
        try:
            kernel.db.execute('PRAGMA journal_mode=DELETE')
            # Pin only this fixture's component controller to the known older
            # version; selection/admission still execute and measure real code.
            with patch('successor.generation.sources', return_value=copy.deepcopy(PRE_MAINTENANCE_SOURCES)), \
                    patch('successor.component_binding.sources', return_value=copy.deepcopy(PRE_MAINTENANCE_SOURCES)):
                self.proposal = kernel.propose_component_generation()
                self.admission = kernel.admit_component_generation()
                self.assertTrue(self.admission['passed'])
                task, expected = next((t, e) for t, e in challenge('maintenance-main')
                                      if t['organ'] == 'THINKING')
                self.request = {'kind': 'component', 'payload': task,
                                'expect': {'path': ['answer'], 'equals': expected}}
                self.assertEqual(kernel.execute(self.request)['status'], 'VERIFIED')
                self.before = kernel.verify_state()
                self.identity = kernel.identity
                self.prefix = [tuple(r) for r in kernel.db.execute('SELECT * FROM events ORDER BY tick')]
        finally:
            kernel.close()

    def migrate(self):
        result = prepare_upgrade(MANIFEST, self.predecessor, self.root / 'upgrade')
        self.assertTrue(result['component_readmission_required'])
        return result, SuccessorKernel(result['manifest'], result['state'])

    def test_exact_transition_requires_fresh_readmission_and_survives_restart(self):
        result, kernel = self.migrate()
        try:
            state = kernel.component_generation_snapshot()
            self.assertFalse(state['execution_admitted'])
            self.assertEqual(state['profile_digest'], self.proposal['profile_digest'])
            self.assertEqual(kernel.identity, self.identity)
            self.assertEqual(kernel.verify_state()['tick'], self.before['tick'] + 2)
            before_execution = kernel.verify_state()
            with self.assertRaisesRegex(ValueError, 'GENERATION_REQUIRES_READMISSION'):
                kernel.execute(self.request)
            self.assertEqual(kernel.verify_state(), before_execution)
            admission = kernel.readmit_component_generation()
            self.assertTrue(admission['passed'], admission)
            self.assertNotEqual(admission['fresh_seed'], self.admission['fresh_seed'])
            self.assertTrue(all(v == 1 for v in admission['child']['scores'].values()))
            self.assertEqual(kernel.execute(self.request)['status'], 'VERIFIED')
            self.assertEqual([tuple(r) for r in kernel.db.execute(
                'SELECT * FROM events WHERE tick<=? ORDER BY tick', (self.before['tick'],))], self.prefix)
        finally:
            kernel.close()
        kernel = SuccessorKernel(result['manifest'], result['state'])
        try:
            self.assertTrue(kernel.component_generation_snapshot()['execution_admitted'])
            self.assertEqual(kernel.verify_state()['status'], 'PASS')
            events = [decode(r['body'])['event'] for r in kernel.db.execute('SELECT body FROM events')
                      if decode(r['body']).get('kind') == EVENT]
            self.assertEqual(events[0]['sources'], PRE_MAINTENANCE_SOURCES)
            upgrade = next(r for r in events if r['kind'] == 'SOURCE_UPGRADE')
            self.assertEqual(upgrade['transition_id'], SOURCE_TRANSITION)
            self.assertEqual(upgrade['sources'], sources())
        finally:
            kernel.close()
        with sqlite3.connect(self.predecessor) as db:
            self.assertEqual(db.execute('SELECT * FROM events ORDER BY tick').fetchall(), self.prefix)

    def test_component_upgrade_must_bind_the_main_implementation_event(self):
        result, kernel = self.migrate()
        kernel.close()
        rewrite_event(result['state'], self.before['tick'] + 2,
                      lambda body: body['event'].update(implementation_identity='f' * 64))
        with self.assertRaisesRegex(ValueError, 'COMPONENT_JOURNAL_IMPLEMENTATION_UPGRADE_BINDING'):
            SuccessorKernel(result['manifest'], result['state'])

    def test_fresh_pass_claim_cannot_replace_reproducible_readmission(self):
        result, kernel = self.migrate()
        try:
            admission = kernel.readmit_component_generation()
            self.assertTrue(admission['passed'])
        finally:
            kernel.close()
        rewrite_event(result['state'], admission['tick'],
                      lambda body: body['event']['child']['outcomes'][0].update(answer='forged'))
        with self.assertRaisesRegex(ValueError, 'GENERATION_READMISSION_NOT_REPRODUCIBLE'):
            SuccessorKernel(result['manifest'], result['state'])


class StandaloneSourceMaintenanceTests(unittest.TestCase):
    def test_original_readmission_does_not_authorize_the_next_source_upgrade(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            kernel = SuccessorKernel(MANIFEST, root / 'kernel.sqlite')
            self.addCleanup(kernel.close)
            predecessor = root / 'old-components.sqlite'
            with patch('successor.generation.sources', return_value=copy.deepcopy(LEGACY_SOURCES)):
                generation = GenerationKernel(kernel, kernel.archive.path, predecessor)
                try:
                    generation.propose()
                    self.assertTrue(generation.admit()['passed'])
                    last = generation.records()[-1]
                    generation._append({'kind': 'SOURCE_UPGRADE',
                        'previous_sources': copy.deepcopy(LEGACY_SOURCES),
                        'sources': copy.deepcopy(PRE_MAINTENANCE_SOURCES),
                        'predecessor_tick': last['tick'], 'predecessor_event_hash': last['event_hash'],
                        'parent_state': kernel.verify_state()})
                finally:
                    generation.close()
            with patch('successor.generation.sources', return_value=copy.deepcopy(PRE_MAINTENANCE_SOURCES)):
                generation = GenerationKernel(kernel, kernel.archive.path, predecessor)
                try:
                    old_readmission = generation.readmit()
                    self.assertTrue(old_readmission['passed'])
                    prefix = generation.db.execute('SELECT * FROM events ORDER BY tick').fetchall()
                finally:
                    generation.close()
            migrated = root / 'components.sqlite'
            status = upgrade_component_state(kernel, kernel.archive.path, predecessor, migrated)
            self.assertFalse(status['execution_admitted'])
            self.assertIsNone(status['readmission_passed'])
            generation = GenerationKernel(kernel, kernel.archive.path, migrated)
            try:
                task, expected = next((t, e) for t, e in challenge('standalone-maintenance')
                                      if t['organ'] == 'THINKING')
                with self.assertRaisesRegex(ValueError, 'GENERATION_REQUIRES_READMISSION'):
                    generation.execute(task)
                readmission = generation.readmit()
                self.assertTrue(readmission['passed'])
                self.assertNotEqual(readmission['upgrade_tick'], old_readmission['upgrade_tick'])
                self.assertNotEqual(readmission['fresh_seed'], old_readmission['fresh_seed'])
                self.assertEqual(generation.execute(task)['result']['answer'], expected)
                self.assertEqual(generation.db.execute(
                    'SELECT * FROM events ORDER BY tick').fetchall()[:len(prefix)], prefix)
            finally:
                generation.close()
            with sqlite3.connect(predecessor) as db:
                self.assertEqual(db.execute('SELECT * FROM events ORDER BY tick').fetchall(), prefix)


if __name__ == '__main__':
    unittest.main()
