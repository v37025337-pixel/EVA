import tempfile,unittest
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_metacognitive_control_runtime_v1 import CapabilityObservation,MetacognitiveTask

class TestDigitalConsciousnessIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.NamedTemporaryFile(suffix='.sqlite',delete=False);self.tmp.close()
        self.k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=self.tmp.name)
    def tearDown(self):
        try:self.k.close()
        except Exception:pass
    def items(self):
        return [
            dict(item_id='e1',source='tool',source_kind='tool_observation',content={'fact':2},confidence=.92,goal_relevance=.95,novelty=.5,epistemic_risk=.05,tags=('solve',)),
            dict(item_id='s1',source='sim',source_kind='simulation',content={'fact':99},confidence=.99,goal_relevance=.85,novelty=.9,epistemic_risk=.7,tags=('solve',)),
            dict(item_id='m1',source='memory',source_kind='memory',content={'fact':3},confidence=.8,goal_relevance=.75,novelty=.2,epistemic_risk=.2,tags=('solve',)),
        ]
    def test_capability_is_present_but_subjective_claim_false(self):
        c=self.k.digital_consciousness_capability()
        self.assertEqual(c['architecture'],'YADO_CAUSAL_REFLECTIVE_WORKSPACE_V1')
        self.assertTrue(c['functional_digital_consciousness_claim'])
        self.assertFalse(c['subjective_consciousness_claimed'])
    def test_metacognitive_controller_is_mandatory_when_no_action_supplied(self):
        p=self.k.build_capability_boundary_profile([CapabilityObservation('INTEGRATION',.3,True) for _ in range(12)])
        t=MetacognitiveTask('t','INTEGRATION',.3,.9,.9,.1,False)
        ep=self.k.digital_conscious_cycle(goal='solve',items=self.items(),consumers={'logic':lambda xs:len(xs),'memory':lambda xs:len(xs)},metacognitive_task=t,capability_profile=p,proposed_belief_ids=('e1','s1'))
        self.assertEqual(ep.metacognitive_action,'EXECUTE')
        self.assertIn('e1',ep.committed_beliefs)
        self.assertNotIn('s1',ep.committed_beliefs)
    def test_snapshot_reports_broadcast_recurrence_and_continuity(self):
        self.k.digital_conscious_cycle(goal='solve',items=self.items(),consumers={'logic':lambda xs:1,'memory':lambda xs:2,'self_model':lambda xs:3},metacognitive_action='WITHHOLD',context='x',action='a',possible_outcomes=('ok','bad'),observed_outcome='ok')
        s=self.k.digital_consciousness_snapshot()
        self.assertTrue(s['global_broadcast']);self.assertTrue(s['recurrent_prediction_loop']);self.assertTrue(s['continuity_verified'])
        self.assertIn('NOT_PROOF_OF_SUBJECTIVE_EXPERIENCE',s['semantic_boundary'])
if __name__=='__main__':unittest.main()
