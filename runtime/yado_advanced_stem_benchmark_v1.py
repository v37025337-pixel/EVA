from __future__ import annotations
from pathlib import Path
import collections, copy, hashlib, itertools, json, os, random, statistics, sys

ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(PKG))

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_algorithm_component_runtime_native_v1 import predict_logic_component, predict_intel_component, _thinking_predict

BUNDLE_PATH=ROOT.parent/'candidates'/'rc8-cognitive-genesis-v3'/'component-bundle.json'
PARENT_STATE=PKG/'yado_canonical_state_v3_rc8_external_cognitive.json'
OUT=ROOT/'advanced_stem_benchmark_v1'
OUT.mkdir(exist_ok=True)

def canonical(o): return json.dumps(o,sort_keys=True,separators=(',',':'),ensure_ascii=False,default=str)
def sha_file(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def majority(labels):
    c=collections.Counter(labels)
    return sorted(c.items(),key=lambda kv:(kv[1],kv[0]),reverse=True)[0][0]

bundle=json.loads(BUNDLE_PATH.read_text())
s1_intel_model=bundle['components']['INTELLIGENCE']['model']
parent_before=sha_file(PARENT_STATE)
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(OUT/'benchmark.sqlite'))

def choose_by_validation(rc5,rc6):
    v5=float(rc5.get('validation',0.0)); v6=float(rc6.get('validation',0.0))
    return ('RC6_META_GRAMMAR',rc6) if v6>v5 else ('RC5_ALGORITHM_GENESIS',rc5)

def eval_intel(task_id,domain,law,feature_gen,seed,fit_n=160,val_n=80,blind_n=240):
    rng=random.Random(seed)
    def make(n):
        rows=[]
        for _ in range(n):
            x=feature_gen(rng)
            rows.append((x,law(x)))
        return rows
    fit,val,blind=make(fit_n),make(val_n),make(blind_n)
    revealed=fit+val
    rc5=k.synthesize_intelligence_algorithm_component(fit,val,revealed,blind)
    rc6=k.synthesize_intelligence_with_extended_meta_grammar(fit,val,revealed,blind)
    origin,sel=choose_by_validation(rc5,rc6)
    model=sel.get('model')
    pred=[predict_intel_component(model,x) for x,_ in blind]
    score=sum(p==y for p,(_,y) in zip(pred,blind))/len(blind)
    base_label=majority([y for _,y in fit])
    baseline=sum(base_label==y for _,y in blind)/len(blind)
    meta_features={
      'integrity_score':1.0,'rollback_score':1.0,'fresh_blind':score,
      'ablation_drop':max(0.0,score-baseline),'transfer_score':score,'evidence_coverage':1.0
    }
    meta_action=predict_intel_component(s1_intel_model,meta_features)
    return {
      'task_id':task_id,'domain':domain,'kind':'INTELLIGENCE_CLASSIFICATION',
      'selected_origin':origin,'validation':float(sel.get('validation',0.0)),
      'fresh_blind':score,'baseline':baseline,'gain':score-baseline,
      'fit_count':len(fit),'validation_count':len(val),'blind_count':len(blind),
      's1_meta_action':meta_action,
      'candidate_status':sel.get('status'),
    }

def eval_logic(task_id,domain,law,seed):
    rng=random.Random(seed)
    core=[]
    for bits in itertools.product([False,True],repeat=6):
        x={f'b{i}':v for i,v in enumerate(bits)}
        core.append((x,law(x)))
    fit=[(dict(x,train_nonce=False),y) for x,y in core]
    val=[(dict(x,train_nonce=True),y) for x,y in core]
    blind=[(dict(x,blind_noise=bool(rng.getrandbits(1)),salt=rng.random()),y) for x,y in core]
    revealed=fit+val
    rc5=k.synthesize_logic_algorithm_component(fit,val,revealed,blind)
    rc6=k.synthesize_logic_with_extended_meta_grammar(fit,val,revealed,blind)
    origin,sel=choose_by_validation(rc5,rc6)
    model=sel.get('model')
    score=sum(bool(predict_logic_component(model,x))==bool(y) for x,y in blind)/len(blind)
    base=majority([y for _,y in fit])
    baseline=sum(bool(base)==bool(y) for _,y in blind)/len(blind)
    meta_features={
      'integrity_score':1.0,'rollback_score':1.0,'fresh_blind':score,
      'ablation_drop':max(0.0,score-baseline),'transfer_score':score,'evidence_coverage':1.0
    }
    return {
      'task_id':task_id,'domain':domain,'kind':'LOGIC_EXACT',
      'selected_origin':origin,'validation':float(sel.get('validation',0.0)),
      'fresh_blind':score,'baseline':baseline,'gain':score-baseline,
      'fit_count':len(fit),'validation_count':len(val),'blind_count':len(blind),
      's1_meta_action':predict_intel_component(s1_intel_model,meta_features),
      'candidate_status':sel.get('status'),
    }

