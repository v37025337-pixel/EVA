"""Bounded second-cycle source grammar derived from frozen V2 deficits.

The baseline was frozen before this module existed.  This extension deliberately
covers only families that are identifiable from the supplied TRAINING examples:
bitwise integer programs and small one-variable integer polynomials.  It does not
add a conditional/compare grammar for the frozen ``not_gate`` deficit because that
training split contains no positive example and therefore does not identify the
hidden x == 0 branch.

This remains host-authored bounded grammar.  YADO selects a concrete program from
training behavior only; validation/holdout labels are never accepted here.
"""
from __future__ import annotations

import ast
import hashlib
import itertools
import json
from typing import Any, Iterable

MAX_ABS_INPUT = 10**6
MAX_ABS_OUTPUT = 10**9
COEFFICIENTS = tuple(range(-8, 9))
MAX_POLYNOMIAL_DEGREE = 3


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha(value: Any) -> str:
    if not isinstance(value, str):
        value = _canon(value)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _training_contract(training: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    rows = list(training)
    if not 3 <= len(rows) <= 64:
        raise ValueError("V2_TRAINING_BUDGET")
    keys: list[str] | None = None
    seen = set()
    clean: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"input", "expected"}:
            raise ValueError("V2_TRAINING_SCHEMA")
        inputs = row["input"]
        if not isinstance(inputs, dict) or not 1 <= len(inputs) <= 3:
            raise ValueError("V2_INPUT_ARITY")
        current = sorted(inputs)
        keys = current if keys is None else keys
        if current != keys:
            raise ValueError("V2_INPUT_SIGNATURE_DRIFT")
        if any(type(inputs[key]) is not int or abs(inputs[key]) > MAX_ABS_INPUT for key in keys):
            raise ValueError("V2_INTEGER_INPUTS_ONLY")
        expected = row["expected"]
        if type(expected) not in {int, bool}:
            raise ValueError("V2_INTEGER_OR_BOOL_OUTPUT_ONLY")
        if type(expected) is int and abs(expected) > MAX_ABS_OUTPUT:
            raise ValueError("V2_OUTPUT_BUDGET")
        marker = tuple(inputs[key] for key in keys)
        if marker in seen:
            raise ValueError("V2_DUPLICATE_INPUT")
        seen.add(marker)
        clean.append({"input": {key: inputs[key] for key in keys}, "expected": expected})
    return clean, list(keys or [])


def _equivalent(left: Any, right: Any) -> bool:
    if isinstance(left, bool) != isinstance(right, bool):
        return False
    return left == right


def _expression_behavior(expression: str, rows: list[dict[str, Any]]) -> tuple[Any, ...] | None:
    try:
        code = compile(expression, "<successor-v2-expression>", "eval")
        values = []
        for row in rows:
            value = eval(code, {"__builtins__": {}}, {"inputs": row["input"]})
            if type(value) not in {int, bool}:
                return None
            if type(value) is int and abs(value) > MAX_ABS_OUTPUT:
                return None
            values.append(value)
        return tuple(values)
    except (ArithmeticError, ValueError, OverflowError, TypeError, KeyError):
        return None


def _target_matches(values: tuple[Any, ...] | None, rows: list[dict[str, Any]]) -> bool:
    return values is not None and len(values) == len(rows) and all(
        _equivalent(value, row["expected"]) for value, row in zip(values, rows)
    )


