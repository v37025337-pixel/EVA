from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from yado_raw_task_representation_experience_repair_v2 import (
    ExperienceGuidedRawTaskRepresentationRepairV2,
)
from yado_raw_task_representation_robustness_v4 import RobustRawTaskRepresentationRuntimeV4

REPO = Path(__file__).resolve().parent.parent
GOAL_PATH = REPO / "candidates/autonomous/yado-endogenous-goal-genesis-v1.json"
HISTORY_PATH = REPO / "receipts/yado-g2-raw-representation-v5-canonical-admission-v1-run-33900049280.json"
HISTORY_DATA_PATH = REPO / "resources/yado-raw-task-representation-v5-canonical-admission-fresh-v1.json"
V3_PATH = REPO / "canonical/yado-raw-task-representation-v3.json"
V4_PATH = REPO / "canonical/yado-raw-task-representation-v4.json"
V4_RUNTIME_PATH = REPO / "runtime/yado_raw_task_representation_robustness_v4.py"
V1_HARNESS_PATH = REPO / "runtime/yado_causal_ablation_cycle_v1.py"
CANDIDATE_PATH = REPO / "runtime/yado_raw_task_representation_experience_repair_v2.py"
REGRESSION_PATHS = [
    REPO / "resources/yado-raw-task-representation-v4-canonical-admission-fresh-v1.json",
    REPO / "resources/yado-raw-task-representation-v4-robustness-fresh-holdout-v1.json",
    REPO / "resources/yado-raw-task-representation-v4-robustness-fresh-holdout-v2.json",
]
DEFAULT_OUT = REPO / "candidates/autonomous/yado-causal-ablation-cycle-v2.json"
EXPECTED_GOAL = "KERNEL_G2_RAW_REPRESENTATION_V4_ROBUSTNESS_SELF_EVOLUTION_V2"
EXPECTED_ACTION = "CAUSAL_ABLATION_OF_CANDIDATE_IMPROVEMENT"
EXPECTED_V4 = "ALG-G2-RAW-TASK-REPRESENTATION-V4"
EXPECTED_V4_MODE = "MULTIVIEW_EDGE_TIE_CORE"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def receipt_digest(value: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json(value).encode("utf-8"))


