from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import re
import sys
import traceback
import urllib.request
import textwrap
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "candidates" / "g2-self-evolution"
RECEIPT = ROOT / "receipts" / "yado-autonomous-meta-source-evolution-v2.json"
EXTERNAL_COMMIT = "b69f0d5b8d13625ac8f0bd3e177cc2d9ec3c2119"
BASE = f"https://raw.githubusercontent.com/exercism/problem-specifications/{EXTERNAL_COMMIT}/exercises"
FRESH_SOURCES = {
    "hamming": f"{BASE}/hamming/canonical-data.json",
    "isogram": f"{BASE}/isogram/canonical-data.json",
    "raindrops": f"{BASE}/raindrops/canonical-data.json",
}


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
        headers={"User-Agent": "YADO-Autonomous-Meta-Source-Evolution-V2/1.0", "Accept": "application/json"},
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
    return sha_text(json.dumps({
        "uuid": case.get("uuid"),
        "property": case.get("property"),
        "input": case.get("input"),
        "expected": case.get("expected"),
    }, sort_keys=True, separators=(",", ":"), ensure_ascii=False))


def split_fresh(data: dict[str, dict[str, Any]]) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    hamming = [
        c for c in flatten_cases(data["hamming"])
        if isinstance(c.get("expected"), int)
        and not isinstance(c.get("expected"), bool)
        and len(str(c["input"]["strand1"])) == len(str(c["input"]["strand2"]))
    ]
    isogram = flatten_cases(data["isogram"])
    raindrops = flatten_cases(data["raindrops"])
    if len(hamming) < 5:
        raise RuntimeError(f"unexpected hamming numeric case count: {len(hamming)}")
    if len(isogram) != 14:
        raise RuntimeError(f"unexpected isogram case count: {len(isogram)}")
    if len(raindrops) != 18:
        raise RuntimeError(f"unexpected raindrops case count: {len(raindrops)}")
    training = {
        "hamming": hamming[:3],
        "isogram": isogram[:10],
        "raindrops": raindrops[:12],
    }
    sealed = {
        "hamming": hamming[3:5],
        "isogram": isogram[10:],
        "raindrops": raindrops[12:],
    }
    return training, sealed


def infer_signature(cases: list[dict[str, Any]]) -> tuple[tuple[str, ...], str, tuple[str, ...]]:
    if not cases:
        raise RuntimeError("empty training partition")
    keys = tuple(sorted(cases[0]["input"]))
    def kind(value: Any) -> str:
        if isinstance(value, bool):
            return "bool"
        if isinstance(value, int):
            return "int"
        if isinstance(value, str):
            return "str"
        return type(value).__name__
    input_kinds = tuple(kind(cases[0]["input"][k]) for k in keys)
    output_kind = kind(cases[0]["expected"])
    for case in cases:
        if tuple(sorted(case["input"])) != keys:
            raise RuntimeError("input schema drift")
        if tuple(kind(case["input"][k]) for k in keys) != input_kinds or kind(case["expected"]) != output_kind:
            raise RuntimeError("type signature drift")
    return input_kinds, output_kind, keys


def score_program(cases: list[dict[str, Any]], fn: Callable[[dict[str, Any]], Any]) -> tuple[int, int]:
    correct = 0
    for case in cases:
        try:
            actual = fn(dict(case["input"]))
        except Exception:
            actual = object()
        correct += int(actual == case["expected"])
    return correct, len(cases)