def eval_plan(task_id,domain,order_fn,context_gen,roles,seed,fit_n=64,val_n=64,blind_n=128):
    rng=random.Random(seed)
    def mk(i,ctx,expected,shuffle):
        actions=[{'id':f'{task_id}-{i}-{j}','role':r} for j,r in enumerate(expected)]
        if shuffle: rng.shuffle(actions)
        return (ctx,actions,expected)
    fit=[];val=[];blind=[]
    for i in range(fit_n):
        ctx=context_gen(rng); exp=order_fn(ctx); fit.append(mk(i,ctx,exp,False))
    for i in range(val_n):
        ctx=context_gen(rng); exp=order_fn(ctx); val.append(mk(1000+i,ctx,exp,True))
    for i in range(blind_n):
        ctx=context_gen(rng); exp=order_fn(ctx); blind.append(mk(5000+i,ctx,exp,True))
    revealed=fit
    rc5=k.synthesize_thinking_algorithm_component(fit,val,revealed,blind)
    rc6=k.synthesize_thinking_with_extended_meta_grammar(fit,val,revealed,blind)
    origin,sel=choose_by_validation(rc5,rc6)
    model=sel.get('model')
    correct=0
    for episode in blind:
        pred,expected=_thinking_predict(model,episode)
        correct += pred==expected
    score=correct/len(blind)
    base_order=majority([tuple(e[2]) for e in fit])
    baseline=sum(tuple(e[2])==tuple(base_order) for e in blind)/len(blind)
    meta_features={
      'integrity_score':1.0,'rollback_score':1.0,'fresh_blind':score,
      'ablation_drop':max(0.0,score-baseline),'transfer_score':score,'evidence_coverage':1.0
    }
    return {
      'task_id':task_id,'domain':domain,'kind':'THINKING_CAUSAL_PLAN',
      'selected_origin':origin,'validation':float(sel.get('validation',0.0)),
      'fresh_blind':score,'baseline':baseline,'gain':score-baseline,
      'fit_count':len(fit),'validation_count':len(val),'blind_count':len(blind),
      's1_meta_action':predict_intel_component(s1_intel_model,meta_features),
      'candidate_status':sel.get('status'),
    }

tasks=[]

# PROGRAMMING / ALGORITHMS
tasks.append(eval_intel('P1_SHORTEST_PATH_ALGO','PROGRAMMING',
    lambda x: 'DAG_DP' if x['dag']>.5 else ('BELLMAN_FORD' if x['negative_edge']>.5 else ('BFS' if x['unweighted']>.5 else 'DIJKSTRA')),
    lambda r:{'dag':float(r.random()<.22),'negative_edge':float(r.random()<.18),'unweighted':float(r.random()<.34),'density':r.random(),'n_scale':r.random()},1101))
tasks.append(eval_intel('P2_SORTING_STRATEGY','PROGRAMMING',
    lambda x: 'INSERTION' if (x['n_scale']<.12 or (x['nearly_sorted']>.5 and x['n_scale']<.35)) else ('MERGESORT' if x['stable_required']>.5 else ('HEAPSORT' if x['memory_tight']>.5 else 'QUICKSORT')),
    lambda r:{'n_scale':r.random(),'nearly_sorted':float(r.random()<.3),'stable_required':float(r.random()<.35),'memory_tight':float(r.random()<.25),'duplicate_ratio':r.random()},1102))
tasks.append(eval_intel('P3_CONCURRENCY_PRIMITIVE','PROGRAMMING',
    lambda x:'ATOMIC_CAS' if x['lock_free_required']>.5 else ('RWLOCK' if x['read_ratio']>.82 and x['writer_ratio']<.2 else ('SHARDED_MUTEX' if x['contention']>.75 else 'MUTEX')),
    lambda r:{'lock_free_required':float(r.random()<.15),'read_ratio':r.random(),'writer_ratio':r.random(),'contention':r.random(),'latency_pressure':r.random()},1103))
