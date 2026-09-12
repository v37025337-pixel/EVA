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


POLICIES = (
    "V4_CONTROL",
    "CORE_ON_SIGNAL",
    "EDGE_ON_SIGNAL",
    "BRACKETLESS_ON_SIGNAL",
    "LONGEST_EDGE_ON_SIGNAL",
    "CLEAN_MAJORITY_TIE_V4",
    "CLEAN_MAJORITY_TIE_CORE",
    "CLEAN_PLURALITY_TIE_V4",
    "CLEAN_PLURALITY_TIE_CORE",
    "CORE_SUPPORTED_2",
    "NON_V4_CLEAN_CONSENSUS_2",
    "V4_CORE_EDGE_MAJORITY",
)


def _winner(predictions, tie):
    counts = Counter(predictions)
    best = max(counts.values())
    winners = sorted(k for k, n in counts.items() if n == best)
    if len(winners) == 1:
        return winners[0]
    if tie in winners:
        return tie
    return winners[0]


class ResidualDrivenRawTaskRepresentationRepairV3:
    COMPONENT_ID = "ALG-G2-RAW-TASK-REPRESENTATION-RESIDUAL-REPAIR-V3"
    PARENT_COMPONENT_ID = "ALG-G2-RAW-TASK-REPRESENTATION-V4"
    PARENT_MODE = "MULTIVIEW_EDGE_TIE_CORE"

    def __init__(self, v3_artifact, policy):
        policy = str(policy)
        if policy not in POLICIES:
            raise ValueError("UNKNOWN_RESIDUAL_REPAIR_POLICY:" + policy)
        self.policy = policy
        self.v4 = RobustRawTaskRepresentationRuntimeV4(v3_artifact, self.PARENT_MODE)
        self.parent = self.v4.parent

    def _views(self, text):
        raw = str(text)
        edge = edge_delimiterless(raw)
        return {
            "raw": raw,
            "bracketless": bracketless(raw),
            "edge": edge,
            "core": core_view(raw),
            "longest_edge": longest_view(edge),
        }

    def _signal(self, text, views):
        raw = str(text).strip()
        return (
            wrapper_signal_v2(raw)
            or views["core"].strip() != raw
            or views["edge"].strip() != raw
            or views["bracketless"].strip() != raw
        )

    def predict_capability(self, text):
        v4p = self.v4.predict_capability(text)
        if self.policy == "V4_CONTROL":
            return v4p

        views = self._views(text)
        if not self._signal(text, views):
            return v4p

        preds = {k: self.parent.predict_capability(v) for k, v in views.items()}
        corep = preds["core"]
        clean = [preds["core"], preds["edge"], preds["bracketless"], preds["longest_edge"]]

        if self.policy == "CORE_ON_SIGNAL":
            return corep
        if self.policy == "EDGE_ON_SIGNAL":
            return preds["edge"]
        if self.policy == "BRACKETLESS_ON_SIGNAL":
            return preds["bracketless"]
        if self.policy == "LONGEST_EDGE_ON_SIGNAL":
            return preds["longest_edge"]
        if self.policy == "CLEAN_MAJORITY_TIE_V4":
            counts = Counter(clean)
            best = max(counts.values())
            if best >= 3:
                return _winner(clean, v4p)
            return v4p
        if self.policy == "CLEAN_MAJORITY_TIE_CORE":
            counts = Counter(clean)
            best = max(counts.values())
            if best >= 3:
                return _winner(clean, corep)
            return v4p
        if self.policy == "CLEAN_PLURALITY_TIE_V4":
            return _winner(clean, v4p)
        if self.policy == "CLEAN_PLURALITY_TIE_CORE":
            return _winner(clean, corep)
        if self.policy == "CORE_SUPPORTED_2":
            return corep if clean.count(corep) >= 2 else v4p
        if self.policy == "NON_V4_CLEAN_CONSENSUS_2":
            counts = Counter(clean)
            alternatives = sorted(
                ((n, label) for label, n in counts.items() if label != v4p and n >= 2),
                key=lambda x: (-x[0], x[1]),
            )
            return alternatives[0][1] if alternatives else v4p
        if self.policy == "V4_CORE_EDGE_MAJORITY":
            votes = [v4p, corep, preds["edge"]]
            return _winner(votes, v4p)
        raise AssertionError(self.policy)

    def descriptor(self, text):
        label = self.predict_capability(text)
        return {
            "capability": label,
            "raw_text": text,
            "repair_component": self.COMPONENT_ID,
            "parent_component": self.PARENT_COMPONENT_ID,
            "policy": self.policy,
        }


def component(policy, parent_digest):
    return {
        "schema": "yado.g2.raw_task_representation_residual_repair_v3.component.v1",
        "component_id": ResidualDrivenRawTaskRepresentationRepairV3.COMPONENT_ID,
        "parent_component_id": ResidualDrivenRawTaskRepresentationRepairV3.PARENT_COMPONENT_ID,
        "parent_component_digest": parent_digest,
        "policy": str(policy),
        "policy_family": list(POLICIES),
        "ordinary_no_signal_preserves_v4": True,
        "canonical_active": False,
        "automatic_promotion": False,
    }


__all__ = ["POLICIES", "ResidualDrivenRawTaskRepresentationRepairV3", "component"]
