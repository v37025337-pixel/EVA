from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from yado_core_v2_9_trace_crystallization import UnifiedYADOKernelV29TraceCrystallization

ROOT=Path(__file__).resolve().parent
DEFAULT_STATE=ROOT/'yado_canonical_state_v3_candidate.json'


def _tupleize(x):
    if isinstance(x,list): return tuple(_tupleize(v) for v in x)
    return x

def _eval(e,args):
    e=_tupleize(e);op=e[0]
    if op=='ARG': return int(args[int(e[1])])
    if op=='CONST': return int(e[1])
    if op=='ADD': return _eval(e[1],args)+_eval(e[2],args)
    if op=='SUB': return _eval(e[1],args)-_eval(e[2],args)
    if op=='MUL': return _eval(e[1],args)*_eval(e[2],args)
    if op=='MIN': return min(_eval(e[1],args),_eval(e[2],args))
    if op=='MAX': return max(_eval(e[1],args),_eval(e[2],args))
    raise ValueError(op)

class UnifiedYADOKernelV30Candidate(UnifiedYADOKernelV29TraceCrystallization):
    SCHEMA_VERSION=12
    PROFILE='YADO_V3_0_RC1_CONTROLLED_DURABLE_LOCAL'
    def __init__(self,db_path='yado_v30_candidate.db',state_path:str|None=None):
        super().__init__(db_path=db_path); self.state_path=Path(state_path) if state_path else DEFAULT_STATE
        self.canonical_state=self._load_state()
    def _load_state(self)->dict[str,Any]:
        if not self.state_path.exists(): return {'version':'2.9','canonical_durable_mutation':False,'learned_atom_registry':[]}
        return json.loads(self.state_path.read_text(encoding='utf-8'))
    def reload_canonical_state(self): self.canonical_state=self._load_state(); return self.canonical_state
    def call_learned_primitive(self,primitive_id:str,*args:int)->int:
        for p in self.canonical_state.get('learned_atom_registry',[]):
            if p.get('primitive_id')==primitive_id:
                if len(args)!=int(p['arity']): raise ValueError('arity')
                return _eval(p['microprogram'],tuple(args))
        raise KeyError(primitive_id)
    def epistemic_decision(self,calibrated_confidence:float,distance_ratio:float,train_output_unique:int)->str:
        p=self.canonical_state.get('epistemic_policy') or {}
        ok=(calibrated_confidence>=float(p.get('p_threshold',1.1)) and distance_ratio<=float(p.get('distance_threshold',-1)))
        if p.get('require_output_variation') and train_output_unique<2: ok=False
        if p.get('require_lattice_support') is True:
            # lattice support requires a richer query object; fail closed in this compact API
            ok=False
        return 'ACCEPT_REVERSIBLE' if ok else 'SEEK_MORE_EVIDENCE'
    def dynamic_domains(self):
        return dict(self.canonical_state.get('dynamic_domain_registry') or {})
    def execute_dynamic_domain(self,domain_id:str,*args:int)->int:
        d=self.dynamic_domains().get(domain_id)
        if d is None: raise KeyError(domain_id)
        return self.call_learned_primitive(d['primitive_id'],*args)
    def unified_snapshot(self):
        s=super().unified_snapshot(); s.update({
          'profile':self.PROFILE,
          'active_lineage':'YADO_V2_9_TRACE_CRYSTALLIZATION -> YADO_V3_0_RC1_CONTROLLED_DURABLE_LOCAL',
          'canonical_durable_mutation':bool(self.canonical_state.get('canonical_durable_mutation',False)),
          'canonical_state_version':self.canonical_state.get('version'),
          'learned_atomic_primitives':len(self.canonical_state.get('learned_atom_registry',[])),
          'calibrated_epistemic_policy_active':bool(self.canonical_state.get('epistemic_policy')),
          'promotion_scope':self.canonical_state.get('promotion_scope','NONE'),
        }); return s

__all__=['UnifiedYADOKernelV30Candidate']
