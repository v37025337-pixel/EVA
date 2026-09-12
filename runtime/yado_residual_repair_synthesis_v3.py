from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from yado_raw_task_representation_residual_repair_v3 import (
    POLICIES,
    ResidualDrivenRawTaskRepresentationRepairV3,
)
from yado_raw_task_representation_robustness_v4 import RobustRawTaskRepresentationRuntimeV4

REPO = Path(__file__).resolve().parent.parent
V3_PATH = REPO / "canonical/yado-raw-task-representation-v3.json"
V4_PATH = REPO / "canonical/yado-raw-task-representation-v4.json"
EXPERIENCE_PATH = REPO / "resources/yado-raw-task-representation-v5-sequential-robustness-fresh-holdout-v1.json"
DIRECT_HISTORY_PATH = REPO / "resources/yado-raw-task-representation-v5-canonical-admission-fresh-v1.json"
SEED_HOLDOUT_PATH = REPO / "resources/yado-raw-task-representation-v4-canonical-admission-fresh-v1.json"
REGRESSION_PATHS = [
    REPO / "resources/yado-raw-task-representation-v4-canonical-admission-fresh-v1.json",
    REPO / "resources/yado-raw-task-representation-v4-robustness-fresh-holdout-v1.json",
    REPO / "resources/yado-raw-task-representation-v4-robustness-fresh-holdout-v2.json",
    DIRECT_HISTORY_PATH,
]
DEFAULT_OUT = REPO / "candidates/autonomous/yado-residual-repair-synthesis-v3.json"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def digest_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def collect_rows(value: Any) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    if isinstance(value, dict):
        if isinstance(value.get("text"), str) and isinstance(value.get("expected"), str):
            out.append({"text": value["text"], "expected": value["expected"]})
        for child in value.values():
            if isinstance(child, (dict, list)):
                out.extend(collect_rows(child))
    elif isinstance(value, list):
        for child in value:
            if isinstance(child, (dict, list)):
                out.extend(collect_rows(child))
    seen = set()
    dedup = []
    for row in out:
        key = (row["text"], row["expected"])
        if key not in seen:
            seen.add(key)
            dedup.append(row)
    return dedup


def score(runtime: Any, rows: list[dict[str, str]]) -> dict[str, Any]:
    errors = []
    changed = 0
    correct = 0
    for row in rows:
        got = runtime.predict_capability(row["text"])
        if got == row["expected"]:
            correct += 1
        else:
            errors.append({
                "text_sha256": digest_text(row["text"]),
                "expected": row["expected"],
                "got": got,
            })
    return {
        "n": len(rows),
        "correct": correct,
        "accuracy": correct / len(rows) if rows else None,
        "errors": errors,
    }


def changed_count(control: Any, treatment: Any, rows: list[dict[str, str]]) -> int:
    return sum(
        control.predict_capability(r["text"]) != treatment.predict_capability(r["text"])
        for r in rows
    )


