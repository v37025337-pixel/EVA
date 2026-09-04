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
from yado_core_v2_1 import RuleProgram,RuleSpec,RulePredicate,BoundedRuleSandbox

TASK=REPO/'architecture/yado-g2-native-source-realization-self-representation-driven-extended-controller-v2-request.json'
SELFREP=REPO/'candidates/kernel-self-generated/g2-native-executable-evolution-controller-self-representation-v1.json'
EXT=REPO/'candidates/kernel-self-generated/g2-self-representation-driven-extended-controller-candidate-v1.json'
EMITTER=REPO/'candidates/kernel-self-generated/g2-experience-conditioned-native-emitter-gene-genesis-v3.json'
CTRL=REPO/'runtime/yado_evolutionary_genome_v1.py'
OUT=REPO/'candidates/kernel-self-generated/g2-native-source-realization-self-representation-driven-extended-controller-v2.json'
CAND=REPO/'candidates/g2-self-evolution/yado_evolutionary_genome_self_realized_candidate_v2.py'
DB=ROOT/'yado_native_source_realization_extended_controller_v2.sqlite'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha_text(s):return hashlib.sha256(s.encode()).hexdigest()

task=load(TASK);selfrep=load(SELFREP);ext=load(EXT);emitter=load(EMITTER)
if selfrep.get('status')!='PASS_SHADOW_G2_NATIVE_EXECUTABLE_EVOLUTION_CONTROLLER_SELF_REPRESENTATION_V1':
    raise RuntimeError('SELFREP_NOT_PASS')
if ext.get('status')!='PASS_SHADOW_G2_SELF_REPRESENTATION_DRIVEN_EXTENDED_CONTROLLER_CANDIDATE_V1':
    raise RuntimeError('EXT_NOT_PASS')
if emitter.get('status')!='PASS_SHADOW_G2_EXPERIENCE_CONDITIONED_NATIVE_EMITTER_GENE_GENESIS_V3':
    raise RuntimeError('EMITTER_GENE_NOT_PASS')

core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)
parent_source=CTRL.read_text(encoding='utf-8');parent_sha=sha_text(parent_source)
candidate_controller=ext.get('candidate_controller') or {}
parent_dims=sorted(candidate_controller.get('parent_dimensions') or [])
target_dim=str(candidate_controller.get('yado_selected_new_dimension') or ext.get('selected_target') or '')
expected_dims=sorted(candidate_controller.get('candidate_dimensions') or [])
if not target_dim or target_dim in parent_dims or not set(parent_dims)<set(expected_dims):
    raise RuntimeError('EXTENDED_CONTROLLER_INVALID')

# Reconstruct and execute the YADO-born emitter gene exactly as stored.
eg=emitter.get('emitter_gene') or {}
pd=eg.get('program') or {}
rules=[]
for rr in pd.get('rules') or []:
    rules.append(RuleSpec(
      predicates=[RulePredicate(**p) for p in rr.get('predicates') or []],
      output=rr.get('output'),support=int(rr.get('support') or 0),confidence=float(rr.get('confidence') or 0)
    ))
program=RuleProgram(
  program_id=pd['program_id'],target_capability=pd['target_capability'],target_organ=pd['target_organ'],
  rules=rules,default_output=pd.get('default_output'),source_digest=pd['source_digest'],
  training_count=int(pd.get('training_count') or 0),status=pd.get('status','SHADOW'),created_at=pd.get('created_at')
)
seq=list(emitter.get('yado_learned_sequence') or [])
fresh_transition_checks=[]
for variant in (700,701,702):
    ok=True;rows=[]
    for a,b in zip(seq,seq[1:]):
        got=BoundedRuleSandbox.execute(program,{'current_primitive':a,'history_variant':variant,'source_process_bound':True})
        rows.append({'current':a,'expected_next':b,'got':got,'ok':got==b})
        ok &= got==b
    fresh_transition_checks.append({'variant':variant,'pass':ok,'rows':rows})
emitter_process_exec_pass=bool(fresh_transition_checks) and all(x['pass'] for x in fresh_transition_checks)

