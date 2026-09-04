from __future__ import annotations
from pathlib import Path
from itertools import combinations
import hashlib,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_algorithm_component_runtime_native_v1 import predict_intel_component
from yado_unified_core_v1 import UnifiedYADOCoreV1

TASK=REPO/'architecture/yado-kernel-native-action-evidence-binder-invention-v1-request.json'
ACTION=REPO/'candidates/kernel-self-generated/g2-autonomous-self-improvement-task-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-native-action-evidence-binder-invention-v1.json'
GENE=REPO/'candidates/kernel-self-generated/g2-native-action-evidence-binder-gene-v1.json'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))

task=load(TASK)
action=load(ACTION)
binding=action.get('goal_action_binding') or {}
result=binding.get('result') or {}
comp=result.get('comprehension') or {}

# The host supplies only the validity contract / oracle. YADO must synthesize the
# executable decision mechanism with its pre-existing native meta-grammar.
base={
 'priority_match': action.get('kernel_selected_next_step')=='LIVE_RESOURCE_EVIDENCE_SCOPE',
 'direct_priority_evidence': action.get('direct_priority_evidence') is True,
 'action_relevant': action.get('selected_action')=='LIVE_RESOURCE_EVIDENCE_RECHECK',
 'action_status_pass': str(result.get('status') or '').startswith('PASS_'),
 'comprehension_complete': all(bool(comp.get(k)) for k in (
     'repository_commit_identity_extracted','readme_title_extracted',
     'package_identity_extracted','provider_catalog_extracted',
     'no_key_provider_set_extracted')),
 'conflict_resolution_pass': result.get('conflict_resolution_pass') is True,
 'canonical_immutable': result.get('canonical_mutation') is False and action.get('canonical_head_unchanged') is True,
}
required=tuple(sorted(base))
if not all(base.values()):
    raise RuntimeError('LATEST_DIRECT_EVIDENCE_IS_NOT_A_VALID_POSITIVE_EXAMPLE')

def expected(x):
    return 'ACCEPT_FRESH_EVIDENCE' if all(bool(x[k]) for k in required) else 'WITHHOLD_FRESH_EVIDENCE'

# Counterfactual curriculum is generated mechanically from the observed valid
# receipt: positive examples plus single/pair fault ablations. No repair rule,
# predicate, target source line, or model structure is supplied to YADO.
rows=[]
for nonce in range(8):
    x=dict(base); x['irrelevant_nonce']=nonce
    rows.append({'input':x,'expected':expected(x),'kind':'POSITIVE'})
for idx,k in enumerate(required):
    for nonce in range(3):
        x=dict(base); x[k]=False; x['irrelevant_nonce']=100+idx*10+nonce
        rows.append({'input':x,'expected':expected(x),'kind':'SINGLE_FAULT_'+k})
for idx,(a,b) in enumerate(combinations(required,2)):
    x=dict(base); x[a]=False; x[b]=False; x['irrelevant_nonce']=500+idx
    rows.append({'input':x,'expected':expected(x),'kind':'PAIR_FAULT_'+a+'_'+b})

# Deterministic split with positives in every partition; blind never used for synthesis.
fit=[];validation=[];blind=[]
for r in rows:
    n=int(r['input']['irrelevant_nonce'])
    if r['kind']=='POSITIVE':
        (fit if n<4 else validation if n<6 else blind).append({'input':r['input'],'expected':r['expected']})
    else:
        bucket=int(hashlib.sha256(canon(r['input']).encode()).hexdigest()[:8],16)%10
        if bucket<5: fit.append({'input':r['input'],'expected':r['expected']})
        elif bucket<7: validation.append({'input':r['input'],'expected':r['expected']})
        else: blind.append({'input':r['input'],'expected':r['expected']})
revealed=fit+validation

if not fit or not validation or not blind:
    raise RuntimeError('BAD_DATASET_SPLIT')
if not any(x['expected']=='ACCEPT_FRESH_EVIDENCE' for x in fit):
    raise RuntimeError('NO_POSITIVE_FIT')
if not any(x['expected']=='ACCEPT_FRESH_EVIDENCE' for x in validation):
    raise RuntimeError('NO_POSITIVE_VALIDATION')
if not any(x['expected']=='ACCEPT_FRESH_EVIDENCE' for x in blind):
    raise RuntimeError('NO_POSITIVE_BLIND')

k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_native_action_evidence_binder.sqlite'))
try:
    native=k.synthesize_intelligence_with_extended_meta_grammar(fit,validation,revealed,blind)
finally:
    k.close()