tasks.append(eval_intel('P4_INDEX_SELECTION','PROGRAMMING',
    lambda x:'INVERTED' if x['full_text']>.5 else ('BTREE' if x['range_query']>.5 else ('HASH' if x['exact_match']>.5 and x['cardinality']>.7 else 'BTREE')),
    lambda r:{'full_text':float(r.random()<.15),'range_query':float(r.random()<.35),'exact_match':float(r.random()<.6),'cardinality':r.random(),'write_ratio':r.random()},1104))
tasks.append(eval_intel('P5_LINEAR_SOLVER_SELECTION','PROGRAMMING',
    lambda x:'CG' if x['sparse']>.5 and x['spd']>.5 else ('GMRES' if x['sparse']>.5 else ('LU' if x['n_scale']<.25 else 'QR')),
    lambda r:{'sparse':float(r.random()<.55),'spd':float(r.random()<.45),'n_scale':r.random(),'condition_scale':r.random(),'memory_pressure':r.random()},1105))

# MATHEMATICS
def quad_gen(r):
    cat=r.choice([-1,0,1])
    d=0.0 if cat==0 else (r.uniform(.05,4.0)*cat)
    return {'discriminant':d,'a_abs':r.uniform(.1,4),'scale':r.random()}
tasks.append(eval_intel('M1_QUADRATIC_REAL_ROOT_COUNT','MATHEMATICS',
    lambda x:'NO_REAL' if x['discriminant']<0 else ('ONE_REAL' if x['discriminant']==0 else 'TWO_REAL'),quad_gen,2101))
tasks.append(eval_intel('M2_LINEAR_SYSTEM_STATUS','MATHEMATICS',
    lambda x:'NONE' if x['rank_gap']>.5 else ('UNIQUE' if x['nullity']<.5 else 'INFINITE'),
    lambda r:{'rank_gap':float(r.random()<.22),'nullity':0.0 if r.random()<.45 else float(r.randint(1,4)),'dimension':r.uniform(2,8),'noise':r.random()},2102))
tasks.append(eval_intel('M3_SYMMETRIC_2X2_DEFINITENESS','MATHEMATICS',
    lambda x:'POSITIVE_DEFINITE' if x['a11']>0 and x['det']>0 else ('NEGATIVE_DEFINITE' if x['a11']<0 and x['det']>0 else 'INDEFINITE'),
    lambda r:{'a11':r.uniform(-3,3),'det':r.uniform(-4,4),'trace':r.uniform(-4,4),'scale':r.random()},2103))
def tri_gen(r):
    valid=r.random()>.12
    typ=r.choice([-1,0,1])
    margin=0.0 if typ==0 else typ*r.uniform(.05,3)
    return {'valid_margin':r.uniform(.05,2) if valid else -r.uniform(.01,1),'c2_minus_a2b2':margin,'scale':r.random()}
tasks.append(eval_intel('M4_TRIANGLE_CLASSIFICATION','MATHEMATICS',
    lambda x:'INVALID' if x['valid_margin']<=0 else ('ACUTE' if x['c2_minus_a2b2']<0 else ('RIGHT' if x['c2_minus_a2b2']==0 else 'OBTUSE')),tri_gen,2104))
tasks.append(eval_logic('M5_SIX_BIT_PARITY','MATHEMATICS',
    lambda x:sum(bool(x[f'b{i}']) for i in range(6))%2==1,2105))

# EXACT SCIENCES / PHYSICS
tasks.append(eval_intel('S1_REYNOLDS_REGIME','EXACT_SCIENCE',
    lambda x:'LAMINAR' if x['reynolds']<2300 else ('TRANSITIONAL' if x['reynolds']<4000 else 'TURBULENT'),
    lambda r:{'reynolds':r.uniform(200,9000),'roughness':r.random(),'aspect':r.random()},3101))
def orbit_gen(r):
    cat=r.choice([-1,0,1]); e=0.0 if cat==0 else cat*r.uniform(.02,4)
    return {'specific_energy':e,'eccentricity':r.uniform(0,2),'angular_momentum':r.random()}
tasks.append(eval_intel('S2_ORBITAL_ENERGY_CLASS','EXACT_SCIENCE',
    lambda x:'BOUND' if x['specific_energy']<0 else ('PARABOLIC' if x['specific_energy']==0 else 'ESCAPE'),orbit_gen,3102))
tasks.append(eval_intel('S3_RELATIVITY_REGIME','EXACT_SCIENCE',
    lambda x:'CLASSICAL' if x['beta']<.01 else ('LOW_RELATIVISTIC' if x['beta']<.3 else 'RELATIVISTIC'),
    lambda r:{'beta':r.uniform(0,.99),'gamma_hint':r.uniform(1,4),'noise':r.random()},3103))
