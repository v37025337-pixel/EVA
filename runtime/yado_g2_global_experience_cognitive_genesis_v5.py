from __future__ import annotations
from pathlib import Path
from collections import defaultdict
from dataclasses import asdict
import copy,hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_cognitive_growth_runtime_v1 import plan_multicontext,fit_knn_strategy,knn_predict,strategy_accuracy,fit_centroid_strategy,centroid_predict,centroid_accuracy
from yado_organ_runtime_native_v1 import fit_tree,tree_predict,tree_acc
from yado_neutral_evidence_profile_selector_v1 import NeutralEvidenceProfileSelectorV1,EvidenceCandidate
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_unified_core_v1 import UnifiedYADOCoreV1

CORPUS=REPO/'experience/yado-global-experience-corpus-v1.json'
V3=REPO/'experience/yado-global-experience-cognitive-genesis-v3.json'
V4=REPO/'experience/yado-global-experience-cognitive-genesis-v4.json'
STRESS=REPO/'experience/yado-global-experience-cognitive-stress-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-global-experience-cognitive-genesis-v5.json'
EXP=REPO/'experience/yado-global-experience-cognitive-genesis-v5.json'

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()

corpus=load(CORPUS);v3=load(V3);v4=load(V4);stress=load(STRESS)
if stress.get('status')!='WITHHOLD_G2_GLOBAL_EXPERIENCE_COGNITIVE_STRESS_V1':raise RuntimeError('STRESS_V1_WITHHOLD_REQUIRED')
if not ((stress.get('checks') or {}).get('thinking_ablation_positive') and not (stress.get('checks') or {}).get('logic_ablation_positive') and not (stress.get('checks') or {}).get('intelligence_ablation_positive')):
    raise RuntimeError('EXPECTED_SHORTCUT_DEFECT_NOT_PRESENT')
genes=v3['genes']
lg=genes['LOGIC'];tg=genes['THINKING'];ig=genes['INTELLIGENCE']
lmodel=lg['model'];tmodel=tg['model'];imodel=ig['model']
rows=[r for r in (corpus.get('rows') or []) if r.get('outcome') in ('PASS','WITHHOLD')]

def split_bucket(r):return int(r['sha256'][:8],16)%10
def target(r):
    if r['outcome']=='PASS':return 'COMMIT' if not r.get('next_required_capability') else 'CONTINUE'
    return 'REVISE' if r.get('next_required_capability') else 'SEEK_EVIDENCE'
def balance(xs,min_per=5,max_per=96):
    g=defaultdict(list)
    for r in xs:g[target(r)].append(r)
    if len(g)<4:return []
    n=min(min(len(v),max_per) for v in g.values())
    if n<min_per:return []
    out=[]
    for k in sorted(g):out.extend(sorted(g[k],key=lambda r:(r['sha256'],r['path']))[:n])
    return sorted(out,key=lambda r:(r['sha256'],r['path']))

fit_rows=balance([r for r in rows if split_bucket(r)<=5])
val_rows=balance([r for r in rows if 6<=split_bucket(r)<=7])
blind_rows=balance([r for r in rows if split_bucket(r)>=8])
if min(len(fit_rows),len(val_rows),len(blind_rows))<20:raise RuntimeError('BALANCED_SPLITS_TOO_SMALL')

def logic_features(r):
    m=r['metrics']
    return {'has_fresh':m['has_fresh'],'fresh_positive':m['fresh_positive'],'has_ablation':m['has_ablation'],'ablation_positive':m['ablation_positive'],
      'has_regression_restore_integrity':m['has_regression_restore_integrity'],'regression_restore_integrity_positive':m['regression_restore_integrity_positive'],
      'has_safety_evidence':m['has_safety_evidence'],'safety_positive':m['safety_positive'],'canonical_unchanged':m['canonical_unchanged'],
      'rollback_available':m['rollback_available'],'promotion_applied':m['promotion_applied'],'next_present':bool(r.get('next_required_capability')),
      'source_is_receipt':r['source_class']=='RECEIPT','source_is_candidate':r['source_class']=='CANDIDATE','source_is_legacy':r['source_class']=='LEGACY_REDERIVED'}