def _bitwise_templates(keys: list[str]) -> list[dict[str, str]]:
    q = {key: f"inputs[{key!r}]" for key in keys}
    out: list[dict[str, str]] = []
    for key in keys:
        x = q[key]
        out.extend((
            {"template": "CLEAR_LSB", "expression": f"({x} & ({x} - 1))"},
            {"template": "LOW_BIT", "expression": f"({x} & 1)"},
            {"template": "OR_ONE", "expression": f"({x} | 1)"},
            {"template": "XOR_ONE", "expression": f"({x} ^ 1)"},
            {"template": "SHIFT_LEFT_ONE", "expression": f"({x} << 1)"},
            {"template": "SHIFT_RIGHT_ONE", "expression": f"({x} >> 1)"},
            {"template": "INVERT", "expression": f"(~{x})"},
        ))
    for left_key in keys:
        for right_key in keys:
            if left_key == right_key:
                continue
            left, right = q[left_key], q[right_key]
            prefix = f"{left_key}:{right_key}"
            out.extend((
                {"template": f"AND:{prefix}", "expression": f"({left} & {right})"},
                {"template": f"OR:{prefix}", "expression": f"({left} | {right})"},
                {"template": f"XOR:{prefix}", "expression": f"({left} ^ {right})"},
                {"template": f"LSHIFT:{prefix}", "expression": f"({left} << {right})"},
                {"template": f"RSHIFT:{prefix}", "expression": f"({left} >> {right})"},
                {"template": f"SET_BIT:{prefix}", "expression": f"({left} | (1 << {right}))"},
                {"template": f"FLIP_BIT:{prefix}", "expression": f"({left} ^ (1 << {right}))"},
                {"template": f"CLEAR_BIT:{prefix}", "expression": f"({left} & ~(1 << {right}))"},
                {"template": f"EXTRACT_BIT:{prefix}", "expression": f"(({left} >> {right}) & 1)"},
                {"template": f"BIT_IS_ONE:{prefix}", "expression": f"((({left} >> {right}) & 1) == 1)"},
                {"template": f"BIT_IS_ZERO:{prefix}", "expression": f"((({left} >> {right}) & 1) == 0)"},
            ))
    # Stable, complexity-biased order independent of target/holdout behavior.
    out.sort(key=lambda row: (len(row["expression"]), row["template"], row["expression"]))
    return out


def _select_bitwise(rows: list[dict[str, Any]], keys: list[str]) -> dict[str, Any] | None:
    attempts = 0
    for template in _bitwise_templates(keys):
        attempts += 1
        behavior = _expression_behavior(template["expression"], rows)
        if _target_matches(behavior, rows):
            return {
                "profile": "BITWISE_TEMPLATE_V2",
                "template": template["template"],
                "expression": template["expression"],
                "search_states": attempts,
            }
    return None


def _polynomial_expression(key: str, coefficients: tuple[int, ...]) -> str:
    x = f"inputs[{key!r}]"
    terms: list[str] = []
    for power, coefficient in enumerate(coefficients):
        if coefficient == 0:
            continue
        if power == 0:
            atom = "1"
        elif power == 1:
            atom = x
        else:
            atom = f"({x} ** {power})"
        if power == 0:
            terms.append(str(coefficient))
        elif coefficient == 1:
            terms.append(atom)
        elif coefficient == -1:
            terms.append(f"(-{atom})")
        else:
            terms.append(f"({coefficient} * {atom})")
    return " + ".join(terms) if terms else "0"


def _select_polynomial(rows: list[dict[str, Any]], keys: list[str]) -> dict[str, Any] | None:
    if len(keys) != 1 or any(type(row["expected"]) is bool for row in rows):
        return None
    key = keys[0]
    xs = [row["input"][key] for row in rows]
    target = [row["expected"] for row in rows]
    attempts = 0
    for degree in range(MAX_POLYNOMIAL_DEGREE + 1):
        candidates = itertools.product(COEFFICIENTS, repeat=degree + 1)
        for coefficients in candidates:
            if degree > 0 and coefficients[-1] == 0:
                continue
            attempts += 1
            values = []
            valid = True
            for x in xs:
                value = 0
                for coefficient in reversed(coefficients):
                    value = value * x + coefficient
                    if abs(value) > MAX_ABS_OUTPUT:
                        valid = False
                        break
                if not valid:
                    break
                values.append(value)
            if valid and all(_equivalent(value, expected) for value, expected in zip(values, target)):
                expression = _polynomial_expression(key, coefficients)
                return {
                    "profile": "INTEGER_POLYNOMIAL_DEGREE3_V2",
                    "template": f"DEGREE_{degree}",
                    "expression": expression,
                    "coefficients": list(coefficients),
                    "search_states": attempts,
                }
    return None


