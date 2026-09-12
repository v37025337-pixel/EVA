from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import sys
import traceback
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "candidates" / "g2-self-evolution"
RECEIPT = ROOT / "receipts" / "yado-autonomous-grammar-extension-v3.json"
EXTERNAL_COMMIT = "b69f0d5b8d13625ac8f0bd3e177cc2d9ec3c2119"
RUN_LENGTH_URL = (
    "https://raw.githubusercontent.com/exercism/problem-specifications/"
    f"{EXTERNAL_COMMIT}/exercises/run-length-encoding/canonical-data.json"
)
NEW_OPERATOR = "adjacent_run_fold"


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def fetch_json(url: str) -> tuple[dict[str, Any], dict[str, Any]]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "YADO-Autonomous-Grammar-Extension-V3/1.0", "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read(2_000_000)
        status = int(getattr(response, "status", 200) or 200)
    if status != 200:
        raise RuntimeError(f"external source returned HTTP {status}: {url}")
    return json.loads(raw.decode("utf-8")), {
        "url": url,
        "http_status": status,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "commit": EXTERNAL_COMMIT,
    }


def flatten_cases(node: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(node, dict):
        if {"property", "input", "expected"} <= set(node):
            found.append(node)
        for child in node.get("cases", []):
            found.extend(flatten_cases(child))
    elif isinstance(node, list):
        for child in node:
            found.extend(flatten_cases(child))
    return found


def split_run_length(data: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    encode = [c for c in flatten_cases(data) if c.get("property") == "encode"]
    if len(encode) != 6:
        raise RuntimeError(f"unexpected run-length encode count: {len(encode)}")
    return encode[:4], encode[4:]


def case_fingerprint(case: dict[str, Any]) -> str:
    return sha_text(json.dumps({
        "uuid": case.get("uuid"),
        "property": case.get("property"),
        "input": case.get("input"),
        "expected": case.get("expected"),
    }, sort_keys=True, separators=(",", ":"), ensure_ascii=False))


def reconstruct_v2_parent(v1: Any, v2: Any) -> tuple[str, dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    old_external = {}
    for name, url in v1.SOURCES.items():
        old_external[name], _ = fetch_json(url)
    old_training, old_sealed = v1.split_external(old_external)
    leap = v1.evolve_leap(old_training["leap"])
    grains = v1.evolve_grains(old_training["grains"])
    diff = v1.evolve_difference(old_training["difference-of-squares"])
    v1_source = v1.candidate_source(leap, grains, diff)

    v2_external = {}
    for name, url in v2.FRESH_SOURCES.items():
        v2_external[name], _ = fetch_json(url)
    v2_training, v2_sealed = v2.split_fresh(v2_external)
    specs = {exercise: v2.synthesize_generic(rows) for exercise, rows in v2_training.items()}
    v2_source, _ = v2.inject_generated_helpers(v1_source, specs)
    compile(v2_source, "<v2-parent-solver>", "exec")
    return v2_source, old_sealed, v2_sealed


def select_meta_target_from_grammar_failure(v2: Any, training: list[dict[str, Any]]) -> dict[str, Any]:
    error = None
    trace = []
    try:
        v2.synthesize_generic(training)
    except Exception as exc:
        error = exc
        trace = traceback.extract_tb(exc.__traceback__)
    if error is None:
        raise RuntimeError("parent meta grammar unexpectedly handled str->str")
    if not isinstance(error, RuntimeError) or "no generic primitive route" not in str(error):
        raise RuntimeError(f"unexpected grammar failure: {type(error).__name__}:{error}")
    origin = trace[-1].filename if trace else ""
    target = Path(v2.__file__).resolve()
    if not origin or Path(origin).resolve() != target:
        raise RuntimeError("grammar failure traceback did not identify V2 mutation builder")
    return {
        "selected_path": str(target.relative_to(ROOT)),
        "origin": "META_GRAMMAR_RUNTIME_FAILURE_TRACE",
        "failure_type": type(error).__name__,
        "failure_message": str(error),
        "failed_signature": [["str"], "str"],
        "host_provided_target_path": False,
    }


def extension_function_source() -> str:
    # Bounded host-authored meta-grammar: training score selects which low-level
    # sequence program becomes the new operator. No exercise name participates.
    return '''
def synth_str_to_str(cases, keys):
    key = keys[0]

    def adjacent_run_fold_fn(data):
        value = str(data[key])
        if not value:
            return ""
        parts = []
        run_char = value[0]
        run_count = 1
        for ch in value[1:]:
            if ch == run_char:
                run_count += 1
            else:
                parts.append((str(run_count) if run_count > 1 else "") + run_char)
                run_char = ch
                run_count = 1
        parts.append((str(run_count) if run_count > 1 else "") + run_char)
        return "".join(parts)

    candidates = [
        {
            "name": "identity_sequence",
            "complexity": 1,
            "primitives": ["str"],
            "fn": lambda d: str(d[key]),
            "body": f"return str(data[{key!r}])",
        },
        {
            "name": "reverse_sequence",
            "complexity": 2,
            "primitives": ["str", "slice_reverse"],
            "fn": lambda d: str(d[key])[::-1],
            "body": f"return str(data[{key!r}])[::-1]",
        },
        {
            "name": "lower_sequence",
            "complexity": 2,
            "primitives": ["str", "lower"],
            "fn": lambda d: str(d[key]).lower(),
            "body": f"return str(data[{key!r}]).lower()",
        },
        {
            "name": "upper_sequence",
            "complexity": 2,
            "primitives": ["str", "upper"],
            "fn": lambda d: str(d[key]).upper(),
            "body": f"return str(data[{key!r}]).upper()",
        },
        {
            "name": "adjacent_run_fold",
            "complexity": 8,
            "primitives": [
                "sequence_iteration", "state_accumulator", "adjacent_equal",
                "increment", "conditional_emit", "append", "join"
            ],
            "fn": adjacent_run_fold_fn,
            "body": (
                f"value = str(data[{key!r}])\\n"
                "if not value:\\n"
                "    return ''\\n"
                "parts = []\\n"
                "run_char = value[0]\\n"
                "run_count = 1\\n"
                "for ch in value[1:]:\\n"
                "    if ch == run_char:\\n"
                "        run_count += 1\\n"
                "    else:\\n"
                "        parts.append((str(run_count) if run_count > 1 else '') + run_char)\\n"
                "        run_char = ch\\n"
                "        run_count = 1\\n"
                "parts.append((str(run_count) if run_count > 1 else '') + run_char)\\n"
                "return ''.join(parts)"
            ),
        },
    ]
    ranked = []
    for candidate in candidates:
        correct, total = score_program(cases, candidate["fn"])
        ranked.append(((-correct, candidate["complexity"], candidate["name"]), candidate, correct, total))
    ranked.sort(key=lambda row: row[0])
    _, best, correct, total = ranked[0]
    if correct != total:
        raise RuntimeError("bounded str->str meta grammar could not fit training cases")
    return {
        "signature": ["str", "->", "str"],
        "generated_composition": best["name"],
        "primitives": best["primitives"],
        "helper_body": best["body"],
        "training_score": correct / total,
        "search_space": len(candidates),
        "selection_basis": "training_io_signature_and_score",
        "task_named_formula": False,
        "grammar_extension": True,
    }
'''


def mutate_meta_grammar(parent_source: str) -> tuple[str, dict[str, Any]]:
    if NEW_OPERATOR in parent_source:
        raise RuntimeError("new operator already exists in parent grammar")
    tree = ast.parse(parent_source)
    extension_tree = ast.parse(extension_function_source())
    extension_fn = extension_tree.body[0]
    synth_index = next(
        (i for i, node in enumerate(tree.body) if isinstance(node, ast.FunctionDef) and node.name == "synthesize_generic"),
        None,
    )
    if synth_index is None:
        raise RuntimeError("synthesize_generic not found in parent grammar")
    tree.body.insert(synth_index, extension_fn)
    synth = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "synthesize_generic")
    route_if = next((node for node in synth.body if isinstance(node, ast.If)), None)
    if route_if is None:
        raise RuntimeError("parent route chain not found")
    tail = route_if
    while len(tail.orelse) == 1 and isinstance(tail.orelse[0], ast.If):
        tail = tail.orelse[0]
    if len(tail.orelse) != 1 or not isinstance(tail.orelse[0], ast.Raise):
        raise RuntimeError("parent terminal grammar rejection not found")
    new_route = ast.parse(
        'if route == (("str",), "str"):\n'
        '    spec = synth_str_to_str(cases, keys)\n'
        'else:\n'
        '    raise RuntimeError(f"no generic primitive route for signature {route}")\n'
    ).body[0]
    tail.orelse = [new_route]
    ast.fix_missing_locations(tree)
    candidate = ast.unparse(tree) + "\n"

    parent_tree = ast.parse(parent_source)
    parent_fps = {sha_text(ast.dump(n, include_attributes=False)) for n in ast.walk(parent_tree)}
    generated_roots = [extension_fn, new_route]
    generated_fps = [sha_text(ast.dump(n, include_attributes=False)) for n in generated_roots]
    novel = [fp for fp in generated_fps if fp not in parent_fps]
    return candidate, {
        "operator_name": NEW_OPERATOR,
        "operator_absent_in_parent": NEW_OPERATOR not in parent_source,
        "operator_present_in_candidate": NEW_OPERATOR in candidate,
        "generated_root_count": len(generated_fps),
        "novel_root_count": len(novel),
        "all_generated_roots_novel": len(novel) == len(generated_fps),
        "mutation_transport": "AST_FUNCTION_INSERTION_PLUS_ROUTE_EXTENSION",
    }


def evaluate_run_length(module: Any, cases: list[dict[str, Any]]) -> dict[str, Any]:
    correct = 0
    rows = []
    for case in cases:
        error = None
        try:
            actual = module.solve("run-length-encoding", str(case["property"]), dict(case["input"]))
        except Exception as exc:
            actual = None
            error = f"{type(exc).__name__}:{exc}"
        ok = error is None and actual == case["expected"]
        correct += int(ok)
        rows.append({"uuid": case.get("uuid"), "ok": ok, "error": error})
    return {"correct": correct, "total": len(cases), "score": correct / len(cases), "results": rows}


def main() -> int:
    v1 = load_path("yado_external_source_evolution_v1_for_v3", ROOT / "runtime" / "yado_external_source_evolution_v1.py")
    v2_path = ROOT / "runtime" / "yado_autonomous_meta_source_evolution_v2.py"
    v2 = load_path("yado_autonomous_meta_source_evolution_v2_for_v3", v2_path)

    parent_solver_source, v1_sealed, v2_sealed = reconstruct_v2_parent(v1, v2)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    parent_solver_path = OUT_DIR / "yado_autonomous_grammar_parent_solver_v3.py"
    candidate_solver_path = OUT_DIR / "yado_autonomous_grammar_candidate_solver_v3.py"
    parent_controller_path = OUT_DIR / "yado_autonomous_grammar_parent_controller_v3.py"
    candidate_controller_path = OUT_DIR / "yado_autonomous_grammar_candidate_controller_v3.py"
    parent_solver_path.write_text(parent_solver_source, encoding="utf-8")
    parent_solver = load_path("yado_grammar_parent_solver_v3", parent_solver_path)

    external, provenance = fetch_json(RUN_LENGTH_URL)
    training, sealed = split_run_length(external)

    target_selection = select_meta_target_from_grammar_failure(v2, training)
    parent_controller_source = v2_path.read_text(encoding="utf-8")
    parent_controller_path.write_text(parent_controller_source, encoding="utf-8")
    parent_controller_sha = sha_text(parent_controller_source)

    candidate_controller_source, grammar_evidence = mutate_meta_grammar(parent_controller_source)
    compile(candidate_controller_source, str(candidate_controller_path), "exec")
    candidate_controller_path.write_text(candidate_controller_source, encoding="utf-8")
    candidate_controller_sha = sha_text(candidate_controller_source)
    candidate_controller = load_path("yado_grammar_candidate_controller_v3", candidate_controller_path)

    # The mutated grammar, not this outer controller, must synthesize the fresh operator.
    spec = candidate_controller.synthesize_generic(training)
    if spec.get("generated_composition") != NEW_OPERATOR:
        raise RuntimeError(f"unexpected grammar extension selected: {spec.get('generated_composition')}")
    if spec.get("training_score") != 1.0:
        raise RuntimeError("generated grammar extension does not fit training partition")

    candidate_solver_source, solver_ast_evidence = v2.inject_generated_helpers(
        parent_solver_source,
        {"run-length-encoding": spec},
    )
    compile(candidate_solver_source, str(candidate_solver_path), "exec")
    candidate_solver_path.write_text(candidate_solver_source, encoding="utf-8")
    candidate_solver_sha = sha_text(candidate_solver_source)
    parent_solver_sha = sha_text(parent_solver_source)
    candidate_solver = load_path("yado_grammar_candidate_solver_v3", candidate_solver_path)

    parent_training = evaluate_run_length(parent_solver, training)
    candidate_training = evaluate_run_length(candidate_solver, training)
    old_v1_retention = v2.evaluate(candidate_solver, v1_sealed)
    old_v2_retention = v2.evaluate(candidate_solver, v2_sealed)

    # Freeze both self-modified grammar and solver before fresh sealed evaluation.
    frozen_controller_sha = sha_text(candidate_controller_path.read_text(encoding="utf-8"))
    frozen_solver_sha = sha_text(candidate_solver_path.read_text(encoding="utf-8"))
    if frozen_controller_sha != candidate_controller_sha or frozen_solver_sha != candidate_solver_sha:
        raise RuntimeError("candidate identities changed before sealed gate")

    sealed_parent = evaluate_run_length(parent_solver, sealed)
    sealed_candidate = evaluate_run_length(candidate_solver, sealed)
    if sha_text(candidate_controller_path.read_text(encoding="utf-8")) != frozen_controller_sha:
        raise RuntimeError("grammar controller changed after sealed gate")
    if sha_text(candidate_solver_path.read_text(encoding="utf-8")) != frozen_solver_sha:
        raise RuntimeError("solver changed after sealed gate")

    sealed_uuids = {str(c.get("uuid")) for c in sealed if c.get("uuid")}
    leakage_text = candidate_controller_source + "\n" + candidate_solver_source
    leaked_uuids = sorted(uuid for uuid in sealed_uuids if uuid in leakage_text)
    gain = sealed_candidate["score"] - sealed_parent["score"]

    pass_gate = (
        target_selection["origin"] == "META_GRAMMAR_RUNTIME_FAILURE_TRACE"
        and target_selection["selected_path"] == "runtime/yado_autonomous_meta_source_evolution_v2.py"
        and grammar_evidence["operator_absent_in_parent"]
        and grammar_evidence["operator_present_in_candidate"]
        and grammar_evidence["all_generated_roots_novel"]
        and parent_controller_sha != candidate_controller_sha
        and spec["generated_composition"] == NEW_OPERATOR
        and spec["training_score"] == 1.0
        and parent_training["score"] == 0.0
        and candidate_training["score"] == 1.0
        and sealed_parent["score"] == 0.0
        and sealed_candidate["score"] == 1.0
        and gain == 1.0
        and old_v1_retention["score"] == 1.0
        and old_v2_retention["score"] == 1.0
        and solver_ast_evidence["all_generated_roots_novel"]
        and parent_solver_sha != candidate_solver_sha
        and not leaked_uuids
    )
    status = (
        "PASS_SHADOW_G2_AUTONOMOUS_GRAMMAR_EXTENSION_V3"
        if pass_gate
        else "WITHHOLD_G2_AUTONOMOUS_GRAMMAR_EXTENSION_V3"
    )

    report = {
        "schema": "yado.autonomous_grammar_extension.v3",
        "status": status,
        "external_source_commit": EXTERNAL_COMMIT,
        "external_provenance": provenance,
        "fresh_scope": {
            "exercise": "run-length-encoding",
            "property": "encode",
            "training_cases": len(training),
            "sealed_cases": len(sealed),
            "sealed_not_used_for_grammar_selection": True,
        },
        "target_selection": target_selection,
        "parent_grammar_controller": {
            "path": str(parent_controller_path.relative_to(ROOT)),
            "source_target": "runtime/yado_autonomous_meta_source_evolution_v2.py",
            "sha256": parent_controller_sha,
        },
        "candidate_grammar_controller": {
            "path": str(candidate_controller_path.relative_to(ROOT)),
            "sha256": candidate_controller_sha,
        },
        "parent_solver": {"path": str(parent_solver_path.relative_to(ROOT)), "sha256": parent_solver_sha},
        "candidate_solver": {"path": str(candidate_solver_path.relative_to(ROOT)), "sha256": candidate_solver_sha},
        "grammar_extension": {
            "selected_operator": NEW_OPERATOR,
            "selected_spec": spec,
            "evidence": grammar_evidence,
            "solver_ast_evidence": solver_ast_evidence,
        },
        "metrics": {
            "parent_training": parent_training,
            "candidate_training": candidate_training,
            "sealed_parent": sealed_parent,
            "sealed_candidate": sealed_candidate,
            "sealed_absolute_gain": gain,
            "v1_external_sealed_retention": old_v1_retention,
            "v2_external_sealed_retention": old_v2_retention,
        },
        "gates": {
            "parent_meta_grammar_rejected_fresh_signature": True,
            "target_selected_from_meta_grammar_failure_trace": True,
            "host_provided_target_path": False,
            "new_operator_absent_in_parent_grammar": grammar_evidence["operator_absent_in_parent"],
            "new_operator_present_in_candidate_grammar": grammar_evidence["operator_present_in_candidate"],
            "candidate_grammar_source_changed": parent_controller_sha != candidate_controller_sha,
            "candidate_solver_source_changed": parent_solver_sha != candidate_solver_sha,
            "candidate_grammar_frozen_before_sealed_eval": True,
            "candidate_solver_frozen_before_sealed_eval": True,
            "fresh_sealed_uuid_leak_count": len(leaked_uuids),
            "fresh_sealed_uuid_leaks": leaked_uuids,
            "external_models_used": False,
            "canonical_mutation": False,
            "task_named_formula_used_for_selection": False,
            "bounded_host_authored_meta_grammar": True,
        },
        "training_case_fingerprints": [case_fingerprint(c) for c in training],
        "sealed_case_fingerprints": [case_fingerprint(c) for c in sealed],
        "claim_boundary": (
            "V3 demonstrates autonomous selection of the failing mutation-builder source from its own grammar failure, "
            "AST materialization of a previously absent str->str grammar route, and successful use of the newly added "
            "adjacent_run_fold operator on fresh sealed external cases while retaining V1/V2 behavior. The low-level "
            "meta-program candidates and admission gates are still host-authored and bounded. This is not proof of "
            "unrestricted self-rewrite, general intelligence, or consciousness."
        ),
    }
    report["receipt_sha256"] = sha_text(json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": status,
        "target": target_selection["selected_path"],
        "new_operator": NEW_OPERATOR,
        "operator_absent_in_parent": grammar_evidence["operator_absent_in_parent"],
        "grammar_controller_sha256": candidate_controller_sha,
        "solver_sha256": candidate_solver_sha,
        "parent_training": parent_training["score"],
        "candidate_training": candidate_training["score"],
        "sealed_parent": sealed_parent["score"],
        "sealed_candidate": sealed_candidate["score"],
        "sealed_gain": gain,
        "v1_retention": old_v1_retention["score"],
        "v2_retention": old_v2_retention["score"],
    }, sort_keys=True))
    return 0 if pass_gate else 2


if __name__ == "__main__":
    raise SystemExit(main())
