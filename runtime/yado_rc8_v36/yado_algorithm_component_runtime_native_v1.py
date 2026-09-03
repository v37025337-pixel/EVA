from __future__ import annotations
import json
from typing import Any
from yado_evolution_runtime_native_v1 import bounded_enum, fit_bool_tree, acc_logic_model, fit_linear, linear_acc, linear_predict
from yado_organ_runtime_native_v1 import fit_tree, tree_acc, tree_predict, learn_edges, plan_with_edges, eval_bool

NATIVE_PROVENANCE={
    'origin':'BOUNDED_REDERIVATION_FROM_ACTIVE_RC5_CONSUMER_CONTRACTS_AND_DURABLE_MODEL_FORMATS',
    'lost_original_recovered':False,
    'external_code_copied_verbatim':False,
    'scope':'RC5_ALGORITHM_COMPONENT_RUNTIME',
}

def cj(value:Any)->str:
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False)

def strip_component(value:Any):
    if isinstance(value,dict):
        return {k:strip_component(v) for k,v in value.items() if k not in {'model','algorithm'}}
    if isinstance(value,list):
        return [strip_component(v) for v in value]
    return value

def _logic_score(family, model, cases):
    return 0.0 if model is None else acc_logic_model(family,model,cases)

def best_logic_leaf(cases,algs):
    ranked=[]
    for spec in algs:
        family=spec.get('family')
        depth=int(spec.get('max_depth',99))
        meta={}
        if family=='ENUM_BOOLEAN':
            model,meta=bounded_enum(cases,int(spec.get('max_depth',3)),float(spec.get('refit_timeout_s',4.0)))
        elif family=='BOOL_DECISION_TREE':
            model=fit_bool_tree(cases,int(spec.get('max_depth',4)))
        else:
            continue
        ranked.append((_logic_score(family,model,cases),-depth,family=='ENUM_BOOLEAN',dict(spec),model,meta))
    if not ranked:
        return None,{'score':0.0}
    score,_,_,spec,model,meta=max(ranked,key=lambda z:(z[0],z[1],z[2]))
    return {'op':'LEAF','algorithm':spec,'model':model},{'score':score,'meta':meta}

def _predicate(program,features):
    if not isinstance(program,dict):
        return False
    kind=program.get('kind')
    if kind=='BOOL_TABLE':
        signals=program.get('signals') or []
        if len(signals)<2:return False
        a=bool(features.get(signals[0],False)); b=bool(features.get(signals[1],False))
        return bool((program.get('table') or {}).get(f'{int(a)}{int(b)}',False))
    if kind=='LINEAR_THRESHOLD':
        signals=program.get('signals') or []; weights=program.get('weights') or []
        if len(signals)!=len(weights):return False
        try: score=sum(float(w)*float(features.get(k,0)) for w,k in zip(weights,signals))
        except (TypeError,ValueError):return False
        return score>float(program.get('threshold',0.0))
    return False

def predict_logic_component(model,features):
    if not isinstance(model,dict):return False
    op=model.get('op')
    if op=='LEAF':
        family=(model.get('algorithm') or {}).get('family')
        if family=='ENUM_BOOLEAN':return bool(eval_bool(model.get('model'),features))
        return bool(tree_predict(model.get('model'),features))
    if op=='IF_SIGNAL':
        s=model.get('signal') or {}; key=s.get('key'); th=float(s.get('threshold',.5))
        try:v=float(features.get(key,0))
        except (TypeError,ValueError):v=0.0
        return predict_logic_component(model.get('then') if v>th else model.get('else'),features)
    if op=='IF_PREDICATE':
        return predict_logic_component(model.get('then') if _predicate(model.get('predicate_program'),features) else model.get('else'),features)
    return False

def best_intel_leaf(cases,algs):
    ranked=[]
    for spec in algs:
        family=spec.get('family'); depth=int(spec.get('max_depth',99))
        if family=='CART_AXIS':
            model=fit_tree(cases,int(spec.get('max_depth',4))); score=tree_acc(model,cases)
        elif family=='LINEAR_SCORE_SEARCH':
            model=fit_linear(cases); score=linear_acc(model,cases) if model else 0.0
        else:continue
        ranked.append((score,-depth,family=='CART_AXIS',dict(spec),model))
    if not ranked:return None,{'score':0.0}
    score,_,_,spec,model=max(ranked,key=lambda z:(z[0],z[1],z[2]))
    return {'op':'LEAF','algorithm':spec,'model':model},{'score':score}

