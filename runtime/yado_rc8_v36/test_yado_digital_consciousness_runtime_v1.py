import unittest
from dataclasses import replace
from yado_digital_consciousness_runtime_v1 import WorkspaceItem,CausalReflectiveWorkspace,EpisodeRecord

class TestDigitalConsciousnessRuntime(unittest.TestCase):
    def _items(self):
        return [
            WorkspaceItem('e1','sensor-a','external',{'v':2},.90,.95,.6,.1,.05,('solve','alpha')),
            WorkspaceItem('e2','sensor-b','tool_observation',{'v':3},.88,.92,.5,.1,.05,('solve','beta')),
            WorkspaceItem('m1','memory','memory',{'v':5},.82,.78,.2,.0,.15,('solve','prior')),
            WorkspaceItem('s1','sim','simulation',{'v':99},.99,.70,.9,.0,.55,('solve','guess')),
            WorkspaceItem('x1','noise','external',{'v':7},.95,.05,.3,.0,.05,('irrelevant',)),
        ]

    def test_limited_capacity_and_state_dependent_selection(self):
        w=CausalReflectiveWorkspace(capacity=3)
        s=w.select(self._items(),'solve alpha beta')
        self.assertEqual(len(s),3)
        self.assertIn('e1',[x.item_id for x in s]); self.assertIn('e2',[x.item_id for x in s])
        self.assertNotIn('x1',[x.item_id for x in s])

    def test_global_broadcast_same_workspace_to_multiple_consumers(self):
        w=CausalReflectiveWorkspace(capacity=2)
        selected=w.select(self._items(),'solve')
        seen={}
        def mk(name):
            return lambda xs: seen.setdefault(name,tuple(x.item_id for x in xs))
        out=w.broadcast(selected,{'logic':mk('logic'),'memory':mk('memory'),'self_model':mk('self_model')})
        self.assertEqual(seen['logic'],seen['memory']); self.assertEqual(seen['memory'],seen['self_model'])
        self.assertEqual(len(out),3)

    def test_source_monitor_blocks_unsupported_simulation(self):
        w=CausalReflectiveWorkspace(capacity=4)
        ep=w.cycle(goal='solve',items=self._items(),consumers={'logic':lambda xs:len(xs)},metacognitive_action='EXECUTE',proposed_belief_ids=['s1','e1'])
        self.assertIn('e1',ep.committed_beliefs)
        self.assertNotIn('s1',ep.committed_beliefs)

    def test_metacognition_is_causal_commit_gate(self):
        w=CausalReflectiveWorkspace(capacity=3)
        a=w.cycle(goal='solve',items=self._items(),consumers={'logic':lambda xs:1},metacognitive_action='WITHHOLD',proposed_belief_ids=['e1'])
        b=w.cycle(goal='solve',items=self._items(),consumers={'logic':lambda xs:1},metacognitive_action='EXECUTE',proposed_belief_ids=['e1'])
        self.assertEqual(a.committed_beliefs,())
        self.assertEqual(b.committed_beliefs,('e1',))

    def test_recurrent_prediction_error_improves(self):
        w=CausalReflectiveWorkspace()
        errors=[]
        for _ in range(30):
            ep=w.cycle(goal='learn transition',items=self._items(),consumers={'model':lambda xs:1},metacognitive_action='WITHHOLD',context='door',action='open',possible_outcomes=('opens','stuck'),observed_outcome='opens')
            errors.append(ep.prediction_error)
        self.assertGreater(errors[0],errors[-1])
        self.assertLess(errors[-1],0.08)

    def test_attention_schema_calibration(self):
        w=CausalReflectiveWorkspace(capacity=2)
        for _ in range(5):
            w.select(self._items(),'solve')
            pred=w.attention.predicted_next_source_kind
            self.assertIsNotNone(pred)
            w.register_actual_next_focus(pred)
        self.assertEqual(w.attention.calibration,1.0)

    def test_content_addressed_continuity_detects_tamper(self):
        w=CausalReflectiveWorkspace(capacity=2)
        for _ in range(3):
            w.cycle(goal='solve',items=self._items(),consumers={'logic':lambda xs:1},metacognitive_action='WITHHOLD')
        self.assertTrue(w.verify_continuity())
        bad=replace(w.episodes[1], goal='tampered')
        w.episodes[1]=bad
        self.assertFalse(w.verify_continuity())

    def test_functional_indicator_snapshot_boundaries(self):
        w=CausalReflectiveWorkspace(capacity=2)
        w.cycle(goal='solve',items=self._items(),consumers={'logic':lambda xs:1,'memory':lambda xs:2},metacognitive_action='WITHHOLD',context='c',action='a',possible_outcomes=('x','y'),observed_outcome='x')
        s=w.functional_indicator_snapshot()
        self.assertTrue(s['global_broadcast']); self.assertTrue(s['recurrent_prediction_loop'])
        self.assertFalse(s['subjective_consciousness_claimed'])

if __name__=='__main__':unittest.main()
