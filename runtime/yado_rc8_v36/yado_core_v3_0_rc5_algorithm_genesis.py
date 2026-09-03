from __future__ import annotations
import copy,json,itertools
from pathlib import Path
from typing import Any,Mapping,Sequence
from yado_core_v3_0_rc4_meta_autoevolution import UnifiedYADOKernelV30RC4MetaAutoEvolution
from yado_algorithm_component_runtime_native_v1 import (
    best_logic_leaf,best_intel_leaf,fit_thinking_skeleton,thinking_component_acc,
    predict_logic_component,predict_intel_component,strip_component,cj
)

ROOT=Path(__file__).resolve().parent
DEFAULT_STATE=ROOT/'yado_canonical_state_v3_rc5_algorithm_genesis.json'

def fill_template(x,bindings):
    if isinstance(x,dict):return {k:fill_template(v,bindings) for k,v in x.items()}
    if isinstance(x,list):return [fill_template(v,bindings) for v in x]
    if isinstance(x,str) and x in bindings:return bindings[x]
    return x

def signal_vars(t):
    out=[]
    def rec(x):
        if isinstance(x,dict):
            for k,v in x.items():
                if k=='key' and isinstance(v,str) and v.startswith('$SIGNAL_'):out.append(v)
                rec(v)
        elif isinstance(x,list):
            for v in x:rec(v)
    rec(t);return sorted(set(out))

def template_source(t):
    src=[]
    def rec(x):
        if isinstance(x,dict):
            if 'signal' in x and isinstance(x['signal'],dict):src.append(x['signal'].get('source'))
            for v in x.values():rec(v)
        elif isinstance(x,list):
            for v in x:rec(v)
    rec(t);return sorted(set(s for s in src if s))

