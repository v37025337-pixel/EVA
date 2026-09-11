from __future__ import annotations

from yado_goal_external_resource_execution_fabric_v1 import (
    GENERIC_TAGS,
    YADOGoalExternalResourceExecutionFabricV1,
    main as base_main,
)
from yado_native_openapi_discovery_integration_v2 import (
    YADONativeOpenAPIDiscoveryIntegrationV2,
    tokens,
)


_ORIGINAL_ROUTE_GOAL = YADOGoalExternalResourceExecutionFabricV1.route_goal
NOVELTY_HINTS = (
    "new api",
    "different api",
    "different public api",
    "new integration",
    "not already",
    "not in the verified integration registry",
    "novel api",
)


def route_goal_v12(self: YADOGoalExternalResourceExecutionFabricV1, goal: str) -> dict:
    """Route an explicit novelty request to discovery without naming a provider."""
    decision = self.binder.classify_goal(goal)
    if decision.get("external_resource_needed") is False:
        return _ORIGINAL_ROUTE_GOAL(self, goal)

    text = " ".join(str(goal).lower().split())
    novelty_matches = [hint for hint in NOVELTY_HINTS if hint in text]
    if not novelty_matches:
        return _ORIGINAL_ROUTE_GOAL(self, goal)

    tags = set(self.binder.goal_tags(goal))
    domain = sorted(tags - GENERIC_TAGS)
    return {
        "route": "DISCOVER_NEW_API",
        "decision": decision,
        "goal_tags": sorted(tags),
        "required_domain_tags": domain,
        "novelty_requested": True,
        "novelty_matches": novelty_matches,
    }


def execute_discovery_novel(self: YADOGoalExternalResourceExecutionFabricV1, goal: str) -> dict:
    """Require DISCOVER_NEW_API to exclude verified integrations.

    If the goal also contains a domain-specific tag, candidates must match that
    domain. For a pure novelty goal, the bounded discovery controller remains
    free to select any new safe provider from the public catalog. The host does
    not name or select a provider or endpoint.
    """
    existing_ids = {
        str(row.get("verified_external_api_id"))
        for row in self.verified_existing()
        if row.get("verified_external_api_id")
    }
    route = self.route_goal(goal)
    required_domain_tags = set(route.get("required_domain_tags") or [])

    class NovelDomainDiscovery(YADONativeOpenAPIDiscoveryIntegrationV2):
        @classmethod
        def rank_catalog(cls, catalog: dict, goal_tags: list[str], limit: int) -> list[dict]:
            broad = super().rank_catalog(catalog, goal_tags, max(768, int(limit)))
            filtered: list[dict] = []
            for row in broad:
                api_id = str(row.get("api_id") or "")
                if api_id in existing_ids:
                    continue
                semantic = set(str(x).lower() for x in row.get("categories", []))
                semantic |= tokens(api_id + " " + str(row.get("title") or ""))
                if required_domain_tags and not (required_domain_tags & semantic):
                    continue
                filtered.append(row)
                if len(filtered) >= int(limit):
                    break
            return filtered

    request = self.binder.build_discovery_request(goal)
    request.setdefault("limits", {})["max_ranked_candidates"] = 128
    request["limits"]["max_spec_fetches"] = 64
    discovery = NovelDomainDiscovery().run(request)
    evaluation = self.binder.evaluate_discovery(discovery)
    selected = discovery.get("selected") or {}
    entry = selected.get("catalog_entry") or {}
    operation = selected.get("operation") or {}
    live = selected.get("live") or {}
    selected_id = entry.get("api_id")
    semantic = set(str(x).lower() for x in entry.get("categories", []))
    semantic |= tokens(str(selected_id or "") + " " + str(entry.get("title") or ""))
    domain_match = (not required_domain_tags) or bool(required_domain_tags & semantic)

    return {
        "goal": goal,
        "route": "DISCOVER_NEW_API",
        "discovery_invoked": True,
        "network_route_invoked": True,
        "registry_reused": False,
        "discovery_evaluation": evaluation,
        "novelty_filter": {
            "excluded_existing_api_ids": sorted(existing_ids),
            "required_domain_tags": sorted(required_domain_tags),
            "selected_domain_metadata": sorted(semantic),
            "selected_domain_match": domain_match,
            "provider_host_selected": False,
            "max_ranked_candidates": 128,
            "max_spec_fetches": 64,
        },
        "result": {
            "pass": evaluation.get("pass") is True and bool(selected_id) and str(selected_id) not in existing_ids and domain_match,
            "api_id": selected_id,
            "api_title": entry.get("title"),
            "api_categories": entry.get("categories"),
            "endpoint": operation.get("url"),
            "http_status": live.get("status"),
            "json_parsed": live.get("parsed"),
            "summary": live.get("summary"),
            "response_sha256": live.get("sha256"),
            "provenance_digest": (discovery.get("provenance") or {}).get("digest"),
            "candidate_source_sha256": discovery.get("candidate_source_sha256"),
        },
    }


# V1.2 remains host-authored shadow routing scaffolding. It tests the existing
# YADO discovery mechanisms; it is not evidence that YADO invented this fabric.
YADOGoalExternalResourceExecutionFabricV1.route_goal = route_goal_v12
YADOGoalExternalResourceExecutionFabricV1.execute_discovery = execute_discovery_novel


if __name__ == "__main__":
    raise SystemExit(base_main())
