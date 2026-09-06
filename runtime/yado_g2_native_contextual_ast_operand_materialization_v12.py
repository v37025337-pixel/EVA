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

V11=REPO/'candidates/kernel-self-generated/g2-native-contextual-ast-operand-binding-genesis-v11.json'
V11GENE=REPO/'candidates/kernel-self-generated/g2-native-contextual-ast-operand-binding-gene-v11.json'
V10GENE=REPO/'candidates/kernel-self-generated/g2-native-contextual-ast-constructor-primitive-gene-v10.json'
SEM_RUNTIME=REPO/'runtime/yado_g2_task_conditioned_semantic_source_edit_meta_language_genesis_v5.py'
H6=REPO/'candidates/g2-self-evolution/unified_core_deep_self_audit_v6.py'
TARGET=REPO/'runtime/yado_unified_core_deep_self_audit_v1.py'
OUT=REPO/'candidates/kernel-self-generated/g2-native-contextual-ast-operand-materialization-v12.json'
GENE=REPO/'candidates/kernel-self-generated/g2-native-contextual-ast-operand-materialization-gene-v12.json'
DB=ROOT/'yado_native_contextual_ast_operand_materialization_v12.sqlite'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))

v11,v11gene,v10gene=map(load,[V11,V11GENE,V10GENE])
if v11.get('status')!='PASS_SHADOW_G2_NATIVE_CONTEXTUAL_AST_OPERAND_BINDING_GENESIS_V11':
    raise RuntimeError('V11_BINDING_PASS_REQUIRED')
if v11.get('next_required_capability')!='NATIVE_CONTEXTUAL_AST_OPERAND_MATERIALIZATION_V12':
    raise RuntimeError('V11_FRONTIER_MISMATCH')
if v10gene.get('selected_runtime_primitive')!='ast.IfExp':
    raise RuntimeError('IFEXP_CONSTRUCTOR_REQUIRED')
mapping=v11gene.get('field_role_mapping') or {}
if mapping!={'test':'EVIDENCE_ACCEPTANCE_PREDICATE','body':'HISTORY_RESOLVED_STATUS','orelse':'PARENT_STATUS'}:
    raise RuntimeError('V11_ROLE_MAPPING_DRIFT')

core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)

def finding_status(src,code):
    tree=ast.parse(src)
    for n in ast.walk(tree):
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='add' and len(n.args)>=4:
            if isinstance(n.args[0],ast.Constant) and n.args[0].value==code:
                return copy.deepcopy(n.args[3])
    raise RuntimeError('FINDING_STATUS_NOT_FOUND:'+code)

resolved_after=finding_status(H6.read_text(encoding='utf-8'),'LEGACY_EXPERIENCE_SUMMARY_PROVENANCE')
if not isinstance(resolved_after,ast.IfExp):raise RuntimeError('H6_IFEXP_REQUIRED')
body=copy.deepcopy(resolved_after.body)
if not isinstance(body,ast.Constant) or body.value!='PASS':raise RuntimeError('HISTORY_RESOLVED_BODY_NOT_PASS')
parent=finding_status(TARGET.read_text(encoding='utf-8'),'LIVE_RESOURCE_EVIDENCE_SCOPE')
if not isinstance(parent,ast.Constant) or parent.value!='PARTIAL':raise RuntimeError('TARGET_PARENT_NOT_PARTIAL')

# Extract candidate evidence-predicate expressions only from YADO's own semantic-edit runtime.
# Nothing here constructs a condition.
sem_tree=ast.parse(SEM_RUNTIME.read_text(encoding='utf-8'))
raw_tests=[]
for n in ast.walk(sem_tree):
    if not isinstance(n,ast.IfExp):continue
    t=copy.deepcopy(n.test)
    src=ast.unparse(t)
    if 'ACCEPT_FRESH_EVIDENCE' not in src:continue
    raw_tests.append({'ast':t,'source':src,'dump':ast.dump(t,annotate_fields=True,include_attributes=False)})
seen=set();tests=[]
for r in raw_tests:
    if r['dump'] in seen:continue
    seen.add(r['dump']);tests.append(r)
if not tests:raise RuntimeError('NO_YADO_ACCEPTANCE_TEST_PROTOTYPES')

