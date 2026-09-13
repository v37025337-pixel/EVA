"""Prove the second bounded deficit-driven improvement after baseline V2 was frozen.

The frozen baseline is rerun first with EvolvedSuccessorKernelV1.  Only then is the
V2 candidate evaluated on the identical real-code tasks.  Candidate selection sees
TRAINING labels only.  The known not_gate split is reported as underdetermined rather
than special-cased: both repair and synthesis training partitions contain only the
zero-output class while the hidden partition contains the unseen positive class.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import tempfile
import time
from typing import Any

from .evolved_kernel import EvolvedSuccessorKernelV1
from .evolved_kernel_v2 import EvolvedSuccessorKernelV2
from .kernel import equivalent
from .real_coding_intelligence_run import ALGORITHMS_URL, discover_real_code_tasks, run_repair
from .real_coding_self_improvement_run import checkout_exact, clone_latest, _git
from .second_cycle_baseline_v2 import (
    ALGORITHMS_V2_SHA,
    REASONING_TARGETS_V2,
    discover_extended_tasks,
    _reasoning_probes,
)

FROZEN_EVIDENCE = Path(__file__).with_name("evidence") / "second_cycle_baseline_v2.json"


def _labelled(task: dict[str, Any], row) -> dict[str, Any]:
    args, expected = row
    return {"input": dict(zip(task["args"], args)), "expected": expected}


def synthesis_probe(kernel, task: dict[str, Any], head: str, *, training_count: int = 8) -> dict[str, Any]:
    rows = task["rows"]
    if len(rows) <= training_count:
        raise ValueError("V2_SYNTHESIS_HOLDOUT_REQUIRED")
    training = [_labelled(task, row) for row in rows[:training_count]]
    hidden = rows[training_count:]
    failure_reason = None
    result: dict[str, Any] = {}
    try:
        event = kernel.execute({
            "kind": "program_synthesis",
            "payload": {"training": copy.deepcopy(training)},
            "history_query": "frozen second-cycle deficit-driven source synthesis",
        })
        event_status = event.get("status", "UNKNOWN")
        result = event.get("result") or {}
        candidate = result if result.get("source") else None
    except Exception as exc:
        event_status = "ERROR"
        candidate = None
        failure_reason = f"{type(exc).__name__}:{exc}"

    # Candidate digest is frozen before any hidden expected value is used below.
    frozen_digest = result.get("source_sha256") if candidate else None
    checks: list[bool] = []
    if candidate:
        inputs = [dict(zip(task["args"], args)) for args, _ in hidden]
        try:
            predictions = kernel.execute_synthesized(candidate, inputs)
            checks = [equivalent(got, expected) for got, (_, expected) in zip(predictions, hidden)]
        except Exception as exc:
            checks = [False] * len(hidden)
            failure_reason = f"{type(exc).__name__}:{exc}"
    passed = bool(candidate and checks and all(checks))
    return {
        "task_id": f"synthesis:{task['path']}:{task['function']}",
        "family": "SECOND_CYCLE_REAL_CODE_SYNTHESIS",
        "status": "PASS" if passed else "DEFICIT",
        "kernel_event_status": event_status,
        "features": task.get("features", []),
        "selected_profile": (result.get("selected") or {}).get("profile"),
        "selected_template": (result.get("selected") or {}).get("template"),
        "candidate_source_sha256_frozen_before_holdout": frozen_digest,
        "holdout_passed": sum(checks),
        "holdout_total": len(hidden),
        "failure_reason": None if passed else (failure_reason or result.get("reason", "NO_GENERALIZING_SOURCE")),
        "training_labels_only_for_selection": True,
        "holdout_labels_consumed_during_selection": False,
        "provenance": {
            "repository": ALGORITHMS_URL,
            "head_sha": head,
            "path": task["path"],
            "function": task["function"],
            "source_sha256": task["source_sha256"],
            "target_expression_sha256": task["target_expression_sha256"],
        },
    }


def repair_probe(kernel, task: dict[str, Any], head: str) -> dict[str, Any]:
    try:
        row = run_repair(kernel, task, head)
    except Exception as exc:
        return {
            "task_id": f"repair:{task['path']}:{task['function']}",
            "family": "SECOND_CYCLE_REAL_CODE_REPAIR",
            "status": "DEFICIT",
            "features": task.get("features", []),
            "failure_reason": f"{type(exc).__name__}:{exc}",
        }
    row = copy.deepcopy(row)
    row["family"] = "SECOND_CYCLE_REAL_CODE_REPAIR"
    row["features"] = task.get("features", [])
    return row


def _score(rows: list[dict[str, Any]], success: str = "PASS") -> int:
    return sum(row.get("status") == success for row in rows)


def _task_map(tasks: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    return {(task["path"], task["function"]): task for task in tasks}


def _not_gate_identifiability(tasks: list[dict[str, Any]]) -> dict[str, Any]:
    mapping = _task_map(tasks)
    task = mapping.get(("boolean_algebra/not_gate.py", "not_gate"))
    if task is None:
        return {"present": False}
    synthesis_training = task["rows"][:8]
    synthesis_hidden = task["rows"][8:]
    repair_training = task["rows"][:10]
    repair_hidden = task["rows"][10:]
    syn_train_outputs = sorted({expected for _, expected in synthesis_training}, key=repr)
    rep_train_outputs = sorted({expected for _, expected in repair_training}, key=repr)
    syn_hidden_outputs = sorted({expected for _, expected in synthesis_hidden}, key=repr)
    rep_hidden_outputs = sorted({expected for _, expected in repair_hidden}, key=repr)
    return {
        "present": True,
        "synthesis_training_output_classes": syn_train_outputs,
        "synthesis_hidden_output_classes": syn_hidden_outputs,
        "repair_training_output_classes": rep_train_outputs,
        "repair_hidden_output_classes": rep_hidden_outputs,
        "positive_class_absent_from_synthesis_training": 1 not in syn_train_outputs and 1 in syn_hidden_outputs,
        "positive_class_absent_from_repair_training": 1 not in rep_train_outputs and 1 in rep_hidden_outputs,
        "policy": "DO_NOT_SPECIAL_CASE_HIDDEN_BRANCH",
    }


def run(manifest: Path, output: Path) -> int:
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    frozen = json.loads(FROZEN_EVIDENCE.read_text())
    if frozen["algorithms_head_sha"] != ALGORITHMS_V2_SHA:
        raise RuntimeError("FROZEN_SECOND_CYCLE_SOURCE_MISMATCH")
    started = time.time()

    predecessor = EvolvedSuccessorKernelV1(manifest, output / "predecessor-v1.sqlite")
    evolved = EvolvedSuccessorKernelV2(manifest, output / "evolved-v2.sqlite")
    try:
        with tempfile.TemporaryDirectory(prefix="yado-second-cycle-improvement-") as temp:
            root = Path(temp)
            pinned = checkout_exact(root, ALGORITHMS_URL, ALGORITHMS_V2_SHA, "frozen-v2-source")
            old_inventory = discover_real_code_tasks(pinned, limit=13)
            excluded = {(task["path"], task["function"]) for task in old_inventory}
            tasks = discover_extended_tasks(pinned, excluded, limit=8)

            predecessor_repairs = [repair_probe(predecessor, task, ALGORITHMS_V2_SHA) for task in tasks]
            predecessor_synthesis = [synthesis_probe(predecessor, task, ALGORITHMS_V2_SHA) for task in tasks]
            reproduced = {
                "repair": _score(predecessor_repairs),
                "synthesis": _score(predecessor_synthesis),
            }

            evolved_repairs = [repair_probe(evolved, task, ALGORITHMS_V2_SHA) for task in tasks]
            evolved_synthesis = [synthesis_probe(evolved, task, ALGORITHMS_V2_SHA) for task in tasks]
            evolved_scores = {
                "repair": _score(evolved_repairs),
                "synthesis": _score(evolved_synthesis),
            }

            identifiability = _not_gate_identifiability(tasks)

            # Reasoning preservation uses fresh clones of the two V2 repositories.
            reasoning_rows = _reasoning_probes(evolved, root)
            reasoning_pass = sum(
                row.get("status") == "VERIFIED" and row.get("independent_check")
                for row in reasoning_rows
            )

            # Fresh transfer is selected after candidate code is frozen.  It uses the
            # current public Algorithms head and excludes every frozen baseline task.
            latest = clone_latest(root, ALGORITHMS_URL, "fresh-v2-transfer")
            latest_sha = _git(latest, "rev-parse", "HEAD")
            latest_old = discover_real_code_tasks(latest, limit=13)
            latest_excluded = {(task["path"], task["function"]) for task in latest_old}
            latest_extended = discover_extended_tasks(latest, latest_excluded, limit=16)
            frozen_pairs = {(task["path"], task["function"]) for task in tasks}
            transfer_tasks = [
                task for task in latest_extended
                if (task["path"], task["function"]) not in frozen_pairs
            ][:6]
            transfer_rows = [synthesis_probe(evolved, task, latest_sha) for task in transfer_tasks]
            transfer_pass = _score(transfer_rows)

            predecessor_state = predecessor.verify_state()
            evolved_state = evolved.verify_state()
            evolved_snapshot = evolved.snapshot()
    finally:
        predecessor.close()
        evolved.close()

    predecessor_total = reproduced["repair"] + reproduced["synthesis"]
    evolved_total = evolved_scores["repair"] + evolved_scores["synthesis"]
    remaining = [
        row["task_id"] for row in evolved_repairs + evolved_synthesis
        if row["status"] != "PASS"
    ]
    expected_ambiguous = {
        "repair:boolean_algebra/not_gate.py:not_gate",
        "synthesis:boolean_algebra/not_gate.py:not_gate",
    }
    profiles_used = sorted({
        row.get("selected_profile") for row in evolved_synthesis
        if row.get("selected_profile")
    })

    strict_pass = (
        frozen["coding_pass_count"] == 9
        and reproduced == {"repair": 7, "synthesis": 2}
        and evolved_scores == {"repair": 7, "synthesis": 7}
        and predecessor_total == 9 and evolved_total == 14
        and set(remaining) == expected_ambiguous
        and identifiability.get("positive_class_absent_from_synthesis_training") is True
        and identifiability.get("positive_class_absent_from_repair_training") is True
        and reasoning_pass == len(REASONING_TARGETS_V2) * 3 == 6
        and len(transfer_rows) >= 2 and transfer_pass >= 1
        and predecessor_state["status"] == evolved_state["status"] == "PASS"
    )

    report = {
        "schema": "yado.second_cycle_deficit_driven_self_improvement.v2",
        "status": "PASS_SHADOW_SECOND_CYCLE_SELF_IMPROVEMENT_V2" if strict_pass else "WITHHOLD_SHADOW_SECOND_CYCLE_SELF_IMPROVEMENT_V2",
        "frozen_baseline_evidence": frozen,
        "pinned_source_sha": ALGORITHMS_V2_SHA,
        "predecessor_scores_reproduced": reproduced,
        "predecessor_total": predecessor_total,
        "evolved_scores": evolved_scores,
        "evolved_total": evolved_total,
        "improvement_delta": evolved_total - predecessor_total,
        "remaining_deficit_ids": remaining,
        "expected_irreducible_under_frozen_split": sorted(expected_ambiguous),
        "not_gate_identifiability": identifiability,
        "predecessor_repairs": predecessor_repairs,
        "predecessor_synthesis": predecessor_synthesis,
        "evolved_repairs": evolved_repairs,
        "evolved_synthesis": evolved_synthesis,
        "profiles_used": profiles_used,
        "reasoning_preservation": {
            "pass_count": reasoning_pass,
            "task_count": len(reasoning_rows),
            "results": reasoning_rows,
        },
        "fresh_transfer": {
            "latest_head_sha": latest_sha,
            "task_count": len(transfer_rows),
            "pass_count": transfer_pass,
            "results": transfer_rows,
            "selection_after_candidate_freeze": True,
            "frozen_baseline_pairs_excluded": True,
        },
        "predecessor_state": predecessor_state,
        "evolved_state": evolved_state,
        "evolved_snapshot": evolved_snapshot,
        "canonical_mutation": False,
        "g2_runtime_mutation": False,
        "automatic_main_mutation": False,
        "grammar_authorship": "HOST_BOUNDED",
        "concrete_program_selection": "KERNEL_TRAINING_ONLY",
        "hidden_holdout_special_casing": False,
        "general_intelligence_established": False,
        "consciousness_established": False,
        "elapsed_seconds": time.time() - started,
    }
    (output / "second-cycle-self-improvement-v2.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps({
        "status": report["status"],
        "before": predecessor_total,
        "after": evolved_total,
        "repair": f"{evolved_scores['repair']}/8",
        "synthesis": f"{evolved_scores['synthesis']}/8",
        "remaining": len(remaining),
        "reasoning": f"{reasoning_pass}/{len(reasoning_rows)}",
        "transfer": f"{transfer_pass}/{len(transfer_rows)}",
        "transfer_head": latest_sha,
    }, sort_keys=True), flush=True)
    return 0 if strict_pass else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    return run(args.manifest, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
