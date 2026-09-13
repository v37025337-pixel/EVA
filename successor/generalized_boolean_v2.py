"""Training-identifiable boolean comparison grammar for second-cycle transfer.

This extension is intentionally unavailable when the training partition contains
only one boolean class.  That prevents the frozen ``not_gate`` holdout from being
special-cased: its positive branch is absent from training.  When both True and
False are observed, YADO may select a small generic comparison/bitwise predicate
using TRAINING labels only.
"""
from __future__ import annotations

import ast
import hashlib
import json
from typing import Any, Iterable

MAX_ABS_INPUT = 10**6


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha(value: Any) -> str:
    if not isinstance(value, str):
        value = _canon(value)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _contract(training: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    rows = list(training)
    if not 3 <= len(rows) <= 64:
        raise ValueError("BOOLEAN_V2_TRAINING_BUDGET")
    keys: list[str] | None = None
    clean: list[dict[str, Any]] = []
    seen = set()
    classes = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"input", "expected"}:
            raise ValueError("BOOLEAN_V2_TRAINING_SCHEMA")
        inputs = row["input"]
        if not isinstance(inputs, dict) or not 1 <= len(inputs) <= 3:
            raise ValueError("BOOLEAN_V2_INPUT_ARITY")
        current = sorted(inputs)
        keys = current if keys is None else keys
        if current != keys:
            raise ValueError("BOOLEAN_V2_INPUT_SIGNATURE_DRIFT")
        if any(type(inputs[key]) is not int or abs(inputs[key]) > MAX_ABS_INPUT for key in keys):
            raise ValueError("BOOLEAN_V2_INTEGER_INPUTS_ONLY")
        expected = row["expected"]
        if type(expected) is not bool:
            raise ValueError("BOOLEAN_V2_BOOL_OUTPUTS_ONLY")
        marker = tuple(inputs[key] for key in keys)
        if marker in seen:
            raise ValueError("BOOLEAN_V2_DUPLICATE_INPUT")
        seen.add(marker)
        classes.add(expected)
        clean.append({"input": {key: inputs[key] for key in keys}, "expected": expected})
    if classes != {False, True}:
        raise ValueError("BOOLEAN_V2_REQUIRES_BOTH_TRAINING_CLASSES")
    return clean, list(keys or [])


def _templates(keys: list[str]) -> list[dict[str, str]]:
    q = {key: f"inputs[{key!r}]" for key in keys}
    out: list[dict[str, str]] = []
    for key in keys:
        x = q[key]
        out.extend((
            {"template": f"EQ_ZERO:{key}", "expression": f"({x} == 0)"},
            {"template": f"NE_ZERO:{key}", "expression": f"({x} != 0)"},
            {"template": f"LT_ZERO:{key}", "expression": f"({x} < 0)"},
            {"template": f"GT_ZERO:{key}", "expression": f"({x} > 0)"},
            {"template": f"LE_ZERO:{key}", "expression": f"({x} <= 0)"},
            {"template": f"GE_ZERO:{key}", "expression": f"({x} >= 0)"},
            {"template": f"ODD:{key}", "expression": f"(({x} & 1) == 1)"},
            {"template": f"EVEN:{key}", "expression": f"(({x} & 1) == 0)"},
            {"template": f"EVEN_SHIFT:{key}", "expression": f"((({x} >> 1) << 1) == {x})"},
        ))
    for left_key in keys:
        for right_key in keys:
            if left_key == right_key:
                continue
            left, right = q[left_key], q[right_key]
            suffix = f"{left_key}:{right_key}"
            out.extend((
                {"template": f"EQ:{suffix}", "expression": f"({left} == {right})"},
                {"template": f"NE:{suffix}", "expression": f"({left} != {right})"},
                {"template": f"LT:{suffix}", "expression": f"({left} < {right})"},
                {"template": f"GT:{suffix}", "expression": f"({left} > {right})"},
                {"template": f"XOR_LT_ZERO:{suffix}", "expression": f"(({left} ^ {right}) < 0)"},
                {"template": f"XOR_GE_ZERO:{suffix}", "expression": f"(({left} ^ {right}) >= 0)"},
                {"template": f"AND_EQ_ZERO:{suffix}", "expression": f"(({left} & {right}) == 0)"},
                {"template": f"AND_NE_ZERO:{suffix}", "expression": f"(({left} & {right}) != 0)"},
            ))
    out.sort(key=lambda row: (len(row["expression"]), row["template"], row["expression"]))
    return out


