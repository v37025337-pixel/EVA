from __future__ import annotations
from pathlib import Path
from itertools import combinations
import hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_algorithm_component_runtime_native_v1 import predict_intel_component
from yado_organ_runtime_native_v1 import tree_predict
from yado_evolution_runtime_native_v1 import linear_predict
from yado_unified_core_v1 import UnifiedYADOCoreV1

TASK=REPO/'architecture/yado-kernel-native-self-created-constructor-after-external-learning-v1-request.json'
LEARN=REPO/'experience/yado-user-external-corpus-learning-v1.json'
ACTION=REPO/'candidates/kernel-self-generated/g2-autonomous-self-improvement-task-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-native-self-created-constructor-after-external-learning-v1.json'
GENE=REPO/'candidates/kernel-self-generated/g2-native-self-created-evidence-binder-gene-v1.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))

task=load(TASK);learn=load(LEARN);action=load(ACTION)
if learn.get('status')!='LEARNED_EXTERNAL_CORPUS':
    raise RuntimeError('EXTERNAL_LEARNING_NOT_COMPLETE')

result=((action.get('goal_action_binding') or {}).get('result') or {})
comp=result.get('comprehension') or {}
# This is a validity contract, not a solution representation. YADO receives only
# observed contract fields + counterfactual IO and must choose/synthesize its model.
base={
 'priority_match':action.get('kernel_selected_next_step')=='LIVE_RESOURCE_EVIDENCE_SCOPE',
 'direct_priority_evidence':action.get('direct_priority_evidence') is True,
 'action_relevant':action.get('selected_action')=='LIVE_RESOURCE_EVIDENCE_RECHECK',
 'action_status_pass':str(result.get('status') or '').startswith('PASS_'),
 'comprehension_complete':all(bool(comp.get(k)) for k in (
   'repository_commit_identity_extracted','readme_title_extracted','package_identity_extracted',
   'provider_catalog_extracted','no_key_provider_set_extracted')),
 'conflict_resolution_pass':result.get('conflict_resolution_pass') is True,
 'canonical_immutable':result.get('canonical_mutation') is False and action.get('canonical_head_unchanged') is True,
}
required=tuple(sorted(base))
if not all(base.values()):raise RuntimeError('VALID_POSITIVE_RECEIPT_REQUIRED')

def oracle(x):
    return 'ACCEPT_FRESH_EVIDENCE' if all(bool(x[k]) for k in required) else 'WITHHOLD_FRESH_EVIDENCE'

rows=[]
for nonce in range(12):
    x=dict(base);x['irrelevant_nonce']=nonce;rows.append((x,oracle(x),'POSITIVE'))
for i,k in enumerate(required):
    for nonce in range(5):
        x=dict(base);x[k]=False;x['irrelevant_nonce']=100+i*10+nonce;rows.append((x,oracle(x),'SINGLE_'+k))
for i,(a,b) in enumerate(combinations(required,2)):
    x=dict(base);x[a]=False;x[b]=False;x['irrelevant_nonce']=500+i;rows.append((x,oracle(x),'PAIR_'+a+'_'+b))

fit=[];val=[];blind=[]
for x,y,kind in rows:
    if kind=='POSITIVE':
        n=int(x['irrelevant_nonce'])
        target=fit if n<6 else val if n<9 else blind
    else:
        bucket=int(hashlib.sha256(canon(x).encode()).hexdigest()[:8],16)%10
        target=fit if bucket<5 else val if bucket<7 else blind
    target.append((x,y))
revealed=fit+val
if not all((fit,val,blind)):raise RuntimeError('BAD_SPLIT')

k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_native_post_external_learning.sqlite'))
routes=[]

# Route A: let YADO's full native INTELLIGENCE algorithm bank choose its own family.
try:
    r=k.meta_evolve_intelligence(fit,val,revealed,blind)
    routes.append({'route':'NATIVE_META_EVOLVE_INTELLIGENCE','result':r})
except Exception as e:
    routes.append({'route':'NATIVE_META_EVOLVE_INTELLIGENCE','error':type(e).__name__+':'+str(e)[:500]})

# Route B: let YADO's self-expanding RC6 meta-grammar try to construct an extension.
try:
    r=k.synthesize_intelligence_with_extended_meta_grammar(fit,val,revealed,blind)
    routes.append({'route':'NATIVE_EXTENDED_META_GRAMMAR','result':r})
except Exception as e:
    routes.append({'route':'NATIVE_EXTENDED_META_GRAMMAR','error':type(e).__name__+':'+str(e)[:500]})

def predict_route(row,x):
    r=row.get('result') or {}
    model=r.get('model')
    if model is None:return None
    if row['route']=='NATIVE_EXTENDED_META_GRAMMAR':
        return predict_intel_component(model,x)
    fam=str((r.get('selected_algorithm') or {}).get('family') or '')
    if fam=='CART_AXIS':return tree_predict(model,x)
    if fam=='LINEAR_SCORE_SEARCH':return linear_predict(model,x)
    return None

def score(row,cases):
    if not cases:return 0.0
    return sum(predict_route(row,x)==y for x,y in cases)/len(cases)

