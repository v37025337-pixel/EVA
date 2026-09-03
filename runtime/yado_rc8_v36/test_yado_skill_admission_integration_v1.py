import unittest
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive

class TestSkillAdmissionIntegration(unittest.TestCase):
    def test_kernel_exposes_precommit_gate(self):
        k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=':memory:')
        try:
            cap=k.unified_snapshot()['skill_admission']
            self.assertEqual(cap['status'],'ACTIVE_BOUNDED_PRECOMMIT_SKILL_GATE_V1')
            good=dict(skill_id='good',artifact_digest='dg',structural_valid=True,semantic_consistency=.99,fit_baseline=.4,fit_candidate=.8,heldout_baseline=.5,heldout_candidate=.7)
            bad=dict(skill_id='bad',artifact_digest='db',structural_valid=True,semantic_consistency=.99,fit_baseline=.4,fit_candidate=.9,heldout_baseline=.8,heldout_candidate=.3)
            out=k.select_evolution_skills([good,bad])
            self.assertEqual(out['selected_skill_ids'],['good'])
        finally:k.close()

if __name__=='__main__': unittest.main()
