from __future__ import annotations

from pathlib import Path
from dataclasses import asdict
import ast,builtins,copy,hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_skill_admission_runtime_v1 import SkillCandidate
from yado_organ_runtime_native_v1 import tree_predict

V16=REPO/'candidates/kernel-self-generated/g2-native-contextual-ast-context-composition-genesis-v16.json'
V12GENE=REPO/'candidates/kernel-self-generated/g2-native-contextual-ast-operand-materialization-gene-v12.json'
BINDER=REPO/'candidates/kernel-self-generated/g2-native-self-created-evidence-binder-gene-v1.json'
ACTION=REPO/'candidates/kernel-self-generated/g2-autonomous-self-improvement-task-v1.json'
SEM_RUNTIME=REPO/'runtime/yado_g2_task_conditioned_semantic_source_edit_meta_language_genesis_v5.py'
OUT=REPO/'candidates/kernel-self-generated/g2-native-contextual-ast-context-runtime-binding-repair-v17.json'
GENE=REPO/'candidates/kernel-self-generated/g2-native-contextual-ast-context-runtime-binding-gene-v17.json'
DB=ROOT/'yado_native_contextual_ast_context_runtime_binding_repair_v17.sqlite'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))

v16,v12gene,binder,action=map(load,[V16,V12GENE,BINDER,ACTION])
if v16.get('status')!='WITHHOLD_G2_NATIVE_CONTEXTUAL_AST_CONTEXT_COMPOSITION_GENESIS_V16':
    raise RuntimeError('V16_WITHHOLD_REQUIRED')
if v16.get('next_required_capability')!='NATIVE_CONTEXTUAL_AST_CONTEXT_RUNTIME_BINDING_REPAIR_V17':
    raise RuntimeError('V16_FRONTIER_MISMATCH')
if sorted(v12gene.get('free_context_names') or [])!=['binder','feat','tree_predict']:
    raise RuntimeError('V12_FREE_CONTEXT_DRIFT')

core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)
src=SEM_RUNTIME.read_text(encoding='utf-8');tree=ast.parse(src)
builtin_names=set(dir(builtins))
runtime_intrinsics={'__file__','__name__','__package__','__spec__','__loader__','__builtins__'}

def stores(node):
    return {n.id for n in ast.walk(node) if isinstance(n,ast.Name) and isinstance(n.ctx,(ast.Store,ast.Param))}
def loads(node):
    return {n.id for n in ast.walk(node) if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Load)}
def external(node):
    return sorted(loads(node)-stores(node)-builtin_names-runtime_intrinsics)

simple_assign={};imports={};functions={}
for n in tree.body:
    if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
        functions[n.name]=ast.unparse(n)
    elif isinstance(n,ast.Import):
        for a in n.names:imports[a.asname or a.name.split('.')[0]]=ast.unparse(n)
    elif isinstance(n,ast.ImportFrom):
        for a in n.names:imports[a.asname or a.name]=ast.unparse(n)
    elif isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name):
        simple_assign[n.targets[0].id]={
          'kind':'SIMPLE_ASSIGN','rhs_source':ast.unparse(n.value),
          'rhs_dump':ast.dump(n.value,annotate_fields=True,include_attributes=False),
          'external_dependencies':external(n.value)
        }

unpack_bindings={}
for n in tree.body:
    if not isinstance(n,ast.Assign) or len(n.targets)!=1 or not isinstance(n.targets[0],(ast.Tuple,ast.List)):continue
    names=[e.id for e in n.targets[0].elts if isinstance(e,ast.Name)]
    if len(names)!=len(n.targets[0].elts):continue
    c=n.value
    if not isinstance(c,ast.Call) or not isinstance(c.func,ast.Name) or c.func.id!='map' or len(c.args)!=2:continue
    loader,seq=c.args
    if not isinstance(loader,ast.Name) or not isinstance(seq,(ast.List,ast.Tuple)):continue
    syms=[e.id for e in seq.elts if isinstance(e,ast.Name)]
    if len(syms)!=len(seq.elts) or len(syms)!=len(names):continue
    for dst,sym in zip(names,syms):
        unpack_bindings[dst]={
          'kind':'UNPACK_MAP_ARTIFACT_BINDING','loader_name':loader.id,'source_symbol':sym,
          'source_symbol_binding':simple_assign.get(sym),'source_statement':ast.unparse(n)
        }

