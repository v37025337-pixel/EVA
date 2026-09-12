from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
STUDY = REPO / "experience" / "python" / "yado-python-study-v1.json"
TARGET = ROOT / "yado_unified_core_v1.py"
OUT_DIR = REPO / "candidates" / "python"
CANDIDATE = OUT_DIR / "yado_unified_core_v1_candidate.py"
REPORT = OUT_DIR / "yado-python-informed-core-self-improvement-v1.json"
SCHEMA = "yado.python_informed_core_self_improvement.v1"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def main() -> None:
    study = json.loads(STUDY.read_text(encoding="utf-8"))
    if study.get("status") != "PASS_SHADOW_BOUNDED_PYTHON_STUDY_V1":
        raise SystemExit("PYTHON_STUDY_NOT_PASS")
    checks = study.get("interpreter_checks", {})
    required = {"ast_parse_function", "compile_exec_local_generated_only", "inspect_signature", "importlib_find_spec", "modern_syntax_match_ast"}
    if not required.issubset(checks) or not all(checks[k] for k in required):
        raise SystemExit("PYTHON_STUDY_INTERPRETER_EVIDENCE_INCOMPLETE")

    parent_bytes = TARGET.read_bytes()
    tree = ast.parse(parent_bytes.decode("utf-8"))
    core_cls = next((n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "UnifiedYADOCoreV1"), None)
    if core_cls is None:
        raise SystemExit("UNIFIED_CORE_CLASS_NOT_FOUND")
    if any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "python_runtime_self_check" for n in core_cls.body):
        raise SystemExit("SELF_CHECK_ALREADY_PRESENT")

    method_src = '''
def python_runtime_self_check(self) -> dict[str, Any]:
    """Verify Python runtime features used by YADO without executing downloaded code."""
    import ast as _ast
    import importlib.util as _importlib_util
    import inspect as _inspect

    def _probe(a: int, b: int = 2) -> int:
        return a + b

    _sig = _inspect.signature(_probe, eval_str=True)
    _tree = _ast.parse("def f(x):\\n    return x * 2 + 1\\n")
    _match = _ast.parse("match x:\\n    case 1:\\n        y = 'one'\\n    case _:\\n        y = 'other'\\n")
    _checks = {
        "ast_parse_function": isinstance(_tree.body[0], _ast.FunctionDef),
        "compile_ast": bool(compile(_tree, "<yado-core-self-check>", "exec")),
        "inspect_signature_resolved": list(_sig.parameters) == ["a", "b"] and _sig.return_annotation is int,
        "importlib_find_spec": _importlib_util.find_spec("json") is not None,
        "modern_syntax_match_ast": any(isinstance(n, _ast.Match) for n in _ast.walk(_match)),
    }
    return {
        "schema": "yado.python_runtime_self_check.v1",
        "checks": _checks,
        "pass": all(_checks.values()),
        "downloaded_code_executed": False,
    }
'''
    method = ast.parse(method_src).body[0]
    core_cls.body.append(method)
    ast.fix_missing_locations(tree)
    candidate_text = ast.unparse(tree) + "\n"
    candidate_bytes = candidate_text.encode("utf-8")
    compile(candidate_text, str(CANDIDATE), "exec")

    # Structural counterfactual: parent must not already contain the capability.
    parent_tree = ast.parse(parent_bytes.decode("utf-8"))
    parent_cls = next(n for n in parent_tree.body if isinstance(n, ast.ClassDef) and n.name == "UnifiedYADOCoreV1")
    parent_has = any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "python_runtime_self_check" for n in parent_cls.body)
    candidate_has = any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "python_runtime_self_check" for n in core_cls.body)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CANDIDATE.write_bytes(candidate_bytes)
    report = {
        "schema": SCHEMA,
        "status": "PASS_SHADOW_PYTHON_INFORMED_CORE_SELF_IMPROVEMENT_V1" if candidate_has and not parent_has else "WITHHOLD",
        "target": "runtime/yado_unified_core_v1.py",
        "parent_sha256": sha(parent_bytes),
        "candidate_sha256": sha(candidate_bytes),
        "study_experience_digest": study.get("experience_digest"),
        "study_source_count": study.get("source_count"),
        "study_fact_count": study.get("fact_count"),
        "candidate_has_new_self_check": candidate_has,
        "parent_has_self_check": parent_has,
        "candidate_compiles": True,
        "external_model_used": False,
        "downloaded_code_executed": False,
        "canonical_mutation": False,
        "claim_boundary": "Bounded Python-informed shadow mutation of the unified-core runtime introspection layer; not open-ended self-programming or consciousness evidence.",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(canon({"status": report["status"], "candidate_sha256": report["candidate_sha256"], "study_experience_digest": report["study_experience_digest"]}))
    if report["status"] != "PASS_SHADOW_PYTHON_INFORMED_CORE_SELF_IMPROVEMENT_V1":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
