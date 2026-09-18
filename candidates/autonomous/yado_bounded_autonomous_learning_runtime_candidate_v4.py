from __future__ import annotations

SELF_REWRITE_V4_STATUS = "WITHHOLD_UNEXECUTED"

def component():
    return {
        "schema": "yado.native_self_rewrite_v4_candidate.placeholder.v1",
        "status": SELF_REWRITE_V4_STATUS,
        "canonical_active": False,
        "automatic_main_mutation": False,
    }
