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

TASK=REPO/'architecture/yado-kernel-native-source-realization-self-representation-driven-extended-controller-v1-request.json'
EXT=REPO/'candidates/kernel-self-generated/g2-self-representation-driven-extended-controller-candidate-v1.json'
SELFREP=REPO/'candidates/kernel-self-generated/g2-native-executable-evolution-controller-self-representation-v1.json'
CTRL=REPO/'runtime/yado_evolutionary_genome_v1.py'
OUT=REPO/'candidates/kernel-self-generated/g2-native-source-realization-self-representation-driven-extended-controller-v1.json'
CAND=REPO/'candidates/g2-self-evolution/yado_evolutionary_genome_self_realized_candidate_v1.py'
DB=ROOT/'yado_native_source_realization_extended_controller_v1.sqlite'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def sha_text(s): return hashlib.sha256(s.encode()).hexdigest()

task=load(TASK); ext=load(EXT); selfrep=load(SELFREP)
if ext.get('status')!='PASS_SHADOW_G2_SELF_REPRESENTATION_DRIVEN_EXTENDED_CONTROLLER_CANDIDATE_V1':
    raise RuntimeError('EXTENDED_CONTROLLER_PARENT_NOT_PASS')
if selfrep.get('status')!='PASS_SHADOW_G2_NATIVE_EXECUTABLE_EVOLUTION_CONTROLLER_SELF_REPRESENTATION_V1':
    raise RuntimeError('SELF_REPRESENTATION_PARENT_NOT_PASS')

core=UnifiedYADOCoreV1(REPO)
head_before=copy.deepcopy(core.head)
parent_source=CTRL.read_text(encoding='utf-8')
parent_source_sha=sha_text(parent_source)
candidate_controller=ext.get('candidate_controller') or {}
parent_dims=sorted(candidate_controller.get('parent_dimensions') or [])
target_dim=str(candidate_controller.get('yado_selected_new_dimension') or ext.get('selected_target') or '')
expected_dims=sorted(candidate_controller.get('candidate_dimensions') or [])
if not target_dim or target_dim in parent_dims or len(expected_dims)<=len(parent_dims):
    raise RuntimeError('PARENT_EXTENSION_ARTIFACT_INVALID')

if DB.exists(): DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    goal=k.executive.create_goal(
      objective=str(task['task']),
      required_capabilities={'NATIVE_SOURCE_REALIZATION_OF_SELF_REPRESENTATION_DRIVEN_EXTENDED_CONTROLLER_V1':1.0},
      success_criteria={'source_bytes':True,'compile':True,'broader_controller':True,'rollback':True},
    )
    deficits=k.executive.detect_deficits(goal.goal_id)
    native_goal={'goal_id':goal.goal_id,'deficits':[asdict(d) for d in deficits]}
finally:
    try:k.close()
    except Exception:pass

parent_state=core.evolutionary_parent_genome()
experience=copy.deepcopy(parent_state.get('experience') or [])
experience += [
  {
    'role':'YADO_EXECUTABLE_CONTROLLER_SELF_REPRESENTATION_PASS',
    'artifact':str(SELFREP.relative_to(REPO)),
    'receipt_sha256':selfrep.get('receipt_sha256'),
    'representation_digest':(selfrep.get('representation') or {}).get('representation_digest'),
    'program_id':(selfrep.get('representation') or {}).get('program_id'),
  },
  {
    'role':'YADO_SELF_REPRESENTATION_DRIVEN_EXTENDED_CONTROLLER_PASS',
    'artifact':str(EXT.relative_to(REPO)),
    'receipt_sha256':ext.get('receipt_sha256'),
    'candidate_digest':(ext.get('candidate_controller') or {}).get('candidate_digest'),
    'candidate_id':(ext.get('candidate_controller') or {}).get('candidate_id'),
    'candidate_dimensions':expected_dims,
    'selected_target':target_dim,
  },
  {
    'role':'YADO_OWN_CONTROLLER_SOURCE',
    'path':str(CTRL.relative_to(REPO)),
    'source_sha256':parent_source_sha,
  },
  {
    'role':'YADO_CURRENT_NATIVE_SOURCE_REALIZATION_TASK',
    'objective':task.get('objective'),
    'constraints':task.get('constraints'),
  },
]

controller=core.evolutionary_genome_cls(parent_state['parent'],experience_sources=experience)

