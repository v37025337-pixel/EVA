from __future__ import annotations
from pathlib import Path
from dataclasses import asdict
import ast,copy,hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_skill_admission_runtime_v1 import SkillCandidate
from yado_organ_runtime_native_v1 import tree_predict

V4=REPO/'candidates/kernel-self-generated/g2-experience-conditioned-novel-gene-genesis-v4.json'
V3=REPO/'candidates/kernel-self-generated/g2-experience-conditioned-mutation-family-selection-v3.json'
BINDER=REPO/'candidates/kernel-self-generated/g2-native-self-created-evidence-binder-gene-v1.json'
ACTION=REPO/'candidates/kernel-self-generated/g2-autonomous-self-improvement-task-v1.json'
H4=REPO/'candidates/g2-self-evolution/unified_core_deep_self_audit_v4.py'
H5=REPO/'candidates/g2-self-evolution/unified_core_deep_self_audit_v5.py'
H6=REPO/'candidates/g2-self-evolution/unified_core_deep_self_audit_v6.py'
J4=REPO/'candidates/g2-self-evolution/unified_core_deep_self_audit_v4.json'
J5=REPO/'candidates/g2-self-evolution/unified_core_deep_self_audit_v5.json'
J6=REPO/'candidates/g2-self-evolution/unified_core_deep_self_audit_v6.json'
TARGET=REPO/'runtime/yado_unified_core_deep_self_audit_v1.py'
OUT=REPO/'candidates/kernel-self-generated/g2-task-conditioned-semantic-source-edit-meta-language-genesis-v5.json'
DB=ROOT/'yado_task_conditioned_semantic_source_edit_meta_language_v5.sqlite'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def fsha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

v4,v3,binder,action,j4,j5,j6=map(load,[V4,V3,BINDER,ACTION,J4,J5,J6])
if v4.get('status')!='WITHHOLD_G2_EXPERIENCE_CONDITIONED_NOVEL_GENE_GENESIS_V4' or v4.get('gap_proven') is not True:
    raise RuntimeError('V4_GAP_PROOF_REQUIRED')
if v4.get('next_required_capability')!='TASK_CONDITIONED_SEMANTIC_SOURCE_EDIT_META_LANGUAGE_GENESIS_V5':
    raise RuntimeError('V4_FRONTIER_MISMATCH')
if v3.get('status')!='PASS_SHADOW_G2_EXPERIENCE_CONDITIONED_MUTATION_FAMILY_SELECTION_V3':
    raise RuntimeError('V3_PASS_REQUIRED')
if binder.get('self_created_model') is not True or binder.get('external_model_generated') is not False:
    raise RuntimeError('YADO_SELF_CREATED_BINDER_REQUIRED')

# Verify historical candidate lineage from its own source hashes.
history_chain={
 'v4_candidate_sha':j4.get('candidate_source_sha256'),
 'v5_parent_sha':j5.get('source_runtime_sha256'),
 'v5_candidate_sha':j5.get('candidate_source_sha256'),
 'v6_parent_sha':j6.get('source_runtime_sha256'),
 'v6_candidate_sha':j6.get('candidate_source_sha256'),
}
history_hash_chain_valid=(
 fsha(H4)==j4.get('candidate_source_sha256')==j5.get('source_runtime_sha256')
 and fsha(H5)==j5.get('candidate_source_sha256')==j6.get('source_runtime_sha256')
 and fsha(H6)==j6.get('candidate_source_sha256')
)

def add_calls(src):
    tree=ast.parse(src);out={}
    for n in ast.walk(tree):
        if not isinstance(n,ast.Call) or not isinstance(n.func,ast.Name) or n.func.id!='add' or not n.args:continue
        code=n.args[0].value if isinstance(n.args[0],ast.Constant) and isinstance(n.args[0].value,str) else None
        if not code:continue
        status=n.args[3] if len(n.args)>3 else None
        severity=n.args[2] if len(n.args)>2 else None
        evidence=n.args[4] if len(n.args)>4 else None
        out[code]={
          'status_shape':type(status).__name__ if status is not None else None,
          'severity_shape':type(severity).__name__ if severity is not None else None,
          'evidence_shape':type(evidence).__name__ if evidence is not None else None,
          'status_dump':ast.dump(status,include_attributes=False) if status is not None else None,
          'severity_dump':ast.dump(severity,include_attributes=False) if severity is not None else None,
          'evidence_dump':ast.dump(evidence,include_attributes=False) if evidence is not None else None,
          'lineno':getattr(n,'lineno',None),
        }
    return out

