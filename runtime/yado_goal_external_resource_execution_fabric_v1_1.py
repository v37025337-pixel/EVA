from __future__ import annotations

import json

from yado_goal_external_resource_execution_fabric_v1 import (
    YADOGoalExternalResourceExecutionFabricV1,
    main as base_main,
)
from yado_native_openapi_discovery_integration_v2 import (
    YADONativeOpenAPIDiscoveryIntegrationV2,
    tokens,
)


def execute_discovery_novel(self: YADOGoalExternalResourceExecutionFabricV1, goal: str) -> dict:
    """Require DISCOVER_NEW_API to be both novel and domain-relevant.

    This repair does not name or select a provider. It excludes integrations
    already present in the verified shadow registry and requires at least one
    domain-specific goal tag to match the candidate API metadata when such tags
    exist. Provider/endpoint selection within the remaining public catalog is
    still performed by the existing bounded discovery controller.
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
            # Ask the inherited scorer for a broad pool, then enforce novelty
            # and domain relevance without choosing a concrete provider.
            broad = super().rank_catalog(catalog, goal_tags, max(512, int(limit)))
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


# V1.1 is a narrow repair of the shadow execution harness. The base report and
# strict checks remain unchanged; only DISCOVER_NEW_API gains novelty/domain
# filtering before provider selection.
YADOGoalExternalResourceExecutionFabricV1.execute_discovery = execute_discovery_novel


if __name__ == "__main__":
    raise SystemExit(base_main())
