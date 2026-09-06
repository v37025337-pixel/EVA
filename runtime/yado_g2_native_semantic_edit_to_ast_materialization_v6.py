from __future__ import annotations

from pathlib import Path
from dataclasses import asdict
import ast,copy,hashlib,inspect,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_skill_admission_runtime_v1 import SkillCandidate
from yado_organ_runtime_native_v1 import tree_predict

V5=REPO/'candidates/kernel-self-generated/g2-target-semantic-source-constructor-genesis-v5.json'
SEM=REPO/'candidates/kernel-self-generated/g2-task-conditioned-semantic-source-edit-meta-language-genesis-v5.json'
BINDER=REPO/'candidates/kernel-self-generated/g2-native-self-created-evidence-binder-gene-v1.json'
ACTION=REPO/'candidates/kernel-self-generated/g2-autonomous-self-improvement-task-v1.json'
OLDV6=REPO/'candidates/kernel-self-generated/g2-history-derived-semantic-source-edit-serialization-v6.json'
TARGET=REPO/'runtime/yado_unified_core_deep_self_audit_v1.py'
OUT=REPO/'candidates/kernel-self-generated/g2-native-semantic-edit-to-ast-materialization-v6.json'
DB=ROOT/'yado_native_semantic_edit_to_ast_materialization_v6.sqlite'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))

v5,sem,binder,action,oldv6=map(load,[V5,SEM,BINDER,ACTION,OLDV6])
if v5.get('status')!='PASS_SHADOW_G2_TARGET_SEMANTIC_SOURCE_CONSTRUCTOR_GENESIS_V5':
    raise RuntimeError('V5_SOURCE_CONSTRUCTOR_PASS_REQUIRED')
if v5.get('next_required_capability')!='NATIVE_SEMANTIC_EDIT_TO_AST_MATERIALIZATION_V6':
    raise RuntimeError('V5_FRONTIER_MISMATCH')
if sem.get('status')!='PASS_SHADOW_G2_TASK_CONDITIONED_SEMANTIC_SOURCE_EDIT_META_LANGUAGE_GENESIS_V5':
    raise RuntimeError('SEMANTIC_EDIT_GENE_REQUIRED')
if not binder.get('self_created_model') or binder.get('external_model_generated') is not False:
    raise RuntimeError('NATIVE_BINDER_REQUIRED')

core=UnifiedYADOCoreV1(REPO)
head_before=copy.deepcopy(core.head)
source=TARGET.read_text(encoding='utf-8')
tree=ast.parse(source)

# Locate the exact kernel-provenant finding and its current status AST without
# constructing any replacement subtree.
target_call=None
for n in ast.walk(tree):
    if not isinstance(n,ast.Call) or not isinstance(n.func,ast.Name) or n.func.id!='add' or len(n.args)<4:
        continue
    a0=n.args[0]
    if isinstance(a0,ast.Constant) and a0.value=='LIVE_RESOURCE_EVIDENCE_SCOPE':
        target_call=n;break
if target_call is None:raise RuntimeError('TARGET_FINDING_NOT_FOUND')
status_node=target_call.args[3]
if not isinstance(status_node,ast.Constant) or status_node.value!='PARTIAL':
    raise RuntimeError('TARGET_STATUS_NO_LONGER_EXPECTED_CONSTANT')

