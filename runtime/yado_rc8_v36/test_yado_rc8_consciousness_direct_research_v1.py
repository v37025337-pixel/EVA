import unittest
import yado_rc8_consciousness_direct_research_v1 as m
class TestDirectResearch(unittest.TestCase):
 def test_allowlist(self):
  self.assertTrue(m.allowed('https://arxiv.org/abs/2308.08708'));self.assertFalse(m.allowed('https://example.com/'))
 def test_distill_multi_theory(self):
  rows=[{'id':'a','text':'global workspace broadcast recurrent processing higher-order metacognition attention schema predictive processing prediction error integrated information'}, {'id':'b','text':'global workspace attention schema active inference metacognition'}]
  cards,hits=m.distill(rows);names={c.theory for c in cards}
  self.assertIn('Global Workspace Theory',names);self.assertIn('Attention Schema Theory',names);self.assertIn('Predictive Processing / Active Inference',names)
  s=m.YADOTheorySynthesizer().synthesize(cards);self.assertEqual(s['architecture'],'YADO_CAUSAL_REFLECTIVE_WORKSPACE_V1')
if __name__=='__main__':unittest.main()
