from __future__ import annotations
from pathlib import Path
from collections import defaultdict,Counter
import copy,hashlib,json,random,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_budget_adaptive_compositional_logic_v2 import BudgetAdaptiveCompositionalLogicV2
from yado_organ_runtime_native_v1 import tree_predict,fit_tree,tree_acc
from yado_cognitive_growth_runtime_v1 import plan_multicontext,fit_knn_strategy,knn_predict,strategy_accuracy,fit_centroid_strategy,centroid_predict,centroid_accuracy
from yado_neutral_evidence_profile_selector_v1 import NeutralEvidenceProfileSelectorV1,EvidenceCandidate
from yado_unified_core_v1 import UnifiedYADOCoreV1

LOGIC_EXP=REPO/'experience/yado-multidomain-logic-training-repair-v2.json'
ORGAN_EXP=REPO/'experience/yado-multidomain-organ-training-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-multidomain-cognitive-composition-training-v1.json'
EXP=REPO/'experience/yado-multidomain-cognitive-composition-training-v1.json'

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
lexp=load(LOGIC_EXP);oexp=load(ORGAN_EXP)
if lexp.get('status')!='TRAINED':raise RuntimeError('LOGIC_V2_TRAINED_REQUIRED')
if oexp.get('status')!='WITHHOLD':raise RuntimeError('ORGAN_V1_EXPECTED_WITHHOLD')
if not ((oexp.get('checks') or {}).get('thinking_mean_fresh_ge_0_80') and (oexp.get('checks') or {}).get('intelligence_mean_fresh_ge_0_80')):
    raise RuntimeError('STRONG_THINKING_INTELLIGENCE_REQUIRED')

logic_gene=lexp['genes']['LOGIC'];thinking_gene=lexp['genes']['THINKING'];intel_gene=lexp['genes']['INTELLIGENCE']
logic_tasks={x['task_id']:x for x in logic_gene['task_models']}
thinking_tasks={x['task_id']:x for x in thinking_gene['task_models']}
intel_tasks={x['task_id']:x for x in intel_gene['task_models']}

domains={
 'PROGRAMMING':('CODE_RELEASE_INVARIANT','CODE_REPAIR','ALGORITHM_SELECTION'),
 'MATHEMATICS':('MATH_PARITY','PROOF_WORKFLOW','MATH_METHOD'),
 'DATA_ANALYSIS':('DATA_RESULT_TRUST','DATA_INVESTIGATION','DATA_REMEDIATION'),
 'SCIENCE':('SCIENTIFIC_EVIDENCE_ACCEPT','EXPERIMENT_DESIGN','SCIENCE_ANALYSIS'),
 'OPERATIONS_CAUSAL':('CAUSAL_CLAIM_VALID','INCIDENT_RESPONSE','RESOURCE_STRATEGY'),
}

def logic_predict(task,x):
    fam=task['selected']['family'];m=task['model']
    if fam=='SYMMETRIC_COUNT_MAP_V2':return bool(BudgetAdaptiveCompositionalLogicV2.predict_symmetric_boolean(m,x))
    return bool(tree_predict(m,x))

def thinking_order(task,ctx):
    roles={
      'CODE_REPAIR':['OBSERVE_FAILURE','BUILD_ORACLE','HYPOTHESIZE','PATCH','TEST','REGRESSION','COMMIT'],
      'PROOF_WORKFLOW':['STATE_GOAL','COUNTEREXAMPLE','LEMMA','EDGE_CASES','COMPOSE','VERIFY','FINALIZE'],
      'DATA_INVESTIGATION':['SCHEMA','CLEAN','PROFILE','HYPOTHESIS','TEST','ROBUSTNESS','CONCLUDE'],
      'EXPERIMENT_DESIGN':['HYPOTHESIS','POWER','RANDOMIZE','BLIND','COLLECT','ANALYZE','REPLICATE'],
      'INCIDENT_RESPONSE':['OBSERVE','ISOLATE','SNAPSHOT','DIAGNOSE','REPAIR','VERIFY','MONITOR'],
    }[task['task_id']]
    acts=[{'id':f'A{i}','role':r} for i,r in enumerate(roles)]
    ids=plan_multicontext(task['model'],ctx,acts);by={a['id']:a['role'] for a in acts}
    return [by[i] for i in ids]

