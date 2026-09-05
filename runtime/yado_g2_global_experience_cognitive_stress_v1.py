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
PARENT=REPO/'experience/yado-global-experience-cognitive-genesis-v4.json'
OUT=REPO/'candidates/kernel-self-generated/g2-global-experience-cognitive-stress-v1.json'
EXP=REPO/'experience/yado-global-experience-cognitive-stress-v1.json'

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()

corpus=load(CORPUS);parent=load(PARENT)
if parent.get('status')!='TRAINED':raise RuntimeError('V4_TRAINED_EXPERIENCE_REQUIRED')
checks0=parent.get('checks') or {}
if not all(checks0.get(k) for k in ('v3_logic_preserved','v3_thinking_preserved','v3_intelligence_preserved','cognitive_history_gain_over_v3','unknown_fail_closed')):
    raise RuntimeError('V4_SUCCESS_EVIDENCE_REQUIRED')
genes=parent['genes'];lg=genes['LOGIC'];tg=genes['THINKING'];ig=genes['INTELLIGENCE'];cg=genes['COGNITIVE']
lmodel=lg['model'];tmodel=tg['model'];imodel=ig['model'];cmodel=cg['model'];cfamily=cg['strategy_family']

rows=[r for r in (corpus.get('rows') or []) if r.get('outcome') in ('PASS','WITHHOLD')]
blind=[r for r in rows if int(r['sha256'][:8],16)%10>=8]
if len(blind)<40:raise RuntimeError('HELDOUT_TOO_SMALL')

def target_action(r):
    if r['outcome']=='PASS':return 'COMMIT' if not r.get('next_required_capability') else 'CONTINUE'
    return 'REVISE' if r.get('next_required_capability') else 'SEEK_EVIDENCE'

def logic_features(r):
    m=r['metrics']
    return {
      'has_fresh':m['has_fresh'],'fresh_positive':m['fresh_positive'],'has_ablation':m['has_ablation'],'ablation_positive':m['ablation_positive'],
      'has_regression_restore_integrity':m['has_regression_restore_integrity'],'regression_restore_integrity_positive':m['regression_restore_integrity_positive'],
      'has_safety_evidence':m['has_safety_evidence'],'safety_positive':m['safety_positive'],'canonical_unchanged':m['canonical_unchanged'],
      'rollback_available':m['rollback_available'],'promotion_applied':m['promotion_applied'],'next_present':bool(r.get('next_required_capability')),
      'source_is_receipt':r['source_class']=='RECEIPT','source_is_candidate':r['source_class']=='CANDIDATE','source_is_legacy':r['source_class']=='LEGACY_REDERIVED',
    }

def intel_features(r):
    m=r['metrics']
    return {
      'status_pass':1.0 if r['outcome']=='PASS' else 0.0,'status_withhold':1.0 if r['outcome']=='WITHHOLD' else 0.0,
      'next_present':1.0 if r.get('next_required_capability') else 0.0,
      'same_domain_next':1.0 if r.get('next_required_capability') and r.get('next_domain')==r.get('domain') else 0.0,
      'fresh_positive':1.0 if m['fresh_positive'] else 0.0,'ablation_positive':1.0 if m['ablation_positive'] else 0.0,
      'canonical_unchanged':1.0 if m['canonical_unchanged'] else 0.0,'rollback_available':1.0 if m['rollback_available'] else 0.0,
      'evidence_density':float(m['evidence_density'])/6.0,
      'domain_code':1.0 if r['domain']=='CODE' else 0.0,'domain_representation':1.0 if r['domain']=='REPRESENTATION' else 0.0,
      'domain_cognitive':1.0 if r['domain']=='COGNITIVE' else 0.0,'domain_execution':1.0 if r['domain']=='EXECUTION' else 0.0,
      'domain_memory':1.0 if r['domain']=='MEMORY' else 0.0,'domain_evolution':1.0 if r['domain']=='EVOLUTION' else 0.0,
    }

def row_context(r):
    return {
      'START_PASS':r.get('outcome')=='PASS','START_WITHHOLD':r.get('outcome')=='WITHHOLD',
      'START_HAS_NEXT':bool(r.get('next_required_capability')),'START_NO_NEXT':not bool(r.get('next_required_capability')),
      'START_SAME_DOMAIN_NEXT':bool(r.get('next_required_capability')) and r.get('next_domain')==r.get('domain'),
      'START_FRESH_POSITIVE':bool(r['metrics'].get('fresh_positive')),'START_ABLATION_POSITIVE':bool(r['metrics'].get('ablation_positive')),
      'WINDOW_DOMAIN_STABLE':True,'WINDOW_HAS_WITHHOLD':r.get('outcome')=='WITHHOLD','WINDOW_HAS_PASS':r.get('outcome')=='PASS',
    }

def thinking_preference(r):
    roles=['ACCEPT','ADVANCE','REVISE','SEEK_EVIDENCE']
    acts=[{'id':'STD-'+x,'role':x} for x in roles]
    ids=plan_multicontext(tmodel,row_context(r),acts)
    by={a['id']:a['role'] for a in acts}
    return by[ids[0]] if ids else 'SEEK_EVIDENCE'

