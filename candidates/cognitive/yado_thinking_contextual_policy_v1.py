from __future__ import annotations

THINKING_CONTEXT_STRATEGY = None
VERIFIED_SCORES = {}

def component():
    return {
        "schema": "yado.thinking_contextual_policy.v1",
        "status": "WITHHOLD_UNEXECUTED",
        "strategy_id": THINKING_CONTEXT_STRATEGY,
        "verified_scores": VERIFIED_SCORES,
        "canonical_active": False,
        "automatic_main_mutation": False,
        "consciousness_claimed": False,
    }
