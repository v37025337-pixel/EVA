import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from successor.kernel import SuccessorKernel
from successor.runtime_evolution import (REQUEST, SELECTION_POLICY, RuntimeEvolution, active_candidates,
                                         evaluation_passed, normalize_request, select_candidate)


class RuntimeEvolutionContractTests(unittest.TestCase):
    def test_objective_cannot_carry_a_program_or_a_claimed_admission(self):
        value = {'schema': 'yado.hivemind.runtime-evolution.v1',
                 'objective': 'repair_native_source_failures'}
        self.assertEqual(normalize_request(value), value)
        for key in ('source', 'passed', 'command', 'candidate', 'regression'):
            with self.assertRaises(ValueError):
                normalize_request({**value, key: 'supplied'})

    def test_no_experience_cannot_generate_a_mechanism(self):
        self.assertIsNone(select_candidate({}))

    def test_historical_success_is_not_a_runtime_deficit(self):
        goal = {'id': 1, 'status': 'VALIDATED_ON_HOLDOUT', 'mode': 'full',
                'spec': {'domain': 'native_source', 'training': []}, 'attempted': ['native_evolved_v2']}
        self.assertIsNone(select_candidate({1: goal}))

    def test_missing_or_incomplete_gates_cannot_admit(self):
        for value in ({}, {'passed': True}, {'regression': {'status': 'PASS'}}):
            self.assertFalse(evaluation_passed(value))

    def test_active_more_capable_mechanism_prevents_a_redundant_proposal(self):
        from successor.native_mechanism import build_candidate
        training = [{'input': {'x': x}, 'expected': 10 - x * x} for x in range(-3, 4)]
        goal = {'id': 1, 'status': 'WITHHOLD', 'mode': 'full',
                'spec': {'domain': 'native_source', 'training': training}, 'attempted': ['native_evolved_v2']}
        self.assertEqual(select_candidate({1: goal})['max_degree'], 2)
        parent = build_candidate(3)
        self.assertIsNone(select_candidate({1: goal}, [parent['source_sha256']], [parent]))

    def test_success_flags_cannot_override_failed_trial_details(self):
        value = {'candidate_sha256': 'frozen',
                 'regression': {'status': 'PASS', 'returncode': 0, 'tests_run': 262,
                     'expected_tests': 262, 'passed_tests': 262, 'source_unchanged': True,
                     'failures': [], 'errors': [], 'skipped': [],
                     'candidate_integration_test_passed': True, 'trial_candidate_sha256': 'frozen'},
                 'trial': {'candidate_sha256': 'frozen', 'passed': True, 'fresh_cases': 4,
                     'negative_cases': 5, 'historical_retry_passed': True, 'fresh_gain_over_parent': 1,
                     'cases': [{'passed': False, 'predictions': [999], 'expected': [0]}],
                     'negative_rejections': [False]},
                 'memory': {'passed': True, 'goals': 1},
                 'audit': {'pass': True, 'full_kernel': {'status': 'PASS', 'returncode': 0, 'findings': []}}}
        self.assertFalse(evaluation_passed(value))

    def test_evidence_cannot_cross_an_implementation_upgrade(self):
        from successor.runtime_evolution import verify_implementations
        records = [{'kind': 'IMPLEMENTATION_UPGRADE', 'predecessor_implementation_digest': 'old',
                    'implementation_digest': 'new'},
                   {'kind': 'COG_RUNTIME_ADMIT', 'implementation_identity': 'old'}]
        with self.assertRaisesRegex(ValueError, 'IMPLEMENTATION_PROVENANCE'):
            verify_implementations(records, 'new')

    def test_legacy_execution_records_without_kind_keep_their_history(self):
        from successor.runtime_evolution import verify_implementations
        records = [{'task': {'kind': 'logic'}, 'status': 'PASS', 'execution_attempted': True},
                   {'kind': 'IMPLEMENTATION_UPGRADE', 'predecessor_implementation_digest': 'old',
                    'implementation_digest': 'new'},
                   {'kind': 'COG_RUNTIME_PROPOSE', 'implementation_identity': 'new'}]
        before = copy.deepcopy(records)
        verify_implementations(records, 'new')
        self.assertEqual(records, before)


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(os.environ.get('YADO_SUCCESSOR_TEST_MANIFEST', ROOT / 'successor/state/birth-v2/manifest.json'))


