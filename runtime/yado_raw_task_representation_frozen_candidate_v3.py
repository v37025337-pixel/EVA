from __future__ import annotations

from yado_raw_task_representation_residual_repair_v3 import (
    ResidualDrivenRawTaskRepresentationRepairV3,
)


class FrozenResidualRepairCandidateV3(ResidualDrivenRawTaskRepresentationRepairV3):
    """Immutable shadow candidate selected by residual synthesis V3.

    The policy is frozen before deep-admission fresh evidence is generated.
    This source is not canonical and performs no automatic promotion.
    """

    COMPONENT_ID = "ALG-G2-RAW-TASK-REPRESENTATION-RESIDUAL-REPAIR-V3-FROZEN"
    PARENT_COMPONENT_ID = "ALG-G2-RAW-TASK-REPRESENTATION-V4"
    SELECTED_POLICY = "CLEAN_PLURALITY_TIE_CORE"
    SELECTION_RECEIPT_SHA256 = "1a37f057135922300091549a843b20a01348ea2bb29c776e3763117a788043b5"

    def __init__(self, v3_artifact):
        super().__init__(v3_artifact, self.SELECTED_POLICY)


def component(parent_digest: str) -> dict:
    return {
        "schema": "yado.g2.raw_task_representation_residual_repair_v3_frozen.component.v1",
        "component_id": FrozenResidualRepairCandidateV3.COMPONENT_ID,
        "parent_component_id": FrozenResidualRepairCandidateV3.PARENT_COMPONENT_ID,
        "policy": FrozenResidualRepairCandidateV3.SELECTED_POLICY,
        "selection_receipt_sha256": FrozenResidualRepairCandidateV3.SELECTION_RECEIPT_SHA256,
        "parent_component_digest": parent_digest,
        "candidate_frozen_before_deep_admission_fresh_evidence": True,
        "canonical_active": False,
        "automatic_promotion": False,
    }


__all__ = ["FrozenResidualRepairCandidateV3", "component"]
