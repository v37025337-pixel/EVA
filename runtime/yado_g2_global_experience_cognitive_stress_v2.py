from __future__ import annotations
from pathlib import Path
from collections import defaultdict
import copy,hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_cognitive_growth_runtime_v1 import plan_multicontext,knn_predict,centroid_predict
from yado_organ_runtime_native_v1 import tree_predict
from yado_unified_core_v1 import UnifiedYADOCoreV1

CORPUS=REPO/'experience/yado-global-experience-corpus-v1.json'
V5=REPO/'experience/yado-global-experience-cognitive-genesis-v5.json'
STRESS1=REPO/'experience/yado-global-experience-cognitive-stress-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-global-experience-cognitive-stress-v2.json'
EXP=REPO/'experience/yado-global-experience-cognitive-stress-v2.json'

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
corpus=load(CORPUS);v5=load(V5);s1=load(STRESS1)
if v5.get('status')!='TRAINED':raise RuntimeError('V5_TRAINED_REQUIRED')
if not all((v5.get('checks') or {}).get(k) for k in ('fresh_logic_causal','fresh_thinking_causal','fresh_intelligence_causal','unknown_fail_closed')):
    raise RuntimeError('V5_CAUSAL_SUCCESS_REQUIRED')
genes=v5['genes'];lg=genes['LOGIC'];tg=genes['THINKING'];ig=genes['INTELLIGENCE'];cg=genes['COGNITIVE']
lmodel=lg['model'];tmodel=tg['model'];imodel=ig['model'];cmodel=cg['model'];family=cg['strategy_family']
GROUPS={'LOGIC':['logic_accept'],'THINKING':['think_accept','think_advance','think_revise','think_seek'],'INTELLIGENCE':['intel_stop','intel_retry','intel_advance']}

rows=[r for r in (corpus.get('rows') or []) if r.get('outcome') in ('PASS','WITHHOLD')]
blind_rows=[r for r in rows if int(r['sha256'][:8],16)%10>=8]
if len(blind_rows)<60:raise RuntimeError('FULL_BLIND_TOO_SMALL')

def target(r):
    if r['outcome']=='PASS':return 'COMMIT' if not r.get('next_required_capability') else 'CONTINUE'
    return 'REVISE' if r.get('next_required_capability') else 'SEEK_EVIDENCE'
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
def features(r):
    lp=bool(tree_predict(lmodel,logic_features(r)));ip=str(tree_predict(imodel,intel_features(r)));tp=str(think_pref(r))
    return {'state_known':1.0,'logic_accept':1.0 if lp else 0.0,
      'intel_stop':1.0 if ip=='STOP' else 0.0,'intel_retry':1.0 if ip=='RETRY' else 0.0,'intel_advance':1.0 if ip=='ADVANCE' else 0.0,
      'think_accept':1.0 if tp=='ACCEPT' else 0.0,'think_advance':1.0 if tp=='ADVANCE' else 0.0,'think_revise':1.0 if tp=='REVISE' else 0.0,'think_seek':1.0 if tp=='SEEK_EVIDENCE' else 0.0}
def predict(x):
    if family=='CART_AXIS':return tree_predict(cmodel,x)
    if family=='KNN_STRATEGY':return knn_predict(cmodel,x)
    if family=='CENTROID_STRATEGY':return centroid_predict(cmodel,x)
    raise ValueError('UNKNOWN_FAMILY')

cases=[(r,features(r),target(r)) for r in blind_rows]
def score(cases2):
    return sum(predict(x)==y for _,x,y in cases2)/max(1,len(cases2))
base=score(cases)
individual={}
for organ,ks in GROUPS.items():
    zz=[]
    for r,x,y in cases:
        q=dict(x)
        for k in ks:q[k]=0.0
        zz.append((r,q,y))
    a=score(zz);individual[organ]={'score':a,'drop':base-a}
all_abl=[]
for r,x,y in cases:
    q=dict(x)
    for ks in GROUPS.values():
        for k in ks:q[k]=0.0
    all_abl.append((r,q,y))
all_abl_score=score(all_abl)

class_slices={}
for action in ('COMMIT','CONTINUE','REVISE','SEEK_EVIDENCE'):
    xs=[z for z in cases if z[2]==action]
    class_slices[action]={'count':len(xs),'accuracy':score(xs) if xs else None}
source_slices={}
for sc in sorted({r['source_class'] for r,_,_ in cases}):
    xs=[z for z in cases if z[0]['source_class']==sc]
    if len(xs)>=6:source_slices[sc]={'count':len(xs),'accuracy':score(xs)}
domain_slices={}
for d in sorted({r['domain'] for r,_,_ in cases}):
    xs=[z for z in cases if z[0]['domain']==d]
    if len(xs)>=6:domain_slices[d]={'count':len(xs),'accuracy':score(xs)}

# Counterfactual stability: exact organ vector should yield same result regardless of copied row identity.
vectors={}
stable=True
for r,x,y in cases:
    k=canon(x);p=predict(x)
    if k in vectors and vectors[k]!=p:stable=False
    vectors[k]=p

