from __future__ import annotations

from collections import Counter

from yado_raw_task_representation_robustness_v4 import (
    RobustRawTaskRepresentationRuntimeV4,
    bracketless,
    core_view,
    edge_delimiterless,
    longest_view,
    wrapper_signal_v2,
)


class ExperienceGuidedRawTaskRepresentationRepairV2:
    """Bounded shadow successor to canonical V4.

    The repair preserves canonical V4 for ordinary inputs.  For wrapper-like or
    sequential inputs it permits an override only when at least three cleaned
    V3 views agree on the same capability.  This is deliberately conservative:
    useful wrapper robustness may transfer, while canonical direct behaviour
    remains the default and no canonical file is modified.
    """

    COMPONENT_ID = "ALG-G2-RAW-TASK-REPRESENTATION-EXPERIENCE-REPAIR-V2"
    PARENT_COMPONENT_ID = "ALG-G2-RAW-TASK-REPRESENTATION-V4"
    PARENT_MODE = "MULTIVIEW_EDGE_TIE_CORE"

    def __init__(self, v3_artifact):
        self.v4 = RobustRawTaskRepresentationRuntimeV4(v3_artifact, self.PARENT_MODE)
        self.parent = self.v4.parent

    def _clean_view_predictions(self, text):
        edge = edge_delimiterless(text)
        views = [
            core_view(text),
            edge,
            bracketless(text),
            longest_view(edge),
        ]
        return [self.parent.predict_capability(v) for v in views]

    def predict_capability(self, text):
        v4_prediction = self.v4.predict_capability(text)
        if not wrapper_signal_v2(text):
            return v4_prediction

        predictions = self._clean_view_predictions(text)
        counts = Counter(predictions)
        winner, count = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0]
        if count >= 3 and winner != v4_prediction:
            return winner
        return v4_prediction

    def descriptor(self, text):
        label = self.predict_capability(text)
        d = {
            "budget_limited": False,
            "quota_limited": False,
            "external_evidence_needed": False,
            "relation_needed": False,
            "disjunction_needed": False,
        }
        if label == "ALG-BUDGETED-STAGE-POLICY-V1":
            d["budget_limited"] = True
        elif label == "RESOURCE-PORTFOLIO-V1":
            d["external_evidence_needed"] = True
        elif label == "ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1":
            d["relation_needed"] = True
        return {
            "capability": label,
            "routing_descriptor": d,
            "raw_text": text,
            "parent_component": self.PARENT_COMPONENT_ID,
            "repair_component": self.COMPONENT_ID,
        }


def component(parent_digest):
    return {
        "schema": "yado.g2.raw_task_representation_experience_repair_v2.component.v1",
        "component_id": ExperienceGuidedRawTaskRepresentationRepairV2.COMPONENT_ID,
        "parent_component_id": ExperienceGuidedRawTaskRepresentationRepairV2.PARENT_COMPONENT_ID,
        "parent_component_digest": parent_digest,
        "strategy": "V4_DEFAULT_STRONG_CLEAN_VIEW_CONSENSUS_OVERRIDE",
        "ordinary_input_preserves_v4": True,
        "wrapper_override_min_clean_consensus": 3,
        "canonical_active": False,
        "automatic_promotion": False,
    }


__all__ = ["ExperienceGuidedRawTaskRepresentationRepairV2", "component"]
