from __future__ import annotations

from yado_external_tool_ecosystem_learning_v1 import ExternalToolEcosystemLearningV1
from yado_unified_core_peer_systems_learning_v1 import UnifiedYADOCorePeerSystemsLearningV1


class UnifiedYADOCoreExternalToolEcosystemLearningV1(UnifiedYADOCorePeerSystemsLearningV1):
    EXTERNAL_TOOL_ECOSYSTEM_LAYER_ID = "UNIFIED_YADO_CORE_EXTERNAL_TOOL_ECOSYSTEM_AGGREGATION_V1"

    def __init__(self, repo_root=None):
        super().__init__(repo_root=repo_root)
        self._external_tool_repo_root = repo_root
        self.external_tool_ecosystem_learning = ExternalToolEcosystemLearningV1()

    def study_external_tool_ecosystem(
        self,
        *,
        timeout=25.0,
        resolver=None,
        transport=None,
        fetch_override=None,
        repo_root=None,
    ):
        fetch = fetch_override or self._external_fetch(
            timeout=timeout,
            resolver=resolver,
            transport=transport,
        )
        out = self.external_tool_ecosystem_learning.study(
            fetch,
            repo_root=repo_root or self._external_tool_repo_root or ".",
        )
        out["core_route"] = self.EXTERNAL_TOOL_ECOSYSTEM_LAYER_ID
        out["generation"] = self.head.get("generation_id")
        return out

    def audit(self):
        report = super().audit()
        snap = self.external_tool_ecosystem_learning.snapshot()
        checks = dict(report["checks"])
        checks.update(
            {
                "external_tool_ecosystem_bound": snap.get("source_count") == 4,
                "external_tool_ecosystem_reuses_existing": snap.get("reuses_existing_components") is True,
                "external_tool_ecosystem_no_new_adapter_duplication": snap.get("new_third_party_adapter_count") == 0,
                "external_tool_ecosystem_read_only": snap.get("read_only_external") is True,
                "external_tool_ecosystem_no_code_execution": snap.get("third_party_code_executed") is False,
                "external_tool_ecosystem_no_code_copy": snap.get("third_party_code_copied") is False,
                "external_tool_ecosystem_no_auto_install": snap.get("automatic_install") is False,
                "external_tool_ecosystem_no_auto_mutation": snap.get("automatic_canonical_mutation") is False,
            }
        )
        report["checks"] = checks
        report["pass"] = all(checks.values())
        report["external_tool_ecosystem_learning"] = snap
        return report

    def snapshot(self):
        snap = super().snapshot()
        snap["external_tool_ecosystem_learning"] = self.external_tool_ecosystem_learning.snapshot()
        snap["external_tool_ecosystem_layer_id"] = self.EXTERNAL_TOOL_ECOSYSTEM_LAYER_ID
        snap["semantic_boundary"] = (
            "AGGREGATES EXISTING EXA, HIVEMIND, FREE-FOR-DEV AND GHIDRA COMPONENTS "
            "BEHIND ONE PROVENANCE GATE. NO DUPLICATE THIRD-PARTY ADAPTER IS CREATED, "
            "NO THIRD-PARTY CODE IS EXECUTED, AND CANONICAL IS NOT AUTO-MUTATED."
        )
        return snap


__all__ = ["UnifiedYADOCoreExternalToolEcosystemLearningV1"]