# Reconstruct the binder input only from the real action receipt, exactly as the
# native binder-invention lineage defined it.
binding=action.get('goal_action_binding') or {}
result=binding.get('result') or {}
comp=result.get('comprehension') or {}
base_features={
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
model=binder.get('model')
positive_decision=tree_predict(model,base_features)
counterfactuals=[]
for k in sorted(base_features):
    cf=dict(base_features);cf[k]=False
    counterfactuals.append({'flipped_field':k,'decision':tree_predict(model,cf)})
if positive_decision!='ACCEPT_FRESH_EVIDENCE':
    raise RuntimeError('REAL_EVIDENCE_NOT_ACCEPTED_BY_BINDER')
if not all(x['decision']=='WITHHOLD_FRESH_EVIDENCE' for x in counterfactuals):
    raise RuntimeError('BINDER_COUNTERFACTUAL_FAIL_CLOSED_LOST')

# Candidate AST primitive inventory: public one-required-argument AST callables that
# were already admitted into the V5 research/selection universe. No NodeTransformer,
# replacement AST, condition source, or operator operands are supplied by the host.
studied={str(x.get('primitive')):x for x in v5.get('candidate_primitives',[]) if isinstance(x,dict)}
candidates=[]
for name,row in sorted(studied.items()):
    fn=getattr(ast,name,None)
    if not callable(fn):continue
    try:sig=inspect.signature(fn)
    except Exception:continue
    req=[p for p in sig.parameters.values()
         if p.default is inspect._empty and p.kind in (p.POSITIONAL_ONLY,p.POSITIONAL_OR_KEYWORD)]
    if len(req)!=1:continue
    candidates.append({'name':name,'fn':fn,'study':row,'signature':str(sig)})
if not candidates:raise RuntimeError('NO_RESEARCHED_AST_PRIMITIVES')

def apply_primitive(row,node,accept):
    # Binder supplies context. WITHHOLD must preserve the original node exactly.
    if not accept:return copy.deepcopy(node)
    try:
        out=row['fn'](copy.deepcopy(node))
    except Exception:
        return None
    return out if isinstance(out,ast.AST) else None

def shape_score(row):
    # Positive semantic requirement is intentionally structural only:
    # accepted fresh evidence must produce a conditional status node.
    # The harness does NOT author the condition/body/orelse AST.
    pos=apply_primitive(row,status_node,True)
    neg=apply_primitive(row,status_node,False)
    pos_shape=type(pos).__name__ if isinstance(pos,ast.AST) else None
    neg_dump=ast.dump(neg,annotate_fields=True,include_attributes=False) if isinstance(neg,ast.AST) else None
    original_dump=ast.dump(status_node,annotate_fields=True,include_attributes=False)
    positive_ok=isinstance(pos,ast.IfExp)
    fail_closed_ok=(neg_dump==original_dump)
    return {
      'primitive':row['name'],'positive_shape':pos_shape,
      'positive_conditionalized':positive_ok,
      'counterfactual_preserves_original':fail_closed_ok,
      'structural_score':(float(positive_ok)+float(fail_closed_ok))/2.0,
    }

metrics=[shape_score(r) for r in candidates]
skills=[]
for row,m in zip(candidates,metrics):
    score=float(m['structural_score'])
    sid='SEMANTIC_AST_PRIMITIVE_'+row['name'].upper()
    skills.append(SkillCandidate(
      skill_id=sid,
      artifact_digest=digest({'primitive':row['name'],'signature':row['signature'],'metric':m}),
      structural_valid=m['positive_conditionalized'] and m['counterfactual_preserves_original'],
      semantic_consistency=score,
      fit_baseline=.5,fit_candidate=score,
      heldout_baseline=.5,heldout_candidate=score,
      regression_pass=m['counterfactual_preserves_original'],
      state_integrity=True,rollback_available=True,
      metadata={'primitive':row['name'],'source':'V5_RESEARCHED_AST_RUNTIME'}
    ))

if DB.exists():DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    goal=k.executive.create_goal(
      objective='Materialize the YADO semantic source-edit intent into a new AST while the self-generated evidence binder controls accept/withhold.',
      required_capabilities={'NATIVE_SEMANTIC_EDIT_TO_AST_MATERIALIZATION_V6':1.0},
      success_criteria={'accepted_evidence_changes_ast_shape':True,'invalid_evidence_preserves_parent_ast':True,'rollback':True},
    )
    deficits=k.executive.detect_deficits(goal.goal_id)
    native_goal={'goal_id':goal.goal_id,'deficits':[asdict(d) for d in deficits]}
    selection=k.select_evolution_skills(
      skills,max_skills=1,min_semantic_consistency=1.0,
      min_fit_gain=.49,min_heldout_gain=.49,max_heldout_drop=0.0
    )
finally:
    try:k.close()
    except Exception:pass

selected_id=(selection.get('selected_skill_ids') or [None])[0]
selected_name=selected_id.removeprefix('SEMANTIC_AST_PRIMITIVE_').lower() if selected_id else None
selected_row=next((r for r in candidates if r['name'].lower()==selected_name),None)
selected_metric=next((m for m in metrics if m['primitive'].lower()==selected_name),None)

candidate_ast=None
candidate_source=None
candidate_compile=False
candidate_changed=False
if selected_row and selected_metric and selected_metric['positive_conditionalized']:
    new_node=apply_primitive(selected_row,status_node,True)
    if isinstance(new_node,ast.AST):
        candidate_tree=copy.deepcopy(tree)
        # Locate by stable finding identity in copied tree, then replace only with
        # the YADO-selected primitive output. No host-authored AST subtree exists.
        copied_call=None
        for n in ast.walk(candidate_tree):
            if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='add' and len(n.args)>=4:
                if isinstance(n.args[0],ast.Constant) and n.args[0].value=='LIVE_RESOURCE_EVIDENCE_SCOPE':
                    copied_call=n;break
        if copied_call is not None:
            copied_call.args[3]=copy.deepcopy(new_node)
            ast.fix_missing_locations(candidate_tree)
            candidate_ast=candidate_tree
            try:
                candidate_source=ast.unparse(candidate_tree)+'\n'
                compile(candidate_source,'<yado-semantic-ast-v6>','exec')
                candidate_compile=True
                candidate_changed=candidate_source!=source
            except Exception:
                candidate_source=None

checks={
 'canonical_v5_continuity_active':core.execution_fabric_cls.COMPONENT_ID=='RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V5',
 'v5_source_constructor_consumed':v5.get('selected_primitive')=='unparse',
 'semantic_edit_gene_consumed':bool((sem.get('meta_language_gene') or {}).get('gene_id')),
 'native_binder_consumed':bool(binder.get('gene_id')),
 'real_action_evidence_consumed':bool(action.get('receipt_sha256')),
 'prior_v6_gap_consumed':oldv6.get('gap_proven') is True,
 'binder_accepts_real_evidence':positive_decision=='ACCEPT_FRESH_EVIDENCE',
 'binder_single_fault_counterfactuals_withhold':all(x['decision']=='WITHHOLD_FRESH_EVIDENCE' for x in counterfactuals),
 'researched_ast_primitive_inventory_nonempty':bool(candidates),
 'native_goal_created':True,
 'native_deficit_detected':bool(native_goal['deficits']),
 'native_skill_selector_executed':True,
 'native_selector_selected_ast_transformer':selected_id is not None,
 'selected_transformer_conditionalizes_ast':bool(selected_metric and selected_metric['positive_conditionalized']),
 'selected_transformer_preserves_invalid_counterfactual':bool(selected_metric and selected_metric['counterfactual_preserves_original']),
 'candidate_ast_materialized':candidate_ast is not None,
 'candidate_source_materialized_via_v5_unparse':candidate_source is not None,
 'candidate_source_changed':candidate_changed,
 'candidate_source_compiles':candidate_compile,
 'host_authored_replacement_ast':False,
 'host_authored_condition_expression':False,
 'host_selected_ast_primitive':False,
 'external_models_used':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'automatic_canonical_promotion':False,
}
positive=(
 'canonical_v5_continuity_active','v5_source_constructor_consumed','semantic_edit_gene_consumed',
 'native_binder_consumed','real_action_evidence_consumed','prior_v6_gap_consumed',
 'binder_accepts_real_evidence','binder_single_fault_counterfactuals_withhold',
 'researched_ast_primitive_inventory_nonempty','native_goal_created','native_deficit_detected',
 'native_skill_selector_executed','native_selector_selected_ast_transformer',
 'selected_transformer_conditionalizes_ast','selected_transformer_preserves_invalid_counterfactual',
 'candidate_ast_materialized','candidate_source_materialized_via_v5_unparse',
 'candidate_source_changed','candidate_source_compiles','canonical_unchanged'
)
negative=(
 'host_authored_replacement_ast','host_authored_condition_expression',
 'host_selected_ast_primitive','external_models_used','automatic_canonical_promotion'
)
passed=all(checks[k] is True for k in positive) and all(checks[k] is False for k in negative)
status='PASS_SHADOW_G2_NATIVE_SEMANTIC_EDIT_TO_AST_MATERIALIZATION_V6' if passed else 'WITHHOLD_G2_NATIVE_SEMANTIC_EDIT_TO_AST_MATERIALIZATION_V6'
next_cap='NATIVE_SEMANTIC_AST_CANDIDATE_FRESH_REGRESSION_V7' if passed else 'NATIVE_CONTEXTUAL_AST_TRANSFORMER_GENE_GENESIS_V7'

report={
 'schema':'yado.g2.native_semantic_edit_to_ast_materialization.v6',
 'status':status,
 'parent_v5_receipt':v5.get('receipt_sha256'),
 'semantic_gene_id':(sem.get('meta_language_gene') or {}).get('gene_id'),
 'binder_gene_id':binder.get('gene_id'),
 'action_receipt_sha256':action.get('receipt_sha256'),
 'target_path':str(TARGET.relative_to(REPO)),
 'target_status_ast_before':ast.dump(status_node,annotate_fields=True,include_attributes=False),
 'binder_positive_decision':positive_decision,
 'binder_counterfactuals':counterfactuals,
 'candidate_metrics':metrics,
 'native_goal':native_goal,
 'native_skill_selection':selection,
 'selected_primitive':selected_metric,
 'candidate_source_sha256':hashlib.sha256(candidate_source.encode()).hexdigest() if candidate_source else None,
 'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'V6 TESTS THE MISSING SEMANTIC-INTENT-TO-AST STEP WITHOUT HOST-AUTHORING THE REPLACEMENT AST. THE YADO SELF-GENERATED BINDER CONTROLS ACCEPT/WITHHOLD. ONLY AST PRIMITIVES ALREADY RESEARCHED IN V5 ARE ELIGIBLE, AND YADO NATIVE SKILL ADMISSION SELECTS OR WITHHOLDS. THE HOST REQUIRES ONLY A STRUCTURAL PROPERTY: ACCEPTED EVIDENCE MUST TURN THE STATUS NODE INTO A CONDITIONAL AST WHILE SINGLE-FAULT COUNTERFACTUALS PRESERVE THE ORIGINAL PARTIAL CONSTANT. NO CONDITION/BODY/ORELSE AST IS PROVIDED. WITHHOLD MEANS YADO STILL NEEDS A CONTEXTUAL AST-TRANSFORMER GENE.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'candidate_count':len(candidates),'metrics':metrics,
 'selection':selection,'selected_primitive':selected_metric,
 'candidate_source_sha256':report['candidate_source_sha256'],
 'next_required_capability':next_cap,'checks':checks,
 'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True,default=str))
if not passed:raise SystemExit(2)