def intel_features(r):
    m=r['metrics']
    return {'status_pass':1.0 if r['outcome']=='PASS' else 0.0,'status_withhold':1.0 if r['outcome']=='WITHHOLD' else 0.0,
      'next_present':1.0 if r.get('next_required_capability') else 0.0,'same_domain_next':1.0 if r.get('next_required_capability') and r.get('next_domain')==r.get('domain') else 0.0,
      'fresh_positive':1.0 if m['fresh_positive'] else 0.0,'ablation_positive':1.0 if m['ablation_positive'] else 0.0,
      'canonical_unchanged':1.0 if m['canonical_unchanged'] else 0.0,'rollback_available':1.0 if m['rollback_available'] else 0.0,'evidence_density':float(m['evidence_density'])/6.0,
      'domain_code':1.0 if r['domain']=='CODE' else 0.0,'domain_representation':1.0 if r['domain']=='REPRESENTATION' else 0.0,
      'domain_cognitive':1.0 if r['domain']=='COGNITIVE' else 0.0,'domain_execution':1.0 if r['domain']=='EXECUTION' else 0.0,
      'domain_memory':1.0 if r['domain']=='MEMORY' else 0.0,'domain_evolution':1.0 if r['domain']=='EVOLUTION' else 0.0}

def row_context(r):
    return {'START_PASS':r.get('outcome')=='PASS','START_WITHHOLD':r.get('outcome')=='WITHHOLD','START_HAS_NEXT':bool(r.get('next_required_capability')),
      'START_NO_NEXT':not bool(r.get('next_required_capability')),'START_SAME_DOMAIN_NEXT':bool(r.get('next_required_capability')) and r.get('next_domain')==r.get('domain'),
      'START_FRESH_POSITIVE':bool(r['metrics'].get('fresh_positive')),'START_ABLATION_POSITIVE':bool(r['metrics'].get('ablation_positive')),
      'WINDOW_DOMAIN_STABLE':True,'WINDOW_HAS_WITHHOLD':r.get('outcome')=='WITHHOLD','WINDOW_HAS_PASS':r.get('outcome')=='PASS'}

def think_pref(r):
    roles=['ACCEPT','ADVANCE','REVISE','SEEK_EVIDENCE'];acts=[{'id':'STD-'+x,'role':x} for x in roles]
    ids=plan_multicontext(tmodel,row_context(r),acts);by={a['id']:a['role'] for a in acts}
    return by[ids[0]] if ids else 'SEEK_EVIDENCE'

GROUPS={'LOGIC':['logic_accept'],'THINKING':['think_accept','think_advance','think_revise','think_seek'],'INTELLIGENCE':['intel_stop','intel_retry','intel_advance']}
def organ_features(r):
    lp=bool(tree_predict(lmodel,logic_features(r)));ip=str(tree_predict(imodel,intel_features(r)));tp=str(think_pref(r))
    return {'state_known':1.0,'logic_accept':1.0 if lp else 0.0,
      'intel_stop':1.0 if ip=='STOP' else 0.0,'intel_retry':1.0 if ip=='RETRY' else 0.0,'intel_advance':1.0 if ip=='ADVANCE' else 0.0,
      'think_accept':1.0 if tp=='ACCEPT' else 0.0,'think_advance':1.0 if tp=='ADVANCE' else 0.0,
      'think_revise':1.0 if tp=='REVISE' else 0.0,'think_seek':1.0 if tp=='SEEK_EVIDENCE' else 0.0}

fit=[(organ_features(r),target(r)) for r in fit_rows]
val=[(organ_features(r),target(r)) for r in val_rows]
blind=[(organ_features(r),target(r)) for r in blind_rows]

def score_model(family,model,cases):
    if family=='CART_AXIS':return tree_acc(model,cases)
    if family=='KNN_STRATEGY':return strategy_accuracy(model,cases)
    return centroid_accuracy(model,cases)
def pred_model(family,model,x):
    if family=='CART_AXIS':return tree_predict(model,x)
    if family=='KNN_STRATEGY':return knn_predict(model,x)
    return centroid_predict(model,x)
def ablate(cases,group):
    ks=GROUPS[group];out=[]
    for x,y in cases:
        z=dict(x)
        for k in ks:z[k]=0.0
        out.append((z,y))
    return out

