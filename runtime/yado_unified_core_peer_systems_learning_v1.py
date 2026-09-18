from __future__ import annotations

from yado_peer_systems_learning_v1 import PeerSystemsLearningV1
from yado_unified_core_external_dev_capability_pack_v1 import UnifiedYADOCoreExternalDevCapabilityPackV1

class UnifiedYADOCorePeerSystemsLearningV1(UnifiedYADOCoreExternalDevCapabilityPackV1):
    PEER_LEARNING_LAYER_ID = "UNIFIED_YADO_CORE_PEER_SYSTEMS_LEARNING_V1"

    def __init__(self, repo_root=None):
        super().__init__(repo_root=repo_root)
        self.peer_systems_learning = PeerSystemsLearningV1()

    def study_peer_systems(self, *, timeout=25.0, resolver=None, transport=None, fetch_override=None):
        fetch = fetch_override or self._external_fetch(timeout=timeout, resolver=resolver, transport=transport)
        out = self.peer_systems_learning.study(fetch)
        out["core_route"] = self.PEER_LEARNING_LAYER_ID
        out["generation"] = self.head.get("generation_id")
        return out

    def audit(self):
        report = super().audit()
        snap = self.peer_systems_learning.snapshot()
        checks = dict(report["checks"])
        checks.update({
            "peer_learning_bound": snap.get("source_count") >= 10,
            "peer_learning_read_only": snap.get("read_only_external") is True,
            "peer_learning_no_code_execution": snap.get("third_party_code_executed") is False,
            "peer_learning_no_code_copy": snap.get("third_party_code_copied") is False,
            "peer_learning_no_auto_mutation": snap.get("automatic_canonical_mutation") is False,
        })
        report["checks"] = checks
        report["pass"] = all(checks.values())
        report["peer_systems_learning"] = snap
        return report

__all__ = ["UnifiedYADOCorePeerSystemsLearningV1"]
