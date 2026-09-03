from __future__ import annotations
from pathlib import Path
from typing import Mapping
from yado_core_v3_0_rc6_r1_real_external import UnifiedYADOKernelV30RC6R1RealExternal
from yado_organ_runtime_native_v1 import tree_predict

ROOT = Path(__file__).resolve().parent
DEFAULT_STATE = ROOT / 'yado_canonical_state_v3_rc6_r3_real_external.json'
PROVENANCE = {
    'origin': 'INDEPENDENT_REDERIVATION_FROM_DURABLE_STATE_AND_R3_CONSUMER_CONTRACT',
    'lost_original_recovered': False,
    'external_code_copied_verbatim': False,
    'scope': 'BOUNDED_RC6_R2_PUBLIC_RUNTIME_CONTRACT',
}

class UnifiedYADOKernelV30RC6R2NativeExternal(UnifiedYADOKernelV30RC6R1RealExternal):
    """Native bounded R2 bridge re-derived from the durable state/consumer contract.

    It preserves the R2 public behavior needed by R3 without depending on the
    compatibility-recovery bridge module. This is a new implementation, not a
    claim that the lost historical source was recovered.
    """
    PROFILE = 'YADO_V3_0_RC6_R2_REAL_EXTERNAL_TRAINED_LOCAL'
    SCHEMA_VERSION = 21

    def __init__(self, db_path='yado_v30_rc6_r2_real_external.db', state_path=None):
        super().__init__(db_path=db_path, state_path=state_path or str(DEFAULT_STATE))

    def logic_registry(self):
        return dict(self.real_external_registry().get('LOGIC') or {})

    def predict_external_logic(self, features: Mapping[str, object]):
        model = self.logic_registry().get('serialized_model')
        if not isinstance(model, dict):
            return {'action': 'SEEK_MORE_EVIDENCE', 'reason': 'NO_DURABLE_LOGIC_MODEL'}
        return {
            'action': 'USE_MODEL',
            'prediction': bool(tree_predict(model, dict(features))),
            'representation_version': self.logic_registry().get('representation_version'),
        }

    def route_external_text(self, text: str):
        cfg = self.real_external_registry().get('INTELLIGENCE', {})
        n = int(cfg.get('ngram_n', 3))
        profiles = cfg.get('centroid_profiles') or {}
        grams = self._grams(text, n)
        scores = {name: self._cos(grams, self._grams(profile, n)) for name, profile in profiles.items()}
        if len(scores) < 2:
            return {
                'action': 'SEEK_MORE_EVIDENCE',
                'scores': scores,
                'margin': 0.0,
                'top_score': max(scores.values(), default=0.0),
            }
        ranked = sorted(scores.items(), key=lambda z: (z[1], z[0]), reverse=True)
        margin = ranked[0][1] - ranked[1][1]
        top = ranked[0][1]
        margin_min = float(cfg.get('defer_margin', 1.0))
        top_min = float(cfg.get('top_score_min', 0.0))
        accepted = margin >= margin_min and top >= top_min
        return {
            'action': 'USE_ROUTE' if accepted else 'SEEK_MORE_EVIDENCE',
            'route': ranked[0][0] if accepted else None,
            'top_candidate': ranked[0][0],
            'margin': margin,
            'threshold': margin_min,
            'top_score': top,
            'top_score_min': top_min,
            'scores': scores,
        }

    def unified_snapshot(self):
        snapshot = super().unified_snapshot()
        snapshot.update({'profile': self.PROFILE, 'schema_version': self.SCHEMA_VERSION, 'r2_logic': self.logic_registry()})
        return snapshot

__all__ = ['PROVENANCE', 'UnifiedYADOKernelV30RC6R2NativeExternal']