class UnifiedYADOKernelV30RC5AlgorithmGenesis(UnifiedYADOKernelV30RC4MetaAutoEvolution):
    PROFILE='YADO_V3_0_RC5_BOUNDED_ALGORITHM_COMPONENT_GENESIS_LOCAL'
    SCHEMA_VERSION=18
    def __init__(self,db_path='yado_v30_rc5_alggen.db',state_path:str|None=None):
        super().__init__(db_path=db_path,state_path=state_path or str(DEFAULT_STATE))
    def algorithm_constructor_registry(self):return list(self.canonical_state.get('evolution_algorithm_constructor_registry') or [])
    def _constructor(self,source,signal_count):
        c=[]
        for z in self.algorithm_constructor_registry():
            t=z['program_template'];sv=signal_vars(t);src=template_source(t)
            if src==[source] and len(sv)==signal_count:c.append(z)
        if not c:raise RuntimeError(f'no constructor source={source} signals={signal_count}')
        return sorted(c,key=lambda z:z['constructor_id'])[0]

    def synthesize_logic_algorithm_component(self,fit,validation,revealed,blind):
        cons=self._constructor('INPUT',1);var=signal_vars(cons['program_template'])[0]
        keys=sorted(k for k in fit[0][0] if len({bool(r[0].get(k,False)) for r in fit})>1)
        cand=[]
        for key in keys:
            sk=fill_template(cons['program_template'],{var:key})
            p=[r for r in fit if bool(r[0].get(key,False))];q=[r for r in fit if not bool(r[0].get(key,False))]
            if not p or not q:continue
            a,_=best_logic_leaf(p,self._algs('LOGIC'));b,_=best_logic_leaf(q,self._algs('LOGIC'))
            m={'op':'IF_SIGNAL','signal':sk['signal'],'then':a,'else':b}
            v=sum(predict_logic_component(m,x)==y for x,y in validation)/len(validation)
            cand.append((v,-len(cj(m)),key,m))
        v,_,key,_=max(cand,key=lambda z:(z[0],z[1],z[2]))
        # refit selected constructor on all revealed evidence
        p=[r for r in revealed if bool(r[0].get(key,False))];q=[r for r in revealed if not bool(r[0].get(key,False))]
        a,_=best_logic_leaf(p,self._algs('LOGIC'));b,_=best_logic_leaf(q,self._algs('LOGIC'))
        m={'op':'IF_SIGNAL','signal':{'source':'INPUT','key':key,'threshold':.5},'then':a,'else':b}
        fresh=sum(predict_logic_component(m,x)==y for x,y in blind)/len(blind)
        return {'constructor_id':cons['constructor_id'],'binding':{var:key},'validation':v,'model':m,'fresh_blind':fresh}

    def synthesize_intelligence_algorithm_component(self,fit,validation,revealed,blind):
        cons=self._constructor('INPUT',1);var=signal_vars(cons['program_template'])[0]
        keys=sorted(k for k in fit[0][0] if len({float(r[0].get(k,0.0)) for r in fit})>1)
        cand=[]
        for key in keys:
            sk=fill_template(cons['program_template'],{var:key});p=[r for r in fit if float(r[0].get(key,0.0))>.5];q=[r for r in fit if float(r[0].get(key,0.0))<=.5]
            if not p or not q:continue
            a,_=best_intel_leaf(p,self._algs('INTELLIGENCE'));b,_=best_intel_leaf(q,self._algs('INTELLIGENCE'))
            m={'op':'IF_SIGNAL','signal':sk['signal'],'then':a,'else':b};v=sum(predict_intel_component(m,x)==y for x,y in validation)/len(validation);cand.append((v,-len(cj(m)),key,m))
        v,_,key,_=max(cand,key=lambda z:(z[0],z[1],z[2]));p=[r for r in revealed if float(r[0].get(key,0.0))>.5];q=[r for r in revealed if float(r[0].get(key,0.0))<=.5]
        a,_=best_intel_leaf(p,self._algs('INTELLIGENCE'));b,_=best_intel_leaf(q,self._algs('INTELLIGENCE'));m={'op':'IF_SIGNAL','signal':{'source':'INPUT','key':key,'threshold':.5},'then':a,'else':b};fresh=sum(predict_intel_component(m,x)==y for x,y in blind)/len(blind)
        return {'constructor_id':cons['constructor_id'],'binding':{var:key},'validation':v,'model':m,'fresh_blind':fresh}

    def synthesize_thinking_algorithm_component(self,fit,validation,revealed,blind):
        cons=self._constructor('EPISODE_CONTEXT',2);vars=signal_vars(cons['program_template']);keys=sorted(k for k in fit[0][0] if len({float(e[0].get(k,0.0)) for e in fit})>1)
        cand=[]
        for assignment in itertools.permutations(keys,len(vars)):
            bindings=dict(zip(vars,assignment));sk=fill_template(cons['program_template'],bindings);m=fit_thinking_skeleton(sk,fit,self._algs('THINKING'))
            if m is None:continue
            v=thinking_component_acc(m,validation);cand.append((v,-len(cj(m)),assignment,m))
        v,_,assignment,_=max(cand,key=lambda z:(z[0],z[1],z[2]));bindings=dict(zip(vars,assignment));sk=fill_template(cons['program_template'],bindings);m=fit_thinking_skeleton(sk,revealed,self._algs('THINKING'));fresh=thinking_component_acc(m,blind)
        return {'constructor_id':cons['constructor_id'],'binding':bindings,'validation':v,'model':m,'fresh_blind':fresh}

    def algorithm_genesis_snapshot(self):
        return {'enabled':bool(self.canonical_state.get('algorithm_component_genesis_enabled')),'constructors':[c['constructor_id'] for c in self.algorithm_constructor_registry()],'policy':self.canonical_state.get('algorithm_component_genesis_policy')}
    def unified_snapshot(self):
        s=super().unified_snapshot();s.update({'profile':self.PROFILE,'algorithm_component_genesis':self.algorithm_genesis_snapshot()});return s

__all__=['UnifiedYADOKernelV30RC5AlgorithmGenesis','fill_template','signal_vars']
