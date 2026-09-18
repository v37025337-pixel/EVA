from __future__ import annotations

RELATIONAL_CAUSAL_LOGIC_POLICY = {'max_depth': 6, 'causal_only': True, 'reject_feedback_cycles': True}
VERIFIED_SCORES = {'train': {'accuracy': 1.0, 'correct': 40, 'total': 40, 'by_kind': {'association_not_cause': 1.0, 'causal_chain': 1.0, 'feedback_contradiction': 1.0, 'wrong_direction': 1.0}}, 'hidden': {'accuracy': 1.0, 'correct': 40, 'total': 40, 'by_kind': {'association_not_cause': 1.0, 'causal_chain': 1.0, 'feedback_contradiction': 1.0, 'wrong_direction': 1.0}}, 'fresh': {'accuracy': 1.0, 'correct': 40, 'total': 40, 'by_kind': {'association_not_cause': 1.0, 'causal_chain': 1.0, 'feedback_contradiction': 1.0, 'wrong_direction': 1.0}}}

def component():
    return {'schema':'yado.relational_causal_logic_policy.v1','policy':RELATIONAL_CAUSAL_LOGIC_POLICY,'verified_scores':VERIFIED_SCORES,'canonical_active':False,'automatic_main_mutation':False,'consciousness_claimed':False}
