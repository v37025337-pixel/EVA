from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
import hashlib
import json
import math
import time


SCHEMA = "yado.rc8.digital_causal_workspace.v1"
SEMANTIC_BOUNDARY = (
    "FUNCTIONAL_DIGITAL_CONSCIOUSNESS_ARCHITECTURE_NOT_PROOF_OF_SUBJECTIVE_EXPERIENCE"
)


def _sha(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _clip(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(v)))


@dataclass(frozen=True)
class Candidate:
    content: str
    source_kind: str
    salience: float
    goal_relevance: float
    novelty: float
    uncertainty: float
    evidence_strength: float
    predicted_utility: float = 0.0

    def score(self, attention_bias: float = 0.0) -> float:
        # Limited workspace competition. Uncertainty alone never wins.
        return (
            0.24 * _clip(self.salience)
            + 0.25 * _clip(self.goal_relevance)
            + 0.16 * _clip(self.novelty)
            + 0.20 * _clip(self.evidence_strength)
            + 0.15 * _clip(self.predicted_utility)
            + attention_bias
            - 0.22 * _clip(self.uncertainty)
        )


@dataclass
class BroadcastReceipt:
    cycle_id: int
    selected_content: str
    source_kind: str
    selection_score: float
    why_selected: Dict[str, float]
    attention_prediction: str
    attention_correct: bool
    predicted_effect: float
    observed_effect: float
    prediction_error: float
    metacognitive_action: str
    broadcast_targets: List[str]
    self_state_before: str
    self_state_after: str
    source_monitoring_ok: bool
    causal_digest: str = ""

    def finalize(self) -> "BroadcastReceipt":
        payload = asdict(self).copy()
        payload["causal_digest"] = ""
        self.causal_digest = _sha(payload)
        return self


