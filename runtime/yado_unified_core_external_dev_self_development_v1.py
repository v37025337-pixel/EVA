from __future__ import annotations

"""Unified G2 core binding for bounded external-dev self-development V1."""

from yado_external_dev_self_development_v1 import ExternalDevSelfDevelopmentV1
from yado_unified_core_external_dev_capability_pack_v1 import UnifiedYADOCoreExternalDevCapabilityPackV1


class UnifiedYADOCoreExternalDevSelfDevelopmentV1(UnifiedYADOCoreExternalDevCapabilityPackV1):
    SELF_DEVELOPMENT_LAYER_ID = "UNIFIED_YADO_CORE_EXTERNAL_DEV_SELF_DEVELOPMENT_V1"

    def __init__(self, repo_root=None):
        super().__init__(repo_root=repo_root)
        self.external_dev_self_development_controller = ExternalDevSelfDevelopmentV1()

    def external_dev_self_develop(
        self,
        objective: str,
        *,
        candidate_path=None,
        receipt_path=None,
        timeout=25.0,
        resolver=None,
        transport=None,
        fetch_override=None,
    ):
        out = self.external_dev_self_development_controller.run(
            self,
            objective,
            candidate_path=candidate_path,
            receipt_path=receipt_path,
            timeout=timeout,
            resolver=resolver,
            transport=transport,
            fetch_override=fetch_override,
        )
        out["core_route"] = self.SELF_DEVELOPMENT_LAYER_ID
        out["generation"] = self.head.get("generation_id")
        return out

    def external_dev_self_development_snapshot(self):
        snap = self.external_dev_self_development_controller.snapshot()
        snap["self_development_layer_id"] = self.SELF_DEVELOPMENT_LAYER_ID
        snap["base_external_dev_layer_id"] = self.EXTERNAL_DEV_LAYER_ID
        return snap

    def audit(self):
        report = super().audit()
        layer = self.external_dev_self_development_snapshot()
        checks = dict(report["checks"])
        checks.update({
            "external_dev_self_development_bound": layer.get("autonomous_capability_selection_target") is True,
            "external_dev_self_development_no_third_party_execution": layer.get("third_party_code_execution") is False,
            "external_dev_self_development_no_third_party_copy": layer.get("third_party_code_copy") is False,
            "external_dev_self_development_no_auto_main": layer.get("automatic_main_mutation") is False,
            "external_dev_self_development_no_g3": layer.get("g3_genesis_performed") is False,
        })
        report["checks"] = checks
        report["pass"] = all(checks.values())
        report["external_dev_self_development"] = layer
        return report

    def snapshot(self):
        snap = super().snapshot()
        snap["external_dev_self_development"] = self.external_dev_self_development_snapshot()
        snap["external_dev_self_development_layer_id"] = self.SELF_DEVELOPMENT_LAYER_ID
        snap["semantic_boundary"] = (
            "CANONICAL G2 PLUS SHADOW SELF-DEVELOPMENT OF EXTERNAL DEV CAPABILITY SELECTION. "
            "THE CORE MAY REFRESH VERIFIED PUBLIC SOURCES, DERIVE AND MATERIALIZE A NATIVE ROUTER "
            "CANDIDATE, AND TEST IT; MAIN ADMISSION REMAINS EXTERNAL-GATED AND NON-AUTOMATIC."
        )
        return snap


__all__ = ["UnifiedYADOCoreExternalDevSelfDevelopmentV1"]
