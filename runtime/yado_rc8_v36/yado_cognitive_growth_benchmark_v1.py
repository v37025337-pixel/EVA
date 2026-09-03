from __future__ import annotations
import argparse, json, random, statistics
from itertools import product
from pathlib import Path

from yado_organ_runtime_native_v1 import synthesize_logic, score_bool, fit_tree, tree_acc, learn_edges, plan_with_edges
from yado_evolution_runtime_native_v1 import fit_linear, linear_acc
from yado_cognitive_growth_runtime_v1 import (
    synthesize_logic_minimal, logic_accuracy,
    learn_multicontext_precedence, planning_accuracy,
    select_knn_k, strategy_accuracy, select_centroid_features, fit_centroid_strategy, centroid_accuracy,
)

VARS=['a','b','c','d']


def eval_expr(e,x):
    op=e[0]
    if op=='VAR': return bool(x[e[1]])
    if op=='NOT': return not eval_expr(e[1],x)
    if op=='AND': return eval_expr(e[1],x) and eval_expr(e[2],x)
    if op=='OR': return eval_expr(e[1],x) or eval_expr(e[2],x)
    if op=='XOR': return eval_expr(e[1],x) ^ eval_expr(e[2],x)
    raise ValueError(op)


def make_expr(rng):
    # Deliberately beyond the old shallow-enumerator sweet spot, but still compact.
    v=rng.sample(VARS,4)
    templates=[
      ['XOR',['XOR',['VAR',v[0]],['VAR',v[1]]],['XOR',['VAR',v[2]],['VAR',v[3]]]],
      ['OR',['AND',['VAR',v[0]],['NOT',['VAR',v[1]]]],['XOR',['VAR',v[2]],['VAR',v[3]]]],
      ['XOR',['AND',['VAR',v[0]],['VAR',v[1]]],['OR',['VAR',v[2]],['NOT',['VAR',v[3]]]]],
      ['AND',['OR',['VAR',v[0]],['XOR',['VAR',v[1]],['VAR',v[2]]]],['NOT',['VAR',v[3]]]],
      ['OR',['XOR',['VAR',v[0]],['VAR',v[1]]],['AND',['NOT',['VAR',v[2]]],['VAR',v[3]]]],
    ]
    return rng.choice(templates)


def all_points():
    return [dict(zip(VARS,bits)) for bits in product([False,True],repeat=4)]


def logic_task(rng):
    expr=make_expr(rng); pts=all_points(); rng.shuffle(pts)
    cases=[(x,eval_expr(expr,x)) for x in pts]
    return expr,cases[:8],cases[8:12],cases[:12],cases[12:]


def baseline_logic(fit,val,revealed,blind):
    candidates=[]
    m,_=synthesize_logic(fit,max_depth=3); candidates.append(('ENUM_BOOLEAN',m,score_bool(m,val) if m else 0.0))
    for d in range(2,9):
        t=fit_tree([(x,bool(y)) for x,y in fit],max_depth=d)
        candidates.append((f'TREE_{d}',t,tree_acc(t,[(x,bool(y)) for x,y in val])))
    fam,_,_=max(candidates,key=lambda z:(z[2], z[0]=='ENUM_BOOLEAN', z[0]))
    if fam=='ENUM_BOOLEAN':
        m,_=synthesize_logic(revealed,max_depth=3); return score_bool(m,blind) if m else 0.0,fam
    d=int(fam.split('_')[1]);m=fit_tree([(x,bool(y)) for x,y in revealed],max_depth=d)
    return tree_acc(m,[(x,bool(y)) for x,y in blind]),fam


