from __future__ import annotations
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "architecture/yado-g2-kernel-component-library-v1.json"
GEN = ROOT / "architecture/yado-g2-genetic-lineage-library-v1.json"
ARCH = ROOT / "architecture/yado-g2-causal-library-kernel-architecture-v1.json"

class G2CausalLibraryKernelV1:
    COMPONENT_ID = "YADO_G2_CAUSAL_LIBRARY_KERNEL_V1"

    def __init__(self, root: Path | None = None):
        self.root = Path(root or ROOT)
        self.library = self._load(self.root / LIB.relative_to(ROOT))
        self.genetics = self._load(self.root / GEN.relative_to(ROOT))
        self.architecture = self._load(self.root / ARCH.relative_to(ROOT))

    @staticmethod
    def _load(path: Path):
        return json.loads(path.read_text(encoding="utf-8"))

    def validate(self):
        normal = list(self.library["normal_dispatch_components"])
        fallback = list(self.library["compatibility_fallback_components"])
        if len(normal) != len(set(normal)):
            raise ValueError("DUPLICATE_NORMAL_DISPATCH_COMPONENT")
        if len(fallback) != len(set(fallback)):
            raise ValueError("DUPLICATE_FALLBACK_COMPONENT")
        if set(normal) & set(fallback):
            raise ValueError("NORMAL_FALLBACK_OVERLAP")
        if len(normal) != 26 or len(fallback) != 5:
            raise ValueError("LIBRARY_COUNT_MISMATCH")
        if self.library["baseline"]["canonical_head_digest"] != self.genetics["current_head_digest"]:
            raise ValueError("HEAD_DIGEST_GENETICS_MISMATCH")

        layers = self.architecture["layers"]
        ids = [x["id"] for x in layers]
        if len(ids) != len(set(ids)):
            raise ValueError("DUPLICATE_LAYER_ID")
        order = {x["id"]: int(x["index"]) for x in layers}
        if sorted(order.values()) != list(range(len(layers))):
            raise ValueError("LAYER_INDEX_GAP")
        for a, b in self.architecture["forward_edges"]:
            if a not in order or b not in order:
                raise ValueError("UNKNOWN_FORWARD_LAYER")
            if order[a] >= order[b]:
                raise ValueError("NON_CAUSAL_FORWARD_EDGE")
        for edge in self.architecture["feedback_edges"]:
            if edge["from"] not in order or edge["to"] not in order:
                raise ValueError("UNKNOWN_FEEDBACK_LAYER")

        owners = self.library["deduplication_policy"]["contract_owners"]
        if owners["RELATION_START_TO_STATE"] == owners["GENERAL_LOGIC_FALLBACK"]:
            raise ValueError("LOGIC_PARENT_CHILD_OWNER_COLLISION")
        if owners["EVENT_SEQUENCE_TO_BOOLEAN"] == owners["GENERAL_THINKING_FALLBACK"]:
            raise ValueError("THINKING_PARENT_CHILD_OWNER_COLLISION")
        if owners["TRI_ORGAN_CONTRACT_ROUTING"] == owners["GENERAL_INTELLIGENCE_FALLBACK"]:
            raise ValueError("INTELLIGENCE_PARENT_CHILD_OWNER_COLLISION")

        chrom = self.genetics["chromosomes"]
        for name in ("LOGIC", "THINKING", "INTELLIGENCE"):
            if "rollback_parent" not in chrom[name]:
                raise ValueError("MISSING_ROLLBACK_PARENT:" + name)
        if self.genetics["tri_organ_genome"]["automatic_promotion"] is not False:
            raise ValueError("AUTO_PROMOTION_MUST_BE_FALSE")
        return {
            "status": "PASS_CAUSAL_LIBRARY_KERNEL_V1",
            "normal_dispatch_count": len(normal),
            "compatibility_fallback_count": len(fallback),
            "layer_count": len(layers),
            "forward_edge_count": len(self.architecture["forward_edges"]),
            "feedback_edge_count": len(self.architecture["feedback_edges"]),
            "canonical_head_digest": self.library["baseline"]["canonical_head_digest"],
            "g3_genesis": self.architecture["g3_genesis"],
        }

    def route_contract(self, contract: str):
        owners = self.library["deduplication_policy"]["contract_owners"]
        direct = {
            "RELATION_START_TO_STATE": owners["RELATION_START_TO_STATE"],
            "EVENT_SEQUENCE_TO_BOOLEAN": owners["EVENT_SEQUENCE_TO_BOOLEAN"],
        }
        if contract in direct:
            return {"status": "PRIMARY_TRI_ORGAN", "component_id": direct[contract]}
        return {
            "status": "FALLBACK_REQUIRED",
            "logic": owners["GENERAL_LOGIC_FALLBACK"],
            "thinking": owners["GENERAL_THINKING_FALLBACK"],
            "intelligence": owners["GENERAL_INTELLIGENCE_FALLBACK"],
        }

    def causal_trace(self, contract: str):
        route = self.route_contract(contract)
        return {
            "kernel_id": self.COMPONENT_ID,
            "contract": contract,
            "route": route,
            "layers": [x["id"] for x in sorted(self.architecture["layers"], key=lambda z: z["index"])],
            "feedback": [dict(x) for x in self.architecture["feedback_edges"]],
            "automatic_promotion": False,
        }

if __name__ == "__main__":
    k = G2CausalLibraryKernelV1()
    print(json.dumps(k.validate(), indent=2, sort_keys=True))
