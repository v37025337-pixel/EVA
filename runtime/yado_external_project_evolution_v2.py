from __future__ import annotations

"""Three-generation, state-derived evolution over admitted project data."""

import copy
import hashlib
import json
from typing import Any

from yado_external_project_training_v1 import (
    SOURCE_ROWS,
    STATUS_PASS,
    STATUS_WITHHOLD,
    route,
    train,
)


SCHEMA = "yado.external_project_evolution.v2"

# G2 receives supervised tasks from the admitted source observations.
SEED_TASKS = (
    ("validate admission criteria and security review", "LOGIC"),
    ("preserve workspace context across architecture events", "THINKING"),
    ("coordinate agent resources and supervise adaptation", "INTELLIGENCE"),
    ("review explicit state and acceptance criteria", "LOGIC"),
)

# G3 receives a distinct continuation campaign. These rows are not the holdout.
ADAPTATION_TASKS = (
    ("sequence persistence and workflow context", "THINKING"),
    ("catalog resource and coordinate agent selection", "INTELLIGENCE"),
)

HOLDOUT_TASKS = (
    ("inspect validated state before admission", "LOGIC"),
    ("map architecture events to persistent workspace", "THINKING"),
    ("supervise agent workflow and adapt resource routing", "INTELLIGENCE"),
)


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _rows(tasks):
    return tuple(
        {
            "repository": "derived/yado-experience",
            "ref": "shadow",
            "source_url": "https://github.com/v37025337-pixel/EVA",
            "lines": "derived-experience",
            "observation": task,
            "labels": (label,),
        }
        for task, label in tasks
    )


def _train(rows):
    # Derived rows are intentionally admitted only after their origin is recorded.
    from yado_external_project_training_v1 import ALLOWED_REPOSITORIES, validate_rows

    original = ALLOWED_REPOSITORIES.get("derived/yado-experience")
    ALLOWED_REPOSITORIES["derived/yado-experience"] = "shadow"
    try:
        return train(rows)
    finally:
        if original is None:
            del ALLOWED_REPOSITORIES["derived/yado-experience"]
        else:
            ALLOWED_REPOSITORIES["derived/yado-experience"] = original


def _passes(trained, tasks):
    results = []
    for task, expected in tasks:
        result = route(task, trained)
        results.append(
            {
                "task": task,
                "expected": expected,
                "selected": result.get("capability"),
                "pass": result.get("status") == STATUS_PASS and result.get("capability") == expected,
            }
        )
    return results


def run() -> dict[str, Any]:
    g1 = train(SOURCE_ROWS)
    g1_seed = _passes(g1, SEED_TASKS)
    g1_failures = sum(1 for item in g1_seed if not item["pass"])
    if g1_failures == 0:
        raise RuntimeError("G1_BASELINE_DEFECT_REQUIRED_FOR_EVOLUTION_PROOF")

    g2_rows = tuple(SOURCE_ROWS) + _rows(SEED_TASKS)
    g2 = _train(g2_rows)
    g2_results = _passes(g2, SEED_TASKS)
    if not all(item["pass"] for item in g2_results):
        raise RuntimeError("G2_SEED_REPLAY_FAILED")

    g3_rows = g2_rows + _rows(ADAPTATION_TASKS)
    g3 = _train(g3_rows)
    holdout = _passes(g3, HOLDOUT_TASKS)
    if not all(item["pass"] for item in holdout):
        raise RuntimeError("G3_HOLDOUT_FAILED")

    return {
        "schema": SCHEMA,
        "status": "PASS_SHADOW_THREE_STATE_DERIVED_GENERATIONS_V2",
        "generations": [
            {"generation": "G1", "rows": len(SOURCE_ROWS), "seed_replay": g1_seed, "baseline_failures": g1_failures},
            {"generation": "G2", "rows": len(g2_rows), "seed_replay": g2_results},
            {"generation": "G3", "rows": len(g3_rows), "holdout": holdout},
        ],
        "state_transition": "SOURCE_OBSERVATIONS_TO_SEED_EXPERIENCE_TO_ADAPTATION_EXPERIENCE",
        "training_digests": [g1["training_digest"], g2["training_digest"], g3["training_digest"]],
        "holdout_count": len(holdout),
        "unknown_withhold": route("unseen semantic domain", g3)["status"] == STATUS_WITHHOLD,
        "third_party_code_executed": False,
        "external_writes": False,
        "automatic_main_mutation": False,
        "g4_genesis_performed": False,
    }
