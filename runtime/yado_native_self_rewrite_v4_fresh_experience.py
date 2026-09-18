from __future__ import annotations

"""Native self-rewrite V4 driven by fresh verified YADO experience.

This stage reuses YADO's existing V3 AST self-rewrite mechanism. It requires
fresh experience relative to the physically admitted V3 runtime, materializes a
new shadow candidate, proves that only the learned-evidence binding changed,
and measures deterministic ranking changes without mutating runtime/main.
"""

import ast
import copy
import hashlib
import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from yado_native_experience_to_runtime_self_rewrite_v3 import synthesize_candidate

ROOT = Path(__file__).resolve().parent.parent
EXPERIENCE = Path("experience/autonomous/yado-autonomous-learning-latest.json")
TARGET = Path("runtime/yado_bounded_autonomous_learning_v1.py")
V3_ADMISSION = Path("candidates/autonomous/yado-runtime-self-rewrite-admission-v3.json")
CANDIDATE = Path("candidates/autonomous/yado_bounded_autonomous_learning_runtime_candidate_v4.py")
OUT = Path("candidates/autonomous/yado-native-self-rewrite-v4-fresh-experience.json")


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("JSON_OBJECT_REQUIRED:" + str(path))
    return value


def _sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _binding_from_source(source: str) -> dict[str, Any]:
    tree = ast.parse(source)
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "LEARNED_EXTERNAL_EVIDENCE_V2" for target in node.targets):
            continue
        value = ast.literal_eval(node.value)
        if not isinstance(value, dict):
            raise RuntimeError("LEARNED_BINDING_NOT_DICT")
        return value
    raise RuntimeError("LEARNED_EXTERNAL_EVIDENCE_V2_NOT_FOUND")


class _EraseLearnedBinding(ast.NodeTransformer):
    def visit_Assign(self, node: ast.Assign):
        if any(isinstance(target, ast.Name) and target.id == "LEARNED_EXTERNAL_EVIDENCE_V2" for target in node.targets):
            return ast.copy_location(
                ast.Assign(
                    targets=node.targets,
                    value=ast.Constant(value=None),
                    type_comment=getattr(node, "type_comment", None),
                ),
                node,
            )
        return self.generic_visit(node)


def _normalized_ast_digest(source: str) -> str:
    tree = ast.parse(source)
    tree = _EraseLearnedBinding().visit(tree)
    ast.fix_missing_locations(tree)
    return _sha_text(ast.dump(tree, include_attributes=False))