def damp_gen(r):
    cat=r.choice([-1,0,1]); z=1.0 if cat==0 else (r.uniform(.05,.95) if cat<0 else r.uniform(1.05,3))
    return {'zeta':z,'omega0':r.uniform(.1,10),'noise':r.random()}
tasks.append(eval_intel('S4_RLC_DAMPING_REGIME','EXACT_SCIENCE',
    lambda x:'UNDERDAMPED' if x['zeta']<1 else ('CRITICAL' if x['zeta']==1 else 'OVERDAMPED'),damp_gen,3104))
tasks.append(eval_intel('S5_MACH_REGIME','EXACT_SCIENCE',
    lambda x:'SUBSONIC' if x['mach']<.8 else ('TRANSONIC' if x['mach']<1.2 else ('SUPERSONIC' if x['mach']<5 else 'HYPERSONIC')),
    lambda r:{'mach':r.uniform(0,8),'temperature_scale':r.random(),'altitude_scale':r.random()},3105))

# OTHER: CAUSAL / SCIENTIFIC PLANNING
roles16=['OBSERVE','ISOLATE','SNAPSHOT','DIAGNOSE','REPAIR','VERIFY','RESTORE','MONITOR']
def ctx16(r): return {'data_corruption':r.random(),'service_down':r.random(),'uncertainty':r.random()}
def ord16(c):
    return ['OBSERVE','ISOLATE','SNAPSHOT','DIAGNOSE','REPAIR','VERIFY','RESTORE','MONITOR'] if c['data_corruption']>.5 else ['OBSERVE','DIAGNOSE','ISOLATE','REPAIR','VERIFY','RESTORE','SNAPSHOT','MONITOR']
tasks.append(eval_plan('O1_INCIDENT_RESPONSE','CAUSAL_PLANNING',ord16,ctx16,roles16,4101))

roles17=['HYPOTHESIS','POWER','RANDOMIZE','BLIND','COLLECT','ANALYZE','REPLICATE','PUBLISH']
def ctx17(r): return {'confound_risk':r.random(),'measurement_bias':r.random(),'cost_pressure':r.random()}
def ord17(c):
    return ['HYPOTHESIS','POWER','RANDOMIZE','BLIND','COLLECT','ANALYZE','REPLICATE','PUBLISH'] if max(c['confound_risk'],c['measurement_bias'])>.55 else ['HYPOTHESIS','POWER','COLLECT','ANALYZE','RANDOMIZE','BLIND','REPLICATE','PUBLISH']
tasks.append(eval_plan('O2_EXPERIMENT_DESIGN','CAUSAL_PLANNING',ord17,ctx17,roles17,4102))

roles18=['SPEC','STATIC_ANALYSIS','UNIT_TEST','INTEGRATION_TEST','FORMAL_CHECK','CANARY','DEPLOY','MONITOR']
def ctx18(r): return {'safety_critical':r.random(),'novelty':r.random(),'deadline_pressure':r.random()}
def ord18(c):
    return ['SPEC','STATIC_ANALYSIS','FORMAL_CHECK','UNIT_TEST','INTEGRATION_TEST','CANARY','DEPLOY','MONITOR'] if c['safety_critical']>.5 else ['SPEC','STATIC_ANALYSIS','UNIT_TEST','INTEGRATION_TEST','FORMAL_CHECK','CANARY','DEPLOY','MONITOR']
tasks.append(eval_plan('O3_SOFTWARE_RELEASE','CAUSAL_PLANNING',ord18,ctx18,roles18,4103))

roles19=['STATE_GOAL','SEARCH_COUNTEREXAMPLE','DERIVE_LEMMA','CHECK_EDGE_CASES','COMPOSE_PROOF','VERIFY','MINIMIZE_ASSUMPTIONS','FINALIZE']
def ctx19(r): return {'counterexample_likelihood':r.random(),'lemma_gap':r.random(),'assumption_risk':r.random()}
def ord19(c):
    return ['STATE_GOAL','SEARCH_COUNTEREXAMPLE','CHECK_EDGE_CASES','DERIVE_LEMMA','COMPOSE_PROOF','MINIMIZE_ASSUMPTIONS','VERIFY','FINALIZE'] if c['counterexample_likelihood']>.5 else ['STATE_GOAL','DERIVE_LEMMA','SEARCH_COUNTEREXAMPLE','COMPOSE_PROOF','CHECK_EDGE_CASES','MINIMIZE_ASSUMPTIONS','VERIFY','FINALIZE']
