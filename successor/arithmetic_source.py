"""Bounded arithmetic source synthesis derived from measured real-code deficits.

This is a host-authored *grammar extension*, not autonomous invention of Python.
YADO selects the smallest grammar profile and the concrete expression using only
training input/output examples.  Validation and holdout labels are not accepted by
this module.  Emission is limited to one pure expression over one or two integer
inputs and a tiny fixed constant/operator vocabulary.
"""
from __future__ import annotations

from dataclasses import dataclass
import ast
import hashlib
import json
from typing import Any, Iterable

CONSTANTS = (-2, -1, 0, 1, 2)
MAX_ABS_VALUE = 10**9
MAX_STATES = 12000
PROFILES = (
    {"id": "ARITH_DEPTH1_V1", "max_depth": 1, "ops": ("add", "sub", "mul")},
    {"id": "ARITH_DEPTH2_V1", "max_depth": 2, "ops": ("add", "sub", "mul")},
    {"id": "ARITH_DEPTH2_FLOORDIV_V1", "max_depth": 2,
     "ops": ("add", "sub", "mul", "floordiv")},
)


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha(value: Any) -> str:
    if not isinstance(value, str):
        value = _canon(value)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Expr:
    op: str
    left: Any = None
    right: Any = None
    depth: int = 0
    text: str = ""


def _value(expr: Expr, env: dict[str, int]) -> int:
    if expr.op == "var":
        return env[expr.left]
    if expr.op == "const":
        return expr.left
    left = _value(expr.left, env)
    right = _value(expr.right, env)
    if expr.op == "add":
        value = left + right
    elif expr.op == "sub":
        value = left - right
    elif expr.op == "mul":
        value = left * right
    elif expr.op == "floordiv":
        if right == 0:
            raise ZeroDivisionError
        value = left // right
    else:
        raise ValueError("UNKNOWN_ARITHMETIC_OPERATOR")
    if type(value) is not int or abs(value) > MAX_ABS_VALUE:
        raise OverflowError("ARITHMETIC_VALUE_BUDGET")
    return value


def _training_contract(training: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    rows = list(training)
    if not 3 <= len(rows) <= 64:
        raise ValueError("ARITHMETIC_TRAINING_BUDGET")
    keys: list[str] | None = None
    seen = set()
    clean = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"input", "expected"}:
            raise ValueError("ARITHMETIC_TRAINING_SCHEMA")
        inputs = row["input"]
        if not isinstance(inputs, dict) or not 1 <= len(inputs) <= 2:
            raise ValueError("ARITHMETIC_INPUT_ARITY")
        current = sorted(inputs)
        keys = current if keys is None else keys
        if current != keys:
            raise ValueError("ARITHMETIC_INPUT_SIGNATURE_DRIFT")
        if any(type(inputs[k]) is not int or abs(inputs[k]) > 10**6 for k in keys):
            raise ValueError("ARITHMETIC_INTEGER_INPUTS_ONLY")
        if type(row["expected"]) is not int or abs(row["expected"]) > 10**6:
            raise ValueError("ARITHMETIC_INTEGER_OUTPUTS_ONLY")
        marker = tuple(inputs[k] for k in keys)
        if marker in seen:
            raise ValueError("ARITHMETIC_DUPLICATE_INPUT")
        seen.add(marker)
        clean.append({"input": {k: inputs[k] for k in keys}, "expected": row["expected"]})
    return clean, list(keys or [])


def applicable(training: Iterable[dict[str, Any]]) -> bool:
    try:
        _training_contract(training)
        return True
    except (TypeError, ValueError):
        return False


def _behavior(expr: Expr, rows: list[dict[str, Any]], keys: list[str]) -> tuple[int, ...] | None:
    values = []
    try:
        for row in rows:
            values.append(_value(expr, {k: row["input"][k] for k in keys}))
    except (ZeroDivisionError, OverflowError, ValueError):
        return None
    return tuple(values)


def _expr_key(expr: Expr) -> tuple[int, int, str]:
    return (expr.depth, len(expr.text), expr.text)


