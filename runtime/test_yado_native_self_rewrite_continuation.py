"""Current-parent behavior and fail-closed controls; fixtures are not gain evidence."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from yado_active_kernel_contract_v1 import active_kernel_identity
from yado_native_experience_to_runtime_self_rewrite_v3 import digest
from yado_native_self_rewrite_continuation import continue_from_active

ROOT = Path(__file__).resolve().parents[1]
EXPERIENCE = ROOT / 'experience/autonomous/yado-autonomous-learning-latest.json'


class CurrentParentContinuationTests(unittest.TestCase):
    def run_attempt(self, experience=None, root=ROOT):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            source = EXPERIENCE
            if experience is not None:
                source = directory / 'experience.json'
                source.write_text(json.dumps(experience))
            result = continue_from_active(root, directory / 'attempt', source)
            self.assertEqual(result, json.loads((directory / 'attempt/receipt.json').read_text()))
            return result

    def test_current_maintenance_parent_is_accepted_but_no_effect_is_withheld(self):
        result = self.run_attempt()
        self.assertEqual(result['parent_identity'], active_kernel_identity(ROOT))
        self.assertEqual(result['status'], 'WITHHOLD')
        self.assertEqual(result['reason'], 'NO_OBSERVABLE_SELECTION_CHANGE')
        self.assertTrue(result['checks']['parent_verified'])
        self.assertTrue(result['checks']['ablation_restores_parent'])
        self.assertEqual(result['diagnostic']['selection_changes'], 0)
        self.assertFalse(result['active_admission_performed'])
        self.assertFalse(result['capability_gain_claimed'])

    def test_receipt_digest_cannot_be_forged(self):
        exp = json.loads(EXPERIENCE.read_text())
        exp['sources'][0]['facts'].append('altered after sealing')
        result = self.run_attempt(exp)
        self.assertEqual(result['reason'], 'EXPERIENCE_CONTENT_DIGEST_MISMATCH')
        self.assertNotIn('candidate_sha256', result)

    def test_unverified_status_and_unsafe_policy_are_rejected(self):
        for field in ('status', 'policy'):
            with self.subTest(field=field):
                exp = json.loads(EXPERIENCE.read_text())
                if field == 'status':
                    exp['status'] = 'WITHHOLD'
                else:
                    exp['network_policy']['external_writes'] = True
                exp['experience_digest'] = digest({k: v for k, v in exp.items() if k != 'experience_digest'})
                self.assertEqual(self.run_attempt(exp)['status'], 'WITHHOLD')

    def test_arbitrary_catalog_source_can_change_selection_without_v3_specific_ids(self):
        exp = json.loads(EXPERIENCE.read_text())
        exp['sources'] = [{'source_id': 'W3C_WEBARCH', 'facts': ['resource protocol architecture'],
                          'network': {'host': 'www.w3.org'}}]
        exp['failures'] = []
        exp['experience_digest'] = digest({k: v for k, v in exp.items() if k != 'experience_digest'})
        result = self.run_attempt(exp)
        self.assertEqual(result['status'], 'READY_FOR_INDEPENDENT_EVALUATION')
        self.assertGreater(result['diagnostic']['selection_changes'], 0)
        self.assertTrue(result['checks']['ablation_restores_parent'])
        self.assertFalse(result['blind_evaluation_performed'])
        self.assertFalse(result['capability_gain_claimed'])

    def test_source_duplicate_or_conflicting_outcomes_are_rejected(self):
        for conflict in (False, True):
            exp = json.loads(EXPERIENCE.read_text())
            if conflict:
                exp['failures'] = [{'source_id': exp['sources'][0]['source_id']}]
            else:
                exp['sources'].append(copy.deepcopy(exp['sources'][0]))
            exp['experience_digest'] = digest({k: v for k, v in exp.items() if k != 'experience_digest'})
            self.assertEqual(self.run_attempt(exp)['reason'], 'AMBIGUOUS_SOURCE_OUTCOMES')

    def test_different_controller_experience_is_rejected(self):
        exp = json.loads(EXPERIENCE.read_text())
        exp['execution_identity']['controller_sha256'] = '0' * 64
        exp['experience_digest'] = digest({k: v for k, v in exp.items() if k != 'experience_digest'})
        self.assertEqual(self.run_attempt(exp)['reason'], 'EXPERIENCE_PARENT_MISMATCH')

    def test_unknown_source_is_withheld(self):
        exp = json.loads(EXPERIENCE.read_text())
        exp['sources'][0]['source_id'] = 'UNKNOWN_NOT_IN_CATALOG'
        exp['experience_digest'] = digest({k: v for k, v in exp.items() if k != 'experience_digest'})
        self.assertEqual(self.run_attempt(exp)['reason'], 'UNKNOWN_EXPERIENCE_SOURCE')

    def test_existing_attempt_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileExistsError):
                continue_from_active(ROOT, Path(directory), EXPERIENCE)


if __name__ == '__main__':
    unittest.main()
