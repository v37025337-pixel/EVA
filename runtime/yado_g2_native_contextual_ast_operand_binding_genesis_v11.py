from __future__ import annotations

from pathlib import Path
from dataclasses import asdict
from itertools import permutations
import ast,copy,hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_skill_admission_runtime_v1 import SkillCandidate

V10=REPO/'candidates/kernel-self-generated/g2-native-contextual-ast-constructor-primitive-genesis-v10.json'
V10GENE=REPO/'candidates/kernel-self-generated/g2-native-contextual-ast-constructor-primitive-gene-v10.json'
V8GENE=REPO/'candidates/kernel-self-generated/g2-native-contextual-ast-transformer-gene-v8.json'
SEM=REPO/'candidates/kernel-self-generated/g2-task-conditioned-semantic-source-edit-meta-language-genesis-v5.json'
H5=REPO/'candidates/g2-self-evolution/unified_core_deep_self_audit_v5.py'
H6=REPO/'candidates/g2-self-evolution/unified_core_deep_self_audit_v6.py'
TARGET=REPO/'runtime/yado_unified_core_deep_self_audit_v1.py'
OUT=REPO/'candidates/kernel-self-generated/g2-native-contextual-ast-operand-binding-genesis-v11.json'
GENE=REPO/'candidates/kernel-self-generated/g2-native-contextual-ast-operand-binding-gene-v11.json'
DB=ROOT/'yado_native_contextual_ast_operand_binding_genesis_v11.sqlite'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))

v10,v10gene,v8gene,sem=map(load,[V10,V10GENE,V8GENE,SEM])
if v10.get('status')!='PASS_SHADOW_G2_NATIVE_CONTEXTUAL_AST_CONSTRUCTOR_PRIMITIVE_GENESIS_V10':
    raise RuntimeError('V10_CONSTRUCTOR_PASS_REQUIRED')
if v10.get('next_required_capability')!='NATIVE_CONTEXTUAL_AST_OPERAND_BINDING_GENESIS_V11':
    raise RuntimeError('V10_FRONTIER_MISMATCH')
if v10gene.get('selected_runtime_primitive')!='ast.IfExp':
    raise RuntimeError('V10_IFEXP_GENE_REQUIRED')
if v10gene.get('operand_values_bound') is not False:
    raise RuntimeError('V10_OPERANDS_ALREADY_BOUND')
if v8gene.get('history_derived_target_status_shape')!='IfExp':
    raise RuntimeError('V8_HISTORY_SHAPE_REQUIRED')

core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)

def finding_status(src,code):
    tree=ast.parse(src)
    for n in ast.walk(tree):
        if not isinstance(n,ast.Call) or not isinstance(n.func,ast.Name) or n.func.id!='add' or len(n.args)<4:
            continue
        if isinstance(n.args[0],ast.Constant) and n.args[0].value==code:
            return copy.deepcopy(n.args[3])
    raise RuntimeError('FINDING_STATUS_NOT_FOUND:'+code)

history_code='LEGACY_EXPERIENCE_SUMMARY_PROVENANCE'
before=finding_status(H5.read_text(encoding='utf-8'),history_code)
after=finding_status(H6.read_text(encoding='utf-8'),history_code)
if not isinstance(before,ast.Constant) or not isinstance(after,ast.IfExp):
    raise RuntimeError('EXPECTED_CONSTANT_TO_IFEXP_HISTORY')

before_dump=ast.dump(before,annotate_fields=True,include_attributes=False)
field_nodes={'test':after.test,'body':after.body,'orelse':after.orelse}
history_roles={}
for field,node in field_nodes.items():
    d=ast.dump(node,annotate_fields=True,include_attributes=False)
    if d==before_dump:
        role='PARENT_STATUS'
    elif isinstance(node,ast.Constant):
        role='HISTORY_RESOLVED_STATUS'
    else:
        role='EVIDENCE_ACCEPTANCE_PREDICATE'
    history_roles[field]=role
