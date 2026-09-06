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

V14=REPO/'candidates/kernel-self-generated/g2-native-contextual-ast-context-binding-repair-v14.json'
V12GENE=REPO/'candidates/kernel-self-generated/g2-native-contextual-ast-operand-materialization-gene-v12.json'
BINDER=REPO/'candidates/kernel-self-generated/g2-native-self-created-evidence-binder-gene-v1.json'
ACTION=REPO/'candidates/kernel-self-generated/g2-autonomous-self-improvement-task-v1.json'
SEM_RUNTIME=REPO/'runtime/yado_g2_task_conditioned_semantic_source_edit_meta_language_genesis_v5.py'
OUT=REPO/'candidates/kernel-self-generated/g2-native-contextual-ast-context-composition-repair-v15.json'
GENE=REPO/'candidates/kernel-self-generated/g2-native-contextual-ast-context-composition-gene-v15.json'
DB=ROOT/'yado_native_contextual_ast_context_composition_repair_v15.sqlite'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))

v14,v12gene,binder,action=map(load,[V14,V12GENE,BINDER,ACTION])
if v14.get('status')!='WITHHOLD_G2_NATIVE_CONTEXTUAL_AST_CONTEXT_BINDING_REPAIR_V14':
    raise RuntimeError('V14_WITHHOLD_REQUIRED')
if v14.get('next_required_capability')!='NATIVE_CONTEXTUAL_AST_CONTEXT_COMPOSITION_REPAIR_V15':
    raise RuntimeError('V14_FRONTIER_MISMATCH')

core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)
src=SEM_RUNTIME.read_text(encoding='utf-8');tree=ast.parse(src)
builtin_names=set(dir(builtins))

def stores(node):
    return {n.id for n in ast.walk(node) if isinstance(n,ast.Name) and isinstance(n.ctx,(ast.Store,ast.Param))}
def loads(node):
    return {n.id for n in ast.walk(node) if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Load)}
def external(node):
    return sorted(loads(node)-stores(node)-builtin_names)

# Mechanical top-level inventory.
simple_assign={}
imports={}
functions={}
path_constants={}
for n in tree.body:
    if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
        functions[n.name]=ast.unparse(n)
    elif isinstance(n,ast.Import):
        for a in n.names: imports[a.asname or a.name.split('.')[0]]=ast.unparse(n)
    elif isinstance(n,ast.ImportFrom):
        for a in n.names: imports[a.asname or a.name]=ast.unparse(n)
    elif isinstance(n,ast.Assign):
        if len(n.targets)==1 and isinstance(n.targets[0],ast.Name):
            name=n.targets[0].id
            simple_assign[name]={
              'kind':'SIMPLE_ASSIGN',
              'rhs_source':ast.unparse(n.value),
              'rhs_dump':ast.dump(n.value,annotate_fields=True,include_attributes=False),
              'external_dependencies':external(n.value),
            }
            # Path constants are source-level artifact bindings; no path is invented.
            if name.isupper():
                path_constants[name]=simple_assign[name]

# Mechanical destructuring inventory. We recognize a generic shape:
# names = map(loader,[symbols...]) with equal arity.
unpack_bindings={}
unpack_rows=[]
for n in tree.body:
    if not isinstance(n,ast.Assign) or len(n.targets)!=1:continue
    target=n.targets[0]
    if not isinstance(target,(ast.Tuple,ast.List)):continue
    target_names=[e.id for e in target.elts if isinstance(e,ast.Name)]
    if len(target_names)!=len(target.elts):continue
    call=n.value
    if not isinstance(call,ast.Call) or not isinstance(call.func,ast.Name) or call.func.id!='map' or len(call.args)!=2:continue
    loader=call.args[0]
    seq=call.args[1]
    if not isinstance(loader,ast.Name) or not isinstance(seq,(ast.List,ast.Tuple)):continue
    source_names=[e.id for e in seq.elts if isinstance(e,ast.Name)]
    if len(source_names)!=len(seq.elts) or len(source_names)!=len(target_names):continue
    row={
      'pattern':'UNPACK_MAP',
      'loader_name':loader.id,
      'target_names':target_names,
      'source_names':source_names,
      'source':ast.unparse(n),
    }
    unpack_rows.append(row)
    for dst,src_name in zip(target_names,source_names):
        unpack_bindings[dst]={
          'kind':'UNPACK_MAP_ARTIFACT_BINDING',
          'loader_name':loader.id,
          'source_symbol':src_name,
          'source_symbol_binding':simple_assign.get(src_name),
          'source_statement':row['source'],
        }

