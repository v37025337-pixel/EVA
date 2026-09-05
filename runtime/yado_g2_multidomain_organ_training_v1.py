from __future__ import annotations
from pathlib import Path
from collections import defaultdict
import copy,hashlib,itertools,json,random,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_evolution_runtime_native_v1 import fit_bool_tree,acc_logic_model,fit_tree,tree_acc
from yado_cognitive_growth_runtime_v1 import learn_multicontext_precedence,planning_accuracy
from yado_neutral_evidence_profile_selector_v1 import NeutralEvidenceProfileSelectorV1,EvidenceCandidate
from yado_unified_core_v1 import UnifiedYADOCoreV1

OUT=REPO/'candidates/kernel-self-generated/g2-multidomain-organ-training-v1.json'
EXP=REPO/'experience/yado-multidomain-organ-training-v1.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()

def select(cands,complexity_penalty=.01):
    s=NeutralEvidenceProfileSelectorV1.select([
        EvidenceCandidate(token=c['token'],evidence=c['validation'],complexity=c['complexity'],risk=0.0,novelty=.2)
        for c in cands
    ],complexity_penalty=complexity_penalty,risk_penalty=.2,novelty_bonus=.01)
    return next(c for c in cands if c['token']==s['selected_token']),s

# ---------------- LOGIC ----------------
logic_specs=[
 ('MATH_PARITY','MATHEMATICS',
  lambda x:(sum(bool(x[f'b{i}']) for i in range(5))%2)==1,
  [f'b{i}' for i in range(5)]),
 ('CODE_RELEASE_INVARIANT','PROGRAMMING',
  lambda x: bool(x['tests_pass'] and x['rollback_ready'] and not x['invariant_break'] and (x['reviewed'] or x['low_risk'])),
  ['tests_pass','rollback_ready','invariant_break','reviewed','low_risk']),
 ('SCIENTIFIC_EVIDENCE_ACCEPT','EXACT_SCIENCE',
  lambda x: bool(x['replicated'] and not x['contradiction'] and (x['strong_effect'] or x['high_power']) and x['measurement_valid']),
  ['replicated','contradiction','strong_effect','high_power','measurement_valid']),
 ('CAUSAL_CLAIM_VALID','CAUSAL_REASONING',
  lambda x: bool(x['temporal_order'] and x['intervention'] and x['mechanism'] and not x['confounder'] and not x['selection_bias']),
  ['temporal_order','intervention','mechanism','confounder','selection_bias']),
 ('DATA_RESULT_TRUST','DATA_ANALYSIS',
  lambda x: bool(x['schema_valid'] and x['sample_adequate'] and not x['leakage'] and (x['replicated'] or x['external_check'])),
  ['schema_valid','sample_adequate','leakage','replicated','external_check']),
]

logic_rows=[]
for ti,(tid,domain,law,fields) in enumerate(logic_specs):
    core=[]
    for bits in itertools.product([False,True],repeat=len(fields)):
        x={k:v for k,v in zip(fields,bits)}
        core.append((x,bool(law(x))))
    rng=random.Random(1000+ti)
    rng.shuffle(core)
    n=len(core)
    fit=core[:max(16,int(n*.50))]
    val=core[max(16,int(n*.50)):max(24,int(n*.75))]
    blind=core[max(24,int(n*.75)):]
    # Guarantee meaningful blind when the truth table is only 32 rows.
    if len(blind)<8:
        fit=core[:16];val=core[16:24];blind=core[24:]
    candidates=[]
    for depth in (1,2,3,4,5,6):
        m=fit_bool_tree(fit,depth)
        candidates.append({'token':f'D{depth}','depth':depth,'complexity':depth,'validation':acc_logic_model('BOOL_DECISION_TREE',m,val),'model':m})
    chosen,selector=select(candidates)
    model=fit_bool_tree(fit+val,chosen['depth'])
    fresh=acc_logic_model('BOOL_DECISION_TREE',model,blind)
    labels=[y for _,y in fit+val]
    maj=sum(labels)>=len(labels)/2
    ablation=sum(bool(maj)==bool(y) for _,y in blind)/len(blind)
    noise=[(dict(x,novel_noise=bool(i%2)),y) for i,(x,y) in enumerate(blind)]
    noise_score=acc_logic_model('BOOL_DECISION_TREE',model,noise)
    logic_rows.append({'task_id':tid,'domain':domain,'selected':{k:chosen[k] for k in ('token','depth','validation')},'native_selector':selector,
      'fit_count':len(fit),'validation_count':len(val),'blind_count':len(blind),'fresh':fresh,'ablation':ablation,'causal_drop':fresh-ablation,
      'noise_score':noise_score,'model':model})

