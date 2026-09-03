import unittest
from yado_metacognitive_control_runtime_v1 import *
class TestMetaControl(unittest.TestCase):
 def setUp(self):
  self.p=CapabilityBoundaryProfile().fit([CapabilityObservation('LOGIC',.2,True)]*20+[CapabilityObservation('MATH',.8,False)]*20)
  self.c=MetacognitiveController()
 def test_framework_conflict_routes_before_execution(self):
  t=MetacognitiveTask('a','LOGIC',.2,.9,.9,.1,True); self.assertEqual(self.c.decide(t,self.p).action,'ROUTE_FRAMEWORK')
 def test_low_evidence_seeks_evidence(self):
  t=MetacognitiveTask('a','LOGIC',.2,.9,.2,.1,False); self.assertEqual(self.c.decide(t,self.p).action,'SEEK_EVIDENCE')
 def test_known_strength_executes(self):
  t=MetacognitiveTask('a','LOGIC',.2,.85,.9,.0,False); self.assertEqual(self.c.decide(t,self.p).action,'EXECUTE')
 def test_known_weakness_withholds_even_when_verbal_confident(self):
  t=MetacognitiveTask('a','MATH',.8,.92,.9,.7,False); self.assertEqual(self.c.decide(t,self.p).action,'WITHHOLD')
 def test_feedback_updates_boundary(self):
  b=self.p.confidence('LOGIC',.2); self.c.feedback(self.p,MetacognitiveTask('x','LOGIC',.2,.8,.9),False); a=self.p.confidence('LOGIC',.2); self.assertLess(a,b)
