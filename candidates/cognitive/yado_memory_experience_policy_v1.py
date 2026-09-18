from __future__ import annotations

MEMORY_EXPERIENCE_POLICY = None
VERIFIED_SCORES = {}

def component():
    return {
        "schema": "yado.memory_experience_policy.v1",
        "status": "WITHHOLD_UNEXECUTED",
        "policy": MEMORY_EXPERIENCE_POLICY,
        "verified_scores": VERIFIED_SCORES,
        "canonical_active": False,
        "automatic_main_mutation": False,
        "consciousness_claimed": False,
    }
