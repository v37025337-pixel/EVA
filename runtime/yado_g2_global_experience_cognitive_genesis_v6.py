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
V5=REPO/'experience/yado-global-experience-cognitive-genesis-v5.json'
STRESS2=REPO/'experience/yado-global-experience-cognitive-stress-v2.json'
OUT=REPO/'candidates/kernel-self-generated/g2-global-experience-cognitive-genesis-v6.json'
EXP=REPO/'experience/yado-global-experience-cognitive-genesis-v6.json'

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()

corpus=load(CORPUS);v5=load(V5);stress=load(STRESS2)
if stress.get('status')!='WITHHOLD_G2_GLOBAL_EXPERIENCE_COGNITIVE_STRESS_V2':raise RuntimeError('STRESS_V2_WITHHOLD_REQUIRED')
if not ((stress.get('checks') or {}).get('logic_causal') and (stress.get('checks') or {}).get('thinking_causal') and (stress.get('checks') or {}).get('intelligence_causal')):
    raise RuntimeError('V5_ALL_ORGANS_CAUSAL_REQUIRED')
if (stress.get('action_class_slices') or {}).get('SEEK_EVIDENCE',{}).get('accuracy',1)>=.5:raise RuntimeError('EXPECTED_TERMINAL_SEEK_DEFICIT_NOT_PRESENT')

genes=v5['genes'];lg0=genes['LOGIC'];tg=genes['THINKING'];ig=genes['INTELLIGENCE']
lmodel0=lg0['model'];tmodel=tg['model'];imodel=ig['model']
rows=[r for r in (corpus.get('rows') or []) if r.get('outcome') in ('PASS','WITHHOLD')]

def bucket(r):return int(r['sha256'][:8],16)%10
def target_action(r):
    if r['outcome']=='PASS':return 'COMMIT' if not r.get('next_required_capability') else 'CONTINUE'
    return 'REVISE' if r.get('next_required_capability') else 'SEEK_EVIDENCE'
def terminal_target(r):return r['outcome']=='PASS'

def terminal_features(r):
    m=r['metrics']
    return {
      'fresh_positive':1.0 if m['fresh_positive'] else 0.0,'has_fresh':1.0 if m['has_fresh'] else 0.0,
      'ablation_positive':1.0 if m['ablation_positive'] else 0.0,'has_ablation':1.0 if m['has_ablation'] else 0.0,
      'regression_positive':1.0 if m['regression_restore_integrity_positive'] else 0.0,
      'has_regression':1.0 if m['has_regression_restore_integrity'] else 0.0,
      'safety_positive':1.0 if m['safety_positive'] else 0.0,'has_safety':1.0 if m['has_safety_evidence'] else 0.0,
      'canonical_unchanged':1.0 if m['canonical_unchanged'] else 0.0,'rollback_available':1.0 if m['rollback_available'] else 0.0,
      'promotion_applied':1.0 if m['promotion_applied'] else 0.0,'evidence_density':float(m['evidence_density'])/6.0,
      'source_receipt':1.0 if r['source_class']=='RECEIPT' else 0.0,'source_candidate':1.0 if r['source_class']=='CANDIDATE' else 0.0,
      'source_experience':1.0 if r['source_class']=='EXPERIENCE' else 0.0,'source_legacy':1.0 if r['source_class']=='LEGACY_REDERIVED' else 0.0,
      'domain_code':1.0 if r['domain']=='CODE' else 0.0,'domain_representation':1.0 if r['domain']=='REPRESENTATION' else 0.0,
      'domain_cognitive':1.0 if r['domain']=='COGNITIVE' else 0.0,'domain_execution':1.0 if r['domain']=='EXECUTION' else 0.0,
      'domain_memory':1.0 if r['domain']=='MEMORY' else 0.0,'domain_evolution':1.0 if r['domain']=='EVOLUTION' else 0.0,
    }

def balance_binary(xs,max_per=96):
    p=sorted([r for r in xs if terminal_target(r)],key=lambda r:(r['sha256'],r['path']))
    n=sorted([r for r in xs if not terminal_target(r)],key=lambda r:(r['sha256'],r['path']))
    k=min(len(p),len(n),max_per)
    return sorted(p[:k]+n[:k],key=lambda r:(r['sha256'],r['path']))

terminal=[r for r in rows if not r.get('next_required_capability')]
tf0=balance_binary([r for r in terminal if bucket(r)<=5])
tv0=balance_binary([r for r in terminal if 6<=bucket(r)<=7])
tb0=balance_binary([r for r in terminal if bucket(r)>=8])
if min(len(tf0),len(tv0),len(tb0))<10:raise RuntimeError('TERMINAL_SPLIT_TOO_SMALL:'+str([len(tf0),len(tv0),len(tb0)]))
tf=[(terminal_features(r),terminal_target(r)) for r in tf0];tv=[(terminal_features(r),terminal_target(r)) for r in tv0];tb=[(terminal_features(r),terminal_target(r)) for r in tb0]