def synth_two_str_to_int(cases: list[dict[str, Any]], keys: tuple[str, ...]) -> dict[str, Any]:
    a_key, b_key = keys
    candidates: list[dict[str, Any]] = [
        {
            "name": "pairwise_mismatch_count",
            "complexity": 4,
            "primitives": ["zip", "not_equal", "int_cast", "sum"],
            "fn": lambda d: sum(int(a != b) for a, b in zip(str(d[a_key]), str(d[b_key]))),
            "body": f'a = str(data[{a_key!r}])\nb = str(data[{b_key!r}])\nreturn sum(int(x != y) for x, y in zip(a, b))',
        },
        {
            "name": "pairwise_match_count",
            "complexity": 4,
            "primitives": ["zip", "equal", "int_cast", "sum"],
            "fn": lambda d: sum(int(a == b) for a, b in zip(str(d[a_key]), str(d[b_key]))),
            "body": f'a = str(data[{a_key!r}])\nb = str(data[{b_key!r}])\nreturn sum(int(x == y) for x, y in zip(a, b))',
        },
        {
            "name": "absolute_length_delta",
            "complexity": 3,
            "primitives": ["len", "subtract", "abs"],
            "fn": lambda d: abs(len(str(d[a_key])) - len(str(d[b_key]))),
            "body": f'return abs(len(str(data[{a_key!r}])) - len(str(data[{b_key!r}])))',
        },
        {"name": "constant_zero", "complexity": 1, "primitives": ["constant"], "fn": lambda d: 0, "body": "return 0"},
        {"name": "constant_one", "complexity": 1, "primitives": ["constant"], "fn": lambda d: 1, "body": "return 1"},
    ]
    ranked = []
    for candidate in candidates:
        correct, total = score_program(cases, candidate["fn"])
        ranked.append(((-correct, candidate["complexity"], candidate["name"]), candidate, correct, total))
    ranked.sort(key=lambda row: row[0])
    _, best, correct, total = ranked[0]
    if correct != total:
        raise RuntimeError("generic two-string->int synthesis failed")
    return {
        "signature": ["str", "str", "->", "int"],
        "generated_composition": best["name"],
        "primitives": best["primitives"],
        "helper_body": best["body"],
        "training_score": correct / total,
        "search_space": len(candidates),
    }


def synth_str_to_bool(cases: list[dict[str, Any]], keys: tuple[str, ...]) -> dict[str, Any]:
    key = keys[0]
    normalizers = [
        ("identity", lambda s: s, "value", 0, []),
        ("lower", lambda s: s.lower(), "value.lower()", 1, ["lower"]),
    ]
    filters = [
        ("identity", lambda s: s, "seq", 0, []),
        ("alpha_only", lambda s: "".join(ch for ch in s if ch.isalpha()), "''.join(ch for ch in seq if ch.isalpha())", 2, ["iteration", "isalpha", "join"]),
        ("alnum_only", lambda s: "".join(ch for ch in s if ch.isalnum()), "''.join(ch for ch in seq if ch.isalnum())", 2, ["iteration", "isalnum", "join"]),
        ("drop_space_hyphen", lambda s: "".join(ch for ch in s if ch not in " -"), "''.join(ch for ch in seq if ch not in ' -')", 2, ["iteration", "membership", "join"]),
    ]
    predicates = [
        ("unique_cardinality", lambda s: len(s) == len(set(s)), "len(seq) == len(set(seq))", 2, ["len", "set", "equal"]),
        ("has_duplicate", lambda s: len(s) != len(set(s)), "len(seq) != len(set(seq))", 2, ["len", "set", "not_equal"]),
        ("is_empty", lambda s: len(s) == 0, "len(seq) == 0", 1, ["len", "equal"]),
    ]
    ranked = []
    for n_name, n_fn, n_src, n_cost, n_prims in normalizers:
        for f_name, f_fn, f_src, f_cost, f_prims in filters:
            for p_name, p_fn, p_src, p_cost, p_prims in predicates:
                def fn(d, n_fn=n_fn, f_fn=f_fn, p_fn=p_fn):
                    return p_fn(f_fn(n_fn(str(d[key]))))
                correct, total = score_program(cases, fn)
                name = f"{n_name}+{f_name}+{p_name}"
                body = (
                    f"value = str(data[{key!r}])\n"
                    f"seq = {n_src}\n"
                    f"seq = {f_src}\n"
                    f"return {p_src}"
                )
                ranked.append(((-correct, n_cost + f_cost + p_cost, name), {
                    "name": name,
                    "primitives": n_prims + f_prims + p_prims,
                    "body": body,
                }, correct, total))
    ranked.sort(key=lambda row: row[0])
    _, best, correct, total = ranked[0]
    if correct != total:
        raise RuntimeError("generic string->bool synthesis failed")
    return {
        "signature": ["str", "->", "bool"],
        "generated_composition": best["name"],
        "primitives": best["primitives"],
        "helper_body": best["body"],
        "training_score": correct / total,
        "search_space": len(ranked),
    }


def tokens(value: str) -> list[str]:
    return re.findall(r"[A-Z][a-z]*", value)


