from __future__ import annotations

"""Unified YADO G2 core with bounded self-directed public-web research V1."""

import hashlib
import json
from urllib.parse import quote_plus

from yado_g2_causal_external_learning_binding_v1 import G2CausalExternalLearningBindingV1
from yado_self_directed_web_research_v1 import SelfDirectedWebResearchV1
from yado_unified_core_personal_web_v2 import UnifiedYADOCorePersonalWebV2


def _digest(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


class UnifiedYADOCoreSelfDirectedWebResearchV1(UnifiedYADOCorePersonalWebV2):
    RESEARCH_LAYER_ID = "UNIFIED_YADO_CORE_SELF_DIRECTED_WEB_RESEARCH_V1"
    MAX_RESEARCH_GENERATIONS = 5

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

    @staticmethod
    def _structured_search_urls(objective: str) -> list[tuple[str, str]]:
        q = quote_plus(" ".join(str(objective).split()))
        return [
            ("wikipedia_opensearch", f"https://en.wikipedia.org/w/api.php?action=opensearch&search={q}&limit=8&namespace=0&format=json"),
            ("stackexchange_search", f"https://api.stackexchange.com/2.3/search/advanced?order=desc&sort=relevance&q={q}&site=stackoverflow&pagesize=8"),
            ("github_repository_search", f"https://api.github.com/search/repositories?q={q}&per_page=8"),
            ("crossref_works", f"https://api.crossref.org/works?query.bibliographic={q}&rows=8"),
        ]

    @staticmethod
    def _structured_candidates(provider: str, content: str) -> list[str]:
        try:
            payload = json.loads(content)
        except (TypeError, json.JSONDecodeError):
            return []
        out = []
        if provider == "wikipedia_opensearch" and isinstance(payload, list) and len(payload) >= 4 and isinstance(payload[3], list):
            out.extend(str(x) for x in payload[3] if isinstance(x, str))
        elif provider == "stackexchange_search" and isinstance(payload, dict):
            for row in payload.get("items") or []:
                if isinstance(row, dict) and isinstance(row.get("link"), str):
                    out.append(row["link"])
        elif provider == "github_repository_search" and isinstance(payload, dict):
            for row in payload.get("items") or []:
                if not isinstance(row, dict):
                    continue
                if isinstance(row.get("homepage"), str) and row["homepage"].startswith("https://"):
                    out.append(row["homepage"])
                if isinstance(row.get("html_url"), str):
                    out.append(row["html_url"])
        elif provider == "crossref_works" and isinstance(payload, dict):
            message = payload.get("message") or {}
            for row in message.get("items") or []:
                if not isinstance(row, dict):
                    continue
                resource = row.get("resource") or {}
                primary = resource.get("primary") or {} if isinstance(resource, dict) else {}
                if isinstance(primary, dict) and isinstance(primary.get("URL"), str):
                    out.append(primary["URL"])
                for link in row.get("link") or []:
                    if isinstance(link, dict) and isinstance(link.get("URL"), str):
                        out.append(link["URL"])
                if isinstance(row.get("URL"), str):
                    out.append(row["URL"])
        cleaned = []
        seen = set()
        for url in out:
            value = str(url).strip()
            if not value.startswith("https://") or value in seen:
                continue
            seen.add(value)
            cleaned.append(value)
        return cleaned

    def _discover_structured_candidates(self, objective: str, *, limit: int, timeout: float, resolver=None, transport=None) -> dict:
        fetch, _ = self._research_callbacks(timeout=timeout, resolver=resolver, transport=transport)
        candidates = []
        receipts = []
        errors = []
        seen = set()
        for provider, url in self._structured_search_urls(objective):
            try:
                page = fetch(url)
                receipt = page.get("receipt") or {}
                found = self._structured_candidates(provider, page.get("content", ""))
                receipts.append({
                    "provider": provider,
                    "url": receipt.get("final_url", url),
                    "host": receipt.get("final_host"),
                    "sha256": receipt.get("sha256"),
                    "candidate_count": len(found),
                    "read_only": receipt.get("read_only") is True,
                })
                for candidate in found:
                    if candidate in seen:
                        continue
                    seen.add(candidate)
                    candidates.append(candidate)
                    if len(candidates) >= limit:
                        break
                if len(candidates) >= limit:
                    break
            except Exception as exc:
                errors.append({"provider": provider, "url": url, "error_type": type(exc).__name__, "reason": str(exc)[:240]})
        return {
            "schema": "yado.structured_public_search_discovery.v1",
            "objective": objective,
            "candidates": candidates,
            "candidate_count": len(candidates),
            "provider_receipts": receipts,
            "provider_errors": errors,
            "providers_contacted": len(receipts) + len(errors),
            "search_pages_are_evidence_sources": False,
            "read_only": True,
        }

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
        structured = self._discover_structured_candidates(
            objective,
            limit=max_search_results,
            timeout=timeout,
            resolver=resolver,
            transport=transport,
        )
        seeds = list(seed_urls or []) + list(structured["candidates"])
        result = self.self_directed_research_controller.research(
            objective,
            fetch=fetch,
            discover=discover,
            seed_urls=seeds,
            max_sources=max_sources,
            max_search_results=max_search_results,
            closure_source_target=closure_source_target,
            use_search=True,
        )
        result["structured_discovery"] = structured
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
        root = " ".join(str(initial_objective or "").split()).strip()
        if not root:
            raise ValueError("RESEARCH_OBJECTIVE_REQUIRED")
        if not 1 <= int(max_generations) <= self.MAX_RESEARCH_GENERATIONS:
            raise ValueError("RESEARCH_GENERATION_BUDGET")
        fetch, discover = self._research_callbacks(timeout=timeout, resolver=resolver, transport=transport)
        goal = root
        generations = []
        seen_goals = set()
        manual_first = list(seed_urls or [])
        for index in range(int(max_generations)):
            if not goal or goal in seen_goals:
                break
            seen_goals.add(goal)
            structured = self._discover_structured_candidates(
                goal,
                limit=max_search_results,
                timeout=timeout,
                resolver=resolver,
                transport=transport,
            )
            seeds = (manual_first if index == 0 else []) + list(structured["candidates"])
            result = self.self_directed_research_controller.research(
                goal,
                root_objective=root,
                fetch=fetch,
                discover=discover,
                seed_urls=seeds,
                max_sources=max_sources_per_generation,
                max_search_results=max_search_results,
                closure_source_target=closure_source_target,
                use_search=True,
            )
            result["structured_discovery"] = structured
            generations.append(result)
            goal = result.get("next_goal")
            if not goal:
                break
        all_hosts = sorted({source.get("host") for generation in generations for source in generation.get("sources", []) if source.get("host")})
        goal_closed = bool(generations and not generations[-1].get("next_goal") and generations[-1].get("status") == "PASS_SELF_DIRECTED_WEB_RESEARCH_V1")
        status = "PASS_BOUNDED_SELF_DIRECTED_WEB_RESEARCH_GENERATIONS_V1" if generations and any(x.get("status") == "PASS_SELF_DIRECTED_WEB_RESEARCH_V1" for x in generations) else "WITHHOLD_BOUNDED_SELF_DIRECTED_WEB_RESEARCH_GENERATIONS_V1"
        return {
            "schema": "yado.self_directed_web_research.generations.v1",
            "status": status,
            "root_objective": root,
            "generation_count": len(generations),
            "goal_closed": goal_closed,
            "independent_hosts_accumulated": all_hosts,
            "generations": generations,
            "remaining_goal": generations[-1].get("next_goal") if generations else root,
            "structured_search_per_generation": True,
            "search_pages_are_evidence_sources": False,
            "automatic_canonical_mutation": False,
            "g3_genesis_performed": False,
            "core_route": self.RESEARCH_LAYER_ID,
            "generation": self.head.get("generation_id"),
        }

    def export_self_directed_research_state(self) -> dict:
        return self.self_directed_research_controller.export_state()

    def restore_self_directed_research_state(self, state: dict) -> dict:
        return self.self_directed_research_controller.import_state(state)

    def self_directed_research_snapshot(self) -> dict:
        snap = self.self_directed_research_controller.snapshot()
        snap["research_layer_id"] = self.RESEARCH_LAYER_ID
        snap["base_access_layer_id"] = self.ACCESS_LAYER_ID
        snap["causal_prepare_source"] = "CURRENT_CANONICAL_CAUSAL_SNAPSHOT_AND_TRI_ORGAN_REDERIVATION"
        snap["structured_search_discovery"] = True
        snap["structured_search_pages_are_evidence_sources"] = False
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
            "self_directed_web_research_structured_discovery": research.get("structured_search_discovery") is True and research.get("structured_search_pages_are_evidence_sources") is False,
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
            "MULTI-SOURCE RESEARCH; PUBLIC SEARCH APIS ONLY DISCOVER CANDIDATE URLS AND ARE NOT COUNTED "
            "AS EVIDENCE SOURCES; DEFICIT MAY CREATE A NEXT RESEARCH GOAL, BUT NO PRIVATE NETWORKS, "
            "CREDENTIALS, EXTERNAL WRITES, DOWNLOADED-CODE EXECUTION, AUTOMATIC CANONICAL MUTATION, "
            "G3, AGI, OR SUBJECTIVE-CONSCIOUSNESS CLAIM."
        )
        return snap


__all__ = ["UnifiedYADOCoreSelfDirectedWebResearchV1"]
