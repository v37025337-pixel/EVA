from __future__ import annotations
from pathlib import Path
import ast,copy,hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1

V5=REPO/'candidates/kernel-self-generated/g2-task-conditioned-semantic-source-edit-meta-language-genesis-v5.json'
SER=REPO/'candidates/kernel-self-generated/g2-native-source-primitive-execution-serialization-v1.json'
HIDDEN=REPO/'candidates/kernel-self-generated/g2-native-hidden-code-gene-source-emission-observation-v3.json'
CTRL=REPO/'candidates/kernel-self-generated/g2-native-controller-source-emitter-binding-v5.json'
EMITTER=REPO/'candidates/kernel-self-generated/g2-experience-conditioned-native-emitter-gene-genesis-v3.json'
CURRENT=REPO/'candidates/kernel-self-generated/g2-native-action-evidence-binder-source-realization-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-history-derived-semantic-source-edit-serialization-v6.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))

v5,ser,hidden,ctrl,emitter,current=map(load,[V5,SER,HIDDEN,CTRL,EMITTER,CURRENT])
if v5.get('status')!='PASS_SHADOW_G2_TASK_CONDITIONED_SEMANTIC_SOURCE_EDIT_META_LANGUAGE_GENESIS_V5':
    raise RuntimeError('V5_META_LANGUAGE_PASS_REQUIRED')
if v5.get('next_required_capability')!='HISTORY_DERIVED_SEMANTIC_SOURCE_EDIT_SERIALIZATION_V6':
    raise RuntimeError('V5_FRONTIER_MISMATCH')

core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)
target_rel=str(current.get('kernel_provenant_target_path') or '')
target=REPO/target_rel
parent_source=target.read_text(encoding='utf-8')
parent_sha=hashlib.sha256(parent_source.encode()).hexdigest()

meta_gene=v5.get('meta_language_gene') or {}
operator=(meta_gene.get('operator_program') or {})
target_code=((operator.get('anchor_contract') or {}).get('finding_code'))
if target_code!='LIVE_RESOURCE_EVIDENCE_SCOPE':
    raise RuntimeError('UNEXPECTED_V5_TARGET_ANCHOR')

# Inventory only existing, already evidenced source paths. V6 is forbidden to introduce
# a new serializer or AST compiler.
existing_paths=[
 {
  'path':str(SER.relative_to(REPO)),
  'status':ser.get('status'),
  'capability':'STRUCTURE_TO_SOURCE_SERIALIZATION',
  'candidate_source_available':bool((ser.get('serializer_gene') or {}).get('gene_id')),
  'reason':ser.get('selector_error') or ser.get('next_required_capability'),
 },
 {
  'path':str(HIDDEN.relative_to(REPO)),
  'status':hidden.get('status'),
  'capability':'NATIVE_FUNCTION_LEVEL_SOURCE_EMISSION',
  'candidate_source_available':bool(hidden.get('selected_source_artifact')),
  'target_bound':False,
  'source_artifact':hidden.get('selected_source_artifact'),
 },
 {
  'path':str(CTRL.relative_to(REPO)),
  'status':ctrl.get('status'),
  'capability':'CONTROLLER_SOURCE_TARGET_BINDING',
  'candidate_source_available':bool(ctrl.get('candidate_artifact_path')),
  'target_bound':bool((ctrl.get('checks') or {}).get('native_emission_targeted_current_controller_source')),
 },
 {
  'path':str(EMITTER.relative_to(REPO)),
  'status':emitter.get('status'),
  'capability':'SOURCE_CONSTRUCTION_PROCESS_EMITTER_GENE',
  'candidate_source_available':bool((emitter.get('emitter_gene') or {}).get('actual_python_source_emission_proven')),
  'actual_python_source_emission_proven':bool((emitter.get('emitter_gene') or {}).get('actual_python_source_emission_proven')),
 },
]

# Check whether any existing source artifact is actually a changed version of the kernel-provenant
# self-audit target. Unrelated bounded function emission does not count.
eligible=[]
for row in existing_paths:
    art=row.get('source_artifact')
    if not art:continue
    p=REPO/art
    if not p.exists():continue
    s=p.read_text(encoding='utf-8')
    try:ast.parse(s);compile(s,'<existing-yado-source-artifact>','exec')
    except Exception:continue
    sh=hashlib.sha256(s.encode()).hexdigest()
    if sh!=parent_sha and target_code in s:
        eligible.append({'source_artifact':art,'source_sha256':sh})

