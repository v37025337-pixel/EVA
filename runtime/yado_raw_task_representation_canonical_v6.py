from __future__ import annotations

from yado_raw_task_representation_residual_repair_v3 import ResidualDrivenRawTaskRepresentationRepairV3


class CanonicalRawTaskRepresentationRuntimeV6(ResidualDrivenRawTaskRepresentationRepairV3):
    """Canonical-binding wrapper for the frozen, admitted residual-repair policy.

    This wrapper changes identity/binding only. The routing implementation remains the
    exact CLEAN_PLURALITY_TIE_CORE policy that passed the frozen shadow admission.
    """

    COMPONENT_ID = "ALG-G2-RAW-TASK-REPRESENTATION-V6"
    PARENT_COMPONENT_ID = "ALG-G2-RAW-TASK-REPRESENTATION-V4"
    SELECTED_POLICY = "CLEAN_PLURALITY_TIE_CORE"
    SELECTION_RECEIPT_SHA256 = "ab16a2e21bc2df656db0ba88f129fff239264b1971f869c32cd05482cab58320"
    DEEP_ADMISSION_RECEIPT_SHA256 = "3e5e78136072be7f93c194a12a569da762adfbe161b4be7bf1f25091c23c643b"
    ADMISSION_COMPLETION_RUN_ID = "34715604111"

    def __init__(self, v3_artifact):
        super().__init__(v3_artifact, self.SELECTED_POLICY)


__all__ = ["CanonicalRawTaskRepresentationRuntimeV6"]
