from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Callable
import hashlib
import json


def _canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _digest(obj: Any) -> str:
    return hashlib.sha256(_canon(obj).encode("utf-8")).hexdigest()


class G2CausalExternalLearningBindingV1:
    COMPONENT_ID = "RUNTIME-G2-CAUSAL-EXTERNAL-LEARNING-BINDING-V1"
    STATE_SCHEMA = "yado.g2.causal_external_learning_binding.state.v1"
    MAX_EPISODES = 128
    CAUSAL_RELATION = (
        ("MEMORY", "THINKING"),
        ("THINKING", "LOGIC"),
        ("LOGIC", "INTELLIGENCE"),
        ("INTELLIGENCE", "ACTION_READ_ONLY_EXTERNAL"),
        ("ACTION_READ_ONLY_EXTERNAL", "RESULT"),
        ("RESULT", "MEMORY_FEEDBACK"),
    )
    REQUIRED_NODES = {x for edge in CAUSAL_RELATION for x in edge}
    RECEIPTS = {
        "v1": "receipts/yado-external-source-evolution-v1.json",
        "v2": "receipts/yado-autonomous-meta-source-evolution-v2.json",
        "v3": "receipts/yado-autonomous-grammar-extension-v3.json",
        "v4": "receipts/yado-autonomous-meta-grammar-evolution-v4.json",
        "v5": "receipts/yado-autonomous-external-library-discovery-v5.json",
        "v6": "receipts/yado-autonomous-open-catalog-discovery-v6.json",
    }
    EXPECTED = {
        "v1": "PASS_SHADOW_G2_EXTERNAL_SOURCE_EVOLUTION_V1",
        "v2": "PASS_SHADOW_G2_AUTONOMOUS_META_SOURCE_EVOLUTION_V2",
        "v3": "PASS_SHADOW_G2_AUTONOMOUS_GRAMMAR_EXTENSION_V3",
        "v4": "PASS_SHADOW_G2_AUTONOMOUS_META_GRAMMAR_EVOLUTION_V4",
        "v5": "PASS_SHADOW_G2_AUTONOMOUS_EXTERNAL_LIBRARY_DISCOVERY_V5",
        "v6": "PASS_SHADOW_G2_AUTONOMOUS_OPEN_CATALOG_DISCOVERY_V6",
    }

    def __init__(self, repo_root: Path | str, artifact: dict[str, Any], memory_search: Callable[..., list[dict[str, Any]]], thinking: Callable[[Any], dict[str, Any]], logic: Callable[[Any, Any], dict[str, Any]], intelligence: Callable[[dict[str, Any]], dict[str, Any]], meta_decide_evidence: Callable[[dict[str, Any]], dict[str, Any]]):
        self.repo = Path(repo_root)
        self.artifact = deepcopy(artifact)
        self.memory_search = memory_search
        self.thinking = thinking
        self.logic = logic
        self.intelligence = intelligence
        self.meta_decide_evidence = meta_decide_evidence
        self._episodes: list[dict[str, Any]] = []
        if self.artifact.get("component_id") != self.COMPONENT_ID or self.artifact.get("status") != "CANONICAL_ACTIVE":
            raise ValueError("CAUSAL_EXTERNAL_BINDING_ARTIFACT_NOT_ACTIVE")
        safety = self.artifact.get("safety") or {}
        if not (safety.get("read_only_external") is True and safety.get("credentials_allowed") is False and safety.get("external_writes_allowed") is False and safety.get("external_models_allowed") is False):
            raise ValueError("CAUSAL_EXTERNAL_BINDING_SAFETY_MISMATCH")
        if self.artifact.get("g3_genesis_performed") is not False:
            raise ValueError("CAUSAL_EXTERNAL_BINDING_G3_FORBIDDEN")

    def _load(self, relative: str) -> dict[str, Any]:
        return json.loads((self.repo / relative).read_text(encoding="utf-8"))

    def _verified_memory(self) -> list[dict[str, Any]]:
        rows = []
        for stage, path in self.RECEIPTS.items():
            doc = self._load(path)
            if doc.get("status") != self.EXPECTED[stage]:
                raise ValueError("CAUSAL_EXTERNAL_BINDING_RECEIPT_NOT_PASS:" + stage)
            rows.append({"stage": stage, "path": path, "status": doc["status"], "digest": _digest(doc)})
        return rows

    @staticmethod
    def verify_v6_result(doc: dict[str, Any]) -> bool:
        gates = doc.get("gates") or {}
        return bool(doc.get("status") == "PASS_SHADOW_G2_AUTONOMOUS_OPEN_CATALOG_DISCOVERY_V6" and gates.get("open_catalog_read_only") is True and gates.get("artifact_digest_verified") is True and gates.get("dependency_discovered_from_external_artifact") is True and gates.get("second_hop_registry_connection_succeeded") is True and gates.get("sealed_independent_registry_surface_verified") is True and gates.get("external_write_methods_used") is False and gates.get("credentials_used") is False and gates.get("external_models_used") is False and gates.get("canonical_mutation") is False)

    def prepare_cycle(self, objective: str) -> dict[str, Any]:
        goal = str(objective or "").strip()
        if not goal:
            raise ValueError("CAUSAL_EXTERNAL_BINDING_OBJECTIVE_REQUIRED")
        memory = {
            "v1_v6": self._verified_memory(),
            "legacy": self.memory_search(["external", "resource", "evidence", "library", "thinking"], limit=6),
            "prior_episode_count": len(self._episodes),
            "prior_event_digest": self._episodes[-1]["event_digest"] if self._episodes else None,
        }
        key = "EXTERNAL_EVIDENCE_WITH_MEMORY" if self._episodes else "EXTERNAL_EVIDENCE_FIRST_PASS"
        thinking = self.thinking([("Q", key), ("R", key)])
        logic = self.logic(self.CAUSAL_RELATION, "MEMORY")
        intelligence = self.intelligence({"input_contract": "RELATION_START_TO_STATE", "relation": self.CAUSAL_RELATION, "start": "MEMORY"})
        logic_nodes = set(logic.get("result") or ())
        intelligence_nodes = set(intelligence.get("result") or ())
        gates = {
            "memory_verified": len(memory["v1_v6"]) == 6,
            "thinking_pass": thinking.get("status") == "PASS_TRI_ORGAN_THINKING" and thinking.get("result") is True,
            "logic_closure_pass": thinking.get("result") is True and self.REQUIRED_NODES.issubset(logic_nodes),
            "intelligence_route_pass": intelligence.get("status") == "PASS_TRI_ORGAN_INTELLIGENCE_ROUTE" and self.REQUIRED_NODES.issubset(intelligence_nodes),
            "intelligence_selected_logic": intelligence.get("selected_component") == "ALG-G2-ALL-EXPERIENCE-RELATIONAL-CAUSAL-LOGIC-V1",
        }
        plan = {
            "schema": "yado.g2.causal_external_learning_action_plan.v1",
            "objective": goal,
            "component_id": self.COMPONENT_ID,
            "adapter": "runtime/yado_autonomous_open_catalog_discovery_v6.py",
            "mode": "READ_ONLY",
            "result_receipt": self.RECEIPTS["v6"],
            "prior_event_digest": memory["prior_event_digest"],
            "gates": gates,
        }
        plan["plan_digest"] = _digest(plan)
        return {"status": "PASS_CAUSAL_PREPARE" if all(gates.values()) else "WITHHOLD_CAUSAL_PREPARE", "memory": memory, "thinking": thinking, "logic": logic, "intelligence": intelligence, "action_plan": plan}

    def apply_result(self, prepared: dict[str, Any], external_result: dict[str, Any]) -> dict[str, Any]:
        plan = deepcopy(prepared.get("action_plan") or {})
        plan_digest = plan.pop("plan_digest", None)
        if plan_digest != _digest(plan):
            raise ValueError("CAUSAL_EXTERNAL_BINDING_PLAN_DIGEST_MISMATCH")
        if prepared.get("status") != "PASS_CAUSAL_PREPARE":
            return {"status": "WITHHOLD_G2_CAUSAL_EXTERNAL_LEARNING_BINDING_V1", "reason": "PREPARE_WITHHOLD", "memory_appended": False}
        verified = self.verify_v6_result(external_result)
        evidence = {"outcome": "PASS" if verified else "WITHHOLD", "domain": "EXECUTION", "next_required_capability": "MEMORY_FEEDBACK" if verified else "BOUNDED_EXTERNAL_EVIDENCE_REPAIR", "next_domain": "MEMORY" if verified else "EXECUTION", "source_class": "RECEIPT", "artifact": external_result}
        meta = self.meta_decide_evidence(evidence)
        event = {
            "sequence": len(self._episodes) + 1,
            "objective": plan["objective"],
            "prior_event_digest": plan.get("prior_event_digest"),
            "memory_feedback_used": bool(plan.get("prior_event_digest")),
            "thinking_component": prepared["thinking"].get("component_id"),
            "logic_component": prepared["logic"].get("component_id"),
            "intelligence_component": prepared["intelligence"].get("component_id"),
            "action_adapter": plan["adapter"],
            "action_mode": plan["mode"],
            "external_verified": verified,
            "external_result_digest": _digest(external_result),
            "selected_package": ((external_result.get("selected_library") or {}).get("name")),
            "discovered_dependency": ((external_result.get("second_hop_library_connection") or {}).get("name")),
            "meta_decision": meta,
        }
        event["event_digest"] = _digest(event)
        self._episodes.append(deepcopy(event))
        self._episodes = self._episodes[-self.MAX_EPISODES:]
        return {"schema": "yado.g2.causal_external_learning_cycle.v1", "status": "PASS_G2_CAUSAL_EXTERNAL_LEARNING_BINDING_V1" if verified else "WITHHOLD_G2_CAUSAL_EXTERNAL_LEARNING_BINDING_V1", "prepared": prepared, "result_verified": verified, "meta_decision": meta, "memory_after": {"episode_count": len(self._episodes), "event": event, "event_digest": event["event_digest"]}, "g3_genesis_performed": False}

    def export_state(self) -> dict[str, Any]:
        state = {"schema": self.STATE_SCHEMA, "component_id": self.COMPONENT_ID, "episodes": deepcopy(self._episodes), "executable_objects": False}
        state["state_digest"] = _digest(state)
        return state

    def import_state(self, state: dict[str, Any]) -> dict[str, Any]:
        x = deepcopy(dict(state or {})); expected = x.pop("state_digest", None)
        if x.get("schema") != self.STATE_SCHEMA or x.get("component_id") != self.COMPONENT_ID or x.get("executable_objects") is not False or not isinstance(x.get("episodes"), list) or len(x["episodes"]) > self.MAX_EPISODES or expected != _digest(x):
            raise ValueError("CAUSAL_EXTERNAL_BINDING_STATE_INVALID")
        previous = None
        for i, row in enumerate(x["episodes"], start=1):
            check = deepcopy(row); event_digest = check.pop("event_digest", None)
            if event_digest != _digest(check) or row.get("sequence") != i or row.get("prior_event_digest") != previous:
                raise ValueError("CAUSAL_EXTERNAL_BINDING_EVENT_CHAIN_INVALID")
            previous = event_digest
        self._episodes = deepcopy(x["episodes"])
        return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        return {"schema": "yado.g2.causal_external_learning_binding.snapshot.v1", "component_id": self.COMPONENT_ID, "status": self.artifact.get("status"), "episode_count": len(self._episodes), "durable_state_supported": True, "read_only_external": True, "automatic_canonical_promotion": False, "g3_genesis_performed": False}


__all__ = ["G2CausalExternalLearningBindingV1"]