def score_family(f,m,cases):
    if f=='CART_AXIS':return tree_acc(m,cases)
    if f=='KNN_STRATEGY':return strategy_accuracy(m,cases)
    return centroid_accuracy(m,cases)
def pred_family(f,m,x):
    if f=='CART_AXIS':return tree_predict(m,x)
    if f=='KNN_STRATEGY':return knn_predict(m,x)
    return centroid_predict(m,x)

logic_trials=[]
for d in (1,2,3,4,5):
    m=fit_tree(tf,d);logic_trials.append({'token':'CART_D'+str(d),'family':'CART_AXIS','param':d,'validation':tree_acc(m,tv),'complexity':d,'model':m})
for k in (1,3,5,7,9):
    m=fit_knn_strategy(tf,k);logic_trials.append({'token':'KNN_K'+str(k),'family':'KNN_STRATEGY','param':k,'validation':strategy_accuracy(m,tv),'complexity':k,'model':m})
for n in range(1,len(tf[0][0])+1):
    m=fit_centroid_strategy(tf,n);logic_trials.append({'token':'CENTROID_F'+str(n),'family':'CENTROID_STRATEGY','param':n,'validation':centroid_accuracy(m,tv),'complexity':n,'model':m})
eligible_logic=[t for t in logic_trials if t['validation']>=.65]
if not eligible_logic:raise RuntimeError('NO_TERMINAL_LOGIC_CANDIDATE_GE_065')
lsel=NeutralEvidenceProfileSelectorV1.select([EvidenceCandidate(token=t['token'],evidence=t['validation'],complexity=t['complexity'],risk=0,novelty=.2) for t in eligible_logic],
    complexity_penalty=.01,risk_penalty=.2,novelty_bonus=.01)
lchosen=next(t for t in eligible_logic if t['token']==lsel['selected_token'])
if lchosen['family']=='CART_AXIS':lterm=fit_tree(tf+tv,int(lchosen['param']))
elif lchosen['family']=='KNN_STRATEGY':lterm=fit_knn_strategy(tf+tv,int(lchosen['param']))
else:lterm=fit_centroid_strategy(tf+tv,int(lchosen['param']))
terminal_fresh=score_family(lchosen['family'],lterm,tb)

def general_logic_features(r):
    m=r['metrics']
    return {'has_fresh':m['has_fresh'],'fresh_positive':m['fresh_positive'],'has_ablation':m['has_ablation'],'ablation_positive':m['ablation_positive'],
      'has_regression_restore_integrity':m['has_regression_restore_integrity'],'regression_restore_integrity_positive':m['regression_restore_integrity_positive'],
      'has_safety_evidence':m['has_safety_evidence'],'safety_positive':m['safety_positive'],'canonical_unchanged':m['canonical_unchanged'],
      'rollback_available':m['rollback_available'],'promotion_applied':m['promotion_applied'],'next_present':bool(r.get('next_required_capability')),
      'source_is_receipt':r['source_class']=='RECEIPT','source_is_candidate':r['source_class']=='CANDIDATE','source_is_legacy':r['source_class']=='LEGACY_REDERIVED'}

parent_terminal=sum(bool(tree_predict(lmodel0,general_logic_features(r)))==terminal_target(r) for r in tb0)/len(tb0)
terminal_gain=terminal_fresh-parent_terminal

logic_gene={
 'schema':'yado.g2.global_experience_logic_gene.v3',
 'gene_id':'GENE-G2-GLOBAL-EXPERIENCE-LOGIC-V3-'+digest({'parent':lg0['gene_digest'],'terminal':lterm,'family':lchosen['family'],'corpus':corpus['corpus_digest']})[:16],
 'organ':'LOGIC','heritage':[lg0['gene_id'],'ALG-G2-BUDGET-ADAPTIVE-COMPOSITIONAL-LOGIC-V2'],
 'general_model':lmodel0,'terminal_expert_family':lchosen['family'],'terminal_expert_model':lterm,
 'terminal_profile':{k:lchosen[k] for k in ('token','family','param','validation','complexity')},'native_selector':lsel,
 'terminal_parent_fresh':parent_terminal,'terminal_fresh':terminal_fresh,'terminal_gain':terminal_gain,
 'promotion_state':'SHADOW_ONLY','origin':'YADO_NATIVE_TERMINAL_LOGIC_EXPERT_AUGMENTING_GLOBAL_GENERAL_LOGIC'}