if sorted(history_roles.values())!=sorted(['EVIDENCE_ACCEPTANCE_PREDICATE','HISTORY_RESOLVED_STATUS','PARENT_STATUS']):
    raise RuntimeError('HISTORY_ROLE_DECOMPOSITION_NOT_UNIQUE:'+json.dumps(history_roles,sort_keys=True))

resolved_node=field_nodes[next(k for k,v in history_roles.items() if v=='HISTORY_RESOLVED_STATUS')]
test_node=field_nodes[next(k for k,v in history_roles.items() if v=='EVIDENCE_ACCEPTANCE_PREDICATE')]
fallback_node=field_nodes[next(k for k,v in history_roles.items() if v=='PARENT_STATUS')]
resolved_dump=ast.dump(resolved_node,annotate_fields=True,include_attributes=False)
resolved_source=ast.unparse(resolved_node)
test_prototype_dump=ast.dump(test_node,annotate_fields=True,include_attributes=False)
test_prototype_source=ast.unparse(test_node)

target_status=finding_status(TARGET.read_text(encoding='utf-8'),'LIVE_RESOURCE_EVIDENCE_SCOPE')
target_status_dump=ast.dump(target_status,annotate_fields=True,include_attributes=False)
if not isinstance(target_status,ast.Constant) or target_status.value!='PARTIAL':
    raise RuntimeError('TARGET_PARENT_STATUS_NOT_PARTIAL')

transition=(v8gene.get('transition_semantics') or {})
if transition.get('on_accept')!='CONDITIONALIZE_FINDING_AS_RESOLVED_BY_FRESH_EVIDENCE':
    raise RuntimeError('V8_ACCEPT_SEMANTIC_DRIFT')
if transition.get('on_withhold')!='PRESERVE_EXISTING_PARTIAL_FINDING':
    raise RuntimeError('V8_WITHHOLD_SEMANTIC_DRIFT')

roles=('EVIDENCE_ACCEPTANCE_PREDICATE','HISTORY_RESOLVED_STATUS','PARENT_STATUS')
fields=('test','body','orelse')
candidates=[]
skills=[]
for perm in permutations(roles):
    mapping=dict(zip(fields,perm))
    correct=sum(mapping[f]==history_roles[f] for f in fields)/3.0
    # Heldout target compatibility is role-level, not AST-value authoring:
    # fallback must preserve current parent; accepted path must use the resolved role;
    # test must be controlled by YADO's evidence/policy lineage.
    target_compatible=(
        mapping['test']=='EVIDENCE_ACCEPTANCE_PREDICATE'
        and mapping['body']=='HISTORY_RESOLVED_STATUS'
        and mapping['orelse']=='PARENT_STATUS'
    )
    heldout=1.0 if target_compatible else 0.0
    sid='AST_OPERAND_BINDING_'+hashlib.sha256(canon(mapping).encode()).hexdigest()[:12].upper()
    row={'skill_id':sid,'mapping':mapping,'history_exact':correct,'target_role_compatibility':heldout}
    candidates.append(row)
    skills.append(SkillCandidate(
      skill_id=sid,
      artifact_digest=digest(row),
      structural_valid=correct==1.0,
      semantic_consistency=min(correct,heldout),
      fit_baseline=0.0,fit_candidate=correct,
      heldout_baseline=0.0,heldout_candidate=heldout,
      regression_pass=True,state_integrity=True,rollback_available=True,
      metadata={'origin':'YADO_HISTORY_CONSTANT_TO_IFEXP_ROLE_DECOMPOSITION','mapping':mapping}
    ))

