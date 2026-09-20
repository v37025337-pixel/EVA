"""Real genetic components must execute through the durable main kernel."""
import copy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from successor.kernel import SuccessorKernel
from successor.generation_tasks import challenge

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(os.environ.get('YADO_SUCCESSOR_TEST_MANIFEST',
                               ROOT / 'successor/state/birth-v2/manifest.json'))


def public_task(task, expected):
    return {'kind': 'component', 'payload': copy.deepcopy(task),
            'expect': {'path': ['answer'], 'equals': expected}}


class ComponentBindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = Path(self.tmp.name) / 'kernel.sqlite'
        self.kernel = SuccessorKernel(MANIFEST, self.state)

    def tearDown(self):
        self.kernel.close()
        self.tmp.cleanup()

    def activate(self):
        proposal = self.kernel.propose_component_generation()
        admission = self.kernel.admit_component_generation()
        self.assertTrue(admission['passed'], admission)
        return proposal, admission

    def test_failed_main_task_uses_admitted_gene_after_restart(self):
        task, expected = next((t, e) for t, e in challenge('shared-main-runtime')
                              if t['organ'] == 'THINKING')
        request = public_task(task, expected)
        before = self.kernel.execute(request)
        self.assertEqual(before['status'], 'FAIL')
        proposal, _ = self.activate()
        self.kernel.close()
        self.kernel = SuccessorKernel(MANIFEST, self.state)
        after = self.kernel.execute(request)
        self.assertEqual(after['status'], 'VERIFIED', after)
        self.assertEqual(after['result']['profile_digest'], proposal['profile_digest'])
        self.assertNotEqual(before['task_signature'], after['task_signature'])
        self.assertEqual(self.kernel.verify_state()['status'], 'PASS')

    def test_all_four_organs_share_queue_memory_and_native_learning(self):
        from successor.tests.test_active_native_loop import reverse_goal
        goal = self.kernel.open_goal(reverse_goal())
        self.kernel.think(20)
        _, admission = self.activate()
        self.assertEqual(admission['inherited_memory']['goals'], 1)
        self.assertEqual(admission['inherited_memory']['checks'][0]['goal_id'], goal)
        cases = challenge('fresh-common-queue')
        jobs = self.kernel.submit('Use the admitted four-organ genome',
                                  [public_task(t, e) for t, e in cases])
        results = self.kernel.resume(10)
        self.assertEqual(len(results), len(jobs))
        self.assertTrue(all(r['status'] == 'VERIFIED' for r in results), results)
        self.assertEqual({r['task']['payload']['organ'] for r in results},
                         {'LOGIC', 'THINKING', 'INTELLIGENCE', 'CODE'})
        self.assertTrue(all(r['result']['component_generation'] == 1 for r in results))
        self.assertEqual(self.kernel.cognitive_snapshot()['goals'][str(goal)]['status'], 'VALIDATED_ON_HOLDOUT')
        recalled = self.kernel.open_goal(reverse_goal(), budget=1)
        self.kernel.think(20)
        learned = self.kernel.cognitive_snapshot()['goals'][str(recalled)]
        self.assertEqual(learned['attempted'], ['reuse_verified_source'])
        self.assertEqual(learned['result']['predictions'], ['pon'])
        self.assertEqual(self.kernel.snapshot()['jobs'], {'VERIFIED': 4})
        self.assertEqual(len(list(Path(self.tmp.name).glob('*.sqlite'))), 1)

    def test_rollback_changes_main_execution_and_preserves_history(self):
        self.activate()
        task, expected = next((t, e) for t, e in challenge('rollback-main')
                              if t['organ'] == 'THINKING')
        request = public_task(task, expected)
        self.assertEqual(self.kernel.execute(request)['status'], 'VERIFIED')
        self.kernel.rollback_component_generation()
        result = self.kernel.execute(request)
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['result']['component_generation'], 0)
        self.assertEqual(self.kernel.component_generation_snapshot()['component_generation'], 0)
        self.assertEqual(self.kernel.verify_state()['status'], 'PASS')

    def test_admission_and_activation_are_atomic_in_main_journal(self):
        self.kernel.propose_component_generation()
        before = self.kernel.verify_state()
        original = self.kernel._append

        def interrupt(body):
            if body.get('kind') == 'COMPONENT_GENERATION' and body['event']['kind'] == 'ACTIVATE':
                raise KeyboardInterrupt()
            return original(body)

        with patch.object(self.kernel, '_append', side_effect=interrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.kernel.admit_component_generation()
        self.assertEqual(self.kernel.verify_state(), before)
        self.assertTrue(self.kernel.admit_component_generation()['passed'])

    def test_unadmitted_activation_is_rejected_by_main_verification(self):
        self.kernel.propose_component_generation()
        self.kernel._append({'kind': 'COMPONENT_GENERATION', 'event': {
            'kind': 'ACTIVATE', 'admission_tick': 0, 'profile_digest': 'forged'}})
        with self.assertRaisesRegex(ValueError, 'ACTIVATION_WITHOUT_ADMISSION'):
            self.kernel.verify_state()

    def test_reading_component_status_does_not_create_events(self):
        before = self.kernel.verify_state()
        status = self.kernel.component_generation_snapshot()
        self.assertEqual(status['component_generation'], 0)
        self.assertEqual(status['events'], 0)
        self.assertEqual(self.kernel.verify_state(), before)

    def test_false_main_result_cannot_borrow_a_real_execution_receipt(self):
        task, expected = next((t, e) for t, e in challenge('forged-main-result', retention=True)
                              if t['organ'] == 'THINKING')
        result = self.kernel.execute(public_task(task, expected))
        self.assertEqual(result['status'], 'VERIFIED')
        forged = {k: copy.deepcopy(v) for k, v in result.items() if k not in {'tick', 'event_hash'}}
        forged['result']['answer'] = 'invented-result'
        self.kernel._append(forged)
        with self.assertRaisesRegex(ValueError, 'COMPONENT_MAIN_EXECUTION_LINK'):
            self.kernel.verify_state()


if __name__ == '__main__':
    unittest.main()
