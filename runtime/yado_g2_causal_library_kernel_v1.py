from __future__ import annotations
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "architecture/yado-g2-kernel-component-library-v1.json"
GEN = ROOT / "architecture/yado-g2-genetic-lineage-library-v1.json"
ARCH = ROOT / "architecture/yado-g2-causal-library-kernel-architecture-v1.json"
TRAINING = ROOT / "architecture/yado-g2-causal-training-binding-v1.json"
LEARNING_CYCLE = ROOT / "architecture/yado-g2-read-understand-apply-learn-cycle-v1.json"
DYNAMIC_MEMORY = ROOT / "experience/yado-g2-dynamic-experience-memory-v1.json"

class G2CausalLibraryKernelV1:
    COMPONENT_ID = "YADO_G2_CAUSAL_LIBRARY_KERNEL_V1"

    def __init__(self, root: Path | None = None):
        self.root = Path(root or ROOT)
        self.library = self._load(self.root / LIB.relative_to(ROOT))
        self.genetics = self._load(self.root / GEN.relative_to(ROOT))
        self.architecture = self._load(self.root / ARCH.relative_to(ROOT))
        self.training = self._load(self.root / TRAINING.relative_to(ROOT))
        self.learning_cycle = self._load(self.root / LEARNING_CYCLE.relative_to(ROOT))
        self.dynamic_memory = self._load(self.root / DYNAMIC_MEMORY.relative_to(ROOT))

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

        training_state = self.library.get("training_state") or {}
        if self.training.get("status") not in {"ACTIVE_DEVELOPMENT_SHADOW_TRAINED","ACTIVE_DEVELOPMENT_SHADOW_TRAINED_AND_CYCLE_CONSOLIDATED"}:
            raise ValueError("TRAINING_BINDING_NOT_ACTIVE")
        if training_state.get("experience_digest") != self.training.get("experience_digest"):
            raise ValueError("TRAINING_DIGEST_LIBRARY_BINDING_MISMATCH")
        if self.training.get("safety", {}).get("canonical_mutation") is not False:
            raise ValueError("TRAINING_CANONICAL_MUTATION_FORBIDDEN")
        if self.training.get("safety", {}).get("third_party_code_executed") is not False:
            raise ValueError("TRAINING_THIRD_PARTY_EXECUTION_FORBIDDEN")
        if self.training.get("safety", {}).get("automatic_promotion") is not False:
            raise ValueError("TRAINING_AUTO_PROMOTION_FORBIDDEN")
        if self.training.get("safety", {}).get("g3_genesis") is not False:
            raise ValueError("TRAINING_G3_FORBIDDEN")
        if self.learning_cycle.get("status") != "PASS_SHADOW_LEARNING_CYCLE_V1":
            raise ValueError("LEARNING_CYCLE_NOT_PASS")
        if self.learning_cycle.get("invariants", {}).get("canonical_mutation") is not False:
            raise ValueError("LEARNING_CYCLE_CANONICAL_MUTATION_FORBIDDEN")
        if self.learning_cycle.get("invariants", {}).get("automatic_promotion") is not False:
            raise ValueError("LEARNING_CYCLE_AUTO_PROMOTION_FORBIDDEN")
        if not self.learning_cycle.get("unresolved_deficits"):
            raise ValueError("LEARNING_CYCLE_MUST_RETAIN_OPEN_DEFICITS")
        if self.dynamic_memory.get("status") != "PASS_SHADOW_G2_DYNAMIC_EXPERIENCE_MEMORY_V1":
            raise ValueError("DYNAMIC_EXPERIENCE_MEMORY_NOT_PASS")
        dm_checks = self.dynamic_memory.get("checks") or {}
        if not all(dm_checks.values()):
            raise ValueError("DYNAMIC_EXPERIENCE_MEMORY_CHECK_FAILED")
        for row in self.dynamic_memory.get("branches", []):
            if row.get("inventory_class") == "RAW_BRANCH_INVENTORY_ONLY":
                if row.get("semantic_use_allowed") is not False or row.get("lessons"):
                    raise ValueError("RAW_BRANCH_SEMANTIC_LEAK:" + str(row.get("branch")))
        cb = self.training.get("causal_binding") or {}
        if cb.get("source_layer") != "L1_MEMORY_EXPERIENCE" or cb.get("conditioning_layer") != "L2_EXPERIENCE_CONDITIONING":
            raise ValueError("TRAINING_CAUSAL_LAYER_BINDING_MISMATCH")
        return {
            "status": "PASS_CAUSAL_LIBRARY_KERNEL_V1",
            "normal_dispatch_count": len(normal),
            "compatibility_fallback_count": len(fallback),
            "layer_count": len(layers),
            "forward_edge_count": len(self.architecture["forward_edges"]),
            "feedback_edge_count": len(self.architecture["feedback_edges"]),
            "canonical_head_digest": self.library["baseline"]["canonical_head_digest"],
            "training_experience_digest": self.training["experience_digest"],
            "training_source_count": int(self.training["corpus"]["source_count"]),
            "training_fetched_count": int(self.training["corpus"]["fetched_count"]),
            "learning_cycle_status": self.learning_cycle["status"],
            "learning_cycle_latest_experience_digest": self.training["learning_cycle"]["latest_experience_digest"],
            "dynamic_memory_experience_digest": self.dynamic_memory["experience_digest"],
            "dynamic_memory_branch_count": int(self.dynamic_memory["remote_branch_count"]),
            "dynamic_memory_raw_lineage_count": int(self.dynamic_memory["raw_lineage_count"]),
            "dynamic_memory_rederived_count": int(self.dynamic_memory.get("dynamic_rederived_count", 0)),
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

    def training_snapshot(self):
        return {
            "status": self.training["status"],
            "experience_digest": self.training["experience_digest"],
            "training_run_id": self.training["training_run_id"],
            "source_count": self.training["corpus"]["source_count"],
            "fetched_count": self.training["corpus"]["fetched_count"],
            "failed_count": self.training["corpus"]["failed_count"],
            "curriculum": list(self.training["curriculum"]),
            "causal_binding": dict(self.training["causal_binding"]),
            "automatic_promotion": False,
        }

    def learning_cycle_snapshot(self):
        return {
            "status": self.learning_cycle["status"],
            "cycle_id": self.learning_cycle["cycle_id"],
            "stage_count": len(self.learning_cycle["stages"]),
            "causal_lesson_count": len(self.learning_cycle["causal_lessons"]),
            "unresolved_deficits": [x["code"] for x in self.learning_cycle["unresolved_deficits"]],
            "latest_experience_digest": self.training["learning_cycle"]["latest_experience_digest"],
            "next_cycle_policy": list(self.learning_cycle["next_cycle_policy"]),
            "automatic_promotion": False,
        }

    def dynamic_memory_snapshot(self):
        return {
            "status": self.dynamic_memory["status"],
            "experience_digest": self.dynamic_memory["experience_digest"],
            "remote_branch_count": self.dynamic_memory["remote_branch_count"],
            "canonical_registry_branch_count": self.dynamic_memory["canonical_registry_branch_count"],
            "raw_lineage_count": self.dynamic_memory["raw_lineage_count"],
            "raw_lineage_branches": list(self.dynamic_memory["raw_lineage_branches"]),
            "dynamic_rederived_count": self.dynamic_memory.get("dynamic_rederived_count", 0),
            "dynamic_rederived_branches": list(self.dynamic_memory.get("dynamic_rederived_branches", [])),
            "next_required_capability": self.dynamic_memory["next_required_capability"],
            "raw_branch_inventory_is_not_semantic_knowledge": self.dynamic_memory["policy"]["raw_branch_inventory_is_not_semantic_knowledge"],
            "automatic_promotion": False,
        }

    def causal_trace(self, contract: str):
        route = self.route_contract(contract)
        return {
            "kernel_id": self.COMPONENT_ID,
            "contract": contract,
            "route": route,
            "layers": [x["id"] for x in sorted(self.architecture["layers"], key=lambda z: z["index"])],
            "feedback": [dict(x) for x in self.architecture["feedback_edges"]],
            "training": self.training_snapshot(),
            "learning_cycle": self.learning_cycle_snapshot(),
            "dynamic_memory": self.dynamic_memory_snapshot(),
            "automatic_promotion": False,
        }

if __name__ == "__main__":
    k = G2CausalLibraryKernelV1()
    print(json.dumps(k.validate(), indent=2, sort_keys=True))