def cautious(task_id,order):
    pairs={
      'CODE_REPAIR':('BUILD_ORACLE','HYPOTHESIZE'),
      'PROOF_WORKFLOW':('COUNTEREXAMPLE','LEMMA'),
      'DATA_INVESTIGATION':('CLEAN','PROFILE'),
      'EXPERIMENT_DESIGN':('RANDOMIZE','COLLECT'),
      'INCIDENT_RESPONSE':('ISOLATE','DIAGNOSE'),
    }
    a,b=pairs[task_id]
    return order.index(a)<order.index(b)

robust_labels={
 'ALGORITHM_SELECTION':{'DAG_DP','BELLMAN_FORD'},
 'MATH_METHOD':{'SYMBOLIC','ROBUST_NUMERIC'},
 'DATA_REMEDIATION':{'REJECT','ROBUST_FILTER'},
 'SCIENCE_ANALYSIS':{'CAUSAL_INTERVENTION','TIME_SERIES'},
 'RESOURCE_STRATEGY':{'DEEP_PROBE','PARALLEL_PROBES','STOP'},
}

def gen_inputs(domain,r):
    if domain=='PROGRAMMING':
        lx={k:bool(r.getrandbits(1)) for k in ['tests_pass','rollback_ready','invariant_break','reviewed','low_risk']}
        tc={'oracle_missing':r.random()<.5,'multi_file':r.random()<.4,'regression_risk':r.random()<.5}
        ix={'dag':float(r.random()<.22),'negative':float(r.random()<.18),'unweighted':float(r.random()<.34),'density':r.random(),'scale':r.random()}
    elif domain=='MATHEMATICS':
        lx={f'b{i}':bool(r.getrandbits(1)) for i in range(5)}
        tc={'counterexample_risk':r.random()<.5,'lemma_gap':r.random()<.5,'assumption_risk':r.random()<.5}
        ix={'exact_required':float(r.random()<.25),'large_sparse':float(r.random()<.35),'ill_conditioned':float(r.random()<.25),'dimension':r.random(),'noise':r.random()}
    elif domain=='DATA_ANALYSIS':
        lx={k:bool(r.getrandbits(1)) for k in ['schema_valid','sample_adequate','leakage','replicated','external_check']}
        tc={'dirty_data':r.random()<.5,'missingness':r.random()<.5,'confounding':r.random()<.4}
        ix={'schema_broken':float(r.random()<.15),'missingness':r.random(),'outliers':r.random(),'sample_scale':r.random(),'noise':r.random()}
    elif domain=='SCIENCE':
        lx={k:bool(r.getrandbits(1)) for k in ['replicated','contradiction','strong_effect','high_power','measurement_valid']}
        tc={'confound_risk':r.random()<.5,'measurement_bias':r.random()<.4,'cost_pressure':r.random()<.5}
        ix={'causal_question':float(r.random()<.35),'intervention_possible':float(r.random()<.45),'temporal':float(r.random()<.30),'categorical_group':float(r.random()<.35),'noise':r.random()}
    else:
        lx={k:bool(r.getrandbits(1)) for k in ['temporal_order','intervention','mechanism','confounder','selection_bias']}
        tc={'data_corruption':r.random()<.5,'uncertain':r.random()<.4,'high_impact':r.random()<.4}
        ix={'confidence':r.random(),'budget_low':float(r.random()<.35),'latency_pressure':float(r.random()<.35),'uncertainty':r.random(),'risk':r.random()}
    return lx,tc,ix

def intel_predict(task,x):return str(tree_predict(task['model'],x))

