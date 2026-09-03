import unittest
from yado_skill_admission_runtime_v1 import SkillCandidate, SkillAdmissionGate, contamination_score


def C(skill_id, *, structural=True, semantic=.98, fit0=.60, fit1=.75, hold0=.60, hold1=.72, regression=True, state=True, rollback=True):
    return SkillCandidate(skill_id, 'd-'+skill_id, structural, semantic, fit0, fit1, hold0, hold1, regression, state, rollback)


class TestSkillAdmissionRuntime(unittest.TestCase):
    def setUp(self):
        self.g = SkillAdmissionGate(min_semantic_consistency=.90, min_fit_gain=.01, max_heldout_drop=0.0, min_heldout_gain=0.0)

    def test_good_skill_is_admitted(self):
        r=self.g.evaluate(C('good'))
        self.assertTrue(r['admitted']); self.assertEqual(r['verdict'],'ADMIT')

    def test_harmful_transfer_rejected_even_with_fit_gain(self):
        r=self.g.evaluate(C('harm',fit0=.5,fit1=.95,hold0=.8,hold1=.55))
        self.assertFalse(r['admitted']); self.assertIn('heldout_harmlessness',r['failed_critics'])

    def test_structural_and_semantic_critics_are_non_substitutable(self):
        a=self.g.evaluate(C('bad-struct',structural=False,semantic=1.0))
        b=self.g.evaluate(C('bad-sem',structural=True,semantic=.2))
        self.assertFalse(a['admitted']); self.assertFalse(b['admitted'])
        self.assertIn('structural',a['failed_critics']); self.assertIn('semantic',b['failed_critics'])

    def test_regression_state_and_rollback_are_hard_constraints(self):
        for key in ('regression','state','rollback'):
            kw={key:False}
            r=self.g.evaluate(C('bad-'+key,**kw))
            self.assertFalse(r['admitted'])

    def test_subset_selection_is_deterministic_and_bounded(self):
        xs=[C('b',hold1=.74),C('a',hold1=.80),C('c',hold1=.76),C('harm',hold1=.20)]
        r1=self.g.select_subset(xs,max_skills=2); r2=self.g.select_subset(reversed(xs),max_skills=2)
        self.assertEqual(r1['selected_skill_ids'],r2['selected_skill_ids'])
        self.assertEqual(len(r1['selected_skill_ids']),2)
        self.assertNotIn('harm',r1['selected_skill_ids'])

    def test_gatekeeper_beats_unconditional_accumulation_on_contamination_case(self):
        xs=[
            C('good1',hold0=.60,hold1=.68),
            C('good2',hold0=.60,hold1=.66),
            C('bad1',fit0=.5,fit1=.9,hold0=.60,hold1=.35),
            C('bad2',fit0=.4,fit1=.95,hold0=.60,hold1=.30),
        ]
        chosen=set(self.g.select_subset(xs,max_skills=8)['selected_skill_ids'])
        gated=[x for x in xs if x.skill_id in chosen]
        self.assertGreater(contamination_score(.60,gated),contamination_score(.60,xs))

if __name__=='__main__': unittest.main()
