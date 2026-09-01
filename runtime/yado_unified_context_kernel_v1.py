from __future__ import annotations

import copy, hashlib, json, sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'runtime'))
from yado_evolution_ledger_v2 import validate_ledger_v2

CORE_PATH = ROOT / "canonical" / "yado-unified-core-v1.json"
HEAD_PATH = ROOT / "canonical" / "yado-main-head-g2.json"
REGISTRY_PATH = ROOT / "canonical" / "yado-unified-experience-registry-v1.json"
LEDGER_PATH = ROOT / "architecture" / "evolution-ledger.json"
CONTEXT_MANIFEST_PATH = ROOT / "canonical" / "yado-unified-context-kernel-v1.json"

def _load(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def _canon(o:Any)->str:
    return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)

def _digest_without(o:Dict[str,Any],field:str)->str:
    x=copy.deepcopy(o);x.pop(field,None)
    return hashlib.sha256(_canon(x).encode()).hexdigest()

class UnifiedContextKernel:
    """Single active YADO context. The causal ledger is authoritative for developmental frontier."""

    def __init__(self) -> None:
        self.context_manifest = _load(CONTEXT_MANIFEST_PATH)
        self.core = _load(CORE_PATH)
        self.head = _load(HEAD_PATH)
        self.registry = _load(REGISTRY_PATH)
        self.ledger = _load(LEDGER_PATH)
        self._validate()

    def _ledger_frontier(self)->str:
        xs=self.ledger.get("open_deficits",[])
        if len(xs)!=1:
            raise RuntimeError(f"EXPECTED_ONE_OPEN_FRONTIER_GOT_{len(xs)}")
        return str(xs[0])

    def _validate(self) -> None:
        validate_ledger_v2(self.ledger)
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
        if self.ledger.get("current_head") != self.head.get("generation_id"):
            raise RuntimeError("LEDGER_HEAD_MISMATCH")
        if self.ledger.get("current_head_digest") != self.head.get("canonical_head_digest"):
            raise RuntimeError("LEDGER_HEAD_DIGEST_MISMATCH")
        if _digest_without(self.head,"canonical_head_digest") != self.head.get("canonical_head_digest"):
            raise RuntimeError("CANONICAL_HEAD_CONTENT_DIGEST_MISMATCH")

        frontier=self._ledger_frontier()
        if self.head.get("current_frontier") != frontier:
            raise RuntimeError("HEAD_FRONTIER_SPLIT_BRAIN")
        if self.core.get("current_frontier") != frontier:
            raise RuntimeError("CORE_FRONTIER_SPLIT_BRAIN")

        active = [b for b in self.registry.get("branches", []) if b.get("mode") == "ACTIVE_LINEAGE"]
        if len(active) != 1:
            raise RuntimeError(f"EXPECTED_ONE_ACTIVE_LINEAGE_GOT_{len(active)}")
        expected_branch=self.context_manifest["branch_policy"]["active_branch"]
        if active[0].get("branch") != expected_branch:
            raise RuntimeError("ACTIVE_BRANCH_MISMATCH")
        generation=self.head.get("generation_id")
        invalid=[]
        for b in self.registry.get("branches",[]):
            if b.get("branch")==expected_branch:
                continue
            if b.get("mode")!="EXPERIENCE_ONLY" or b.get("history_only") is not True or b.get("runtime_active") is not False:
                invalid.append(str(b.get("branch")))
            if b.get("closed_into_generation")!=generation:
                invalid.append(str(b.get("branch"))+":NOT_CLOSED_INTO_G2")
        if invalid:
            raise RuntimeError("NON_ACTIVE_BRANCH_NOT_CLOSED_HISTORY_ONLY:"+",".join(invalid))

    def snapshot(self) -> Dict[str, Any]:
        branches = self.registry.get("branches", [])
        active = [b for b in branches if b.get("mode") == "ACTIVE_LINEAGE"]
        memory = [b for b in branches if b.get("mode") == "EXPERIENCE_ONLY"]
        events = self.ledger.get("events", [])
        return {
            "kernel_id": self.context_manifest["kernel_id"],
            "generation": self.head.get("generation_id"),
            "active_head": self.ledger.get("current_head"),
            "current_frontier": self._ledger_frontier(),
            "frontier_source": "architecture/evolution-ledger.json:open_deficits",
            "head_frontier_snapshot": self.head.get("current_frontier"),
            "active_lineage_count": len(active),
            "historical_branch_memory_count": len(memory),
            "causal_history_event_count": self.ledger.get("event_count", len(events)),
            "open_deficits": copy.deepcopy(self.ledger.get("open_deficits", [])),
            "g3_genesis_performed": bool(self.head.get("g3_genesis_performed", False)),
            "single_context_invariant": True,
        }

    def retrieve_branch_history(self, *, tags: Optional[List[str]] = None, branch: Optional[str] = None, limit: int = 8) -> List[Dict[str, Any]]:
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
                "closed_into_generation": item.get("closed_into_generation"),
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
