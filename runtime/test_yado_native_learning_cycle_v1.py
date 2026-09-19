"""Offline evidence-contract checks; these fixtures are not live learning proof."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import yado_bounded_autonomous_learning_v1 as learner
import yado_native_learning_cycle_v1 as cycle
from yado_native_experience_to_runtime_self_rewrite_v3 import synthesize_candidate
from yado_persist_learning_feed_v1 import verified_learning_outputs, copy_verified_outputs, EXPERIENCE, RECEIPT

ROOT = Path(__file__).resolve().parents[1]
IDENTITY = {'controller_sha256': hashlib.sha256((ROOT / cycle.TARGET).read_bytes()).hexdigest()}


class NativeLearningCycleTests(unittest.TestCase):
    def evidence(self, root):
        exp = json.loads((ROOT / EXPERIENCE).read_text())
        exp['execution_identity'] = IDENTITY
        exp['run_id'] = 'OFFLINE_CONTRACT_FIXTURE'
        exp['experience_digest'] = learner.digest({k:v for k,v in exp.items() if k != 'experience_digest'})
        recall = root / 'candidates/autonomous/yado_learned_recall_test.py'
        capability = learner.synthesize_recall_module(exp, recall, root)
        receipt = {'status': exp['status'], 'experience_digest': exp['experience_digest'],
                   'source_success_count': len(exp['sources']), 'source_failure_count': len(exp['failures']),
                   'generated_capability': capability, 'real_network_used': True,
                   'external_model_used': False, 'credentials_used': False, 'external_mutation': False,
                   'candidate_canonical_active': False}
        receipt['receipt_sha256'] = learner.digest(receipt)
        for name, value in [(EXPERIENCE, exp), (RECEIPT, receipt)]:
            p=root/name;p.parent.mkdir(parents=True, exist_ok=True);p.write_text(json.dumps(value))
        return exp, receipt

    def test_metadata_refresh_is_not_reported_as_capability_gain(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(cycle, 'active_kernel_identity', return_value=IDENTITY):
            root=Path(tmp); self.evidence(root)
            report=cycle.run(root,root/'output')
            self.assertEqual(report['status'],'NO_MEASURED_BEHAVIOR_GAIN')
            self.assertEqual(report['novel_fact_count'],0)
            self.assertTrue(report['effective_binding_verified'])
            self.assertFalse(report['capability_gain_proven'])
            self.assertFalse(report['candidate_full_regression_admission'])
            self.assertFalse(report['canonical_runtime_mutated'])

    def test_tampered_experience_replaces_stale_success_with_withhold(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(cycle, 'active_kernel_identity', return_value=IDENTITY):
            root=Path(tmp); exp,_=self.evidence(root)
            output=root/'output';output.mkdir();(output/'receipt.json').write_text('{"status":"PASS"}')
            exp['sources'][0]['facts'][0]='tampered evidence'
            (root/EXPERIENCE).write_text(json.dumps(exp))
            with self.assertRaisesRegex(ValueError,'UNVERIFIED_LEARNING_OUTPUT'):
                cycle.run(root,output)
            self.assertEqual(json.loads((output/'receipt.json').read_text())['status'],'WITHHOLD_UNVERIFIED_LEARNING_CYCLE')

    def test_self_consistent_receipt_cannot_inflate_fact_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); _,receipt=self.evidence(root)
            receipt['generated_capability']['fact_count'] += 1
            receipt['receipt_sha256']=learner.digest({k:v for k,v in receipt.items() if k!='receipt_sha256'})
            (root/RECEIPT).write_text(json.dumps(receipt))
            with self.assertRaisesRegex(ValueError,'INCONSISTENT_LEARNING_EVIDENCE'):
                verified_learning_outputs(root,IDENTITY)

    def test_replayed_experience_from_different_kernel_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); self.evidence(root)
            with self.assertRaisesRegex(ValueError,'UNVERIFIED_LEARNING_OUTPUT'):
                verified_learning_outputs(root,{'controller_sha256':'wrong'})

    def test_probe_rejects_shadowed_binding_even_if_ranking_changes(self):
        exp=json.loads((ROOT/EXPERIENCE).read_text());exp['experience_digest']='b'*64
        source,learned,_=synthesize_candidate((ROOT/cycle.TARGET).read_text(),exp)
        source += '\nLEARNED_EXTERNAL_EVIDENCE_V2 = {}\n'
        with tempfile.TemporaryDirectory() as tmp:
            candidate=Path(tmp)/'candidate.py';candidate.write_text(source)
            with self.assertRaisesRegex(ValueError,'DUPLICATE_LEARNED_BINDING'):
                cycle.probe_candidate(ROOT/cycle.TARGET,candidate,learned)

    def test_data_only_feed_rejects_internal_symlink_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp, patch('yado_active_kernel_contract_v1.active_kernel_identity', return_value=IDENTITY):
            root=Path(tmp); source=root/'source'; source.mkdir(); self.evidence(source)
            destination=root/'feed'; sentinel=destination/'runtime/sentinel.py'
            sentinel.parent.mkdir(parents=True);sentinel.write_text('UNCHANGED')
            alias=destination/RECEIPT;alias.parent.mkdir(parents=True)
            alias.symlink_to('../../runtime/sentinel.py')
            with self.assertRaisesRegex(ValueError,'FEED_PATH_SYMLINK'):
                copy_verified_outputs(source,destination)
            self.assertEqual(sentinel.read_text(),'UNCHANGED')
            self.assertFalse((destination/EXPERIENCE).exists())

    def test_source_symlink_is_not_accepted_as_a_data_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);_,receipt=self.evidence(root)
            recall=root/receipt['generated_capability']['path']
            other=root/'alias.py';recall.rename(other);recall.symlink_to('../../alias.py')
            with self.assertRaisesRegex(ValueError,'FEED_PATH_SYMLINK'):
                verified_learning_outputs(root,IDENTITY)


if __name__=='__main__':
    unittest.main()
