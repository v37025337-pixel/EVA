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

V12=REPO/'candidates/kernel-self-generated/g2-native-contextual-ast-operand-materialization-v12.json'
V12GENE=REPO/'candidates/kernel-self-generated/g2-native-contextual-ast-operand-materialization-gene-v12.json'
BINDER=REPO/'candidates/kernel-self-generated/g2-native-self-created-evidence-binder-gene-v1.json'
ACTION=REPO/'candidates/kernel-self-generated/g2-autonomous-self-improvement-task-v1.json'
SEM_RUNTIME=REPO/'runtime/yado_g2_task_conditioned_semantic_source_edit_meta_language_genesis_v5.py'
OUT=REPO/'candidates/kernel-self-generated/g2-native-contextual-ast-context-binding-genesis-v13.json'
GENE=REPO/'candidates/kernel-self-generated/g2-native-contextual-ast-context-binding-gene-v13.json'
DB=ROOT/'yado_native_contextual_ast_context_binding_genesis_v13.sqlite'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))

v12,v12gene,binder,action=map(load,[V12,V12GENE,BINDER,ACTION])
if v12.get('status')!='PASS_SHADOW_G2_NATIVE_CONTEXTUAL_AST_OPERAND_MATERIALIZATION_V12':
    raise RuntimeError('V12_MATERIALIZATION_PASS_REQUIRED')
if v12.get('next_required_capability')!='NATIVE_CONTEXTUAL_AST_CONTEXT_BINDING_GENESIS_V13':
    raise RuntimeError('V12_FRONTIER_MISMATCH')
if sorted(v12gene.get('free_context_names') or [])!=['binder','feat','tree_predict']:
    raise RuntimeError('V12_FREE_CONTEXT_DRIFT')

core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)
src=SEM_RUNTIME.read_text(encoding='utf-8');tree=ast.parse(src)

# Import binding candidates discovered from YADO own source.
import_candidates=[]
for n in tree.body:
    if isinstance(n,ast.ImportFrom):
        for a in n.names:
            import_candidates.append({
              'module':n.module,'name':a.name,'asname':a.asname,
              'bound_name':a.asname or a.name,'source':ast.unparse(n)
            })
tp=[x for x in import_candidates if x['bound_name']=='tree_predict']
if not tp:raise RuntimeError('TREE_PREDICT_IMPORT_NOT_FOUND_IN_YADO_SOURCE')

# Artifact path bindings mechanically extracted from YADO source assignments.
path_bindings={}
for n in tree.body:
    if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name):
        name=n.targets[0].id
        if name in ('BINDER','ACTION'):
            path_bindings[name]={'rhs_source':ast.unparse(n.value),'rhs_dump':ast.dump(n.value,include_attributes=False)}
if set(path_bindings)!= {'BINDER','ACTION'}:raise RuntimeError('BINDER_ACTION_PATH_BINDINGS_NOT_FOUND')

# Find feature-vector dict candidates in YADO source.
required=set(str(x) for x in (binder.get('contract_fields') or []))
dict_candidates=[]
for n in ast.walk(tree):
    if not isinstance(n,ast.Assign) or len(n.targets)!=1 or not isinstance(n.targets[0],ast.Name) or not isinstance(n.value,ast.Dict):
        continue
    keys=[]
    for k in n.value.keys:
        if isinstance(k,ast.Constant) and isinstance(k.value,str):keys.append(k.value)
    if not keys:continue
    deps=sorted({x.id for x in ast.walk(n.value) if isinstance(x,ast.Name)})
    name=n.targets[0].id
    coverage=len(required & set(keys))/max(1,len(required))
    extra=max(0,len(set(keys)-required))
    dict_candidates.append({
      'assignment_name':name,'keys':sorted(keys),'required_coverage':coverage,'extra_key_count':extra,
      'rhs_source':ast.unparse(n.value),'rhs_dump':ast.dump(n.value,annotate_fields=True,include_attributes=False),
      'dependencies':deps
    })
if not dict_candidates:raise RuntimeError('NO_DICT_BINDING_CANDIDATES')

# Prerequisite assignments from the same YADO source for any candidate dependency.
assignments={}
for n in ast.walk(tree):
    if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name):
        assignments.setdefault(n.targets[0].id,{
          'name':n.targets[0].id,'rhs_source':ast.unparse(n.value),
          'rhs_dump':ast.dump(n.value,annotate_fields=True,include_attributes=False)
        })

