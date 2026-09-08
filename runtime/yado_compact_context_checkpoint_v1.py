from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

PATHS = {
    "head": ROOT / "canonical" / "yado-main-head-g2.json",
    "core": ROOT / "canonical" / "yado-unified-core-v1.json",
    "registry": ROOT / "canonical" / "yado-unified-experience-registry-v1.json",
    "ledger": ROOT / "architecture" / "evolution-ledger.json",
    "graph": ROOT / "audits" / "yado-g2-module-dependency-graph-v1.json",
    "audit": ROOT / "audits" / "yado-full-kernel-audit-v1-report.json",
}
DEFAULT_OUTPUT = ROOT / "canonical" / "yado-compact-context-checkpoint-v1.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_checkpoint(recent_events: int = 4) -> dict[str, Any]:
    head = _load(PATHS["head"])
    core = _load(PATHS["core"])
    registry = _load(PATHS["registry"])
    ledger = _load(PATHS["ledger"])
    graph = _load(PATHS["graph"])
    audit = _load(PATHS["audit"])

    frontier = list(ledger.get("open_deficits", []))
    if len(frontier) != 1:
        raise RuntimeError(f"EXPECTED_ONE_OPEN_FRONTIER_GOT_{len(frontier)}")
    frontier_id = str(frontier[0])

    if head.get("current_frontier") != frontier_id:
        raise RuntimeError("HEAD_FRONTIER_MISMATCH")
    if core.get("current_frontier") != frontier_id:
        raise RuntimeError("CORE_FRONTIER_MISMATCH")
    if head.get("canonical_head_digest") != ledger.get("current_head_digest"):
        raise RuntimeError("HEAD_LEDGER_DIGEST_MISMATCH")
    if audit.get("status") != "PASS":
        raise RuntimeError("FULL_KERNEL_AUDIT_NOT_PASS")
    if list(graph.get("orphans", [])):
        raise RuntimeError("ACTIVE_MODULE_ORPHANS_PRESENT")

    branches = list(registry.get("branches", []))
    active = [b for b in branches if b.get("mode") == "ACTIVE_LINEAGE"]
    history = [b for b in branches if b.get("mode") == "EXPERIENCE_ONLY"]
    if len(active) != 1:
        raise RuntimeError(f"EXPECTED_ONE_ACTIVE_LINEAGE_GOT_{len(active)}")

    events = list(ledger.get("events", []))
    recent = []
    for e in events[-max(1, int(recent_events)):]:
        recent.append({
            "index": e.get("index"),
            "event_id": e.get("event_id"),
            "event_type": e.get("event_type"),
            "status": e.get("status"),
            "run_id": e.get("run_id"),
            "event_hash": e.get("event_hash"),
            "deficit": e.get("deficit"),
            "canonical_mutation": bool(e.get("canonical_mutation", False)),
        })

    closure = dict(registry.get("closure", {}))
    counts = dict(audit.get("counts", {}))

    return {
        "schema": "yado.compact_context_checkpoint.v1",
        "status": "PASS",
        "purpose": "HOT_CONTEXT_FOR_FAST_SESSION_BOOTSTRAP_WITH_FULL_EVIDENCE_LAZY_HYDRATION",
        "generation": head.get("generation_id"),
        "active_lineage": active[0].get("branch"),
        "current_frontier": frontier_id,
        "open_deficits": frontier,
        "canonical_head_digest": head.get("canonical_head_digest"),
        "g3_genesis_performed": bool(head.get("g3_genesis_performed", False)),
        "ledger": {
            "event_count": ledger.get("event_count", len(events)),
            "latest_event": recent[-1] if recent else None,
            "recent_events": recent,
        },
        "active_graph": {
            "active_module_count": graph.get("active_module_count"),
            "role_counts": graph.get("role_counts", {}),
            "semantic_edge_count": graph.get("semantic_edge_count"),
            "static_import_edge_count": graph.get("static_import_edge_count"),
            "orphans": graph.get("orphans", []),
            "graph_digest": graph.get("graph_digest"),
        },
        "branch_memory": {
            "registered_branch_count": len(branches),
            "historical_branch_count": len(history),
            "all_non_active_branches_history_only": closure.get("all_non_active_branches_history_only"),
            "all_remote_tips_in_active_ancestry": closure.get("all_current_remote_tips_contained_in_active_ancestry"),
            "physical_branches_preserved": closure.get("physical_branches_preserved"),
        },
        "full_audit": {
            "status": audit.get("status"),
            "audited_commit": audit.get("audited_commit"),
            "findings_count": len(audit.get("findings", [])),
            "runtime_python_files": counts.get("runtime_python_files"),
            "json_files": counts.get("json_files"),
            "workflow_files": counts.get("workflow_files"),
            "active_runtime_sources": counts.get("active_runtime_sources"),
            "duplicate_python_groups": counts.get("duplicate_python_groups"),
            "module_stem_collisions": counts.get("module_stem_collisions"),
        },
        "hydration": {
            "normal_start": [
                "canonical/yado-compact-context-checkpoint-v1.json"
            ],
            "hydrate_on_change_or_dispute": [
                "canonical/yado-main-head-g2.json",
                "canonical/yado-unified-core-v1.json",
                "architecture/evolution-ledger.json",
                "canonical/yado-unified-experience-registry-v1.json",
                "audits/yado-g2-module-dependency-graph-v1.json",
                "audits/yado-full-kernel-audit-v1-report.json",
            ],
            "cold_history_dirs": [
                "candidates/",
                "receipts/",
                "experience/",
                "quarantine/",
            ],
            "rule": "NORMAL SESSION CONTINUATION READS THE COMPACT CHECKPOINT FIRST. FULL HISTORY IS HYDRATED ONLY FOR A SPECIFIC EVIDENCE QUESTION, DIGEST MISMATCH, FRONTIER CHANGE, AUDIT FAILURE, OR BRANCH-LINEAGE CHANGE.",
        },
    }


def write_checkpoint(path: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    checkpoint = build_checkpoint()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(checkpoint, indent=2) + "\n", encoding="utf-8")
    return checkpoint


if __name__ == "__main__":
    checkpoint = write_checkpoint()
    print(json.dumps(checkpoint, indent=2, sort_keys=True))