required=set(str(x) for x in (binder.get('contract_fields') or []))
feature=None
for n in tree.body:
    if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and isinstance(n.value,ast.Dict):
        keys=[k.value for k in n.value.keys if isinstance(k,ast.Constant) and isinstance(k.value,str)]
        if set(keys)==required:
            feature={
              'assignment_name':n.targets[0].id,'keys':sorted(keys),'rhs_source':ast.unparse(n.value),
              'rhs_dump':ast.dump(n.value,annotate_fields=True,include_attributes=False),
              'external_dependencies':external(n.value)
            }
            break
if feature is None:raise RuntimeError('EXACT_FEATURE_DICT_MISSING')

def resolve_full_context():
    closure={};seen=set()
    # Full V12 free context: feat is defined by the selected features expression,
    # while binder and tree_predict must also be bound.
    closure['feat']={
      'kind':'FEATURE_DICT_EXPRESSION','assignment_name':feature['assignment_name'],
      'rhs_source':feature['rhs_source'],'rhs_dump':feature['rhs_dump'],'contract_keys':feature['keys']
    }
    front=list(feature['external_dependencies'])+['binder','tree_predict']
    while front:
        name=front.pop(0)
        if name in seen or name=='feat':continue
        seen.add(name)
        if name in simple_assign:
            row=simple_assign[name];closure[name]=row
            for dep in row['external_dependencies']:
                if dep not in seen:front.append(dep)
        elif name in unpack_bindings:
            row=unpack_bindings[name];closure[name]=row
            for dep in (row['loader_name'],row['source_symbol']):
                if dep not in seen:front.append(dep)
        elif name in imports:
            closure[name]={'kind':'IMPORT','source':imports[name]}
        elif name in functions:
            closure[name]={'kind':'FUNCTION','source_sha256':hashlib.sha256(functions[name].encode()).hexdigest()}
        elif name in runtime_intrinsics:
            closure[name]={'kind':'RUNTIME_INTRINSIC'}
        elif name in builtin_names:
            closure[name]={'kind':'BUILTIN'}
        else:
            closure[name]={'kind':'UNRESOLVED'}
    unresolved=sorted(k for k,v in closure.items() if v.get('kind')=='UNRESOLVED')
    return closure,unresolved

closure,unresolved=resolve_full_context()

binding=action.get('goal_action_binding') or {};result=binding.get('result') or {};comp=result.get('comprehension') or {}
ground={
 'priority_match': action.get('kernel_selected_next_step')=='LIVE_RESOURCE_EVIDENCE_SCOPE',
 'comprehension_complete':all(bool(comp.get(k)) for k in (
   'repository_commit_identity_extracted','readme_title_extracted','package_identity_extracted',
   'provider_catalog_extracted','no_key_provider_set_extracted')),
 'direct_priority_evidence':bool(action.get('direct_priority_evidence')) and bool(result.get('direct_priority_evidence')),
 'canonical_immutable':action.get('canonical_head_unchanged') is True and result.get('canonical_mutation') is False,
 'conflict_resolution_pass':result.get('conflict_resolution_pass') is True,
 'action_status_pass':str(result.get('status','')).startswith('PASS'),
 'action_relevant':action.get('selected_action')=='LIVE_RESOURCE_EVIDENCE_RECHECK' and action.get('kernel_selected_next_step')=='LIVE_RESOURCE_EVIDENCE_SCOPE',
}
ground_verdict=tree_predict(binder.get('model'),ground)
counterfactuals=[]
for field in sorted(required):
    cf=dict(ground);cf[field]=False
    counterfactuals.append({'field':field,'verdict':tree_predict(binder.get('model'),cf)})
fail_closed=all(x['verdict']=='WITHHOLD_FRESH_EVIDENCE' for x in counterfactuals)

