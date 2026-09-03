import unittest
from yado_consciousness_theory_synthesis_v1 import synthesize_default,YADOTheorySynthesizer,TheoryCard

class TestTheorySynthesis(unittest.TestCase):
    def test_default_synthesis_is_yado_native_and_multi_theory(self):
        s=synthesize_default()
        self.assertEqual(s['architecture'],'YADO_CAUSAL_REFLECTIVE_WORKSPACE_V1')
        for m in ('limited_global_workspace','causal_broadcast','recurrent_processing','self_world_prediction_error','attention_schema','metacognitive_executive_binding'):
            self.assertIn(m,s['selected_mechanisms'])
        self.assertIn('content_addressed_episode_lineage',s['yado_native_additions'])
        self.assertIn('NOT_PROOF_OF_SUBJECTIVE_EXPERIENCE',s['semantic_boundary'])

    def test_no_single_theory_is_required_authority(self):
        cards=[
            TheoryCard('A',('limited_global_workspace','causal_broadcast'),.8,.9,('a',)),
            TheoryCard('B',('recurrent_processing','attention_schema'),.8,.9,('b',)),
            TheoryCard('C',('metacognitive_executive_binding','self_world_prediction_error'),.8,.9,('c',)),
        ]
        s=YADOTheorySynthesizer().synthesize(cards)
        self.assertEqual(set(s['source_ids']),{'a','b','c'})
        self.assertGreaterEqual(len(s['selected_mechanisms']),5)

if __name__=='__main__':unittest.main()
