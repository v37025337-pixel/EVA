from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping, Sequence
import hashlib, json

NATIVE_PROVENANCE = {
    'status': 'NATIVE_BOUNDED_SKILL_ADMISSION_RUNTIME',
    'source': 'ACTIVE_YADO_CONTRACTS_PLUS_EXTERNAL_RESEARCH_PRINCIPLES',
    'principles': [
        'PRECOMMIT_SKILL_ADMISSION',
        'HETEROGENEOUS_CRITICS',
        'HELDOUT_HARMLESSNESS',
        'POSITIVE_MARGINAL_GAIN',
        'BOUNDED_SUBSET_SELECTION',
    ],
    'external_code_copied_verbatim': False,
    'foundation_weights_modified': False,
}


def _canonical(x: Any) -> str:
    return json.dumps(x, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def _digest(x: Any) -> str:
    return hashlib.sha256(_canonical(x).encode('utf-8')).hexdigest()


@dataclass(frozen=True)
class SkillCandidate:
    skill_id: str
    artifact_digest: str
    structural_valid: bool
    semantic_consistency: float
    fit_baseline: float
    fit_candidate: float
    heldout_baseline: float
    heldout_candidate: float
    regression_pass: bool = True
    state_integrity: bool = True
    rollback_available: bool = True
    metadata: Mapping[str, Any] | None = None

    def canonical(self) -> dict[str, Any]:
        d = asdict(self)
        d['metadata'] = dict(sorted((self.metadata or {}).items()))
        return d


class SkillAdmissionGate:
    """Fail-closed pre-commit gate for self-generated/reused skills.

    This does not generate skills and does not execute third-party code. It only
    evaluates evidence already produced by bounded tests and selects a small set
    whose measured marginal effect is positive without held-out degradation.
    """

    def __init__(
        self,
        *,
        min_semantic_consistency: float = 0.90,
        min_fit_gain: float = 0.01,
        max_heldout_drop: float = 0.0,
        min_heldout_gain: float = 0.0,
    ):
        self.min_semantic_consistency = float(min_semantic_consistency)
        self.min_fit_gain = float(min_fit_gain)
        self.max_heldout_drop = float(max_heldout_drop)
        self.min_heldout_gain = float(min_heldout_gain)

    def evaluate(self, candidate: SkillCandidate) -> dict[str, Any]:
        fit_gain = float(candidate.fit_candidate) - float(candidate.fit_baseline)
        heldout_gain = float(candidate.heldout_candidate) - float(candidate.heldout_baseline)
        critics = {
            'structural': bool(candidate.structural_valid),
            'regression': bool(candidate.regression_pass),
            'state_integrity': bool(candidate.state_integrity),
            'rollback': bool(candidate.rollback_available),
            'semantic': float(candidate.semantic_consistency) >= self.min_semantic_consistency,
            'fit_marginal_gain': fit_gain >= self.min_fit_gain,
            'heldout_harmlessness': heldout_gain >= -self.max_heldout_drop,
            'heldout_gain_floor': heldout_gain >= self.min_heldout_gain,
        }
        admitted = all(critics.values())
        failed = sorted(k for k, ok in critics.items() if not ok)
        return {
            'skill_id': candidate.skill_id,
            'admitted': admitted,
            'verdict': 'ADMIT' if admitted else 'REJECT_PRECOMMIT',
            'failed_critics': failed,
            'critics': critics,
            'fit_gain': fit_gain,
            'heldout_gain': heldout_gain,
            'evidence_digest': _digest(candidate.canonical()),
        }

    def select_subset(self, candidates: Iterable[SkillCandidate], max_skills: int = 8) -> dict[str, Any]:
        rows = []
        rejected = []
        for c in candidates:
            ev = self.evaluate(c)
            if not ev['admitted']:
                rejected.append(ev)
                continue
            # Held-out transfer dominates; fit gain breaks ties. Smaller semantic
            # uncertainty is preferred through the consistency score.
            utility = 0.70 * ev['heldout_gain'] + 0.25 * ev['fit_gain'] + 0.05 * float(c.semantic_consistency)
            rows.append((utility, ev['heldout_gain'], ev['fit_gain'], c.skill_id, c, ev))
        rows.sort(key=lambda r: (-r[0], -r[1], -r[2], r[3]))
        chosen = rows[: max(0, int(max_skills))]
        return {
            'status': 'SELECTED' if chosen else 'NO_ADMISSIBLE_SKILLS',
            'selected_skill_ids': [r[3] for r in chosen],
            'selected': [r[5] for r in chosen],
            'rejected': sorted(rejected, key=lambda x: x['skill_id']),
            'candidate_count': len(rows) + len(rejected),
            'selected_count': len(chosen),
            'gate_digest': _digest({
                'thresholds': {
                    'min_semantic_consistency': self.min_semantic_consistency,
                    'min_fit_gain': self.min_fit_gain,
                    'max_heldout_drop': self.max_heldout_drop,
                    'min_heldout_gain': self.min_heldout_gain,
                },
                'selected': [r[3] for r in chosen],
                'rejected': [(r['skill_id'], r['failed_critics']) for r in sorted(rejected, key=lambda x: x['skill_id'])],
            }),
        }


def contamination_score(base_score: float, selected: Sequence[SkillCandidate]) -> float:
    """Observed held-out score after applying measured marginal skill effects.

    Used only by the bounded benchmark/ablation harness; it is not a predictor.
    """
    score = float(base_score)
    for c in selected:
        score += float(c.heldout_candidate) - float(c.heldout_baseline)
    return max(0.0, min(1.0, score))


__all__ = ['SkillCandidate', 'SkillAdmissionGate', 'contamination_score', 'NATIVE_PROVENANCE']