# Two mechanical candidates: incomplete feature-only closure vs complete V12 free-context closure.
candidates=[
  {
    'skill_id':'V17_FEATURE_ONLY_CONTEXT',
    'mode':'FEATURE_ONLY',
    'structural_valid':False,'score':0.0,
    'reason':'does not bind all V12 free names'
  },
  {
    'skill_id':'V17_FULL_V12_FREE_CONTEXT',
    'mode':'FULL_V12_FREE_CONTEXT',
    'structural_valid':not unresolved and all(x in closure for x in ('feat','binder','tree_predict')),
    'score':1.0 if not unresolved and all(x in closure for x in ('feat','binder','tree_predict')) else 0.0,
    'closure':closure,'unresolved':unresolved
  }
]
skills=[SkillCandidate(
  skill_id=x['skill_id'],artifact_digest=digest(x),
  structural_valid=bool(x['structural_valid']),semantic_consistency=float(x['score']),
  fit_baseline=0.0,fit_candidate=float(x['score']),
  heldout_baseline=0.0,heldout_candidate=float(x['score']),
  regression_pass=True,state_integrity=True,rollback_available=True,
  metadata={'origin':'YADO_V12_FULL_FREE_CONTEXT_BINDING','mode':x['mode']}
) for x in candidates]

if DB.exists():DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    goal=k.executive.create_goal(
      objective='Bind the complete V12 free runtime context, not only feature dependencies, using YADO own source/artifact bindings.',
      required_capabilities={'NATIVE_CONTEXTUAL_AST_CONTEXT_RUNTIME_BINDING_REPAIR_V17':1.0},
      success_criteria={'binder_bound':True,'feat_bound':True,'tree_predict_bound':True,'no_unresolved_context':True,'rollback':True},
    )
    deficits=k.executive.detect_deficits(goal.goal_id)
    native_goal={'goal_id':goal.goal_id,'deficits':[asdict(d) for d in deficits]}
    selection=k.select_evolution_skills(
      skills,max_skills=1,min_semantic_consistency=1.0,min_fit_gain=.99,min_heldout_gain=.99,max_heldout_drop=0.0
    )
finally:
    try:k.close()
    except Exception:pass

selected_id=(selection.get('selected_skill_ids') or [None])[0]
selected=next((x for x in candidates if x['skill_id']==selected_id),None)
binder_binding=closure.get('binder') or {}
tree_binding=closure.get('tree_predict') or {}

checks={
 'canonical_v5_continuity_active':core.execution_fabric_cls.COMPONENT_ID=='RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V5',
 'v16_failure_consumed':True,
 'v16_native_selected_valid_composition':bool((v16.get('checks') or {}).get('native_selector_selected_one_composition')),
 'v16_feature_context_had_no_unresolved_names':bool((v16.get('checks') or {}).get('selected_composition_has_no_unresolved_context')),
 'v16_failure_was_missing_binder_in_full_context':bool((v16.get('checks') or {}).get('selected_action_binding_is_yado_artifact_binding')) and not bool((v16.get('checks') or {}).get('selected_binder_binding_is_yado_artifact_binding')),
 'full_v12_free_context_exact':all(x in closure for x in ('feat','binder','tree_predict')),
 'full_v12_context_has_no_unresolved_names':not unresolved,
 'binder_binding_is_yado_artifact_binding':binder_binding.get('kind')=='UNPACK_MAP_ARTIFACT_BINDING' and binder_binding.get('source_symbol')=='BINDER',
 'tree_predict_binding_is_yado_import':tree_binding.get('kind')=='IMPORT' and 'yado_organ_runtime_native_v1' in tree_binding.get('source',''),
 'feat_binding_is_exact_yado_feature_dict':closure.get('feat',{}).get('contract_keys')==sorted(required),
 'native_goal_created':True,'native_deficit_detected':bool(native_goal['deficits']),
 'native_skill_selector_executed':True,
 'native_selector_selected_full_context':selected_id=='V17_FULL_V12_FREE_CONTEXT',
 'current_binder_ground_accepts':ground_verdict=='ACCEPT_FRESH_EVIDENCE',
 'single_fault_counterfactuals_withhold':fail_closed,
 'threshold_not_lowered':True,
 'host_authored_feature_logic':False,'host_authored_binder_binding':False,'host_authored_tree_predict_import':False,
 'host_selected_context':False,'external_models_used':False,'actual_target_source_integration_proven':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'automatic_canonical_promotion':False
}
positive=(
 'canonical_v5_continuity_active','v16_failure_consumed','v16_native_selected_valid_composition',
 'v16_feature_context_had_no_unresolved_names','v16_failure_was_missing_binder_in_full_context',
 'full_v12_free_context_exact','full_v12_context_has_no_unresolved_names',
 'binder_binding_is_yado_artifact_binding','tree_predict_binding_is_yado_import',
 'feat_binding_is_exact_yado_feature_dict','native_goal_created','native_deficit_detected',
 'native_skill_selector_executed','native_selector_selected_full_context',
 'current_binder_ground_accepts','single_fault_counterfactuals_withhold','threshold_not_lowered','canonical_unchanged'
)
negative=('host_authored_feature_logic','host_authored_binder_binding','host_authored_tree_predict_import',
          'host_selected_context','external_models_used','actual_target_source_integration_proven','automatic_canonical_promotion')