if DB.exists():DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    goal=k.executive.create_goal(
      objective=str(task['objective']),
      required_capabilities={'NATIVE_SOURCE_REALIZATION_OF_SELF_REPRESENTATION_DRIVEN_EXTENDED_CONTROLLER_V2':1.0},
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
 {'role':'YADO_SELF_REPRESENTATION_PASS','artifact':str(SELFREP.relative_to(REPO)),'receipt_sha256':selfrep.get('receipt_sha256')},
 {'role':'YADO_EXTENDED_CONTROLLER_PASS','artifact':str(EXT.relative_to(REPO)),'receipt_sha256':ext.get('receipt_sha256'),'selected_target':target_dim,'candidate_dimensions':expected_dims},
 {'role':'YADO_EMITTER_GENE_PASS','artifact':str(EMITTER.relative_to(REPO)),'receipt_sha256':emitter.get('receipt_sha256'),'gene_id':eg.get('gene_id'),'gene_digest':eg.get('gene_digest'),'learned_process_digest':eg.get('learned_process_digest')},
 {'role':'YADO_EMITTER_PROCESS_EXECUTION','fresh_transition_checks':fresh_transition_checks},
 {'role':'YADO_OWN_CONTROLLER_SOURCE','path':str(CTRL.relative_to(REPO)),'source_sha256':parent_sha},
]
controller=core.evolutionary_genome_cls(parent_state['parent'],experience_sources=experience)

native_calls={}
for owner_name,obj in [('core',core),('controller',controller)]:
    for name in sorted(dir(obj)):
        if name.startswith('_') or not any(t in name.lower() for t in ('source','emit','synth','code','evol','genesis','construct')):
            continue
        fn=getattr(obj,name,None)
        if not callable(fn):continue
        try:sig=inspect.signature(fn)
        except Exception:continue
        required=[p for p in sig.parameters.values() if p.default is inspect._empty and p.kind in (p.POSITIONAL_ONLY,p.POSITIONAL_OR_KEYWORD)]
        if required:continue
        key=owner_name+'.'+name
        try:native_calls[key]=fn()
        except Exception as e:native_calls[key]={'error':type(e).__name__+':'+str(e)[:600]}
if 'controller.evolve_once' not in native_calls:
    native_calls['controller.evolve_once']=controller.evolve_once()

source_candidates=[]
def walk(x,path='root'):
    if isinstance(x,dict):
        for k,v in x.items():walk(v,path+'.'+str(k))
    elif isinstance(x,list):
        for i,v in enumerate(x):walk(v,path+f'[{i}]')
    elif isinstance(x,str) and len(x)>=80:
        try:t=ast.parse(x)
        except Exception:return
        if not any(isinstance(n,(ast.FunctionDef,ast.ClassDef)) for n in ast.walk(t)):return
        h=sha_text(x)
        source_candidates.append({'path':path,'sha256':h,'source':x,'unchanged_parent':h==parent_sha})
walk(native_calls)
changed=[c for c in source_candidates if not c['unchanged_parent']]
changed.sort(key=lambda c:(int('YADOEvolutionaryGenomeV1' in c['source']),int(target_dim in c['source']),len(c['source']),c['sha256']),reverse=True)
winner=changed[0] if changed else None
candidate_source=winner['source'] if winner else None

compile_pass=False;static_safe=False;broader=False;regression=False;candidate_dims=[];source_error=None
def import_roots(t):
    out=set()
    for n in ast.walk(t):
        if isinstance(n,ast.Import):out.update(a.name.split('.')[0] for a in n.names)
        elif isinstance(n,ast.ImportFrom) and n.module:out.add(n.module.split('.')[0])
    return out
if candidate_source:
    try:
        pt=ast.parse(parent_source);ct=ast.parse(candidate_source)
        compile(candidate_source,'<yado-native-source-v2>','exec');compile_pass=True
        pimports=import_roots(pt);cimports=import_roots(ct)
        banned={'eval','exec','compile','open','__import__'};bad=False
        for n in ast.walk(ct):
            if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in banned:bad=True
        static_safe=(cimports<=pimports and not bad)
        if static_safe:
            ns={'__name__':'_yado_native_source_v2_'}
            exec(compile(candidate_source,'<yado-native-source-v2>','exec'),ns,ns)
            C=ns.get('YADOEvolutionaryGenomeV1')
            if C is not None and hasattr(C,'component'):
                comp=C.component();candidate_dims=sorted(comp.get('chromosomes') or [])
                regression=set(parent_dims)<=set(candidate_dims)
                broader=regression and target_dim in candidate_dims and len(candidate_dims)>len(parent_dims)
    except Exception as e:
        source_error=type(e).__name__+':'+str(e)[:800]
if candidate_source and compile_pass:
    CAND.parent.mkdir(parents=True,exist_ok=True);CAND.write_text(candidate_source,encoding='utf-8')

evo=native_calls.get('controller.evolve_once') or {}
child_exp=((evo.get('child') or {}).get('experience_sources') or []) if isinstance(evo,dict) else []
all_parents_visible=all(str(x) in canon(child_exp) for x in (selfrep.get('receipt_sha256'),ext.get('receipt_sha256'),emitter.get('receipt_sha256')))

