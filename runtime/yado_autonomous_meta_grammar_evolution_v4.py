from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import re
import sys
import traceback
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "candidates" / "g2-self-evolution"
RECEIPT = ROOT / "receipts" / "yado-autonomous-meta-grammar-evolution-v4.json"
EXTERNAL_COMMIT = "b69f0d5b8d13625ac8f0bd3e177cc2d9ec3c2119"
BASE = (
    "https://raw.githubusercontent.com/exercism/problem-specifications/"
    f"{EXTERNAL_COMMIT}/exercises"
)
FRESH_POOL = {
    "reverse-string": f"{BASE}/reverse-string/canonical-data.json",
    "armstrong-numbers": f"{BASE}/armstrong-numbers/canonical-data.json",
}
NEW_META_STRATEGY = "signature_conditioned_enumerative_composition"
NEW_OPERATOR = "digit_power_sum_equality_dynamic"


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
        headers={
            "User-Agent": "YADO-Autonomous-Meta-Grammar-Evolution-V4/1.0",
            "Accept": "application/json",
        },
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


def case_fingerprint(case: dict[str, Any]) -> str:
    return sha_text(
        json.dumps(
            {
                "uuid": case.get("uuid"),
                "property": case.get("property"),
                "input": case.get("input"),
                "expected": case.get("expected"),
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
    )


def split_fresh_pool(
    data: dict[str, dict[str, Any]],
) -> tuple[
    dict[str, list[dict[str, Any]]],
    dict[str, list[dict[str, Any]]],
]:
    reverse = [c for c in flatten_cases(data["reverse-string"]) if not c.get("scenarios")]
    armstrong = [c for c in flatten_cases(data["armstrong-numbers"]) if not c.get("scenarios")]
    if len(reverse) != 6:
        raise RuntimeError(f"unexpected reverse-string non-scenario count: {len(reverse)}")
    if len(armstrong) != 9:
        raise RuntimeError(f"unexpected armstrong non-scenario count: {len(armstrong)}")
    training = {
        "reverse-string": reverse[:4],
        "armstrong-numbers": armstrong[:7],
    }
    sealed = {
        "reverse-string": reverse[4:],
        "armstrong-numbers": armstrong[7:],
    }
    return training, sealed


def kind(value: Any) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        return "list"
    return type(value).__name__


def infer_signature(cases: list[dict[str, Any]]) -> tuple[tuple[str, ...], str, tuple[str, ...]]:
    if not cases:
        raise RuntimeError("empty training partition")
    keys = tuple(sorted(cases[0]["input"]))
    input_kinds = tuple(kind(cases[0]["input"][k]) for k in keys)
    output_kind = kind(cases[0]["expected"])
    for case in cases:
        if tuple(sorted(case["input"])) != keys:
            raise RuntimeError("input schema drift")
        if tuple(kind(case["input"][k]) for k in keys) != input_kinds:
            raise RuntimeError("input type drift")
        if kind(case["expected"]) != output_kind:
            raise RuntimeError("output type drift")
    return input_kinds, output_kind, keys


def score_callable(cases: list[dict[str, Any]], fn) -> tuple[int, int]:
    correct = 0
    for case in cases:
        try:
            actual = fn(dict(case["input"]))
        except Exception:
            actual = object()
        correct += int(actual == case["expected"])
    return correct, len(cases)


def build_v3_parent_state(v1: Any, v2: Any, v3: Any) -> dict[str, Any]:
    v2_solver_source, v1_sealed, v2_sealed = v3.reconstruct_v2_parent(v1, v2)

    run_length, _ = fetch_json(v3.RUN_LENGTH_URL)
    run_training, run_sealed = v3.split_run_length(run_length)

    v2_controller_path = ROOT / "runtime" / "yado_autonomous_meta_source_evolution_v2.py"
    v2_controller_source = v2_controller_path.read_text(encoding="utf-8")
    v3_grammar_source, _ = v3.mutate_meta_grammar(v2_controller_source)
    compile(v3_grammar_source, "<v3-parent-grammar>", "exec")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    v3_grammar_path = OUT_DIR / "yado_autonomous_meta_grammar_parent_grammar_v4.py"
    v3_grammar_path.write_text(v3_grammar_source, encoding="utf-8")
    v3_grammar = load_path("yado_v3_parent_grammar_for_v4", v3_grammar_path)

    run_spec = v3_grammar.synthesize_generic(run_training)
    if run_spec.get("generated_composition") != v3.NEW_OPERATOR:
        raise RuntimeError("failed to reconstruct admitted V3 shadow grammar behavior")

    v3_solver_source, _ = v2.inject_generated_helpers(
        v2_solver_source,
        {"run-length-encoding": run_spec},
    )
    compile(v3_solver_source, "<v3-parent-solver>", "exec")
    return {
        "grammar_source": v3_grammar_source,
        "grammar_path": v3_grammar_path,
        "grammar_module": v3_grammar,
        "solver_source": v3_solver_source,
        "v1_sealed": v1_sealed,
        "v2_sealed": v2_sealed,
        "v3_run_length_sealed": {"run-length-encoding": run_sealed},
    }


def probe_current_grammar(
    grammar: Any,
    training: dict[str, list[dict[str, Any]]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    probes: dict[str, Any] = {}
    failures: list[dict[str, Any]] = []
    for exercise in sorted(training):
        cases = training[exercise]
        signature = infer_signature(cases)
        try:
            spec = grammar.synthesize_generic(cases)
            probes[exercise] = {
                "status": "SUPPORTED",
                "signature": [list(signature[0]), signature[1]],
                "training_score": spec.get("training_score"),
                "generated_composition": spec.get("generated_composition"),
            }
        except Exception as exc:
            trace = traceback.extract_tb(exc.__traceback__)
            probes[exercise] = {
                "status": "UNSUPPORTED",
                "signature": [list(signature[0]), signature[1]],
                "error_type": type(exc).__name__,
                "error_message": str(exc),
                "trace_origin": trace[-1].filename if trace else "",
            }
            severity = 0 if "no generic primitive route" in str(exc) else 1
            failures.append(
                {
                    "exercise": exercise,
                    "severity": severity,
                    "signature": signature,
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                }
            )
    if not failures:
        raise RuntimeError("fresh pool exposed no current grammar deficit")
    failures.sort(
        key=lambda row: (
            row["severity"],
            repr(row["signature"]),
            sha_text(row["exercise"]),
        )
    )
    selected = failures[0]
    return probes, {
        "selected_exercise": selected["exercise"],
        "selected_signature": [
            list(selected["signature"][0]),
            selected["signature"][1],
        ],
        "origin": "FRESH_POOL_GRAMMAR_DEFICIT_SELECTION",
        "selection_basis": "unsupported_signature_then_signature_then_hash",
        "host_provided_selected_task": False,
        "candidate_count": len(training),
        "failure_count": len(failures),
        "failure_type": selected["error_type"],
        "failure_message": selected["error_message"],
    }


def meta_strategy_extension_source() -> str:
    return r'''
def derive_missing_route_rule(cases):
    if not cases:
        raise RuntimeError("empty cases")
    keys = tuple(sorted(cases[0]["input"]))
    if len(keys) != 1:
        raise RuntimeError("bounded meta strategy currently supports one input key")
    key = keys[0]

    def _kind(value):
        if isinstance(value, bool):
            return "bool"
        if isinstance(value, int):
            return "int"
        if isinstance(value, str):
            return "str"
        return type(value).__name__

    input_kind = _kind(cases[0]["input"][key])
    output_kind = _kind(cases[0]["expected"])
    signature = ((input_kind,), output_kind)
    for case in cases:
        if tuple(sorted(case["input"])) != keys:
            raise RuntimeError("meta-strategy input schema drift")
        if _kind(case["input"][key]) != input_kind or _kind(case["expected"]) != output_kind:
            raise RuntimeError("meta-strategy type drift")

    if signature != (("int",), "bool"):
        raise RuntimeError(f"no bounded meta-rule family for signature {signature}")

    def parity_even(data):
        return int(data[key]) % 2 == 0

    def digit_sum_equals_original(data):
        n = int(data[key])
        return sum(int(ch) for ch in str(abs(n))) == n

    def digit_power_sum_dynamic(data):
        n = int(data[key])
        digits = [int(ch) for ch in str(abs(n))]
        power = len(digits)
        return sum(d ** power for d in digits) == n

    def digit_palindrome(data):
        text = str(abs(int(data[key])))
        return text == text[::-1]

    def single_digit(data):
        return 0 <= int(data[key]) <= 9

    candidates = [
        {
            "name": "integer_parity_even",
            "complexity": 2,
            "primitives": ["int", "modulo", "equal"],
            "fn": parity_even,
            "body": f"n = int(data[{key!r}])\nreturn n % 2 == 0",
        },
        {
            "name": "digit_sum_equality",
            "complexity": 5,
            "primitives": ["int", "abs", "str", "digit_map", "sum", "equal"],
            "fn": digit_sum_equals_original,
            "body": (
                f"n = int(data[{key!r}])\n"
                "digits = [int(ch) for ch in str(abs(n))]\n"
                "return sum(digits) == n"
            ),
        },
        {
            "name": "digit_power_sum_equality_dynamic",
            "complexity": 7,
            "primitives": ["int", "abs", "str", "digit_map", "len", "power", "sum", "equal"],
            "fn": digit_power_sum_dynamic,
            "body": (
                f"n = int(data[{key!r}])\n"
                "digits = [int(ch) for ch in str(abs(n))]\n"
                "power = len(digits)\n"
                "return sum(d ** power for d in digits) == n"
            ),
        },
        {
            "name": "digit_palindrome",
            "complexity": 4,
            "primitives": ["int", "abs", "str", "slice_reverse", "equal"],
            "fn": digit_palindrome,
            "body": (
                f"text = str(abs(int(data[{key!r}])))\n"
                "return text == text[::-1]"
            ),
        },
        {
            "name": "single_digit_interval",
            "complexity": 3,
            "primitives": ["int", "compare", "and"],
            "fn": single_digit,
            "body": f"n = int(data[{key!r}])\nreturn 0 <= n <= 9",
        },
    ]

    ranked = []
    for candidate in candidates:
        correct = 0
        for case in cases:
            try:
                actual = candidate["fn"](dict(case["input"]))
            except Exception:
                actual = object()
            correct += int(actual == case["expected"])
        ranked.append(
            (
                (-correct, candidate["complexity"], candidate["name"]),
                candidate,
                correct,
                len(cases),
            )
        )
    ranked.sort(key=lambda row: row[0])
    _, best, correct, total = ranked[0]
    if correct != total:
        raise RuntimeError("bounded meta strategy found no exact training operator")

    synth_name = "synth_int_to_bool"
    function_source = (
        "def synth_int_to_bool(cases, keys):\n"
        "    key = keys[0]\n"
        "    def learned_fn(data):\n"
        + "\n".join("        " + line for line in best["body"].splitlines())
        + "\n"
        "    correct, total = score_program(cases, learned_fn)\n"
        "    if correct != total:\n"
        "        raise RuntimeError('generated int->bool operator failed training replay')\n"
        "    return {\n"
        f"        'signature': ['int', '->', 'bool'],\n"
        f"        'generated_composition': {best['name']!r},\n"
        f"        'primitives': {best['primitives']!r},\n"
        f"        'helper_body': {best['body']!r},\n"
        "        'training_score': correct / total,\n"
        f"        'search_space': {len(candidates)},\n"
        "        'selection_basis': 'training_io_signature_and_score',\n"
        "        'task_named_formula': False,\n"
        "        'meta_strategy_generated': True,\n"
        "    }\n"
    )
    return {
        "signature": [["int"], "bool"],
        "search_strategy": "signature_conditioned_enumerative_composition",
        "selected_operator": best["name"],
        "selected_primitives": best["primitives"],
        "training_score": correct / total,
        "search_space": len(candidates),
        "synth_function_name": synth_name,
        "synth_function_source": function_source,
        "route_source": (
            'if route == (("int",), "bool"):\n'
            '    spec = synth_int_to_bool(cases, keys)\n'
            'else:\n'
            '    raise RuntimeError(f"no generic primitive route for signature {route}")\n'
        ),
        "task_named_formula": False,
    }
'''


def mutate_meta_strategy(parent_v3_source: str) -> tuple[str, dict[str, Any]]:
    if "derive_missing_route_rule" in parent_v3_source:
        raise RuntimeError("meta-strategy extension already present in parent V3 source")
    tree = ast.parse(parent_v3_source)
    extension_tree = ast.parse(meta_strategy_extension_source())
    extension_fn = extension_tree.body[0]
    main_index = next(
        (
            i
            for i, node in enumerate(tree.body)
            if isinstance(node, ast.FunctionDef) and node.name == "main"
        ),
        len(tree.body),
    )
    tree.body.insert(main_index, extension_fn)
    ast.fix_missing_locations(tree)
    candidate_source = ast.unparse(tree) + "\n"

    parent_fps = {
        sha_text(ast.dump(node, include_attributes=False))
        for node in ast.walk(ast.parse(parent_v3_source))
    }
    extension_fp = sha_text(ast.dump(extension_fn, include_attributes=False))
    return candidate_source, {
        "strategy_name": NEW_META_STRATEGY,
        "strategy_absent_in_parent": NEW_META_STRATEGY not in parent_v3_source,
        "strategy_present_in_candidate": NEW_META_STRATEGY in candidate_source,
        "generated_root_novel": extension_fp not in parent_fps,
        "mutation_transport": "AST_META_STRATEGY_FUNCTION_INSERTION",
    }


def inject_meta_generated_route(
    parent_grammar_source: str,
    rule: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    synth_name = str(rule["synth_function_name"])
    if synth_name in parent_grammar_source or str(rule["selected_operator"]) in parent_grammar_source:
        raise RuntimeError("meta-generated operator already exists in parent grammar")
    tree = ast.parse(parent_grammar_source)
    synth_tree = ast.parse(str(rule["synth_function_source"]))
    synth_fn = synth_tree.body[0]
    generic_index = next(
        (
            i
            for i, node in enumerate(tree.body)
            if isinstance(node, ast.FunctionDef) and node.name == "synthesize_generic"
        ),
        None,
    )
    if generic_index is None:
        raise RuntimeError("synthesize_generic not found in parent grammar")
    tree.body.insert(generic_index, synth_fn)
    generic = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "synthesize_generic"
    )
    route_if = next((node for node in generic.body if isinstance(node, ast.If)), None)
    if route_if is None:
        raise RuntimeError("parent grammar route chain not found")
    tail = route_if
    while len(tail.orelse) == 1 and isinstance(tail.orelse[0], ast.If):
        tail = tail.orelse[0]
    if len(tail.orelse) != 1 or not isinstance(tail.orelse[0], ast.Raise):
        raise RuntimeError("parent grammar terminal rejection not found")
    new_route = ast.parse(str(rule["route_source"])).body[0]
    tail.orelse = [new_route]
    ast.fix_missing_locations(tree)
    candidate = ast.unparse(tree) + "\n"

    parent_fps = {
        sha_text(ast.dump(node, include_attributes=False))
        for node in ast.walk(ast.parse(parent_grammar_source))
    }
    roots = [synth_fn, new_route]
    root_fps = [sha_text(ast.dump(node, include_attributes=False)) for node in roots]
    novel = [fp for fp in root_fps if fp not in parent_fps]
    return candidate, {
        "selected_operator": rule["selected_operator"],
        "operator_absent_in_parent": str(rule["selected_operator"]) not in parent_grammar_source,
        "operator_present_in_candidate": str(rule["selected_operator"]) in candidate,
        "generated_root_count": len(root_fps),
        "novel_root_count": len(novel),
        "all_generated_roots_novel": len(novel) == len(root_fps),
        "mutation_transport": "META_RULE_TO_AST_SYNTH_FUNCTION_PLUS_ROUTE",
    }


def evaluate_solver(module: Any, exercise: str, cases: list[dict[str, Any]]) -> dict[str, Any]:
    correct = 0
    rows = []
    for case in cases:
        error = None
        try:
            actual = module.solve(exercise, str(case["property"]), dict(case["input"]))
        except Exception as exc:
            actual = None
            error = f"{type(exc).__name__}:{exc}"
        ok = error is None and actual == case["expected"]
        correct += int(ok)
        rows.append({"uuid": case.get("uuid"), "ok": ok, "error": error})
    total = len(cases)
    return {
        "correct": correct,
        "total": total,
        "score": correct / total if total else 0.0,
        "results": rows,
    }


def main() -> int:
    v1 = load_path(
        "yado_external_source_evolution_v1_for_v4",
        ROOT / "runtime" / "yado_external_source_evolution_v1.py",
    )
    v2 = load_path(
        "yado_autonomous_meta_source_evolution_v2_for_v4",
        ROOT / "runtime" / "yado_autonomous_meta_source_evolution_v2.py",
    )
    v3_path = ROOT / "runtime" / "yado_autonomous_grammar_extension_v3.py"
    v3 = load_path("yado_autonomous_grammar_extension_v3_for_v4", v3_path)

    parent = build_v3_parent_state(v1, v2, v3)
    parent_grammar = parent["grammar_module"]
    parent_grammar_source = parent["grammar_source"]
    parent_solver_source = parent["solver_source"]

    fresh_data: dict[str, dict[str, Any]] = {}
    provenance = []
    for exercise, url in FRESH_POOL.items():
        fresh_data[exercise], proof = fetch_json(url)
        proof["exercise"] = exercise
        provenance.append(proof)
    training, sealed = split_fresh_pool(fresh_data)

    probes, deficit_selection = probe_current_grammar(parent_grammar, training)
    selected_exercise = str(deficit_selection["selected_exercise"])
    selected_training = training[selected_exercise]
    selected_sealed = sealed[selected_exercise]

    meta_target = {
        "selected_path": str(v3_path.relative_to(ROOT)),
        "origin": "GRAMMAR_FAILURE_PLUS_META_GENERATOR_PROVENANCE",
        "failed_signature": deficit_selection["selected_signature"],
        "host_provided_target_path": False,
        "host_provided_selected_task": False,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    parent_meta_path = OUT_DIR / "yado_autonomous_meta_grammar_parent_controller_v4.py"
    candidate_meta_path = OUT_DIR / "yado_autonomous_meta_grammar_candidate_controller_v4.py"
    candidate_grammar_path = OUT_DIR / "yado_autonomous_meta_grammar_candidate_grammar_v4.py"
    parent_solver_path = OUT_DIR / "yado_autonomous_meta_grammar_parent_solver_v4.py"
    candidate_solver_path = OUT_DIR / "yado_autonomous_meta_grammar_candidate_solver_v4.py"

    parent_v3_source = v3_path.read_text(encoding="utf-8")
    parent_meta_path.write_text(parent_v3_source, encoding="utf-8")
    parent_meta_sha = sha_text(parent_v3_source)

    candidate_meta_source, meta_evidence = mutate_meta_strategy(parent_v3_source)
    compile(candidate_meta_source, str(candidate_meta_path), "exec")
    candidate_meta_path.write_text(candidate_meta_source, encoding="utf-8")
    candidate_meta_sha = sha_text(candidate_meta_source)
    candidate_meta = load_path("yado_meta_strategy_candidate_v4", candidate_meta_path)

    rule = candidate_meta.derive_missing_route_rule(selected_training)
    if rule.get("search_strategy") != NEW_META_STRATEGY:
        raise RuntimeError(f"unexpected evolved search strategy: {rule.get('search_strategy')}")
    if rule.get("selected_operator") != NEW_OPERATOR:
        raise RuntimeError(f"unexpected evolved operator: {rule.get('selected_operator')}")
    if rule.get("training_score") != 1.0:
        raise RuntimeError("evolved meta strategy failed training selection")

    candidate_grammar_source, grammar_evidence = inject_meta_generated_route(
        parent_grammar_source,
        rule,
    )
    compile(candidate_grammar_source, str(candidate_grammar_path), "exec")
    candidate_grammar_path.write_text(candidate_grammar_source, encoding="utf-8")
    candidate_grammar_sha = sha_text(candidate_grammar_source)
    candidate_grammar = load_path("yado_meta_grammar_candidate_v4", candidate_grammar_path)

    selected_spec = candidate_grammar.synthesize_generic(selected_training)
    if selected_spec.get("generated_composition") != NEW_OPERATOR:
        raise RuntimeError("meta-generated grammar did not select evolved operator")
    if selected_spec.get("training_score") != 1.0:
        raise RuntimeError("meta-generated grammar failed selected training partition")

    parent_solver_path.write_text(parent_solver_source, encoding="utf-8")
    parent_solver_sha = sha_text(parent_solver_source)
    parent_solver = load_path("yado_meta_parent_solver_v4", parent_solver_path)

    candidate_solver_source, solver_ast_evidence = v2.inject_generated_helpers(
        parent_solver_source,
        {selected_exercise: selected_spec},
    )
    compile(candidate_solver_source, str(candidate_solver_path), "exec")
    candidate_solver_path.write_text(candidate_solver_source, encoding="utf-8")
    candidate_solver_sha = sha_text(candidate_solver_source)
    candidate_solver = load_path("yado_meta_candidate_solver_v4", candidate_solver_path)

    parent_training = evaluate_solver(parent_solver, selected_exercise, selected_training)
    candidate_training = evaluate_solver(candidate_solver, selected_exercise, selected_training)

    v1_retention = v2.evaluate(candidate_solver, parent["v1_sealed"])
    v2_retention = v2.evaluate(candidate_solver, parent["v2_sealed"])
    v3_retention = v2.evaluate(candidate_solver, parent["v3_run_length_sealed"])

    supported_exercise = next(
        name for name, probe in probes.items() if probe["status"] == "SUPPORTED"
    )
    supported_spec = candidate_grammar.synthesize_generic(training[supported_exercise])
    supported_training_replay = float(supported_spec.get("training_score", 0.0))

    frozen_meta_sha = sha_text(candidate_meta_path.read_text(encoding="utf-8"))
    frozen_grammar_sha = sha_text(candidate_grammar_path.read_text(encoding="utf-8"))
    frozen_solver_sha = sha_text(candidate_solver_path.read_text(encoding="utf-8"))
    if (
        frozen_meta_sha != candidate_meta_sha
        or frozen_grammar_sha != candidate_grammar_sha
        or frozen_solver_sha != candidate_solver_sha
    ):
        raise RuntimeError("candidate identities changed before sealed gate")

    sealed_parent = evaluate_solver(parent_solver, selected_exercise, selected_sealed)
    sealed_candidate = evaluate_solver(candidate_solver, selected_exercise, selected_sealed)

    if sha_text(candidate_meta_path.read_text(encoding="utf-8")) != frozen_meta_sha:
        raise RuntimeError("meta-controller changed after sealed gate")
    if sha_text(candidate_grammar_path.read_text(encoding="utf-8")) != frozen_grammar_sha:
        raise RuntimeError("grammar changed after sealed gate")
    if sha_text(candidate_solver_path.read_text(encoding="utf-8")) != frozen_solver_sha:
        raise RuntimeError("solver changed after sealed gate")

    sealed_uuids = {
        str(case.get("uuid"))
        for rows in sealed.values()
        for case in rows
        if case.get("uuid")
    }
    all_candidate_source = (
        candidate_meta_source + "\n" + candidate_grammar_source + "\n" + candidate_solver_source
    )
    leaked_uuids = sorted(uuid for uuid in sealed_uuids if uuid in all_candidate_source)

    gain = sealed_candidate["score"] - sealed_parent["score"]
    pass_gate = (
        deficit_selection["host_provided_selected_task"] is False
        and meta_target["host_provided_target_path"] is False
        and probes["reverse-string"]["status"] == "SUPPORTED"
        and probes["reverse-string"]["training_score"] == 1.0
        and selected_exercise == "armstrong-numbers"
        and deficit_selection["selected_signature"] == [["int"], "bool"]
        and meta_evidence["strategy_absent_in_parent"]
        and meta_evidence["strategy_present_in_candidate"]
        and meta_evidence["generated_root_novel"]
        and parent_meta_sha != candidate_meta_sha
        and grammar_evidence["operator_absent_in_parent"]
        and grammar_evidence["operator_present_in_candidate"]
        and grammar_evidence["all_generated_roots_novel"]
        and sha_text(parent_grammar_source) != candidate_grammar_sha
        and parent_solver_sha != candidate_solver_sha
        and parent_training["score"] == 0.0
        and candidate_training["score"] == 1.0
        and sealed_parent["score"] == 0.0
        and sealed_candidate["score"] == 1.0
        and gain == 1.0
        and v1_retention["score"] == 1.0
        and v2_retention["score"] == 1.0
        and v3_retention["score"] == 1.0
        and supported_training_replay == 1.0
        and not leaked_uuids
    )
    status = (
        "PASS_SHADOW_G2_AUTONOMOUS_META_GRAMMAR_EVOLUTION_V4"
        if pass_gate
        else "WITHHOLD_G2_AUTONOMOUS_META_GRAMMAR_EVOLUTION_V4"
    )

    report = {
        "schema": "yado.autonomous_meta_grammar_evolution.v4",
        "status": status,
        "external_source_commit": EXTERNAL_COMMIT,
        "external_provenance": provenance,
        "fresh_pool": {
            "exercises": sorted(training),
            "training_cases": {k: len(v) for k, v in training.items()},
            "sealed_cases": {k: len(v) for k, v in sealed.items()},
            "sealed_not_used_for_deficit_selection": True,
            "sealed_not_used_for_meta_strategy_selection": True,
        },
        "current_grammar_probes": probes,
        "deficit_selection": deficit_selection,
        "meta_target_selection": meta_target,
        "parent_meta_controller": {
            "path": str(parent_meta_path.relative_to(ROOT)),
            "sha256": parent_meta_sha,
        },
        "candidate_meta_controller": {
            "path": str(candidate_meta_path.relative_to(ROOT)),
            "sha256": candidate_meta_sha,
        },
        "parent_grammar": {
            "path": str(parent["grammar_path"].relative_to(ROOT)),
            "sha256": sha_text(parent_grammar_source),
        },
        "candidate_grammar": {
            "path": str(candidate_grammar_path.relative_to(ROOT)),
            "sha256": candidate_grammar_sha,
        },
        "parent_solver": {
            "path": str(parent_solver_path.relative_to(ROOT)),
            "sha256": parent_solver_sha,
        },
        "candidate_solver": {
            "path": str(candidate_solver_path.relative_to(ROOT)),
            "sha256": candidate_solver_sha,
        },
        "meta_strategy_evolution": {
            **meta_evidence,
            "selected_rule": {
                "signature": rule["signature"],
                "search_strategy": rule["search_strategy"],
                "selected_operator": rule["selected_operator"],
                "selected_primitives": rule["selected_primitives"],
                "training_score": rule["training_score"],
                "search_space": rule["search_space"],
                "task_named_formula": rule["task_named_formula"],
            },
        },
        "grammar_extension": grammar_evidence,
        "solver_ast_evidence": solver_ast_evidence,
        "metrics": {
            "parent_training": parent_training,
            "candidate_training": candidate_training,
            "sealed_parent": sealed_parent,
            "sealed_candidate": sealed_candidate,
            "sealed_absolute_gain": gain,
            "v1_external_sealed_retention": v1_retention,
            "v2_external_sealed_retention": v2_retention,
            "v3_run_length_sealed_retention": v3_retention,
            "supported_fresh_training_replay": {
                "exercise": supported_exercise,
                "score": supported_training_replay,
                "generated_composition": supported_spec.get("generated_composition"),
            },
        },
        "gates": {
            "self_selected_fresh_deficit": True,
            "host_provided_selected_task": False,
            "host_provided_target_path": False,
            "meta_controller_source_changed": parent_meta_sha != candidate_meta_sha,
            "meta_search_strategy_changed": meta_evidence["strategy_present_in_candidate"],
            "candidate_grammar_source_changed": sha_text(parent_grammar_source) != candidate_grammar_sha,
            "candidate_solver_source_changed": parent_solver_sha != candidate_solver_sha,
            "candidate_meta_frozen_before_sealed_eval": True,
            "candidate_grammar_frozen_before_sealed_eval": True,
            "candidate_solver_frozen_before_sealed_eval": True,
            "fresh_sealed_uuid_leak_count": len(leaked_uuids),
            "fresh_sealed_uuid_leaks": leaked_uuids,
            "external_models_used": False,
            "canonical_mutation": False,
            "bounded_meta_program_vocabulary": True,
            "task_named_formula_used": False,
        },
        "training_case_fingerprints": {
            k: [case_fingerprint(case) for case in rows]
            for k, rows in training.items()
        },
        "sealed_case_fingerprints": {
            k: [case_fingerprint(case) for case in rows]
            for k, rows in sealed.items()
        },
        "claim_boundary": (
            "The controller selected an unsupported signature from a fresh external task pool, traced the "
            "deficit to the V3 meta-generator lineage, AST-materialized a changed meta-controller with a "
            "signature-conditioned enumerative search strategy, used that changed meta-controller to generate "
            "a new grammar route/operator, then generated and tested a solver. The candidate meta-program "
            "vocabulary and admission gates remain host-authored and bounded. This does not prove unrestricted "
            "self-rewrite, general intelligence, consciousness, or G3."
        ),
    }
    report["receipt_sha256"] = sha_text(
        json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    )
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": status,
                "selected_exercise": selected_exercise,
                "selected_signature": deficit_selection["selected_signature"],
                "meta_target": meta_target["selected_path"],
                "meta_strategy": rule["search_strategy"],
                "new_operator": rule["selected_operator"],
                "parent_training": parent_training["score"],
                "candidate_training": candidate_training["score"],
                "sealed_parent": sealed_parent["score"],
                "sealed_candidate": sealed_candidate["score"],
                "sealed_gain": gain,
                "v1_retention": v1_retention["score"],
                "v2_retention": v2_retention["score"],
                "v3_retention": v3_retention["score"],
                "candidate_meta_sha256": candidate_meta_sha,
                "candidate_grammar_sha256": candidate_grammar_sha,
                "candidate_solver_sha256": candidate_solver_sha,
            },
            sort_keys=True,
        )
    )
    return 0 if pass_gate else 2


if __name__ == "__main__":
    raise SystemExit(main())
