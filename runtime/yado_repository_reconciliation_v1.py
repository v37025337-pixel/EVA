from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "audits" / "yado-repository-reconciliation-v1-report.json"

HEAD = ROOT / "canonical" / "yado-main-head-g2.json"
CORE = ROOT / "canonical" / "yado-unified-core-v1.json"
EXP = ROOT / "canonical" / "yado-unified-experience-registry-v1.json"
LEDGER = ROOT / "architecture" / "evolution-ledger.json"
CONTRACT = ROOT / "architecture" / "yado-unified-architecture-v2.json"
MANAGED_POLICY = ROOT / "architecture" / "yado-active-managed-branch-policy-v1.json"
PROMOTION = ROOT / "candidates" / "autonomous" / "yado-runtime-self-rewrite-promotion-v4.json"
TARGET = ROOT / "runtime" / "yado_bounded_autonomous_learning_v1.py"
V4 = ROOT / "candidates" / "autonomous" / "yado_bounded_autonomous_learning_runtime_candidate_v4.py"
UNIFIED_RUNTIME = ROOT / "runtime" / "yado_unified_core_v1.py"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    cp = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )
    if cp.returncode != 0:
        raise RuntimeError("GIT_FAILED:" + " ".join(args) + ":" + cp.stderr[-1000:])
    return cp.stdout.strip()


def tracked_files() -> list[Path]:
    try:
        raw = git("ls-files", "-z")
    except Exception:
        return []
    return [ROOT / x for x in raw.split("\0") if x]


