from __future__ import annotations
from pathlib import Path
import ast,copy,hashlib,inspect,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_evolutionary_genome_v2 import YADOEvolutionaryGenomeV2
from yado_evolutionary_genome_v3 import YADOEvolutionaryGenomeV3
from yado_generic_compile_repair_meta_language_v1 import GenericCompileRepairMetaLanguageV1
from yado_generic_history_compile_repair_meta_language_v1 import GenericHistoryCompileRepairMetaLanguageV1
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive

V3=REPO/'candidates/kernel-self-generated/g2-experience-conditioned-mutation-family-selection-v3.json'
V2=REPO/'candidates/kernel-self-generated/g2-experience-conditioned-deficit-to-mutation-binding-v2.json'
CURRENT=REPO/'candidates/kernel-self-generated/g2-native-action-evidence-binder-source-realization-v1.json'
BINDER=REPO/'candidates/kernel-self-generated/g2-native-self-created-evidence-binder-gene-v1.json'
EMITTER=REPO/'candidates/kernel-self-generated/g2-experience-conditioned-native-emitter-gene-genesis-v3.json'
WHOLE=REPO/'candidates/kernel-self-generated/g2-coding-whole-function-substrate-expansion-v3.json'
OUT=REPO/'candidates/kernel-self-generated/g2-experience-conditioned-novel-gene-genesis-v4.json'
DB=ROOT/'yado_experience_conditioned_novel_gene_genesis_v4.sqlite'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))

v3,v2,current,binder,emitter,whole=map(load,[V3,V2,CURRENT,BINDER,EMITTER,WHOLE])
if v3.get('status')!='PASS_SHADOW_G2_EXPERIENCE_CONDITIONED_MUTATION_FAMILY_SELECTION_V3':
    raise RuntimeError('V3_PASS_REQUIRED')
if (v3.get('mutation_family_decision') or {}).get('family')!='INVENT_NEW_GENE':
    raise RuntimeError('V3_INVENT_FAMILY_REQUIRED')
if v2.get('status')!='PASS_SHADOW_G2_EXPERIENCE_CONDITIONED_DEFICIT_TO_MUTATION_BINDING_V2':
    raise RuntimeError('V2_PASS_REQUIRED')
if current.get('status')!='WITHHOLD_G2_NATIVE_ACTION_EVIDENCE_BINDER_SOURCE_REALIZATION_V1':
    raise RuntimeError('CURRENT_NATIVE_SOURCE_WITHHOLD_REQUIRED')
if emitter.get('status')!='PASS_SHADOW_G2_EXPERIENCE_CONDITIONED_NATIVE_EMITTER_GENE_GENESIS_V3':
    raise RuntimeError('EMITTER_GENE_PARENT_REQUIRED')

core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)
target_rel=str(current.get('kernel_provenant_target_path') or '')
if not target_rel.startswith('runtime/') or not target_rel.endswith('.py'):
    raise RuntimeError('KERNEL_PROVENANT_TARGET_INVALID')
target=REPO/target_rel
source=target.read_text(encoding='utf-8')
compile_error=None
try:compile(source,str(target),'exec')
except SyntaxError as e:compile_error={'msg':e.msg,'lineno':e.lineno,'offset':e.offset}

# Inspect the actual invention API surface rather than inferring it from names.
def public_methods(cls):
    out={}
    for name in sorted(dir(cls)):
        if name.startswith('_'):continue
        fn=getattr(cls,name,None)
        if callable(fn):
            try:out[name]=str(inspect.signature(fn))
            except Exception:out[name]='<signature-unavailable>'
    return out

v2_api=public_methods(YADOEvolutionaryGenomeV2)
v3_api=public_methods(YADOEvolutionaryGenomeV3)
source_invention_methods=[
    name for name in sorted(set(v2_api)|set(v3_api))
    if any(t in name.lower() for t in ('source','ast','edit','patch','rewrite'))
]