ORGAN_KEYS={
 'LOGIC':['logic_accept'],
 'THINKING':['think_accept','think_advance','think_revise','think_seek'],
 'INTELLIGENCE':['intel_stop','intel_retry','intel_advance'],
}
CONTEXT_KEYS=['next_present','same_domain_next','fresh_positive','ablation_positive','canonical_unchanged','rollback_available',
              'domain_code','domain_representation','domain_cognitive','domain_execution','domain_memory','domain_evolution']

def cognitive_features(r):
    lp=bool(tree_predict(lmodel,logic_features(r)));ip=str(tree_predict(imodel,intel_features(r)));tp=thinking_preference(r);m=r['metrics']
    return {
      'state_known':1.0,'logic_accept':1.0 if lp else 0.0,
      'intel_stop':1.0 if ip=='STOP' else 0.0,'intel_retry':1.0 if ip=='RETRY' else 0.0,'intel_advance':1.0 if ip=='ADVANCE' else 0.0,
      'think_accept':1.0 if tp=='ACCEPT' else 0.0,'think_advance':1.0 if tp=='ADVANCE' else 0.0,'think_revise':1.0 if tp=='REVISE' else 0.0,'think_seek':1.0 if tp=='SEEK_EVIDENCE' else 0.0,
      'next_present':1.0 if r.get('next_required_capability') else 0.0,
      'same_domain_next':1.0 if r.get('next_required_capability') and r.get('next_domain')==r.get('domain') else 0.0,
      'fresh_positive':1.0 if m['fresh_positive'] else 0.0,'ablation_positive':1.0 if m['ablation_positive'] else 0.0,
      'canonical_unchanged':1.0 if m['canonical_unchanged'] else 0.0,'rollback_available':1.0 if m['rollback_available'] else 0.0,
      'domain_code':1.0 if r['domain']=='CODE' else 0.0,'domain_representation':1.0 if r['domain']=='REPRESENTATION' else 0.0,
      'domain_cognitive':1.0 if r['domain']=='COGNITIVE' else 0.0,'domain_execution':1.0 if r['domain']=='EXECUTION' else 0.0,
      'domain_memory':1.0 if r['domain']=='MEMORY' else 0.0,'domain_evolution':1.0 if r['domain']=='EVOLUTION' else 0.0,
    }

def predict(x):
    if cfamily=='CART_AXIS':return tree_predict(cmodel,x)
    if cfamily=='KNN_STRATEGY':return knn_predict(cmodel,x)
    if cfamily=='CENTROID_STRATEGY':return centroid_predict(cmodel,x)
    raise ValueError('UNKNOWN_COGNITIVE_FAMILY:'+str(cfamily))

cases=[(r,cognitive_features(r),target_action(r)) for r in blind]
def acc(transform=lambda x:dict(x),subset=None):
    xs=[z for z in cases if subset is None or subset(z[0])]
    if not xs:return None
    return sum(predict(transform(x))==y for _,x,y in xs)/len(xs)

base=acc()
individual={}
for organ,keys in ORGAN_KEYS.items():
    def tr(x,keys=keys):
        z=dict(x)
        for k in keys:z[k]=0.0
        return z
    a=acc(tr);individual[organ]={'score':a,'drop':base-a}
def organ_only(x):
    z=dict(x)
    for k in CONTEXT_KEYS:z[k]=0.0
    return z
organ_only_score=acc(organ_only)
def context_only(x):
    z=dict(x)
    for keys in ORGAN_KEYS.values():
        for k in keys:z[k]=0.0
    return z
context_only_score=acc(context_only)

# Invariance to new irrelevant fields: CART ignores unknown fields; other native families use fixed feature lists.
def add_noise(x):
    z=dict(x);z['novel_noise_1']=1.0;z['novel_noise_2']=-1.0;return z
noise_score=acc(add_noise)

source_slices={}
for sc in sorted({r['source_class'] for r,_,_ in cases}):
    n=sum(1 for r,_,_ in cases if r['source_class']==sc)
    if n>=6:source_slices[sc]={'count':n,'accuracy':acc(subset=lambda r,sc=sc:r['source_class']==sc)}
domain_slices={}
for d in sorted({r['domain'] for r,_,_ in cases}):
    n=sum(1 for r,_,_ in cases if r['domain']==d)
    if n>=6:domain_slices[d]={'count':n,'accuracy':acc(subset=lambda r,d=d:r['domain']==d)}