def sample(domain,r):
    ltid,ttid,itid=domains[domain]
    lt=logic_tasks[ltid];tt=thinking_tasks[ttid];it=intel_tasks[itid]
    lx,tc,ix=gen_inputs(domain,r)
    lo=logic_predict(lt,lx)
    order=thinking_order(tt,tc);co=cautious(ttid,order)
    il=intel_predict(it,ix);rob=il in robust_labels[itid]
    feat={'state_known':1.0,'logic_accept':1.0 if lo else 0.0,'thinking_cautious':1.0 if co else 0.0,'intelligence_robust':1.0 if rob else 0.0}
    if not lo:y='WITHHOLD'
    elif co and rob:y='VERIFY'
    elif co and not rob:y='REPLAN'
    elif (not co) and rob:y='ACT_WITH_GUARD'
    else:y='ACT'
    return feat,y,{'domain':domain,'logic_task':ltid,'thinking_task':ttid,'intelligence_task':itid,'logic_output':lo,'thinking_cautious':co,'intelligence_output':il,'intelligence_robust':rob}

def balanced_set(seed,per_class):
    r=random.Random(seed);g=defaultdict(list);classes={'WITHHOLD','VERIFY','REPLAN','ACT_WITH_GUARD','ACT'}
    for _ in range(20000):
        d=r.choice(sorted(domains));x,y,meta=sample(d,r)
        if len(g[y])<per_class:g[y].append((x,y,meta))
        if all(len(g[c])>=per_class for c in classes):break
    if not all(len(g[c])>=per_class for c in classes):raise RuntimeError('COGNITIVE_CLASS_BALANCE_FAILED:'+str({c:len(g[c]) for c in classes}))
    out=[]
    for c in sorted(classes):out.extend(g[c][:per_class])
    r.shuffle(out);return out

fit3=balanced_set(4101,60);val3=balanced_set(4102,30);blind3=balanced_set(4103,50)
fit=[(x,y) for x,y,_ in fit3];val=[(x,y) for x,y,_ in val3];blind=[(x,y) for x,y,_ in blind3]

def score(f,m,cases):
    if f=='CART_AXIS':return tree_acc(m,cases)
    if f=='KNN_STRATEGY':return strategy_accuracy(m,cases)
    return centroid_accuracy(m,cases)
def fitm(f,param,cases):
    if f=='CART_AXIS':return fit_tree(cases,int(param))
    if f=='KNN_STRATEGY':return fit_knn_strategy(cases,int(param))
    return fit_centroid_strategy(cases,int(param))
def pred(f,m,x):
    if f=='CART_AXIS':return tree_predict(m,x)
    if f=='KNN_STRATEGY':return knn_predict(m,x)
    return centroid_predict(m,x)
groups={'LOGIC':['logic_accept'],'THINKING':['thinking_cautious'],'INTELLIGENCE':['intelligence_robust']}
def ablate(cases,organ):
    out=[]
    for x,y in cases:
        z=dict(x)
        for k in groups[organ]:z[k]=0.0
        out.append((z,y))
    return out

trials=[]
profiles=[('CART_AXIS',d,d) for d in (1,2,3,4,5)]+[('KNN_STRATEGY',k,k) for k in (1,3,5,7,9)]+[('CENTROID_STRATEGY',n,n) for n in (1,2,3,4)]
for fam,param,complexity in profiles:
    m=fitm(fam,param,fit);va=score(fam,m,val)
    drops={g:va-score(fam,m,ablate(val,g)) for g in groups}
    trials.append({'token':fam+'_'+str(param),'family':fam,'param':param,'complexity':complexity,'validation':va,'drops':drops,'model':m})
