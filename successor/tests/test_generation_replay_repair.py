"""Offline retention must verify frozen evidence, never repeat discovery."""
import copy
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from successor.cognitive import CognitiveLoop
from successor.generation import retained_memory
from successor.tests.test_state_semantics import candidate_records
from yado_autonomous_external_library_discovery_v5 import sha_json


def library_records():
    spec={'domain':'library_discovery','objective':'html_xml_parser'}
    bundle={'package':'example','filename':'example.whl','artifact_sha256':'a'*64}
    result={'status':'CANDIDATE','bundle':bundle,'bundle_sha256':sha_json(bundle),
            'artifact':{'expected_sha256':bundle['artifact_sha256']}}
    proof={'source':{'url':'https://pypi.org/simple/example/'},'filename':bundle['filename'],
           'sha256':bundle['artifact_sha256'],'matched':True,'selection_data_used':False}
    evidence={'passed':True,'scope':'SEPARATE_PYPI_SIMPLE_AFTER_BUNDLE_FREEZE','checks':1,'proof':proof}
    verification={'passed':True,'checks':1,'scope':evidence['scope'],'evidence':evidence}
    return candidate_records(spec,'catalog_v6',4,result,verification)


class HistoricalLibraryRetentionTests(unittest.TestCase):
    def test_retention_is_offline_and_matches_archived_check(self):
        records=library_records()
        parent=SimpleNamespace(native_library_candidate=Mock(side_effect=OSError('offline')),
                               verify_native_library=Mock(side_effect=OSError('offline')))
        with patch.object(CognitiveLoop,'_records',return_value=records):
            measured=retained_memory(SimpleNamespace(parent=parent))
        self.assertEqual(measured,{'goals':1,'passed':True,'checks':[
            {'goal_id':1,'status':'VERIFIED','retained':True,
             'scope':'SEPARATE_PYPI_SIMPLE_AFTER_BUNDLE_FREEZE','checks':1}]})
        parent.native_library_candidate.assert_not_called()
        parent.verify_native_library.assert_not_called()

    def test_changed_frozen_proof_is_rejected_even_when_live_network_would_pass(self):
        records=library_records()
        records[3]['evidence']['proof']['filename']='different.whl'
        parent=SimpleNamespace(native_library_candidate=Mock(),verify_native_library=Mock(return_value={'passed':True}))
        with patch.object(CognitiveLoop,'_records',return_value=records):
            with self.assertRaisesRegex(ValueError,'COGNITIVE_VERIFICATION_RESULT'):
                retained_memory(SimpleNamespace(parent=parent))
        parent.native_library_candidate.assert_not_called()

    def test_prior_rejection_is_preserved(self):
        records=library_records()
        failed={'passed':False,'checks':0,'scope':'LIBRARY_VALIDATION_ERROR',
                'evidence':{'error_type':'OSError','error':'offline'}}
        records=candidate_records(records[0]['spec'],'catalog_v6',4,copy.deepcopy(records[2]['result']),failed)
        with patch.object(CognitiveLoop,'_records',return_value=records):
            measured=retained_memory(SimpleNamespace(parent=SimpleNamespace()))
        self.assertEqual(measured['checks'][0]['status'],'WITHHOLD')
        self.assertEqual(measured['checks'][0]['scope'],'REJECTION_PRESERVED')


if __name__=='__main__':unittest.main()