skills=[]
for i,row in enumerate(routes):
    fit_acc=score(row,fit);val_acc=score(row,val);blind_acc=score(row,blind)
    actual=predict_route(row,base)
    majority=max(sorted({y for _,y in revealed}),key=lambda y:sum(1 for _,z in revealed if z==y))
    ablation=sum(majority==y for _,y in blind)/len(blind)
    row['metrics']={'fit':fit_acc,'validation':val_acc,'fresh_blind':blind_acc,'ablation':ablation}
    row['actual_receipt_prediction']=actual
    structural=bool(row.get('result')) and fit_acc>=.95 and val_acc>=.95
    semantic=blind_acc
    sid='NATIVE_SELF_CREATED_'+str(i)+'_'+row['route']
    row['skill_id']=sid
    skills.append({
      'skill_id':sid,
      'artifact_digest':digest({'route':row['route'],'result':row.get('result'),'metrics':row['metrics']}),
      'structural_valid':structural,
      'semantic_consistency':semantic,
      'fit_baseline':0.0,'fit_candidate':fit_acc,
      'heldout_baseline':ablation,'heldout_candidate':blind_acc,
      'regression_pass':blind_acc>=.95,
      'state_integrity':True,'rollback_available':True,
    })

try:
    selection=k.select_evolution_skills(skills,max_skills=1,min_semantic_consistency=.95,min_fit_gain=.50,max_heldout_drop=0,min_heldout_gain=.05)
finally:
    k.close()

selected_ids=selection.get('selected_skill_ids') or []
winner=next((x for x in routes if x.get('skill_id') in selected_ids),None)
core=UnifiedYADOCoreV1(REPO)
gene=None
if winner is not None:
    m=winner['metrics']
    if m['fit']==1.0 and m['validation']==1.0 and m['fresh_blind']==1.0 and m['fresh_blind']>m['ablation'] and winner.get('actual_receipt_prediction')=='ACCEPT_FRESH_EVIDENCE':
        native=winner['result']
        gene={
          'schema':'yado.g2.native_self_created_evidence_binder_gene.v1',
          'gene_id':'GENE-YADO-NATIVE-EVIDENCE-BINDER-'+digest({'route':winner['route'],'model':native.get('model')})[:16],
          'origin':'YADO_NATIVE_ALGORITHM_BANK_AFTER_EXTERNAL_CORPUS_LEARNING',
          'self_created_model':True,
          'external_model_generated':False,
          'selected_native_route':winner['route'],
          'selected_algorithm':native.get('selected_algorithm'),
          'grammar_extension_id':native.get('grammar_extension_id'),
          'predicate_program':native.get('predicate_program'),
          'model':native.get('model'),
          'contract_fields':list(required),
          'external_learning_experience_digest':learn.get('experience_digest'),
          'promotion_state':'SHADOW_ONLY',
          'canonical_active':False,
        }
        gene['gene_digest']=digest(gene)
        GENE.parent.mkdir(parents=True,exist_ok=True)
        GENE.write_text(json.dumps(gene,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

checks={
 'external_learning_completed':learn.get('status')=='LEARNED_EXTERNAL_CORPUS',
 'external_models_used_for_constructor':False,
 'host_selected_algorithm_family':False,
 'native_routes_evaluated':len(routes)>=2,
 'kernel_skill_gate_selected':winner is not None,
 'fresh_blind_exact':bool(winner and winner['metrics']['fresh_blind']==1.0),
 'causal_ablation_drop':bool(winner and winner['metrics']['fresh_blind']>winner['metrics']['ablation']),
 'actual_valid_receipt_accepted':bool(winner and winner.get('actual_receipt_prediction')=='ACCEPT_FRESH_EVIDENCE'),
 'gene_created':gene is not None,
 'gene_shadow_only':bool(gene and gene.get('promotion_state')=='SHADOW_ONLY'),
 'canonical_unchanged':core.head.get('g3_genesis_performed') is False,
}
status='PASS_SHADOW_G2_NATIVE_SELF_CREATED_CONSTRUCTOR_AFTER_EXTERNAL_LEARNING_V1' if all(checks.values()) else 'WITHHOLD_G2_NATIVE_SELF_CREATED_CONSTRUCTOR_AFTER_EXTERNAL_LEARNING_V1'
report={
 'schema':'yado.g2.native_self_created_constructor_after_external_learning.v1',
 'status':status,'task':task,
 'external_learning':{'experience_digest':learn.get('experience_digest'),'fetched_count':learn.get('fetched_count'),'source_count':learn.get('source_count')},
 'training_contract_fields':list(required),'case_counts':{'fit':len(fit),'validation':len(val),'blind':len(blind)},
 'native_routes':routes,'kernel_skill_selection':selection,'selected_skill_id':selected_ids[0] if selected_ids else None,
 'invented_gene':gene,'checks':checks,
 'canonical_mutation':False,'architecture_mutation':False,
 'semantic_boundary':'YADO STUDIED THE USER-SUPPLIED PUBLIC CORPUS FIRST, THEN THE HOST PROVIDED ONLY A VALIDITY CONTRACT AND FRESH/ABLATION GATES. YADO CHOSE BETWEEN ITS NATIVE CONSTRUCTOR ROUTES AND ITS NATIVE SKILL GATE SELECTED THE EXECUTABLE MODEL. IF PASS, THE RESULT IS A YADO-GENERATED SHADOW GENE WITHIN EXISTING NATIVE ALGORITHM SUBSTRATES; IT IS NOT YET A NEW UNBOUNDED META-LANGUAGE FAMILY OR CANONICAL SELF-AUDIT INTEGRATION.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({'status':status,'selected_skill_id':report['selected_skill_id'],
 'routes':[{'route':x['route'],'metrics':x.get('metrics'),'algorithm':(x.get('result') or {}).get('selected_algorithm'),
            'grammar_extension_id':(x.get('result') or {}).get('grammar_extension_id')} for x in routes],
 'gene_id':gene.get('gene_id') if gene else None,'checks':checks,'receipt_sha256':report['receipt_sha256']},indent=2,sort_keys=True,default=str))
if status!='PASS_SHADOW_G2_NATIVE_SELF_CREATED_CONSTRUCTOR_AFTER_EXTERNAL_LEARNING_V1':raise SystemExit(2)