def predict_intel_component(model,features):
    if not isinstance(model,dict):return None
    op=model.get('op')
    if op=='LEAF':
        family=(model.get('algorithm') or {}).get('family')
        return linear_predict(model.get('model'),features) if family=='LINEAR_SCORE_SEARCH' else tree_predict(model.get('model'),features)
    if op=='IF_SIGNAL':
        s=model.get('signal') or {}; key=s.get('key'); th=float(s.get('threshold',.5))
        try:v=float(features.get(key,0))
        except (TypeError,ValueError):v=0.0
        return predict_intel_component(model.get('then') if v>th else model.get('else'),features)
    if op=='IF_PREDICATE':
        return predict_intel_component(model.get('then') if _predicate(model.get('predicate_program'),features) else model.get('else'),features)
    return None

def _thinking_leaf_fit(episodes,algs):
    traces=[]
    for episode in episodes:
        if len(episode)<2 or not isinstance(episode[1],list):continue
        seq=episode[1]
        if seq and isinstance(seq[0],dict):traces.append([str(a.get('role')) for a in seq])
        else:traces.append([str(v) for v in seq])
    best=None
    for spec in algs:
        if spec.get('family')!='GLOBAL_PRECEDENCE':continue
        edges=learn_edges(traces,float(spec.get('threshold',.5)),int(spec.get('min_support',2)))
        leaf={'op':'LEAF','algorithm':dict(spec),'model':edges}
        acc=thinking_component_acc(leaf,episodes)
        candidate=(acc,-len(edges),cj(leaf),leaf)
        if best is None or candidate[:3]>best[:3]:best=candidate
    return best[3] if best else {'op':'LEAF','algorithm':{'family':'GLOBAL_PRECEDENCE'},'model':[]}

def fit_thinking_skeleton(skeleton,episodes,algs):
    def rec(node,rows):
        if not rows or node.get('op')=='LEAF':return _thinking_leaf_fit(rows,algs)
        if node.get('op')!='IF_SIGNAL':return None
        signal=node.get('signal') or {}; key=signal.get('key'); th=float(signal.get('threshold',.5))
        left=[]; right=[]
        for e in rows:
            ctx=e[0] if e and isinstance(e[0],dict) else {}
            try:v=float(ctx.get(key,0))
            except (TypeError,ValueError):v=0.0
            (left if v>th else right).append(e)
        if not left or not right:return None
        return {'op':'IF_SIGNAL','signal':dict(signal),'then':rec(node['then'],left),'else':rec(node['else'],right)}
    return rec(skeleton,list(episodes))

def _thinking_predict(model,episode):
    ctx=episode[0] if episode and isinstance(episode[0],dict) else {}
    if model.get('op')=='IF_SIGNAL':
        s=model.get('signal') or {}; key=s.get('key'); th=float(s.get('threshold',.5))
        try:v=float(ctx.get(key,0))
        except (TypeError,ValueError):v=0.0
        return _thinking_predict(model.get('then') if v>th else model.get('else'),episode)
    if model.get('op')=='IF_PREDICATE':
        return _thinking_predict(model.get('then') if _predicate(model.get('predicate_program'),ctx) else model.get('else'),episode)
    if len(episode)<3:return [],[]
    inp=episode[1]; expected=list(episode[2])
    if inp and isinstance(inp[0],dict):
        actions=inp
    else:
        actions=[{'id':str(i),'role':role} for i,role in enumerate(inp)]
    ids=plan_with_edges(actions,model.get('model',[])); roles={str(a['id']):str(a['role']) for a in actions}
    return [roles[i] for i in ids],expected

def thinking_component_acc(model,cases):
    if not cases:return 0.0
    correct=0
    for episode in cases:
        pred,expected=_thinking_predict(model,episode); correct+=pred==expected
    return correct/len(cases)

__all__=['NATIVE_PROVENANCE','best_logic_leaf','best_intel_leaf','fit_thinking_skeleton','thinking_component_acc','predict_logic_component','predict_intel_component','strip_component','cj']
