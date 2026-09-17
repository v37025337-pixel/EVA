from __future__ import annotations

import ast
import hashlib

ALLOWED_OPERATION = "weighted_hypothesis_score"
ALLOWED_NODES = {
    ast.Module,
    ast.FunctionDef,
    ast.arguments,
    ast.arg,
    ast.Return,
    ast.BinOp,
    ast.Name,
    ast.Constant,
    ast.Load,
    ast.Mult,
    ast.Sub,
}

def _safe_source(source: str) -> tuple[bool, tuple[str, ...]]:
    try:
        tree = ast.parse(source, mode="exec")
    except SyntaxError:
        return False, ("syntax_error",)
    violations = sorted({
        type(node).__name__
        for node in ast.walk(tree)
        if type(node) not in ALLOWED_NODES
    })
    return not violations, tuple(violations)

def register_shadow_capability(materialized: dict) -> dict:
    if materialized.get("status") != "PASS_SHADOW":
        return {"schema": "yado.shadow_capability_admission.v1", "status": "WITHHOLD", "reason": "source_not_passed", "canonical_active": False}
    if materialized.get("operation") != ALLOWED_OPERATION:
        return {"schema": "yado.shadow_capability_admission.v1", "status": "WITHHOLD", "reason": "operation_not_allowed", "canonical_active": False}
    source = materialized.get("source", "")
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    if digest != materialized.get("source_sha256"):
        return {"schema": "yado.shadow_capability_admission.v1", "status": "WITHHOLD", "reason": "hash_mismatch", "canonical_active": False}
    safe, violations = _safe_source(source)
    if not safe:
        return {"schema": "yado.shadow_capability_admission.v1", "status": "WITHHOLD", "reason": "unsafe_ast", "violations": violations, "canonical_active": False}
    compile(source, "<shadow-capability>", "exec")
    namespace = {}
    exec(compile(source, "<shadow-capability>", "exec"), namespace)
    observed = namespace[ALLOWED_OPERATION](2, 1)
    if observed != 19:
        return {"schema": "yado.shadow_capability_admission.v1", "status": "WITHHOLD", "reason": "behavior_regression", "observed": observed, "canonical_active": False}
    return {
        "schema": "yado.shadow_capability_admission.v1",
        "status": "SHADOW_REGISTERED",
        "capability_id": "sha256:" + digest,
        "operation": ALLOWED_OPERATION,
        "observed": observed,
        "rollback_supported": True,
        "canonical_active": False,
        "external_code_executed": False,
    }

def component() -> dict:
    return {
        "schema": "yado.shadow_capability_admission.v1",
        "allowed_operation": ALLOWED_OPERATION,
        "canonical_active": False,
        "external_code_executed": False,
    }