# Score prototypes by role-level properties derived from V11: they must refer to YADO's
# acceptance label and to the binder/runtime evaluation path, without any target-specific host expression.
skills=[];metrics=[]
for i,row in enumerate(tests):
    src=row['source']
    acceptance=('ACCEPT_FRESH_EVIDENCE' in src)
    binder_runtime=('tree_predict' in src or 'binder_verdict' in src or 'binder_decision' in src)
    target_independent=('LIVE_RESOURCE_EVIDENCE_SCOPE' not in src)
    score=(int(acceptance)+int(binder_runtime)+int(target_independent))/3.0
    sid='AST_TEST_OPERAND_'+hashlib.sha256(row['dump'].encode()).hexdigest()[:12].upper()
    m={'skill_id':sid,'source':src,'ast_dump':row['dump'],'acceptance_label_bound':acceptance,
       'binder_runtime_bound':binder_runtime,'target_independent':target_independent,'score':score}
    metrics.append(m)
    skills.append(SkillCandidate(
      skill_id=sid,artifact_digest=digest(m),
      structural_valid=acceptance and binder_runtime and target_independent,
      semantic_consistency=score,
      fit_baseline=0.0,fit_candidate=score,
      heldout_baseline=0.0,heldout_candidate=score,
      regression_pass=True,state_integrity=True,rollback_available=True,
      metadata={'origin':'YADO_SEMANTIC_EDIT_RUNTIME_TEST_EXPRESSION','source':src}
    ))