def _behavior(expression: str, rows: list[dict[str, Any]]) -> tuple[bool, ...] | None:
    try:
        code = compile(expression, "<successor-boolean-v2-expression>", "eval")
        values = []
        for row in rows:
            value = eval(code, {"__builtins__": {}}, {"inputs": row["input"]})
            if type(value) is not bool:
                return None
            values.append(value)
        return tuple(values)
    except (ArithmeticError, ValueError, OverflowError, TypeError, KeyError):
        return None


def select_boolean_expression_v2(training: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows, keys = _contract(training)
    target = tuple(row["expected"] for row in rows)
    for index, template in enumerate(_templates(keys), start=1):
        if _behavior(template["expression"], rows) == target:
            program = {
                "profile": "BOOLEAN_COMPARISON_IDENTIFIABLE_V2",
                "template": template["template"],
                "expression": template["expression"],
                "keys": keys,
                "expression_digest": _sha(template["expression"]),
                "search_states": index,
                "training_count": len(rows),
                "selection_basis": "FIRST_GENERIC_PREDICATE_WITH_EXACT_TWO_CLASS_TRAINING_FIT",
                "training_only": True,
                "holdout_access": False,
                "requires_both_training_classes": True,
            }
            return {"program": program}
    raise ValueError("NO_IDENTIFIABLE_BOOLEAN_V2_PROGRAM_FITS_TRAINING")


def synthesize_boolean_candidate_v2(training: Iterable[dict[str, Any]]) -> dict[str, Any]:
    frozen = list(training)
    selected = select_boolean_expression_v2(frozen)["program"]
    source = (
        "def solve(component_id, program_id, inputs):\n"
        f"    return {selected['expression']}\n"
    )
    compile(source, "<successor-boolean-v2-candidate>", "exec")
    return {
        "source": source,
        "source_sha256": _sha(source),
        "compiled": True,
        "selected": selected,
        "profile_attempts": [{"profile": "BOOLEAN_COMPARISON_IDENTIFIABLE_V2", "matched": True}],
        "grammar_stage": "SUCCESSOR_BOOLEAN_IDENTIFIABLE_V2",
        "training_digest": _sha(frozen),
        "synthesis_inputs": "TRAINING_ONLY",
        "origin": "YADO_SELECTION_FROM_HOST_BOUNDED_IDENTIFIABLE_BOOLEAN_GRAMMAR",
        "automatic_canonical_promotion": False,
    }


def synthesize_boolean_repair_v2(source: str, function_name: str,
                                 train_examples: Iterable[tuple[tuple[Any, ...], Any]]) -> dict[str, Any]:
    tree = ast.parse(source)
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == function_name]
    if len(functions) != 1:
        raise ValueError("BOOLEAN_V2_REPAIR_FUNCTION_NOT_UNIQUE")
    fn = functions[0]
    if fn.args.vararg or fn.args.kwarg or fn.args.kwonlyargs or fn.args.posonlyargs:
        raise ValueError("BOOLEAN_V2_REPAIR_ARGUMENT_CONTRACT")
    keys = [arg.arg for arg in fn.args.args]
    if not 1 <= len(keys) <= 3 or len(set(keys)) != len(keys):
        raise ValueError("BOOLEAN_V2_REPAIR_ARITY")
    cases = []
    for args, expected in train_examples:
        args = tuple(args)
        if len(args) != len(keys):
            raise ValueError("BOOLEAN_V2_REPAIR_EXAMPLE_ARITY")
        cases.append({"input": dict(zip(keys, args)), "expected": expected})
    selected = select_boolean_expression_v2(cases)["program"]
    expression = selected["expression"]
    for key in keys:
        expression = expression.replace(f"inputs[{key!r}]", key)
    emitted = f"def {function_name}({', '.join(keys)}):\n    return {expression}\n"
    compile(emitted, "<successor-boolean-v2-repair>", "exec")
    return {
        "status": "PASS_REPAIR",
        "repair_mode": "SUCCESSOR_BOOLEAN_IDENTIFIABLE_FALLBACK_V2",
        "source": emitted,
        "source_sha256": _sha(emitted),
        "selected": selected,
        "profile_attempts": [{"profile": "BOOLEAN_COMPARISON_IDENTIFIABLE_V2", "matched": True}],
        "search_nodes": selected["search_states"],
        "training_only": True,
        "automatic_canonical_promotion": False,
    }


__all__ = [
    "select_boolean_expression_v2",
    "synthesize_boolean_candidate_v2",
    "synthesize_boolean_repair_v2",
]