class YADODigitalCausalWorkspaceV1:
    """
    YADO-specific functional digital-consciousness candidate.

    Distinguishing design:
      * bounded selective workspace rather than full-state exposure;
      * proof-carrying global broadcasts;
      * attention-schema prediction of what will win the workspace;
      * recurrent self/world prediction-error update;
      * metacognitive action gate;
      * source monitoring for external vs internally generated content;
      * event-driven temporal continuity via explicit persisted state.

    This class does not claim or infer subjective consciousness.
    """

    def __init__(
        self,
        *,
        capacity: int = 3,
        subscribers: Optional[Iterable[str]] = None,
        continuity_path: Optional[str] = None,
    ):
        if capacity < 1 or capacity > 8:
            raise ValueError("capacity must be in [1,8]")
        self.capacity = int(capacity)
        self.subscribers = list(subscribers or [
            "MEMORY", "LOGIC", "THINKING", "INTELLIGENCE", "SELF_MODEL", "EXECUTIVE"
        ])
        self.continuity_path = Path(continuity_path) if continuity_path else None
        self.cycle_id = 0
        self.attention_schema: Dict[str, float] = {}
        self.world_expectation: Dict[str, float] = {}
        self.self_state: Dict[str, Any] = {
            "workspace_load": 0.0,
            "mean_prediction_error": 1.0,
            "last_action": "WITHHOLD",
            "broadcast_count": 0,
            "continuity_epoch": 0,
        }
        self.receipts: List[BroadcastReceipt] = []
        if self.continuity_path and self.continuity_path.exists():
            self._load_continuity()

    def _load_continuity(self) -> None:
        data = json.loads(self.continuity_path.read_text(encoding="utf-8"))
        if data.get("schema") != SCHEMA:
            raise ValueError("continuity schema mismatch")
        self.cycle_id = int(data.get("cycle_id", 0))
        self.attention_schema = {
            str(k): float(v) for k, v in dict(data.get("attention_schema", {})).items()
        }
        self.world_expectation = {
            str(k): float(v) for k, v in dict(data.get("world_expectation", {})).items()
        }
        self.self_state.update(dict(data.get("self_state", {})))
        self.self_state["continuity_epoch"] = int(
            self.self_state.get("continuity_epoch", 0)
        ) + 1

    def persist(self) -> Dict[str, Any]:
        if not self.continuity_path:
            return {"persisted": False}
        payload = {
            "schema": SCHEMA,
            "semantic_boundary": SEMANTIC_BOUNDARY,
            "cycle_id": self.cycle_id,
            "attention_schema": self.attention_schema,
            "world_expectation": self.world_expectation,
            "self_state": self.self_state,
            "last_receipt_digest": self.receipts[-1].causal_digest if self.receipts else None,
        }
        self.continuity_path.parent.mkdir(parents=True, exist_ok=True)
        self.continuity_path.write_text(
            json.dumps(payload, sort_keys=True, indent=2),
            encoding="utf-8",
        )
        return {"persisted": True, "digest": _sha(payload)}

    def _attention_bias(self, c: Candidate) -> float:
        return 0.08 * _clip(self.attention_schema.get(c.source_kind, 0.5) - 0.5, -0.5, 0.5)

    def _predict_attention(self, candidates: List[Candidate]) -> str:
        if not candidates:
            return ""
        # Attention schema is intentionally approximate; it is trained from wins.
        return max(
            candidates,
            key=lambda c: (
                0.55 * c.goal_relevance
                + 0.25 * c.salience
                + 0.20 * self.attention_schema.get(c.source_kind, 0.5)
            ),
        ).content

    def compete(self, candidates: Iterable[Candidate]) -> List[Candidate]:
        cs = list(candidates)
        if not cs:
            return []
        ranked = sorted(
            cs,
            key=lambda c: c.score(self._attention_bias(c)),
            reverse=True,
        )
        return ranked[: self.capacity]

    def _metacognitive_action(self, winner: Candidate, score: float) -> str:
        # Conservative action selection: uncertain/weakly grounded content is not executed.
        if winner.uncertainty >= 0.72 or winner.evidence_strength < 0.30:
            return "SEEK_EVIDENCE"
        if score < 0.20:
            return "WITHHOLD"
        if winner.source_kind == "simulated" and winner.evidence_strength < 0.65:
            return "ROUTE_FRAMEWORK"
        return "EXECUTE"

    def _prediction_key(self, c: Candidate) -> str:
        return f"{c.source_kind}:{hashlib.sha1(c.content.encode('utf-8')).hexdigest()[:10]}"

    def _predict_effect(self, c: Candidate) -> float:
        key = self._prediction_key(c)
        return _clip(self.world_expectation.get(key, c.predicted_utility))

    def _update_prediction(self, c: Candidate, observed_effect: float) -> float:
        key = self._prediction_key(c)
        old = self._predict_effect(c)
        err = float(observed_effect) - old
        self.world_expectation[key] = _clip(old + 0.45 * err)
        return abs(err)

    def _update_attention_schema(self, winner: Candidate, predicted: str) -> None:
        for kind in {winner.source_kind}:
            old = self.attention_schema.get(kind, 0.5)
            target = 1.0
            self.attention_schema[kind] = _clip(old + 0.25 * (target - old))
        # Mild decay keeps the schema adaptive.
        for kind in list(self.attention_schema):
            if kind != winner.source_kind:
                self.attention_schema[kind] = _clip(
                    self.attention_schema[kind] * 0.98 + 0.01
                )

    def cycle(
        self,
        candidates: Iterable[Candidate],
        *,
        observed_effects: Optional[Dict[str, float]] = None,
        disable_broadcast: bool = False,
        disable_metacognition: bool = False,
        disable_recurrence: bool = False,
        disable_attention_schema: bool = False,
    ) -> Dict[str, Any]:
        cs = list(candidates)
        self.cycle_id += 1
        before = _sha(self.self_state)
        predicted_attention = "" if disable_attention_schema else self._predict_attention(cs)
        winners = self.compete(cs)
        if not winners:
            self.self_state["last_action"] = "WITHHOLD"
            return {
                "schema": SCHEMA,
                "cycle_id": self.cycle_id,
                "winners": [],
                "action": "WITHHOLD",
                "semantic_boundary": SEMANTIC_BOUNDARY,
            }

        winner = winners[0]
        score = winner.score(self._attention_bias(winner))
        action = (
            "EXECUTE"
            if disable_metacognition
            else self._metacognitive_action(winner, score)
        )
        predicted_effect = self._predict_effect(winner)
        observed_effect = _clip(
            (observed_effects or {}).get(winner.content, winner.predicted_utility)
        )
        pred_err = (
            abs(observed_effect - predicted_effect)
            if disable_recurrence
            else self._update_prediction(winner, observed_effect)
        )

        source_monitoring_ok = winner.source_kind in {
            "external", "memory", "simulated", "self_model", "tool"
        }
        targets = [] if disable_broadcast else list(self.subscribers)

        if not disable_attention_schema:
            self._update_attention_schema(winner, predicted_attention)

        prev_mean = float(self.self_state.get("mean_prediction_error", 1.0))
        self.self_state["mean_prediction_error"] = 0.7 * prev_mean + 0.3 * pred_err
        self.self_state["workspace_load"] = len(winners) / self.capacity
        self.self_state["last_action"] = action
        self.self_state["broadcast_count"] = int(self.self_state.get("broadcast_count", 0)) + (
            0 if disable_broadcast else 1
        )
        self.self_state["last_selected_source"] = winner.source_kind
        self.self_state["last_selected_digest"] = hashlib.sha256(
            winner.content.encode("utf-8")
        ).hexdigest()
        after = _sha(self.self_state)

        receipt = BroadcastReceipt(
            cycle_id=self.cycle_id,
            selected_content=winner.content,
            source_kind=winner.source_kind,
            selection_score=score,
            why_selected={
                "salience": winner.salience,
                "goal_relevance": winner.goal_relevance,
                "novelty": winner.novelty,
                "uncertainty": winner.uncertainty,
                "evidence_strength": winner.evidence_strength,
            },
            attention_prediction=predicted_attention,
            attention_correct=(predicted_attention == winner.content),
            predicted_effect=predicted_effect,
            observed_effect=observed_effect,
            prediction_error=pred_err,
            metacognitive_action=action,
            broadcast_targets=targets,
            self_state_before=before,
            self_state_after=after,
            source_monitoring_ok=source_monitoring_ok,
        ).finalize()
        self.receipts.append(receipt)

        return {
            "schema": SCHEMA,
            "semantic_boundary": SEMANTIC_BOUNDARY,
            "cycle_id": self.cycle_id,
            "workspace_capacity": self.capacity,
            "winners": [c.content for c in winners],
            "selected": winner.content,
            "action": action,
            "broadcast_targets": targets,
            "prediction_error": pred_err,
            "attention_prediction": predicted_attention,
            "attention_correct": predicted_attention == winner.content,
            "source_monitoring_ok": source_monitoring_ok,
            "causal_receipt": asdict(receipt),
        }


