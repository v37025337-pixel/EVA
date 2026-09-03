from __future__ import annotations
from collections import Counter
from itertools import combinations
from typing import Any, Mapping, Sequence

NATIVE_PROVENANCE={
    'origin':'BOUNDED_REDERIVATION_FROM_ACTIVE_RC3_PLUS_CONSUMER_CONTRACTS_AND_SERIALIZED_MODEL_FORMATS',
    'lost_original_recovered':False,
    'external_code_copied_verbatim':False,
    'scope':'CROSS_LAYER_ORGAN_EVOLUTION_RUNTIME',
}

def _as_bool_label(value:Any)->bool:
    if isinstance(value,bool):return value
    if isinstance(value,(int,float)):return bool(value)
    return str(value).upper() in {'1','TRUE','ALLOW','PASS','ACCEPT','ACCEPT_DURABLE','USE_SOURCE','EXPERIMENT','SYNTHESIZE'}

def eval_bool(model,features:Mapping[str,Any])->bool:
    if model is None:return False
    if isinstance(model,bool):return model
    if isinstance(model,(int,float)):return bool(model)
    if isinstance(model,dict) and 'label' in model:return _as_bool_label(model['label'])
    if not isinstance(model,(list,tuple)) or not model:return False
    op=str(model[0]).upper()
    if op=='VAR':return bool(features.get(str(model[1]),False))
    if op=='TRUE':return True
    if op=='FALSE':return False
    if op=='NOT':return not eval_bool(model[1],features)
    if op=='AND':return eval_bool(model[1],features) and eval_bool(model[2],features)
    if op=='OR':return eval_bool(model[1],features) or eval_bool(model[2],features)
    if op=='XOR':return eval_bool(model[1],features) ^ eval_bool(model[2],features)
    return False

def score_bool(model,cases)->float:
    if not cases:return 0.0
    return sum(bool(eval_bool(model,x))==bool(y) for x,y in cases)/len(cases)

def synthesize_logic(train,max_depth=3):
    if not train:return None,{'candidates':0}
    keys=sorted({k for x,_ in train for k in x})
    initial=[['FALSE'],['TRUE']]+[['VAR',k] for k in keys]
    seen={}; candidate_count=0; active=[]
    def signature(model):return tuple(eval_bool(model,x) for x,_ in train)
    for model in initial:
        sig=signature(model);candidate_count+=1
        if sig not in seen:
            seen[sig]=model;active.append(model)
        if score_bool(model,train)==1.0:return model,{'candidates':candidate_count,'depth':0}
    all_models=list(active)
    for depth in range(1,int(max_depth)+1):
        newly=[]
        for a in list(all_models):
            model=['NOT',a];sig=signature(model);candidate_count+=1
            if sig not in seen:
                seen[sig]=model;newly.append(model)
                if score_bool(model,train)==1.0:return model,{'candidates':candidate_count,'depth':depth}
        pool=list(all_models)
        for a,b in combinations(pool,2):
            for op in ('AND','OR','XOR'):
                model=[op,a,b];sig=signature(model);candidate_count+=1
                if sig in seen:continue
                seen[sig]=model;newly.append(model)
                if score_bool(model,train)==1.0:return model,{'candidates':candidate_count,'depth':depth}
        all_models.extend(newly)
        if len(all_models)>4096:all_models=all_models[:4096]
    best=max(seen.values(),key=lambda m:score_bool(m,train)) if seen else None
    return best,{'candidates':candidate_count,'depth':max_depth,'exact':score_bool(best,train) if best else 0.0}

def learn_edges(successful_traces:Sequence[Sequence[str]],threshold=1.0,min_support=2):
    roles=sorted({str(role) for trace in successful_traces for role in trace}); result=[]
    for a,b in combinations(roles,2):
        support=ab=ba=0
        for trace in successful_traces:
            if a in trace and b in trace:
                support+=1
                if list(trace).index(a)<list(trace).index(b):ab+=1
                else:ba+=1
        if support<min_support:continue
        if ab/support>=threshold:result.append({'before':a,'after':b,'confidence':ab/support,'support':support})
        elif ba/support>=threshold:result.append({'before':b,'after':a,'confidence':ba/support,'support':support})
    return sorted(result,key=lambda e:(e['before'],e['after']))

