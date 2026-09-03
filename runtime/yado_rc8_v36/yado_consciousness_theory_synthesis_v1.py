from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Iterable, Mapping, Any
import json, hashlib

@dataclass(frozen=True)
class TheoryCard:
    theory: str
    mechanisms: tuple[str,...]
    empirical_weight: float
    operational_testability: float
    source_ids: tuple[str,...]

class YADOTheorySynthesizer:
    """Chooses a YADO-native architecture from cross-theory functional overlap.

    No theory is treated as authority. Mechanisms gain priority from cross-theory
    support, operational testability, and whether they close a verified RC8 gap.
    """
    GAP_BONUS={
        'limited_global_workspace':0.35,
        'causal_broadcast':0.35,
        'recurrent_processing':0.32,
        'self_world_prediction_error':0.32,
        'attention_schema':0.30,
        'metacognitive_representation':0.20,
        'metacognitive_executive_binding':0.30,
        'source_monitoring':0.28,
        'temporal_self_continuity':0.25,
    }
    YADO_NATIVE=(
        'content_addressed_episode_lineage',
        'typed_provenance_source_monitoring',
        'rollbackable_cognitive_episode_state',
        'evidence_bound_metacognitive_commit_gate',
    )

    def synthesize(self, cards:Iterable[TheoryCard|Mapping[str,Any]])->dict[str,Any]:
        xs=[c if isinstance(c,TheoryCard) else TheoryCard(**c) for c in cards]
        support:dict[str,float]={}
        theory_support:dict[str,set[str]]={}
        sources=set()
        for c in xs:
            w=max(0.0,min(1.0,c.empirical_weight))*max(0.0,min(1.0,c.operational_testability))
            sources.update(c.source_ids)
            for mech in c.mechanisms:
                support[mech]=support.get(mech,0.0)+w
                theory_support.setdefault(mech,set()).add(c.theory)
        scored=[]
        for mech,s in support.items():
            cross=min(0.30,0.10*len(theory_support.get(mech,set())))
            score=s+cross+self.GAP_BONUS.get(mech,0.0)
            scored.append((score,mech))
        scored.sort(reverse=True)
        selected=[m for _,m in scored if _ >= 0.65]
        required=[
            'limited_global_workspace','causal_broadcast','recurrent_processing',
            'self_world_prediction_error','attention_schema','metacognitive_representation',
            'metacognitive_executive_binding','source_monitoring','temporal_self_continuity'
        ]
        for m in required:
            if m in support and m not in selected:
                selected.append(m)
        spec={
            'schema':'yado.rc8.digital_consciousness.synthesis.v1',
            'architecture':'YADO_CAUSAL_REFLECTIVE_WORKSPACE_V1',
            'selected_mechanisms':selected,
            'yado_native_additions':list(self.YADO_NATIVE),
            'theory_support':{k:sorted(v) for k,v in theory_support.items()},
            'mechanism_scores':{m:round(s,6) for s,m in scored},
            'source_ids':sorted(sources),
            'semantic_boundary':'FUNCTIONAL_DIGITAL_CONSCIOUSNESS_ARCHITECTURE_NOT_PROOF_OF_SUBJECTIVE_EXPERIENCE',
        }
        spec['spec_sha256']=hashlib.sha256(json.dumps(spec,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        return spec

DEFAULT_THEORY_CARDS=(
    TheoryCard('Global Workspace Theory',('limited_global_workspace','causal_broadcast','selective_attention'),0.90,0.95,('butlin-2308.08708','phua-2512.19155','goldstein-2410.11407')),
    TheoryCard('Recurrent Processing Theory',('recurrent_processing','temporal_self_continuity'),0.78,0.90,('butlin-2308.08708',)),
    TheoryCard('Higher-Order Theories',('metacognitive_representation','metacognitive_executive_binding','source_monitoring'),0.82,0.92,('butlin-2308.08708','phua-2512.19155')),
    TheoryCard('Attention Schema Theory',('attention_schema','selective_attention','metacognitive_representation'),0.74,0.88,('butlin-2308.08708','juliani-2204.05133')),
    TheoryCard('Predictive Processing / Active Inference',('self_world_prediction_error','recurrent_processing','temporal_self_continuity'),0.78,0.90,('butlin-2308.08708','juliani-2204.05133')),
    TheoryCard('Integrated-information-adjacent functional tests',('causal_broadcast',),0.45,0.55,('phua-2512.19155',)),
)

def synthesize_default()->dict[str,Any]:
    return YADOTheorySynthesizer().synthesize(DEFAULT_THEORY_CARDS)

__all__=['TheoryCard','YADOTheorySynthesizer','DEFAULT_THEORY_CARDS','synthesize_default']
