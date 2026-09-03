import unittest
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
class TestTransferEvaluationIntegration(unittest.TestCase):
    def test_kernel_evaluates_bounded_stream_without_overclaim(self):
        k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=':memory:')
        try:
            xs=[dict(case_id='r',relation='REUSABLE',baseline_score=.5,adapted_score=.8),dict(case_id='u',relation='UNRELATED',baseline_score=.7,adapted_score=.7),dict(case_id='h',relation='HELDOUT',baseline_score=.4,adapted_score=.65)]
            o=k.evaluate_transfer_stream(xs);self.assertTrue(o['pass']);self.assertFalse(o['general_open_ended_transfer_proven'])
            self.assertEqual(k.unified_snapshot()['transfer_evaluation']['status'],'ACTIVE_BOUNDED_CONTROLLED_TRANSFER_EVALUATOR_V1')
        finally:k.close()
if __name__=='__main__':unittest.main()
