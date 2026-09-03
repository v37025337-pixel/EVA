import unittest
from yado_transfer_evaluation_runtime_v1 import TransferEvaluationCase,TransferEvaluationRuntime

def C(i,r,b,a,pb=1,pa=1):return TransferEvaluationCase(i,r,b,a,pb,pa)
class TestTransferEvaluationRuntime(unittest.TestCase):
    def test_positive_controlled_transfer_passes(self):
        xs=[C('r1','REUSABLE',.5,.7),C('r2','REUSABLE',.4,.6),C('u','UNRELATED',.7,.7),C('h','HELDOUT',.5,.62)]
        o=TransferEvaluationRuntime().evaluate(xs);self.assertTrue(o['pass']);self.assertFalse(o['general_open_ended_transfer_proven'])
    def test_negative_transfer_fails(self):
        xs=[C('r','REUSABLE',.5,.7),C('u','UNRELATED',.8,.4),C('h','HELDOUT',.5,.6)]
        o=TransferEvaluationRuntime(max_negative_transfer_rate=.2).evaluate(xs);self.assertFalse(o['pass']);self.assertIn('unrelated_harmlessness',o['failed_gates'])
    def test_forgetting_fails(self):
        xs=[C('r','REUSABLE',.5,.7,1,.8),C('u','UNRELATED',.5,.5),C('h','HELDOUT',.5,.6)]
        o=TransferEvaluationRuntime().evaluate(xs);self.assertFalse(o['pass']);self.assertIn('forgetting',o['failed_gates'])
    def test_missing_stream_relation_fails_coverage(self):
        o=TransferEvaluationRuntime().evaluate([C('r','REUSABLE',.5,.8),C('h','HELDOUT',.5,.8)])
        self.assertFalse(o['pass']);self.assertIn('coverage',o['failed_gates'])
    def test_digest_is_order_invariant_by_case_id(self):
        xs=[C('r','REUSABLE',.5,.7),C('u','UNRELATED',.5,.5),C('h','HELDOUT',.5,.6)]
        a=TransferEvaluationRuntime().evaluate(xs)['evidence_digest'];b=TransferEvaluationRuntime().evaluate(reversed(xs))['evidence_digest'];self.assertEqual(a,b)
if __name__=='__main__':unittest.main()