checks={
 'all_three_yado_parent_artifacts_consumed':all_parents_visible,
 'emitter_gene_process_execution_fresh_pass':emitter_process_exec_pass,
 'native_goal_created':True,
 'native_deficit_detected':bool(native_goal['deficits']),
 'native_source_realization_attempt_executed':True,
 'actual_new_source_bytes_produced_by_yado':bool(candidate_source),
 'candidate_not_parent_copy':bool(candidate_source) and sha_text(candidate_source)!=parent_sha,
 'candidate_source_compiles':compile_pass,
 'candidate_static_safety_gate':static_safe,
 'structurally_broader_controller':broader,
 'parent_dimensions_regression_preserved':regression,
 'rollback_parent_available':bool((evo.get('parent') or {}).get('genome_digest')) if isinstance(evo,dict) else False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'external_coding_models_used':False,'new_external_research_used':False,'host_source_template_used':False,
 'host_ast_skeleton_used':False,'host_patch_used':False,'host_emitter_schema_used':False,
 'host_target_function_selected':False,'host_new_dimension_name_invented':False,'automatic_canonical_promotion':False,
}
positive=('all_three_yado_parent_artifacts_consumed','emitter_gene_process_execution_fresh_pass','native_goal_created','native_deficit_detected',
          'native_source_realization_attempt_executed','actual_new_source_bytes_produced_by_yado','candidate_not_parent_copy',
          'candidate_source_compiles','candidate_static_safety_gate','structurally_broader_controller',
          'parent_dimensions_regression_preserved','rollback_parent_available','canonical_unchanged')
negative=('external_coding_models_used','new_external_research_used','host_source_template_used','host_ast_skeleton_used',
          'host_patch_used','host_emitter_schema_used','host_target_function_selected','host_new_dimension_name_invented','automatic_canonical_promotion')
passed=all(checks[k] for k in positive) and all(checks[k] is False for k in negative)
if passed:
    next_cap=None
elif emitter_process_exec_pass and not candidate_source:
    next_cap='NATIVE_SOURCE_PRIMITIVE_EXECUTION_AND_SERIALIZATION_V1'
else:
    next_cap='NATIVE_SOURCE_REALIZATION_V2_REPAIR'
status='PASS_SHADOW_G2_NATIVE_SOURCE_REALIZATION_SELF_REPRESENTATION_DRIVEN_EXTENDED_CONTROLLER_V2' if passed else 'WITHHOLD_G2_NATIVE_SOURCE_REALIZATION_SELF_REPRESENTATION_DRIVEN_EXTENDED_CONTROLLER_V2'
report={
 'schema':'yado.g2.native_source_realization_self_representation_driven_extended_controller.v2',
 'status':status,'task':task,'native_goal':native_goal,
 'emitter_gene_id':eg.get('gene_id'),'emitter_gene_digest':eg.get('gene_digest'),
 'emitter_process_fresh_checks':fresh_transition_checks,
 'parent_source_sha256':parent_sha,'parent_dimensions':parent_dims,'target_dimension_from_yado_candidate':target_dim,
 'expected_extended_dimensions':expected_dims,'native_calls':native_calls,
 'native_source_candidate_count':len(source_candidates),'changed_native_source_candidate_count':len(changed),
 'selected_native_source_path':winner.get('path') if winner else None,
 'candidate_source_sha256':sha_text(candidate_source) if candidate_source else None,
 'candidate_artifact_path':str(CAND.relative_to(REPO)) if CAND.exists() else None,
 'candidate_dimensions':candidate_dims,'source_error':source_error,
 'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'V2 SEPARATES SOURCE-PROCESS PLANNING FROM SOURCE-BYTE MATERIALIZATION. THE YADO-BORN EMITTER GENE MUST FIRST REPRODUCE ITS OWN PROCESS ON FRESH VARIANTS. PASS STILL REQUIRES ACTUAL CHANGED PYTHON SOURCE TO APPEAR FROM YADO NATIVE OUTPUTS. HOST PROVIDES NO SOURCE TEMPLATE, AST SKELETON, PATCH, EMITTER SCHEMA OR TARGET FUNCTION.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'emitter_process_exec_pass':emitter_process_exec_pass,
 'native_source_candidate_count':len(source_candidates),'changed_native_source_candidate_count':len(changed),
 'candidate_source_compiles':compile_pass,'candidate_dimensions':candidate_dims,
 'next_required_capability':next_cap,'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