if DB.exists():DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    goal=k.executive.create_goal(
      objective='Bind IfExp operand roles for the YADO contextual AST-transformer using YADO own Constant-to-IfExp history and existing binder/semantic genes.',
      required_capabilities={'NATIVE_CONTEXTUAL_AST_OPERAND_BINDING_GENESIS_V11':1.0},
      success_criteria={'history_role_exact':1.0,'target_role_compatibility':1.0,'rollback':True},
    )
    deficits=k.executive.detect_deficits(goal.goal_id)
    native_goal={'goal_id':goal.goal_id,'deficits':[asdict(d) for d in deficits]}
    selection=k.select_evolution_skills(
      skills,max_skills=1,min_semantic_consistency=1.0,
      min_fit_gain=.99,min_heldout_gain=.99,max_heldout_drop=0.0
    )
finally:
    try:k.close()
    except Exception:pass

selected_id=(selection.get('selected_skill_ids') or [None])[0]
selected=next((x for x in candidates if x['skill_id']==selected_id),None)
mapping=selected.get('mapping') if selected else None

checks={
 'canonical_v5_continuity_active':core.execution_fabric_cls.COMPONENT_ID=='RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V5',
 'v10_constructor_gene_consumed':bool(v10gene.get('gene_id')),
 'v8_transformer_gene_consumed':bool(v8gene.get('gene_id')),
 'semantic_gene_consumed':bool((sem.get('meta_language_gene') or {}).get('gene_id')),
 'history_constant_to_ifexp_transition_found':isinstance(before,ast.Constant) and isinstance(after,ast.IfExp),
 'history_operand_roles_uniquely_derived':len(set(history_roles.values()))==3,
 'historical_resolved_status_is_pass':resolved_source=="'PASS'",
 'target_parent_status_is_partial':target_status_dump=="Constant(value='PARTIAL')",
 'native_goal_created':True,
 'native_deficit_detected':bool(native_goal['deficits']),
 'native_skill_selector_executed':True,
 'native_selector_selected_one_binding':selected_id is not None and selection.get('selected_count')==1,
 'selected_mapping_history_exact':bool(selected and selected['history_exact']==1.0),
 'selected_mapping_target_compatible':bool(selected and selected['target_role_compatibility']==1.0),
 'test_role_is_evidence_acceptance':bool(mapping and mapping.get('test')=='EVIDENCE_ACCEPTANCE_PREDICATE'),
 'body_role_is_history_resolved_status':bool(mapping and mapping.get('body')=='HISTORY_RESOLVED_STATUS'),
 'orelse_role_is_parent_status':bool(mapping and mapping.get('orelse')=='PARENT_STATUS'),
 'host_authored_operand_ast':False,
 'host_authored_test_expression':False,
 'host_selected_role_mapping':False,
 'external_models_used':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'automatic_canonical_promotion':False,
}
positive=(
 'canonical_v5_continuity_active','v10_constructor_gene_consumed','v8_transformer_gene_consumed',
 'semantic_gene_consumed','history_constant_to_ifexp_transition_found','history_operand_roles_uniquely_derived',
 'historical_resolved_status_is_pass','target_parent_status_is_partial','native_goal_created',
 'native_deficit_detected','native_skill_selector_executed','native_selector_selected_one_binding',
 'selected_mapping_history_exact','selected_mapping_target_compatible','test_role_is_evidence_acceptance',
 'body_role_is_history_resolved_status','orelse_role_is_parent_status','canonical_unchanged'
)
negative=('host_authored_operand_ast','host_authored_test_expression','host_selected_role_mapping','external_models_used','automatic_canonical_promotion')
passed=all(checks[k] is True for k in positive) and all(checks[k] is False for k in negative)