def collect_rows(value: Any, path: str = "root") -> list[tuple[str, dict[str, Any]]]:
    rows: list[tuple[str, dict[str, Any]]] = []
    if isinstance(value, dict):
        if isinstance(value.get("text"), str) and isinstance(value.get("expected"), str):
            rows.append((path, value))
        for key, child in value.items():
            if isinstance(child, (dict, list)):
                rows.extend(collect_rows(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            if isinstance(child, (dict, list)):
                rows.extend(collect_rows(child, f"{path}[{idx}]"))
    return rows


def lane_from_path(path: str) -> str:
    p = path.lower()
    if "sequential" in p or "sequence" in p:
        return "sequential"
    if "wrapped" in p or "wrapper" in p:
        return "wrapped"
    if "direct" in p or "plain" in p:
        return "direct"
    return "other"


def score(runtime: Any, rows: list[tuple[str, dict[str, Any]]]) -> dict[str, Any]:
    totals: dict[str, int] = defaultdict(int)
    correct: dict[str, int] = defaultdict(int)
    disagreements: list[dict[str, Any]] = []
    for path, row in rows:
        lane = lane_from_path(path)
        pred = runtime.predict_capability(row["text"])
        expected = row["expected"]
        totals[lane] += 1
        if pred == expected:
            correct[lane] += 1
        else:
            disagreements.append({
                "lane": lane,
                "text_sha256": sha256_bytes(row["text"].encode("utf-8")),
                "expected": expected,
                "predicted": pred,
            })
    metrics = {}
    for lane in sorted(totals):
        metrics[lane] = {
            "n": totals[lane],
            "correct": correct[lane],
            "accuracy": correct[lane] / totals[lane] if totals[lane] else None,
        }
    total = sum(totals.values())
    total_correct = sum(correct.values())
    return {
        "metrics": metrics,
        "overall": total_correct / total if total else None,
        "n": total,
        "errors": disagreements,
    }


def generated_holdout(base_rows: list[tuple[str, dict[str, Any]]]) -> list[tuple[str, dict[str, Any]]]:
    # Candidate source is fixed before these perturbations are materialized.  Labels are inherited
    # from the unmodified task; only generic non-semantic edge/sequential noise is added.
    unique: dict[str, dict[str, Any]] = {}
    for _, row in base_rows:
        key = sha256_bytes((row["text"] + "|" + row["expected"]).encode("utf-8"))
        unique.setdefault(key, row)
    out: list[tuple[str, dict[str, Any]]] = []
    for idx, (key, row) in enumerate(sorted(unique.items())):
        token = key[:8]
        text = row["text"]
        expected = row["expected"]
        out.append((f"generated.wrapped[{idx}]", {
            "text": f"(trace_{token}) {text} <seal_{token}>",
            "expected": expected,
        }))
        out.append((f"generated.sequential[{idx}]", {
            "text": f"Hdr {token}. {text} End {token}.",
            "expected": expected,
        }))
    return out


def lane_accuracy(result: dict[str, Any], lane: str) -> float | None:
    lane_result = result["metrics"].get(lane)
    return None if lane_result is None else lane_result["accuracy"]


def compare(control: dict[str, Any], treatment: dict[str, Any]) -> dict[str, Any]:
    lanes = sorted(set(control["metrics"]) | set(treatment["metrics"]))
    deltas = {}
    for lane in lanes:
        a = lane_accuracy(control, lane)
        b = lane_accuracy(treatment, lane)
        deltas[lane] = None if a is None or b is None else b - a
    overall_delta = None
    if control["overall"] is not None and treatment["overall"] is not None:
        overall_delta = treatment["overall"] - control["overall"]
    return {"lanes": deltas, "overall": overall_delta}


def generate() -> dict[str, Any]:
    goal = load(GOAL_PATH)
    history = load(HISTORY_PATH)
    history_data = load(HISTORY_DATA_PATH)
    v3 = load(V3_PATH)
    v4 = load(V4_PATH)

    if goal.get("selected_goal") != EXPECTED_GOAL:
        raise RuntimeError(f"UNEXPECTED_ENDOGENOUS_GOAL:{goal.get('selected_goal')}")
    selected_action = (goal.get("selected_action") or {}).get("action")
    if selected_action != EXPECTED_ACTION:
        raise RuntimeError(f"UNEXPECTED_ENDOGENOUS_ACTION:{selected_action}")
    if goal.get("host_supplied_goal") is not False or goal.get("host_selected_goal") is not False:
        raise RuntimeError("GOAL_NOT_ENDOGENOUS")

    # Study the two V1 fail-closed errors from the actual prior harness text.
    v1_text = V1_HARNESS_PATH.read_text(encoding="utf-8")
    stale_provenance_pattern_present = "HISTORICAL_CANDIDATE_SHA256" in v1_text
    stale_physical_binding_present = "raw_representation_consumers" in v1_text and "yado_rc8_v36" in v1_text
    learned_errors = [
        {
            "error_id": "V1_STALE_HARDCODED_PROVENANCE",
            "observed": stale_provenance_pattern_present,
            "lesson": "Candidate identity must be read from canonical receipt/evidence, not duplicated as a harness constant.",
            "correction": "BIND_HISTORY_CANDIDATE_DIGEST_FROM_CANONICAL_RECEIPT",
        },
        {
            "error_id": "V1_WRONG_PHYSICAL_RUNTIME_BINDING",
            "observed": stale_physical_binding_present,
            "lesson": "Developmental frontier identity does not imply that the mechanism lives in reconstructed RC8 runtime.py.",
            "correction": "RESOLVE_ACTIVE_RAW_COMPONENT_AND_RUNTIME_SOURCE_FROM_CANONICAL_V4",
        },
    ]
    if not all(x["observed"] for x in learned_errors):
        raise RuntimeError("PRIOR_FAILURE_SIGNATURE_NOT_REPRODUCED")

    history_digest = history.get("candidate_digest")
    evidence_digest = history_data.get("candidate_digest_fixed_before_fresh")
    if not history_digest or history_digest != evidence_digest:
        raise RuntimeError("CANONICAL_V5_PROVENANCE_MISMATCH")

    if v4.get("component_id") != EXPECTED_V4 or v4.get("canonical_active") is not True:
        raise RuntimeError("CANONICAL_V4_IDENTITY_INVALID")
    if v4.get("selected_mode") != EXPECTED_V4_MODE:
        raise RuntimeError("CANONICAL_V4_MODE_CHANGED")
    if v4.get("runtime_source") != str(V4_RUNTIME_PATH.relative_to(REPO)):
        raise RuntimeError("CANONICAL_V4_RUNTIME_SOURCE_CHANGED")
    if v3.get("component_id") != "ALG-G2-RAW-TASK-REPRESENTATION-V3" or v3.get("canonical_active") is not True:
        raise RuntimeError("CANONICAL_V3_PARENT_INVALID")

    control = RobustRawTaskRepresentationRuntimeV4(v3, EXPECTED_V4_MODE)
    treatment = ExperienceGuidedRawTaskRepresentationRepairV2(v3)

    historical_rows = collect_rows(history_data)
    if not historical_rows:
        raise RuntimeError("NO_HISTORICAL_EXPERIENCE_ROWS")
    history_control = score(control, historical_rows)
    history_treatment = score(treatment, historical_rows)
    history_delta = compare(history_control, history_treatment)

    regression_results = []
    regression_ok = True
    for path in REGRESSION_PATHS:
        rows = collect_rows(load(path))
        if not rows:
            raise RuntimeError(f"NO_REGRESSION_ROWS:{path.name}")
        c = score(control, rows)
        t = score(treatment, rows)
        delta = compare(c, t)
        no_regression = t["overall"] is not None and c["overall"] is not None and t["overall"] >= c["overall"]
        regression_ok = regression_ok and no_regression
        regression_results.append({
            "source": str(path.relative_to(REPO)),
            "control": c,
            "treatment": t,
            "delta": delta,
            "no_regression": no_regression,
        })

    # New perturbations are generated only after the candidate source has already been fixed.
    direct_seed_rows = [(p, r) for p, r in historical_rows if lane_from_path(p) == "direct"]
    if not direct_seed_rows:
        direct_seed_rows = collect_rows(load(REGRESSION_PATHS[0]))
    fresh_rows = generated_holdout(direct_seed_rows)
    fresh_control = score(control, fresh_rows)
    fresh_treatment = score(treatment, fresh_rows)
    fresh_delta = compare(fresh_control, fresh_treatment)
    fresh_no_regression = (
        fresh_control["overall"] is not None
        and fresh_treatment["overall"] is not None
        and fresh_treatment["overall"] >= fresh_control["overall"]
    )

    direct_delta = history_delta["lanes"].get("direct")
    wrapped_delta = history_delta["lanes"].get("wrapped")
    sequential_delta = history_delta["lanes"].get("sequential")
    target_gain = any((d is not None and d > 0.0) for d in (wrapped_delta, sequential_delta))
    direct_preserved = direct_delta is None or direct_delta >= 0.0
    causal_candidate_pass = regression_ok and fresh_no_regression and direct_preserved and target_gain

    if causal_candidate_pass:
        status = "PASS_SHADOW_CAUSAL_ABLATION_CYCLE_V2"
        verdict = "EXPERIENCE_GUIDED_REPAIR_HAS_CAUSAL_SUPPORT"
        next_action = "RUN_FULL_KERNEL_AUDIT_FRESH_SUCCESSOR_AND_COMPLETE_REGRESSION_GATE"
    else:
        status = "WITHHOLD_SHADOW_CAUSAL_ABLATION_CYCLE_V2"
        verdict = "EXPERIENCE_GUIDED_REPAIR_NOT_YET_ADMISSIBLE"
        next_action = "SYNTHESIZE_NEXT_REPAIR_FROM_RESIDUAL_COUNTEREXAMPLES_WITHOUT_CANONICAL_MUTATION"

    report: dict[str, Any] = {
        "schema": "yado.causal_ablation_cycle.v2",
        "status": status,
        "canonical_mutation": False,
        "architecture_mutation": False,
        "automatic_main_mutation": False,
        "consciousness_claimed": False,
        "goal_provenance": {
            "goal": goal.get("selected_goal"),
            "action": selected_action,
            "goal_source": goal.get("goal_source"),
            "host_supplied_goal": goal.get("host_supplied_goal"),
            "host_selected_goal": goal.get("host_selected_goal"),
        },
        "self_correction": {
            "prior_cycle": "yado.causal_ablation_cycle.v1",
            "learned_errors": learned_errors,
            "corrections_applied": [x["correction"] for x in learned_errors],
            "historical_candidate_digest_bound_from_receipt": history_digest,
            "active_component": v4.get("component_id"),
            "active_runtime_source": v4.get("runtime_source"),
            "active_mode": v4.get("selected_mode"),
        },
        "candidate": {
            "component_id": treatment.COMPONENT_ID,
            "parent_component_id": treatment.PARENT_COMPONENT_ID,
            "strategy": "V4_DEFAULT_STRONG_CLEAN_VIEW_CONSENSUS_OVERRIDE",
            "source": str(CANDIDATE_PATH.relative_to(REPO)),
            "source_sha256": sha256_file(CANDIDATE_PATH),
            "fixed_before_generated_holdout": True,
        },
        "experience_replay": {
            "source": str(HISTORY_DATA_PATH.relative_to(REPO)),
            "historical_v5_candidate_digest": history_digest,
            "historical_v5_status": history.get("status"),
            "control": history_control,
            "treatment": history_treatment,
            "delta": history_delta,
            "note": "Historical rows are experience replay, not fresh admission evidence.",
        },
        "regression": {
            "all_no_regression": regression_ok,
            "corpora": regression_results,
        },
        "generated_holdout": {
            "design": "POST_FIX_GENERIC_WRAPPER_AND_SEQUENTIAL_PERTURBATIONS_FROM_DIRECT_TASKS",
            "row_count": len(fresh_rows),
            "control": fresh_control,
            "treatment": fresh_treatment,
            "delta": fresh_delta,
            "no_regression": fresh_no_regression,
            "claim_boundary": "New perturbations of known labeled tasks; not a new external-domain benchmark.",
        },
        "causal_evaluation": {
            "verdict": verdict,
            "target_gain_on_historical_wrapper_or_sequential_lane": target_gain,
            "historical_direct_preserved": direct_preserved,
            "regression_preserved": regression_ok,
            "generated_holdout_preserved": fresh_no_regression,
            "admit_candidate": False,
            "reason": (
                "Candidate shows bounded causal support; canonical admission is still forbidden until full kernel audit, fresh successor and complete regression pass."
                if causal_candidate_pass
                else "The corrected physical experiment completed, but the candidate did not satisfy every preregistered causal gate. Residual counterexamples must drive the next shadow synthesis."
            ),
        },
        "self_selected_next_action": next_action,
        "next_action_constraints": {
            "canonical_direct_write": False,
            "full_kernel_audit_required_before_admission": True,
            "fresh_successor_required_before_admission": True,
            "complete_regression_required_before_admission": True,
            "no_historical_v5_code_reconstruction_by_guess": True,
        },
        "semantic_boundary": "Bounded self-correction and causal shadow evaluation of raw-task representation. This does not establish consciousness, general agency, or unrestricted self-modification.",
    }
    report["receipt_sha256"] = receipt_digest(report)
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()
    report = generate()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "verdict": report["causal_evaluation"]["verdict"],
        "learned_errors": [x["error_id"] for x in report["self_correction"]["learned_errors"]],
        "history_delta": report["experience_replay"]["delta"],
        "fresh_delta": report["generated_holdout"]["delta"],
        "regression_preserved": report["causal_evaluation"]["regression_preserved"],
        "next_action": report["self_selected_next_action"],
        "canonical_mutation": report["canonical_mutation"],
        "receipt_sha256": report["receipt_sha256"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