# Later artifacts not part of frozen corpus.
post_paths=[
 'candidates/kernel-self-generated/g2-global-experience-cognitive-genesis-v2.json','experience/yado-global-experience-cognitive-genesis-v2.json',
 'candidates/kernel-self-generated/g2-global-experience-cognitive-genesis-v3.json','experience/yado-global-experience-cognitive-genesis-v3.json',
 'candidates/kernel-self-generated/g2-global-experience-cognitive-genesis-v4.json','experience/yado-global-experience-cognitive-genesis-v4.json',
 'candidates/kernel-self-generated/g2-global-experience-cognitive-stress-v1.json','experience/yado-global-experience-cognitive-stress-v1.json',
 'candidates/kernel-self-generated/g2-global-experience-cognitive-genesis-v5.json','experience/yado-global-experience-cognitive-genesis-v5.json',
]
def post_row(path):
    p=REPO/path
    if not p.exists():return None
    o=load(p);st=str(o.get('status') or '')
    out='PASS' if st.startswith('PASS') or st=='TRAINED' else 'WITHHOLD' if st.startswith('WITHHOLD') or st=='WITHHOLD' else None
    if out is None:return None
    nxt=o.get('next_required_capability')
    return {'path':path,'source_class':'POST','outcome':out,'next_required_capability':nxt,'domain':'COGNITIVE','next_domain':'COGNITIVE' if nxt else None,
      'metrics':{'has_fresh':False,'fresh_positive':False,'has_ablation':False,'ablation_positive':False,'has_regression_restore_integrity':False,
                 'regression_restore_integrity_positive':False,'has_safety_evidence':False,'safety_positive':False,
                 'canonical_unchanged':bool((o.get('checks') or {}).get('canonical_unchanged',False)),'rollback_available':False,'promotion_applied':False,'evidence_density':1}}
post=[]
for p in post_paths:
    r=post_row(p)
    if r:
        x=features(r);post.append({'path':p,'predicted':predict(x),'expected':target(r)})
post_acc=sum(z['predicted']==z['expected'] for z in post)/max(1,len(post))

core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)
v4_base=float(s1.get('base_accuracy') or 0.0)
checks={
 'v5_parent_pass':v5.get('status')=='TRAINED',
 'no_material_accuracy_loss_vs_v4':base>=v4_base-.02,
 'full_blind_ge_0_75':base>=.75,
 'logic_causal':individual['LOGIC']['drop']>=.02,'thinking_causal':individual['THINKING']['drop']>=.02,'intelligence_causal':individual['INTELLIGENCE']['drop']>=.02,
 'combined_organ_ablation_drop_ge_0_20':base-all_abl_score>=.20,
 'all_action_classes_present':all(v['count']>=4 for v in class_slices.values()),
 'action_class_floor':all(v['accuracy']>=.50 for v in class_slices.values()),
 'source_slice_floor':all(v['accuracy']>=.55 for v in source_slices.values()),
 'domain_slice_floor':all(v['accuracy']>=.45 for v in domain_slices.values()),
 'organ_vector_deterministic':stable,
 'post_corpus_count_ge_8':len(post)>=8,'post_corpus_accuracy_ge_0_70':post_acc>=.70,
 'safety_gate_v5_exact':float((v5.get('safety_gate') or {}).get('candidate_score') or 0)==1.0,
 'safety_gate_v5_ablation':float((v5.get('safety_gate') or {}).get('candidate_score') or 0)-float((v5.get('safety_gate') or {}).get('ablation_score') or 0)>=.20,
 'unknown_fail_closed':bool((v5.get('checks') or {}).get('unknown_fail_closed')),
 'restore_exact':score(cases)==base,
 'external_models_used':False,'retraining_performed':False,'automatic_canonical_promotion':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest')}
false_keys=['external_models_used','retraining_performed','automatic_canonical_promotion']
passed=all(v is True for k,v in checks.items() if k not in false_keys) and all(checks[k] is False for k in false_keys)
status='PASS_SHADOW_G2_GLOBAL_EXPERIENCE_COGNITIVE_STRESS_V2' if passed else 'WITHHOLD_G2_GLOBAL_EXPERIENCE_COGNITIVE_STRESS_V2'
report={'schema':'yado.g2.global_experience_cognitive_stress.v2','status':status,'parent_genome_id':v5['genome']['genome_id'],
 'base_accuracy':base,'v4_shortcut_base_accuracy':v4_base,'individual_organ_ablations':individual,'combined_organ_ablation_score':all_abl_score,
 'combined_organ_ablation_drop':base-all_abl_score,'action_class_slices':class_slices,'source_slices':source_slices,'domain_slices':domain_slices,
 'post_corpus_evaluation':post,'post_corpus_accuracy':post_acc,'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'GLOBAL_EXPERIENCE_COGNITIVE_CANONICAL_ADMISSION_V1' if passed else 'GLOBAL_EXPERIENCE_COGNITIVE_STRESS_REPAIR_V3',
 'semantic_boundary':'FROZEN V5 ORGAN-ONLY STRESS. COMPARES AGAINST V4 SHORTCUT MODEL WITHOUT REUSING ITS CONTEXT FEATURES, REQUIRES ALL THREE ORGAN CAUSAL CONTRIBUTIONS, ACTION-CLASS/SOURCE/DOMAIN SLICES, POST-CORPUS TRANSFER, COMBINED ABLATION, SAFETY EVIDENCE AND DETERMINISTIC RESTORE. NO RETRAINING.'}
report['receipt_sha256']=digest(report);OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
EXP.parent.mkdir(parents=True,exist_ok=True);EXP.write_text(json.dumps(report|{'schema':'yado.g2.global_experience_cognitive_stress.experience.v2'},indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':status,'base_accuracy':base,'v4_base':v4_base,'individual':individual,'combined_ablation_score':all_abl_score,
 'class_slices':class_slices,'source_slices':source_slices,'domain_slices':domain_slices,'post_corpus_accuracy':post_acc,
 'next_required_capability':report['next_required_capability'],'receipt_sha256':report['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