def candidate_logic(fit,val,revealed,blind):
    # Cross-validated family admission over the full revealed set. This avoids
    # promoting a new representation on a single lucky validation partition.
    families=[('ENUM_BOOLEAN',None)]+[(f'TREE_{d}',d) for d in range(2,9)]+[('MINIMAL_SEMANTIC_DP',None)]
    n=len(revealed); folds=[list(range(i,n,3)) for i in range(3)]
    scores={name:[] for name,_ in families}
    for test_idx in folds:
        test_set=[revealed[i] for i in test_idx]; train_set=[revealed[i] for i in range(n) if i not in test_idx]
        for name,param in families:
            if name=='ENUM_BOOLEAN':
                m,_=synthesize_logic(train_set,max_depth=3); a=score_bool(m,test_set) if m else 0.0
            elif name=='MINIMAL_SEMANTIC_DP':
                m,_=synthesize_logic_minimal(train_set,max_nodes=11,max_signatures=65536); a=logic_accuracy(m,test_set)
            else:
                m=fit_tree([(x,bool(y)) for x,y in train_set],max_depth=param); a=tree_acc(m,[(x,bool(y)) for x,y in test_set])
            scores[name].append(a)
    avgs={name:sum(vals)/len(vals) for name,vals in scores.items()}
    # Existing families win exact ties; new family must show a real CV edge.
    old_names=[name for name,_ in families if name!='MINIMAL_SEMANTIC_DP']
    best_old=max(old_names,key=lambda name:(avgs[name], name=='ENUM_BOOLEAN', name))
    chosen='MINIMAL_SEMANTIC_DP' if avgs['MINIMAL_SEMANTIC_DP']>avgs[best_old] else best_old
    if chosen=='MINIMAL_SEMANTIC_DP':
        m,meta=synthesize_logic_minimal(revealed,max_nodes=11,max_signatures=65536)
        return logic_accuracy(m,blind),chosen,dict(meta,cv=avgs[chosen],old_cv=avgs[best_old])
    if chosen=='ENUM_BOOLEAN':
        m,_=synthesize_logic(revealed,max_depth=3); return (score_bool(m,blind) if m else 0.0),chosen,{'cv':avgs[chosen]}
    d=int(chosen.split('_')[1]);m=fit_tree([(x,bool(y)) for x,y in revealed],max_depth=d)
    return tree_acc(m,[(x,bool(y)) for x,y in blind]),chosen,{'cv':avgs[chosen],'depth':d}


def roles_for_context(ctx):
    # Same roles, different correct precedence under two context bits.
    # 00: OBSERVE -> MODEL -> TEST -> ACT
    # 10: MODEL -> OBSERVE -> TEST -> ACT
    # 01: OBSERVE -> TEST -> MODEL -> ACT
    # 11: TEST -> MODEL -> OBSERVE -> ACT
    key=(bool(ctx['urgent']),bool(ctx['uncertain']))
    return {
      (False,False):['OBSERVE','MODEL','TEST','ACT'],
      (True,False):['MODEL','OBSERVE','TEST','ACT'],
      (False,True):['OBSERVE','TEST','MODEL','ACT'],
      (True,True):['TEST','MODEL','OBSERVE','ACT'],
    }[key]


def thinking_data(rng,n):
    out=[]
    for i in range(n):
        ctx={'urgent':bool(rng.getrandbits(1)),'uncertain':bool(rng.getrandbits(1))}
        expected=roles_for_context(ctx)
        actions=[{'id':f'a{i}_{j}_{rng.randrange(10**6)}','role':r} for j,r in enumerate(rng.sample(expected,len(expected)))]
        out.append((ctx,actions,expected))
    return out


def baseline_thinking(train,blind):
    # Old global precedence; the old single-marker contextual family has no external-context key learner.
    traces=[expected for _,_,expected in train]
    best=None
    for th in (0.5,0.6,0.67,0.75,0.8,1.0):
        m=learn_edges(traces,threshold=th,min_support=2)
        def acc(data):
            ok=0
            for _,actions,expected in data:
                ids=plan_with_edges(actions,m); by={a['id']:a['role'] for a in actions}
                ok += [by[i] for i in ids]==expected
            return ok/len(data)
        a=acc(train); cand=(a,-len(m),th,m)
        if best is None or cand[:3]>best[:3]: best=cand
    m=best[3]
    ok=0
    for _,actions,expected in blind:
        ids=plan_with_edges(actions,m);by={a['id']:a['role'] for a in actions};ok += [by[i] for i in ids]==expected
    return ok/len(blind)


def candidate_thinking(train,validation,revealed,blind):
    trials=[]
    tr=[(ctx,expected) for ctx,_,expected in train]
    for th in (0.5,0.6,0.67,0.75,0.8,1.0):
        m=learn_multicontext_precedence(tr,threshold=th,min_support=2,max_context_keys=2)
        a=planning_accuracy(m,validation);trials.append((a,-len(json.dumps(m,sort_keys=True)),th))
    _,_,th=max(trials)
    m=learn_multicontext_precedence([(ctx,expected) for ctx,_,expected in revealed],threshold=th,min_support=2,max_context_keys=2)
    return planning_accuracy(m,blind),th,m


def intelligence_episode(rng, centers):
    label=rng.randrange(len(centers)); cx,cy=centers[label]
    # clustered nonlinear strategy landscape with irrelevant dimensions
    x={
      'signal_x':rng.gauss(cx,0.55),
      'signal_y':rng.gauss(cy,0.55),
      'noise_a':rng.uniform(-4,4),
      'noise_b':rng.uniform(-4,4),
      'noise_c':rng.uniform(-4,4),
    }
    return x,f'STRATEGY_{label}'


