from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]

CORE_PATH = ROOT / "canonical" / "yado-unified-core-v1.json"
HEAD_PATH = ROOT / "canonical" / "yado-main-head-g2.json"
REGISTRY_PATH = ROOT / "canonical" / "yado-unified-experience-registry-v1.json"
LEDGER_PATH = ROOT / "architecture" / "evolution-ledger.json"
CONTEXT_MANIFEST_PATH = ROOT / "canonical" / "yado-unified-context-kernel-v1.json"


def _load(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


class UnifiedContextKernel:
    """Single active YADO context over canonical state plus historical memory."""

    def __init__(self) -> None:
        self.context_manifest = _load(CONTEXT_MANIFEST_PATH)
        self.core = _load(CORE_PATH)
        self.head = _load(HEAD_PATH)
        self.registry = _load(REGISTRY_PATH)
        self.ledger = _load(LEDGER_PATH)
        self._validate()

    def _validate(self) -> None:
        if self.context_manifest.get("status") != "CANONICAL_ACTIVE":
            raise RuntimeError("CONTEXT_KERNEL_NOT_CANONICAL_ACTIVE")
        if self.context_manifest.get("kernel_id") != "YADO_UNIFIED_CONTEXT_KERNEL_V1":
            raise RuntimeError("UNEXPECTED_CONTEXT_KERNEL_ID")
        if not self.core.get("canonical_active"):
            raise RuntimeError("UNIFIED_CORE_NOT_CANONICAL")
        if self.head.get("status") != "HEAD":
            raise RuntimeError("CANONICAL_HEAD_NOT_ACTIVE")
        if self.head.get("generation_id") != self.core.get("generation"):
            raise RuntimeError("GENERATION_SPLIT_BRAIN")

        active = [
            b for b in self.registry.get("branches", [])
            if b.get("mode") == "ACTIVE_LINEAGE"
        ]
        if len(active) != 1:
            raise RuntimeError(f"EXPECTED_ONE_ACTIVE_LINEAGE_GOT_{len(active)}")
        if active[0].get("branch") != self.context_manifest["branch_policy"]["active_branch"]:
            raise RuntimeError("ACTIVE_BRANCH_MISMATCH")

        non_active = [
            b for b in self.registry.get("branches", [])
            if b.get("branch") != active[0].get("branch")
        ]
        invalid = [
            b.get("branch") for b in non_active
            if b.get("mode") != "EXPERIENCE_ONLY"
        ]
        if invalid:
            raise RuntimeError("NON_ACTIVE_BRANCH_NOT_MEMORY_ONLY:" + ",".join(invalid))

        if self.ledger.get("current_head") != self.head.get("generation_id"):
            raise RuntimeError("LEDGER_HEAD_MISMATCH")

    def snapshot(self) -> Dict[str, Any]:
        branches = self.registry.get("branches", [])
        active = [b for b in branches if b.get("mode") == "ACTIVE_LINEAGE"]
        memory = [b for b in branches if b.get("mode") == "EXPERIENCE_ONLY"]
        events = self.ledger.get("events", [])
        return {
            "kernel_id": self.context_manifest["kernel_id"],
            "generation": self.head.get("generation_id"),
            "active_head": self.ledger.get("current_head"),
            "current_frontier": self.head.get("current_frontier"),
            "active_lineage_count": len(active),
            "historical_branch_memory_count": len(memory),
            "causal_history_event_count": self.ledger.get("event_count", len(events)),
            "open_deficits": list(self.ledger.get("open_deficits", [])),
            "g3_genesis_performed": bool(self.head.get("g3_genesis_performed", False)),
            "single_context_invariant": True,
        }

    def retrieve_branch_history(
        self,
        *,
        tags: Optional[List[str]] = None,
        branch: Optional[str] = None,
        limit: int = 8,
    ) -> List[Dict[str, Any]]:
        tags = [t.lower() for t in (tags or [])]
        out: List[Dict[str, Any]] = []
        for item in self.registry.get("branches", []):
            if item.get("mode") != "EXPERIENCE_ONLY":
                continue
            if branch and item.get("branch") != branch:
                continue
            item_tags = [str(t).lower() for t in item.get("tags", [])]
            lessons = [str(x).lower() for x in item.get("lessons", [])]
            haystack = item_tags + lessons + [str(item.get("role", "")).lower()]
            if tags and not all(any(t in h for h in haystack) for t in tags):
                continue
            out.append({
                "branch": item.get("branch"),
                "role": item.get("role"),
                "registered_head_sha": item.get("head_sha"),
                "evidence": item.get("evidence", []),
                "lessons": item.get("lessons", []),
                "mode": item.get("mode"),
            })
            if len(out) >= limit:
                break
        return out

    def recent_causal_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        events = self.ledger.get("events", [])
        return events[-max(1, int(limit)):]


if __name__ == "__main__":
    kernel = UnifiedContextKernel()
    print(json.dumps(kernel.snapshot(), indent=2, sort_keys=True))