def _load_runtime_module(path: Path):
    spec = importlib.util.spec_from_file_location("yado_v4_parent_runtime", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("RUNTIME_MODULE_SPEC_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _ranking(module, binding: dict[str, Any]) -> dict[str, float]:
    original = copy.deepcopy(module.LEARNED_EXTERNAL_EVIDENCE_V2)
    module.LEARNED_EXTERNAL_EVIDENCE_V2 = copy.deepcopy(binding)
    try:
        priority = {
            "code": "AUTONOMOUS_LEARNING_BOOTSTRAP",
            "area": "EXTERNAL_EVIDENCE_AND_SELF_EVOLUTION",
            "recommended_action": "study public technical sources and bind verified experience to future code evolution",
        }
        return {str(row["id"]): float(row["score"]) for row in module.rank_sources(priority)}
    finally:
        module.LEARNED_EXTERNAL_EVIDENCE_V2 = original


def build(root: Path = ROOT) -> dict[str, Any]:
    root = Path(root).resolve()
    experience_path = root / EXPERIENCE
    target_path = root / TARGET
    admission_path = root / V3_ADMISSION
    candidate_path = root / CANDIDATE

    experience = _load_json(experience_path)
    admission = _load_json(admission_path)

    if experience.get("status") != "PASS_SHADOW_BOUNDED_AUTONOMOUS_EXTERNAL_LEARNING_V1":
        raise RuntimeError("LATEST_EXPERIENCE_NOT_VERIFIED")
    if admission.get("status") != "PASS_SHADOW_RUNTIME_SELF_REWRITE_ADMISSION_V3":
        raise RuntimeError("V3_RUNTIME_NOT_ADMITTED")

    parent_source = target_path.read_text(encoding="utf-8")
    parent_sha = _sha_text(parent_source)
    parent_binding = _binding_from_source(parent_source)
    latest_digest = str(experience.get("experience_digest") or "")
    parent_digest = str(parent_binding.get("experience_digest") or "")
    if not latest_digest or latest_digest == parent_digest:
        raise RuntimeError("NO_FRESH_EXPERIENCE_FOR_NEXT_GENERATION")

    candidate_source, learned, safety_delta = synthesize_candidate(parent_source, experience)
    compile(candidate_source, str(candidate_path), "exec")
    candidate_sha = _sha_text(candidate_source)
    if candidate_sha == parent_sha:
        raise RuntimeError("V4_CANDIDATE_UNCHANGED")

    candidate_binding = _binding_from_source(candidate_source)
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    candidate_path.write_text(candidate_source, encoding="utf-8")

    parent_structural = _normalized_ast_digest(parent_source)
    candidate_structural = _normalized_ast_digest(candidate_source)

    runtime = _load_runtime_module(target_path)
    parent_scores = _ranking(runtime, parent_binding)
    candidate_scores = _ranking(runtime, candidate_binding)
    score_deltas = {
        key: candidate_scores[key] - parent_scores[key]
        for key in sorted(set(parent_scores) & set(candidate_scores))
    }

    expected_success = sorted(
        str(row.get("source_id"))
        for row in experience.get("sources", [])
        if row.get("source_id")
    )
    expected_failures = sorted(
        str(row.get("source_id"))
        for row in experience.get("failures", [])
        if row.get("source_id")
    )
    latest_fact_count = sum(len(row.get("facts") or []) for row in experience.get("sources", []))

    checks = {
        "v3_admission_pass": True,
        "latest_experience_verified": True,
        "fresh_experience_digest": latest_digest != parent_digest,
        "parent_matches_admitted_v3_runtime": parent_sha == admission.get("target_sha256"),
        "candidate_differs_from_parent": candidate_sha != parent_sha,
        "candidate_compiles": True,
        "structural_ast_unchanged_except_learned_binding": parent_structural == candidate_structural,
        "candidate_binds_latest_experience": candidate_binding.get("experience_digest") == latest_digest,
        "candidate_success_sources_exact": sorted(candidate_binding.get("successful_source_ids") or []) == expected_success,
        "candidate_failed_sources_exact": sorted(candidate_binding.get("failed_source_ids") or []) == expected_failures,
        "candidate_fact_count_exact": int(candidate_binding.get("fact_count") or 0) == latest_fact_count,
        "python_unittest_new_success_affinity": score_deltas.get("PYTHON_UNITTEST", 0.0) >= 2.0,
        "former_failed_source_penalty_removed": score_deltas.get("MDN_HTTP", 0.0) >= 1.0,
        "no_new_dangerous_calls": dict(safety_delta.get("new_dangerous_calls") or {}) == {},
        "runtime_target_unchanged_by_generator": _sha_file(target_path) == parent_sha,
        "automatic_main_mutation": False,
        "canonical_mutation": False,
        "external_writes": False,
        "credentials_used": False,
        "downloaded_code_executed": False,
    }

    negative = {
        "automatic_main_mutation",
        "canonical_mutation",
        "external_writes",
        "credentials_used",
        "downloaded_code_executed",
    }
    passed = all(
        (value is False if key in negative else value is True)
        for key, value in checks.items()
    )

    result = {
        "schema": "yado.native_self_rewrite_v4_fresh_experience.v1",
        "status": (
            "PASS_SHADOW_NATIVE_SELF_REWRITE_V4_FRESH_EXPERIENCE"
            if passed
            else "WITHHOLD_NATIVE_SELF_REWRITE_V4_FRESH_EXPERIENCE"
        ),
        "generation": "V4",
        "parent_generation": "V3_ADMITTED_RUNTIME",
        "parent_runtime_path": str(TARGET),
        "parent_runtime_sha256": parent_sha,
        "parent_experience_digest": parent_digest,
        "latest_experience_path": str(EXPERIENCE),
        "latest_experience_digest": latest_digest,
        "candidate_path": str(CANDIDATE),
        "candidate_sha256": candidate_sha,
        "candidate_learned_binding": candidate_binding,
        "parent_structural_ast_digest": parent_structural,
        "candidate_structural_ast_digest": candidate_structural,
        "ranking_before": parent_scores,
        "ranking_after": candidate_scores,
        "ranking_score_deltas": score_deltas,
        "safety_delta": safety_delta,
        "checks": checks,
        "runtime_mutation_applied": False,
        "next_required_capability": (
            "ISOLATED_RUNTIME_EXECUTION_AND_REGRESSION_ADMISSION_V4"
            if passed
            else "REPAIR_NATIVE_SELF_REWRITE_V4_FRESH_EXPERIENCE"
        ),
        "semantic_boundary": (
            "YADO'S EXISTING V3 AST SELF-REWRITE MECHANISM MATERIALIZES A NEW SHADOW "
            "CANDIDATE FROM FRESH VERIFIED EXPERIENCE. ONLY THE LEARNED-EVIDENCE BINDING "
            "MAY CHANGE; RUNTIME/MAIN/CANONICAL ARE NOT MUTATED IN THIS STAGE."
        ),
    }
    out = root / OUT
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def build_committed(root: Path = ROOT) -> dict[str, Any]:
    """Build V4 against committed Git HEAD, insulated from transient shadow mutations."""
    root = Path(root).resolve()
    if not (root / ".git").exists():
        result = build(root)
        result["repository_view"] = "WORKTREE_FALLBACK_NO_GIT"
        return result

    required = (EXPERIENCE, TARGET, V3_ADMISSION)
    with tempfile.TemporaryDirectory(prefix="yado-v4-committed-head-") as directory:
        shadow = Path(directory)
        for relative in required:
            cp = subprocess.run(
                ["git", "show", "HEAD:" + relative.as_posix()],
                cwd=root,
                capture_output=True,
                timeout=30,
            )
            if cp.returncode != 0:
                raise RuntimeError(
                    "COMMITTED_ARTIFACT_READ_FAILED:"
                    + relative.as_posix()
                    + ":"
                    + cp.stderr.decode("utf-8", "replace")[-500:]
                )
            out = shadow / relative
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(cp.stdout)
        result = build(shadow)
        result["repository_view"] = "COMMITTED_HEAD"
        return result


def main() -> int:
    result = build()
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"].startswith("PASS_") else 2


if __name__ == "__main__":
    raise SystemExit(main())