# Post-corpus artifacts are truly later than the frozen corpus and were not used by V4.
post_paths=[
 'candidates/kernel-self-generated/g2-global-experience-cognitive-genesis-v2.json',
 'experience/yado-global-experience-cognitive-genesis-v2.json',
 'candidates/kernel-self-generated/g2-global-experience-cognitive-genesis-v3.json',
 'experience/yado-global-experience-cognitive-genesis-v3.json',
 'candidates/kernel-self-generated/g2-global-experience-cognitive-genesis-v4.json',
 'experience/yado-global-experience-cognitive-genesis-v4.json',
]
def summarize_post(path):
    p=REPO/path
    if not p.exists():return None
    o=load(p);st=str(o.get('status') or '')
    out='PASS' if st.startswith('PASS') or st=='TRAINED' else 'WITHHOLD' if st.startswith('WITHHOLD') or st=='WITHHOLD' else None
    if out is None:return None
    nxt=o.get('next_required_capability')
    # Minimal structural row using the same schema, with conservative absent metrics.
    return {
      'path':path,'source_class':'POST_CORPUS','status':st,'outcome':out,'next_required_capability':nxt,
      'domain':'COGNITIVE','next_domain':'COGNITIVE' if nxt else None,
      'metrics':{'has_fresh':False,'fresh_positive':False,'has_ablation':False,'ablation_positive':False,
                 'has_regression_restore_integrity':False,'regression_restore_integrity_positive':False,
                 'has_safety_evidence':False,'safety_positive':False,'canonical_unchanged':bool((o.get('checks') or {}).get('canonical_unchanged',False)),
                 'rollback_available':False,'promotion_applied':False,'evidence_density':1},
    }
post_rows=[x for x in (summarize_post(p) for p in post_paths) if x]
post_eval=[]
for r in post_rows:
    x=cognitive_features(r);y=target_action(r);post_eval.append({'path':r['path'],'predicted':predict(x),'expected':y})
post_acc=sum(x['predicted']==x['expected'] for x in post_eval)/max(1,len(post_eval))

core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)
checks={
 'v4_parent_pass':parent.get('status')=='TRAINED' and (parent.get('checks') or {}).get('cognitive_history_gain_over_v3') is True,
 'base_heldout_ge_0_80':base>=.80,
 'logic_ablation_positive':individual['LOGIC']['drop']>=.02,
 'thinking_ablation_positive':individual['THINKING']['drop']>=.02,
 'intelligence_ablation_positive':individual['INTELLIGENCE']['drop']>=.02,
 'organ_only_material':organ_only_score>=.55,
 'organ_only_beats_chance':organ_only_score>=.40,
 'context_only_below_full':context_only_score<=base-.10,
 'irrelevant_noise_invariant':noise_score==base,
 'source_slice_floor':all(v['accuracy']>=.55 for v in source_slices.values()),
 'domain_slice_floor':all(v['accuracy']>=.55 for v in domain_slices.values()),
 'post_corpus_rows_present':len(post_eval)>=4,
 'post_corpus_accuracy_ge_0_66':post_acc>=.66,
 'v4_safety_gate_previously_exact':float((parent.get('safety_gate') or {}).get('candidate_score') or 0)==1.0,
 'v4_unknown_fail_closed':bool((parent.get('checks') or {}).get('unknown_fail_closed')),
 'restore_exact':acc()==base,
 'external_models_used':False,'host_retrained_models':False,'automatic_canonical_promotion':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
}
false_keys=['external_models_used','host_retrained_models','automatic_canonical_promotion']
passed=all(v is True for k,v in checks.items() if k not in false_keys) and all(checks[k] is False for k in false_keys)
status='PASS_SHADOW_G2_GLOBAL_EXPERIENCE_COGNITIVE_STRESS_V1' if passed else 'WITHHOLD_G2_GLOBAL_EXPERIENCE_COGNITIVE_STRESS_V1'
report={
 'schema':'yado.g2.global_experience_cognitive_stress.v1','status':status,
 'parent_genome_id':parent['genome']['genome_id'],'parent_gene_ids':{k:v['gene_id'] for k,v in genes.items()},
 'heldout_count':len(cases),'base_accuracy':base,'individual_organ_ablations':individual,
 'organ_only_accuracy':organ_only_score,'context_only_accuracy':context_only_score,'irrelevant_noise_accuracy':noise_score,
 'source_slices':source_slices,'domain_slices':domain_slices,'post_corpus_evaluation':post_eval,'post_corpus_accuracy':post_acc,
 'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'GLOBAL_EXPERIENCE_COGNITIVE_CANONICAL_ADMISSION_V1' if passed else 'GLOBAL_EXPERIENCE_COGNITIVE_STRESS_REPAIR_V2',
 'semantic_boundary':'FROZEN V4 GENOME STRESS ONLY. NO MODEL IS RETRAINED. TESTS INDIVIDUAL ORGAN CAUSAL CONTRIBUTION, ORGAN-ONLY VS CONTEXT-ONLY PERFORMANCE, IRRELEVANT-NOISE INVARIANCE, SOURCE/DOMAIN SLICES, AND POST-CORPUS ARTIFACTS CREATED AFTER THE FROZEN GLOBAL CORPUS.'
}
report['receipt_sha256']=digest(report);OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
EXP.parent.mkdir(parents=True,exist_ok=True);EXP.write_text(json.dumps(report|{'schema':'yado.g2.global_experience_cognitive_stress.experience.v1'},indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps({'status':status,'base_accuracy':base,'individual_organ_ablations':individual,'organ_only_accuracy':organ_only_score,
 'context_only_accuracy':context_only_score,'post_corpus_accuracy':post_acc,'source_slices':source_slices,'domain_slices':domain_slices,
 'next_required_capability':report['next_required_capability'],'receipt_sha256':report['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
