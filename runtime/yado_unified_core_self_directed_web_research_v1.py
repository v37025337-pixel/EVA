from __future__ import annotations

"""Unified YADO G2 core with bounded self-directed public-web research V1."""

import hashlib
import json

from yado_g2_causal_external_learning_binding_v1 import G2CausalExternalLearningBindingV1
from yado_self_directed_web_research_v1 import SelfDirectedWebResearchV1
from yado_unified_core_personal_web_v2 import UnifiedYADOCorePersonalWebV2


def _digest(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


class UnifiedYADOCoreSelfDirectedWebResearchV1(UnifiedYADOCorePersonalWebV2):
    RESEARCH_LAYER_ID = "UNIFIED_YADO_CORE_SELF_DIRECTED_WEB_RESEARCH_V1"

    def __init__(self, repo_root=None):
        super().__init__(repo_root=repo_root)
        self.self_directed_research_controller = SelfDirectedWebResearchV1(
            self._prepare_live_causal_research,
            self.global_experience_meta_decide_evidence,
        )

    def _prepare_live_causal_research(self, objective: str) -> dict:
        """Re-derive causal readiness from the live canonical G2 mechanisms.

        The older V1 prepare path also re-opens historical V1-V6 receipt files.
        Those receipts are not part of the current physical main tree anymore, so
        a new research layer must not pretend they still exist. The canonical
        causal artifact was already validated during core construction; here we
        re-run the currently active tri-organ relation and bind the resulting
        evidence to the live causal snapshot instead of deleted receipt paths.
        """
        goal = " ".join(str(objective or "").split()).strip()
        if not goal:
            raise ValueError("RESEARCH_OBJECTIVE_REQUIRED")
        causal = self.causal_external_learning_snapshot()
        relation = G2CausalExternalLearningBindingV1.CAUSAL_RELATION
        required = G2CausalExternalLearningBindingV1.REQUIRED_NODES
        memory_count = self.self_directed_research_controller.snapshot().get("episode_count", 0) if hasattr(self, "self_directed_research_controller") else 0
        key = "SELF_DIRECTED_WEB_RESEARCH_WITH_MEMORY" if memory_count else "SELF_DIRECTED_WEB_RESEARCH_FIRST_PASS"
        thinking = self.all_experience_thinking([("Q", key), ("R", key)])
        logic = self.all_experience_logic(relation, "MEMORY")
        intelligence = self.all_experience_intelligence({
            "input_contract": "RELATION_START_TO_STATE",
            "relation": relation,
            "start": "MEMORY",
        })
        logic_nodes = set(logic.get("result") or ())
        intelligence_nodes = set(intelligence.get("result") or ())
        gates = {
            "canonical_causal_binding_active": causal.get("status") == "CANONICAL_ACTIVE",
            "canonical_causal_binding_read_only": causal.get("read_only_external") is True,
            "thinking_pass": thinking.get("status") == "PASS_TRI_ORGAN_THINKING" and thinking.get("result") is True,
            "logic_closure_pass": required.issubset(logic_nodes),
            "intelligence_route_pass": intelligence.get("status") == "PASS_TRI_ORGAN_INTELLIGENCE_ROUTE" and required.issubset(intelligence_nodes),
            "intelligence_selected_logic": intelligence.get("selected_component") == "ALG-G2-ALL-EXPERIENCE-RELATIONAL-CAUSAL-LOGIC-V1",
        }
        plan = {
            "schema": "yado.g2.live_causal_web_research_prepare.v1",
            "objective": goal,
            "source": "CURRENT_CANONICAL_CAUSAL_SNAPSHOT_AND_TRI_ORGAN_REDERIVATION",
            "causal_component": causal.get("component_id"),
            "mode": "READ_ONLY",
            "relation": relation,
            "prior_research_episode_count": memory_count,
            "gates": gates,
            "automatic_canonical_mutation": False,
            "g3_genesis_performed": False,
        }
        plan["plan_digest"] = _digest(plan)
        return {
            "status": "PASS_CAUSAL_PREPARE" if all(gates.values()) else "WITHHOLD_CAUSAL_PREPARE",
            "memory": {
                "source": "LIVE_RESEARCH_EPISODIC_MEMORY",
                "prior_episode_count": memory_count,
                "historical_deleted_receipts_required": False,
            },
            "thinking": thinking,
            "logic": logic,
            "intelligence": intelligence,
            "causal_snapshot": causal,
            "action_plan": plan,
        }

    def _research_callbacks(self, *, timeout=15.0, resolver=None, transport=None):
        def fetch(url):
            return self.public_web_fetch(url, timeout=timeout, resolver=resolver, transport=transport)

        def discover(content, base_url, limit):
            return self.public_web_discover(content, base_url, limit=limit, resolver=resolver)

        return fetch, discover

    def self_directed_web_research(
        self,
        objective: str,
        *,
        seed_urls=None,
        max_sources: int = 3,
        max_search_results: int = 16,
        closure_source_target: int = 4,
        timeout: float = 15.0,
        resolver=None,
        transport=None,
    ) -> dict:
        fetch, discover = self._research_callbacks(timeout=timeout, resolver=resolver, transport=transport)
        result = self.self_directed_research_controller.research(
            objective,
            fetch=fetch,
            discover=discover,
            seed_urls=seed_urls,
            max_sources=max_sources,
            max_search_results=max_search_results,
            closure_source_target=closure_source_target,
            use_search=True,
        )
        result["core_route"] = self.RESEARCH_LAYER_ID
        result["generation"] = self.head.get("generation_id")
        return result

    def self_directed_web_research_generations(
        self,
        initial_objective: str,
        *,
        seed_urls=None,
        max_generations: int = 3,
        max_sources_per_generation: int = 2,
        closure_source_target: int = 4,
        max_search_results: int = 20,
        timeout: float = 15.0,
        resolver=None,
        transport=None,
    ) -> dict:
        fetch, discover = self._research_callbacks(timeout=timeout, resolver=resolver, transport=transport)
        result = self.self_directed_research_controller.run_generations(
            initial_objective,
            fetch=fetch,
            discover=discover,
            seed_urls=seed_urls,
            max_generations=max_generations,
            max_sources_per_generation=max_sources_per_generation,
            closure_source_target=closure_source_target,
            max_search_results=max_search_results,
        )
        result["core_route"] = self.RESEARCH_LAYER_ID
        result["generation"] = self.head.get("generation_id")
        return result

    def export_self_directed_research_state(self) -> dict:
        return self.self_directed_research_controller.export_state()

    def restore_self_directed_research_state(self, state: dict) -> dict:
        return self.self_directed_research_controller.import_state(state)

    def self_directed_research_snapshot(self) -> dict:
        snap = self.self_directed_research_controller.snapshot()
        snap["research_layer_id"] = self.RESEARCH_LAYER_ID
        snap["base_access_layer_id"] = self.ACCESS_LAYER_ID
        snap["causal_prepare_source"] = "CURRENT_CANONICAL_CAUSAL_SNAPSHOT_AND_TRI_ORGAN_REDERIVATION"
        return snap

    def audit(self) -> dict:
        report = super().audit()
        research = self.self_directed_research_snapshot()
        checks = dict(report["checks"])
        checks.update({
            "self_directed_web_research_v1_bound": research.get("status") == "SHADOW_READY",
            "self_directed_web_research_uses_causal_prepare": research.get("uses_causal_prepare") is True,
            "self_directed_web_research_live_causal_source": research.get("causal_prepare_source") == "CURRENT_CANONICAL_CAUSAL_SNAPSHOT_AND_TRI_ORGAN_REDERIVATION",
            "self_directed_web_research_multi_source": research.get("multi_source_comparison") is True,
            "self_directed_web_research_deficit_to_goal": research.get("deficit_to_next_goal") is True,
            "self_directed_web_research_read_only": research.get("read_only_external") is True,
            "self_directed_web_research_no_auto_promotion": research.get("automatic_canonical_promotion") is False,
        })
        report["checks"] = checks
        report["pass"] = all(checks.values())
        report["self_directed_web_research"] = research
        return report

    def snapshot(self) -> dict:
        snap = super().snapshot()
        snap["self_directed_web_research"] = self.self_directed_research_snapshot()
        snap["research_layer_id"] = self.RESEARCH_LAYER_ID
        snap["semantic_boundary"] = (
            "CANONICAL G2 CORE PLUS BROAD PUBLIC HTTPS READ/DISCOVERY AND BOUNDED SELF-DIRECTED "
            "MULTI-SOURCE RESEARCH; DEFICIT MAY CREATE A NEXT RESEARCH GOAL, BUT NO PRIVATE NETWORKS, "
            "CREDENTIALS, EXTERNAL WRITES, DOWNLOADED-CODE EXECUTION, AUTOMATIC CANONICAL MUTATION, "
            "G3, AGI, OR SUBJECTIVE-CONSCIOUSNESS CLAIM."
        )
        return snap


__all__ = ["UnifiedYADOCoreSelfDirectedWebResearchV1"]
