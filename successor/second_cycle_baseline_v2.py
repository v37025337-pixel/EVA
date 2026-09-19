"""Independent second-cycle baseline for the admitted programming candidate.

This runner is measurement-only.  It evaluates the already frozen
EvolvedSuccessorKernelV1 on real code shapes that were outside the first 13-task
inventory, and on fresh public Git repositories that were not used by the V1
real-world benchmark.  No grammar, canonical state, G2 runtime, or architecture
ledger is mutated by this module.
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import time
from typing import Any

from .evolved_kernel import EvolvedSuccessorKernelV1
from .kernel import equivalent
from .real_coding_intelligence_run import (
    ALGORITHMS_URL,
    INPUT_VALUES,
    _mutate_expr,
    _bounded_oracle,
    discover_real_code_tasks,
    run_repair,
)
from .real_coding_self_improvement_run import checkout_exact
from .real_world_run import (
    choose_python_source,
    clone_target,
    commit_relation,
    run_git,
    run_goal,
    sha256,
    truncated_real_prefix,
)

# This public source revision was observed after the V1 candidate was frozen/admitted.
ALGORITHMS_V2_SHA = "4379c6368c7c3decc25ef9cd1b33fba5b5234ab2"
REASONING_TARGETS_V2 = (
    ("flask", "https://github.com/pallets/flask.git"),
    ("httpx", "https://github.com/encode/httpx.git"),
)
SAFE_CALLS = {"abs": abs, "min": min, "max": max}
NOVEL_FEATURE_ORDER = (
    "arity3",
    "call",
    "mod",
    "pow",
    "bitwise",
    "ifexp",
    "compare",
    "boolop",
    "depth3plus",
    "wide_constant",
)


def _digest(value: Any) -> str:
    if isinstance(value, bytes):
        raw = value
    elif isinstance(value, str):
        raw = value.encode("utf-8")
    else:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _docless_body(fn: ast.FunctionDef) -> list[ast.stmt]:
    body = list(fn.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
        body = body[1:]
    return body


def _safe_extended_expr(expr: ast.AST, args: set[str]) -> bool:
    allowed = (
        ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.IfExp, ast.Name,
        ast.Load, ast.Constant, ast.Add, ast.Sub, ast.Mult, ast.FloorDiv, ast.Mod,
        ast.Pow, ast.BitAnd, ast.BitOr, ast.BitXor, ast.LShift, ast.RShift,
        ast.USub, ast.UAdd, ast.Not, ast.And, ast.Or, ast.Eq, ast.NotEq,
        ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Call,
    )
    for node in ast.walk(expr):
        if not isinstance(node, allowed):
            return False
        if isinstance(node, ast.Name) and node.id not in args and node.id not in SAFE_CALLS:
            return False
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in SAFE_CALLS or node.keywords:
                return False
            if node.func.id == "abs" and len(node.args) != 1:
                return False
            if node.func.id in {"min", "max"} and len(node.args) != 2:
                return False
        if isinstance(node, ast.Constant):
            if type(node.value) not in {int, bool}:
                return False
            if type(node.value) is int and abs(node.value) > 100_000:
                return False
    return True


def _source_for(args: list[str], expr: ast.AST) -> str:
    return f"def solve({', '.join(args)}):\n    return {ast.unparse(expr)}\n"


def _compile_extended(source: str):
    return _bounded_oracle(source, _safe_extended_expr, 3, SAFE_CALLS, 'EXTENDED_ORACLE')


def _sample_inputs(argc: int) -> list[tuple[int, ...]]:
    values = tuple(INPUT_VALUES)
    if argc == 1:
        return [(x,) for x in values]
    if argc == 2:
        rows = []
        for index, x in enumerate(values):
            y = values[(index * 7 + 5) % len(values)]
            rows.extend(((x, y), (y, x)))
        return rows
    rows = []
    for index, x in enumerate(values):
        y = values[(index * 5 + 3) % len(values)]
        z = values[(index * 11 + 7) % len(values)]
        rows.extend(((x, y, z), (z, x, y)))
    return rows


def _rows_for(target_source: str, damaged_source: str, argc: int) -> list[tuple[tuple[int, ...], Any]]:
    target = _compile_extended(target_source)
    damaged = _compile_extended(damaged_source)
    rows: list[tuple[tuple[int, ...], Any]] = []
    changed = 0
    seen = set()
    for args in _sample_inputs(argc):
        if args in seen:
            continue
        seen.add(args)
        try:
            expected = target(*args)
            before = damaged(*args)
        except (ArithmeticError, ValueError, OverflowError, TypeError):
            continue
        if type(expected) not in {int, bool}:
            continue
        if type(expected) is int and abs(expected) > 1_000_000:
            continue
        changed += int(not equivalent(before, expected))
        rows.append((args, expected))
    unique_outputs = {json.dumps(value) for _, value in rows}
    if len(rows) < 14 or len(unique_outputs) < 2 or changed < 4:
        return []
    rows.sort(key=lambda row: _digest(repr(row[0])))
    return rows[:24]


def _ast_depth(node: ast.AST) -> int:
    children = list(ast.iter_child_nodes(node))
    return 0 if not children else 1 + max(_ast_depth(child) for child in children)


def _features(expr: ast.AST, argc: int) -> list[str]:
    out = set()
    if argc == 3:
        out.add("arity3")
    depth = _ast_depth(expr)
    if depth >= 5:
        out.add("depth3plus")
    for node in ast.walk(expr):
        if isinstance(node, ast.Call):
            out.add("call")
        if isinstance(node, ast.Mod):
            out.add("mod")
        if isinstance(node, ast.Pow):
            out.add("pow")
        if isinstance(node, (ast.BitAnd, ast.BitOr, ast.BitXor, ast.LShift, ast.RShift)):
            out.add("bitwise")
        if isinstance(node, ast.IfExp):
            out.add("ifexp")
        if isinstance(node, ast.Compare):
            out.add("compare")
        if isinstance(node, ast.BoolOp):
            out.add("boolop")
        if isinstance(node, ast.Constant) and type(node.value) is int and node.value not in {-2, -1, 0, 1, 2}:
            out.add("wide_constant")
    return sorted(out)


def discover_extended_tasks(repo: Path, excluded_pairs: set[tuple[str, str]], limit: int = 8) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for path in sorted(repo.rglob("*.py")):
        if ".git" in path.parts or not path.is_file() or path.stat().st_size > 180_000:
            continue
        try:
            data = path.read_bytes()
            tree = ast.parse(data.decode("utf-8"))
        except (UnicodeDecodeError, SyntaxError, OSError):
            continue
        for fn in [node for node in tree.body if isinstance(node, ast.FunctionDef)]:
            if fn.decorator_list or fn.args.vararg or fn.args.kwarg or fn.args.kwonlyargs or fn.args.posonlyargs:
                continue
            args = [arg.arg for arg in fn.args.args]
            if not 1 <= len(args) <= 3 or len(set(args)) != len(args):
                continue
            rel = path.relative_to(repo).as_posix()
            if (rel, fn.name) in excluded_pairs:
                continue
            body = _docless_body(fn)
            if len(body) != 1 or not isinstance(body[0], ast.Return) or body[0].value is None:
                continue
            expr = body[0].value
            if not _safe_extended_expr(expr, set(args)):
                continue
            features = _features(expr, len(args))
            if not features:
                continue
            mutated, mutation = _mutate_expr(expr)
            if mutated is None or not _safe_extended_expr(mutated, set(args)):
                continue
            target_source = _source_for(args, expr)
            damaged_source = _source_for(args, mutated)
            try:
                rows = _rows_for(target_source, damaged_source, len(args))
            except Exception:
                continue
            if not rows:
                continue
            candidates.append({
                "path": rel,
                "function": fn.name,
                "args": args,
                "source_sha256": _digest(data),
                "target_expression_sha256": _digest(ast.dump(expr)),
                "damaged_source": damaged_source,
                "mutation": mutation,
                "rows": rows,
                "features": features,
                "selection_key": _digest(f"{rel}:{fn.name}"),
            })

    candidates.sort(key=lambda row: row["selection_key"])
    selected: list[dict[str, Any]] = []
    used = set()
    for feature in NOVEL_FEATURE_ORDER:
        for task in candidates:
            key = (task["path"], task["function"])
            if key in used or feature not in task["features"]:
                continue
            selected.append(task)
            used.add(key)
            break
        if len(selected) >= limit:
            break
    if len(selected) < limit:
        for task in candidates:
            key = (task["path"], task["function"])
            if key in used:
                continue
            selected.append(task)
            used.add(key)
            if len(selected) >= limit:
                break
    if len(selected) < 6:
        raise RuntimeError(f"INSUFFICIENT_EXTENDED_REAL_CODE_TASKS:{len(selected)}<6")
    return selected[:limit]


def _repair_probe(kernel: EvolvedSuccessorKernelV1, task: dict[str, Any]) -> dict[str, Any]:
    try:
        row = run_repair(kernel, task, ALGORITHMS_V2_SHA)
    except Exception as exc:
        return {
            "task_id": f"repair:{task['path']}:{task['function']}",
            "family": "SECOND_CYCLE_REAL_CODE_REPAIR",
            "status": "DEFICIT",
            "failure_reason": f"{type(exc).__name__}:{exc}",
            "features": task["features"],
        }
    row = copy.deepcopy(row)
    row["family"] = "SECOND_CYCLE_REAL_CODE_REPAIR"
    row["features"] = task["features"]
    return row


def _synthesis_probe(kernel: EvolvedSuccessorKernelV1, task: dict[str, Any], training_count: int = 8) -> dict[str, Any]:
    rows = task["rows"]
    training = [
        {"input": dict(zip(task["args"], args)), "expected": expected}
        for args, expected in rows[:training_count]
    ]
    hidden = rows[training_count:]
    candidate = None
    event_status = "NOT_RUN"
    failure_reason = None
    try:
        event = kernel.execute({
            "kind": "program_synthesis",
            "payload": {"training": training},
            "history_query": "second-cycle fresh real code generalization",
        })
        event_status = event.get("status", "UNKNOWN")
        result = event.get("result") or {}
        candidate = result if result.get("source") else None
    except Exception as exc:
        result = {}
        failure_reason = f"{type(exc).__name__}:{exc}"

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
        "features": task["features"],
        "candidate_source_sha256_frozen_before_holdout": frozen_digest,
        "holdout_passed": sum(checks),
        "holdout_total": len(hidden),
        "failure_reason": None if passed else (failure_reason or result.get("reason", "NO_GENERALIZING_SOURCE")),
        "training_labels_only_for_selection": True,
        "holdout_labels_consumed_during_selection": False,
        "provenance": {
            "repository": ALGORITHMS_URL,
            "head_sha": ALGORITHMS_V2_SHA,
            "path": task["path"],
            "function": task["function"],
            "source_sha256": task["source_sha256"],
            "target_expression_sha256": task["target_expression_sha256"],
        },
    }


def _reasoning_probes(kernel: EvolvedSuccessorKernelV1, root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name, url in REASONING_TARGETS_V2:
        repo = clone_target(root, name, url)
        head = run_git(repo, "rev-parse", "HEAD")
        relation = commit_relation(repo)
        rows.append(run_goal(kernel, f"{name}:commit-ancestry-v2", relation, {
            "repository": url,
            "head_sha": head,
            "commit_edge_count": len(relation["relation"]),
            "source_set": "SECOND_CYCLE_FRESH_REPOSITORY",
        }))
        path, data, events = choose_python_source(repo)
        rel = path.relative_to(repo).as_posix()
        provenance = {
            "repository": url,
            "head_sha": head,
            "path": rel,
            "source_sha256": sha256(data),
            "full_event_count": len(events),
            "source_set": "SECOND_CYCLE_FRESH_REPOSITORY",
        }
        rows.append(run_goal(kernel, f"{name}:source-nesting-full-v2",
                             {"domain": "events", "events": events},
                             {**provenance, "derived_view": "complete token stream"}))
        prefix = truncated_real_prefix(events)
        rows.append(run_goal(kernel, f"{name}:source-nesting-prefix-v2",
                             {"domain": "events", "events": prefix},
                             {**provenance, "derived_view": "real token-stream prefix",
                              "prefix_event_count": len(prefix)}))
    return rows


def run(manifest: Path, output: Path) -> int:
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    started = time.time()
    kernel = EvolvedSuccessorKernelV1(manifest, output / "second-cycle.sqlite")
    try:
        with tempfile.TemporaryDirectory(prefix="yado-second-cycle-v2-") as temp:
            root = Path(temp)
            algorithms = checkout_exact(root, ALGORITHMS_URL, ALGORITHMS_V2_SHA, "algorithms-v2")
            old_inventory = discover_real_code_tasks(algorithms, limit=13)
            excluded = {(task["path"], task["function"]) for task in old_inventory}
            coding_tasks = discover_extended_tasks(algorithms, excluded, limit=8)
            repair_rows = [_repair_probe(kernel, task) for task in coding_tasks]
            synthesis_rows = [_synthesis_probe(kernel, task) for task in coding_tasks]
            reasoning_rows = _reasoning_probes(kernel, root)
            verification = kernel.verify_state()
            snapshot = kernel.snapshot()
    finally:
        kernel.close()

    all_rows = repair_rows + synthesis_rows + reasoning_rows
    coding_pass = sum(row["status"] == "PASS" for row in repair_rows + synthesis_rows)
    reasoning_pass = sum(row.get("status") == "VERIFIED" and row.get("independent_check") for row in reasoning_rows)
    deficit_ids = [row.get("task_id", row.get("name")) for row in repair_rows + synthesis_rows if row["status"] != "PASS"]
    deficit_ids.extend(row.get("name") for row in reasoning_rows if not (row.get("status") == "VERIFIED" and row.get("independent_check")))

    report = {
        "schema": "yado.second_cycle_independent_baseline.v2",
        "status": "MEASURED_SECOND_CYCLE_BASELINE_V2",
        "candidate_under_test": "YADO_SUCCESSOR_DEFICIT_DRIVEN_PROGRAMMING_V1",
        "algorithms_repository": ALGORITHMS_URL,
        "algorithms_head_sha": ALGORITHMS_V2_SHA,
        "first_cycle_inventory_excluded": len(excluded),
        "coding_task_count": len(coding_tasks),
        "coding_probe_count": len(repair_rows) + len(synthesis_rows),
        "coding_pass_count": coding_pass,
        "reasoning_probe_count": len(reasoning_rows),
        "reasoning_pass_count": reasoning_pass,
        "deficit_count": len(deficit_ids),
        "deficit_ids": deficit_ids,
        "selected_real_code_tasks": [
            {
                "path": task["path"],
                "function": task["function"],
                "args": task["args"],
                "features": task["features"],
                "source_sha256": task["source_sha256"],
                "target_expression_sha256": task["target_expression_sha256"],
            }
            for task in coding_tasks
        ],
        "repair_results": repair_rows,
        "synthesis_results": synthesis_rows,
        "reasoning_results": reasoning_rows,
        "state_verification": verification,
        "kernel_snapshot": snapshot,
        "baseline_only": True,
        "self_improvement_applied": False,
        "canonical_mutation": False,
        "g2_runtime_mutation": False,
        "architecture_ledger_mutation": False,
        "automatic_main_mutation": False,
        "answers_supplied_to_kernel": False,
        "holdout_labels_supplied_during_selection": False,
        "general_intelligence_established": False,
        "consciousness_established": False,
        "elapsed_seconds": time.time() - started,
    }
    (output / "second-cycle-baseline-v2.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({
        "status": report["status"],
        "coding": f"{coding_pass}/{report['coding_probe_count']}",
        "reasoning": f"{reasoning_pass}/{report['reasoning_probe_count']}",
        "deficits": report["deficit_count"],
        "algorithms_head": ALGORITHMS_V2_SHA,
    }, sort_keys=True), flush=True)

    infrastructure_ok = (
        len(coding_tasks) >= 6
        and len(reasoning_rows) == len(REASONING_TARGETS_V2) * 3
        and verification.get("status") == "PASS"
    )
    return 0 if infrastructure_ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    return run(args.manifest, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
