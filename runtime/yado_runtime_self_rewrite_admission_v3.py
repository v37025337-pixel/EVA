from __future__ import annotations

"""Admission gate for the already-materialized native runtime self-rewrite V3.

This gate does NOT rewrite runtime source. It verifies that the current runtime
already matches the previously generated V3 candidate byte-for-byte, proves
the learned-evidence binding has an observable deterministic effect, and emits
a fail-closed admission receipt for later full regression.
"""

import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SOURCE_RECEIPT = Path("candidates/autonomous/yado-native-experience-to-runtime-self-rewrite-v3.json")
CANDIDATE = Path("candidates/autonomous/yado_bounded_autonomous_learning_runtime_candidate_v3.py")
TARGET = Path("runtime/yado_bounded_autonomous_learning_v1.py")
CANONICAL_HEAD = Path("canonical/yado-main-head-g2.json")
OUT = Path("candidates/autonomous/yado-runtime-self-rewrite-admission-v3.json")


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_file(path: Path) -> str:
    return _sha_bytes(path.read_bytes())


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("JSON_OBJECT_REQUIRED:" + str(path))
    return value


def _compile_ok(path: Path) -> tuple[bool, str | None]:
    try:
        source = path.read_text(encoding="utf-8")
        compile(source, str(path), "exec")
        return True, None
    except Exception as exc:
        return False, type(exc).__name__ + ":" + str(exc)[:500]


def _ast_digest(path: Path) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    rendered = ast.dump(tree, include_attributes=False)
    return _sha_bytes(rendered.encode("utf-8"))