def synth_int_to_str(cases: list[dict[str, Any]], keys: tuple[str, ...]) -> dict[str, Any]:
    key = keys[0]
    rows = [(int(c["input"][key]), str(c["expected"])) for c in cases]
    token_order: list[str] = []
    for _, expected in rows:
        if expected.isdigit():
            continue
        for token in tokens(expected):
            if token not in token_order:
                token_order.append(token)
    if not token_order:
        raise RuntimeError("no symbolic output tokens discovered")
    learned: list[tuple[str, int]] = []
    searched = 0
    for token in token_order:
        choices = []
        for divisor in range(2, 33):
            searched += 1
            errors = 0
            for n, expected in rows:
                present = token in tokens(expected)
                errors += int((n % divisor == 0) != present)
            choices.append((errors, divisor))
        choices.sort()
        errors, divisor = choices[0]
        if errors:
            raise RuntimeError(f"no exact conditional relation for token {token}")
        learned.append((token, divisor))
    def learned_fn(data: dict[str, Any]) -> str:
        n = int(data[key])
        out = "".join(token for token, divisor in learned if n % divisor == 0)
        return out or str(n)
    correct, total = score_program(cases, learned_fn)
    if correct != total:
        raise RuntimeError("conditional concatenation induction failed")
    lines = [f"n = int(data[{key!r}])", "parts = []"]
    primitives = ["modulo", "conditional", "list_append", "join", "string_fallback"]
    for token, divisor in learned:
        lines.append(f"if n % {divisor} == 0:")
        lines.append(f"    parts.append({token!r})")
    lines.append("return ''.join(parts) or str(n)")
    return {
        "signature": ["int", "->", "str"],
        "generated_composition": "induced_conditional_token_concatenation",
        "primitives": primitives,
        "helper_body": "\n".join(lines),
        "learned_relations": [{"token": token, "divisor": divisor} for token, divisor in learned],
        "training_score": correct / total,
        "search_space": searched,
    }


def synthesize_generic(cases: list[dict[str, Any]]) -> dict[str, Any]:
    input_kinds, output_kind, keys = infer_signature(cases)
    route = (input_kinds, output_kind)
    if route == (("str", "str"), "int"):
        spec = synth_two_str_to_int(cases, keys)
    elif route == (("str",), "bool"):
        spec = synth_str_to_bool(cases, keys)
    elif route == (("int",), "str"):
        spec = synth_int_to_str(cases, keys)
    else:
        raise RuntimeError(f"no generic primitive route for signature {route}")
    spec["input_keys"] = list(keys)
    spec["selection_basis"] = "training_io_signature_and_score"
    spec["task_named_formula"] = False
    return spec


