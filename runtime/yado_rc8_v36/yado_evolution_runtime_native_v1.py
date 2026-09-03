"""Native bounded evolution runtime re-derived from active YADO contracts.

This module replaces the RC4 compatibility-recovery shim. It preserves the
bounded public contract while making provenance explicit: it is a new runtime,
not a recovered original developmental source.
"""
from __future__ import annotations
import itertools, time
from typing import Mapping
from yado_organ_runtime_native_v1 import synthesize_logic, score_bool, fit_tree, tree_acc, plan_with_edges

NATIVE_PROVENANCE={
    'status':'NATIVE_REDERIVED_RUNTIME',
    'source':'ACTIVE_CONTRACTS_PLUS_DIFFERENTIAL_VALIDATION',
    'scope':'RC4_EVOLUTION_RUNTIME',
    'lost_original_recovered':False,
    'external_code_copied_verbatim':False,
}

def bounded_enum(cases,max_depth=3,timeout_s=1.5):
    start=time.monotonic()
    model, meta=synthesize_logic(cases,max_depth=max_depth)
    out=dict(meta or {})
    out['elapsed_s']=time.monotonic()-start
    out['timeout_budget_s']=timeout_s
    return model,out

def fit_bool_tree(cases,max_depth=4):
    return fit_tree([(x,bool(y)) for x,y in cases],max_depth=max_depth)

def acc_logic_model(family,model,cases):
    if model is None:return 0.0
    if str(family)=='ENUM_BOOLEAN':return score_bool(model,cases)
    return tree_acc(model,[(x,bool(y)) for x,y in cases])

def _predict_plan_model(model,episode):
    if len(episode)==3:
        ctx,actions,expected=episode
        edges=model
        if isinstance(model,dict) and model.get('kind')=='CONTEXTUAL_PRECEDENCE':
            marker=model.get('marker')
            roles=[a.get('role') for a in actions]
            edges=model.get('present_edges' if marker in ctx or marker in roles else 'absent_edges',[])
        ids=plan_with_edges(actions,edges)
        by_id={str(a['id']):str(a['role']) for a in actions}
        return [by_id[i] for i in ids],list(expected)
    if len(episode)==2 and isinstance(episode[0],list):
        trace,expected=episode
        actions=[{'id':str(i),'role':r} for i,r in enumerate(trace)]
        ids=plan_with_edges(actions,model)
        by_id={str(a['id']):str(a['role']) for a in actions}
        return [by_id[i] for i in ids],list(expected)
    return [],[]

def plan_acc(model,cases):
    if not cases:return 0.0
    return sum(_predict_plan_model(model,e)[0]==_predict_plan_model(model,e)[1] for e in cases)/len(cases)

def fit_linear(cases):
    if not cases:return None
    keys=sorted({k for x,_ in cases for k in x})
    labels=sorted({y for _,y in cases},key=str)
    if len(labels)!=2:return None
    best=None
    for weights in itertools.product((-1.0,0.0,1.0),repeat=len(keys)):
        if not any(weights):continue
        vals=[sum(w*float(x.get(k,0.0)) for w,k in zip(weights,keys)) for x,_ in cases]
        unique=sorted(set(vals))
        thresholds=[(a+b)/2 for a,b in zip(unique,unique[1:])] or [0.0]
        for th in thresholds:
            for orient in (1,-1):
                preds=[labels[1] if orient*v>orient*th else labels[0] for v in vals]
                acc=sum(p==y for p,(_,y) in zip(preds,cases))/len(cases)
                cand=(acc,-sum(abs(w) for w in weights),tuple(weights),-abs(th),orient,th)
                model={'kind':'LINEAR_SCORE','features':keys,'weights':list(weights),'threshold':th,
                       'orientation':orient,'low_label':labels[0],'high_label':labels[1]}
                if best is None or cand>best[0]:best=(cand,model)
    return None if best is None else best[1]

def linear_predict(model,x:Mapping[str,float]):
    if not model:return None
    score=sum(float(w)*float(x.get(k,0.0)) for w,k in zip(model['weights'],model['features']))
    orient=int(model.get('orientation',1)); threshold=float(model['threshold'])
    return model['high_label'] if orient*score>orient*threshold else model['low_label']

def linear_acc(model,cases):
    if not model or not cases:return 0.0
    return sum(linear_predict(model,x)==y for x,y in cases)/len(cases)

__all__=['NATIVE_PROVENANCE','bounded_enum','fit_bool_tree','acc_logic_model','plan_acc','fit_linear','linear_acc','linear_predict']