# ---------------- THINKING ----------------
thinking_specs=[
 ('INCIDENT_RESPONSE','OPERATIONS',['OBSERVE','ISOLATE','SNAPSHOT','DIAGNOSE','REPAIR','VERIFY','MONITOR'],
  lambda c: ['OBSERVE','ISOLATE','SNAPSHOT','DIAGNOSE','REPAIR','VERIFY','MONITOR'] if c['data_corruption'] else ['OBSERVE','DIAGNOSE','ISOLATE','REPAIR','VERIFY','SNAPSHOT','MONITOR'],
  lambda r:{'data_corruption':r.random()<.5,'uncertain':r.random()<.4,'high_impact':r.random()<.4}),
 ('EXPERIMENT_DESIGN','SCIENCE',['HYPOTHESIS','POWER','RANDOMIZE','BLIND','COLLECT','ANALYZE','REPLICATE'],
  lambda c: ['HYPOTHESIS','POWER','RANDOMIZE','BLIND','COLLECT','ANALYZE','REPLICATE'] if c['confound_risk'] else ['HYPOTHESIS','POWER','COLLECT','ANALYZE','RANDOMIZE','BLIND','REPLICATE'],
  lambda r:{'confound_risk':r.random()<.5,'measurement_bias':r.random()<.4,'cost_pressure':r.random()<.5}),
 ('PROOF_WORKFLOW','MATHEMATICS',['STATE_GOAL','COUNTEREXAMPLE','LEMMA','EDGE_CASES','COMPOSE','VERIFY','FINALIZE'],
  lambda c: ['STATE_GOAL','COUNTEREXAMPLE','EDGE_CASES','LEMMA','COMPOSE','VERIFY','FINALIZE'] if c['counterexample_risk'] else ['STATE_GOAL','LEMMA','COUNTEREXAMPLE','COMPOSE','EDGE_CASES','VERIFY','FINALIZE'],
  lambda r:{'counterexample_risk':r.random()<.5,'lemma_gap':r.random()<.5,'assumption_risk':r.random()<.5}),
 ('CODE_REPAIR','PROGRAMMING',['OBSERVE_FAILURE','BUILD_ORACLE','HYPOTHESIZE','PATCH','TEST','REGRESSION','COMMIT'],
  lambda c: ['OBSERVE_FAILURE','BUILD_ORACLE','HYPOTHESIZE','PATCH','TEST','REGRESSION','COMMIT'] if c['oracle_missing'] else ['OBSERVE_FAILURE','HYPOTHESIZE','TEST','PATCH','REGRESSION','BUILD_ORACLE','COMMIT'],
  lambda r:{'oracle_missing':r.random()<.5,'multi_file':r.random()<.4,'regression_risk':r.random()<.5}),
 ('DATA_INVESTIGATION','DATA_ANALYSIS',['SCHEMA','CLEAN','PROFILE','HYPOTHESIS','TEST','ROBUSTNESS','CONCLUDE'],
  lambda c: ['SCHEMA','CLEAN','PROFILE','HYPOTHESIS','TEST','ROBUSTNESS','CONCLUDE'] if c['dirty_data'] else ['SCHEMA','PROFILE','HYPOTHESIS','TEST','ROBUSTNESS','CLEAN','CONCLUDE'],
  lambda r:{'dirty_data':r.random()<.5,'missingness':r.random()<.5,'confounding':r.random()<.4}),
]

def make_episode(tid,i,ctx,expected,rng,shuffle=True):
    acts=[{'id':f'{tid}-{i}-{j}','role':role} for j,role in enumerate(expected)]
    if shuffle:rng.shuffle(acts)
    return (ctx,acts,expected)

thinking_rows=[]
for ti,(tid,domain,roles,order_fn,ctx_fn) in enumerate(thinking_specs):
    rng=random.Random(2000+ti)
    fit=[];val=[];blind=[]
    for i in range(80):
        c=ctx_fn(rng);fit.append((c,order_fn(c)))
    for i in range(40):
        c=ctx_fn(rng);val.append(make_episode(tid,1000+i,c,order_fn(c),rng,True))
    for i in range(80):
        c=ctx_fn(rng);blind.append(make_episode(tid,5000+i,c,order_fn(c),rng,True))
    candidates=[]
    for threshold in (.55,.60,.67,.75):
        for keys in (1,2,3):
            for support in (2,3,4):
                m=learn_multicontext_precedence(fit,threshold=threshold,min_support=support,max_context_keys=keys)
                va=planning_accuracy(m,val)
                candidates.append({'token':f'T{threshold}_K{keys}_S{support}','threshold':threshold,'max_context_keys':keys,'min_support':support,
                                   'complexity':keys+.25*support,'validation':va,'model':m})
    chosen,selector=select(candidates,.008)
    model=learn_multicontext_precedence(fit,threshold=chosen['threshold'],min_support=chosen['min_support'],max_context_keys=chosen['max_context_keys'])
    fresh=planning_accuracy(model,blind)
    ab_model=learn_multicontext_precedence([({},trace) for _,trace in fit],threshold=chosen['threshold'],min_support=chosen['min_support'],max_context_keys=0)
    ablation=planning_accuracy(ab_model,blind)
    thinking_rows.append({'task_id':tid,'domain':domain,'selected':{k:chosen[k] for k in ('token','threshold','max_context_keys','min_support','validation')},
      'native_selector':selector,'fit_count':len(fit),'validation_count':len(val),'blind_count':len(blind),'fresh':fresh,'ablation':ablation,
      'causal_drop':fresh-ablation,'model':model})

