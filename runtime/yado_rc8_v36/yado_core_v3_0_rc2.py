from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from yado_core_v3_0_candidate import UnifiedYADOKernelV30Candidate

ROOT=Path(__file__).resolve().parent
DEFAULT_STATE=ROOT/'yado_canonical_state_v3_rc2_candidate.json'

class UnifiedYADOKernelV30RC2(UnifiedYADOKernelV30Candidate):
    SCHEMA_VERSION=13
    PROFILE='YADO_V3_0_RC2_EXTENSIBLE_MICROCODE_LOCAL'
    def __init__(self,db_path='yado_v30_rc2.db',state_path:str|None=None):
        super().__init__(db_path=db_path,state_path=state_path or str(DEFAULT_STATE))

    def extension_primitives(self):
        return {p['primitive_id']:p for p in self.canonical_state.get('extension_primitive_registry',[])}

    def call_extension_primitive(self, primitive_id:str, x:int)->int:
        p=self.extension_primitives().get(primitive_id)
        if p is None: raise KeyError(primitive_id)
        if p.get('representation')!='UNARY_TRANSLATION_TRANSDUCER': raise ValueError('representation')
        d=p['descriptor']; anchor=int(d['anchor']); prefix=[int(v) for v in d['prefix']]; cycle=[int(v) for v in d['cycle']]
        if not cycle: raise ValueError('empty_cycle')
        if x<anchor: raise ValueError('out_of_support_left')
        i=x-anchor
        if i<len(prefix): return prefix[i]
        return cycle[(i-len(prefix))%len(cycle)]

    def eval_extensible_expr(self,e:Any,x:int)->int:
        op=e[0]
        if op=='ARG': return x
        if op=='CONST': return int(e[1])
        if op=='CALL_EXT': return self.call_extension_primitive(e[1], self.eval_extensible_expr(e[2],x))
        a=self.eval_extensible_expr(e[1],x); b=self.eval_extensible_expr(e[2],x)
        if op=='ADD': return a+b
        if op=='SUB': return a-b
        if op=='MUL': return a*b
        if op=='MIN': return min(a,b)
        if op=='MAX': return max(a,b)
        raise ValueError(op)

    def unified_snapshot(self):
        s=super().unified_snapshot(); s.update({
            'profile':self.PROFILE,
            'active_lineage':'YADO_V3_0_RC1 -> YADO_V3_0_RC2_EXTENSIBLE_MICROCODE_LOCAL',
            'extension_atomic_primitives':len(self.extension_primitives()),
            'fixed_microcode_operator_set_no_longer_complete':bool(self.extension_primitives()),
        }); return s

__all__=['UnifiedYADOKernelV30RC2']