eligible=[t for t in trials if t['validation']>=.95 and all(t['drops'][g]>=.10 for g in groups)]
if not eligible:
    best=sorted([{k:v for k,v in t.items() if k!='model'} for t in trials],key=lambda t:(-min(t['drops'].values()),-t['validation']))[:10]
    report={'schema':'yado.g2.multidomain_cognitive_composition_training.v1','status':'WITHHOLD_G2_MULTIDOMAIN_COGNITIVE_COMPOSITION_TRAINING_V1',
      'reason':'NO_NATIVE_COMPOSITION_MODEL_REQUIRES_ALL_THREE_ORGANS','best_trials':best,'canonical_mutation':False,
      'next_required_capability':'MULTIDOMAIN_COGNITIVE_COMPLEMENTARITY_REPAIR_V2'}
    report['receipt_sha256']=digest(report);OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    EXP.parent.mkdir(parents=True,exist_ok=True);EXP.write_text(json.dumps(report|{'schema':'yado.g2.multidomain_cognitive_composition_training.experience.v1'},indent=2,sort_keys=True)+'\n')
    print(json.dumps(report,indent=2,sort_keys=True));raise SystemExit(2)
sel=NeutralEvidenceProfileSelectorV1.select([EvidenceCandidate(token=t['token'],evidence=t['validation']+.5*min(t['drops'].values()),complexity=t['complexity'],risk=0,novelty=.2) for t in eligible],
 complexity_penalty=.008,risk_penalty=.2,novelty_bonus=.01)
chosen=next(t for t in eligible if t['token']==sel['selected_token'])
model=fitm(chosen['family'],chosen['param'],fit+val)
fresh=score(chosen['family'],model,blind)
drops={g:fresh-score(chosen['family'],model,ablate(blind,g)) for g in groups}
class_scores={}
for c in ('WITHHOLD','VERIFY','REPLAN','ACT_WITH_GUARD','ACT'):
    xs=[z for z in blind if z[1]==c];class_scores[c]={'count':len(xs),'accuracy':score(chosen['family'],model,xs)}
# Domain slices are metadata only and were never exposed as model features.
domain_scores={}
for d in sorted(domains):
    xs=[(x,y) for x,y,m in blind3 if m['domain']==d]
    domain_scores[d]={'count':len(xs),'accuracy':score(chosen['family'],model,xs) if xs else None}
noise=[]
for i,(x,y) in enumerate(blind):
    z=dict(x);z['unseen_domain_noise']=float(i%7);z['irrelevant']=1.0
    noise.append((z,y))
noise_score=score(chosen['family'],model,noise)

cog_gene={'schema':'yado.g2.multidomain_cognitive_composition_gene.v1',
 'gene_id':'GENE-G2-MULTIDOMAIN-COGNITIVE-V1-'+digest({'model':model,'parents':[logic_gene['gene_digest'],thinking_gene['gene_digest'],intel_gene['gene_digest']]})[:16],
 'organ':'CONSCIOUS_WORKSPACE','heritage':[logic_gene['gene_id'],thinking_gene['gene_id'],intel_gene['gene_id'],'RUNTIME-G2-EXPERIENCE-CONDITIONED-COGNITIVE-LAYER-V3'],
 'strategy_family':chosen['family'],'selected_profile':{k:chosen[k] for k in ('token','family','param','validation','drops')},
 'native_selector':sel,'model':model,'fresh_blind':fresh,'organ_ablation_drops':drops,'class_scores':class_scores,'domain_scores':domain_scores,
 'unknown_policy':'WITHHOLD_VIA_EXISTING_CANONICAL_SAFETY_SUBSTRATE','promotion_state':'SHADOW_ONLY',
 'origin':'YADO_NATIVE_COGNITIVE_COMPOSITION_OVER_MULTIDOMAIN_ORGAN_OUTPUTS'}
cog_gene['gene_digest']=digest(cog_gene)
genes={'LOGIC':logic_gene,'THINKING':thinking_gene,'INTELLIGENCE':intel_gene,'COGNITIVE':cog_gene}
genome={'schema':'yado.g2.multidomain_cognitive_curriculum_genome.v1',
 'genome_id':'GENOME-G2-MULTIDOMAIN-COGNITIVE-V1-'+digest({k:v['gene_digest'] for k,v in genes.items()})[:16],
 'organs':{k:v['gene_id'] for k,v in genes.items()},'promotion_state':'SHADOW_ONLY','automatic_canonical_promotion':False}
