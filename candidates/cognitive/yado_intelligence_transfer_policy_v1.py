from __future__ import annotations

INTELLIGENCE_TRANSFER_STRATEGY = None
VERIFIED_SCORES = {}

def component():
    return {
        "schema": "yado.intelligence_transfer_policy.v1",
        "status": "WITHHOLD_UNEXECUTED",
        "strategy_id": INTELLIGENCE_TRANSFER_STRATEGY,
        "verified_scores": VERIFIED_SCORES,
        "canonical_active": False,
        "automatic_main_mutation": False,
        "consciousness_claimed": False,
    }
