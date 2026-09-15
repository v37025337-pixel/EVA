"""Measure YADO on fresh real code before allowing any self-improvement.

The benchmark deliberately separates measurement from mutation.  It clones public
repositories at run time, derives coding and reasoning tasks before observing YADO's
answers, independently checks every answer, and records failures as deficits.  Real
source is used for the coding targets; the injected defect is a deterministic
single-AST-node perturbation so that the original live source remains the hidden
oracle.  No canonical or architecture file is changed by this runner.
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import time
from typing import Any

from .cognitive import CognitiveLoop
from .kernel import SuccessorKernel, decode, equivalent
from .real_world_run import clone_target, commit_relation, run_git, run_goal

ALGORITHMS_URL = "https://github.com/TheAlgorithms/Python.git"
REASONING_TARGETS = (
    ("opentrashmail", "https://github.com/HaschekSolutions/opentrashmail.git"),
    ("requests", "https://github.com/psf/requests.git"),
    ("click", "https://github.com/pallets/click.git"),
)
INPUT_VALUES = (-13, -9, -7, -5, -3, -2, -1, 0, 1, 2, 3, 4, 5, 7, 9, 11, 13, 17)
MAX_CODE_TASKS = 8


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _docless_body(fn: ast.FunctionDef) -> list[ast.stmt]:
    body = list(fn.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
        body = body[1:]
    return body


def _safe_expr(expr: ast.AST, args: set[str]) -> bool:
    allowed = (
        ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.IfExp, ast.Name,
        ast.Load, ast.Constant, ast.Add, ast.Sub, ast.Mult, ast.FloorDiv, ast.Mod,
        ast.USub, ast.UAdd, ast.Not, ast.And, ast.Or, ast.Eq, ast.NotEq,
        ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    )
    for node in ast.walk(expr):
        if not isinstance(node, allowed):
            return False
        if isinstance(node, ast.Name) and node.id not in args:
            return False
        if isinstance(node, ast.Constant):
            if type(node.value) not in {int, bool}:
                return False
            if type(node.value) is int and abs(node.value) > 10_000:
                return False
    return True


def _mutate_expr(expr: ast.AST) -> tuple[ast.AST, str] | tuple[None, None]:
    out = copy.deepcopy(expr)
    for node in ast.walk(out):
        if isinstance(node, ast.BinOp):
            old = type(node.op).__name__
            replacement = {
                ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.Add,
                ast.FloorDiv: ast.Mult, ast.Mod: ast.Add,
            }.get(type(node.op))
            if replacement:
                node.op = replacement()
                ast.fix_missing_locations(out)
                return out, f"BINOP_{old}_TO_{replacement.__name__}"
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            old = type(node.ops[0]).__name__
            replacement = {
                ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.Lt: ast.Gt,
                ast.LtE: ast.GtE, ast.Gt: ast.Lt, ast.GtE: ast.LtE,
            }.get(type(node.ops[0]))
            if replacement:
                node.ops[0] = replacement()
                ast.fix_missing_locations(out)
                return out, f"COMPARE_{old}_TO_{replacement.__name__}"
        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                node.op = ast.Or(); ast.fix_missing_locations(out); return out, "BOOLOP_AND_TO_OR"
            if isinstance(node.op, ast.Or):
                node.op = ast.And(); ast.fix_missing_locations(out); return out, "BOOLOP_OR_TO_AND"
    for node in ast.walk(out):
        if isinstance(node, ast.Constant) and type(node.value) is int:
            node.value += 1
            ast.fix_missing_locations(out)
            return out, "INTEGER_CONSTANT_PLUS_ONE"
    return None, None


def _source_for(args: list[str], expr: ast.AST) -> str:
    return f"def solve({', '.join(args)}):\n    return {ast.unparse(expr)}\n"


def _compile_oracle(source: str):
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.Attribute, ast.Call, ast.Subscript,
                             ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp,
                             ast.Lambda, ast.Assign, ast.AugAssign, ast.While, ast.For)):
            raise ValueError("ORACLE_SOURCE_ESCAPED_SAFE_EXPRESSION_SUBSET")
    ns: dict[str, Any] = {"__builtins__": {}}
    exec(compile(tree, "<real-source-oracle>", "exec"), ns)
    return ns["solve"]


def _sample_inputs(argc: int) -> list[tuple[int, ...]]:
    if argc == 1:
        return [(x,) for x in INPUT_VALUES]
    pairs = []
    for i, x in enumerate(INPUT_VALUES):
        y = INPUT_VALUES[(i * 7 + 5) % len(INPUT_VALUES)]
        pairs.append((x, y))
        pairs.append((y, x))
    return pairs


def _rows_for(target_source: str, damaged_source: str, argc: int) -> list[tuple[tuple[int, ...], Any]]:
    target = _compile_oracle(target_source)
    damaged = _compile_oracle(damaged_source)
    rows = []
    changed = 0
    seen = set()
    for args in _sample_inputs(argc):
        if args in seen:
            continue
        seen.add(args)
        try:
            expected = target(*args)
            before = damaged(*args)
        except (ArithmeticError, ValueError, OverflowError):
            continue
        if type(expected) not in {int, bool}:
            continue
        if type(expected) is int and abs(expected) > 1_000_000:
            continue
        changed += int(not equivalent(before, expected))
        rows.append((args, expected))
    minimum_outputs = 2 if rows and all(type(value) is bool for _, value in rows) else 3
    if len(rows) < 14 or len({json.dumps(v) for _, v in rows}) < minimum_outputs or changed < 4:
        return []
    # Input order is fixed independently of YADO output.
    rows.sort(key=lambda row: hashlib.sha256(repr(row[0]).encode()).hexdigest())
    return rows[:18]


def discover_real_code_tasks(repo: Path, limit: int = MAX_CODE_TASKS) -> list[dict[str, Any]]:
    candidates = []
    for path in sorted(repo.rglob("*.py")):
        if ".git" in path.parts or not path.is_file() or path.stat().st_size > 180_000:
            continue
        try:
            data = path.read_bytes()
            tree = ast.parse(data.decode("utf-8"))
        except (UnicodeDecodeError, SyntaxError, OSError):
            continue
        for fn in [n for n in tree.body if isinstance(n, ast.FunctionDef)]:
            if fn.decorator_list or fn.args.vararg or fn.args.kwarg or fn.args.kwonlyargs or fn.args.posonlyargs:
                continue
            args = [a.arg for a in fn.args.args]
            if not 1 <= len(args) <= 2 or len(set(args)) != len(args):
                continue
            body = _docless_body(fn)
            if len(body) != 1 or not isinstance(body[0], ast.Return) or body[0].value is None:
                continue
            expr = body[0].value
            if not _safe_expr(expr, set(args)):
                continue
            mutated, mutation = _mutate_expr(expr)
            if mutated is None:
                continue
            target_source = _source_for(args, expr)
            damaged_source = _source_for(args, mutated)
            rows = _rows_for(target_source, damaged_source, len(args))
            if not rows:
                continue
            rel = path.relative_to(repo).as_posix()
            candidates.append({
                "sort_key": (rel, fn.name),
                "path": rel,
                "function": fn.name,
                "args": args,
                "source_sha256": sha256_bytes(data),
                "target_expression_sha256": hashlib.sha256(ast.dump(expr).encode()).hexdigest(),
                "damaged_source": damaged_source,
                "mutation": mutation,
                "rows": rows,
            })
    candidates.sort(key=lambda x: x["sort_key"])
    if len(candidates) < limit:
        raise RuntimeError(f"INSUFFICIENT_REAL_CODE_TASKS:{len(candidates)}<{limit}")
    return candidates[:limit]


def run_repair(kernel: SuccessorKernel, task: dict[str, Any], head: str) -> dict[str, Any]:
    rows = task["rows"]
    train, holdout = rows[:10], rows[10:]
    payload = {
        "source": task["damaged_source"],
        "function_name": "solve",
        "train_examples": [[list(args), expected] for args, expected in train],
        "max_candidates": 4000,
    }
    event = kernel.execute({"kind": "repair", "payload": payload,
                            "history_query": "real code program repair"})
    result = event.get("result") or {}
    source = result.get("source")
    checks = []
    if source:
        for args, expected in holdout:
            try:
                got = kernel.parent.execute_program_task(source, "solve", tuple(args))
                checks.append(equivalent(got, expected))
            except Exception:
                checks.append(False)
    passed = bool(source) and len(checks) == len(holdout) and all(checks)
    return {
        "task_id": f"repair:{task['path']}:{task['function']}",
        "family": "REAL_CODE_REPAIR",
        "status": "PASS" if passed else "DEFICIT",
        "kernel_event_status": event["status"],
        "repair_mode": result.get("repair_mode"),
        "search_nodes": result.get("search_nodes"),
        "holdout_passed": sum(checks),
        "holdout_total": len(holdout),
        "failure_reason": None if passed else result.get("reason", "HOLDOUT_MISMATCH_OR_NO_SOURCE"),
        "provenance": {
            "repository": ALGORITHMS_URL,
            "head_sha": head,
            "path": task["path"],
            "source_sha256": task["source_sha256"],
            "function": task["function"],
            "target_expression_sha256": task["target_expression_sha256"],
            "defect_origin": "DETERMINISTIC_SINGLE_AST_NODE_PERTURBATION_OF_REAL_SOURCE",
            "mutation": task["mutation"],
        },
        "oracle_source_supplied_to_kernel": False,
        "holdout_labels_supplied_to_kernel": False,
    }


def _finish_record(kernel: SuccessorKernel, goal_id: int) -> tuple[dict[str, Any] | None, list[str]]:
    finish = None
    strategies = []
    for row in kernel.db.execute("SELECT tick,body FROM events ORDER BY tick"):
        body = decode(row["body"])
        if body.get("goal_id") != goal_id:
            continue
        if body.get("kind") == "COG_DECIDE":
            strategies.append(body["choice"]["strategy"])
        if body.get("kind") == "COG_FINISH":
            finish = body
    return finish, strategies


def run_source_synthesis(kernel: SuccessorKernel, task: dict[str, Any], head: str) -> dict[str, Any]:
    from yado_active_native_learning_v1 import execute_source

    rows = task["rows"]
    if len(rows) < 14:
        raise RuntimeError("SOURCE_SYNTHESIS_ROWS")
    def labelled(row):
        args, expected = row
        return {"input": dict(zip(task["args"], args)), "expected": expected}
    training = [labelled(r) for r in rows[:7]]
    validation = [labelled(r) for r in rows[7:11]]
    query_rows = rows[11:13]
    queries = [{"input": dict(zip(task["args"], args))} for args, _ in query_rows]
    extra = rows[13:]
    spec = {"domain": "native_source", "training": training, "validation": validation, "queries": queries}
    loop = CognitiveLoop(kernel)
    goal_id = loop.open_goal(spec, budget=8, mode="full")
    loop.run(max_steps=80)
    finish, strategies = _finish_record(kernel, goal_id)
    result = (finish or {}).get("result") or {}
    candidate = result if isinstance(result, dict) and result.get("source") else None
    checks = []
    if candidate:
        check_rows = list(query_rows) + list(extra)
        inputs = [dict(zip(task["args"], args)) for args, _ in check_rows]
        try:
            outputs = execute_source(candidate, inputs)
            checks = [equivalent(got, expected) for got, (_, expected) in zip(outputs, check_rows)]
        except Exception:
            checks = [False] * len(check_rows)
    passed = bool(finish and finish.get("status") == "VALIDATED_ON_HOLDOUT" and checks and all(checks))
    return {
        "task_id": f"synthesis:{task['path']}:{task['function']}",
        "family": "REAL_CODE_BEHAVIOR_SYNTHESIS",
        "status": "PASS" if passed else "DEFICIT",
        "goal_id": goal_id,
        "finish_status": (finish or {}).get("status", "NO_FINISH"),
        "strategies": strategies,
        "independent_post_validation_passed": sum(checks),
        "independent_post_validation_total": len(checks),
        "candidate_source_sha256": result.get("source_sha256") if candidate else None,
        "grammar_stage": result.get("grammar_stage") if candidate else None,
        "provenance": {
            "repository": ALGORITHMS_URL,
            "head_sha": head,
            "path": task["path"],
            "source_sha256": task["source_sha256"],
            "function": task["function"],
            "target_expression_sha256": task["target_expression_sha256"],
        },
        "oracle_source_supplied_to_kernel": False,
        "independent_post_validation_labels_supplied_to_kernel": False,
    }


def run(manifest: Path, output: Path) -> int:
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    state = output / "kernel.sqlite"
    kernel = SuccessorKernel(manifest, state)
    started = time.time()
    results: list[dict[str, Any]] = []
    code_inventory: list[dict[str, Any]] = []
    repositories: list[dict[str, Any]] = []
    try:
        with tempfile.TemporaryDirectory(prefix="yado-real-code-training-") as temp:
            root = Path(temp)
            algorithms = root / "algorithms"
            subprocess.run(["git", "clone", "--depth", "1", "--no-tags", "--quiet", ALGORITHMS_URL, str(algorithms)],
                           check=True, timeout=240)
            algorithms_head = run_git(algorithms, "rev-parse", "HEAD")
            code_tasks = discover_real_code_tasks(algorithms)
            repositories.append({"repository": ALGORITHMS_URL, "head_sha": algorithms_head})
            code_inventory = [{k: v for k, v in task.items() if k not in {"rows", "damaged_source", "sort_key"}}
                              for task in code_tasks]

            # Programming baseline: eight repairs, then four independent behavior-synthesis goals.
            for task in code_tasks:
                results.append(run_repair(kernel, task, algorithms_head))
            for task in code_tasks[:4]:
                results.append(run_source_synthesis(kernel, task, algorithms_head))

            # Intellectual transfer: fresh commit ancestry from three unrelated live repositories.
            for name, url in REASONING_TARGETS:
                repo = clone_target(root, name, url)
                head = run_git(repo, "rev-parse", "HEAD")
                spec = commit_relation(repo)
                provenance = {
                    "repository": url,
                    "head_sha": head,
                    "collector": "fresh shallow git parent graph",
                    "edge_count": len(spec["relation"]),
                }
                row = run_goal(kernel, f"{name}:fresh-ancestry-intelligence", spec, provenance)
                results.append({
                    "task_id": f"logic:{name}:commit-ancestry",
                    "family": "REAL_RELATIONAL_REASONING",
                    "status": "PASS" if row["status"] == "VERIFIED" and row["independent_check"] else "DEFICIT",
                    "kernel_status": row["status"],
                    "independent_check": row["independent_check"],
                    "attempted": row["attempted"],
                    "spent": row["spent"],
                    "provenance": provenance,
                    "answer_supplied_to_kernel": False,
                })
                repositories.append({"repository": url, "head_sha": head})

        state_verification = kernel.verify_state()
        snapshot = kernel.cognitive_snapshot()
    finally:
        kernel.close()

    deficits = [{
        "task_id": row["task_id"],
        "family": row["family"],
        "reason": row.get("failure_reason") or row.get("finish_status") or row.get("kernel_status"),
        "provenance": row.get("provenance"),
    } for row in results if row["status"] != "PASS"]
    by_family: dict[str, dict[str, int]] = {}
    for row in results:
        fam = by_family.setdefault(row["family"], {"total": 0, "pass": 0, "deficit": 0})
        fam["total"] += 1
        fam["pass" if row["status"] == "PASS" else "deficit"] += 1

    report = {
        "schema": "yado.real_coding_intelligence_baseline.v1",
        "status": "PASS_REAL_CODING_INTELLIGENCE_BASELINE_CAPTURE_V1",
        "measurement_phase": "BASELINE_ONLY_NO_SELF_IMPROVEMENT",
        "repositories": repositories,
        "task_count": len(results),
        "pass_count": sum(r["status"] == "PASS" for r in results),
        "deficit_count": len(deficits),
        "family_summary": by_family,
        "results": results,
        "deficits": deficits,
        "code_task_inventory": code_inventory,
        "task_selection_policy": "DETERMINISTIC_SORTED_REAL_SOURCE_BEFORE_YADO_OUTCOMES",
        "coding_defect_policy": "ONE_DETERMINISTIC_AST_PERTURBATION_OF_LIVE_SOURCE; ORIGINAL_EXPRESSION_HIDDEN_FROM_YADO",
        "answers_supplied_to_kernel": False,
        "canonical_mutation": False,
        "architecture_mutation": False,
        "self_improvement_applied": False,
        "state_verification": state_verification,
        "cognitive_snapshot": snapshot,
        "elapsed_seconds": time.time() - started,
        "general_intelligence_established": False,
        "consciousness_established": False,
    }
    (output / "baseline.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({
        "status": report["status"],
        "tasks": report["task_count"],
        "passes": report["pass_count"],
        "deficits": report["deficit_count"],
        "families": report["family_summary"],
        "algorithm_head": algorithms_head,
    }, sort_keys=True), flush=True)
    # Performance deficits are data, not infrastructure failure.  The run fails only if
    # causal state integrity was lost or the benchmark itself could not be constructed.
    return 0 if state_verification["status"] == "PASS" and len(results) == 15 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    return run(args.manifest, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
