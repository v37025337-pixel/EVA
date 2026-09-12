from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from yado_raw_task_representation_frozen_candidate_v3 import FrozenResidualRepairCandidateV3
from yado_raw_task_representation_robustness_v4 import RobustRawTaskRepresentationRuntimeV4

REPO = Path(__file__).resolve().parent.parent
V3_PATH = REPO / "canonical/yado-raw-task-representation-v3.json"
V4_PATH = REPO / "canonical/yado-raw-task-representation-v4.json"
SEED_PATH = REPO / "resources/yado-raw-task-representation-v4-canonical-admission-fresh-v1.json"
REGRESSION_PATHS = [
    REPO / "resources/yado-raw-task-representation-v4-canonical-admission-fresh-v1.json",
    REPO / "resources/yado-raw-task-representation-v4-robustness-fresh-holdout-v1.json",
    REPO / "resources/yado-raw-task-representation-v4-robustness-fresh-holdout-v2.json",
    REPO / "resources/yado-raw-task-representation-v5-canonical-admission-fresh-v1.json",
]
DEFAULT_OUT = REPO / "candidates/autonomous/yado-raw-task-representation-frozen-deep-admission-v1.json"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect_rows(value: Any) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if isinstance(value, dict):
        if isinstance(value.get("text"), str) and isinstance(value.get("expected"), str):
            rows.append({"text": value["text"], "expected": value["expected"]})
        for child in value.values():
            if isinstance(child, (dict, list)):
                rows.extend(collect_rows(child))
    elif isinstance(value, list):
        for child in value:
            if isinstance(child, (dict, list)):
                rows.extend(collect_rows(child))
    seen = set()
    out = []
    for row in rows:
        key = (row["text"], row["expected"])
        if key not in seen:
            seen.add(key)
            out.append(row)
    return out


def score(runtime: Any, rows: list[dict[str, str]]) -> dict[str, Any]:
    errors = []
    correct = 0
    for row in rows:
        got = runtime.predict_capability(row["text"])
        if got == row["expected"]:
            correct += 1
        else:
            errors.append({
                "text_sha256": sha(row["text"]),
                "expected": row["expected"],
                "got": got,
            })
    n = len(rows)
    return {"n": n, "correct": correct, "accuracy": correct / n if n else None, "errors": errors}