tasks.append(eval_plan('O4_PROOF_WORKFLOW','CAUSAL_PLANNING',ord19,ctx19,roles19,4104))

roles20=['OBSERVE','HYPOTHESES','INTERVENTION','MEASURE','UPDATE_GRAPH','FALSIFY','REPLICATE','CONCLUDE']
def ctx20(r): return {'confounding':r.random(),'intervention_cost':r.random(),'observational_strength':r.random()}
def ord20(c):
    return ['OBSERVE','HYPOTHESES','INTERVENTION','MEASURE','UPDATE_GRAPH','FALSIFY','REPLICATE','CONCLUDE'] if c['confounding']>.5 else ['OBSERVE','HYPOTHESES','MEASURE','UPDATE_GRAPH','INTERVENTION','FALSIFY','REPLICATE','CONCLUDE']
tasks.append(eval_plan('O5_CAUSAL_DISCOVERY','CAUSAL_PLANNING',ord20,ctx20,roles20,4105))

# Summaries
by_domain={}
for d in sorted(set(t['domain'] for t in tasks)):
    xs=[t for t in tasks if t['domain']==d]
    by_domain[d]={
      'task_count':len(xs),
      'mean_fresh_blind':statistics.mean(t['fresh_blind'] for t in xs),
      'min_fresh_blind':min(t['fresh_blind'] for t in xs),
      'mean_baseline':statistics.mean(t['baseline'] for t in xs),
      'mean_gain':statistics.mean(t['gain'] for t in xs),
      'promote_actions':sum(t['s1_meta_action']=='PROMOTE_CANDIDATE' for t in xs),
      'repair_actions':sum(t['s1_meta_action']=='SHADOW_REPAIR' for t in xs),
      'research_actions':sum(t['s1_meta_action']=='RESEARCH_MORE' for t in xs),
      'rollback_actions':sum(t['s1_meta_action']=='ROLLBACK' for t in xs),
    }

summary={
  'task_count':len(tasks),
  'overall_mean_fresh_blind':statistics.mean(t['fresh_blind'] for t in tasks),
  'overall_min_fresh_blind':min(t['fresh_blind'] for t in tasks),
  'tasks_ge_0_90':sum(t['fresh_blind']>=.90 for t in tasks),
  'tasks_ge_0_80':sum(t['fresh_blind']>=.80 for t in tasks),
  'tasks_below_0_70':sum(t['fresh_blind']<.70 for t in tasks),
  'domains':by_domain,
  'weakest_tasks':sorted(
      [{'task_id':t['task_id'],'domain':t['domain'],'fresh_blind':t['fresh_blind'],'baseline':t['baseline'],'origin':t['selected_origin']} for t in tasks],
      key=lambda x:x['fresh_blind']
  )[:8],
}

parent_after=sha_file(PARENT_STATE)
receipt={
  'schema':'yado.rc8.s1.advanced_stem_benchmark.v1',
  'status':'ADVANCED_STEM_BENCHMARK_COMPLETED',
  'github_run_id':os.getenv('GITHUB_RUN_ID'),
  'github_sha':os.getenv('GITHUB_SHA'),
  'lineage_under_test':'S1-b86c3ab0c1eea088675d',
  'mode':'KERNEL_NATIVE_TASK_SPECIFIC_SYNTHESIS_WITH_FRESH_BLIND',
  'programming_boundary':'ALGORITHM_SELECTION_AND_CAUSAL_PLANNING_ONLY; NO_FREEFORM_CODE_GENERATION_OR_EXECUTION_CAPABILITY_IN_RC8',
  'tasks':tasks,
  'summary':summary,
  'parent_state_sha256_before':parent_before,
  'parent_state_sha256_after':parent_after,
  'parent_byte_identical':parent_before==parent_after,
  'canonical_mutation':False,
  'promotion_applied':False,
  'semantic_boundary':'MEASURES BOUNDED INDUCTION/PLANNING ON REPRESENTABLE STEM TASKS; NOT GENERAL MATHEMATICAL PROOF OR GENERAL PROGRAM SYNTHESIS',
}
receipt['receipt_sha256']=hashlib.sha256(canonical(receipt).encode()).hexdigest()
(ROOT/'yado_advanced_stem_benchmark_v1_receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True,ensure_ascii=False,default=str)+'\n')
print(json.dumps({'status':receipt['status'],'summary':summary,'parent_byte_identical':receipt['parent_byte_identical'],'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
k.close()