# A compile-only language must be inert on an already compiling semantic target.
compile_program=next(iter(GenericCompileRepairMetaLanguageV1.programs()))
compile_attempt=GenericCompileRepairMetaLanguageV1.execute(compile_program,source)
compile_changed=isinstance(compile_attempt,str) and compile_attempt!=source

history_program=next(iter(GenericHistoryCompileRepairMetaLanguageV1.programs()))
history_attempt=GenericHistoryCompileRepairMetaLanguageV1.repair(history_program,source,[source])
history_changed=isinstance(history_attempt.get('source'),str) and history_attempt.get('source')!=source

unlocked={(str(x.get('path')),str(x.get('function_name'))) for x in whole.get('unlocked_candidates') or []}
target_in_whole_substrate=any(p==target_rel for p,_ in unlocked)

emitter_gene=emitter.get('emitter_gene') or {}
emitter_actual_source=bool(emitter_gene.get('actual_python_source_emission_proven'))

# Query the real lower native snapshots from RC8.
if DB.exists():DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    meta_snapshot=k.meta_grammar_snapshot() if hasattr(k,'meta_grammar_snapshot') else None
    alg_snapshot=k.algorithm_genesis_snapshot() if hasattr(k,'algorithm_genesis_snapshot') else None
finally:
    try:k.close()
    except Exception:pass

meta_policy=(meta_snapshot or {}).get('policy') or {}
alg_policy=(alg_snapshot or {}).get('policy') or {}
meta_operators=list((meta_snapshot or {}).get('operators') or [])
alg_constructors=list((alg_snapshot or {}).get('constructors') or [])

binder_contract=set(map(str,binder.get('contract_fields') or []))
required_semantics={
 'direct_priority_evidence','comprehension_complete','conflict_resolution_pass',
 'action_status_pass','canonical_immutable','action_relevant'
}
binder_contract_complete=required_semantics.issubset(binder_contract)

new_gene=None
native_source_candidate=None
# Fail closed: none of the existing native invention APIs expose a source/AST/edit
# constructor for this already-compiling semantic target. V4 is forbidden to fabricate
# an operator family or source template merely to turn the run green.

checks={
 'v3_invent_new_gene_decision_consumed':True,
 'experience_bound_target_consumed':(v2.get('bound_deficit') or {}).get('target_capability')==(v3.get('mutation_family_decision') or {}).get('target_capability'),
 'kernel_provenant_target_consumed':target_rel==current.get('kernel_provenant_target_path'),
 'target_already_compiles':compile_error is None,
 'binder_contract_available':binder_contract_complete,
 'emitter_gene_available':bool(emitter_gene.get('gene_id')),
 'emitter_gene_does_not_claim_python_source_emission':emitter_actual_source is False,
 'genome_v2_v3_have_no_source_edit_invention_api':len(source_invention_methods)==0,
 'generic_compile_repair_is_inert_on_semantic_target':compile_changed is False,
 'generic_history_compile_repair_is_inert_on_compiling_target':history_changed is False,
 'target_not_in_proven_whole_function_substrate':target_in_whole_substrate is False,
 'lower_meta_grammar_exists_but_is_bounded':bool(meta_operators) and meta_policy.get('unrestricted_self_code_rewrite') is False,
 'lower_algorithm_genesis_exists_but_is_bounded':bool(alg_constructors) and alg_policy.get('unrestricted_self_code_rewrite') is False,
 'new_semantic_source_edit_gene_created':new_gene is not None,
 'new_python_source_candidate_created':native_source_candidate is not None,
 'host_supplied_source_edit_grammar':False,
 'host_supplied_ast_skeleton':False,
 'host_supplied_patch':False,
 'external_models_used':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'automatic_canonical_promotion':False,
}