def _toposort_roles(roles,edges):
    ordered=list(dict.fromkeys(map(str,roles)))
    adj={r:set() for r in ordered}; indegree={r:0 for r in ordered}
    for edge in edges or []:
        a=str(edge.get('before'));b=str(edge.get('after'))
        if a in adj and b in adj and b not in adj[a]:adj[a].add(b);indegree[b]+=1
    ready=sorted(r for r in ordered if indegree[r]==0);out=[]
    while ready:
        r=ready.pop(0);out.append(r)
        for n in sorted(adj[r]):
            indegree[n]-=1
            if indegree[n]==0:ready.append(n);ready.sort()
    if len(out)!=len(ordered):out.extend(r for r in ordered if r not in out)
    return out

def plan_with_edges(actions,edges):
    if isinstance(edges,dict) and edges.get('kind')=='CONTEXTUAL_PRECEDENCE':
        marker=edges.get('marker'); roles=[str(a.get('role')) for a in actions]
        edges=edges.get('present_edges' if marker in roles else 'absent_edges',[])
    role_order=_toposort_roles([a.get('role') for a in actions],edges)
    rank={role:i for i,role in enumerate(role_order)}
    return [str(a.get('id')) for a in sorted(actions,key=lambda a:(rank.get(str(a.get('role')),10**6),str(a.get('id'))))]

def _majority(labels):
    counts=Counter(labels)
    return sorted(counts.items(),key=lambda kv:(kv[1],str(kv[0])),reverse=True)[0][0]

def _thresholds(values):
    uniq=sorted(set(float(v) for v in values))
    return [] if len(uniq)<2 else [(a+b)/2 for a,b in zip(uniq,uniq[1:])]

def _gini(labels):
    if not labels:return 0.0
    counts=Counter(labels);n=len(labels)
    return 1-sum((count/n)**2 for count in counts.values())

def fit_tree(cases,max_depth=4):
    data=[(dict(x),y) for x,y in cases]
    def build(rows,depth):
        ys=[y for _,y in rows]
        if not rows:return {'label':False}
        if len(set(map(str,ys)))==1:return {'label':ys[0]}
        if depth>=max_depth:return {'label':_majority(ys)}
        keys=sorted({k for x,_ in rows for k in x});parent=_gini(ys);best=None
        for key in keys:
            vals=[]
            for x,_ in rows:
                raw=x.get(key,0)
                vals.append(float(bool(raw)) if isinstance(raw,bool) else float(raw if raw is not None else 0.0))
            thresholds=_thresholds(vals)
            if not thresholds and set(vals)<=set([0.0,1.0]):thresholds=[0.5]
            for threshold in thresholds:
                left=[r for r,v in zip(rows,vals) if v<=threshold];right=[r for r,v in zip(rows,vals) if v>threshold]
                if not left or not right:continue
                impurity=(len(left)*_gini([y for _,y in left])+len(right)*_gini([y for _,y in right]))/len(rows)
                candidate=(parent-impurity,-len(left)*len(right),key,-threshold,left,right,threshold)
                if best is None or candidate[:4]>best[:4]:best=candidate
        if best is None:return {'label':_majority(ys)}
        _,_,key,_,left,right,threshold=best
        return {'feature':key,'threshold':threshold,'left':build(left,depth+1),'right':build(right,depth+1)}
    return build(data,0)

def tree_predict(tree,features:Mapping[str,Any]):
    node=tree
    while isinstance(node,dict) and 'label' not in node:
        key=node.get('feature');threshold=float(node.get('threshold',0.5));value=features.get(key,0.0)
        try:value=float(value)
        except (TypeError,ValueError):value=1.0 if bool(value) else 0.0
        node=node.get('left') if value<=threshold else node.get('right')
    return node.get('label') if isinstance(node,dict) else node

def tree_acc(tree,cases)->float:
    if not cases:return 0.0
    return sum(tree_predict(tree,x)==y for x,y in cases)/len(cases)

__all__=['NATIVE_PROVENANCE','eval_bool','score_bool','synthesize_logic','learn_edges','plan_with_edges','fit_tree','tree_predict','tree_acc']