def inject_generated_helpers(parent_source: str, specs: dict[str, dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    tree = ast.parse(parent_source)
    solve = next((node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "solve"), None)
    if solve is None:
        raise RuntimeError("parent solve() not found")
    raise_index = next(
        (i for i in range(len(solve.body) - 1, -1, -1) if isinstance(solve.body[i], ast.Raise)),
        None,
    )
    if raise_index is None:
        raise RuntimeError("parent terminal raise not found")
    generated_nodes: list[ast.AST] = []
    dispatch_nodes: list[ast.stmt] = []
    helper_names = {}
    for exercise in sorted(specs):
        safe = re.sub(r"[^a-zA-Z0-9_]", "_", exercise)
        helper_name = f"_generated_{safe}"
        helper_names[exercise] = helper_name
        helper_source = f"def {helper_name}(data):\n{textwrap.indent(specs[exercise]['helper_body'], '    ')}\n"
        helper_tree = ast.parse(helper_source)
        generated_nodes.extend(helper_tree.body)
        dispatch_source = f"if exercise == {exercise!r}:\n    return {helper_name}(data)\n"
        dispatch_nodes.extend(ast.parse(dispatch_source).body)
    solve.body[raise_index:raise_index] = dispatch_nodes
    tree.body.extend(generated_nodes)
    ast.fix_missing_locations(tree)
    candidate_source = ast.unparse(tree) + "\n"

    parent_fingerprints = {
        sha_text(ast.dump(node, include_attributes=False))
        for node in ast.walk(ast.parse(parent_source))
    }
    generated_fingerprints = [
        sha_text(ast.dump(node, include_attributes=False))
        for node in generated_nodes + dispatch_nodes
    ]
    novel = [fp for fp in generated_fingerprints if fp not in parent_fingerprints]
    return candidate_source, {
        "helper_names": helper_names,
        "generated_node_count": len(generated_fingerprints),
        "novel_node_fingerprints": novel,
        "all_generated_roots_novel": len(novel) == len(generated_fingerprints),
    }


def evaluate(module: Any, cases: dict[str, list[dict[str, Any]]], detailed: bool = False) -> dict[str, Any]:
    correct = 0
    total = 0
    rows = []
    for exercise, group in cases.items():
        for case in group:
            total += 1
            error = None
            try:
                actual = module.solve(exercise, str(case["property"]), dict(case["input"]))
            except Exception as exc:
                actual = None
                error = f"{type(exc).__name__}:{exc}"
            ok = error is None and actual == case["expected"]
            correct += int(ok)
            if detailed:
                rows.append({"exercise": exercise, "uuid": case.get("uuid"), "ok": ok, "error": error})
    result = {"correct": correct, "total": total, "score": correct / total if total else 0.0}
    if detailed:
        result["results"] = rows
    return result


def select_target_from_failures(module: Any, parent_path: Path, training: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    traces = []
    for exercise, group in training.items():
        for case in group:
            try:
                module.solve(exercise, str(case["property"]), dict(case["input"]))
            except Exception as exc:
                frames = traceback.extract_tb(exc.__traceback__)
                origin = frames[-1].filename if frames else ""
                traces.append({
                    "exercise": exercise,
                    "error_type": type(exc).__name__,
                    "origin_filename": origin,
                    "origin_matches_parent": Path(origin).resolve() == parent_path.resolve() if origin else False,
                })
    if not traces or not all(t["error_type"] == "KeyError" and t["origin_matches_parent"] for t in traces):
        raise RuntimeError("runtime failure trace did not causally identify parent source")
    return {
        "selected_path": str(parent_path.relative_to(ROOT)),
        "origin": "RUNTIME_FAILURE_TRACE",
        "failure_count": len(traces),
        "failure_types": sorted({t["error_type"] for t in traces}),
        "host_provided_target_path": False,
    }


def main() -> int:
    v1 = load_path("yado_external_source_evolution_v1_for_v2", ROOT / "runtime" / "yado_external_source_evolution_v1.py")

    old_external = {}
    for name, url in v1.SOURCES.items():
        old_external[name], _ = fetch_json(url)
    old_training, old_sealed = v1.split_external(old_external)
    leap = v1.evolve_leap(old_training["leap"])
    grains = v1.evolve_grains(old_training["grains"])
    diff = v1.evolve_difference(old_training["difference-of-squares"])
    parent_source = v1.candidate_source(leap, grains, diff)
    compile(parent_source, "<v1-parent>", "exec")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    parent_path = OUT_DIR / "yado_autonomous_meta_source_parent_v2.py"
    candidate_path = OUT_DIR / "yado_autonomous_meta_source_candidate_v2.py"
    parent_path.write_text(parent_source, encoding="utf-8")
    parent_module = load_path("yado_meta_parent_v2", parent_path)

    fresh_external = {}
    provenance = []
    for name, url in FRESH_SOURCES.items():
        fresh_external[name], proof = fetch_json(url)
        proof["exercise"] = name
        provenance.append(proof)
    training, sealed = split_fresh(fresh_external)

    # The failing source is chosen from actual runtime traces, not passed as a target argument.
    target_selection = select_target_from_failures(parent_module, parent_path, training)
    parent_training = evaluate(parent_module, training)

    specs = {exercise: synthesize_generic(rows) for exercise, rows in training.items()}
    candidate_source, ast_evidence = inject_generated_helpers(parent_source, specs)
    compile(candidate_source, str(candidate_path), "exec")
    candidate_path.write_text(candidate_source, encoding="utf-8")
    candidate_sha = sha_text(candidate_source)
    parent_sha = sha_text(parent_source)
    candidate_module = load_path("yado_meta_candidate_v2", candidate_path)

    training_candidate = evaluate(candidate_module, training)
    old_sealed_candidate = evaluate(candidate_module, old_sealed)

    # Freeze the candidate identity before any fresh sealed expected value is consumed by evaluation.
    frozen_candidate_sha = sha_text(candidate_path.read_text(encoding="utf-8"))
    if frozen_candidate_sha != candidate_sha:
        raise RuntimeError("candidate changed before sealed gate")

    sealed_parent = evaluate(parent_module, sealed)
    sealed_candidate = evaluate(candidate_module, sealed)
    if sha_text(candidate_path.read_text(encoding="utf-8")) != frozen_candidate_sha:
        raise RuntimeError("candidate changed after sealed gate")

    sealed_uuids = {str(c.get("uuid")) for rows in sealed.values() for c in rows if c.get("uuid")}
    leaked_uuids = sorted(uuid for uuid in sealed_uuids if uuid in candidate_source)
    training_fingerprints = {k: [case_fingerprint(c) for c in v] for k, v in training.items()}
    sealed_fingerprints = {k: [case_fingerprint(c) for c in v] for k, v in sealed.items()}

    gain = sealed_candidate["score"] - sealed_parent["score"]
    pass_gate = (
        target_selection["origin"] == "RUNTIME_FAILURE_TRACE"
        and parent_training["score"] == 0.0
        and training_candidate["score"] == 1.0
        and sealed_candidate["score"] >= 0.90
        and gain >= 0.75
        and old_sealed_candidate["score"] == 1.0
        and parent_sha != candidate_sha
        and ast_evidence["all_generated_roots_novel"]
        and not leaked_uuids
    )
    status = (
        "PASS_SHADOW_G2_AUTONOMOUS_META_SOURCE_EVOLUTION_V2"
        if pass_gate
        else "WITHHOLD_G2_AUTONOMOUS_META_SOURCE_EVOLUTION_V2"
    )
    report = {
        "schema": "yado.autonomous_meta_source_evolution.v2",
        "status": status,
        "external_source_commit": EXTERNAL_COMMIT,
        "external_provenance": provenance,
        "target_selection": target_selection,
        "parent_source": {"path": str(parent_path.relative_to(ROOT)), "sha256": parent_sha},
        "candidate_source": {"path": str(candidate_path.relative_to(ROOT)), "sha256": candidate_sha},
        "fresh_scope": {
            "exercises": sorted(training),
            "training_cases": sum(len(v) for v in training.values()),
            "sealed_cases": sum(len(v) for v in sealed.values()),
            "sealed_not_used_for_selection": True,
        },
        "generated_mutation_specs": specs,
        "ast_evidence": ast_evidence,
        "metrics": {
            "parent_training": parent_training,
            "training_candidate": training_candidate,
            "sealed_parent": sealed_parent,
            "sealed_candidate": sealed_candidate,
            "sealed_absolute_gain": gain,
            "previous_external_sealed_retention": old_sealed_candidate,
        },
        "gates": {
            "source_changed": parent_sha != candidate_sha,
            "candidate_frozen_before_sealed_eval": True,
            "fresh_sealed_uuid_leak_count": len(leaked_uuids),
            "fresh_sealed_uuid_leaks": leaked_uuids,
            "generated_ast_roots_novel": ast_evidence["all_generated_roots_novel"],
            "external_models_used": False,
            "canonical_mutation": False,
            "task_named_formulas_used": False,
            "bounded_python_primitive_vocabulary": True,
        },
        "training_case_fingerprints": training_fingerprints,
        "sealed_case_fingerprints": sealed_fingerprints,
        "claim_boundary": (
            "The controller autonomously selected its failing self-generated source from runtime traceback evidence "
            "and composed new AST source from generic typed primitives. The primitive vocabulary and admission gates "
            "remain host-authored; this does not prove unrestricted self-rewrite, general intelligence, or consciousness."
        ),
    }
    report["receipt_sha256"] = sha_text(json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": status,
        "target": target_selection["selected_path"],
        "parent_training": parent_training["score"],
        "training_candidate": training_candidate["score"],
        "sealed_parent": sealed_parent["score"],
        "sealed_candidate": sealed_candidate["score"],
        "sealed_gain": gain,
        "old_sealed_retention": old_sealed_candidate["score"],
        "candidate_sha256": candidate_sha,
        "compositions": {k: v["generated_composition"] for k, v in specs.items()},
    }, sort_keys=True))
    return 0 if pass_gate else 2


if __name__ == "__main__":
    raise SystemExit(main())