def intelligence_data(rng,n):
    centers=[(-2.2,-2.2),(-2.2,2.2),(2.2,-2.2),(2.2,2.2),(0.0,0.0),(0.0,3.8)]
    return [intelligence_episode(rng,centers) for _ in range(n)]


def baseline_intelligence(fit,val,revealed,blind):
    cands=[]
    for d in range(1,8):
        m=fit_tree(fit,max_depth=d);cands.append((tree_acc(m,val),-d,'TREE',d))
    lin=fit_linear(fit)
    if lin is not None:cands.append((linear_acc(lin,val),-99,'LINEAR',None))
    _,_,fam,param=max(cands)
    if fam=='TREE':m=fit_tree(revealed,max_depth=param);return tree_acc(m,blind),fam,param
    m=fit_linear(revealed);return linear_acc(m,blind),fam,param


def candidate_intelligence(fit,val,revealed,blind):
    # Add two generic non-axis candidates to the existing CART/linear portfolio.
    base_val,base_fam,base_param=baseline_intelligence(fit,val,fit,val)
    knn,km=select_knn_k(fit,val,(1,3,5,7,9))
    cen,cm=select_centroid_features(fit,val)
    choices=[(base_val,0,'BASE',{'family':base_fam,'param':base_param}),
             (km['validation'],-1,'KNN',km),(cm['validation'],-2,'CENTROID',cm)]
    _,_,chosen,meta=max(choices,key=lambda z:(z[0],z[1]))
    if chosen=='CENTROID':
        m=fit_centroid_strategy(revealed,meta['selected_features'])
        return centroid_accuracy(m,blind),'CENTROID_STRATEGY',meta
    if chosen=='KNN':
        fitm=fit_knn_strategy(revealed,meta['selected_k'])
        return strategy_accuracy(fitm,blind),'KNN_STRATEGY',meta
    b,f,p=baseline_intelligence(fit,val,revealed,blind);return b,f,{'param':p}


def run(seed:int,logic_tasks:int=20,thinking_cases:int=120,intel_cases:int=360):
    rng=random.Random(seed)
    lb=[];lc=[];lfams=[];lcands=[]
    for _ in range(logic_tasks):
        _,fit,val,revealed,blind=logic_task(rng)
        b,f=baseline_logic(fit,val,revealed,blind); c,cf,_=candidate_logic(fit,val,revealed,blind)
        lb.append(b);lc.append(c);lfams.append(f);lcands.append(cf)
    think=thinking_data(rng,thinking_cases)
    split=int(thinking_cases*.55);split2=int(thinking_cases*.75)
    tfit=think[:split];tval=think[split:split2];tblind=think[split2:]
    tb=baseline_thinking(tfit,tblind);tc,th,_=candidate_thinking(tfit,tval,think[:split2],tblind)
    intel=intelligence_data(rng,intel_cases)
    a=int(intel_cases*.5);b=int(intel_cases*.7)
    ifit,ival,irev,iblind=intel[:a],intel[a:b],intel[:b],intel[b:]
    ib,ifam,ip=baseline_intelligence(ifit,ival,irev,iblind);ic,icfam,im=candidate_intelligence(ifit,ival,irev,iblind)
    return {
      'seed':seed,
      'logic':{'baseline_mean':statistics.mean(lb),'candidate_mean':statistics.mean(lc),'baseline_per_task':lb,'candidate_per_task':lc,'baseline_families':lfams,'candidate_families':lcands},
      'thinking':{'baseline':tb,'candidate':tc,'selected_threshold':th,'blind_cases':len(tblind)},
      'intelligence':{'baseline':ib,'candidate':ic,'baseline_family':ifam,'baseline_param':ip,'candidate_family':icfam,'candidate_meta':im,'blind_cases':len(iblind)},
    }


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--seed',type=int,required=True);ap.add_argument('--out',required=True);ap.add_argument('--logic-tasks',type=int,default=20);args=ap.parse_args()
    r=run(args.seed,args.logic_tasks)
    Path(args.out).write_text(json.dumps(r,indent=2,sort_keys=True),encoding='utf-8')
    print(json.dumps({
      'seed':r['seed'],
      'logic':[r['logic']['baseline_mean'],r['logic']['candidate_mean']],
      'thinking':[r['thinking']['baseline'],r['thinking']['candidate']],
      'intelligence':[r['intelligence']['baseline'],r['intelligence']['candidate']],
    },sort_keys=True))

if __name__=='__main__': main()
