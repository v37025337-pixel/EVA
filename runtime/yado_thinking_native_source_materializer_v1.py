#!/usr/bin/env python3
"""Bounded native AST materialization arm for YADO THINKING repair policies."""
from __future__ import annotations
import argparse, ast, hashlib, importlib.util, json, py_compile
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Sequence

SCHEMA = "yado.thinking_native_source_materializer.v1"
TARGET_DEFICIT = "THINKING_BOUNDARY_REASONING"
ALLOWED_FEATURES = ("forward_chain", "contradiction_guard", "representation_normalization")
CRITICAL_FAMILIES = ("multi_hop", "contradiction", "representation")


def stable_digest(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _parse_body(source: str) -> List[ast.stmt]:
    return ast.parse(source).body


def build_candidate_ast(features: Sequence[str]) -> ast.Module:
    chosen = tuple(sorted(set(features)))
    unknown = sorted(set(chosen) - set(ALLOWED_FEATURES))
    if unknown:
        raise ValueError(f"unsupported policy features: {unknown}")

    body: List[ast.stmt] = []
    body += _parse_body("import re\n")
    body += _parse_body(f"POLICY_FEATURES = {chosen!r}\n")
    body += _parse_body(
        "def normalize_surface(value):\n"
        "    return re.sub(r'[^a-z0-9]+', '', str(value).lower())\n"
    )

    if "representation_normalization" in chosen:
        body += _parse_body(
            "def canonicalize(value, aliases):\n"
            "    lookup = {}\n"
            "    for surface, canonical in aliases:\n"
            "        lookup[normalize_surface(surface)] = canonical\n"
            "        lookup[normalize_surface(canonical)] = canonical\n"
            "    return lookup.get(normalize_surface(value), normalize_surface(value))\n"
        )
    else:
        body += _parse_body(
            "def canonicalize(value, aliases):\n"
            "    return value\n"
        )

    body += _parse_body(
        "def canon_edges(items, aliases):\n"
        "    return {(canonicalize(a, aliases), canonicalize(b, aliases)) for a, b in items}\n"
    )

    if "forward_chain" in chosen:
        body += _parse_body(
            "def reachable(edges, src, dst):\n"
            "    if (src, dst) in edges:\n"
            "        return True\n"
            "    graph = {}\n"
            "    for a, b in edges:\n"
            "        graph.setdefault(a, set()).add(b)\n"
            "    seen, frontier = {src}, [src]\n"
            "    while frontier:\n"
            "        current = frontier.pop(0)\n"
            "        for nxt in sorted(graph.get(current, ())):\n"
            "            if nxt == dst:\n"
            "                return True\n"
            "            if nxt not in seen:\n"
            "                seen.add(nxt)\n"
            "                frontier.append(nxt)\n"
            "    return False\n"
        )
    else:
        body += _parse_body(
            "def reachable(edges, src, dst):\n"
            "    return (src, dst) in edges\n"
        )

    reason_lines = [
        "def reason(task):",
        "    aliases = tuple(tuple(x) for x in task.get('aliases', ()))",
        "    positive = canon_edges(tuple(tuple(x) for x in task.get('positive_edges', ())), aliases)",
        "    negative = canon_edges(tuple(tuple(x) for x in task.get('negative_edges', ())), aliases)",
        "    query = task.get('query', ('', ''))",
        "    src, dst = canonicalize(query[0], aliases), canonicalize(query[1], aliases)",
        "    support = reachable(positive, src, dst)",
    ]
    if "contradiction_guard" in chosen:
        reason_lines += [
            "    counter = (src, dst) in negative",
            "    if support and counter:",
            "        return 'CONFLICT'",
            "    if counter:",
            "        return 'CONTRADICTED'",
        ]
    reason_lines += [
        "    return 'SUPPORTED' if support else 'UNSUPPORTED'",
        "",
    ]
    body += _parse_body("\n".join(reason_lines))
    module = ast.Module(body=body, type_ignores=[])
    ast.fix_missing_locations(module)
    return module


def materialize_source(features: Sequence[str]) -> str:
    module = build_candidate_ast(features)
    source = ast.unparse(module).rstrip() + "\n"
    compile(source, "<yado-native-thinking-candidate>", "exec")
    return source


def validate_generated_ast(source: str) -> Dict[str, Any]:
    tree = ast.parse(source)
    forbidden_calls = {"eval", "exec", "compile", "open", "__import__", "input"}
    imports: List[str] = []
    bad_calls: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in forbidden_calls:
            bad_calls.append(node.func.id)
    allowed_imports = imports == ["re"]
    safe = allowed_imports and not bad_calls
    return {"safe": safe, "imports": imports, "forbidden_calls": bad_calls, "allowed_imports_only": allowed_imports}


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("yado_native_thinking_candidate", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to create import spec")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def task_payload(task: Any) -> Dict[str, Any]:
    return {
        "positive_edges": [list(x) for x in task.positive_edges],
        "negative_edges": [list(x) for x in task.negative_edges],
        "aliases": [list(x) for x in task.aliases],
        "query": list(task.query),
    }


def evaluate_module(tasks: Sequence[Any], module: Any) -> Dict[str, Any]:
    by: Dict[str, List[int]] = defaultdict(list)
    failures: List[Dict[str, Any]] = []
    correct = 0
    for task in tasks:
        pred = module.reason(task_payload(task))
        ok = pred == task.expected
        correct += int(ok)
        by[task.family].append(int(ok))
        if not ok:
            failures.append({"task_id": task.task_id, "family": task.family, "domain": task.domain, "expected": task.expected, "predicted": pred})
    family = {k: round(sum(v) / len(v), 6) for k, v in sorted(by.items())}
    return {"score": round(correct / len(tasks), 6), "correct": correct, "total": len(tasks), "family_accuracy": family, "failure_count": len(failures), "failure_examples": failures[:12]}


def run(repair: Dict[str, Any], out_source: Path, fresh_seed: int, per_family: int) -> Dict[str, Any]:
    from yado_thinking_boundary_adaptive_repair_v1 import generate_suite

    status = str(repair.get("status", ""))
    candidate = repair.get("candidate", {})
    features = tuple(candidate.get("features", ()))
    input_gate = status == "PASS_SHADOW_THINKING_BOUNDARY_ADAPTIVE_REPAIR_V1" and candidate.get("target_deficit") == TARGET_DEFICIT
    if not input_gate:
        raise RuntimeError("adaptive repair evidence is not admissible")
    unknown = sorted(set(features) - set(ALLOWED_FEATURES))
    if unknown:
        raise RuntimeError(f"repair selected unsupported features: {unknown}")

    baseline_source = materialize_source(())
    candidate_source = materialize_source(features)
    source_changed = baseline_source != candidate_source
    source_sha = sha256_text(candidate_source)
    baseline_sha = sha256_text(baseline_source)
    ast_gate = validate_generated_ast(candidate_source)

    out_source.parent.mkdir(parents=True, exist_ok=True)
    out_source.write_text(candidate_source, encoding="utf-8")
    py_compile.compile(str(out_source), doraise=True)
    module = load_module(out_source)
    if tuple(module.POLICY_FEATURES) != tuple(sorted(features)):
        raise RuntimeError("materialized policy features do not match repair evidence")

    baseline_path = out_source.with_name(out_source.stem + "_baseline.py")
    baseline_path.write_text(baseline_source, encoding="utf-8")
    py_compile.compile(str(baseline_path), doraise=True)
    baseline_module = load_module(baseline_path)

    tasks = generate_suite(fresh_seed, "native_source_fresh", per_family)
    baseline = evaluate_module(tasks, baseline_module)
    materialized = evaluate_module(tasks, module)
    gain = round(materialized["score"] - baseline["score"], 6)
    no_regression = all(float(materialized["family_accuracy"].get(f, 0.0)) + 1e-12 >= float(baseline["family_accuracy"].get(f, 0.0)) for f in CRITICAL_FAMILIES)
    floor_pass = all(float(materialized["family_accuracy"].get(f, 0.0)) >= 0.80 for f in CRITICAL_FAMILIES)
    execution_gate = source_changed and ast_gate["safe"] and materialized["score"] >= 0.85 and gain >= 0.20 and no_regression and floor_pass
    passed = input_gate and execution_gate

    result: Dict[str, Any] = {
        "schema": SCHEMA,
        "status": "PASS_SHADOW_NATIVE_THINKING_SOURCE_MATERIALIZATION_V1" if passed else "WITHHOLD_NATIVE_THINKING_SOURCE_MATERIALIZATION_V1",
        "target_deficit": TARGET_DEFICIT,
        "source_origin": "YADO_BOUNDED_NATIVE_AST_COMPOSITION",
        "external_llm_candidate_used": False,
        "canonical_direct_write": False,
        "adaptive_repair_evidence_digest": repair.get("evidence_digest"),
        "policy": {"features": sorted(features), "policy_digest": candidate.get("policy_digest")},
        "native_source": {
            "native_source_candidate_count": 1,
            "changed_native_source_candidate_count": 1 if source_changed else 0,
            "candidate_source_sha256": source_sha,
            "baseline_source_sha256": baseline_sha,
            "candidate_path": str(out_source),
            "compile_status": "PASS",
            "import_status": "PASS",
            "ast_safety": ast_gate
        },
        "fresh_execution": {
            "seed": fresh_seed,
            "per_family": per_family,
            "task_count": len(tasks),
            "suite_digest": stable_digest([t.__dict__ for t in tasks]),
            "baseline": baseline,
            "materialized_candidate": materialized,
            "absolute_gain": gain,
            "no_critical_regression": no_regression,
            "critical_family_floor_pass": floor_pass
        },
        "gates": {"input_gate": input_gate, "execution_gate": execution_gate, "required_score": 0.85, "required_gain": 0.20, "required_critical_family_floor": 0.80},
        "claim_boundary": {
            "native_source_materialization_proven": passed,
            "open_ended_source_invention_proven": False,
            "general_intelligence_claimed": False,
            "phenomenal_consciousness_claimed": False,
            "interpretation": "This proves bounded endogenous source materialization from a measured repair policy; it does not prove unrestricted code invention, general intelligence, or subjective consciousness."
        },
        "admission_route": ["adaptive_repair", "native_ast_materialization", "compile_import", "fresh_execution", "full_kernel_audit", "complete_regression", "explicit_main_admission"]
    }
    result["evidence_digest"] = stable_digest(result)
    return result


def self_test(tmp_dir: Path) -> None:
    full = materialize_source(ALLOWED_FEATURES)
    empty = materialize_source(())
    assert full != empty
    safety = validate_generated_ast(full)
    assert safety["safe"] is True, safety
    p = tmp_dir / "candidate.py"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(full, encoding="utf-8")
    py_compile.compile(str(p), doraise=True)
    mod = load_module(p)
    direct = {"positive_edges": [["a", "b"]], "negative_edges": [], "aliases": [], "query": ["a", "b"]}
    multi = {"positive_edges": [["a", "b"], ["b", "c"]], "negative_edges": [], "aliases": [], "query": ["a", "c"]}
    conflict = {"positive_edges": [["a", "b"], ["b", "c"]], "negative_edges": [["a", "c"]], "aliases": [], "query": ["a", "c"]}
    repr_case = {"positive_edges": [["Node-A", "node b"], ["node b", "[node_c]"]], "negative_edges": [], "aliases": [["Node-A", "a"], ["node b", "b"], ["[node_c]", "c"]], "query": ["a", "c"]}
    assert mod.reason(direct) == "SUPPORTED"
    assert mod.reason(multi) == "SUPPORTED"
    assert mod.reason(conflict) == "CONFLICT"
    assert mod.reason(repr_case) == "SUPPORTED"
    print("PASS_NATIVE_THINKING_SOURCE_MATERIALIZER_SELF_TEST")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repair-evidence")
    p.add_argument("--candidate-out", default="artifacts/generated/yado_thinking_boundary_policy_candidate_v1.py")
    p.add_argument("--out", default="artifacts/yado-thinking-native-source-materializer-v1.json")
    p.add_argument("--fresh-seed", type=int, default=20260914)
    p.add_argument("--per-family", type=int, default=24)
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args()
    if args.self_test:
        self_test(Path("artifacts/self-test-native-materializer"))
        return 0
    if not args.repair_evidence:
        raise SystemExit("--repair-evidence is required unless --self-test is used")
    repair = json.loads(Path(args.repair_evidence).read_text(encoding="utf-8"))
    result = run(repair, Path(args.candidate_out), args.fresh_seed, args.per_family)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "candidate_source_sha256": result["native_source"]["candidate_source_sha256"],
        "native_source_candidate_count": result["native_source"]["native_source_candidate_count"],
        "changed_native_source_candidate_count": result["native_source"]["changed_native_source_candidate_count"],
        "fresh_baseline": result["fresh_execution"]["baseline"]["score"],
        "fresh_candidate": result["fresh_execution"]["materialized_candidate"]["score"],
        "fresh_gain": result["fresh_execution"]["absolute_gain"],
        "evidence_digest": result["evidence_digest"]
    }, indent=2, sort_keys=True))
    return 0 if result["status"].startswith("PASS_") else 2

if __name__ == "__main__":
    raise SystemExit(main())
