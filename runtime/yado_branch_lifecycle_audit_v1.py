from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
REGISTRY = REPO / "canonical" / "yado-unified-experience-registry-v1.json"
OUT = REPO / "canonical" / "yado-branch-lifecycle-v1.json"
MEMORY_OUT = REPO / "experience" / "branch-lifecycle" / "yado-branch-memory-index-v1.json"

COGNITIVE_PATH_PREFIXES = (
    "runtime/",
    "successor/",
    "canonical/",
    "architecture/",
    "candidates/",
    "experience/",
    "receipts/",
)


def _run(*args: str, check: bool = True) -> str:
    cp = subprocess.run(
        list(args),
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=90,
    )
    if check and cp.returncode != 0:
        raise RuntimeError(
            f"COMMAND_FAILED:{' '.join(args)}:{cp.returncode}:{cp.stderr[-600:]}"
        )
    return cp.stdout.strip()


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canon(value).encode("utf-8")).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _remote_heads() -> dict[str, str]:
    text = _run("git", "for-each-ref", "--format=%(refname:short) %(objectname)", "refs/remotes/origin")
    out: dict[str, str] = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) != 2:
            continue
        ref, sha = parts
        if ref in {"origin/HEAD"} or not ref.startswith("origin/"):
            continue
        out[ref[len("origin/"):]] = sha
    if "main" not in out:
        raise RuntimeError("ORIGIN_MAIN_MISSING")
    return out


