from __future__ import annotations
import json, random, time, multiprocessing as mp, statistics
from itertools import product
from pathlib import Path

from yado_organ_runtime_native_v1 import synthesize_logic, score_bool, learn_edges, plan_with_edges, fit_tree, tree_acc
from yado_evolution_runtime_native_v1 import fit_linear, linear_acc
from yado_cognitive_growth_runtime_v1 import (
    synthesize_logic_exact_table, synthesize_logic_bitset, logic_accuracy,
    learn_multicontext_precedence, planning_accuracy,
    select_centroid_features, fit_centroid_strategy, centroid_accuracy,
)

SEED=8808291441
OUT=Path('yado_cognitive_growth_fresh_holdout_v1_report.json')


def eval_expr(e,x):
    op=e[0]
    if op=='VAR': return bool(x[e[1]])
    if op=='NOT': return not eval_expr(e[1],x)
    if op=='AND': return eval_expr(e[1],x) and eval_expr(e[2],x)
    if op=='OR': return eval_expr(e[1],x) or eval_expr(e[2],x)
    if op=='XOR': return eval_expr(e[1],x) ^ eval_expr(e[2],x)
    raise ValueError(op)


def fresh_logic_expr(rng):
    v=rng.sample(list('abcdef'),6)
    templates=[
      ['XOR',['XOR',['VAR',v[0]],['VAR',v[1]]],['XOR',['XOR',['VAR',v[2]],['VAR',v[3]]],['XOR',['VAR',v[4]],['VAR',v[5]]]]],
      ['XOR',['AND',['VAR',v[0]],['VAR',v[1]]],['XOR',['OR',['VAR',v[2]],['VAR',v[3]]],['AND',['VAR',v[4]],['NOT',['VAR',v[5]]]]]],
      ['OR',['XOR',['VAR',v[0]],['AND',['VAR',v[1]],['VAR',v[2]]]],['XOR',['VAR',v[3]],['AND',['NOT',['VAR',v[4]]],['VAR',v[5]]]]],
    ]
    return rng.choice(templates)


def old_logic_worker(cases,q):
    t=time.perf_counter();m,meta=synthesize_logic(cases,max_depth=3);q.put({'elapsed_s':time.perf_counter()-t,'accuracy':score_bool(m,cases) if m else 0.0,'meta':meta})


def logic_holdout(rng):
    expr=fresh_logic_expr(rng)
    cases=[]
    for bits in product([False,True],repeat=6):
        x=dict(zip('abcdef',bits));cases.append((x,eval_expr(expr,x)))
    ctx=mp.get_context('fork');q=ctx.Queue();p=ctx.Process(target=old_logic_worker,args=(cases,q));p.start();p.join(8.0)
    if p.is_alive():
        p.terminate();p.join();old={'status':'TIMEOUT_8S','elapsed_s':8.0,'accuracy':None}
    else:
        old={'status':'COMPLETED',**q.get()}
    t=time.perf_counter();m,meta=synthesize_logic_bitset(cases,max_nodes=17,max_signatures=524288);acc=logic_accuracy(m,cases)
    if acc<1.0:
        em,emeta=synthesize_logic_exact_table(cases,max_vars=10)
        if em is not None:
            m,meta,acc=em,dict(emeta,fallback_from=meta),logic_accuracy(em,cases)
    elapsed=time.perf_counter()-t
    new={'status':'COMPLETED','elapsed_s':elapsed,'accuracy':acc,'meta':meta}
    pass_logic = new['accuracy']==1.0 and (old['status']=='TIMEOUT_8S' or (old.get('accuracy')==1.0 and new['elapsed_s'] < old['elapsed_s']))
    return {'expression':expr,'cases':len(cases),'baseline':old,'candidate':new,'pass':pass_logic}


def order_for(ctx):
    u=bool(ctx['urgent']);w=bool(ctx['uncertain'])
    return {(False,False):['OBSERVE','MODEL','TEST','ACT'],(True,False):['MODEL','OBSERVE','TEST','ACT'],(False,True):['OBSERVE','TEST','MODEL','ACT'],(True,True):['TEST','MODEL','OBSERVE','ACT']}[(u,w)]