# ---------------- INTELLIGENCE ----------------
intel_specs=[
 ('ALGORITHM_SELECTION','PROGRAMMING',
  lambda x:'DAG_DP' if x['dag']>.5 else ('BELLMAN_FORD' if x['negative']>.5 else ('BFS' if x['unweighted']>.5 else 'DIJKSTRA')),
  lambda r:{'dag':float(r.random()<.22),'negative':float(r.random()<.18),'unweighted':float(r.random()<.34),'density':r.random(),'scale':r.random()}),
 ('MATH_METHOD','MATHEMATICS',
  lambda x:'SYMBOLIC' if x['exact_required']>.5 else ('ITERATIVE' if x['large_sparse']>.5 else ('ROBUST_NUMERIC' if x['ill_conditioned']>.5 else 'DIRECT_NUMERIC')),
  lambda r:{'exact_required':float(r.random()<.25),'large_sparse':float(r.random()<.35),'ill_conditioned':float(r.random()<.25),'dimension':r.random(),'noise':r.random()}),
 ('SCIENCE_ANALYSIS','EXACT_SCIENCE',
  lambda x:'CAUSAL_INTERVENTION' if x['causal_question']>.5 and x['intervention_possible']>.5 else ('TIME_SERIES' if x['temporal']>.5 else ('GROUP_COMPARISON' if x['categorical_group']>.5 else 'CORRELATION')),
  lambda r:{'causal_question':float(r.random()<.35),'intervention_possible':float(r.random()<.45),'temporal':float(r.random()<.30),'categorical_group':float(r.random()<.35),'noise':r.random()}),
 ('RESOURCE_STRATEGY','OPERATIONS',
  lambda x:'STOP' if x['confidence']>.88 else ('CHEAP_PROBE' if x['budget_low']>.5 else ('PARALLEL_PROBES' if x['latency_pressure']>.5 else 'DEEP_PROBE')),
  lambda r:{'confidence':r.random(),'budget_low':float(r.random()<.35),'latency_pressure':float(r.random()<.35),'uncertainty':r.random(),'risk':r.random()}),
 ('DATA_REMEDIATION','DATA_ANALYSIS',
  lambda x:'REJECT' if x['schema_broken']>.5 else ('IMPUTE' if x['missingness']>.35 else ('ROBUST_FILTER' if x['outliers']>.4 else 'USE_AS_IS')),
  lambda r:{'schema_broken':float(r.random()<.15),'missingness':r.random(),'outliers':r.random(),'sample_scale':r.random(),'noise':r.random()}),
]

intel_rows=[]
for ti,(tid,domain,law,gen) in enumerate(intel_specs):
    rng=random.Random(3000+ti)
    def mk(n):
        return [(gen(rng),None) for _ in range(n)]
    fit0=mk(180);fit=[(x,law(x)) for x,_ in fit0]
    val0=mk(90);val=[(x,law(x)) for x,_ in val0]
    blind0=mk(180);blind=[(x,law(x)) for x,_ in blind0]
    candidates=[]
    for depth in (1,2,3,4,5,6):
        m=fit_tree(fit,depth)
        candidates.append({'token':f'D{depth}','depth':depth,'complexity':depth,'validation':tree_acc(m,val),'model':m})
    chosen,selector=select(candidates)
    model=fit_tree(fit+val,chosen['depth'])
    fresh=tree_acc(model,blind)
    counts=defaultdict(int)
    for _,y in fit+val:counts[y]+=1
    maj=max(counts,key=counts.get)
    ablation=sum(y==maj for _,y in blind)/len(blind)
    intel_rows.append({'task_id':tid,'domain':domain,'selected':{k:chosen[k] for k in ('token','depth','validation')},'native_selector':selector,
      'fit_count':len(fit),'validation_count':len(val),'blind_count':len(blind),'fresh':fresh,'ablation':ablation,'causal_drop':fresh-ablation,'model':model})

def organ_summary(rows):
    return {'task_count':len(rows),'mean_fresh':sum(x['fresh'] for x in rows)/len(rows),'min_fresh':min(x['fresh'] for x in rows),
            'mean_ablation':sum(x['ablation'] for x in rows)/len(rows),'mean_causal_drop':sum(x['causal_drop'] for x in rows)/len(rows),
            'tasks_ge_0_80':sum(x['fresh']>=.80 for x in rows),'tasks_ge_0_90':sum(x['fresh']>=.90 for x in rows)}