# Invoke only YADO-native zero-argument paths. No source seed, patch, AST skeleton,
# target function or emitter schema is supplied by the host.
native_calls={}
for owner_name,obj in [('core',core),('controller',controller)]:
    for name in sorted(dir(obj)):
        if name.startswith('_') or not any(t in name.lower() for t in ('source','emit','synth','code','evol','genesis','construct')):
            continue
        fn=getattr(obj,name,None)
        if not callable(fn): continue
        try:sig=inspect.signature(fn)
        except Exception:continue
        required=[p for p in sig.parameters.values()
                  if p.default is inspect._empty and p.kind in (p.POSITIONAL_ONLY,p.POSITIONAL_OR_KEYWORD)]
        if required: continue
        key=owner_name+'.'+name
        try:native_calls[key]=fn()
        except Exception as e:native_calls[key]={'error':type(e).__name__+':'+str(e)[:600]}

if 'controller.evolve_once' not in native_calls:
    native_calls['controller.evolve_once']=controller.evolve_once()

# Search YADO outputs for actual Python source. Strings copied unchanged from the
# parent controller or request/artifact metadata do not count.
source_candidates=[]
def walk(x,path='root'):
    if isinstance(x,dict):
        for k,v in x.items(): walk(v,path+'.'+str(k))
    elif isinstance(x,list):
        for i,v in enumerate(x): walk(v,path+f'[{i}]')
    elif isinstance(x,str) and len(x)>=80:
        try:t=ast.parse(x)
        except Exception:return
        if not any(isinstance(n,(ast.ClassDef,ast.FunctionDef)) for n in ast.walk(t)):return
        h=sha_text(x)
        source_candidates.append({'path':path,'sha256':h,'source':x,'unchanged_parent':h==parent_source_sha})
walk(native_calls)

# Prefer changed controller-like candidates; source provenance must come only from native outputs.
changed=[c for c in source_candidates if not c['unchanged_parent']]
def candidate_rank(c):
    s=c['source']
    return (
      int('YADOEvolutionaryGenomeV1' in s),
      int(target_dim in s),
      len(s),
      c['sha256'],
    )
changed.sort(key=candidate_rank,reverse=True)
winner=changed[0] if changed else None
candidate_source=winner['source'] if winner else None

compile_pass=False
static_safe=False
broader=False
regression=False
candidate_dims=[]
source_error=None

def import_roots(t):
    out=set()
    for n in ast.walk(t):
        if isinstance(n,ast.Import):
            out.update(a.name.split('.')[0] for a in n.names)
        elif isinstance(n,ast.ImportFrom) and n.module:
            out.add(n.module.split('.')[0])
    return out

if candidate_source:
    try:
        pt=ast.parse(parent_source); ct=ast.parse(candidate_source)
        compile(candidate_source,'<yado-native-extended-controller>','exec')
        compile_pass=True
        parent_imports=import_roots(pt); cand_imports=import_roots(ct)
        banned_names={'eval','exec','compile','open','__import__'}
        banned_attrs={('os','system'),('subprocess','run'),('subprocess','Popen'),('socket','socket')}
        bad_call=False
        for n in ast.walk(ct):
            if not isinstance(n,ast.Call): continue
            if isinstance(n.func,ast.Name) and n.func.id in banned_names: bad_call=True
            if isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name):
                if (n.func.value.id,n.func.attr) in banned_attrs: bad_call=True
        static_safe=(cand_imports<=parent_imports and not bad_call)
        if static_safe:
            ns={'__name__':'_yado_native_extended_controller_candidate_'}
            exec(compile(candidate_source,'<yado-native-extended-controller>','exec'),ns,ns)
            C=ns.get('YADOEvolutionaryGenomeV1')
            if C is not None and hasattr(C,'component'):
                comp=C.component()
                candidate_dims=sorted(comp.get('chromosomes') or [])
                broader=(len(candidate_dims)>len(parent_dims) and target_dim in candidate_dims and set(parent_dims)<=set(candidate_dims))
                regression=set(parent_dims)<=set(candidate_dims)
    except Exception as e:
        source_error=type(e).__name__+':'+str(e)[:800]

if candidate_source and compile_pass:
    CAND.parent.mkdir(parents=True,exist_ok=True)
    CAND.write_text(candidate_source,encoding='utf-8')

evo=native_calls.get('controller.evolve_once') or {}
child_exp=((evo.get('child') or {}).get('experience_sources') or []) if isinstance(evo,dict) else []
artifacts_visible=(
    str(ext.get('receipt_sha256')) in canon(child_exp)
    and str(selfrep.get('receipt_sha256')) in canon(child_exp)
)