class RuntimeEvolutionIntegrationTests(unittest.TestCase):
    def setUp(self):
        if not MANIFEST.exists():
            self.skipTest('Build the pinned successor before integration tests')
        self.tmp = tempfile.TemporaryDirectory()
        self.state = Path(self.tmp.name) / 'kernel.sqlite'
        self.kernel = SuccessorKernel(MANIFEST, self.state)
        self.kernel.db.execute('PRAGMA journal_mode=DELETE')
        self.evolution = RuntimeEvolution(self.kernel)

    def tearDown(self):
        if hasattr(self, 'kernel'):
            self.kernel.close()
            self.tmp.cleanup()

    def test_no_deficit_is_durable_idempotent_withhold_through_tracker(self):
        from successor.hivemind_evolution import CRITERIA, run_issue
        from successor.tests.test_hivemind import Tracker
        tracker = Tracker({})
        tracker.issue['description'] = json.dumps(REQUEST)
        tracker.issue['acceptanceCriteria'] = [{'text': text, 'done': False} for text in CRITERIA]
        first = run_issue(self.kernel, tracker, 'evolution-test', 'YADO-1.1', self.tmp.name)
        self.assertEqual(first['status'], 'WITHHOLD')
        self.assertFalse(first['emitted'])
        before = self.kernel.verify_state()
        saved = copy.deepcopy(tracker.issue)
        self.assertEqual(run_issue(self.kernel, tracker, 'evolution-test', 'YADO-1.1', self.tmp.name), first)
        self.assertEqual(self.kernel.verify_state(), before)
        self.assertEqual(tracker.issue, saved)
        self.kernel.close()
        self.kernel = SuccessorKernel(MANIFEST, self.state)
        self.assertEqual(self.kernel.verify_state(), before)

    def test_active_goal_prevents_proposal_without_corrupting_history(self):
        self.kernel.open_goal({'domain': 'relation', 'relation': [[1, 2]], 'start': 1})
        before = self.kernel.verify_state()
        with self.assertRaisesRegex(ValueError, 'IDLE'):
            self.evolution.propose('evolution-test', 'YADO-2', REQUEST)
        self.assertEqual(self.kernel.verify_state(), before)

    def test_ungated_activation_is_rejected(self):
        from successor.cognitive import CognitiveLoop
        proposal = self.evolution.propose('evolution-test', 'YADO-3', REQUEST)
        before = self.kernel.verify_state()
        with self.assertRaisesRegex(ValueError, 'WITHOUT_GATES'):
            self.evolution.admit(proposal['tick'])
        self.assertEqual(self.kernel.verify_state(), before)
        self.assertEqual(active_candidates(CognitiveLoop(self.kernel)._records()), {})

    def test_actual_failed_goal_selects_a_reusable_module_but_cannot_admit_it(self):
        from successor.cognitive import CognitiveLoop
        from successor.native_mechanism import synthesize
        self.kernel.activate_native_synthesis()
        row = lambda x: {'input': {'x': x}, 'expected': 10 - x * x}
        spec = {'domain': 'native_source', 'training': [row(x) for x in range(-3, 4)],
                'validation': [row(-8), row(9)], 'queries': [{'input': {'x': 17}}]}
        goal_id = self.kernel.open_goal(spec, budget=10)
        self.kernel.think(40)
        old = self.kernel.cognitive_snapshot()['goals'][str(goal_id)]
        self.assertEqual(old['status'], 'WITHHOLD')
        self.assertIn('native_evolved_v2', old['attempted'])
        proposal = self.evolution.propose('evolution-test', 'YADO-4', REQUEST)
        self.assertEqual(proposal['selection_policy'], SELECTION_POLICY)
        self.assertEqual(proposal['selection']['goal_id'], goal_id)
        self.assertEqual(proposal['selection']['max_degree'], 2)
        candidate = proposal['selection']['candidate']
        transfer = [{'input': {'new_key': x}, 'expected': 17 * x * x - 41} for x in range(-3, 4)]
        result = synthesize(candidate, transfer)
        self.assertEqual(self.kernel.parent.execute_native_source(result, [{'new_key': 11}]), [2016])
        self.assertEqual(active_candidates(CognitiveLoop(self.kernel)._records()), {})
        before = self.kernel.verify_state()
        with self.assertRaisesRegex(ValueError, 'WITHOUT_GATES'):
            self.evolution.admit(proposal['tick'])
        self.assertEqual(self.kernel.verify_state(), before)
        self.assertEqual(self.kernel.cognitive_snapshot()['goals'][str(goal_id)], old)
        # Even a correctly hashed direct journal write cannot bypass causal gates.
        self.kernel._append({'kind': 'COG_RUNTIME_ADMIT', 'proposal_tick': proposal['tick'],
            'evaluation_tick': 0, 'candidate_sha256': candidate['source_sha256'],
            'strategy': 'native_materialized_' + candidate['source_sha256'][:16], 'cost': 4})
        with self.assertRaisesRegex(ValueError, 'WITHOUT_GATES'):
            self.kernel.verify_state()

    def test_interrupted_evaluation_preserves_explicit_seed_and_frozen_candidate(self):
        self.kernel.activate_native_synthesis()
        row = lambda x: {'input': {'x': x}, 'expected': 10 - x * x}
        goal = {'domain': 'native_source', 'training': [row(x) for x in range(-3, 4)],
                'validation': [row(-8), row(9)], 'queries': [{'input': {'x': 17}}]}
        self.kernel.open_goal(goal, budget=10)
        self.kernel.think(40)
        proposal = self.evolution.propose('seed-test', 'YADO-1', REQUEST)
        before = self.kernel.verify_state()
        seed = 'a1' * 24
        for attempt in range(2):
            output = Path(self.tmp.name) / ('interrupted-' + str(attempt))
            # Interrupt at the trial boundary; no trial/regression/admission PASS
            # is imported or fabricated by this transport-contract test.
            with patch('successor.runtime_evolution.trial_report',
                       side_effect=InterruptedError('before trials')) as trial:
                with self.assertRaisesRegex(InterruptedError, 'before trials'):
                    self.evolution.evaluate(proposal['tick'], output, trial_seed=seed)
                trial.assert_called_once_with(self.kernel, proposal, seed)
            self.assertEqual(json.loads((output / 'candidate.json').read_text()),
                             proposal['selection']['candidate'])
            self.assertEqual(self.kernel.verify_state(), before)
        invalid_output = Path(self.tmp.name) / 'invalid-seed'
        with self.assertRaisesRegex(ValueError, 'FRESH_SEED_CONTRACT'):
            self.evolution.evaluate(proposal['tick'], invalid_output, trial_seed='invalid')
        self.assertFalse(invalid_output.exists())
        self.assertEqual(self.kernel.verify_state(), before)


if __name__ == '__main__':
    unittest.main()
