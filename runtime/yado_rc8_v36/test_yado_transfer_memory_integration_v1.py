import unittest
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
class TestTransferMemoryIntegration(unittest.TestCase):
    def test_kernel_consolidates_cross_domain_procedure(self):
        k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=':memory:')
        try:
            xs=[
              dict(experience_id='1',domain='code',tags=['verify','rollback','code'],procedure=['TEST','VERIFY','ROLLBACK'],outcome_score=1),
              dict(experience_id='2',domain='research',tags=['verify','rollback','research'],procedure=['TEST','VERIFY','ROLLBACK'],outcome_score=.95),
              dict(experience_id='3',domain='ops',tags=['verify','rollback','ops'],procedure=['TEST','VERIFY','ROLLBACK'],outcome_score=.9),
            ]
            out=k.consolidate_transfer_memory(xs)
            self.assertEqual(out['memory_count'],1)
            cap=k.unified_snapshot()['transfer_memory'];self.assertEqual(cap['status'],'ACTIVE_BOUNDED_PROCEDURAL_TRANSFER_MEMORY_V1')
        finally:k.close()
if __name__=='__main__':unittest.main()
