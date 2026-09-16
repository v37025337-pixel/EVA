"""Bounded family-agnostic typed program induction for native scalar source tasks.

The host defines a small safe primitive universe, deterministic enumerator, and
resource limits. No named target family, source code, operator subset, or PASS
verdict is supplied by the caller. A kernel-selected failed goal contributes only
its training examples; the smallest exact training behavior determines the
candidate primitive profile. The resulting reusable profile can then synthesize
new programs using only that frozen primitive subset.

This is bounded program induction, not unrestricted program or architecture
invention.
"""
from __future__ import annotations

import hashlib
import json
import re

SCHEMA = "yado.inductive_mechanism.v1"
GRAMMAR_VERSION = "YADO_TYPED_SEMANTIC_PROGRAM_INDUCTION_V1"
PRIMITIVE_ORDER = ("var", "const", "neg", "add", "sub", "mul", "mod", "lt", "le", "eq", "if")
PRIMITIVE_SET = frozenset(PRIMITIVE_ORDER)
CONSTANTS = (0, 1, -1, 2, -2)
MAX_NODES = 7
MAX_STATES = 50000
MAX_ABS_INPUT = 10**6
MAX_ABS_OUTPUT = 10**9


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _withhold(reason):
    return {"status": "WITHHOLD", "reason": reason, "source": None, "compiled": False,
            "synthesis_inputs": "TRAINING_ONLY", "automatic_canonical_promotion": False}


def _training(training):
    if type(training) is not list or not 3 <= len(training) <= 64:
        raise ValueError("INDUCTIVE_TRAINING_BUDGET")
    rows, seen, key, output_type = [], set(), None, None
    for row in training:
        if type(row) is not dict or set(row) != {"input", "expected"}:
            raise ValueError("INDUCTIVE_TRAINING_SCHEMA")
        inputs = row["input"]
        if type(inputs) is not dict or len(inputs) != 1:
            raise ValueError("INDUCTIVE_UNIVARIATE_INPUT_REQUIRED")
        current = next(iter(inputs))
        if type(current) is not str or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,31}", current):
            raise ValueError("INDUCTIVE_INPUT_KEY")
        key = current if key is None else key
        if current != key:
            raise ValueError("INDUCTIVE_INPUT_SIGNATURE_DRIFT")
        x, y = inputs[key], row["expected"]
        if type(x) is not int or abs(x) > MAX_ABS_INPUT:
            raise ValueError("INDUCTIVE_BOUNDED_INTEGER_INPUT_REQUIRED")
        if type(y) not in {int, bool} or type(y) is int and abs(y) > MAX_ABS_OUTPUT:
            raise ValueError("INDUCTIVE_BOUNDED_INTEGER_OR_BOOL_OUTPUT_REQUIRED")
        current_type = type(y)
        output_type = current_type if output_type is None else output_type
        if current_type is not output_type:
            raise ValueError("INDUCTIVE_OUTPUT_SIGNATURE_DRIFT")
        if x in seen:
            raise ValueError("INDUCTIVE_DUPLICATE_INPUT")
        seen.add(x)
        rows.append({"input": {key: x}, "expected": y})
    return rows, key, "bool" if output_type is bool else "int"


def _safe_int(values):
    return all(type(value) is int and abs(value) <= MAX_ABS_OUTPUT for value in values)


def _safe_bool(values):
    return all(type(value) is bool for value in values)