def _ancestor(tip: str, main_sha: str) -> bool:
    cp = subprocess.run(
        ["git", "merge-base", "--is-ancestor", tip, main_sha],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if cp.returncode == 0:
        return True
    if cp.returncode == 1:
        return False
    raise RuntimeError("ANCESTRY_CHECK_FAILED:" + cp.stderr[-400:])


def _exclusive_count(main_sha: str, tip: str) -> int:
    value = _run("git", "rev-list", "--count", f"{main_sha}..{tip}")
    return int(value or "0")


def _changed_paths(main_sha: str, tip: str) -> list[str]:
    cp = subprocess.run(
        ["git", "diff", "--name-only", f"{main_sha}...{tip}"],
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if cp.returncode != 0:
        raise RuntimeError('BRANCH_DIFF_FAILED:' + cp.stderr[-500:])
    return sorted({line.strip() for line in cp.stdout.splitlines() if line.strip()})


def _role_history(name: str) -> bool:
    lower = name.lower()
    return (
        name.startswith(("pre-", "tmp-", "deployment-"))
        or any(token in lower for token in ("integration", "inventory", "reconcile", "backup"))
    )


def _classify(
    name: str,
    *,
    is_self: bool,
    registered: bool,
    tip_is_ancestor: bool,
    exclusive_commits: int,
    changed_paths: list[str],
) -> tuple[str, str]:
    if name == "main":
        return "ACTIVE_MAIN", "CANONICAL_MAIN"
    if is_self:
        return "ACTIVE_AUDIT_TRANSPORT", "CURRENT_AUDIT_BRANCH"
    if registered and tip_is_ancestor:
        return "MEMORY_REGISTERED_ABSORBED", "REGISTERED_EXPERIENCE_AND_IN_MAIN_ANCESTRY"
    if registered and not tip_is_ancestor:
        return "MEMORY_REGISTERED_CANDIDATE", "REGISTERED_EXPERIENCE_WITH_DIVERGED_TIP"
    if tip_is_ancestor:
        return "HISTORY_ABSORBED", "TIP_IS_ANCESTOR_OF_MAIN"
    if _role_history(name):
        return "HISTORY_INFRASTRUCTURE_DIVERGED", "INFRASTRUCTURE_OR_VERIFICATION_ROLE"
    cognitive = any(path.startswith(COGNITIVE_PATH_PREFIXES) for path in changed_paths)
    if exclusive_commits > 0 and cognitive:
        return "ACTIVE_CANDIDATE_REQUIRES_ADMISSION", "DIVERGED_COGNITIVE_OR_RUNTIME_CHANGES"
    if exclusive_commits > 0:
        return "HISTORY_DIVERGED_NONCOGNITIVE", "DIVERGED_WITHOUT_COGNITIVE_PATH_CHANGES"
    return "WITHHOLD_UNCLASSIFIED", "NO_SAFE_CLASSIFICATION"


def main() -> None:
    audit_branch = os.environ.get("YADO_AUDIT_BRANCH", "").strip()
    remote = _remote_heads()
    main_sha = remote["main"]
    registry = _load(REGISTRY)
    registered = {
        str(row.get("branch"))
        for row in registry.get("branches", [])
        if isinstance(row, dict) and row.get("branch")
    }

    rows: list[dict[str, Any]] = []
    for name in sorted(remote):
        sha = remote[name]
        is_self = bool(audit_branch and name == audit_branch)
        tip_is_ancestor = False if is_self else _ancestor(sha, main_sha)
        exclusive = 0 if (is_self or tip_is_ancestor or name == "main") else _exclusive_count(main_sha, sha)
        changed = [] if (is_self or tip_is_ancestor or name == "main") else _changed_paths(main_sha, sha)
        classification, reason = _classify(
            name,
            is_self=is_self,
            registered=name in registered,
            tip_is_ancestor=tip_is_ancestor,
            exclusive_commits=exclusive,
            changed_paths=changed,
        )
        rows.append(
            {
                "branch": name,
                "head_sha": "SELF" if is_self else sha,
                "classification": classification,
                "classification_reason": reason,
                "registered_in_experience_registry": name in registered,
                "runtime_active": name == "main",
                "tip_is_ancestor_of_main": None if is_self else tip_is_ancestor,
                "exclusive_commit_count": exclusive,
                "changed_path_count": len(changed),
                "cognitive_path_count": sum(
                    1 for path in changed if path.startswith(COGNITIVE_PATH_PREFIXES)
                ),
                "changed_paths_sample": changed[:24],
            }
        )

    classes: dict[str, int] = {}
    for row in rows:
        classes[row["classification"]] = classes.get(row["classification"], 0) + 1

    active = [
        row["branch"]
        for row in rows
        if row["classification"] in {"ACTIVE_MAIN", "ACTIVE_AUDIT_TRANSPORT", "ACTIVE_CANDIDATE_REQUIRES_ADMISSION"}
    ]
    memory = [
        row["branch"]
        for row in rows
        if row["classification"].startswith("MEMORY_")
    ]
    history = [
        row["branch"]
        for row in rows
        if row["classification"].startswith("HISTORY_")
    ]
    withheld = [
        row["branch"]
        for row in rows
        if row["classification"].startswith("WITHHOLD_")
    ]
    admission_candidates = [
        row["branch"]
        for row in rows
        if row["classification"] == "ACTIVE_CANDIDATE_REQUIRES_ADMISSION"
    ]

    artifact = {
        "schema": "yado.branch_lifecycle.v1",
        "status": "PASS_COMPLETE_BRANCH_LIFECYCLE_AUDIT" if not withheld else "WITHHOLD_BRANCH_LIFECYCLE_AUDIT",
        "baseline_main_sha": main_sha,
        "audit_branch": audit_branch or None,
        "remote_branch_count": len(remote),
        "classification_counts": dict(sorted(classes.items())),
        "active_refs": active,
        "memory_refs": memory,
        "history_refs": history,
        "admission_candidates": admission_candidates,
        "withheld_refs": withheld,
        "coverage_complete": len(rows) == len(remote),
        "policy": {
            "active_main": "KEEP_ACTIVE",
            "active_audit_transport": "KEEP_ONLY_AS_AUDIT_TRANSPORT_UNTIL_MAIN_MERGE",
            "active_candidate_requires_admission": "KEEP_ACTIVE_CANDIDATE_AND_REQUIRE_SEPARATE_EVIDENCE_GATE",
            "memory_registered": "PRESERVE_AS_EXPERIENCE_MEMORY_WITH_PROVENANCE",
            "history_absorbed": "PRESERVE_IN_GIT_HISTORY_NOT_ACTIVE_RUNTIME",
            "history_infrastructure": "PRESERVE_AS_INFRASTRUCTURE_HISTORY_NOT_COGNITIVE_MEMORY",
            "unknown": "FAIL_CLOSED",
        },
        "rows": rows,
        "automatic_branch_deletion": False,
        "automatic_canonical_promotion": False,
        "claim_boundary": (
            "Classification preserves all refs. HISTORY means retained in Git history, MEMORY means "
            "registered experience semantics, ACTIVE_CANDIDATE means separate admission is still required. "
            "No branch name alone promotes code into canonical runtime."
        ),
    }
    artifact["artifact_digest"] = _digest(artifact)

    memory_rows = [
        {
            "branch": row["branch"],
            "classification": row["classification"],
            "head_sha": row["head_sha"],
            "registered_in_experience_registry": row["registered_in_experience_registry"],
        }
        for row in rows
        if row["classification"].startswith("MEMORY_")
    ]
    memory_index = {
        "schema": "yado.branch_memory_index.v1",
        "status": "PASS_MEMORY_INDEX",
        "source_artifact_digest": artifact["artifact_digest"],
        "memory_ref_count": len(memory_rows),
        "memory_refs": memory_rows,
        "automatic_runtime_activation": False,
    }
    memory_index["artifact_digest"] = _digest(memory_index)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    MEMORY_OUT.write_text(json.dumps(memory_index, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "status": artifact["status"],
                "remote_branch_count": artifact["remote_branch_count"],
                "classification_counts": artifact["classification_counts"],
                "active_candidate_count": len(admission_candidates),
                "memory_ref_count": len(memory),
                "history_ref_count": len(history),
                "withheld_count": len(withheld),
                "artifact_digest": artifact["artifact_digest"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