def make_deep_fresh(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    """Create a second, post-freeze perturbation family.

    These transforms differ from the policy-search holdout. Labels are inherited
    from the unchanged semantic task. This is a robustness holdout, not a new
    external-domain benchmark.
    """
    families: dict[str, list[dict[str, str]]] = {
        "nested_wrapper": [],
        "sequential_envelope": [],
        "punctuation_frame": [],
        "mixed_edge_noise": [],
    }
    for idx, row in enumerate(rows):
        text = row["text"]
        expected = row["expected"]
        token = sha(text + "|" + expected + "|deep-admission-v1")[:12]
        families["nested_wrapper"].append({
            "text": f"((audit:{token})) [[ {text} ]] ((/audit:{token}))",
            "expected": expected,
        })
        families["sequential_envelope"].append({
            "text": f"Stage {idx % 19}. Context {token}. {text} Final {idx % 23}.",
            "expected": expected,
        })
        families["punctuation_frame"].append({
            "text": f"<<<{token}>>> ::: {text} ::: <<</{token}>>>",
            "expected": expected,
        })
        families["mixed_edge_noise"].append({
            "text": f"[meta-{idx % 11}] {{{token}}} -- {text} -- {{{token[::-1]}}} [/meta-{idx % 11}]",
            "expected": expected,
        })
    return families


def report() -> dict[str, Any]:
    v3 = load(V3_PATH)
    v4 = load(V4_PATH)
    assert v4["component_id"] == "ALG-G2-RAW-TASK-REPRESENTATION-V4"
    assert v4["canonical_active"] is True
    assert v4["selected_mode"] == "MULTIVIEW_EDGE_TIE_CORE"

    control = RobustRawTaskRepresentationRuntimeV4(v3, v4["selected_mode"])
    candidate = FrozenResidualRepairCandidateV3(v3)

    # Frozen identity is checked before any new evidence is materialized.
    frozen_source = REPO / "runtime/yado_raw_task_representation_frozen_candidate_v3.py"
    frozen_identity = {
        "component_id": candidate.COMPONENT_ID,
        "parent_component_id": candidate.PARENT_COMPONENT_ID,
        "selected_policy": candidate.SELECTED_POLICY,
        "selection_receipt_sha256": candidate.SELECTION_RECEIPT_SHA256,
        "source": str(frozen_source.relative_to(REPO)),
        "source_sha256": file_sha(frozen_source),
        "frozen_before_deep_fresh_generation": True,
    }

    regression = []
    regression_ok = True
    for path in REGRESSION_PATHS:
        rows = collect_rows(load(path))
        if not rows:
            raise RuntimeError(f"EMPTY_REGRESSION_SET:{path.name}")
        c = score(control, rows)
        t = score(candidate, rows)
        preserved = t["accuracy"] >= c["accuracy"]
        regression_ok = regression_ok and preserved
        regression.append({
            "source": str(path.relative_to(REPO)),
            "control": c,
            "candidate": t,
            "delta": t["accuracy"] - c["accuracy"],
            "preserved": preserved,
        })

    seed_rows = collect_rows(load(SEED_PATH))
    if not seed_rows:
        raise RuntimeError("NO_DEEP_FRESH_SEEDS")
    families = make_deep_fresh(seed_rows)
    fresh_results = {}
    total_control_correct = total_candidate_correct = total_n = 0
    improved_families = 0
    for name, rows in families.items():
        c = score(control, rows)
        t = score(candidate, rows)
        delta = t["accuracy"] - c["accuracy"]
        if delta > 0:
            improved_families += 1
        fresh_results[name] = {
            "control": c,
            "candidate": t,
            "delta": delta,
            "no_regression": delta >= 0,
        }
        total_control_correct += c["correct"]
        total_candidate_correct += t["correct"]
        total_n += c["n"]

    control_acc = total_control_correct / total_n
    candidate_acc = total_candidate_correct / total_n
    fresh_delta = candidate_acc - control_acc
    all_fresh_preserved = all(x["no_regression"] for x in fresh_results.values())
    fresh_positive = fresh_delta > 0 and improved_families >= 1
    pass_shadow = regression_ok and all_fresh_preserved and fresh_positive

    if pass_shadow:
        status = "PASS_SHADOW_FROZEN_RAW_REPRESENTATION_DEEP_ADMISSION_V1"
        next_action = "RUN_NATIVE_CORE_DEEP_AUDIT_FRESH_SUCCESSOR_AND_COMPLETE_170_REGRESSION"
    else:
        status = "WITHHOLD_SHADOW_FROZEN_RAW_REPRESENTATION_DEEP_ADMISSION_V1"
        next_action = "RETURN_TO_RESIDUAL_SYNTHESIS_WITH_DEEP_FRESH_COUNTEREXAMPLES"

    out = {
        "schema": "yado.g2.raw_task_representation_frozen_deep_admission.v1",
        "status": status,
        "canonical_mutation": False,
        "automatic_main_mutation": False,
        "consciousness_claimed": False,
        "frozen_candidate": frozen_identity,
        "regression": {"all_preserved": regression_ok, "corpora": regression},
        "deep_fresh_holdout": {
            "created_after_candidate_freeze": True,
            "seed_source": str(SEED_PATH.relative_to(REPO)),
            "families": fresh_results,
            "total_n": total_n,
            "control_accuracy": control_acc,
            "candidate_accuracy": candidate_acc,
            "delta": fresh_delta,
            "improved_family_count": improved_families,
            "all_families_no_regression": all_fresh_preserved,
            "claim_boundary": "Second post-freeze robustness perturbation holdout; not a new external-domain benchmark.",
        },
        "gate": {
            "regression_preserved": regression_ok,
            "deep_fresh_all_families_preserved": all_fresh_preserved,
            "deep_fresh_positive_gain": fresh_positive,
            "admit_to_canonical": False,
        },
        "self_selected_next_action": next_action,
        "semantic_boundary": "Candidate-level deep-admission readiness only. Passing does not itself integrate the candidate into UnifiedYADOCoreV1 and does not establish consciousness or general intelligence.",
    }
    out["receipt_sha256"] = hashlib.sha256(
        json.dumps(out, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()
    r = report()
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(r, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": r["status"],
        "policy": r["frozen_candidate"]["selected_policy"],
        "regression_preserved": r["gate"]["regression_preserved"],
        "fresh_delta": r["deep_fresh_holdout"]["delta"],
        "improved_family_count": r["deep_fresh_holdout"]["improved_family_count"],
        "next_action": r["self_selected_next_action"],
        "receipt_sha256": r["receipt_sha256"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