def _synthesize_profile(rows: list[dict[str, Any]], keys: list[str], profile: dict[str, Any]) -> dict[str, Any] | None:
    target = tuple(row["expected"] for row in rows)
    states: dict[tuple[int, ...], Expr] = {}

    leaves = [Expr("var", key, depth=0, text=f"inputs[{key!r}]") for key in keys]
    leaves += [Expr("const", value, depth=0, text=repr(value)) for value in CONSTANTS]
    for expr in sorted(leaves, key=_expr_key):
        behavior = _behavior(expr, rows, keys)
        if behavior is not None and behavior not in states:
            states[behavior] = expr
    if target in states:
        selected = states[target]
        return {"expr": selected, "search_states": len(states)}

    symbols = {"add": "+", "sub": "-", "mul": "*", "floordiv": "//"}
    for depth in range(1, int(profile["max_depth"]) + 1):
        snapshot = sorted(states.values(), key=_expr_key)
        additions: dict[tuple[int, ...], Expr] = {}
        for left in snapshot:
            for right in snapshot:
                if max(left.depth, right.depth) != depth - 1:
                    continue
                for op in profile["ops"]:
                    # Addition and multiplication are commutative; generate one ordering.
                    if op in {"add", "mul"} and right.text < left.text:
                        continue
                    expr = Expr(op, left, right, depth,
                                f"({left.text} {symbols[op]} {right.text})")
                    behavior = _behavior(expr, rows, keys)
                    if behavior is None or behavior in states or behavior in additions:
                        continue
                    additions[behavior] = expr
                    if behavior == target:
                        selected = expr
                        return {"expr": selected,
                                "search_states": len(states) + len(additions)}
                    if len(states) + len(additions) >= MAX_STATES:
                        break
                if len(states) + len(additions) >= MAX_STATES:
                    break
            if len(states) + len(additions) >= MAX_STATES:
                break
        for behavior, expr in sorted(additions.items(), key=lambda item: _expr_key(item[1])):
            states.setdefault(behavior, expr)
        if len(states) >= MAX_STATES:
            break
    return None


def select_expression(training: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Select the smallest successful profile and concrete program from TRAINING ONLY."""
    rows, keys = _training_contract(training)
    attempts = []
    for profile in PROFILES:
        found = _synthesize_profile(rows, keys, profile)
        attempts.append({"profile": profile["id"], "matched": found is not None,
                         "search_states": None if found is None else found["search_states"]})
        if found is None:
            continue
        expr = found["expr"]
        program = {
            "profile": profile["id"],
            "max_depth": profile["max_depth"],
            "operators": list(profile["ops"]),
            "keys": keys,
            "expression": expr.text,
            "expression_digest": _sha(expr.text),
            "search_states": found["search_states"],
            "training_count": len(rows),
            "selection_basis": "FIRST_MINIMAL_PROFILE_WITH_EXACT_TRAINING_FIT",
            "training_only": True,
        }
        return {"program": program, "attempts": attempts}
    raise ValueError("NO_BOUNDED_ARITHMETIC_PROGRAM_FITS_TRAINING")


def synthesize_candidate(training: Iterable[dict[str, Any]]) -> dict[str, Any]:
    selected = select_expression(training)
    program = selected["program"]
    source = (
        "def solve(component_id, program_id, inputs):\n"
        f"    return {program['expression']}\n"
    )
    compile(source, "<successor-arithmetic-candidate>", "exec")
    return {
        "source": source,
        "source_sha256": _sha(source),
        "compiled": True,
        "selected": program,
        "profile_attempts": selected["attempts"],
        "grammar_stage": "SUCCESSOR_ARITHMETIC_V1",
        "training_digest": _sha(list(training)),
        "synthesis_inputs": "TRAINING_ONLY",
        "origin": "YADO_SELECTION_FROM_BOUNDED_SUCCESSOR_ARITHMETIC_GRAMMAR",
        "automatic_canonical_promotion": False,
    }


def synthesize_repair(source: str, function_name: str,
                      train_examples: Iterable[tuple[tuple[Any, ...], Any]]) -> dict[str, Any]:
    """Behavioral fallback for a failed repair; source structure supplies argument names only."""
    tree = ast.parse(source)
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == function_name]
    if len(functions) != 1:
        raise ValueError("ARITHMETIC_REPAIR_FUNCTION_NOT_UNIQUE")
    fn = functions[0]
    if fn.args.vararg or fn.args.kwarg or fn.args.kwonlyargs or fn.args.posonlyargs:
        raise ValueError("ARITHMETIC_REPAIR_ARGUMENT_CONTRACT")
    keys = [arg.arg for arg in fn.args.args]
    if not 1 <= len(keys) <= 2 or len(set(keys)) != len(keys):
        raise ValueError("ARITHMETIC_REPAIR_ARITY")
    cases = []
    for args, expected in train_examples:
        args = tuple(args)
        if len(args) != len(keys):
            raise ValueError("ARITHMETIC_REPAIR_EXAMPLE_ARITY")
        cases.append({"input": dict(zip(keys, args)), "expected": expected})
    selected = select_expression(cases)
    program = selected["program"]
    expression = program["expression"]
    for key in keys:
        expression = expression.replace(f"inputs[{key!r}]", key)
    emitted = f"def {function_name}({', '.join(keys)}):\n    return {expression}\n"
    compile(emitted, "<successor-arithmetic-repair>", "exec")
    return {
        "status": "PASS_REPAIR",
        "repair_mode": "SUCCESSOR_ARITHMETIC_FALLBACK_V1",
        "source": emitted,
        "source_sha256": _sha(emitted),
        "selected": program,
        "profile_attempts": selected["attempts"],
        "search_nodes": program["search_states"],
        "training_only": True,
        "automatic_canonical_promotion": False,
    }


__all__ = [
    "PROFILES", "applicable", "select_expression", "synthesize_candidate", "synthesize_repair"
]