summary={'LOGIC':organ_summary(logic_rows),'THINKING':organ_summary(thinking_rows),'INTELLIGENCE':organ_summary(intel_rows)}
parents={'LOGIC':'GENE-G2-GLOBAL-EXPERIENCE-LOGIC-V3-a00c3f7d2b3021c0',
         'THINKING':'GENE-G2-GLOBAL-EXPERIENCE-THINKING-V3-70cc30f21cdab3ac',
         'INTELLIGENCE':'GENE-G2-GLOBAL-EXPERIENCE-INTELLIGENCE-V2-64c61db88585744d'}
genes={}
for organ,rows in [('LOGIC',logic_rows),('THINKING',thinking_rows),('INTELLIGENCE',intel_rows)]:
    g={'schema':'yado.g2.multidomain_organ_portfolio_gene.v1','organ':organ,'heritage':[parents[organ]],
       'gene_id':'GENE-G2-MULTIDOMAIN-'+organ+'-V1-'+digest({'organ':organ,'models':[x['model'] for x in rows]})[:16],
       'task_models':[{k:v for k,v in x.items() if k not in ('native_selector',)} for x in rows],
       'summary':summary[organ],'promotion_state':'SHADOW_ONLY',
       'origin':'YADO_NATIVE_MULTI_DOMAIN_FIT_VALIDATION_FRESH_TRAINING'}
    g['gene_digest']=digest(g);genes[organ]=g

core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)
checks={
 'five_logic_domains':len(logic_rows)==5,'five_thinking_domains':len(thinking_rows)==5,'five_intelligence_domains':len(intel_rows)==5,
 'logic_mean_fresh_ge_0_80':summary['LOGIC']['mean_fresh']>=.80,'logic_min_fresh_ge_0_65':summary['LOGIC']['min_fresh']>=.65,
 'thinking_mean_fresh_ge_0_80':summary['THINKING']['mean_fresh']>=.80,'thinking_min_fresh_ge_0_65':summary['THINKING']['min_fresh']>=.65,
 'intelligence_mean_fresh_ge_0_80':summary['INTELLIGENCE']['mean_fresh']>=.80,'intelligence_min_fresh_ge_0_65':summary['INTELLIGENCE']['min_fresh']>=.65,
 'logic_causal_drop':summary['LOGIC']['mean_causal_drop']>=.15,'thinking_causal_drop':summary['THINKING']['mean_causal_drop']>=.15,
 'intelligence_causal_drop':summary['INTELLIGENCE']['mean_causal_drop']>=.15,
 'three_new_gene_identities':len({x['gene_id'] for x in genes.values()})==3,
 'external_models_used':False,'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'automatic_canonical_promotion':False}
false_keys=['external_models_used','automatic_canonical_promotion']
passed=all(v is True for k,v in checks.items() if k not in false_keys) and all(checks[k] is False for k in false_keys)
status='PASS_SHADOW_G2_MULTIDOMAIN_ORGAN_TRAINING_V1' if passed else 'WITHHOLD_G2_MULTIDOMAIN_ORGAN_TRAINING_V1'

exp={'schema':'yado.g2.multidomain_organ_training.experience.v1','status':'TRAINED' if passed else 'WITHHOLD',
 'summary':summary,'logic_tasks':logic_rows,'thinking_tasks':thinking_rows,'intelligence_tasks':intel_rows,'genes':genes,'checks':checks,
 'canonical_mutation':False,'semantic_boundary':'CONTROLLED MULTIDOMAIN TRAINING WITH PERSISTED NATIVE MODELS. EACH ORGAN HAS FIVE SPECIALIST TASK MODELS ACROSS DIFFERENT DOMAINS. THIS DOES NOT YET PROVE GENERAL COGNITION OR REAL-DATA TRANSFER; NEXT STEP IS COGNITIVE COMPOSITION AND THEN REAL DATA.'}
exp['experience_digest']=digest(exp);EXP.parent.mkdir(parents=True,exist_ok=True);EXP.write_text(json.dumps(exp,indent=2,sort_keys=True,default=str)+'\n')
report={'schema':'yado.g2.multidomain_organ_training.v1','status':status,'summary':summary,'gene_ids':{k:v['gene_id'] for k,v in genes.items()},
 'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'MULTIDOMAIN_COGNITIVE_COMPOSITION_TRAINING_V1' if passed else 'MULTIDOMAIN_ORGAN_TRAINING_REPAIR_V2',
 'receipt_sha256':None}
report['receipt_sha256']=digest({k:v for k,v in report.items() if k!='receipt_sha256'});OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
print(json.dumps(report,indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