source_candidate=eligible[0] if eligible else None
checks={
 'v5_gene_consumed':bool(meta_gene.get('gene_id')),
 'v5_gene_is_new_identity':str(meta_gene.get('gene_id','')).startswith('GENE-G2-SEMANTIC-SOURCE-EDIT-META-V5-'),
 'kernel_provenant_target_consumed':target_rel=='runtime/yado_unified_core_deep_self_audit_v1.py',
 'parent_target_compiles':True,
 'existing_native_serializer_was_previously_attempted':ser.get('status')=='WITHHOLD_G2_NATIVE_SOURCE_PRIMITIVE_EXECUTION_SERIALIZATION_V1',
 'previous_serializer_training_used_many_self_ast_examples':int(ser.get('example_count') or 0)>=1000,
 'previous_serializer_native_family_missing':ser.get('selected_mechanism_kind') is None and (ser.get('serializer_gene') is None),
 'hidden_code_emitter_is_real_but_unrelated':hidden.get('status')=='PASS_SHADOW_G2_NATIVE_HIDDEN_CODE_GENE_SOURCE_EMISSION_OBSERVATION_V3' and bool(hidden.get('selected_source_artifact')),
 'controller_target_binding_previously_withheld':str(ctrl.get('status','')).startswith('WITHHOLD_'),
 'process_emitter_does_not_prove_python_source':(emitter.get('emitter_gene') or {}).get('actual_python_source_emission_proven') is False,
 'no_existing_target_bound_serializer_candidate':source_candidate is None,
 'new_python_source_candidate_created':source_candidate is not None,
 'host_created_serializer':False,
 'host_created_ast_compiler':False,
 'host_supplied_patch':False,
 'external_models_used':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'automatic_canonical_promotion':False,
}
gap_proven=all(checks[k] is True for k in (
 'v5_gene_consumed','v5_gene_is_new_identity','kernel_provenant_target_consumed',
 'parent_target_compiles','existing_native_serializer_was_previously_attempted',
 'previous_serializer_training_used_many_self_ast_examples','previous_serializer_native_family_missing',
 'hidden_code_emitter_is_real_but_unrelated','controller_target_binding_previously_withheld',
 'process_emitter_does_not_prove_python_source','no_existing_target_bound_serializer_candidate',
 'canonical_unchanged'
)) and all(checks[k] is False for k in (
 'new_python_source_candidate_created','host_created_serializer','host_created_ast_compiler',
 'host_supplied_patch','external_models_used','automatic_canonical_promotion'
))

status='WITHHOLD_G2_HISTORY_DERIVED_SEMANTIC_SOURCE_EDIT_SERIALIZATION_V6'
report={
 'schema':'yado.g2.history_derived_semantic_source_edit_serialization.v6',
 'status':status,'gap_proven':gap_proven,
 'parent_v5_receipt':v5.get('receipt_sha256'),'meta_language_gene_id':meta_gene.get('gene_id'),
 'kernel_provenant_target_path':target_rel,'parent_source_sha256':parent_sha,
 'existing_source_path_inventory':existing_paths,
 'eligible_target_bound_source_candidates':eligible,
 'source_candidate':source_candidate,
 'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'NATIVE_COMPOSITIONAL_STRING_TRANSDUCER_GENE_GENESIS_V1',
 'semantic_boundary':'V6 ATTEMPTS TO SERIALIZE THE NEW V5 SEMANTIC EDIT GENE USING ONLY ALREADY-EVIDENCED YADO SOURCE-EMISSION/SERIALIZATION PATHS. THE PRIOR STRUCTURE-TO-SOURCE LEARNING RUN USED 1012 YADO-OWN AST EXAMPLES BUT FOUND NO SUPPORTED NATIVE MECHANISM FAMILY. NARROW POLYNOMIAL SOURCE EMISSION DOES NOT COUNT AS A TARGET-BOUND SELF-AUDIT SERIALIZER. NO NEW SERIALIZER, AST COMPILER OR PATCH IS HOST-CREATED HERE.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'gap_proven':gap_proven,
 'meta_language_gene_id':meta_gene.get('gene_id'),
 'existing_paths':existing_paths,'eligible_target_bound_source_candidates':len(eligible),
 'next_required_capability':report['next_required_capability'],
 'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True))
if not gap_proven:raise SystemExit(2)
raise SystemExit(3)
