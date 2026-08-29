from __future__ import annotations
from pathlib import Path
import subprocess, json, hashlib, sys, os

ROOT = Path(__file__).resolve().parent
PKG = ROOT / "yado_rc8_v36"
sys.path.insert(0, str(PKG))

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive

V37_REF = "origin/yado-rc8-v37-digital-consciousness"
META_PATH = "runtime/v37_overlay_meta.json"

def git_show(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{V37_REF}:{path}"], cwd=ROOT.parent)

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

meta = json.loads(git_show(META_PATH).decode("utf-8"))
mismatches = []
for name, expected in meta["files"].items():
    data = git_show(f"runtime/v37_overlay/{name}")
    actual = {"bytes": len(data), "sha256": sha256(data)}
    if actual["sha256"] != expected["sha256"] or actual["bytes"] != expected["bytes"]:
        mismatches.append({
            "file": name,
            "expected": expected,
            "actual": actual,
            "byte_delta": actual["bytes"] - expected["bytes"],
        })

task = {
    "task_id": "YADO-V37-INTEGRITY-SELF-REPAIR-001",
    "goal": "Diagnose the failed v37 synchronization and choose the next repair action using YADO's own audit, integrity, development and workspace mechanisms.",
    "failure": "OVERLAY_HASH_MISMATCH:test_yado_rc8_self_audit_consistency_v1.py",
    "constraints": [
        "Do not weaken, bypass, disable, or remove content-addressed integrity checks.",
        "Preserve fail-closed behavior.",
        "Preserve v36 verified proof lineage until a new external run passes.",
        "Prefer the smallest evidence-backed repair and require regression plus fresh verification before promotion.",
    ],
    "mismatches": mismatches,
    "v36_verified_run_id": 33266617685,
}

db = ROOT / "yado_v37_repair_task.sqlite"
k = UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(db))
try:
    pre = {
        "audit_snapshot": k.audit_snapshot(),
        "self_audit_registry": k.self_audit_registry(),
        "development_priority": k.development_priority(),
        "integrity_control_plane": k.integrity_control_plane(),
    }
    items = [
        dict(
            item_id="v37-failure",
            source="github-actions-run-33266924600",
            source_kind="external",
            content={"failure": task["failure"], "stage": "Apply content-addressed v37 overlay and boot"},
            confidence=1.0,
            goal_relevance=1.0,
            novelty=0.9,
            epistemic_risk=0.05,
            tags=("v37", "integrity", "failure"),
        ),
        dict(
            item_id="v37-mismatch-evidence",
            source="git-content-addressed-readback",
            source_kind="external",
            content={"mismatches": mismatches},
            confidence=1.0,
            goal_relevance=1.0,
            novelty=0.95,
            epistemic_risk=0.05,
            tags=("hash", "overlay", "evidence"),
        ),
        dict(
            item_id="v37-repair-constraints",
            source="task-contract",
            source_kind="external",
            content={"constraints": task["constraints"]},
            confidence=1.0,
            goal_relevance=1.0,
            novelty=0.4,
            epistemic_risk=0.0,
            tags=("fail-closed", "repair", "constraints"),
        ),
    ]
    result = k.digital_conscious_cycle(
        goal=task["goal"],
        items=items,
        consumers={
            "SELF_AUDIT": lambda xs: k.audit_snapshot(),
            "INTEGRITY": lambda xs: k.integrity_control_plane(),
            "DEVELOPMENT": lambda xs: k.development_priority(),
            "REGISTRY": lambda xs: k.self_audit_registry(),
        },
        metacognitive_action=None,
        context="v37_sync_integrity_failure",
        action="diagnose_and_select_repair",
        possible_outcomes=(
            "REBUILD_OVERLAY_FROM_CANONICAL_BYTES",
            "RECOMPUTE_METADATA_FROM_VERIFIED_ACTUAL_BYTES",
            "RESTORE_EXPECTED_BYTE_REPRESENTATION",
            "ROLLBACK_TO_V36_AND_REDERIVE_V37",
            "SEEK_MORE_EVIDENCE",
        ),
        observed_outcome=None,
        proposed_belief_ids=("v37-failure", "v37-mismatch-evidence"),
    )
    post = {
        "audit_snapshot": k.audit_snapshot(),
        "self_audit_registry": k.self_audit_registry(),
        "development_priority": k.development_priority(),
        "integrity_control_plane": k.integrity_control_plane(),
        "digital_consciousness_snapshot": k.digital_consciousness_snapshot(),
    }
finally:
    k.close()

receipt = {
    "schema": "yado.rc8.v37.integrity.self_repair.task.v1",
    "status": "TASK_EXECUTED_BY_YADO_NATIVE_RUNTIME",
    "task": task,
    "pre": pre,
    "kernel_result": result,
    "post": post,
    "host_role": "transport_and_observation_only",
    "repair_applied": False,
    "promotion_applied": False,
    "github_run_id": os.getenv("GITHUB_RUN_ID"),
    "github_sha": os.getenv("GITHUB_SHA"),
}
out = ROOT / "yado_v37_integrity_self_repair_task_receipt.json"
out.write_text(json.dumps(receipt, indent=2, sort_keys=True, default=str) + "\n")
print(json.dumps(receipt, indent=2, sort_keys=True, default=str))