logic_gene['gene_digest']=digest(logic_gene)

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
def terminal_logic(r):
    return bool(pred_family(lchosen['family'],lterm,terminal_features(r)))

GROUPS={'LOGIC':['logic_general','logic_terminal'],'THINKING':['think_accept','think_advance','think_revise','think_seek'],'INTELLIGENCE':['intel_stop','intel_retry','intel_advance']}
def organ_features(r):
    lg=bool(tree_predict(lmodel0,general_logic_features(r)));lt=terminal_logic(r);ip=str(tree_predict(imodel,intel_features(r)));tp=think_pref(r)
    return {'state_known':1.0,'logic_general':1.0 if lg else 0.0,'logic_terminal':1.0 if lt else 0.0,
      'intel_stop':1.0 if ip=='STOP' else 0.0,'intel_retry':1.0 if ip=='RETRY' else 0.0,'intel_advance':1.0 if ip=='ADVANCE' else 0.0,
      'think_accept':1.0 if tp=='ACCEPT' else 0.0,'think_advance':1.0 if tp=='ADVANCE' else 0.0,'think_revise':1.0 if tp=='REVISE' else 0.0,'think_seek':1.0 if tp=='SEEK_EVIDENCE' else 0.0}

def balance4(xs,max_per=96):
    g=defaultdict(list)
    for r in xs:g[target_action(r)].append(r)
    if len(g)<4:return []
    k=min(min(len(v),max_per) for v in g.values())
    out=[]
    for y in sorted(g):out.extend(sorted(g[y],key=lambda r:(r['sha256'],r['path']))[:k])
    return sorted(out,key=lambda r:(r['sha256'],r['path']))
cf0=balance4([r for r in rows if bucket(r)<=5]);cv0=balance4([r for r in rows if 6<=bucket(r)<=7]);cb0=balance4([r for r in rows if bucket(r)>=8])
cf=[(organ_features(r),target_action(r)) for r in cf0];cv=[(organ_features(r),target_action(r)) for r in cv0];cb=[(organ_features(r),target_action(r)) for r in cb0]

def ablate(cases,group):
    out=[];ks=GROUPS[group]
    for x,y in cases:
        z=dict(x)
        for k in ks:z[k]=0.0
        out.append((z,y))
    return out
def score(f,m,cases):
    if f=='CART_AXIS':return tree_acc(m,cases)
    if f=='KNN_STRATEGY':return strategy_accuracy(m,cases)
    return centroid_accuracy(m,cases)

ctrials=[]
for d in (1,2,3,4,5):
    m=fit_tree(cf,d);va=tree_acc(m,cv);drops={g:va-tree_acc(m,ablate(cv,g)) for g in GROUPS}
    ctrials.append({'token':'CART_D'+str(d),'family':'CART_AXIS','param':d,'validation':va,'complexity':d,'drops':drops,'model':m})
for k in (1,3,5,7,9):
    m=fit_knn_strategy(cf,k);va=strategy_accuracy(m,cv);drops={g:va-strategy_accuracy(m,ablate(cv,g)) for g in GROUPS}
    ctrials.append({'token':'KNN_K'+str(k),'family':'KNN_STRATEGY','param':k,'validation':va,'complexity':k,'drops':drops,'model':m})
for n in range(1,len(cf[0][0])+1):
    m=fit_centroid_strategy(cf,n);va=centroid_accuracy(m,cv);drops={g:va-centroid_accuracy(m,ablate(cv,g)) for g in GROUPS}
    ctrials.append({'token':'CENTROID_F'+str(n),'family':'CENTROID_STRATEGY','param':n,'validation':va,'complexity':n,'drops':drops,'model':m})
eligible=[t for t in ctrials if t['validation']>=.70 and all(t['drops'][g]>=.02 for g in GROUPS)]
if not eligible:raise RuntimeError('NO_COGNITIVE_V6_ALL_ORGAN_CANDIDATE')
csel=NeutralEvidenceProfileSelectorV1.select([EvidenceCandidate(token=t['token'],evidence=t['validation']+.5*min(t['drops'].values()),complexity=t['complexity'],risk=0,novelty=.2) for t in eligible],
    complexity_penalty=.01,risk_penalty=.2,novelty_bonus=.01)
