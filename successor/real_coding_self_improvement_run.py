"""Prove a bounded programming improvement against the immutable real-data baseline.

The baseline commit and external source revision are pinned before this experiment.
The predecessor kernel is rerun on the exact same real code to reproduce the measured
7/8 repair and 0/4 source-synthesis scores.  The evolved candidate then receives the
same TRAINING partitions; candidate programs are frozen before hidden holdout labels
are checked.  A later block samples additional real functions for transfer evidence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import time
from typing import Any

from .evolved_kernel import EvolvedSuccessorKernelV1
from .kernel import SuccessorKernel, equivalent
from .real_coding_intelligence_run import (
    ALGORITHMS_URL,
    discover_real_code_tasks,
    run_repair,
    run_source_synthesis,
)

BASELINE_EVIDENCE = Path(__file__).with_name("evidence") / "real_coding_intelligence_baseline_v1.json"


def _git(cwd: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def checkout_exact(root: Path, url: str, sha: str, name: str) -> Path:
    target = root / name
    target.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=target, check=True)
    subprocess.run(["git", "remote", "add", "origin", url], cwd=target, check=True)
    subprocess.run(["git", "fetch", "--depth", "1", "--quiet", "origin", sha],
                   cwd=target, check=True, timeout=240)
    subprocess.run(["git", "checkout", "--detach", "--quiet", "FETCH_HEAD"],
                   cwd=target, check=True)
    actual = _git(target, "rev-parse", "HEAD")
    if actual != sha:
        raise RuntimeError(f"PINNED_SOURCE_SHA_MISMATCH:{actual}:{sha}")
    return target


def clone_latest(root: Path, url: str, name: str) -> Path:
    target = root / name
    subprocess.run(["git", "clone", "--depth", "1", "--no-tags", "--quiet", url, str(target)],
                   check=True, timeout=240)
    return target


def _labelled(task: dict[str, Any], row) -> dict[str, Any]:
    args, expected = row
    return {"input": dict(zip(task["args"], args)), "expected": expected}


def evolved_synthesis(kernel: EvolvedSuccessorKernelV1, task: dict[str, Any], *, training_count: int = 7) -> dict[str, Any]:
    rows = task["rows"]
    if len(rows) <= training_count:
        raise ValueError("INSUFFICIENT_SYNTHESIS_HOLDOUT")
    training = [_labelled(task, row) for row in rows[:training_count]]
    hidden = rows[training_count:]
    event = kernel.execute({
        "kind": "program_synthesis",
        "payload": {"training": training},
        "history_query": "measured real coding deficit arithmetic source synthesis",
    })
    result = event.get("result") or {}
    candidate = result if result.get("source") else None
    candidate_digest_before_holdout = result.get("source_sha256") if candidate else None
    checks = []
    if candidate:
        inputs = [dict(zip(task["args"], args)) for args, _ in hidden]
        try:
            predictions = kernel.execute_synthesized(candidate, inputs)
            checks = [equivalent(got, expected) for got, (_, expected) in zip(predictions, hidden)]
        except Exception:
            checks = [False] * len(hidden)
    passed = bool(candidate and checks and all(checks))
    return {
        "task_id": f"synthesis:{task['path']}:{task['function']}",
        "status": "PASS" if passed else "DEFICIT",
        "kernel_event_status": event["status"],
        "selected_profile": (result.get("selected") or {}).get("profile"),
        "expression_digest": (result.get("selected") or {}).get("expression_digest"),
        "profile_attempts": result.get("profile_attempts", []),
        "candidate_source_sha256_frozen_before_holdout": candidate_digest_before_holdout,
        "holdout_passed": sum(checks),
        "holdout_total": len(hidden),
        "training_labels_only_for_selection": True,
        "holdout_labels_consumed_during_selection": False,
        "provenance": {
            "path": task["path"],
            "function": task["function"],
            "source_sha256": task["source_sha256"],
            "target_expression_sha256": task["target_expression_sha256"],
        },
    }


def _repair_rows(kernel, tasks, head):
    return [run_repair(kernel, task, head) for task in tasks]


def _baseline_synthesis_rows(kernel, tasks, head):
    return [run_source_synthesis(kernel, task, head) for task in tasks]


def _score(rows):
    return sum(row["status"] == "PASS" for row in rows)


def run(manifest: Path, output: Path) -> int:
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    evidence = json.loads(BASELINE_EVIDENCE.read_text())
    pinned_sha = evidence["algorithms_head_sha"]
    started = time.time()

    predecessor = SuccessorKernel(manifest, output / "predecessor.sqlite")
    evolved = EvolvedSuccessorKernelV1(manifest, output / "evolved.sqlite")
    try:
        with tempfile.TemporaryDirectory(prefix="yado-self-improvement-") as temp:
            root = Path(temp)
            pinned = checkout_exact(root, ALGORITHMS_URL, pinned_sha, "baseline-source")
            pinned_tasks = discover_real_code_tasks(pinned, limit=8)
            task_ids = [f"{t['path']}:{t['function']}" for t in pinned_tasks]

            predecessor_repairs = _repair_rows(predecessor, pinned_tasks, pinned_sha)
            predecessor_synthesis = _baseline_synthesis_rows(predecessor, pinned_tasks[:4], pinned_sha)
            reproduced = {
                "repair": _score(predecessor_repairs),
                "synthesis": _score(predecessor_synthesis),
            }
            if reproduced != {"repair": 7, "synthesis": 0}:
                raise RuntimeError(f"IMMUTABLE_BASELINE_DID_NOT_REPRODUCE:{reproduced}")

            evolved_repairs = _repair_rows(evolved, pinned_tasks, pinned_sha)
            evolved_synthesis_rows = [evolved_synthesis(evolved, task) for task in pinned_tasks[:4]]
            evolved_scores = {
                "repair": _score(evolved_repairs),
                "synthesis": _score(evolved_synthesis_rows),
            }

            # Blind transfer is selected after the improvement code and baseline task set are frozen.
            latest = clone_latest(root, ALGORITHMS_URL, "fresh-transfer")
            latest_sha = _git(latest, "rev-parse", "HEAD")
            latest_tasks = discover_real_code_tasks(latest, limit=16)
            baseline_pairs = {(t["path"], t["function"]) for t in pinned_tasks}
            transfer_tasks = [t for t in latest_tasks if (t["path"], t["function"]) not in baseline_pairs][:6]
            transfer_rows = [evolved_synthesis(evolved, task) for task in transfer_tasks]

            predecessor_state = predecessor.verify_state()
            evolved_state = evolved.verify_state()
            evolved_snapshot = evolved.snapshot()
    finally:
        predecessor.close()
        evolved.close()

    repair_fixed = evolved_scores["repair"] - reproduced["repair"]
    synthesis_fixed = evolved_scores["synthesis"] - reproduced["synthesis"]
    deficit_rows = [r for r in evolved_repairs + evolved_synthesis_rows if r["status"] != "PASS"]
    floor_div_required = any(
        row.get("selected_profile") == "ARITH_DEPTH2_FLOORDIV_V1"
        and any(a.get("profile") == "ARITH_DEPTH2_V1" and not a.get("matched")
                for a in row.get("profile_attempts", []))
        for row in evolved_synthesis_rows
    ) or any(
        (row.get("selected") or {}).get("profile") == "ARITH_DEPTH2_FLOORDIV_V1"
        for row in evolved_repairs
    )
    depth2_evidence = any(
        row.get("selected_profile") in {"ARITH_DEPTH2_V1", "ARITH_DEPTH2_FLOORDIV_V1"}
        and any(a.get("profile") == "ARITH_DEPTH1_V1" and not a.get("matched")
                for a in row.get("profile_attempts", []))
        for row in evolved_synthesis_rows
    )

    transfer_pass = _score(transfer_rows)
    strict_pass = (
        reproduced == {"repair": 7, "synthesis": 0}
        and evolved_scores == {"repair": 8, "synthesis": 4}
        and not deficit_rows
        and repair_fixed == 1 and synthesis_fixed == 4
        and predecessor_state["status"] == evolved_state["status"] == "PASS"
        and len(transfer_rows) >= 2 and transfer_pass >= 1
        and depth2_evidence and floor_div_required
    )
    report = {
        "schema": "yado.real_coding_deficit_driven_self_improvement.v1",
        "status": "PASS_SHADOW_REAL_CODING_SELF_IMPROVEMENT_V1" if strict_pass else "WITHHOLD_SHADOW_REAL_CODING_SELF_IMPROVEMENT_V1",
        "baseline_evidence": evidence,
        "pinned_source_sha": pinned_sha,
        "baseline_task_ids": task_ids,
        "predecessor_scores_reproduced": reproduced,
        "evolved_scores": evolved_scores,
        "improvement_delta": {"repair": repair_fixed, "synthesis": synthesis_fixed,
                              "closed_deficits": repair_fixed + synthesis_fixed},
        "predecessor_repairs": predecessor_repairs,
        "predecessor_synthesis": predecessor_synthesis,
        "evolved_repairs": evolved_repairs,
        "evolved_synthesis": evolved_synthesis_rows,
        "causal_grammar_evidence": {
            "depth2_needed_on_at_least_one_real_task": depth2_evidence,
            "floordiv_profile_needed_on_at_least_one_real_task": floor_div_required,
            "profile_selection_uses_training_only": True,
        },
        "fresh_transfer": {
            "latest_head_sha": latest_sha,
            "task_count": len(transfer_rows),
            "pass_count": transfer_pass,
            "results": transfer_rows,
            "selection_after_candidate_freeze": True,
        },
        "predecessor_state": predecessor_state,
        "evolved_state": evolved_state,
        "evolved_snapshot": evolved_snapshot,
        "canonical_mutation": False,
        "g2_runtime_mutation": False,
        "automatic_main_mutation": False,
        "grammar_authorship": "HOST_BOUNDED",
        "concrete_program_selection": "KERNEL_TRAINING_ONLY",
        "general_intelligence_established": False,
        "consciousness_established": False,
        "elapsed_seconds": time.time() - started,
    }
    (output / "self-improvement.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({
        "status": report["status"],
        "before": reproduced,
        "after": evolved_scores,
        "closed_deficits": repair_fixed + synthesis_fixed,
        "transfer": f"{transfer_pass}/{len(transfer_rows)}",
        "latest_transfer_head": latest_sha,
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
