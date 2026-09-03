from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Iterable, Mapping, Sequence
import hashlib
import json
import math
import time

NATIVE_PROVENANCE = {
    "origin": "YADO_NATIVE_SYNTHESIS_FROM_MULTI_THEORY_FUNCTIONAL_INDICATORS",
    "architecture": "YADO_CAUSAL_REFLECTIVE_WORKSPACE_V1",
    "copies_external_code_verbatim": False,
    "changes_foundation_weights": False,
    "subjective_consciousness_claimed": False,
}

_ALLOWED_SOURCE_KINDS = {"external", "memory", "simulation", "self_model", "tool_observation"}


def _canon(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha(obj: Any) -> str:
    return hashlib.sha256(_canon(obj)).hexdigest()


@dataclass(frozen=True)
class WorkspaceItem:
    item_id: str
    source: str
    source_kind: str
    content: Any
    confidence: float = 0.5
    goal_relevance: float = 0.5
    novelty: float = 0.5
    urgency: float = 0.0
    epistemic_risk: float = 0.0
    tags: tuple[str, ...] = ()
    support_ids: tuple[str, ...] = ()

    def __post_init__(self):
        if self.source_kind not in _ALLOWED_SOURCE_KINDS:
            raise ValueError(f"UNKNOWN_SOURCE_KIND:{self.source_kind}")
        for name in ("confidence", "goal_relevance", "novelty", "urgency", "epistemic_risk"):
            v = float(getattr(self, name))
            if not (0.0 <= v <= 1.0):
                raise ValueError(f"INVALID_{name.upper()}:{v}")


@dataclass
class AttentionSchemaState:
    cycle_index: int = 0
    selected_ids: list[str] = field(default_factory=list)
    selected_sources: list[str] = field(default_factory=list)
    selection_reasons: dict[str, dict[str, float]] = field(default_factory=dict)
    predicted_next_source_kind: str | None = None
    actual_next_source_kind: str | None = None
    prediction_total: int = 0
    prediction_correct: int = 0

    @property
    def calibration(self) -> float | None:
        return None if self.prediction_total == 0 else self.prediction_correct / self.prediction_total


@dataclass
class PredictionState:
    counts: dict[str, dict[str, int]] = field(default_factory=dict)
    total_updates: int = 0
    cumulative_error: float = 0.0

    def _key(self, context: str, action: str) -> str:
        return f"{context}::{action}"

    def predict(self, context: str, action: str, outcomes: Sequence[str] | None = None) -> dict[str, float]:
        key = self._key(context, action)
        row = self.counts.get(key, {})
        universe = set(outcomes or ()) | set(row)
        if not universe:
            return {}
        # Laplace smoothing makes the initial prediction explicit rather than magical.
        denom = sum(row.values()) + len(universe)
        return {o: (row.get(o, 0) + 1) / denom for o in sorted(universe)}

    def update(self, context: str, action: str, observed: str, outcomes: Sequence[str] | None = None) -> float:
        pred = self.predict(context, action, outcomes=tuple(set(outcomes or ()) | {observed}))
        p = pred.get(observed, 0.0)
        error = 1.0 - p
        key = self._key(context, action)
        row = self.counts.setdefault(key, {})
        row[observed] = row.get(observed, 0) + 1
        self.total_updates += 1
        self.cumulative_error += error
        return error

    @property
    def mean_prediction_error(self) -> float | None:
        return None if self.total_updates == 0 else self.cumulative_error / self.total_updates


@dataclass(frozen=True)
class EpisodeRecord:
    episode_id: str
    parent_hash: str | None
    episode_hash: str
    goal: str
    selected_ids: tuple[str, ...]
    selected_source_kinds: tuple[str, ...]
    broadcasts: Mapping[str, Any]
    metacognitive_action: str
    action: str | None
    predicted_outcomes: Mapping[str, float]
    observed_outcome: str | None
    prediction_error: float | None
    commit_candidates: tuple[str, ...]
    committed_beliefs: tuple[str, ...]
    attention_prediction: str | None
    timestamp_ns: int


class CausalReflectiveWorkspace:
    """Bounded functional integration runtime synthesized for YADO.

    Design commitments:
      * limited capacity / selective competition;
      * global broadcast to heterogeneous consumers;
      * recurrent prediction->observation->error loop;
      * explicit attention schema and calibration;
      * metacognitive action is a causal gate;
      * provenance-aware source monitoring;
      * content-addressed episodic continuity.

    It is an engineering architecture. It makes no claim of subjective experience.
    """

    def __init__(self, capacity: int = 4, diversity_penalty: float = 0.16):
        if capacity < 1 or capacity > 16:
            raise ValueError("CAPACITY_OUT_OF_BOUNDS")
        self.capacity = int(capacity)
        self.diversity_penalty = float(diversity_penalty)
        self.attention = AttentionSchemaState()
        self.predictor = PredictionState()
        self.episodes: list[EpisodeRecord] = []
        self._last_focus_kind: str | None = None

    @staticmethod
    def _goal_terms(goal: str) -> set[str]:
        return {t.lower() for t in goal.replace("_", " ").replace("/", " ").split() if t}

    def _score(self, item: WorkspaceItem, goal: str, selected: Sequence[WorkspaceItem]) -> tuple[float, dict[str, float]]:
        goal_terms = self._goal_terms(goal)
        tag_terms = {t.lower() for t in item.tags}
        lexical_goal = 1.0 if goal_terms and goal_terms.intersection(tag_terms) else 0.0
        provenance_bonus = 0.12 if item.source_kind in {"external", "tool_observation"} else 0.04 if item.source_kind in {"memory", "self_model"} else -0.08
        repeated_source = sum(1 for x in selected if x.source == item.source)
        diversity_cost = self.diversity_penalty * repeated_source
        unresolved_bonus = 0.08 if self._last_focus_kind and item.source_kind != self._last_focus_kind else 0.0
        components = {
            "goal": 0.34 * float(item.goal_relevance) + 0.12 * lexical_goal,
            "confidence": 0.18 * float(item.confidence),
            "novelty": 0.12 * float(item.novelty),
            "urgency": 0.10 * float(item.urgency),
            "provenance": provenance_bonus,
            "unresolved_shift": unresolved_bonus,
            "epistemic_risk": -0.22 * float(item.epistemic_risk),
            "diversity_cost": -diversity_cost,
        }
        return sum(components.values()), components

    def select(self, items: Iterable[WorkspaceItem | Mapping[str, Any]], goal: str) -> list[WorkspaceItem]:
        pool = [x if isinstance(x, WorkspaceItem) else WorkspaceItem(**x) for x in items]
        chosen: list[WorkspaceItem] = []
        reasons: dict[str, dict[str, float]] = {}
        while pool and len(chosen) < self.capacity:
            scored = []
            for item in pool:
                score, comps = self._score(item, goal, chosen)
                scored.append((score, item.item_id, item, comps))
            scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
            _, _, best, comps = scored[0]
            chosen.append(best)
            reasons[best.item_id] = {**comps, "total": sum(comps.values())}
            pool = [x for x in pool if x.item_id != best.item_id]

        self.attention.cycle_index += 1
        self.attention.selected_ids = [x.item_id for x in chosen]
        self.attention.selected_sources = [x.source for x in chosen]
        self.attention.selection_reasons = reasons
        if chosen:
            # Predict a shift away from a saturated current kind; otherwise retain the dominant kind.
            counts: dict[str, int] = {}
            for x in chosen:
                counts[x.source_kind] = counts.get(x.source_kind, 0) + 1
            dominant = max(sorted(counts), key=lambda k: counts[k])
            self.attention.predicted_next_source_kind = (
                "external" if dominant in {"simulation", "self_model"} else dominant
            )
        else:
            self.attention.predicted_next_source_kind = None
        return chosen

    def register_actual_next_focus(self, source_kind: str) -> None:
        if source_kind not in _ALLOWED_SOURCE_KINDS:
            raise ValueError("UNKNOWN_FOCUS_SOURCE_KIND")
        pred = self.attention.predicted_next_source_kind
        self.attention.actual_next_source_kind = source_kind
        if pred is not None:
            self.attention.prediction_total += 1
            self.attention.prediction_correct += int(pred == source_kind)
        self._last_focus_kind = source_kind

    def broadcast(self, selected: Sequence[WorkspaceItem], consumers: Mapping[str, Callable[[Sequence[WorkspaceItem]], Any]]) -> dict[str, Any]:
        # True broadcast means every registered consumer receives the same selected workspace state.
        payload = tuple(selected)
        return {name: fn(payload) for name, fn in consumers.items()}

    @staticmethod
    def source_monitor_allows_commit(item: WorkspaceItem, selected: Sequence[WorkspaceItem]) -> bool:
        if item.source_kind in {"external", "tool_observation"}:
            return True
        if item.source_kind in {"memory", "self_model"}:
            return item.confidence >= 0.75 and item.epistemic_risk <= 0.35
        # Simulations can influence planning but cannot become external facts without independent support.
        support = set(item.support_ids)
        selected_external = {x.item_id for x in selected if x.source_kind in {"external", "tool_observation"}}
        return bool(support & selected_external) and item.confidence >= 0.80 and item.epistemic_risk <= 0.25

    def cycle(
        self,
        *,
        goal: str,
        items: Iterable[WorkspaceItem | Mapping[str, Any]],
        consumers: Mapping[str, Callable[[Sequence[WorkspaceItem]], Any]],
        metacognitive_action: str,
        context: str = "default",
        action: str | None = None,
        possible_outcomes: Sequence[str] = (),
        observed_outcome: str | None = None,
        proposed_belief_ids: Sequence[str] = (),
    ) -> EpisodeRecord:
        if metacognitive_action not in {"EXECUTE", "SEEK_EVIDENCE", "ROUTE_FRAMEWORK", "WITHHOLD"}:
            raise ValueError("INVALID_METACOGNITIVE_ACTION")
        selected = self.select(items, goal)
        broadcasts = self.broadcast(selected, consumers)
        predicted = self.predictor.predict(context, action or "NO_ACTION", outcomes=possible_outcomes)
        prediction_error = None
        if observed_outcome is not None:
            prediction_error = self.predictor.update(context, action or "NO_ACTION", observed_outcome, outcomes=possible_outcomes)

        by_id = {x.item_id: x for x in selected}
        commits: list[str] = []
        if metacognitive_action == "EXECUTE":
            for item_id in proposed_belief_ids:
                item = by_id.get(item_id)
                if item and self.source_monitor_allows_commit(item, selected):
                    commits.append(item_id)

        parent_hash = self.episodes[-1].episode_hash if self.episodes else None
        timestamp_ns = time.time_ns()
        core = {
            "parent_hash": parent_hash,
            "goal": goal,
            "selected_ids": [x.item_id for x in selected],
            "selected_source_kinds": [x.source_kind for x in selected],
            "broadcasts": broadcasts,
            "metacognitive_action": metacognitive_action,
            "action": action,
            "predicted_outcomes": predicted,
            "observed_outcome": observed_outcome,
            "prediction_error": prediction_error,
            "commit_candidates": list(proposed_belief_ids),
            "committed_beliefs": commits,
            "attention_prediction": self.attention.predicted_next_source_kind,
            "timestamp_ns": timestamp_ns,
        }
        episode_hash = _sha(core)
        episode_id = f"CRW-{len(self.episodes)+1:08d}-{episode_hash[:12]}"
        ep = EpisodeRecord(
            episode_id=episode_id,
            parent_hash=parent_hash,
            episode_hash=episode_hash,
            goal=goal,
            selected_ids=tuple(core["selected_ids"]),
            selected_source_kinds=tuple(core["selected_source_kinds"]),
            broadcasts=broadcasts,
            metacognitive_action=metacognitive_action,
            action=action,
            predicted_outcomes=predicted,
            observed_outcome=observed_outcome,
            prediction_error=prediction_error,
            commit_candidates=tuple(proposed_belief_ids),
            committed_beliefs=tuple(commits),
            attention_prediction=self.attention.predicted_next_source_kind,
            timestamp_ns=timestamp_ns,
        )
        self.episodes.append(ep)
        return ep

    def verify_continuity(self) -> bool:
        parent = None
        for ep in self.episodes:
            if ep.parent_hash != parent:
                return False
            core = {
                "parent_hash": ep.parent_hash,
                "goal": ep.goal,
                "selected_ids": list(ep.selected_ids),
                "selected_source_kinds": list(ep.selected_source_kinds),
                "broadcasts": ep.broadcasts,
                "metacognitive_action": ep.metacognitive_action,
                "action": ep.action,
                "predicted_outcomes": dict(ep.predicted_outcomes),
                "observed_outcome": ep.observed_outcome,
                "prediction_error": ep.prediction_error,
                "commit_candidates": list(ep.commit_candidates),
                "committed_beliefs": list(ep.committed_beliefs),
                "attention_prediction": ep.attention_prediction,
                "timestamp_ns": ep.timestamp_ns,
            }
            if _sha(core) != ep.episode_hash:
                return False
            parent = ep.episode_hash
        return True

    def functional_indicator_snapshot(self) -> dict[str, Any]:
        # Engineering indicators, explicitly not a consciousness probability.
        recurrence = self.predictor.total_updates > 0
        broadcast = bool(self.episodes and any(len(ep.broadcasts) >= 2 for ep in self.episodes))
        attention = self.attention.cycle_index > 0
        continuity = self.verify_continuity() if self.episodes else False
        source_monitor = bool(self.episodes)
        return {
            "architecture": "YADO_CAUSAL_REFLECTIVE_WORKSPACE_V1",
            "limited_capacity_workspace": True,
            "selective_attention": attention,
            "global_broadcast": broadcast,
            "recurrent_prediction_loop": recurrence,
            "attention_schema": attention,
            "metacognitive_gate": True,
            "source_monitoring": source_monitor,
            "content_addressed_temporal_continuity": continuity,
            "subjective_consciousness_claimed": False,
        }


__all__ = [
    "WorkspaceItem", "AttentionSchemaState", "PredictionState", "EpisodeRecord",
    "CausalReflectiveWorkspace", "NATIVE_PROVENANCE",
]