def _search(training, allowed=PRIMITIVE_SET, max_nodes=MAX_NODES, max_states=MAX_STATES):
    rows, key, target_type = _training(training)
    allowed = frozenset(allowed)
    if not allowed or not allowed <= PRIMITIVE_SET:
        raise ValueError("INDUCTIVE_PRIMITIVE_SET")
    if type(max_nodes) is not int or not 1 <= max_nodes <= MAX_NODES:
        raise ValueError("INDUCTIVE_NODE_BUDGET")
    if type(max_states) is not int or not 1 <= max_states <= MAX_STATES:
        raise ValueError("INDUCTIVE_STATE_BUDGET")
    xs = tuple(row["input"][key] for row in rows)
    target = tuple(row["expected"] for row in rows)
    tables = {"int": {size: {} for size in range(1, max_nodes + 1)},
              "bool": {size: {} for size in range(1, max_nodes + 1)}}
    states = 0

    def add(kind, size, behavior, expression, primitives):
        nonlocal states
        valid = _safe_int(behavior) if kind == "int" else _safe_bool(behavior)
        if not valid or behavior in tables[kind][size]:
            return
        if states >= max_states:
            raise OverflowError("INDUCTIVE_SEMANTIC_STATE_BUDGET")
        tables[kind][size][behavior] = {
            "expression": expression,
            "primitives": tuple(p for p in PRIMITIVE_ORDER if p in primitives),
            "nodes": size,
        }
        states += 1

    if "var" in allowed:
        add("int", 1, xs, "inputs[" + repr(key) + "]", {"var"})
    if "const" in allowed:
        for constant in CONSTANTS:
            add("int", 1, tuple(constant for _ in rows), str(constant), {"const"})

    for size in range(1, max_nodes + 1):
        match = tables[target_type][size].get(target)
        if match is not None:
            return {**match, "key": key, "semantic_states": states,
                    "training_count": len(rows), "training_digest": _sha(
                        json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=True))}
        if size == max_nodes:
            break
        total = size + 1
        if "neg" in allowed:
            for behavior, item in tuple(tables["int"][total - 1].items()):
                add("int", total, tuple(-value for value in behavior),
                    "(-" + item["expression"] + ")", set(item["primitives"]) | {"neg"})

        for left_size in range(1, total - 1):
            right_size = total - 1 - left_size
            if right_size < 1:
                continue
            for left_behavior, left in tuple(tables["int"][left_size].items()):
                for right_behavior, right in tuple(tables["int"][right_size].items()):
                    base_primitives = set(left["primitives"]) | set(right["primitives"])
                    for name, symbol, function in (
                        ("add", "+", lambda a, b: a + b),
                        ("sub", "-", lambda a, b: a - b),
                        ("mul", "*", lambda a, b: a * b),
                    ):
                        if name in allowed:
                            add("int", total,
                                tuple(function(a, b) for a, b in zip(left_behavior, right_behavior)),
                                "(" + left["expression"] + " " + symbol + " " + right["expression"] + ")",
                                base_primitives | {name})
                    if "mod" in allowed and all(value != 0 for value in right_behavior):
                        add("int", total,
                            tuple(a % b for a, b in zip(left_behavior, right_behavior)),
                            "(" + left["expression"] + " % " + right["expression"] + ")",
                            base_primitives | {"mod"})
                    for name, symbol, function in (
                        ("lt", "<", lambda a, b: a < b),
                        ("le", "<=", lambda a, b: a <= b),
                        ("eq", "==", lambda a, b: a == b),
                    ):
                        if name in allowed:
                            add("bool", total,
                                tuple(function(a, b) for a, b in zip(left_behavior, right_behavior)),
                                "(" + left["expression"] + " " + symbol + " " + right["expression"] + ")",
                                base_primitives | {name})

        if "if" in allowed:
            for condition_size in range(1, total - 2):
                for then_size in reversed(range(1, total - 1 - condition_size)):
                    else_size = total - 1 - condition_size - then_size
                    if else_size < 1:
                        continue
                    for condition_behavior, condition in tuple(tables["bool"][condition_size].items()):
                        for then_behavior, then in tuple(tables["int"][then_size].items()):
                            for else_behavior, other in tuple(tables["int"][else_size].items()):
                                add("int", total,
                                    tuple(t if c else e for c, t, e in
                                          zip(condition_behavior, then_behavior, else_behavior)),
                                    "(" + then["expression"] + " if " + condition["expression"]
                                    + " else " + other["expression"] + ")",
                                    set(condition["primitives"]) | set(then["primitives"])
                                    | set(other["primitives"]) | {"if"})
    return None


def derive_profile(training):
    """Infer the smallest exact primitive profile from training behavior only."""
    try:
        selected = _search(training)
    except (ValueError, OverflowError):
        return None
    if selected is None:
        return None
    return {
        "grammar_version": GRAMMAR_VERSION,
        "primitive_set": list(selected["primitives"]),
        "max_nodes": selected["nodes"],
        "constants": list(CONSTANTS),
    }