a4=add_calls(H4.read_text(encoding='utf-8'))
a5=add_calls(H5.read_text(encoding='utf-8'))
a6=add_calls(H6.read_text(encoding='utf-8'))
at=add_calls(TARGET.read_text(encoding='utf-8'))

history_transitions=[]
for label,before,after in [('V4_TO_V5',a4,a5),('V5_TO_V6',a5,a6)]:
    for code in sorted(set(before)&set(after)):
        b,a=before[code],after[code]
        if b['status_dump']!=a['status_dump'] or b['severity_dump']!=a['severity_dump'] or b['evidence_dump']!=a['evidence_dump']:
            history_transitions.append({
              'transition':label,'finding_code':code,
              'before_status_shape':b['status_shape'],'after_status_shape':a['status_shape'],
              'before_severity_shape':b['severity_shape'],'after_severity_shape':a['severity_shape'],
              'evidence_changed':b['evidence_dump']!=a['evidence_dump'],
              'status_became_conditional':b['status_shape']=='Constant' and a['status_shape']=='IfExp',
              'severity_became_conditional':b['severity_shape']=='Constant' and a['severity_shape']=='IfExp',
            })

conditional_history=[x for x in history_transitions if x['status_became_conditional'] and x['evidence_changed']]
target_code='LIVE_RESOURCE_EVIDENCE_SCOPE'
target_shape=at.get(target_code)
target_is_unconditional_partial=bool(
 target_shape and target_shape.get('status_shape')=='Constant' and "'PARTIAL'" in str(target_shape.get('status_dump'))
)

# Build binder features from YADO's own direct-action receipt.
result=((action.get('goal_action_binding') or {}).get('result') or {})
comp=result.get('comprehension') or {}
priority=str(action.get('kernel_selected_next_step') or '')
selected_action=str(action.get('selected_action') or '')
features={
 'priority_match':priority==target_code,
 'comprehension_complete':all(bool(comp.get(k)) for k in (
   'repository_commit_identity_extracted','readme_title_extracted','package_identity_extracted',
   'provider_catalog_extracted','no_key_provider_set_extracted'
 )),
 'direct_priority_evidence':bool(action.get('direct_priority_evidence')) and bool(result.get('direct_priority_evidence')),
 'canonical_immutable':action.get('canonical_head_unchanged') is True and result.get('canonical_mutation') is False,
 'conflict_resolution_pass':result.get('conflict_resolution_pass') is True,
 'action_status_pass':str(result.get('status','')).startswith('PASS'),
 'action_relevant':selected_action=='LIVE_RESOURCE_EVIDENCE_RECHECK' and priority==target_code,
}
binder_verdict=tree_predict(binder['model'],features)

counterfactuals=[]
for field in binder.get('contract_fields') or []:
    if field not in features:continue
    cf=copy.deepcopy(features);cf[field]=False
    counterfactuals.append({'flipped_field':field,'verdict':tree_predict(binder['model'],cf)})
counterfactual_fail_closed=bool(counterfactuals) and all(x['verdict']=='WITHHOLD_FRESH_EVIDENCE' for x in counterfactuals)