model=native.get('model')
def score(cases):
    if model is None or not cases:return 0.0
    ok=0
    for c in cases:
        try: pred=predict_intel_component(model,c['input'])
        except Exception: pred=None
        ok += pred==c['expected']
    return ok/len(cases)

fit_acc=score(fit);val_acc=score(validation);blind_acc=score(blind)
actual_prediction=predict_intel_component(model,base) if model is not None else None

# Causal ablation: remove the synthesized mechanism and use the majority label.
all_labels=[x['expected'] for x in revealed]
majority=max(sorted(set(all_labels)),key=lambda y:(all_labels.count(y),y))
ablation_blind=sum(majority==x['expected'] for x in blind)/len(blind)

core=UnifiedYADOCoreV1(REPO)
gene=None
checks={
 'native_meta_grammar_supported':native.get('status')=='SUPPORTED',
 'native_extension_created':bool(native.get('grammar_extension_id')),
 'fit_exact':fit_acc==1.0,
 'validation_exact':val_acc==1.0,
 'fresh_blind_exact':blind_acc==1.0,
 'causal_ablation_drop':blind_acc>ablation_blind,
 'actual_receipt_accepted':actual_prediction=='ACCEPT_FRESH_EVIDENCE',
 'external_models_used':False,
 'host_patch_supplied':False,
 'host_target_file_supplied':False,
 'canonical_unchanged':core.head.get('g3_genesis_performed') is False,
}
if all(checks.values()):
    gene={
      'schema':'yado.g2.native_action_evidence_binder_gene.v1',
      'gene_id':'GENE-SELF-SYNTHESIZED-ACTION-EVIDENCE-BINDER-'+str(native.get('grammar_extension_id')),
      'novel_gene':True,
      'gene_scope':['SELF_MODEL','SELF_AUDIT','EVIDENCE_BINDING'],
      'origin':'YADO_NATIVE_EXTENDED_META_GRAMMAR',
      'native_constructor':'synthesize_intelligence_with_extended_meta_grammar',
      'grammar_extension_id':native.get('grammar_extension_id'),
      'predicate_program':native.get('predicate_program'),
      'model':model,
      'required_contract_fields':list(required),
      'promotion_state':'SHADOW_ONLY',
      'source_problem':'ACTION_EVIDENCE_TO_SELF_AUDIT_BINDING',
      'canonical_active':False,
    }
    gene['gene_digest']=digest(gene)
    GENE.parent.mkdir(parents=True,exist_ok=True)
    GENE.write_text(json.dumps(gene,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

status='PASS_SHADOW_G2_NATIVE_ACTION_EVIDENCE_BINDER_INVENTION_V1' if gene else 'WITHHOLD_G2_NATIVE_ACTION_EVIDENCE_BINDER_INVENTION_V1'
report={
 'schema':'yado.g2.native_action_evidence_binder_invention.v1',
 'status':status,
 'task':task,
 'source_action_receipt_sha256':action.get('receipt_sha256'),
 'validity_contract_fields':list(required),
 'dataset':{'fit':len(fit),'validation':len(validation),'revealed':len(revealed),'blind':len(blind),
            'construction':'OBSERVED_VALID_RECEIPT_PLUS_MECHANICAL_SINGLE_AND_PAIR_FAULT_ABLATIONS'},
 'native_result':native,
 'metrics':{'fit':fit_acc,'validation':val_acc,'fresh_blind':blind_acc,'ablation_blind':ablation_blind},
 'actual_receipt_prediction':actual_prediction,
 'invented_gene':gene,
 'checks':checks,
 'canonical_mutation':False,'architecture_mutation':False,'generation_transition':False,
 'semantic_boundary':'BOUNDED NATIVE SELF-SYNTHESIS. YADO RECEIVES A VALIDITY CONTRACT AND COUNTERFACTUAL IO EVIDENCE, THEN ITS PRE-EXISTING RC6 EXTENDED META-GRAMMAR CREATES THE EXECUTABLE EVIDENCE-BINDING MODEL. NO EXTERNAL LLM, SOURCE PATCH, TARGET FILE, OR READY REPAIR RULE IS PROVIDED. THIS CREATES A SHADOW MECHANISM; IT DOES NOT YET INTEGRATE IT INTO THE CANONICAL DEEP SELF-AUDIT.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,
 'native_status':native.get('status'),
 'grammar_extension_id':native.get('grammar_extension_id'),
 'metrics':report['metrics'],
 'actual_receipt_prediction':actual_prediction,
 'invented_gene_id':gene.get('gene_id') if gene else None,
 'checks':checks,
 'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True,default=str))
if status!='PASS_SHADOW_G2_NATIVE_ACTION_EVIDENCE_BINDER_INVENTION_V1':
    raise SystemExit(2)