def split_experience(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    fit, validation = [], []
    for row in rows:
        bucket = int(digest_text(row["text"])[:8], 16) % 4
        (validation if bucket == 0 else fit).append(row)
    if not validation or not fit:
        raise RuntimeError("DETERMINISTIC_EXPERIENCE_SPLIT_DEGENERATE")
    return fit, validation


def make_generated_holdout(seed_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    out = []
    for idx, row in enumerate(seed_rows):
        token = digest_text(row["text"] + row["expected"])[:10]
        out.extend([
            {
                "text": f"<frame key={token}> {row['text']} </frame>",
                "expected": row["expected"],
            },
            {
                "text": f"Memo {idx % 17}: {row['text']} End {token}.",
                "expected": row["expected"],
            },
            {
                "text": f"[trace={token}] {row['text']} [closed={idx % 23}]",
                "expected": row["expected"],
            },
        ])
    return out


def main_report() -> dict[str, Any]:
    v3 = load(V3_PATH)
    v4 = load(V4_PATH)
    experience_artifact = load(EXPERIENCE_PATH)
    experience_rows = collect_rows(experience_artifact)
    if len(experience_rows) < 20:
        raise RuntimeError(f"INSUFFICIENT_RESIDUAL_EXPERIENCE:{len(experience_rows)}")
    fit_rows, validation_rows = split_experience(experience_rows)

    control = RobustRawTaskRepresentationRuntimeV4(v3, v4["selected_mode"])
    control_fit = score(control, fit_rows)
    control_validation = score(control, validation_rows)
    control_all = score(control, experience_rows)

    regression_sets = [(p, collect_rows(load(p))) for p in REGRESSION_PATHS]
    if any(not rows for _, rows in regression_sets):
        raise RuntimeError("EMPTY_REGRESSION_CORPUS")
    control_regression = {str(p.relative_to(REPO)): score(control, rows) for p, rows in regression_sets}

    policy_results = []
    for policy in POLICIES:
        runtime = ResidualDrivenRawTaskRepresentationRepairV3(v3, policy)
        fit = score(runtime, fit_rows)
        validation = score(runtime, validation_rows)
        all_exp = score(runtime, experience_rows)
        regressions = {}
        regression_ok = True
        for path, rows in regression_sets:
            key = str(path.relative_to(REPO))
            result = score(runtime, rows)
            regressions[key] = result
            regression_ok = regression_ok and result["accuracy"] >= control_regression[key]["accuracy"]
        policy_results.append({
            "policy": policy,
            "fit": fit,
            "validation": validation,
            "all_experience": all_exp,
            "fit_gain": fit["accuracy"] - control_fit["accuracy"],
            "validation_gain": validation["accuracy"] - control_validation["accuracy"],
            "all_experience_gain": all_exp["accuracy"] - control_all["accuracy"],
            "changed_on_experience": changed_count(control, runtime, experience_rows),
            "regression_ok": regression_ok,
            "regressions": regressions,
        })

    admissible_search = [p for p in policy_results if p["regression_ok"]]
    if not admissible_search:
        raise RuntimeError("NO_POLICY_PRESERVES_REGRESSION")
    admissible_search.sort(key=lambda p: (
        -p["validation_gain"],
        -p["fit_gain"],
        -p["all_experience_gain"],
        p["changed_on_experience"],
        p["policy"],
    ))
    selected = admissible_search[0]
    selected_runtime = ResidualDrivenRawTaskRepresentationRepairV3(v3, selected["policy"])

    # Materialize the generated holdout only after policy selection is complete.
    seed_rows = collect_rows(load(SEED_HOLDOUT_PATH))
    generated_rows = make_generated_holdout(seed_rows)
    generated_control = score(control, generated_rows)
    generated_selected = score(selected_runtime, generated_rows)
    generated_gain = generated_selected["accuracy"] - generated_control["accuracy"]
    generated_no_regression = generated_gain >= 0.0

    selected_non_control = selected["policy"] != "V4_CONTROL"
    evidence_gain = selected["validation_gain"] > 0.0 and selected["all_experience_gain"] > 0.0
    fit_not_worse = selected["fit_gain"] >= 0.0
    pass_shadow = (
        selected_non_control
        and evidence_gain
        and fit_not_worse
        and selected["regression_ok"]
        and generated_no_regression
    )

    if pass_shadow:
        status = "PASS_SHADOW_RESIDUAL_REPAIR_SYNTHESIS_V3"
        next_action = "FREEZE_SELECTED_POLICY_THEN_RUN_DEEP_ADMISSION_AUDIT_SUCCESSOR_REGRESSION"
    else:
        status = "WITHHOLD_SHADOW_RESIDUAL_REPAIR_SYNTHESIS_V3"
        next_action = "EXPAND_REPAIR_REPRESENTATION_FROM_RESIDUAL_ERROR_CLUSTERS_WITHOUT_CANONICAL_MUTATION"

    report = {
        "schema": "yado.g2.residual_repair_synthesis.v3",
        "status": status,
        "canonical_mutation": False,
        "automatic_main_mutation": False,
        "consciousness_claimed": False,
        "input_experience": {
            "source": str(EXPERIENCE_PATH.relative_to(REPO)),
            "historical_metrics": experience_artifact.get("metrics"),
            "row_count": len(experience_rows),
            "fit_count": len(fit_rows),
            "validation_count": len(validation_rows),
            "split": "SHA256(text) mod 4; bucket 0 validation, others fit",
        },
        "control": {
            "component": v4["component_id"],
            "mode": v4["selected_mode"],
            "fit": control_fit,
            "validation": control_validation,
            "all_experience": control_all,
        },
        "search": {
            "policy_family": list(POLICIES),
            "policy_results": policy_results,
            "selection_rule": "maximize validation gain, then fit gain, all-experience gain, then minimize changed predictions; only regression-preserving policies eligible",
            "selected": selected,
        },
        "generated_holdout": {
            "created_after_policy_selection": True,
            "seed_source": str(SEED_HOLDOUT_PATH.relative_to(REPO)),
            "n": len(generated_rows),
            "control": generated_control,
            "selected": generated_selected,
            "gain": generated_gain,
            "no_regression": generated_no_regression,
            "claim_boundary": "Perturbations of known labeled tasks, not a new external-domain benchmark.",
        },
        "causal_evaluation": {
            "selected_non_control": selected_non_control,
            "historical_validation_gain_positive": selected["validation_gain"] > 0.0,
            "historical_all_experience_gain_positive": selected["all_experience_gain"] > 0.0,
            "historical_fit_not_worse": fit_not_worse,
            "canonical_regression_preserved": selected["regression_ok"],
            "generated_holdout_preserved": generated_no_regression,
            "admit_candidate": False,
        },
        "self_selected_next_action": next_action,
        "semantic_boundary": "Bounded policy synthesis from historical residual errors with held-out and regression gates. No canonical admission, no claim of consciousness or general self-modification.",
    }
    report["receipt_sha256"] = hashlib.sha256(
        json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()
    report = main_report()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    s = report["search"]["selected"]
    print(json.dumps({
        "status": report["status"],
        "selected_policy": s["policy"],
        "fit_gain": s["fit_gain"],
        "validation_gain": s["validation_gain"],
        "all_experience_gain": s["all_experience_gain"],
        "changed_on_experience": s["changed_on_experience"],
        "regression_ok": s["regression_ok"],
        "generated_holdout_gain": report["generated_holdout"]["gain"],
        "next_action": report["self_selected_next_action"],
        "canonical_mutation": report["canonical_mutation"],
        "receipt_sha256": report["receipt_sha256"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