def _checked_profile(profile):
    if type(profile) is not dict or set(profile) != {"grammar_version", "primitive_set", "max_nodes", "constants"}:
        raise ValueError("INDUCTIVE_PROFILE_SCHEMA")
    primitives = profile["primitive_set"]
    if (profile["grammar_version"] != GRAMMAR_VERSION or type(primitives) is not list
            or not primitives or len(primitives) != len(set(primitives))
            or any(p not in PRIMITIVE_SET for p in primitives)
            or primitives != [p for p in PRIMITIVE_ORDER if p in primitives]
            or type(profile["max_nodes"]) is not int or not 1 <= profile["max_nodes"] <= MAX_NODES
            or profile["constants"] != list(CONSTANTS)):
        raise ValueError("INDUCTIVE_PROFILE_MISMATCH")
    return {"grammar_version": GRAMMAR_VERSION, "primitive_set": list(primitives),
            "max_nodes": profile["max_nodes"], "constants": list(CONSTANTS)}


def emit(profile):
    checked = _checked_profile(profile)
    # The emitted artifact freezes the kernel-derived language profile. The
    # reviewed semantic enumerator above is the generic host harness.
    return (
        '"""Frozen bounded inductive runtime profile; no task labels or supplied code."""\n'
        + "PROFILE = " + repr(checked) + "\n"
        + "def profile():\n    return PROFILE.copy()\n"
    )


def build_candidate(training):
    profile = derive_profile(training)
    if profile is None:
        return None
    source = emit(profile)
    return {"schema": SCHEMA, "profile": profile, "source": source,
            "source_sha256": _sha(source)}


def validate_candidate(candidate):
    if type(candidate) is not dict or set(candidate) != {"schema", "profile", "source", "source_sha256"}:
        raise ValueError("INDUCTIVE_CANDIDATE_SCHEMA")
    if candidate["schema"] != SCHEMA or type(candidate["source"]) is not str:
        raise ValueError("INDUCTIVE_CANDIDATE_SCHEMA")
    expected = emit(candidate["profile"])
    if candidate["source"] != expected or candidate["source_sha256"] != _sha(expected):
        raise ValueError("INDUCTIVE_CANDIDATE_SOURCE_MISMATCH")


def synthesize(candidate, training):
    """Synthesize a concrete program using only the frozen derived profile."""
    validate_candidate(candidate)
    profile = _checked_profile(candidate["profile"])
    try:
        selected = _search(training, allowed=profile["primitive_set"], max_nodes=profile["max_nodes"])
    except (ValueError, OverflowError) as exc:
        return {**_withhold(str(exc)), "mechanism_source_sha256": candidate["source_sha256"]}
    if selected is None:
        return {**_withhold("INDUCTIVE_PROFILE_NO_EXACT_TRAINING_PROGRAM"),
                "mechanism_source_sha256": candidate["source_sha256"]}
    source = "def solve(component_id, program_id, inputs):\n    return " + selected["expression"] + "\n"
    compile(source, "<inductive-native-program>", "exec")
    return {
        "status": "SOURCE_CANDIDATE",
        "source": source,
        "source_sha256": _sha(source),
        "compiled": True,
        "selected": {
            "profile": "INDUCTIVE_TYPED_EXPRESSION",
            "expression": selected["expression"],
            "primitives": list(selected["primitives"]),
            "nodes": selected["nodes"],
            "semantic_states": selected["semantic_states"],
            "key": selected["key"],
        },
        "grammar_stage": GRAMMAR_VERSION,
        "training_digest": selected["training_digest"],
        "synthesis_inputs": "TRAINING_ONLY",
        "origin": "KERNEL_SELECTED_STRUCTURE_FROM_HOST_SAFE_PRIMITIVE_UNIVERSE",
        "mechanism_source_sha256": candidate["source_sha256"],
        "automatic_canonical_promotion": False,
    }


__all__ = ["SCHEMA", "GRAMMAR_VERSION", "derive_profile", "emit", "build_candidate",
           "validate_candidate", "synthesize"]
