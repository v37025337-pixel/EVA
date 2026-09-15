import copy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from successor.kernel import SuccessorKernel, fingerprint, equivalent
from successor.generation import (GenerationKernel, discover, select, evaluate,
    parent_profile, execute_component, admission_passed)
from successor.generation_tasks import challenge

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(os.environ.get('YADO_SUCCESSOR_TEST_MANIFEST', ROOT / 'successor/state/birth-v2/manifest.json'))


class GenerationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kernel = SuccessorKernel(MANIFEST, Path(self.tmp.name) / 'kernel.sqlite')
        self.kernel.db.execute('PRAGMA journal_mode=DELETE')
        self.state = Path(self.tmp.name) / 'generation.sqlite'
        self.archive_path = Path(os.environ.get('YADO_GENERATION_TEST_ARCHIVE', self.kernel.archive.path))
        self.generation = GenerationKernel(self.kernel, self.archive_path, self.state)

    def tearDown(self):
        self.generation.close()
        self.kernel.close()
        self.tmp.cleanup()

    def test_memory_recombination_rejects_real_planner_regressions(self):
        options = discover(self.generation.archive)
        self.assertGreaterEqual(len(options), 16)
        tasks, protected = challenge('development'), challenge('development', retention=True)
        profile, evidence = select(options, tasks, protected)
        self.assertEqual(profile['THINKING']['family'], 'genome')
        rejected = [row for row in evidence if row['organ'] == 'THINKING' and row['regressions']]
        self.assertEqual(len(rejected), 3)
        self.assertTrue(all(len(row['regressions']) >= 4 for row in rejected))
        self.assertEqual(select([], tasks, protected)[0], parent_profile())
        fresh = challenge('unseen schema and coefficients')
        self.assertTrue(all(x == 1 for x in evaluate(profile, fresh)['scores'].values()))
        self.assertTrue(all(x == 0 for x in evaluate(parent_profile(), fresh)['scores'].values()))

    def test_frozen_child_activates_executes_restarts_and_rolls_back(self):
        gid = self.kernel.open_goal({'domain': 'relation', 'relation': [[1, 2], [2, 3]], 'start': 1})
        self.kernel.think(20)
        # Re-create birth after the observed goal; the previous empty journal
        # belongs only to this isolated test fixture.
        self.generation.close()
        self.state.unlink()
        self.generation = GenerationKernel(self.kernel, self.archive_path, self.state)
        proposal = self.generation.propose()
        admitted = self.generation.admit()
        self.assertTrue(admitted['passed'])
        self.assertEqual(admitted['inherited_memory']['goals'], 1)
        self.assertEqual(admitted['inherited_memory']['checks'][0]['goal_id'], gid)
        before = self.generation.snapshot()
        self.generation.close()
        self.generation = GenerationKernel(self.kernel, self.archive_path, self.state)
        self.assertEqual(self.generation.snapshot(), before)
        for task, expected in challenge('post-restart'):
            result = self.generation.execute(task)
            self.assertTrue(equivalent(result['result']['answer'], expected))
            self.assertEqual(result['profile_digest'], proposal['profile_digest'])
            self.assertEqual(result['generation'], 1)
        self.generation.rollback()
        self.assertEqual(self.generation.snapshot()['component_generation'], 0)
        planning = next(t for t, _ in challenge('rollback') if t['organ'] == 'THINKING')
        self.assertEqual(self.generation.execute(planning)['result']['answer'], planning['stages'][0]['stage_id'])

    def test_activation_without_audit_is_rejected(self):
        self.generation._append({'kind': 'ACTIVATE', 'admission_tick': 0, 'profile_digest': 'forged'})
        with self.assertRaisesRegex(ValueError, 'ACTIVATION_WITHOUT_ADMISSION'):
            self.generation.snapshot()

    def test_self_consistent_forged_proposal_is_recomputed(self):
        proposal = self.generation.propose()
        self.generation.close()
        self.state.unlink()
        self.generation = GenerationKernel(self.kernel, self.archive_path, self.state)
        forged = {k: copy.deepcopy(v) for k, v in proposal.items() if k not in ('tick', 'event_hash')}
        forged['profile'] = parent_profile()
        forged['profile_digest'] = fingerprint(forged['profile'])
        self.generation._append(forged)
        with self.assertRaisesRegex(ValueError, 'SELECTION_NOT_REPRODUCIBLE'):
            self.generation.snapshot()

    def test_interrupted_activation_has_no_partial_admission(self):
        self.generation.propose()
        before = self.generation.snapshot()
        append = self.generation._append
        def interrupt(body):
            if body['kind'] == 'ACTIVATE':
                raise KeyboardInterrupt()
            return append(body)
        with patch.object(self.generation, '_append', side_effect=interrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.generation.admit()
        self.assertEqual(self.generation.snapshot(), before)

    def test_failed_retention_withholds_activation(self):
        self.generation.propose()
        with patch('successor.generation.retained_memory', return_value={'goals': 1, 'passed': False, 'checks': []}):
            result = self.generation.admit()
            self.assertFalse(result['passed'])
            self.assertEqual(self.generation.snapshot()['component_generation'], 0)
        self.assertFalse(any(r['kind'] == 'ACTIVATE' for r in self.generation.records()))

    def test_source_drift_and_input_bounds_prevent_execution(self):
        task = next(t for t, _ in challenge('budget') if t['organ'] == 'THINKING')
        task['stages'] *= 5
        with self.assertRaisesRegex(ValueError, 'STAGE_BUDGET'):
            self.generation.execute(task)
        with patch('successor.generation.sources', return_value={}):
            with self.assertRaisesRegex(ValueError, 'SOURCE_DRIFT'):
                self.generation.propose()
        self.assertEqual(len(self.generation.records()), 1)


if __name__ == '__main__':
    unittest.main()
