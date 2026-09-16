from __future__ import annotations

"""Unified YADO G2 core with bounded self-directed public-web research V1."""

from yado_self_directed_web_research_v1 import SelfDirectedWebResearchV1
from yado_unified_core_personal_web_v2 import UnifiedYADOCorePersonalWebV2


class UnifiedYADOCoreSelfDirectedWebResearchV1(UnifiedYADOCorePersonalWebV2):
    RESEARCH_LAYER_ID = "UNIFIED_YADO_CORE_SELF_DIRECTED_WEB_RESEARCH_V1"

    def __init__(self, repo_root=None):
        super().__init__(repo_root=repo_root)
        self.self_directed_research_controller = SelfDirectedWebResearchV1(
            self.prepare_causal_external_learning,
            self.global_experience_meta_decide_evidence,
        )

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
        return snap

    def audit(self) -> dict:
        report = super().audit()
        research = self.self_directed_research_snapshot()
        checks = dict(report["checks"])
        checks.update({
            "self_directed_web_research_v1_bound": research.get("status") == "SHADOW_READY",
            "self_directed_web_research_uses_causal_prepare": research.get("uses_causal_prepare") is True,
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
