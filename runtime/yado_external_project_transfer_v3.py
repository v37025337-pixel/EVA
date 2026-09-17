from __future__ import annotations

"""G4 transfer and ambiguity guard derived from the three-generation receipt."""

import hashlib
import json
import re
from typing import Any

from yado_external_project_evolution_v2 import (
    ADAPTATION_TASKS,
    SEED_TASKS,
    _rows,
    _train,
    run as run_three_generations,
)
from yado_external_project_training_v1 import SOURCE_ROWS, STATUS_PASS, STATUS_WITHHOLD, route


SCHEMA = "yado.external_project_transfer.v3"
STATUS_AMBIGUOUS = "WITHHOLD_G4_AMBIGUOUS_MULTI_CAPABILITY_TASK"
TRANSFER_TASKS = (
    ("admit a validated free-tier security criterion", "LOGIC"),
    ("restore workspace context after an architecture event", "THINKING"),
    ("supervise MCP agents while selecting resources", "INTELLIGENCE"),
)
AMBIGUOUS_TASK = "review agent state and coordinate security admission"


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.lower()))


def _profile_scores(task: str, trained: dict[str, Any]):
    tokens = _tokens(task)
    scores = {}
    for capability, profile in trained["profiles"].items():
        matched = [token for token in profile if token in tokens]
        raw = sum(profile[token] for token in matched)
        scores[capability] = (raw / sum(profile.values())) if profile else 0.0
    return scores


def route_transfer(task: str, trained: dict[str, Any]) -> dict[str, Any]:
    """Use G3 profiles, withholding when multiple capability families are active."""
    base = route(task, trained)
    scores = sorted(_profile_scores(task, trained).items(), key=lambda item: item[1], reverse=True)
    active = [capability for capability, score in scores if score > 0.0]
    if len(active) > 1 and (scores[0][1] - scores[1][1]) <= 0.25:
        return {
            "status": STATUS_AMBIGUOUS,
            "capability": None,
            "reason": "AMBIGUOUS_MULTI_CAPABILITY_TASK",
            "active_capabilities": active,
        }
    return base


def run() -> dict[str, Any]:
    prior = run_three_generations()
    if prior["status"] != "PASS_SHADOW_THREE_STATE_DERIVED_GENERATIONS_V2":
        raise RuntimeError("G3_RECEIPT_REQUIRED")
    g3 = _train(tuple(SOURCE_ROWS) + _rows(SEED_TASKS) + _rows(ADAPTATION_TASKS))
    transfer = []
    for task, expected in TRANSFER_TASKS:
        result = route_transfer(task, g3)
        transfer.append({
            "task": task,
            "expected": expected,
            "selected": result.get("capability"),
            "pass": result.get("status") == STATUS_PASS and result.get("capability") == expected,
        })
    if not all(item["pass"] for item in transfer):
        raise RuntimeError("G4_TRANSFER_HOLDOUT_FAILED")

    baseline_ambiguous = route(AMBIGUOUS_TASK, g3)
    guarded_ambiguous = route_transfer(AMBIGUOUS_TASK, g3)
    if baseline_ambiguous.get("status") != STATUS_PASS or guarded_ambiguous.get("status") != STATUS_AMBIGUOUS:
        raise RuntimeError("G4_AMBIGUITY_GUARD_NOT_PROVEN")

    return {
        "schema": SCHEMA,
        "status": "PASS_SHADOW_G4_TRANSFER_AND_AMBIGUITY_GUARD_V3",
        "parent_status": prior["status"],
        "transfer_count": len(transfer),
        "transfer": transfer,
        "baseline_ambiguous_selected": baseline_ambiguous.get("capability"),
        "guarded_ambiguous_status": guarded_ambiguous.get("status"),
        "training_digest": g3["training_digest"],
        "receipt_digest": _digest(prior),
        "unknown_withhold": route_transfer("unseen semantic domain", g3)["status"] == STATUS_WITHHOLD,
        "third_party_code_executed": False,
        "external_writes": False,
        "automatic_main_mutation": False,
        "g5_genesis_performed": False,
    }