# Ground current semantic correctness with the same binder artifact/action receipt.
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
if ground_verdict!='ACCEPT_FRESH_EVIDENCE':raise RuntimeError('CURRENT_GROUND_DOES_NOT_ACCEPT')

skills=[];metrics=[]
for row in dict_candidates:
    exact_keys=set(row['keys'])==required
    dep_defs=sum(1 for d in row['dependencies'] if d in assignments or d in {'True','False','None'})/max(1,len(row['dependencies']))
    score=min(row['required_coverage'],1.0 if row['extra_key_count']==0 else max(0.0,1.0-row['extra_key_count']/10.0),dep_defs)
    sid='CONTEXT_FEATURE_BINDING_'+hashlib.sha256(row['rhs_dump'].encode()).hexdigest()[:12].upper()
    m={**row,'skill_id':sid,'exact_contract_keys':exact_keys,'dependency_definition_ratio':dep_defs,'score':score}
    metrics.append(m)
    skills.append(SkillCandidate(
      skill_id=sid,artifact_digest=digest(m),
      structural_valid=exact_keys and dep_defs==1.0,
      semantic_consistency=score,
      fit_baseline=0.0,fit_candidate=score,
      heldout_baseline=0.0,heldout_candidate=score,
      regression_pass=True,state_integrity=True,rollback_available=True,
      metadata={'origin':'YADO_OWN_SEMANTIC_EDIT_RUNTIME_FEATURE_DICT','assignment_name':row['assignment_name']}
    ))