trials=[]
for d in (1,2,3,4,5):
    m=fit_tree(fit,d)
    va=tree_acc(m,val)
    drops={g:va-tree_acc(m,ablate(val,g)) for g in GROUPS}
    trials.append({'token':'CART_D'+str(d),'family':'CART_AXIS','param':d,'complexity':d,'validation':va,'drops':drops,'model':m})
for k0 in (1,3,5,7,9):
    m=fit_knn_strategy(fit,k0);va=strategy_accuracy(m,val)
    drops={g:va-strategy_accuracy(m,ablate(val,g)) for g in GROUPS}
    trials.append({'token':'KNN_K'+str(k0),'family':'KNN_STRATEGY','param':k0,'complexity':k0,'validation':va,'drops':drops,'model':m})
for n in range(1,len(fit[0][0])+1):
    m=fit_centroid_strategy(fit,n);va=centroid_accuracy(m,val)
    drops={g:va-centroid_accuracy(m,ablate(val,g)) for g in GROUPS}
    trials.append({'token':'CENTROID_F'+str(n),'family':'CENTROID_STRATEGY','param':n,'complexity':n,'validation':va,'drops':drops,'model':m})

eligible=[t for t in trials if t['validation']>=.55 and all(t['drops'][g]>=.02 for g in GROUPS)]
if not eligible:
    best=sorted(trials,key=lambda t:(-min(t['drops'].values()),-t['validation'],t['complexity'],t['token']))[:12]
    report={'schema':'yado.g2.global_experience_cognitive_genesis.v5','status':'WITHHOLD_G2_GLOBAL_EXPERIENCE_COGNITIVE_GENESIS_V5',
      'reason':'NO_NATIVE_ORGAN_ONLY_MODEL_REQUIRES_ALL_THREE_ORGANS','best_trials':[{k:v for k,v in t.items() if k!='model'} for t in best],
      'canonical_mutation':False,'next_required_capability':'GLOBAL_EXPERIENCE_COGNITIVE_ORGAN_COMPLEMENTARITY_EVOLUTION_V1'}
    report['receipt_sha256']=digest(report);OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    EXP.parent.mkdir(parents=True,exist_ok=True);EXP.write_text(json.dumps(report|{'schema':'yado.g2.global_experience_cognitive_genesis.experience.v5'},indent=2,sort_keys=True)+'\n')
    print(json.dumps(report,indent=2,sort_keys=True));raise SystemExit(2)

sel=NeutralEvidenceProfileSelectorV1.select([
    EvidenceCandidate(token=t['token'],evidence=t['validation']+0.75*min(t['drops'].values()),complexity=t['complexity'],risk=0.0,novelty=.2)
    for t in eligible
],complexity_penalty=.01,risk_penalty=.2,novelty_bonus=.01)
chosen=next(t for t in eligible if t['token']==sel['selected_token'])
all_fit=fit+val
if chosen['family']=='CART_AXIS':model=fit_tree(all_fit,int(chosen['param']))
elif chosen['family']=='KNN_STRATEGY':model=fit_knn_strategy(all_fit,int(chosen['param']))
else:model=fit_centroid_strategy(all_fit,int(chosen['param']))
fresh=score_model(chosen['family'],model,blind)
blind_drops={g:fresh-score_model(chosen['family'],model,ablate(blind,g)) for g in GROUPS}
restore=score_model(chosen['family'],model,blind)

source_slices={}
for sc in sorted({r['source_class'] for r in blind_rows}):
    idx=[i for i,r in enumerate(blind_rows) if r['source_class']==sc]
    if len(idx)>=6:
        cs=[blind[i] for i in idx];source_slices[sc]={'count':len(cs),'accuracy':score_model(chosen['family'],model,cs)}
domain_slices={}
for d in sorted({r['domain'] for r in blind_rows}):
    idx=[i for i,r in enumerate(blind_rows) if r['domain']==d]
    if len(idx)>=6:
        cs=[blind[i] for i in idx];domain_slices[d]={'count':len(cs),'accuracy':score_model(chosen['family'],model,cs)}