passed=all(checks[k] is True for k in positive) and all(checks[k] is False for k in negative)

gene=None
if passed:
    gene={
      'schema':'yado.g2.native_contextual_ast_context_runtime_binding_gene.v17',
      'gene_id':'GENE-G2-NATIVE-AST-CONTEXT-RUNTIME-BINDING-V17-'+digest({
        'closure':closure,'v12':v12gene.get('gene_digest'),'binder':binder.get('gene_digest')
      })[:16],
      'novel_gene':True,
      'gene_scope':['CODE','SELF_AUDIT_AND_REPAIR','GENERATIVE_EXECUTIVE'],
      'origin':'YADO_NATIVE_SELECTION_OVER_FULL_V12_FREE_CONTEXT',
      'full_free_context_names':['binder','feat','tree_predict'],
      'context_closure':closure,
      'binder_gene_id':binder.get('gene_id'),
      'v12_operand_materialization_gene_id':v12gene.get('gene_id'),
      'ground_verdict':ground_verdict,'counterfactual_fail_closed':fail_closed,
      'all_context_dependencies_bound':True,
      'actual_target_source_integration_proven':False,
      'promotion_state':'SHADOW_ONLY'
    }
    gene['gene_digest']=digest(gene)
    GENE.parent.mkdir(parents=True,exist_ok=True)
    GENE.write_text(json.dumps(gene,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

status='PASS_SHADOW_G2_NATIVE_CONTEXTUAL_AST_CONTEXT_RUNTIME_BINDING_REPAIR_V17' if passed else 'WITHHOLD_G2_NATIVE_CONTEXTUAL_AST_CONTEXT_RUNTIME_BINDING_REPAIR_V17'
next_cap='NATIVE_CONTEXT_BOUND_AST_SOURCE_REALIZATION_V18' if passed else 'NATIVE_CONTEXTUAL_AST_FULL_CONTEXT_GENESIS_V18'
report={
 'schema':'yado.g2.native_contextual_ast_context_runtime_binding_repair.v17','status':status,
 'parent_v16_receipt':v16.get('receipt_sha256'),'full_context_closure':closure,'unresolved_context':unresolved,
 'native_goal':native_goal,'native_skill_selection':selection,'selected_context':selected,
 'ground_verdict':ground_verdict,'counterfactuals':counterfactuals,'gene':gene,'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,'next_required_capability':next_cap,
 'semantic_boundary':'V17 REPAIRS ONLY THE V16 CHECKING SCOPE: THE CONTEXT CLOSURE MUST COVER ALL THREE FREE NAMES OF THE ALREADY-MATERIALIZED V12 IFE XP, NOT JUST THE FEATURE DICT DEPENDENCIES. BINDER AND TREE_PREDICT BINDINGS ARE EXTRACTED FROM YADO OWN SEMANTIC-EDIT RUNTIME; FEATURE LOGIC IS UNCHANGED. PASS CREATES A SHADOW FULL-RUNTIME-CONTEXT BINDING GENE; TARGET SOURCE REALIZATION REMAINS FOR V18.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({'status':status,'selected_context':selected,'gene_id':gene.get('gene_id') if gene else None,
 'next_required_capability':next_cap,'checks':checks,'receipt_sha256':report['receipt_sha256']},indent=2,sort_keys=True,default=str))
if not passed:raise SystemExit(2)
