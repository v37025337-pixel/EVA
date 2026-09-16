from __future__ import annotations

"""Unified G2 core binding for the user-selected external developer capability pack."""

from yado_external_dev_capability_pack_v1 import ExternalDevCapabilityPackV1
from yado_unified_core_self_directed_web_research_v1 import UnifiedYADOCoreSelfDirectedWebResearchV1


class UnifiedYADOCoreExternalDevCapabilityPackV1(UnifiedYADOCoreSelfDirectedWebResearchV1):
    EXTERNAL_DEV_LAYER_ID = "UNIFIED_YADO_CORE_EXTERNAL_DEV_CAPABILITY_PACK_V1"

    def __init__(self, repo_root=None):
        super().__init__(repo_root=repo_root)
        self.external_dev_capability_pack = ExternalDevCapabilityPackV1()

    def _external_fetch(self, *, timeout=20.0, resolver=None, transport=None):
        return lambda url: self.public_web_fetch(url, timeout=timeout, resolver=resolver, transport=transport)

    def refresh_external_dev_capabilities(self, *, timeout=20.0, resolver=None, transport=None, fetch_override=None):
        fetch = fetch_override or self._external_fetch(timeout=timeout, resolver=resolver, transport=transport)
        out = self.external_dev_capability_pack.refresh(fetch)
        out["core_route"] = self.EXTERNAL_DEV_LAYER_ID
        out["generation"] = self.head.get("generation_id")
        return out

    def external_dev_task_contract(self, objective: str, acceptance_criteria: list[str]):
        return self.external_dev_capability_pack.task_contract(objective, acceptance_criteria)

    def external_dev_api_probe(self, url: str, *, must_contain=None, timeout=20.0, resolver=None, transport=None, fetch_override=None):
        fetch = fetch_override or self._external_fetch(timeout=timeout, resolver=resolver, transport=transport)
        return self.external_dev_capability_pack.api_probe(fetch, url, must_contain=must_contain)

    def external_dev_app_build_plan(self, objective: str, stack: str, tests: list[str]):
        return self.external_dev_capability_pack.app_build_plan(objective, stack, tests)

    def external_dev_utility(self, name: str, value: str):
        return self.external_dev_capability_pack.utility(name, value)

    def external_dev_free_resource_candidates(self, keywords: list[str], *, limit=10, timeout=20.0, resolver=None, transport=None, fetch_override=None):
        fetch = fetch_override or self._external_fetch(timeout=timeout, resolver=resolver, transport=transport)
        return self.external_dev_capability_pack.free_resource_candidates(fetch, keywords, limit=limit)

    def external_dev_capability_snapshot(self):
        snap = self.external_dev_capability_pack.snapshot()
        snap["external_dev_layer_id"] = self.EXTERNAL_DEV_LAYER_ID
        snap["base_research_layer_id"] = self.RESEARCH_LAYER_ID
        return snap

    def audit(self):
        report = super().audit()
        pack = self.external_dev_capability_snapshot()
        checks = dict(report["checks"])
        checks.update({
            "external_dev_capability_pack_bound": pack.get("source_count") == 5,
            "external_dev_capability_pack_read_only": pack.get("read_only_external") is True,
            "external_dev_capability_pack_no_code_execution": pack.get("third_party_code_execution") is False,
            "external_dev_capability_pack_no_code_copy": pack.get("third_party_code_copy") is False,
            "external_dev_capability_pack_no_auto_mutation": pack.get("automatic_canonical_mutation") is False,
        })
        report["checks"] = checks
        report["pass"] = all(checks.values())
        report["external_dev_capability_pack"] = pack
        return report

    def snapshot(self):
        snap = super().snapshot()
        snap["external_dev_capability_pack"] = self.external_dev_capability_snapshot()
        snap["external_dev_layer_id"] = self.EXTERNAL_DEV_LAYER_ID
        snap["semantic_boundary"] = (
            "CANONICAL G2 PLUS USER-SELECTED PUBLIC DEV REPOSITORY INTAKE. THIRD-PARTY MATERIAL IS "
            "READ AS EVIDENCE AND TRANSLATED INTO BOUNDED NATIVE PATTERNS; NO AUTOMATIC INSTALL, "
            "THIRD-PARTY CODE EXECUTION, BULK CODE COPY, CREDENTIAL USE, PRIVATE NETWORK ACCESS, "
            "EXTERNAL WRITE, CANONICAL MUTATION, OR G3 CLAIM."
        )
        return snap


__all__ = ["UnifiedYADOCoreExternalDevCapabilityPackV1"]