genome['genome_digest']=digest(genome)

core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)
checks={
 'logic_v2_parent_pass':lexp.get('status')=='TRAINED',
 'thinking_parent_strong':thinking_gene['summary']['mean_fresh']>=.95,
 'intelligence_parent_strong':intel_gene['summary']['mean_fresh']>=.95,
 'model_surface_only_organ_outputs':set(fit[0][0])=={'state_known','logic_accept','thinking_cautious','intelligence_robust'},
 'native_family_selection':sel.get('selected_token')==chosen['token'],
 'validation_ge_0_95':chosen['validation']>=.95,'fresh_ge_0_95':fresh>=.95,
 'logic_causal':drops['LOGIC']>=.10,'thinking_causal':drops['THINKING']>=.10,'intelligence_causal':drops['INTELLIGENCE']>=.10,
 'all_class_exact_or_near':all(v['accuracy']>=.90 for v in class_scores.values()),
 'all_domains_ge_0_90':all(v['accuracy'] is not None and v['accuracy']>=.90 for v in domain_scores.values()),
 'irrelevant_noise_invariant':noise_score==fresh,
 'four_gene_genome':len({v['gene_id'] for v in genes.values()})==4,
 'external_models_used':False,'automatic_canonical_promotion':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest')}
false_keys=['external_models_used','automatic_canonical_promotion']
passed=all(v is True for k,v in checks.items() if k not in false_keys) and all(checks[k] is False for k in false_keys)
status='PASS_SHADOW_G2_MULTIDOMAIN_COGNITIVE_COMPOSITION_TRAINING_V1' if passed else 'WITHHOLD_G2_MULTIDOMAIN_COGNITIVE_COMPOSITION_TRAINING_V1'
exp={'schema':'yado.g2.multidomain_cognitive_composition_training.experience.v1','status':'TRAINED' if passed else 'WITHHOLD',
 'fit_count':len(fit),'validation_count':len(val),'blind_count':len(blind),'trials':[{k:v for k,v in t.items() if k!='model'} for t in trials],
 'selected':cog_gene['selected_profile'],'fresh':fresh,'organ_drops':drops,'class_scores':class_scores,'domain_scores':domain_scores,'noise_score':noise_score,
 'genes':genes,'genome':genome,'checks':checks,'canonical_mutation':False,
 'semantic_boundary':'CONTROLLED COMPOSITION TRAINING. COGNITIVE MODEL SEES ONLY OUTPUTS OF THE THREE TRAINED ORGAN PORTFOLIOS, NOT DOMAIN ID OR RAW TASK FEATURES. TARGET ACTIONS ARE SYNTHETIC CURRICULUM LABELS DESIGNED TO REQUIRE ALL THREE SIGNALS. THIS IS NOT YET REAL-DATA VALIDATION.'}
exp['experience_digest']=digest(exp);EXP.parent.mkdir(parents=True,exist_ok=True);EXP.write_text(json.dumps(exp,indent=2,sort_keys=True,default=str)+'\n')
report={'schema':'yado.g2.multidomain_cognitive_composition_training.v1','status':status,'selected':cog_gene['selected_profile'],'fresh':fresh,
 'organ_drops':drops,'class_scores':class_scores,'domain_scores':domain_scores,'gene_ids':{k:v['gene_id'] for k,v in genes.items()},
 'genome_id':genome['genome_id'],'genome_digest':genome['genome_digest'],'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'MULTIDOMAIN_REAL_DATA_TRANSFER_V1' if passed else 'MULTIDOMAIN_COGNITIVE_COMPOSITION_REPAIR_V2'}
report['receipt_sha256']=digest(report);OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
print(json.dumps(report,indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
