from __future__ import annotations
import json
from pathlib import Path
from typing import Any,Mapping,Sequence,Tuple
from yado_core_v3_0_rc3_trained import UnifiedYADOKernelV30RC3Trained
from yado_evolution_runtime_native_v1 import (
    bounded_enum,fit_bool_tree,acc_logic_model,plan_acc,fit_linear,linear_acc
)
from yado_organ_runtime_native_v1 import score_bool,learn_edges,plan_with_edges,fit_tree,tree_acc

ROOT=Path(__file__).resolve().parent
DEFAULT_STATE=ROOT/'yado_canonical_state_v3_rc4_meta_autoevolution.json'

class UnifiedYADOKernelV30RC4MetaAutoEvolution(UnifiedYADOKernelV30RC3Trained):
    PROFILE='YADO_V3_0_RC4_BOUNDED_EVOLUTION_OF_EVOLUTION_LOCAL'
    SCHEMA_VERSION=17
    def __init__(self,db_path='yado_v30_rc4_meta.db',state_path:str|None=None):
        super().__init__(db_path=db_path,state_path=state_path or str(DEFAULT_STATE))
    def organ_evolution_algorithm_bank(self):
        return dict(self.canonical_state.get('organ_evolution_algorithm_bank') or {})
    def _algs(self,organ):return list(self.organ_evolution_algorithm_bank().get(organ,[]))

    def meta_evolve_logic(self,fit,validation,revealed_train,blind):
        candidates=[]
        for a in self._algs('LOGIC'):
            fam=a['family']
            if fam=='ENUM_BOOLEAN':
                model,meta=bounded_enum(fit,int(a.get('max_depth',3)),float(a.get('timeout_s',1.5)))
                val=0.0 if model is None else score_bool(model,validation)
            elif fam=='BOOL_DECISION_TREE':
                model=fit_bool_tree(fit,int(a['max_depth']));meta={};val=acc_logic_model(fam,model,validation)
            else:continue
            candidates.append({'algorithm':a,'model':model,'validation':val,'meta':meta})
        if not candidates:raise RuntimeError('no LOGIC meta algorithms')
        sel=max(candidates,key=lambda z:(z['validation'],z['algorithm']['family']=='ENUM_BOOLEAN',-(z['algorithm'].get('max_depth') or 99)))
        a=sel['algorithm'];fam=a['family']
        if fam=='ENUM_BOOLEAN':model,_=bounded_enum(revealed_train,int(a.get('max_depth',3)),float(a.get('refit_timeout_s',4.0)))
        else:model=fit_bool_tree(revealed_train,int(a['max_depth']))
        fresh=0.0 if model is None else acc_logic_model(fam,model,blind)
        return {'organ':'LOGIC','selected_algorithm':a,'validation':sel['validation'],'model':model,'fresh_blind':fresh}

    def meta_evolve_thinking(self,fit_traces,validation_blind,revealed_traces,blind):
        candidates=[]
        roles=sorted({r for t in fit_traces for r in t})
        for a in self._algs('THINKING'):
            fam=a['family'];threshold=float(a.get('threshold',.5))
            if fam=='GLOBAL_PRECEDENCE':model=learn_edges(fit_traces,threshold,int(a.get('min_support',2)))
            elif fam=='CONTEXTUAL_PRECEDENCE':
                for marker in roles:
                    p=[t for t in fit_traces if marker in t];q=[t for t in fit_traces if marker not in t]
                    if len(p)<2 or len(q)<2:continue
                    m={'kind':'CONTEXTUAL_PRECEDENCE','marker':marker,'present_edges':learn_edges(p,threshold,2),'absent_edges':learn_edges(q,threshold,2)}
                    candidates.append({'algorithm':dict(a,marker=marker),'model':m,'validation':plan_acc(m,validation_blind)})
                continue
            else:continue
            candidates.append({'algorithm':a,'model':model,'validation':plan_acc(model,validation_blind)})
        if not candidates:raise RuntimeError('no THINKING meta algorithms')
        sel=max(candidates,key=lambda z:(z['validation'],z['algorithm']['family']=='GLOBAL_PRECEDENCE',-len(json.dumps(z['model'],sort_keys=True))))
        a=sel['algorithm'];th=float(a.get('threshold',.5))
        if a['family']=='GLOBAL_PRECEDENCE':model=learn_edges(revealed_traces,th,int(a.get('min_support',2)))
        else:
            marker=a['marker'];p=[t for t in revealed_traces if marker in t];q=[t for t in revealed_traces if marker not in t]
            model={'kind':'CONTEXTUAL_PRECEDENCE','marker':marker,'present_edges':learn_edges(p,th,2),'absent_edges':learn_edges(q,th,2)}
        return {'organ':'THINKING','selected_algorithm':a,'validation':sel['validation'],'model':model,'fresh_blind':plan_acc(model,blind)}

    def meta_evolve_intelligence(self,fit,validation,revealed_train,blind):
        candidates=[]
        for a in self._algs('INTELLIGENCE'):
            fam=a['family']
            if fam=='CART_AXIS':model=fit_tree(fit,int(a['max_depth']));val=tree_acc(model,validation)
            elif fam=='LINEAR_SCORE_SEARCH':
                model=fit_linear(fit);val=0.0 if model is None else linear_acc(model,validation)
            else:continue
            candidates.append({'algorithm':a,'model':model,'validation':val})
        if not candidates:raise RuntimeError('no INTELLIGENCE meta algorithms')
        sel=max(candidates,key=lambda z:(z['validation'],z['algorithm']['family']=='CART_AXIS',-(z['algorithm'].get('max_depth') or 99)))
        a=sel['algorithm']
        if a['family']=='CART_AXIS':model=fit_tree(revealed_train,int(a['max_depth']));fresh=tree_acc(model,blind)
        else:model=fit_linear(revealed_train);fresh=0.0 if model is None else linear_acc(model,blind)
        return {'organ':'INTELLIGENCE','selected_algorithm':a,'validation':sel['validation'],'model':model,'fresh_blind':fresh}

    def meta_evolution_snapshot(self):
        b=self.organ_evolution_algorithm_bank()
        return {'profile':self.PROFILE,'enabled':bool(self.canonical_state.get('evolution_of_evolution_enabled')),
                'algorithm_counts':{k:len(v) for k,v in b.items()},'selection_policy':self.canonical_state.get('evolution_of_evolution_policy')}
    def unified_snapshot(self):
        s=super().unified_snapshot();s.update({'profile':self.PROFILE,'evolution_of_evolution':self.meta_evolution_snapshot()});return s

__all__=['UnifiedYADOKernelV30RC4MetaAutoEvolution']