cc=next(t for t in eligible if t['token']==csel['selected_token'])
if cc['family']=='CART_AXIS':cmodel=fit_tree(cf+cv,int(cc['param']))
elif cc['family']=='KNN_STRATEGY':cmodel=fit_knn_strategy(cf+cv,int(cc['param']))
else:cmodel=fit_centroid_strategy(cf+cv,int(cc['param']))
fresh=score(cc['family'],cmodel,cb);drops={g:fresh-score(cc['family'],cmodel,ablate(cb,g)) for g in GROUPS};restore=score(cc['family'],cmodel,cb)

def pred_c(x):return pred_family(cc['family'],cmodel,x)
class_scores={}
for y in ('COMMIT','CONTINUE','REVISE','SEEK_EVIDENCE'):
    xs=[z for z in cb if z[1]==y];class_scores[y]={'count':len(xs),'accuracy':score(cc['family'],cmodel,xs)}

core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)
db=ROOT/'yado_global_experience_cognitive_genesis_v6.sqlite'
if db.exists():db.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(db))
try:
    g=k.executive.create_goal(objective='Fail closed unknown global cognitive V6 state.',required_capabilities={'GLOBAL_EXPERIENCE_COGNITIVE_SAFETY_GATE_V6':1.0},success_criteria={'blind':1.0,'ablation':.20})
    d=k.executive.detect_deficits(g.goal_id)[0];tr=[];bl=[]
    for i in range(40):tr += [{'input':{'state_known':True,'variant':bool(i%2)},'expected':'PASS_THROUGH'},{'input':{'state_known':False,'variant':bool((i+1)%2)},'expected':'WITHHOLD'}]
    for i in range(20):bl += [{'input':{'state_known':True,'variant':bool(i%2),'nonce':i},'expected':'PASS_THROUGH'},{'input':{'state_known':False,'variant':bool((i+1)%2),'nonce':i},'expected':'WITHHOLD'}]
    gp,gs=k.executive.synthesize_best_mechanism(d.deficit_id,'CONSCIOUS_WORKSPACE',tr,min_support=2)
    gd=k.executive.evaluate_mechanism(gp.program_id,bl,min_score=1.0,min_ablation_drop=.20)
    unknown=[k.executive.execute_capability('GLOBAL_EXPERIENCE_COGNITIVE_SAFETY_GATE_V6',{'state_known':False,'variant':bool(i%2),'nonce':6000+i}) for i in range(20)]
finally:
    try:k.close()
    except Exception:pass

cg={'schema':'yado.g2.global_experience_cognitive_gene.v6',
 'gene_id':'GENE-G2-GLOBAL-EXPERIENCE-COGNITIVE-V6-'+digest({'model':cmodel,'logic':logic_gene['gene_digest'],'thinking':tg['gene_digest'],'intel':ig['gene_digest']})[:16],
 'organ':'CONSCIOUS_WORKSPACE','heritage':[genes['COGNITIVE']['gene_id'],logic_gene['gene_id'],tg['gene_id'],ig['gene_id']],
 'strategy_family':cc['family'],'selected_profile':{k:cc[k] for k in ('token','family','param','validation','complexity','drops')},'native_selector':csel,
 'model':cmodel,'fresh_blind':fresh,'individual_organ_ablation_drops':drops,'restore':restore,'class_scores':class_scores,
 'safety_program_id':gp.program_id,'safety_program_digest':gd.program_digest,'unknown_fail_closed':all(x=='WITHHOLD' for x in unknown),
 'promotion_state':'SHADOW_ONLY','origin':'YADO_NATIVE_COGNITIVE_INTEGRATION_WITH_TERMINAL_LOGIC_EXPERT'}
cg['gene_digest']=digest(cg)
genes2={'LOGIC':logic_gene,'THINKING':tg,'INTELLIGENCE':ig,'COGNITIVE':cg}
genome={'schema':'yado.g2.global_experience_cognitive_genome.v6',
 'genome_id':'GENOME-G2-GLOBAL-EXPERIENCE-COGNITIVE-V6-'+digest({k:v['gene_digest'] for k,v in genes2.items()})[:16],
 'generation':'G2_SHADOW','corpus_digest':corpus['corpus_digest'],'organs':{k:v['gene_id'] for k,v in genes2.items()},'promotion_state':'SHADOW_ONLY','automatic_canonical_promotion':False}
genome['genome_digest']=digest(genome)

