import unittest
from yado_transfer_memory_runtime_v1 import TransferExperience,TransferMemoryRuntime,naive_trajectory_retrieve

def E(i,d,tags,proc,score=1.0,success=True):return TransferExperience(i,d,tags,proc,score,success)

class TestTransferMemoryRuntime(unittest.TestCase):
    def test_cross_domain_repeated_procedure_is_consolidated(self):
        xs=[E('1','code',['verify','compare','code'],['OBSERVE','VERIFY','COMPARE']),E('2','research',['verify','compare','research'],['OBSERVE','VERIFY','COMPARE']),E('3','ops',['verify','compare','ops'],['OBSERVE','VERIFY','COMPARE'])]
        out=TransferMemoryRuntime().consolidate(xs)
        self.assertEqual(out['memory_count'],1);m=out['memories'][0]
        self.assertEqual(set(m.stable_tags),{'verify','compare'});self.assertEqual(len(m.support_domains),3)
    def test_single_domain_brittle_pattern_is_rejected(self):
        xs=[E('1','code',['patch','code'],['PATCH']),E('2','code',['patch','code'],['PATCH']),E('3','code',['patch','code'],['PATCH'])]
        out=TransferMemoryRuntime().consolidate(xs)
        self.assertEqual(out['memory_count'],0);self.assertIn('INSUFFICIENT_DOMAIN_DIVERSITY',out['rejected'][0]['reasons'])
    def test_high_failure_pattern_is_rejected(self):
        xs=[E('1','a',['x'],['P'],1,True),E('2','b',['x'],['P'],0,False),E('3','c',['x'],['P'],0,False)]
        out=TransferMemoryRuntime(max_failure_rate=.2).consolidate(xs)
        self.assertEqual(out['memory_count'],0);self.assertIn('FAILURE_RATE_TOO_HIGH',out['rejected'][0]['reasons'])
    def test_retrieval_uses_stable_procedural_tags(self):
        xs=[
          E('1','a',['verify','compare','a'],['V','C']),E('2','b',['verify','compare','b'],['V','C']),E('3','c',['verify','compare','c'],['V','C']),
          E('4','a',['plan','execute','a'],['P','E']),E('5','b',['plan','execute','b'],['P','E']),E('6','c',['plan','execute','c'],['P','E']),
        ]
        c=TransferMemoryRuntime().consolidate(xs);r=TransferMemoryRuntime().retrieve(c['memories'],['verify','compare','new'],target_domain='new',k=1)
        self.assertEqual(r['rows'][0]['procedure'],['V','C'])
    def test_naive_trajectory_can_be_distracted_by_domain_specific_overlap(self):
        xs=[
          E('1','old',['verify','compare','old'],['V','C']),
          E('9','old',['verify','new','old'],['WRONG'],.4,True),
        ]
        n=naive_trajectory_retrieve(xs,['verify','new'])
        self.assertEqual(list(n.procedure),['WRONG'])

if __name__=='__main__':unittest.main()