def _load_runtime_module(path: Path):
    spec = importlib.util.spec_from_file_location("yado_admission_runtime_v3", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("RUNTIME_MODULE_SPEC_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _rank_map(module, priority: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = module.rank_sources(priority)
    return {str(row["id"]): dict(row) for row in rows}


def analyze(root: Path = ROOT) -> dict[str, Any]:
    root = Path(root).resolve()
    receipt_path = root / SOURCE_RECEIPT
    candidate_path = root / CANDIDATE
    target_path = root / TARGET
    canonical_path = root / CANONICAL_HEAD

    receipt = _load_json(receipt_path)
    if receipt.get("status") != "PASS_SHADOW_NATIVE_EXPERIENCE_TO_RUNTIME_SELF_REWRITE_CANDIDATE_V3":
        raise RuntimeError("SELF_REWRITE_V3_SOURCE_RECEIPT_NOT_PASS")
    if receipt.get("next_required_capability") != "ISOLATED_RUNTIME_EXECUTION_AND_REGRESSION_ADMISSION_V3":
        raise RuntimeError("SELF_REWRITE_V3_FRONTIER_MISMATCH")

    candidate_sha = _sha_file(candidate_path)
    target_sha = _sha_file(target_path)
    candidate_compile, candidate_error = _compile_ok(candidate_path)
    target_compile, target_error = _compile_ok(target_path)
    candidate_ast = _ast_digest(candidate_path) if candidate_compile else None
    target_ast = _ast_digest(target_path) if target_compile else None
    canonical_before = _sha_file(canonical_path)

    runtime = _load_runtime_module(target_path)
    learned = copy.deepcopy(getattr(runtime, "LEARNED_EXTERNAL_EVIDENCE_V2", None))
    if not isinstance(learned, dict):
        raise RuntimeError("LEARNED_EXTERNAL_EVIDENCE_V2_MISSING")

    source_binding = dict(receipt.get("learned_binding") or {})
    priority = {
        "code": "AUTONOMOUS_LEARNING_BOOTSTRAP",
        "area": "EXTERNAL_EVIDENCE_AND_SELF_EVOLUTION",
        "recommended_action": "study public technical sources and bind verified experience to future code evolution",
    }

    with_evidence = _rank_map(runtime, priority)
    runtime.LEARNED_EXTERNAL_EVIDENCE_V2 = {
        "experience_digest": "ABLATION_NONE",
        "successful_source_ids": [],
        "failed_source_ids": [],
        "successful_hosts": [],
        "fact_count": 0,
        "learning_tokens": [],
    }
    try:
        without_evidence = _rank_map(runtime, priority)
    finally:
        runtime.LEARNED_EXTERNAL_EVIDENCE_V2 = learned

    successful_ids = list(learned.get("successful_source_ids") or [])
    successful_hosts = set(learned.get("successful_hosts") or [])
    success_deltas = {
        source_id: (
            float(with_evidence[source_id]["score"])
            - float(without_evidence[source_id]["score"])
        )
        for source_id in successful_ids
        if source_id in with_evidence and source_id in without_evidence
    }
    host_only_deltas = {}
    for source_id, row in with_evidence.items():
        host = str(row.get("url") or "")
        try:
            import urllib.parse
            hostname = (urllib.parse.urlsplit(host).hostname or "").lower()
        except Exception:
            hostname = ""
        if hostname in successful_hosts and source_id not in successful_ids:
            host_only_deltas[source_id] = (
                float(row["score"])
                - float(without_evidence[source_id]["score"])
            )

    source_text = target_path.read_text(encoding="utf-8")
    unsafe_tokens = {
        "eval_call": "eval(" in source_text,
        "exec_call": "exec(" in source_text,
        "subprocess_import": "import subprocess" in source_text or "from subprocess" in source_text,
    }
    safety_delta = dict(receipt.get("safety_delta") or {})
    new_dangerous = dict(safety_delta.get("new_dangerous_calls") or {})

    canonical_after = _sha_file(canonical_path)

    checks = {
        "source_receipt_pass": True,
        "frontier_matches_admission_v3": True,
        "candidate_sha_matches_receipt": candidate_sha == receipt.get("candidate_sha256"),
        "target_sha_matches_candidate": target_sha == candidate_sha,
        "target_differs_from_recorded_parent": target_sha != receipt.get("parent_sha256"),
        "candidate_compiles": candidate_compile,
        "target_compiles": target_compile,
        "candidate_target_ast_identical": candidate_ast == target_ast,
        "runtime_learned_binding_exact": learned == source_binding,
        "experience_digest_bound": learned.get("experience_digest") == receipt.get("experience_digest"),
        "successful_source_affinity_observed": bool(success_deltas) and all(delta >= 2.0 for delta in success_deltas.values()),
        "successful_host_affinity_observed": bool(host_only_deltas) and any(delta >= 1.0 for delta in host_only_deltas.values()),
        "no_new_dangerous_calls_in_source_receipt": new_dangerous == {},
        "no_eval_exec_or_subprocess_added_to_target": not any(unsafe_tokens.values()),
        "canonical_head_unchanged_during_admission_probe": canonical_before == canonical_after,
        "runtime_rewrite_performed_by_gate": False,
        "automatic_main_mutation": False,
        "external_writes": False,
        "credentials_used": False,
        "downloaded_code_executed": False,
    }

    positive = [
        key for key in checks
        if key not in {
            "runtime_rewrite_performed_by_gate",
            "automatic_main_mutation",
            "external_writes",
            "credentials_used",
            "downloaded_code_executed",
        }
    ]
    negative = [
        "runtime_rewrite_performed_by_gate",
        "automatic_main_mutation",
        "external_writes",
        "credentials_used",
        "downloaded_code_executed",
    ]
    passed = all(checks[key] is True for key in positive) and all(checks[key] is False for key in negative)

    return {
        "schema": "yado.runtime_self_rewrite_admission.v3",
        "status": (
            "PASS_SHADOW_RUNTIME_SELF_REWRITE_ADMISSION_V3"
            if passed
            else "WITHHOLD_RUNTIME_SELF_REWRITE_ADMISSION_V3"
        ),
        "admission_mode": "ALREADY_PHYSICALLY_PRESENT_IDENTICAL_BYTES",
        "source_receipt": str(SOURCE_RECEIPT),
        "source_receipt_sha256": _sha_file(receipt_path),
        "target_path": str(TARGET),
        "target_sha256": target_sha,
        "candidate_path": str(CANDIDATE),
        "candidate_sha256": candidate_sha,
        "recorded_parent_sha256": receipt.get("parent_sha256"),
        "candidate_compile_error": candidate_error,
        "target_compile_error": target_error,
        "candidate_ast_digest": candidate_ast,
        "target_ast_digest": target_ast,
        "experience_digest": receipt.get("experience_digest"),
        "learned_binding": learned,
        "ranking_effect": {
            "successful_source_score_deltas": success_deltas,
            "successful_host_only_score_deltas": host_only_deltas,
        },
        "unsafe_token_probe": unsafe_tokens,
        "checks": checks,
        "canonical_head_sha256_before": canonical_before,
        "canonical_head_sha256_after": canonical_after,
        "next_required_capability": (
            "NEXT_GENERATION_NATIVE_SELF_REWRITE_FROM_FRESH_EXPERIENCE_V1"
            if passed
            else "REPAIR_RUNTIME_SELF_REWRITE_ADMISSION_V3"
        ),
        "semantic_boundary": (
            "THIS GATE DOES NOT CREATE OR APPLY A NEW PATCH. IT PROVES THAT THE PREVIOUSLY "
            "GENERATED V3 SELF-REWRITE CANDIDATE IS ALREADY THE PHYSICAL RUNTIME SOURCE, "
            "THAT ITS EXPERIENCE BINDING CHANGES DETERMINISTIC SOURCE RANKING, AND THAT "
            "THE OUTER CANONICAL HEAD IS UNCHANGED. FULL REGRESSION IS REQUIRED BY CI "
            "BEFORE MERGE. THIS IS NOT OPEN-ENDED AUTONOMY OR A CONSCIOUSNESS CLAIM."
        ),
    }


def run(root: Path = ROOT) -> dict[str, Any]:
    root = Path(root).resolve()
    result = analyze(root)
    out = root / OUT
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return result


def main() -> int:
    result = run()
    return 0 if result["status"].startswith("PASS_") else 2


if __name__ == "__main__":
    raise SystemExit(main())