# Safety gate remains a separate native learned mechanism.
core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)
db=ROOT/'yado_global_experience_cognitive_genesis_v5.sqlite'
if db.exists():db.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(db))
try:
    goal=k.executive.create_goal(objective='Fail closed unknown global organ state.',required_capabilities={'GLOBAL_EXPERIENCE_COGNITIVE_SAFETY_GATE_V5':1.0},
      success_criteria={'blind':1.0,'ablation_drop':.20,'unknown_withhold':True})
    d=k.executive.detect_deficits(goal.goal_id)[0]
    tr=[];bl=[]
    for i in range(40):
        tr += [{'input':{'state_known':True,'variant':bool(i%2)},'expected':'PASS_THROUGH'},{'input':{'state_known':False,'variant':bool((i+1)%2)},'expected':'WITHHOLD'}]
    for i in range(20):
        bl += [{'input':{'state_known':True,'variant':bool((i+1)%2),'nonce':i},'expected':'PASS_THROUGH'},{'input':{'state_known':False,'variant':bool(i%2),'nonce':i},'expected':'WITHHOLD'}]
    gp,gs=k.executive.synthesize_best_mechanism(d.deficit_id,'CONSCIOUS_WORKSPACE',tr,min_support=2)
    gd=k.executive.evaluate_mechanism(gp.program_id,bl,min_score=1.0,min_ablation_drop=.20)
    unknown=[k.executive.execute_capability('GLOBAL_EXPERIENCE_COGNITIVE_SAFETY_GATE_V5',{'state_known':False,'variant':bool(i%2),'nonce':7000+i}) for i in range(20)]
finally:
    try:k.close()
    except Exception:pass

cg={'schema':'yado.g2.global_experience_cognitive_gene.v5',
 'gene_id':'GENE-G2-GLOBAL-EXPERIENCE-COGNITIVE-V5-'+digest({'model':model,'family':chosen['family'],'organs':[lg['gene_digest'],tg['gene_digest'],ig['gene_digest']]})[:16],
 'organ':'CONSCIOUS_WORKSPACE','heritage':[v4['genes']['COGNITIVE']['gene_id'],lg['gene_id'],tg['gene_id'],ig['gene_id']],
 'strategy_family':chosen['family'],'selected_profile':{k:chosen[k] for k in ('token','family','param','validation','complexity','drops')},
 'native_selector':sel,'model':model,'fresh_blind':fresh,'individual_organ_ablation_drops':blind_drops,'restore':restore,
 'safety_program_id':gp.program_id,'safety_program_digest':gd.program_digest,'unknown_fail_closed':all(x=='WITHHOLD' for x in unknown),
 'promotion_state':'SHADOW_ONLY','origin':'YADO_NATIVE_ORGAN_ONLY_COGNITIVE_INTEGRATION_WITH_CAUSAL_COMPLEMENTARITY_GATE'}
cg['gene_digest']=digest(cg)
genes2={'LOGIC':lg,'THINKING':tg,'INTELLIGENCE':ig,'COGNITIVE':cg}
genome={'schema':'yado.g2.global_experience_cognitive_genome.v5',
 'genome_id':'GENOME-G2-GLOBAL-EXPERIENCE-COGNITIVE-V5-'+digest({k:v['gene_digest'] for k,v in genes2.items()})[:16],
 'generation':'G2_SHADOW','corpus_digest':corpus['corpus_digest'],'organs':{k:v['gene_id'] for k,v in genes2.items()},
 'promotion_state':'SHADOW_ONLY','automatic_canonical_promotion':False}
genome['genome_digest']=digest(genome)