def theory_synthesis_contract() -> Dict[str, Any]:
    """
    YADO's own synthesis. The contract records influence, not endorsement.
    """
    return {
        "schema": "yado.rc8.digital_consciousness.theory_synthesis.v1",
        "architecture_name": "YADO_DIGITAL_CAUSAL_WORKSPACE_V1",
        "semantic_boundary": SEMANTIC_BOUNDARY,
        "influences": {
            "GWT": "limited-capacity competition and global availability",
            "HOT": "higher-order metacognitive access and confidence-sensitive control",
            "AST": "explicit model of attention allocation and expected shifts",
            "RPT_PREDICTIVE": "recurrent state update through prediction-error correction",
            "IIT_INSPIRED": "require causal self-effect and integration tests; no Phi claim",
        },
        "yado_specific_principles": [
            "PROOF_CARRYING_BROADCAST",
            "EVIDENCE_LINEAGE_BEFORE_GLOBAL_ACCESS",
            "PREDICTED_EFFECT_VS_OBSERVED_EFFECT_RECEIPT",
            "SOURCE_MONITORING_EXTERNAL_VS_SIMULATED",
            "EVENT_DRIVEN_TEMPORAL_CONTINUITY",
            "FAIL_CLOSED_METACOGNITIVE_EXECUTION",
        ],
        "not_claimed": [
            "subjective_experience",
            "phenomenal_consciousness",
            "qualia",
            "general_intelligence",
        ],
    }