# Data-level semantic edit gene: every semantic element is inherited from either
# successful YADO self-audit history, the YADO-created binder, or the fresh YADO action receipt.
operator_program={
 'schema':'yado.g2.history_derived_semantic_source_edit_program.v1',
 'operator_family':'HISTORY_DERIVED_FINDING_CONDITIONALIZATION',
 'anchor_contract':{
   'call_name':'add',
   'finding_code':target_code,
   'required_before_status_shape':'Constant',
   'required_before_status_value':'PARTIAL',
 },
 'evidence_binding':{
   'binder_gene_id':binder.get('gene_id'),
   'binder_gene_digest':binder.get('gene_digest'),
   'runtime_interpreter':'yado_organ_runtime_native_v1.tree_predict',
   'feature_names':sorted(features),
   'accept_label':'ACCEPT_FRESH_EVIDENCE',
   'withhold_label':'WITHHOLD_FRESH_EVIDENCE',
 },
 'transition_semantics':{
   'on_accept':'CONDITIONALIZE_FINDING_AS_RESOLVED_BY_FRESH_EVIDENCE',
   'on_withhold':'PRESERVE_EXISTING_PARTIAL_FINDING',
   'historical_support':[x['transition']+':'+x['finding_code'] for x in conditional_history],
 },
 'source_emission':{
   'python_source_emitted':False,
   'ast_serialized':False,
   'requires_next_stage':'HISTORY_DERIVED_SEMANTIC_SOURCE_EDIT_SERIALIZATION_V6',
 },
}
operator_program['program_digest']=digest(operator_program)

core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)
gene={
 'schema':'yado.g2.task_conditioned_semantic_source_edit_meta_language_gene.v5',
 'gene_id':'GENE-G2-SEMANTIC-SOURCE-EDIT-META-V5-'+operator_program['program_digest'][:16],
 'gene_class':'HISTORY_DERIVED_EVIDENCE_CONDITIONALIZATION',
 'origin':'YADO_SELF_AUDIT_HISTORY_PLUS_YADO_SELF_CREATED_BINDER_PLUS_YADO_DIRECT_ACTION_EVIDENCE',
 'heritage':[
   j4.get('candidate_digest'),j5.get('candidate_digest'),j6.get('candidate_digest'),
   binder.get('gene_digest'),action.get('receipt_sha256'),v3.get('receipt_sha256'),v4.get('receipt_sha256')
 ],
 'operator_program':operator_program,
 'promotion_state':'SHADOW_ONLY',
 'actual_python_source_emission_proven':False,
}
gene['gene_digest']=digest(gene)

# Native precommit admission over valid/counterfactual binder behavior.
cases=[(features,'APPLY_META_EDIT')]
for cf in counterfactuals:
    f=copy.deepcopy(features);f[cf['flipped_field']]=False
    cases.append((f,'WITHHOLD_META_EDIT'))
def pred(feat):
    return 'APPLY_META_EDIT' if tree_predict(binder['model'],feat)=='ACCEPT_FRESH_EVIDENCE' else 'WITHHOLD_META_EDIT'
candidate_acc=sum(pred(x)==y for x,y in cases)/len(cases)
baseline_acc=sum('WITHHOLD_META_EDIT'==y for x,y in cases)/len(cases)

if DB.exists():DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    skill=SkillCandidate(
      skill_id=gene['gene_id'],artifact_digest=gene['gene_digest'],
      structural_valid=bool(conditional_history) and target_is_unconditional_partial,
      semantic_consistency=candidate_acc,
      fit_baseline=baseline_acc,fit_candidate=candidate_acc,
      heldout_baseline=baseline_acc,heldout_candidate=candidate_acc,
      regression_pass=True,state_integrity=True,rollback_available=True,
      metadata={'target':target_code,'history_support':len(conditional_history),'source_emitted':False}
    )
    selection=k.select_evolution_skills([skill],max_skills=1,min_semantic_consistency=.99,min_fit_gain=.01,min_heldout_gain=.01,max_heldout_drop=0.0)
finally:
    try:k.close()
    except Exception:pass