def select_expression_v2(training: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Select a V2 program from TRAINING ONLY; hidden labels are not an input."""
    rows, keys = _training_contract(training)
    attempts: list[dict[str, Any]] = []

    bitwise = _select_bitwise(rows, keys)
    attempts.append({"profile": "BITWISE_TEMPLATE_V2", "matched": bitwise is not None})
    if bitwise is not None:
        selected = bitwise
    else:
        polynomial = _select_polynomial(rows, keys)
        attempts.append({"profile": "INTEGER_POLYNOMIAL_DEGREE3_V2", "matched": polynomial is not None})
        if polynomial is None:
            raise ValueError("NO_BOUNDED_V2_PROGRAM_FITS_TRAINING")
        selected = polynomial

    program = {
        **selected,
        "keys": keys,
        "expression_digest": _sha(selected["expression"]),
        "training_count": len(rows),
        "selection_basis": "FIRST_BOUNDED_PROFILE_WITH_EXACT_TYPED_TRAINING_FIT",
        "training_only": True,
        "holdout_access": False,
    }
    return {"program": program, "attempts": attempts}


def synthesize_candidate_v2(training: Iterable[dict[str, Any]]) -> dict[str, Any]:
    frozen_training = list(training)
    selected = select_expression_v2(frozen_training)
    program = selected["program"]
    source = (
        "def solve(component_id, program_id, inputs):\n"
        f"    return {program['expression']}\n"
    )
    compile(source, "<successor-generalized-v2-candidate>", "exec")
    return {
        "source": source,
        "source_sha256": _sha(source),
        "compiled": True,
        "selected": program,
        "profile_attempts": selected["attempts"],
        "grammar_stage": "SUCCESSOR_GENERALIZED_SOURCE_V2",
        "training_digest": _sha(frozen_training),
        "synthesis_inputs": "TRAINING_ONLY",
        "origin": "YADO_SELECTION_FROM_HOST_BOUNDED_SECOND_CYCLE_GRAMMAR",
        "automatic_canonical_promotion": False,
    }


def synthesize_repair_v2(source: str, function_name: str,
                         train_examples: Iterable[tuple[tuple[Any, ...], Any]]) -> dict[str, Any]:
    tree = ast.parse(source)
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == function_name]
    if len(functions) != 1:
        raise ValueError("V2_REPAIR_FUNCTION_NOT_UNIQUE")
    fn = functions[0]
    if fn.args.vararg or fn.args.kwarg or fn.args.kwonlyargs or fn.args.posonlyargs:
        raise ValueError("V2_REPAIR_ARGUMENT_CONTRACT")
    keys = [arg.arg for arg in fn.args.args]
    if not 1 <= len(keys) <= 3 or len(set(keys)) != len(keys):
        raise ValueError("V2_REPAIR_ARITY")
    cases = []
    for args, expected in train_examples:
        args = tuple(args)
        if len(args) != len(keys):
            raise ValueError("V2_REPAIR_EXAMPLE_ARITY")
        cases.append({"input": dict(zip(keys, args)), "expected": expected})
    selected = select_expression_v2(cases)
    program = selected["program"]
    expression = program["expression"]
    for key in keys:
        expression = expression.replace(f"inputs[{key!r}]", key)
    emitted = f"def {function_name}({', '.join(keys)}):\n    return {expression}\n"
    compile(emitted, "<successor-generalized-v2-repair>", "exec")
    return {
        "status": "PASS_REPAIR",
        "repair_mode": "SUCCESSOR_GENERALIZED_FALLBACK_V2",
        "source": emitted,
        "source_sha256": _sha(emitted),
        "selected": program,
        "profile_attempts": selected["attempts"],
        "search_nodes": program["search_states"],
        "training_only": True,
        "automatic_canonical_promotion": False,
    }


__all__ = [
    "select_expression_v2",
    "synthesize_candidate_v2",
    "synthesize_repair_v2",
]