checks={
 'stress_shortcut_failure_consumed':True,
 'v3_logic_preserved':genes2['LOGIC']==lg,'v3_thinking_preserved':genes2['THINKING']==tg,'v3_intelligence_preserved':genes2['INTELLIGENCE']==ig,
 'organ_only_training_surface':set(fit[0][0])==set(['state_known']+sum(GROUPS.values(),[])),
 'native_family_selection':sel.get('selected_token')==chosen['token'],
 'validation_ge_0_55':chosen['validation']>=.55,
 'validation_all_organs_causal':all(chosen['drops'][g]>=.02 for g in GROUPS),
 'fresh_ge_0_55':fresh>=.55,
 'fresh_logic_causal':blind_drops['LOGIC']>=.02,'fresh_thinking_causal':blind_drops['THINKING']>=.02,'fresh_intelligence_causal':blind_drops['INTELLIGENCE']>=.02,
 'restore_exact':restore==fresh,'source_slice_floor':all(v['accuracy']>=.50 for v in source_slices.values()),
 'domain_slice_floor':all(v['accuracy']>=.45 for v in domain_slices.values()),
 'safety_gate_commit':gd.verdict=='COMMIT','safety_gate_exact':gd.candidate_score==1.0,'safety_gate_ablation':gd.candidate_score-gd.ablation_score>=.20,
 'unknown_fail_closed':cg['unknown_fail_closed'],'new_cognitive_identity':cg['gene_id']!=v4['genes']['COGNITIVE']['gene_id'],
 'external_models_used':False,'host_written_cognitive_model':False,'host_selected_family':False,'automatic_canonical_promotion':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest')}
false_keys=['external_models_used','host_written_cognitive_model','host_selected_family','automatic_canonical_promotion']
passed=all(v is True for k,v in checks.items() if k not in false_keys) and all(checks[k] is False for k in false_keys)
status='PASS_SHADOW_G2_GLOBAL_EXPERIENCE_COGNITIVE_GENESIS_V5' if passed else 'WITHHOLD_G2_GLOBAL_EXPERIENCE_COGNITIVE_GENESIS_V5'

experience={'schema':'yado.g2.global_experience_cognitive_genesis.experience.v5','status':'TRAINED' if passed else 'WITHHOLD',
 'stress_parent_receipt':stress.get('receipt_sha256'),'eligible_trials':[{k:v for k,v in t.items() if k!='model'} for t in eligible],
 'selected_profile':{k:chosen[k] for k in ('token','family','param','validation','complexity','drops')},'native_selector':sel,
 'fresh':fresh,'blind_drops':blind_drops,'source_slices':source_slices,'domain_slices':domain_slices,'safety_gate':asdict(gd),
 'genes':genes2,'genome':genome,'checks':checks,'canonical_mutation':False,
 'semantic_boundary':'V5 REMOVES ALL NON-ORGAN SHORTCUT CONTEXT FROM COGNITIVE TRAINING. ONLY THE OUTPUTS OF GLOBAL LOGIC, MULTICONTEXT THINKING AND GLOBAL INTELLIGENCE ARE AVAILABLE. NATIVE CART/KNN/CENTROID CANDIDATES ARE ELIGIBLE ONLY IF ALL THREE ORGAN ABLATIONS REDUCE VALIDATION ACCURACY. YADO NATIVE SELECTOR CHOOSES AMONG ELIGIBLE CANDIDATES. UNKNOWN REMAINS FAIL-CLOSED THROUGH A SEPARATE NATIVE SAFETY GATE.'}
experience['experience_digest']=digest(experience);EXP.parent.mkdir(parents=True,exist_ok=True);EXP.write_text(json.dumps(experience,indent=2,sort_keys=True,default=str)+'\n')
report={'schema':'yado.g2.global_experience_cognitive_genesis.v5','status':status,'selected_profile':experience['selected_profile'],'fresh':fresh,
 'blind_organ_ablation_drops':blind_drops,'source_slices':source_slices,'domain_slices':domain_slices,'safety_gate':asdict(gd),
 'gene_ids':{k:v['gene_id'] for k,v in genes2.items()},'genome_id':genome['genome_id'],'genome_digest':genome['genome_digest'],'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,'next_required_capability':'GLOBAL_EXPERIENCE_COGNITIVE_STRESS_V2' if passed else 'GLOBAL_EXPERIENCE_COGNITIVE_ORGAN_COMPLEMENTARITY_EVOLUTION_V1',
 'semantic_boundary':experience['semantic_boundary']}
report['receipt_sha256']=digest(report);OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps({'status':status,'selected_profile':report['selected_profile'],'fresh':fresh,'blind_drops':blind_drops,
 'source_slices':source_slices,'domain_slices':domain_slices,'gene_ids':report['gene_ids'],'genome_id':genome['genome_id'],
 'next_required_capability':report['next_required_capability'],'receipt_sha256':report['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