def _path_allowed(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def branch_inventory(managed_policy: dict[str, Any]) -> dict[str, Any]:
    try:
        refs = [
            x for x in git("for-each-ref", "--format=%(refname:short)", "refs/remotes/origin").splitlines()
            if x and x not in {"origin/HEAD", "origin/main"}
        ]
        current = os.getenv("GITHUB_HEAD_REF") or ""
        if not current:
            try:
                current = git("branch", "--show-current")
            except Exception:
                current = ""
        managed = managed_policy.get("branches", {})
        rows = []
        blocking = []
        managed_divergence = []
        for ref in refs:
            name = ref.removeprefix("origin/")
            if name == current:
                continue
            ahead = int(git("rev-list", "--count", "origin/main.." + ref) or "0")
            behind = int(git("rev-list", "--count", ref + "..origin/main") or "0")
            changed = []
            if ahead:
                changed = [
                    x for x in git("diff", "--name-only", "origin/main..." + ref).splitlines()
                    if x
                ]
            policy = managed.get(name)
            allowed = False
            violations: list[str] = []
            if ahead and policy and policy.get("branch_divergence_allowed") is True:
                patterns = list(policy.get("allowed_paths", []))
                violations = [x for x in changed if not _path_allowed(x, patterns)]
                allowed = not violations
            row = {
                "branch": name,
                "ahead": ahead,
                "behind": behind,
                "managed": bool(policy),
                "managed_role": policy.get("role") if policy else None,
                "changed_paths": changed,
                "scope_violations": violations,
                "divergence_allowed": allowed,
            }
            rows.append(row)
            if ahead:
                if allowed:
                    managed_divergence.append(row)
                else:
                    blocking.append(row)
        return {
            "available": True,
            "branch_count": len(rows),
            "ahead_branches": [x for x in rows if x["ahead"] > 0],
            "blocking_ahead_branches": blocking,
            "managed_divergence": managed_divergence,
            "rows": rows,
        }
    except Exception as exc:
        return {
            "available": False,
            "error": repr(exc),
            "branch_count": 0,
            "ahead_branches": [],
            "blocking_ahead_branches": [],
            "managed_divergence": [],
            "rows": [],
        }


def conflict_markers(paths: list[Path]) -> list[str]:
    bad = []
    suffixes = {".py", ".json", ".yml", ".yaml", ".toml", ".ini", ".cfg"}
    left = "<" * 7
    middle = "=" * 7
    right = ">" * 7
    for path in paths:
        if path.suffix.lower() not in suffixes or not path.is_file():
            continue
        try:
            if path.stat().st_size > 2_000_000:
                continue
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue
        if any(
            line.startswith(left + " ")
            or line == middle
            or line.startswith(right + " ")
            for line in lines
        ):
            bad.append(path.relative_to(ROOT).as_posix())
    return bad


def active_status(obj: dict[str, Any]) -> bool:
    return obj.get("canonical_active") is True or obj.get("status") == "CANONICAL_ACTIVE"


def run(strict: bool = False) -> dict[str, Any]:
    head = load(HEAD)
    core = load(CORE)
    exp = load(EXP)
    ledger = load(LEDGER)
    contract = load(CONTRACT)
    managed_policy = load(MANAGED_POLICY)
    promotion = load(PROMOTION)

    branches = exp.get("branches", [])
    active = [x for x in branches if x.get("mode") == "ACTIVE_LINEAGE"]
    legacy = [x for x in branches if x.get("mode") == "EXPERIENCE_ONLY"]
    closure = exp.get("closure", {})
    policy = exp.get("policy", {})

    tracked = tracked_files()
    tracked_rel = {p.relative_to(ROOT).as_posix() for p in tracked}
    tracked_bytecode = sorted(
        x for x in tracked_rel if x.endswith(".pyc") or "/__pycache__/" in ("/" + x)
    )
    markers = conflict_markers(tracked)

    unified_source = UNIFIED_RUNTIME.read_text(encoding="utf-8")
    branch_state = branch_inventory(managed_policy)

    execution_versions = [
        head.get("execution_fabric_v1", {}),
        head.get("execution_fabric_v2", {}),
        head.get("execution_fabric_v3", {}),
        head.get("execution_fabric_v4", {}),
        head.get("execution_fabric_v5", {}),
    ]
    experience_versions = [
        head.get("experience_conditioned_cognitive_layer_v3", {}),
        head.get("experience_conditioned_cognitive_layer_v4", {}),
    ]

    checks = {
        "head_ledger_generation": head.get("generation_id") == ledger.get("current_head"),
        "head_ledger_digest": head.get("canonical_head_digest") == ledger.get("current_head_digest"),
        "core_generation_matches_head": core.get("generation") == head.get("generation_id"),
        "contract_formal_generation_matches_head": contract.get("formal_architecture", {}).get("generation") == head.get("generation_id"),
        "single_registry_active_lineage": len(active) == 1 and active[0].get("branch") == policy.get("active_branch"),
        "registry_entries_partitioned": len(active) + len(legacy) == len(branches),
        "registry_count_self_consistent": closure.get("remote_branch_count") == len(branches),
        "registry_scope_explicit": contract.get("branch_policy", {}).get("experience_registry_scope") == "CURATED_LEGACY_EXPERIENCE_NOT_REMOTE_REF_INVENTORY",
        "runtime_v4_target_exact": TARGET.exists() and V4.exists() and sha256(TARGET) == sha256(V4),
        "runtime_v4_digest_bound": sha256(V4) == promotion.get("candidate_sha256") == contract.get("runtime_lineage", {}).get("candidate_sha256"),
        "runtime_v4_promotion_closed": promotion.get("status") == "MERGED_PHYSICAL_RUNTIME_PROMOTION_V4",
        "runtime_v4_gates_recorded": all(promotion.get(k) is True for k in ("physical_runtime_promotion", "exact_candidate_binding", "full_kernel_audit", "canonical_guard", "full_regression")),
        "single_active_execution_fabric": sum(active_status(x) for x in execution_versions) == 1 and active_status(head.get("execution_fabric_v5", {})),
        "single_active_experience_layer": sum(active_status(x) for x in experience_versions) == 1 and active_status(head.get("experience_conditioned_cognitive_layer_v4", {})),
        "no_tracked_bytecode": not tracked_bytecode,
        "no_merge_conflict_markers": not markers,
        "unified_core_no_hardcoded_branch_count": "len(branches)==14" not in unified_source and "len(branches) == 14" not in unified_source,
        "unified_core_no_hardcoded_active_branch": "active[0].get('branch')=='yado-architecture-shadow-search'" not in unified_source,
        "development_loop_complete": contract.get("development_continuity") == [
            "MEASURE_DEFICIT",
            "SELECT_TARGET_FROM_CURRENT_STATE",
            "MATERIALIZE_CHANGE",
            "FRESH_TEST",
            "FULL_REGRESSION",
            "FULL_KERNEL_AUDIT",
            "ADMIT_OR_ROLLBACK",
            "DERIVE_NEXT_DEFICIT_FROM_ADMITTED_STATE",
        ],
        "remote_branch_divergence_policy_satisfied": (not branch_state.get("available")) or not branch_state.get("blocking_ahead_branches"),
    }

    findings = []
    for key, ok in checks.items():
        if not ok:
            findings.append({"code": key.upper(), "severity": "HIGH", "status": "OPEN"})

    report = {
        "schema": "yado.repository_reconciliation.v1",
        "status": "PASS" if all(checks.values()) else "FAIL_RECONCILIATION",
        "architecture_id": contract.get("architecture_id"),
        "formal_generation": head.get("generation_id"),
        "runtime_generation": contract.get("runtime_lineage", {}).get("generation"),
        "runtime_target_sha256": sha256(TARGET),
        "runtime_candidate_sha256": sha256(V4),
        "checks": checks,
        "findings": findings,
        "tracked_bytecode": tracked_bytecode,
        "conflict_marker_files": markers,
        "branch_inventory": branch_state,
        "claim_boundary": contract.get("claim_boundary"),
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "formal_generation": report["formal_generation"],
        "runtime_generation": report["runtime_generation"],
        "failed_checks": [k for k, v in checks.items() if not v],
        "ahead_branches": branch_state.get("ahead_branches", []),
        "managed_divergence": branch_state.get("managed_divergence", []),
        "blocking_ahead_branches": branch_state.get("blocking_ahead_branches", []),
        "report": str(OUT.relative_to(ROOT)),
    }, sort_keys=True))
    if strict and report["status"] != "PASS":
        raise SystemExit(1)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    run(strict=args.strict)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