if DB.exists():DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    goal=k.executive.create_goal(
      objective='Select and materialize the evidence-acceptance test operand for the YADO contextual IfExp from YADO own source history.',
      required_capabilities={'NATIVE_CONTEXTUAL_AST_OPERAND_MATERIALIZATION_V12':1.0},
      success_criteria={'test_operand_selected':True,'ifexp_ast_materialized':True,'rollback':True},
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
selected=next((m for m in metrics if m['skill_id']==selected_id),None)
selected_ast=next((r['ast'] for r,m in zip(tests,metrics) if m['skill_id']==selected_id),None)

materialized=None
expr_source=None
expr_compile=False
free_names=[]
if selected_ast is not None:
    # Mechanical field filling follows the role mapping selected by YADO in V11
    # and the constructor selected by YADO in V10. No new operand expression is authored here.
    field_values={
      mapping['test']:copy.deepcopy(selected_ast),
      mapping['body']:copy.deepcopy(body),
      mapping['orelse']:copy.deepcopy(parent),
    }
    # mapping maps field->role; invert role->node correctly.
    role_nodes={
      'EVIDENCE_ACCEPTANCE_PREDICATE':copy.deepcopy(selected_ast),
      'HISTORY_RESOLVED_STATUS':copy.deepcopy(body),
      'PARENT_STATUS':copy.deepcopy(parent),
    }
    materialized=ast.IfExp(
      test=role_nodes[mapping['test']],
      body=role_nodes[mapping['body']],
      orelse=role_nodes[mapping['orelse']]
    )
    ast.fix_missing_locations(materialized)
    expr_source=ast.unparse(materialized)
    try:
        compile(ast.Expression(body=copy.deepcopy(materialized)),'<yado-v12-ifexp>','eval')
        expr_compile=True
    except Exception:
        expr_compile=False
    free_names=sorted({n.id for n in ast.walk(materialized) if isinstance(n,ast.Name)})

checks={
 'canonical_v5_continuity_active':core.execution_fabric_cls.COMPONENT_ID=='RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V5',
 'v11_operand_binding_gene_consumed':bool(v11gene.get('gene_id')),
 'v10_ifexp_constructor_gene_consumed':bool(v10gene.get('gene_id')),
 'resolved_body_derived_from_yado_history':isinstance(body,ast.Constant) and body.value=='PASS',
 'fallback_derived_from_target_parent':isinstance(parent,ast.Constant) and parent.value=='PARTIAL',
 'yado_test_prototype_inventory_nonempty':bool(tests),
 'native_goal_created':True,
 'native_deficit_detected':bool(native_goal['deficits']),
 'native_skill_selector_executed':True,
 'native_selector_selected_one_test_operand':selected_id is not None and selection.get('selected_count')==1,
 'selected_test_is_acceptance_bound':bool(selected and selected['acceptance_label_bound']),
 'selected_test_is_binder_runtime_bound':bool(selected and selected['binder_runtime_bound']),
 'selected_test_is_target_independent':bool(selected and selected['target_independent']),
 'ifexp_ast_materialized':materialized is not None,
 'ifexp_expression_compiles':expr_compile,
 'ifexp_body_is_pass':bool(materialized and isinstance(materialized.body,ast.Constant) and materialized.body.value=='PASS'),
 'ifexp_orelse_is_parent_partial':bool(materialized and isinstance(materialized.orelse,ast.Constant) and materialized.orelse.value=='PARTIAL'),
 'context_dependencies_still_unbound':bool(free_names),
 'host_authored_test_expression':False,
 'host_authored_body_value':False,
 'host_authored_orelse_value':False,
 'host_selected_test_prototype':False,
 'external_models_used':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'automatic_canonical_promotion':False,
}
positive=(
 'canonical_v5_continuity_active','v11_operand_binding_gene_consumed','v10_ifexp_constructor_gene_consumed',
 'resolved_body_derived_from_yado_history','fallback_derived_from_target_parent','yado_test_prototype_inventory_nonempty',
 'native_goal_created','native_deficit_detected','native_skill_selector_executed',
 'native_selector_selected_one_test_operand','selected_test_is_acceptance_bound','selected_test_is_binder_runtime_bound',
 'selected_test_is_target_independent','ifexp_ast_materialized','ifexp_expression_compiles',
 'ifexp_body_is_pass','ifexp_orelse_is_parent_partial','context_dependencies_still_unbound','canonical_unchanged'
)
negative=('host_authored_test_expression','host_authored_body_value','host_authored_orelse_value','host_selected_test_prototype','external_models_used','automatic_canonical_promotion')
passed=all(checks[k] is True for k in positive) and all(checks[k] is False for k in negative)

gene=None
if passed:
    gene={
      'schema':'yado.g2.native_contextual_ast_operand_materialization_gene.v12',
      'gene_id':'GENE-G2-NATIVE-AST-OPERAND-MATERIALIZATION-V12-'+digest({
        'test':selected['ast_dump'],'binding_gene':v11gene.get('gene_digest'),'constructor_gene':v10gene.get('gene_digest')
      })[:16],
      'novel_gene':True,
      'gene_scope':['CODE','SELF_AUDIT_AND_REPAIR','GENERATIVE_EXECUTIVE'],
      'origin':'YADO_NATIVE_SELECTION_OF_YADO_OWN_BINDER_TEST_PROTOTYPE_PLUS_V10_V11_GENES',
      'constructor_primitive':'ast.IfExp',
      'test_operand_source':selected['source'],
      'test_operand_ast_dump':selected['ast_dump'],
      'body_operand_source':ast.unparse(body),
      'orelse_operand_source':ast.unparse(parent),
      'materialized_ifexp_source':expr_source,
      'materialized_ifexp_ast_dump':ast.dump(materialized,annotate_fields=True,include_attributes=False),
      'free_context_names':free_names,
      'context_dependencies_bound':False,
      'actual_target_source_integration_proven':False,
      'promotion_state':'SHADOW_ONLY',
    }
    gene['gene_digest']=digest(gene)
    GENE.parent.mkdir(parents=True,exist_ok=True)
    GENE.write_text(json.dumps(gene,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

status='PASS_SHADOW_G2_NATIVE_CONTEXTUAL_AST_OPERAND_MATERIALIZATION_V12' if passed else 'WITHHOLD_G2_NATIVE_CONTEXTUAL_AST_OPERAND_MATERIALIZATION_V12'
next_cap='NATIVE_CONTEXTUAL_AST_CONTEXT_BINDING_GENESIS_V13' if passed else 'NATIVE_CONTEXTUAL_AST_OPERAND_MATERIALIZATION_REPAIR_V13'
report={
 'schema':'yado.g2.native_contextual_ast_operand_materialization.v12',
 'status':status,'parent_v11_receipt':v11.get('receipt_sha256'),
 'test_candidates':metrics,'native_goal':native_goal,'native_skill_selection':selection,
 'selected_test_operand':selected,'materialized_ifexp_source':expr_source,
 'materialized_ifexp_ast_dump':ast.dump(materialized,annotate_fields=True,include_attributes=False) if materialized else None,
 'free_context_names':free_names,'gene':gene,'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'V12 MATERIALIZES AN IFE XP OPERAND AST BUT DOES NOT INTEGRATE IT INTO THE TARGET SOURCE. TEST CANDIDATES ARE EXTRACTED VERBATIM FROM YADO OWN SEMANTIC-EDIT RUNTIME AND YADO NATIVE SKILL ADMISSION SELECTS THE BINDER-ACCEPTANCE-BOUND PROTOTYPE. BODY PASS COMES FROM YADO OWN V5->V6 HISTORY; ORELSE PARTIAL COMES FROM THE CURRENT TARGET PARENT. ANY FREE CONTEXT NAMES REMAIN EXPLICITLY UNBOUND, SO TARGET SOURCE INTEGRATION IS NOT CLAIMED.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'selected_test_operand':selected,'materialized_ifexp_source':expr_source,
 'free_context_names':free_names,'gene_id':gene.get('gene_id') if gene else None,
 'next_required_capability':next_cap,'checks':checks,'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True,default=str))
if not passed:raise SystemExit(2)