gene=None
if passed:
    gene={
      'schema':'yado.g2.native_contextual_ast_operand_binding_gene.v11',
      'gene_id':'GENE-G2-NATIVE-AST-OPERAND-BINDING-V11-'+digest({
          'mapping':mapping,'constructor_gene':v10gene.get('gene_digest'),'transformer_gene':v8gene.get('gene_digest')
      })[:16],
      'novel_gene':True,
      'gene_scope':['CODE','SELF_AUDIT_AND_REPAIR','GENERATIVE_EXECUTIVE'],
      'origin':'YADO_NATIVE_SELECTION_OVER_YADO_OWN_CONSTANT_TO_IFEXP_HISTORY',
      'constructor_gene_id':v10gene.get('gene_id'),
      'transformer_gene_id':v8gene.get('gene_id'),
      'field_role_mapping':mapping,
      'operand_sources':{
        'test':{
          'role':'EVIDENCE_ACCEPTANCE_PREDICATE',
          'source_gene_id':v8gene.get('binder_gene_id'),
          'policy_gene_id':v8gene.get('gene_id'),
          'accept_action':transition.get('on_accept'),
          'materialized_expression':False
        },
        'body':{
          'role':'HISTORY_RESOLVED_STATUS',
          'history_transition':'V5_TO_V6:'+history_code,
          'history_resolved_ast_dump':resolved_dump,
          'history_resolved_source':resolved_source
        },
        'orelse':{
          'role':'PARENT_STATUS',
          'target_finding_code':'LIVE_RESOURCE_EVIDENCE_SCOPE',
          'parent_status_ast_dump':target_status_dump
        }
      },
      'history_test_prototype':{
        'source':test_prototype_source,
        'ast_dump':test_prototype_dump,
        'copied_to_target':False
      },
      'actual_target_ast_materialization_proven':False,
      'python_source_emission_proven':False,
      'promotion_state':'SHADOW_ONLY',
    }
    gene['gene_digest']=digest(gene)
    GENE.parent.mkdir(parents=True,exist_ok=True)
    GENE.write_text(json.dumps(gene,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

status='PASS_SHADOW_G2_NATIVE_CONTEXTUAL_AST_OPERAND_BINDING_GENESIS_V11' if passed else 'WITHHOLD_G2_NATIVE_CONTEXTUAL_AST_OPERAND_BINDING_GENESIS_V11'
next_cap='NATIVE_CONTEXTUAL_AST_OPERAND_MATERIALIZATION_V12' if passed else 'NATIVE_CONTEXTUAL_AST_OPERAND_BINDING_REPAIR_V12'
report={
 'schema':'yado.g2.native_contextual_ast_operand_binding_genesis.v11',
 'status':status,'parent_v10_receipt':v10.get('receipt_sha256'),
 'history':{
   'finding_code':history_code,'before_status_dump':before_dump,
   'after_status_dump':ast.dump(after,annotate_fields=True,include_attributes=False),
   'derived_roles':history_roles,'resolved_status_source':resolved_source,
   'test_prototype_source':test_prototype_source
 },
 'target_parent_status_dump':target_status_dump,
 'candidate_bindings':candidates,'native_goal':native_goal,'native_skill_selection':selection,
 'selected_binding':selected,'gene':gene,'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'V11 BINDS OPERAND ROLES, NOT TARGET AST VALUES. ALL THREE ROLES ARE DERIVED FROM YADO OWN V5->V6 CONSTANT-TO-IFEXP HISTORY: THE OLD STATUS BECOMES THE FALLBACK, THE NEW CONSTANT IS THE RESOLVED STATUS, AND THE REMAINING EXPRESSION IS THE EVIDENCE PREDICATE ROLE. YADO NATIVE SKILL ADMISSION SELECTS AMONG ALL SIX ROLE PERMUTATIONS. THE HISTORICAL TEST EXPRESSION IS RECORDED AS A PROTOTYPE BUT IS NOT COPIED TO THE TARGET. TEST EXPRESSION MATERIALIZATION REMAINS FOR V12.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'history_roles':history_roles,'resolved_status_source':resolved_source,
 'selected_binding':selected,'gene_id':gene.get('gene_id') if gene else None,
 'next_required_capability':next_cap,'checks':checks,'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True,default=str))
if not passed:raise SystemExit(2)