def thinking_holdout(rng):
    episodes=[]
    for i in range(160):
        ctx={'urgent':bool(rng.getrandbits(1)),'uncertain':bool(rng.getrandbits(1))}
        expected=order_for(ctx);roles=list(expected);rng.shuffle(roles)
        actions=[{'id':f'fresh-{i}-{j}-{rng.randrange(10**8)}','role':r} for j,r in enumerate(roles)]
        episodes.append((ctx,actions,expected))
    train=episodes[:112];blind=episodes[112:]
    traces=[e[2] for e in train]
    old_trials=[]
    for th in (.5,.6,.67,.75,.8,1.0):
        m=learn_edges(traces,threshold=th,min_support=2)
        ok=0
        for _,actions,expected in train:
            ids=plan_with_edges(actions,m);by={a['id']:a['role'] for a in actions};ok += [by[i] for i in ids]==expected
        old_trials.append((ok/len(train),-len(m),th,m))
    oldm=max(old_trials,key=lambda z:z[:3])[3]
    old_ok=0
    for _,actions,expected in blind:
        ids=plan_with_edges(actions,oldm);by={a['id']:a['role'] for a in actions};old_ok += [by[i] for i in ids]==expected
    old=old_ok/len(blind)
    newm=learn_multicontext_precedence([(ctx,expected) for ctx,_,expected in train],threshold=.75,min_support=2,max_context_keys=2)
    new=planning_accuracy(newm,blind)
    return {'train_cases':len(train),'blind_cases':len(blind),'baseline':old,'candidate':new,'pass':new>=.95 and new>old}


def intel_data(rng,n=240):
    centers=[(-2.2,-2.2),(-2.2,2.2),(2.2,-2.2),(2.2,2.2),(0,0),(0,3.8)]
    out=[]
    for _ in range(n):
        label=rng.randrange(len(centers));cx,cy=centers[label]
        x={'signal_x':rng.gauss(cx,.55),'signal_y':rng.gauss(cy,.55),'noise_a':rng.uniform(-4,4),'noise_b':rng.uniform(-4,4),'noise_c':rng.uniform(-4,4)}
        out.append((x,f'STRATEGY_{label}'))
    return out


def baseline_intel(fit,val,revealed,blind):
    trials=[]
    for d in range(1,8):
        m=fit_tree(fit,max_depth=d);trials.append((tree_acc(m,val),-d,'TREE',d))
    lin=fit_linear(fit)
    if lin is not None: trials.append((linear_acc(lin,val),-99,'LINEAR',None))
    _,_,fam,param=max(trials)
    if fam=='TREE': return tree_acc(fit_tree(revealed,max_depth=param),blind),fam,param
    return linear_acc(fit_linear(revealed),blind),fam,param


def intelligence_holdout(rng):
    rows=[]
    for batch in range(3):
        data=intel_data(random.Random(rng.randrange(10**12)),240);a=120;b=168
        fit,val,rev,blind=data[:a],data[a:b],data[:b],data[b:]
        old,fam,param=baseline_intel(fit,val,rev,blind)
        _,meta=select_centroid_features(fit,val);model=fit_centroid_strategy(rev,meta['selected_features']);new=centroid_accuracy(model,blind)
        rows.append({'batch':batch,'baseline':old,'candidate':new,'baseline_family':fam,'baseline_param':param,'selected_features':meta['selected_features']})
    oldm=statistics.mean(r['baseline'] for r in rows);newm=statistics.mean(r['candidate'] for r in rows)
    return {'batches':rows,'baseline_mean':oldm,'candidate_mean':newm,'pass':newm>=oldm+.02 and all(r['candidate']>=r['baseline'] for r in rows)}


def main():
    rng=random.Random(SEED)
    report={'schema':'yado.cognitive_growth.fresh_holdout.v1','seed':SEED,'fresh_used_for_selection':False}
    report['logic']=logic_holdout(rng);report['thinking']=thinking_holdout(rng);report['intelligence']=intelligence_holdout(rng)
    report['pass']=all(report[k]['pass'] for k in ('logic','thinking','intelligence'))
    OUT.write_text(json.dumps(report,indent=2,sort_keys=True),encoding='utf-8')
    print(json.dumps({'pass':report['pass'],'logic':report['logic'],'thinking':report['thinking'],'intelligence':{'baseline_mean':report['intelligence']['baseline_mean'],'candidate_mean':report['intelligence']['candidate_mean'],'pass':report['intelligence']['pass']}},sort_keys=True))

if __name__=='__main__':main()
