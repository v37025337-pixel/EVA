from __future__ import annotations

import ast
import hashlib

ALLOWED_OPERATIONS = ("weighted_hypothesis_score",)

def _weighted_score_tree() -> ast.Module:
    args = ast.arguments(
        posonlyargs=[],
        args=[
            ast.arg(arg="coverage"),
            ast.arg(arg="risk"),
        ],
        vararg=None,
        kwonlyargs=[],
        kw_defaults=[],
        kwarg=None,
        defaults=[],
    )
    body = ast.Return(
        value=ast.BinOp(
            left=ast.BinOp(
                left=ast.Name(id="coverage", ctx=ast.Load()),
                op=ast.Mult(),
                right=ast.Constant(value=10),
            ),
            op=ast.Sub(),
            right=ast.Name(id="risk", ctx=ast.Load()),
        )
    )
    return ast.fix_missing_locations(
        ast.Module(
            body=[ast.FunctionDef(
                name="weighted_hypothesis_score",
                args=args,
                body=[body],
                decorator_list=[],
                returns=None,
            )],
            type_ignores=[],
        )
    )

def materialize_algorithm(operation: str) -> dict:
    if operation not in ALLOWED_OPERATIONS:
        return {
            "schema": "yado.native_ast_algorithm_mutator.v1",
            "status": "WITHHOLD",
            "reason": "operation_not_allowlisted",
            "canonical_active": False,
            "external_code_executed": False,
        }
    tree = _weighted_score_tree()
    source = ast.unparse(tree) + "\n"
    compile(source, "<generated-shadow-candidate>", "exec")
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    return {
        "schema": "yado.native_ast_algorithm_mutator.v1",
        "status": "PASS_SHADOW",
        "operation": operation,
        "source": source,
        "source_sha256": digest,
        "generated_by": "native_ast",
        "canonical_active": False,
        "external_code_executed": False,
    }

def verify_candidate(materialized: dict) -> dict:
    if materialized.get("status") != "PASS_SHADOW":
        return {"status": "WITHHOLD", "reason": "candidate_not_materialized"}
    namespace = {}
    exec(compile(materialized["source"], "<generated-shadow-candidate>", "exec"), namespace)
    result = namespace["weighted_hypothesis_score"](2, 1)
    return {
        "status": "PASS_SHADOW" if result == 19 else "WITHHOLD",
        "observed": result,
        "expected": 19,
        "canonical_active": False,
        "external_code_executed": False,
    }

def component() -> dict:
    return {
        "schema": "yado.native_ast_algorithm_mutator.v1",
        "allowlisted_operations": ALLOWED_OPERATIONS,
        "canonical_active": False,
        "external_code_executed": False,
    }