checks={
 'both_prior_pass_artifacts_consumed':artifacts_visible,
 'native_goal_created':True,
 'native_deficit_detected':bool(native_goal['deficits']),
 'native_zero_argument_source_realization_attempt_executed':True,
 'actual_new_source_bytes_produced_by_yado':bool(candidate_source),
 'candidate_not_parent_copy':bool(candidate_source) and sha_text(candidate_source)!=parent_source_sha,
 'candidate_source_compiles':compile_pass,
 'candidate_static_safety_gate':static_safe,
 'structurally_broader_controller':broader,
 'parent_dimensions_regression_preserved':regression,
 'rollback_parent_available':bool((evo.get('parent') or {}).get('genome_digest')) if isinstance(evo,dict) else False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'external_coding_models_used':False,
 'new_external_research_used':False,
 'host_patch_used':False,
 'host_source_template_used':False,
 'host_ast_skeleton_used':False,
 'host_emitter_schema_used':False,
 'host_target_function_selected':False,
 'host_new_dimension_name_invented':False,
 'host_transported_yado_selected_dimension':True,
 'dimension_origin_yado_failure_history':bool((ext.get('checks') or {}).get('extension_targets_from_yado_failure_history_only')),
 'dimension_selected_by_yado':bool((ext.get('checks') or {}).get('new_dimension_selected_by_yado_not_host')),
 'host_gene_schema_used':False,
}
positive_keys=[
 'both_prior_pass_artifacts_consumed','native_goal_created','native_deficit_detected',
 'native_zero_argument_source_realization_attempt_executed','actual_new_source_bytes_produced_by_yado',
 'candidate_not_parent_copy','candidate_source_compiles','candidate_static_safety_gate',
 'structurally_broader_controller','parent_dimensions_regression_preserved',
 'rollback_parent_available','canonical_unchanged'
]
negative_keys=[
 'external_coding_models_used','new_external_research_used','host_patch_used','host_source_template_used',
 'host_ast_skeleton_used','host_emitter_schema_used','host_target_function_selected',
 'host_new_dimension_name_invented','host_gene_schema_used'
]
passed=all(checks[k] for k in positive_keys) and all(checks[k] is False for k in negative_keys)
status='PASS_SHADOW_G2_NATIVE_SOURCE_REALIZATION_SELF_REPRESENTATION_DRIVEN_EXTENDED_CONTROLLER_V1' if passed else 'WITHHOLD_G2_NATIVE_SOURCE_REALIZATION_SELF_REPRESENTATION_DRIVEN_EXTENDED_CONTROLLER_V1'

report={
 'schema':'yado.g2.native_source_realization_self_representation_driven_extended_controller.v1',
 'status':status,'task':task,'native_goal':native_goal,
 'parent_source_sha256':parent_source_sha,
 'parent_dimensions':parent_dims,'target_dimension_from_yado_candidate':target_dim,
 'expected_extended_dimensions':expected_dims,
 'native_calls':native_calls,
 'native_source_candidate_count':len(source_candidates),
 'changed_native_source_candidate_count':len(changed),
 'selected_native_source_path':winner.get('path') if winner else None,
 'candidate_source_sha256':sha_text(candidate_source) if candidate_source else None,
 'candidate_artifact_path':str(CAND.relative_to(REPO)) if CAND.exists() else None,
 'candidate_dimensions':candidate_dims,
 'source_error':source_error,
 'checks':checks,
 'canonical_mutation':False,
 'next_required_capability':None if passed else 'NATIVE_SOURCE_REALIZATION_OF_SELF_REPRESENTATION_DRIVEN_EXTENDED_CONTROLLER_V2',
 'provenance':{'dimension_origin':'YADO_NATIVE_FAILURE_HISTORY','dimension_selector':'YADO_NATIVE_SKILL_SELECTION','host_role':'TRANSPORT_ALREADY_SELECTED_YADO_ARTIFACT_ONLY','host_dimension_invention':False},
 'semantic_boundary':'STRICT NATIVE SOURCE-REALIZATION TEST. THE HOST TRANSPORTS YADO OWN PASS ARTIFACTS, INCLUDING THE DIMENSION ALREADY SELECTED BY YADO, AND EVALUATES PROVENANCE/COMPILE/STRUCTURAL REGRESSION ONLY. IT DOES NOT INVENT THE DIMENSION, PROVIDE SOURCE, PATCHES, AST SKELETONS, EMITTER SCHEMAS OR TARGET FUNCTIONS. PASS REQUIRES SOURCE BYTES TO APPEAR IN YADO NATIVE OUTPUTS.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,
 'native_source_candidate_count':len(source_candidates),
 'changed_native_source_candidate_count':len(changed),
 'candidate_source_sha256':report['candidate_source_sha256'],
 'candidate_source_compiles':compile_pass,
 'candidate_dimensions':candidate_dims,
 'structurally_broader_controller':broader,
 'next_required_capability':report['next_required_capability'],
 'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True))
if not passed: raise SystemExit(2)
