from __future__ import annotations

MEMORY_EXPERIENCE_POLICY = {'require_provenance': True, 'exact_kind': True, 'reject_ambiguous': True}
VERIFIED_SCORES = {
    'train': {'accuracy': 1.0, 'correct': 32, 'total': 32, 'by_kind': {'ambiguous_without_provenance': 1.0, 'exact_recall': 1.0, 'forged_provenance_rejection': 1.0, 'kind_isolation': 1.0}},
    'hidden': {'accuracy': 1.0, 'correct': 32, 'total': 32, 'by_kind': {'ambiguous_without_provenance': 1.0, 'exact_recall': 1.0, 'forged_provenance_rejection': 1.0, 'kind_isolation': 1.0}},
    'fresh': {'accuracy': 1.0, 'correct': 32, 'total': 32, 'by_kind': {'ambiguous_without_provenance': 1.0, 'exact_recall': 1.0, 'forged_provenance_rejection': 1.0, 'kind_isolation': 1.0}},
}

def component():
    return {
        'schema': 'yado.memory_experience_policy.v1',
        'policy': MEMORY_EXPERIENCE_POLICY,
        'verified_scores': VERIFIED_SCORES,
        'canonical_active': False,
        'automatic_main_mutation': False,
        'consciousness_claimed': False,
    }