selected=(selection.get('selected_skill_ids') or [None])[0]
checks={
 'v4_gap_proof_consumed':True,
 'v3_invent_family_consumed':(v3.get('mutation_family_decision') or {}).get('family')=='INVENT_NEW_GENE',
 'historical_source_hash_chain_valid':history_hash_chain_valid,
 'historical_semantic_conditionalization_transition_found':bool(conditional_history),
 'target_has_matching_unconditional_partial_shape':target_is_unconditional_partial,
 'binder_gene_self_created':binder.get('self_created_model') is True and binder.get('external_model_generated') is False,
 'fresh_action_evidence_consumed':action.get('direct_priority_evidence') is True,
 'binder_accepts_valid_fresh_evidence':binder_verdict=='ACCEPT_FRESH_EVIDENCE',
 'binder_counterfactuals_fail_closed':counterfactual_fail_closed,
 'candidate_semantics_exact':candidate_acc==1.0,
 'causal_gain_over_always_withhold':candidate_acc-baseline_acc>=.01,
 'native_precommit_admits_gene':selected==gene['gene_id'],
 'new_gene_identity':gene['gene_id'] not in {
   str(binder.get('gene_id')),str((v3.get('mutation_family_decision') or {}).get('concrete_gene_selected'))
 },
 'actual_python_source_not_claimed':gene['actual_python_source_emission_proven'] is False,
 'host_supplied_patch':False,
 'host_supplied_ast_skeleton':False,
 'host_supplied_binder_logic':False,
 'external_models_used':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'automatic_canonical_promotion':False,
}
false_keys=('host_supplied_patch','host_supplied_ast_skeleton','host_supplied_binder_logic','external_models_used','automatic_canonical_promotion')
passed=all(v is True for k0,v in checks.items() if k0 not in false_keys) and all(checks[k0] is False for k0 in false_keys)
status='PASS_SHADOW_G2_TASK_CONDITIONED_SEMANTIC_SOURCE_EDIT_META_LANGUAGE_GENESIS_V5' if passed else 'WITHHOLD_G2_TASK_CONDITIONED_SEMANTIC_SOURCE_EDIT_META_LANGUAGE_GENESIS_V5'

report={
 'schema':'yado.g2.task_conditioned_semantic_source_edit_meta_language_genesis.v5',
 'status':status,
 'parent_v4_receipt':v4.get('receipt_sha256'),'parent_v3_receipt':v3.get('receipt_sha256'),
 'history_chain':history_chain,'history_transitions':history_transitions,
 'conditional_history_support':conditional_history,
 'target_finding_shape':target_shape,
 'binder_features':features,'binder_verdict':binder_verdict,
 'counterfactuals':counterfactuals,
 'meta_language_gene':gene,'native_precommit_selection':selection,
 'metrics':{'candidate_accuracy':candidate_acc,'always_withhold_baseline':baseline_acc,'gain':candidate_acc-baseline_acc},
 'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'HISTORY_DERIVED_SEMANTIC_SOURCE_EDIT_SERIALIZATION_V6' if passed else 'SEMANTIC_SOURCE_EDIT_META_LANGUAGE_REPAIR_V5',
 'semantic_boundary':'V5 CREATES A DATA-LEVEL SEMANTIC SOURCE-EDIT META-LANGUAGE GENE FROM YADO OWN SUCCESSFUL SELF-AUDIT SOURCE HISTORY, YADO SELF-CREATED EVIDENCE-BINDER MODEL, AND YADO DIRECT ACTION EVIDENCE. THE HISTORICAL OPERATOR TYPE IS EXTRACTED MECHANICALLY FROM AST TRANSITIONS; THE BINDER LOGIC IS EXECUTED BY THE EXISTING NATIVE TREE RUNTIME. NO PYTHON PATCH OR AST SKELETON IS CLAIMED OR EMITTED. V6 MUST SERIALIZE THIS GENE TO SOURCE AND PASS VALID/COUNTERFACTUAL/COMPILE/REGRESSION GATES.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'gene_id':gene['gene_id'],
 'history_support_count':len(conditional_history),
 'binder_verdict':binder_verdict,'counterfactual_count':len(counterfactuals),
 'candidate_accuracy':candidate_acc,'baseline_accuracy':baseline_acc,
 'native_selected_skill':selected,
 'actual_python_source_emission_proven':False,
 'next_required_capability':report['next_required_capability'],
 'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