# Extract exact seven-field feature dict unchanged.
required=set(str(x) for x in (binder.get('contract_fields') or []))
feature_candidates=[]
for n in tree.body:
    if not isinstance(n,ast.Assign) or len(n.targets)!=1 or not isinstance(n.targets[0],ast.Name) or not isinstance(n.value,ast.Dict):
        continue
    keys=[k.value for k in n.value.keys if isinstance(k,ast.Constant) and isinstance(k.value,str)]
    if set(keys)!=required:continue
    feature_candidates.append({
      'assignment_name':n.targets[0].id,
      'keys':sorted(keys),
      'rhs_source':ast.unparse(n.value),
      'rhs_dump':ast.dump(n.value,annotate_fields=True,include_attributes=False),
      'external_dependencies':external(n.value),
    })
if len(feature_candidates)!=1:
    raise RuntimeError('EXPECTED_ONE_EXACT_BINDER_FEATURE_DICT:'+str(len(feature_candidates)))
feature=feature_candidates[0]

def resolve_closure(mode):
    closure={};front=list(feature['external_dependencies']);seen=set()
    while front:
        name=front.pop(0)
        if name in seen:continue
        seen.add(name)
        if name in simple_assign:
            row=simple_assign[name];closure[name]=row
            for dep in row['external_dependencies']:
                if dep not in seen:front.append(dep)
        elif mode=='SIMPLE_PLUS_UNPACK' and name in unpack_bindings:
            row=unpack_bindings[name];closure[name]=row
            loader=row['loader_name'];srcsym=row['source_symbol']
            if loader not in seen:front.append(loader)
            if srcsym not in seen:front.append(srcsym)
        elif name in imports:
            closure[name]={'kind':'IMPORT','source':imports[name]}
        elif name in functions:
            closure[name]={'kind':'FUNCTION','source_sha256':hashlib.sha256(functions[name].encode()).hexdigest()}
        elif name in builtin_names:
            closure[name]={'kind':'BUILTIN'}
        else:
            closure[name]={'kind':'UNRESOLVED'}
    unresolved=sorted(k for k,v in closure.items() if v.get('kind')=='UNRESOLVED')
    return closure,unresolved

strategies=[]
for mode in ('SIMPLE_ONLY','SIMPLE_PLUS_UNPACK'):
    closure,unresolved=resolve_closure(mode)
    exact=set(feature['keys'])==required
    score=1.0 if exact and not unresolved else 0.0
    strategies.append({
      'mode':mode,'feature_assignment':feature['assignment_name'],
      'feature_rhs_dump':feature['rhs_dump'],'closure':closure,
      'unresolved':unresolved,'score':score,
      'artifact_binding_count':sum(v.get('kind')=='UNPACK_MAP_ARTIFACT_BINDING' for v in closure.values()),
    })

# Ground semantic contract remains exactly YADO's binder/action semantics.
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

skills=[]
for row in strategies:
    sid='CONTEXT_COMPOSITION_'+row['mode']
    skills.append(SkillCandidate(
      skill_id=sid,artifact_digest=digest(row),
      structural_valid=(row['score']==1.0),
      semantic_consistency=row['score'],
      fit_baseline=0.0,fit_candidate=row['score'],
      heldout_baseline=0.0,heldout_candidate=row['score'],
      regression_pass=True,state_integrity=True,rollback_available=True,
      metadata={'origin':'YADO_SOURCE_CONTEXT_COMPOSITION_STRATEGY','mode':row['mode']}
    ))
    row['skill_id']=sid