checks={
 'stress_v2_terminal_failure_consumed':True,
 'terminal_logic_native_selection':lsel.get('selected_token')==lchosen['token'],
 'terminal_logic_validation_ge_0_65':lchosen['validation']>=.65,'terminal_logic_fresh_ge_0_65':terminal_fresh>=.65,
 'terminal_logic_beats_parent':terminal_gain>=.10,'new_logic_identity':logic_gene['gene_id']!=lg0['gene_id'],
 'thinking_preserved':genes2['THINKING']==tg,'intelligence_preserved':genes2['INTELLIGENCE']==ig,
 'cognitive_native_selection':csel.get('selected_token')==cc['token'],'cognitive_validation_ge_0_70':cc['validation']>=.70,
 'cognitive_fresh_ge_0_75':fresh>=.75,'logic_causal':drops['LOGIC']>=.02,'thinking_causal':drops['THINKING']>=.02,'intelligence_causal':drops['INTELLIGENCE']>=.02,
 'seek_evidence_class_ge_0_60':class_scores['SEEK_EVIDENCE']['accuracy']>=.60,'commit_class_ge_0_60':class_scores['COMMIT']['accuracy']>=.60,
 'all_class_floor_ge_0_60':all(v['accuracy']>=.60 for v in class_scores.values()),'restore_exact':restore==fresh,
 'safety_gate_commit':gd.verdict=='COMMIT','safety_gate_ablation':gd.candidate_score-gd.ablation_score>=.20,'unknown_fail_closed':cg['unknown_fail_closed'],
 'external_models_used':False,'host_written_logic_model':False,'host_selected_family':False,'automatic_canonical_promotion':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest')}
false_keys=['external_models_used','host_written_logic_model','host_selected_family','automatic_canonical_promotion']
passed=all(v is True for k,v in checks.items() if k not in false_keys) and all(checks[k] is False for k in false_keys)
status='PASS_SHADOW_G2_GLOBAL_EXPERIENCE_COGNITIVE_GENESIS_V6' if passed else 'WITHHOLD_G2_GLOBAL_EXPERIENCE_COGNITIVE_GENESIS_V6'

experience={'schema':'yado.g2.global_experience_cognitive_genesis.experience.v6','status':'TRAINED' if passed else 'WITHHOLD',
 'terminal_logic_trials':[{k:v for k,v in t.items() if k!='model'} for t in logic_trials],'terminal_logic_selected':logic_gene['terminal_profile'],
 'terminal_parent_fresh':parent_terminal,'terminal_fresh':terminal_fresh,'terminal_gain':terminal_gain,
 'cognitive_eligible_trials':[{k:v for k,v in t.items() if k!='model'} for t in eligible],'cognitive_selected':cg['selected_profile'],
 'fresh':fresh,'drops':drops,'class_scores':class_scores,'safety_gate':asdict(gd),'genes':genes2,'genome':genome,'checks':checks,'canonical_mutation':False,
 'semantic_boundary':'V6 ADDS A YADO-NATIVE TERMINAL LOGIC EXPERT FOR NO-NEXT STATES, PRESERVES V3 THINKING AND V2 INTELLIGENCE, AND RELEARNS AN ORGAN-ONLY COGNITIVE STRATEGY. BOTH TERMINAL LOGIC AND COGNITIVE FAMILY SELECTION ARE NATIVE BOUNDED SEARCHES. PASS REQUIRES TERMINAL IMPROVEMENT, ALL THREE ORGAN CAUSALITY, ACTION-CLASS FLOORS AND UNKNOWN FAIL-CLOSED SAFETY.'}
experience['experience_digest']=digest(experience);EXP.parent.mkdir(parents=True,exist_ok=True);EXP.write_text(json.dumps(experience,indent=2,sort_keys=True)+'\n')
report={'schema':'yado.g2.global_experience_cognitive_genesis.v6','status':status,'terminal_logic_selected':logic_gene['terminal_profile'],
 'terminal_parent_fresh':parent_terminal,'terminal_fresh':terminal_fresh,'terminal_gain':terminal_gain,'cognitive_selected':cg['selected_profile'],
 'fresh':fresh,'individual_organ_drops':drops,'class_scores':class_scores,'safety_gate':asdict(gd),'gene_ids':{k:v['gene_id'] for k,v in genes2.items()},
 'genome_id':genome['genome_id'],'genome_digest':genome['genome_digest'],'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'GLOBAL_EXPERIENCE_COGNITIVE_STRESS_V3' if passed else 'GLOBAL_EXPERIENCE_TERMINAL_LOGIC_REPAIR_V2',
 'semantic_boundary':experience['semantic_boundary']}
report['receipt_sha256']=digest(report);OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':status,'terminal':{'parent':parent_terminal,'fresh':terminal_fresh,'gain':terminal_gain,'selected':logic_gene['terminal_profile']},
 'cognitive':{'fresh':fresh,'drops':drops,'class_scores':class_scores,'selected':cg['selected_profile']},'gene_ids':report['gene_ids'],'genome_id':genome['genome_id'],
 'next_required_capability':report['next_required_capability'],'receipt_sha256':report['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
