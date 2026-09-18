from __future__ import annotations

COGNITIVE_INTEGRATION_POLICY = 'ALL_FOUR'
REQUIRED_GATES = ('MEMORY_EXPERIENCE', 'LOGIC', 'THINKING', 'INTELLIGENCE')
VERIFIED_SCORES = {
    'train': {'accuracy': 1.0, 'correct': 50, 'total': 50},
    'hidden': {'accuracy': 1.0, 'correct': 50, 'total': 50},
    'fresh': {'accuracy': 1.0, 'correct': 50, 'total': 50},
}
FRESH_ABLATION_DROPS = {
    'MEMORY_EXPERIENCE': 0.2,
    'LOGIC': 0.2,
    'THINKING': 0.2,
    'INTELLIGENCE': 0.2,
}

def component():
    return {
        'schema': 'yado.cognitive_integration_policy.v1',
        'policy_id': COGNITIVE_INTEGRATION_POLICY,
        'required_gates': REQUIRED_GATES,
        'verified_scores': VERIFIED_SCORES,
        'fresh_ablation_drops': FRESH_ABLATION_DROPS,
        'canonical_active': False,
        'automatic_main_mutation': False,
        'consciousness_claimed': False,
    }