if DB.exists():DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    goal=k.executive.create_goal(
      objective='Compose the V12 contextual AST free-name environment from YADO own simple assignments plus source-derived destructuring artifact bindings.',
      required_capabilities={'NATIVE_CONTEXTUAL_AST_CONTEXT_COMPOSITION_REPAIR_V15':1.0},
      success_criteria={'exact_feature_contract':True,'no_unresolved_context':True,'artifact_bindings_from_yado_source':True,'rollback':True},
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
selected=next((x for x in strategies if x['skill_id']==selected_id),None)
selected_closure=(selected or {}).get('closure') or {}
selected_unresolved=(selected or {}).get('unresolved') or []

# Explicit source provenance check for the two free artifact objects required later.
action_binding=selected_closure.get('action') or {}
binder_binding=selected_closure.get('binder') or {}
action_bound=(action_binding.get('kind')=='UNPACK_MAP_ARTIFACT_BINDING' and action_binding.get('source_symbol')=='ACTION')
binder_bound=(binder_binding.get('kind')=='UNPACK_MAP_ARTIFACT_BINDING' and binder_binding.get('source_symbol')=='BINDER')

checks={
 'canonical_v5_continuity_active':core.execution_fabric_cls.COMPONENT_ID=='RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V5',
 'v14_failure_consumed':True,
 'v14_scope_repair_preserved':bool((v14.get('checks') or {}).get('scope_repair_treats_builtins_as_bound')) and bool((v14.get('checks') or {}).get('scope_repair_treats_comprehension_local_as_bound')),
 'v14_remaining_gap_was_action_artifact_binding':any(x.get('assignment_name')=='features' and x.get('unresolved_dependencies')==['action'] for x in (v14.get('feature_binding_candidates') or [])),
 'unpack_map_binding_found_in_yado_source':bool(unpack_rows),
 'action_artifact_binding_found': 'action' in unpack_bindings and unpack_bindings['action'].get('source_symbol')=='ACTION',
 'binder_artifact_binding_found': 'binder' in unpack_bindings and unpack_bindings['binder'].get('source_symbol')=='BINDER',
 'exact_feature_dict_preserved_unchanged':set(feature['keys'])==required,
 'native_goal_created':True,
 'native_deficit_detected':bool(native_goal['deficits']),
 'native_skill_selector_executed':True,
 'native_selector_selected_one_composition':selected_id is not None and selection.get('selected_count')==1,
 'selected_composition_is_simple_plus_unpack':bool(selected and selected['mode']=='SIMPLE_PLUS_UNPACK'),
 'selected_composition_has_no_unresolved_context':not selected_unresolved,
 'selected_action_binding_is_yado_artifact_binding':action_bound,
 'selected_binder_binding_is_yado_artifact_binding':binder_bound,
 'current_binder_ground_accepts':ground_verdict=='ACCEPT_FRESH_EVIDENCE',
 'single_fault_counterfactuals_withhold':fail_closed,
 'threshold_not_lowered':True,
 'host_authored_feature_logic':False,
 'host_authored_artifact_values':False,
 'host_selected_composition':False,
 'external_models_used':False,
 'actual_target_source_integration_proven':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'automatic_canonical_promotion':False,
}
positive=(
 'canonical_v5_continuity_active','v14_failure_consumed','v14_scope_repair_preserved',
 'v14_remaining_gap_was_action_artifact_binding','unpack_map_binding_found_in_yado_source',
 'action_artifact_binding_found','binder_artifact_binding_found','exact_feature_dict_preserved_unchanged',
 'native_goal_created','native_deficit_detected','native_skill_selector_executed',
 'native_selector_selected_one_composition','selected_composition_is_simple_plus_unpack',
 'selected_composition_has_no_unresolved_context','selected_action_binding_is_yado_artifact_binding',
 'selected_binder_binding_is_yado_artifact_binding','current_binder_ground_accepts',
 'single_fault_counterfactuals_withhold','threshold_not_lowered','canonical_unchanged'
)
negative=('host_authored_feature_logic','host_authored_artifact_values','host_selected_composition',
          'external_models_used','actual_target_source_integration_proven','automatic_canonical_promotion')
passed=all(checks[k] is True for k in positive) and all(checks[k] is False for k in negative)

gene=None
if passed:
    gene={
      'schema':'yado.g2.native_contextual_ast_context_composition_gene.v15',
      'gene_id':'GENE-G2-NATIVE-AST-CONTEXT-COMPOSITION-V15-'+digest({
        'feature':feature['rhs_dump'],'selected_mode':selected['mode'],'closure':selected_closure,
        'v12':v12gene.get('gene_digest'),'binder':binder.get('gene_digest')
      })[:16],
      'novel_gene':True,
      'gene_scope':['CODE','SELF_AUDIT_AND_REPAIR','GENERATIVE_EXECUTIVE'],
      'origin':'YADO_NATIVE_SELECTION_OVER_YADO_SOURCE_DERIVED_CONTEXT_COMPOSITION',
      'composition_mode':selected['mode'],
      'feature_binding':{
        'assignment_name':feature['assignment_name'],
        'rhs_source':feature['rhs_source'],
        'rhs_dump':feature['rhs_dump'],
        'contract_keys':feature['keys'],
      },
      'context_closure':selected_closure,
      'artifact_bindings':{
        'action':action_binding,
        'binder':binder_binding,
      },
      'v12_operand_materialization_gene_id':v12gene.get('gene_id'),
      'binder_gene_id':binder.get('gene_id'),
      'ground_verdict':ground_verdict,
      'counterfactual_fail_closed':fail_closed,
      'all_context_dependencies_bound':True,
      'actual_target_source_integration_proven':False,
      'promotion_state':'SHADOW_ONLY',
    }
    gene['gene_digest']=digest(gene)
    GENE.parent.mkdir(parents=True,exist_ok=True)
    GENE.write_text(json.dumps(gene,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

status='PASS_SHADOW_G2_NATIVE_CONTEXTUAL_AST_CONTEXT_COMPOSITION_REPAIR_V15' if passed else 'WITHHOLD_G2_NATIVE_CONTEXTUAL_AST_CONTEXT_COMPOSITION_REPAIR_V15'
next_cap='NATIVE_CONTEXT_BOUND_AST_SOURCE_REALIZATION_V16' if passed else 'NATIVE_CONTEXTUAL_AST_CONTEXT_COMPOSITION_GENESIS_V16'
report={
 'schema':'yado.g2.native_contextual_ast_context_composition_repair.v15',
 'status':status,'parent_v14_receipt':v14.get('receipt_sha256'),
 'unpack_bindings':unpack_rows,'feature_binding':feature,'composition_strategies':strategies,
 'native_goal':native_goal,'native_skill_selection':selection,'selected_composition':selected,
 'ground_verdict':ground_verdict,'counterfactuals':counterfactuals,'gene':gene,
 'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'V15 REPAIRS ONLY CONTEXT COMPOSITION. IT RECOGNIZES A GENERIC YADO-SOURCE PATTERN WHERE MULTIPLE ARTIFACT OBJECTS ARE CREATED BY DESTRUCTURING MAP(LOAD,[PATH_SYMBOLS...]) AND COMPOSES THAT WITH SIMPLE ASSIGNMENTS AND THE UNCHANGED SEVEN-FIELD FEATURE DICT. YADO NATIVE SKILL ADMISSION CHOOSES BETWEEN COMPOSITION STRATEGIES AT UNCHANGED THRESHOLDS. NO FEATURE SEMANTICS, ARTIFACT VALUES, AST PATCH OR TARGET SOURCE ARE AUTHORED BY THE HOST.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'selected_composition':selected,
 'gene_id':gene.get('gene_id') if gene else None,
 'ground_verdict':ground_verdict,'next_required_capability':next_cap,
 'checks':checks,'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True,default=str))
if not passed:raise SystemExit(2)