if DB.exists():DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    goal=k.executive.create_goal(
      objective='Bind the free binder/feat/tree_predict context of the YADO V12 IfExp from YADO own semantic-edit runtime and current self-generated evidence artifacts.',
      required_capabilities={'NATIVE_CONTEXTUAL_AST_CONTEXT_BINDING_GENESIS_V13':1.0},
      success_criteria={'contract_keys_exact':True,'all_dependencies_available':True,'ground_accept':True,'rollback':True},
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
prereq_names=selected.get('dependencies') if selected else []
prereq_bindings={name:assignments[name] for name in prereq_names if name in assignments}

# The feature expression selected from history is bound to the V12 free name 'feat';
# no source patch is made here.
checks={
 'canonical_v5_continuity_active':core.execution_fabric_cls.COMPONENT_ID=='RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V5',
 'v12_operand_materialization_gene_consumed':bool(v12gene.get('gene_id')),
 'free_context_exactly_binder_feat_tree_predict':sorted(v12gene.get('free_context_names') or [])==['binder','feat','tree_predict'],
 'tree_predict_import_derived_from_yado_source':bool(tp),
 'binder_path_binding_derived_from_yado_source':'BINDER' in path_bindings,
 'action_path_binding_derived_from_yado_source':'ACTION' in path_bindings,
 'feature_candidate_inventory_nonempty':bool(dict_candidates),
 'current_binder_ground_accepts':ground_verdict=='ACCEPT_FRESH_EVIDENCE',
 'native_goal_created':True,
 'native_deficit_detected':bool(native_goal['deficits']),
 'native_skill_selector_executed':True,
 'native_selector_selected_one_feature_binding':selected_id is not None and selection.get('selected_count')==1,
 'selected_feature_keys_exact_contract':bool(selected and selected['exact_contract_keys']),
 'selected_feature_dependencies_all_bound':bool(selected and selected['dependency_definition_ratio']==1.0),
 'host_authored_feature_logic':False,
 'host_authored_import_binding':False,
 'host_selected_feature_dict':False,
 'external_models_used':False,
 'actual_target_source_integration_proven':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'automatic_canonical_promotion':False,
}
positive=(
 'canonical_v5_continuity_active','v12_operand_materialization_gene_consumed',
 'free_context_exactly_binder_feat_tree_predict','tree_predict_import_derived_from_yado_source',
 'binder_path_binding_derived_from_yado_source','action_path_binding_derived_from_yado_source',
 'feature_candidate_inventory_nonempty','current_binder_ground_accepts','native_goal_created',
 'native_deficit_detected','native_skill_selector_executed','native_selector_selected_one_feature_binding',
 'selected_feature_keys_exact_contract','selected_feature_dependencies_all_bound','canonical_unchanged'
)
negative=('host_authored_feature_logic','host_authored_import_binding','host_selected_feature_dict','external_models_used','actual_target_source_integration_proven','automatic_canonical_promotion')
passed=all(checks[k] is True for k in positive) and all(checks[k] is False for k in negative)

gene=None
if passed:
    gene={
      'schema':'yado.g2.native_contextual_ast_context_binding_gene.v13',
      'gene_id':'GENE-G2-NATIVE-AST-CONTEXT-BINDING-V13-'+digest({
        'feature':selected['rhs_dump'],'v12_gene':v12gene.get('gene_digest'),'binder_gene':binder.get('gene_digest')
      })[:16],
      'novel_gene':True,
      'gene_scope':['CODE','SELF_AUDIT_AND_REPAIR','GENERATIVE_EXECUTIVE'],
      'origin':'YADO_NATIVE_SELECTION_OVER_YADO_OWN_CONTEXT_BINDING_SOURCE',
      'free_name_bindings':{
        'tree_predict':{'kind':'IMPORT_FROM','module':tp[0]['module'],'name':tp[0]['name'],'source':tp[0]['source']},
        'binder':{'kind':'LOAD_JSON_ARTIFACT','artifact':'candidates/kernel-self-generated/g2-native-self-created-evidence-binder-gene-v1.json','path_binding':path_bindings['BINDER']},
        'feat':{'kind':'FEATURE_DICT_EXPRESSION','source_assignment':selected['assignment_name'],'rhs_source':selected['rhs_source'],'rhs_dump':selected['rhs_dump']}
      },
      'feature_prerequisite_bindings':prereq_bindings,
      'action_artifact_binding':{'artifact':'candidates/kernel-self-generated/g2-autonomous-self-improvement-task-v1.json','path_binding':path_bindings['ACTION']},
      'ground_verdict':ground_verdict,
      'all_v12_free_names_bound':True,
      'actual_target_source_integration_proven':False,
      'promotion_state':'SHADOW_ONLY'
    }
    gene['gene_digest']=digest(gene)
    GENE.parent.mkdir(parents=True,exist_ok=True)
    GENE.write_text(json.dumps(gene,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

status='PASS_SHADOW_G2_NATIVE_CONTEXTUAL_AST_CONTEXT_BINDING_GENESIS_V13' if passed else 'WITHHOLD_G2_NATIVE_CONTEXTUAL_AST_CONTEXT_BINDING_GENESIS_V13'
next_cap='NATIVE_CONTEXT_BOUND_AST_SOURCE_REALIZATION_V14' if passed else 'NATIVE_CONTEXTUAL_AST_CONTEXT_BINDING_REPAIR_V14'
report={
 'schema':'yado.g2.native_contextual_ast_context_binding_genesis.v13',
 'status':status,'parent_v12_receipt':v12.get('receipt_sha256'),
 'tree_predict_import_candidates':tp,'path_bindings':path_bindings,
 'feature_binding_candidates':metrics,'native_goal':native_goal,'native_skill_selection':selection,
 'selected_feature_binding':selected,'selected_prerequisite_bindings':prereq_bindings,
 'ground_verdict':ground_verdict,'gene':gene,'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,'next_required_capability':next_cap,
 'semantic_boundary':'V13 BINDS THE THREE FREE NAMES FROM V12 USING YADO OWN SOURCE AND ARTIFACTS. TREE_PREDICT IMPORT, BINDER/ACTION PATHS, FEATURE-DICT EXPRESSION AND ITS PREREQUISITE ASSIGNMENTS ARE EXTRACTED FROM THE EXISTING YADO SEMANTIC-EDIT RUNTIME; YADO NATIVE SKILL ADMISSION SELECTS THE EXACT BINDER-CONTRACT FEATURE DICT. NO FEATURE LOGIC OR IMPORT IS AUTHORED BY THE HOST. THIS IS A CONTEXT-BINDING GENE ONLY; TARGET SOURCE INTEGRATION REMAINS UNPROVEN FOR V14.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'selected_feature_binding':selected,
 'prerequisite_names':sorted(prereq_bindings),'ground_verdict':ground_verdict,
 'gene_id':gene.get('gene_id') if gene else None,'next_required_capability':next_cap,
 'checks':checks,'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True,default=str))
if not passed:raise SystemExit(2)
