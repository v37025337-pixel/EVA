from __future__ import annotations
import hashlib, itertools, json
from yado_algorithm_component_runtime_native_v1 import (
    best_logic_leaf, best_intel_leaf, predict_logic_component, predict_intel_component,
    fit_thinking_skeleton, thinking_component_acc,
)

PROVENANCE={
 'origin':'BOUNDED_REDERIVATION_FROM_META_GRAMMAR_CONSUMER_CONTRACT_AND_DURABLE_OPERATOR_SCHEMA',
 'lost_original_recovered':False,
 'external_code_copied_verbatim':False,
 'scope':'RC6_META_GRAMMAR_PREDICATE_SYNTHESIS_RUNTIME',
}

def _gid(program):
    raw=json.dumps(program,sort_keys=True,separators=(',',':')).encode()
    return 'G_'+hashlib.sha256(raw).hexdigest()[:12]

def _predicate(program,features):
    if program['kind']=='BOOL_TABLE':
        a,b=program['signals']; key=f"{int(bool(features.get(a,False)))}{int(bool(features.get(b,False)))}"
        return bool(program['table'][key])
    return sum(w*float(features.get(k,0)) for w,k in zip(program['weights'],program['signals']))>program['threshold']

def _logic_acc(model,cases):
    return sum(predict_logic_component(model,x)==bool(y) for x,y in cases)/len(cases) if cases else 0.0

def _intel_acc(model,cases):
    return sum(predict_intel_component(model,x)==y for x,y in cases)/len(cases) if cases else 0.0

def synth_logic_predicate(fit,val,revealed,blind,algs):
    keys=sorted({k for x,_ in fit for k in x}); candidates=[]
    for a,b in itertools.combinations(keys,2):
        buckets={f'{int(i)}{int(j)}':[] for i in (False,True) for j in (False,True)}
        for x,y in fit:
            buckets[f'{int(bool(x.get(a,False)))}{int(bool(x.get(b,False)))}'].append(bool(y))
        table={k:(sum(v)>=len(v)/2 if v else False) for k,v in buckets.items()}
        p={'kind':'BOOL_TABLE','signals':[a,b],'table':table}
        left=[r for r in fit if _predicate(p,r[0])]; right=[r for r in fit if not _predicate(p,r[0])]
        if not left or not right: continue
        lmodel,_=best_logic_leaf(left,algs); rmodel,_=best_logic_leaf(right,algs)
        model={'op':'IF_PREDICATE','predicate_program':p,'then':lmodel,'else':rmodel}
        candidates.append((_logic_acc(model,val),a,b,p))
    if not candidates:return {'status':'WITHHOLD'}
    _,a,b,p=max(candidates,key=lambda z:(z[0],z[1],z[2]))
    left=[r for r in revealed if _predicate(p,r[0])]; right=[r for r in revealed if not _predicate(p,r[0])]
    lmodel,_=best_logic_leaf(left,algs); rmodel,_=best_logic_leaf(right,algs)
    model={'op':'IF_PREDICATE','predicate_program':p,'then':lmodel,'else':rmodel}
    return {'status':'SUPPORTED','grammar_extension_id':_gid(p),'predicate_program':p,'model':model,
            'validation':max(z[0] for z in candidates),'fresh_blind':_logic_acc(model,blind)}

def _linear_candidates(cases):
    keys=sorted({k for x,*_ in cases for k in (x if isinstance(x,dict) else {})})
    for a,b in itertools.combinations(keys,2):
        vals=[(float(x.get(a,0)),float(x.get(b,0))) for x,*_ in cases]
        for wa,wb in itertools.product((-1.0,1.0),repeat=2):
            scores=sorted(set(wa*u+wb*v for u,v in vals))
            for lo,hi in zip(scores,scores[1:]):
                yield {'kind':'LINEAR_THRESHOLD','signals':[a,b],'weights':[wa,wb],'threshold':(lo+hi)/2}

def synth_intel_predicate(fit,val,revealed,blind,algs):
    candidates=[]
    for p in _linear_candidates(fit):
        left=[r for r in fit if _predicate(p,r[0])]; right=[r for r in fit if not _predicate(p,r[0])]
        if not left or not right:continue
        lmodel,_=best_intel_leaf(left,algs); rmodel,_=best_intel_leaf(right,algs)
        model={'op':'IF_PREDICATE','predicate_program':p,'then':lmodel,'else':rmodel}
        candidates.append((_intel_acc(model,val),p))
    if not candidates:return {'status':'WITHHOLD'}
    validation,p=max(candidates,key=lambda z:z[0])
    left=[r for r in revealed if _predicate(p,r[0])]; right=[r for r in revealed if not _predicate(p,r[0])]
    lmodel,_=best_intel_leaf(left,algs); rmodel,_=best_intel_leaf(right,algs)
    model={'op':'IF_PREDICATE','predicate_program':p,'then':lmodel,'else':rmodel}
    return {'status':'SUPPORTED','grammar_extension_id':_gid(p),'predicate_program':p,'model':model,
            'validation':validation,'fresh_blind':_intel_acc(model,blind)}

def synth_thinking_predicate(fit,val,revealed,blind,algs):
    candidates=[]
    for p in _linear_candidates(fit):
        def lift(rows):return [(dict(e[0],__REC=float(_predicate(p,e[0]))),*e[1:]) for e in rows]
        skeleton={'op':'IF_SIGNAL','signal':{'source':'EPISODE_CONTEXT','key':'__REC','threshold':.5},
                  'then':{'op':'LEAF'},'else':{'op':'LEAF'}}
        fitted=fit_thinking_skeleton(skeleton,lift(fit),algs)
        if fitted is None:continue
        model={'op':'IF_PREDICATE','predicate_program':p,'then':fitted['then'],'else':fitted['else']}
        candidates.append((thinking_component_acc(model,val),p))
    if not candidates:return {'status':'WITHHOLD'}
    validation,p=max(candidates,key=lambda z:z[0])
    skeleton={'op':'IF_SIGNAL','signal':{'source':'EPISODE_CONTEXT','key':'__REC','threshold':.5},
              'then':{'op':'LEAF'},'else':{'op':'LEAF'}}
    lifted=[(dict(e[0],__REC=float(_predicate(p,e[0]))),*e[1:]) for e in revealed]
    fitted=fit_thinking_skeleton(skeleton,lifted,algs)
    if fitted is None:
        return {'status':'WITHHOLD','reason':'REVEALED_PARTITION_COLLAPSE'}
    model={'op':'IF_PREDICATE','predicate_program':p,'then':fitted['then'],'else':fitted['else']}
    return {'status':'SUPPORTED','grammar_extension_id':_gid(p),'predicate_program':p,'model':model,
            'validation':validation,'fresh_blind':thinking_component_acc(model,blind)}

__all__=['PROVENANCE','synth_logic_predicate','synth_thinking_predicate','synth_intel_predicate']
