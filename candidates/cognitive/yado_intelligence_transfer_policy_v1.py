from __future__ import annotations

INTELLIGENCE_TRANSFER_STRATEGY = 'G4_TRANSFER_AMBIGUITY_GUARD'
VERIFIED_SCORES = {
    'train': {'accuracy': 1.0, 'correct': 56, 'total': 56},
    'hidden': {'accuracy': 1.0, 'correct': 56, 'total': 56},
    'fresh': {'accuracy': 1.0, 'correct': 56, 'total': 56},
}

def component():
    return {
        'schema': 'yado.intelligence_transfer_policy.v1',
        'strategy_id': INTELLIGENCE_TRANSFER_STRATEGY,
        'verified_scores': VERIFIED_SCORES,
        'canonical_active': False,
        'automatic_main_mutation': False,
        'consciousness_claimed': False,
    }