# This is a deliberate WITHHOLD-capability proof. The first twelve positive facts plus
# absence of a fabricated gene/source prove the exact architecture gap.
gap_proven=all(checks[k] is True for k in (
 'v3_invent_new_gene_decision_consumed','experience_bound_target_consumed',
 'kernel_provenant_target_consumed','target_already_compiles','binder_contract_available',
 'emitter_gene_available','emitter_gene_does_not_claim_python_source_emission',
 'genome_v2_v3_have_no_source_edit_invention_api',
 'generic_compile_repair_is_inert_on_semantic_target',
 'generic_history_compile_repair_is_inert_on_compiling_target',
 'target_not_in_proven_whole_function_substrate',
 'lower_meta_grammar_exists_but_is_bounded','lower_algorithm_genesis_exists_but_is_bounded',
 'canonical_unchanged'
)) and all(checks[k] is False for k in (
 'new_semantic_source_edit_gene_created','new_python_source_candidate_created',
 'host_supplied_source_edit_grammar','host_supplied_ast_skeleton','host_supplied_patch',
 'external_models_used','automatic_canonical_promotion'
))

status='WITHHOLD_G2_EXPERIENCE_CONDITIONED_NOVEL_GENE_GENESIS_V4'
report={
 'schema':'yado.g2.experience_conditioned_novel_gene_genesis.v4',
 'status':status,
 'gap_proven':gap_proven,
 'parent_v3_receipt':v3.get('receipt_sha256'),
 'parent_v2_receipt':v2.get('receipt_sha256'),
 'current_failure_receipt':current.get('receipt_sha256'),
 'kernel_provenant_target_path':target_rel,
 'kernel_provenant_target_sha256':hashlib.sha256(source.encode()).hexdigest(),
 'binder_gene_id':binder.get('gene_id'),
 'emitter_gene_id':emitter_gene.get('gene_id'),
 'existing_invention_api':{'genome_v2':v2_api,'genome_v3':v3_api,'source_edit_methods':source_invention_methods},
 'lower_native_genesis':{'meta_grammar':meta_snapshot,'algorithm_genesis':alg_snapshot},
 'compile_repair_probe':{'target_compile_error':compile_error,'changed_source':compile_changed},
 'history_compile_repair_probe':{'status':history_attempt.get('status'),'changed_source':history_changed},
 'whole_function_substrate':{'target_present':target_in_whole_substrate,'unlocked_count':len(unlocked)},
 'checks':checks,
 'new_gene':new_gene,'native_source_candidate':native_source_candidate,
 'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'TASK_CONDITIONED_SEMANTIC_SOURCE_EDIT_META_LANGUAGE_GENESIS_V5',
 'semantic_boundary':'V4 IS AN EXPLICIT ARCHITECTURE-GAP PROOF AFTER YADO ITSELF SELECTED INVENT_NEW_GENE. EXISTING RELATION/EVENT GENOME INVENTION, COMPILE-REPAIR LANGUAGES, WHOLE-FUNCTION SUBSTRATE, RC5 ALGORITHM CONSTRUCTORS, RC6 META-GRAMMAR AND THE NATIVE EMITTER GENE DO NOT EXPOSE A TASK-CONDITIONED SEMANTIC SOURCE-EDIT PRIMITIVE SPACE FOR THIS ALREADY-COMPILING TARGET. THE HOST DOES NOT FABRICATE A PATCH, AST SKELETON OR SOURCE-EDIT GRAMMAR. THE NEXT FRONTIER IS TO GENESIZE THAT PRIMITIVE SPACE FROM YADO OWN CODE/FAILURE HISTORY.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'gap_proven':gap_proven,
 'target':target_rel,'source_edit_invention_methods':source_invention_methods,
 'meta_grammar_operators':meta_operators,'algorithm_constructors':alg_constructors,
 'target_in_whole_substrate':target_in_whole_substrate,
 'new_gene_created':False,'native_source_candidate_created':False,
 'next_required_capability':report['next_required_capability'],
 'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True))
if not gap_proven:raise SystemExit(2)
raise SystemExit(3)
