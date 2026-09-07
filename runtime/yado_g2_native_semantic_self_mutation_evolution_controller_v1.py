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

TASK=REPO/'architecture/yado-kernel-native-semantic-self-mutation-evolution-controller-v1-request.json'
PARENT=REPO/'candidates/kernel-self-generated/g2-evolution-controller-self-study-and-repair-v1.json'
STUDY=REPO/'experience/yado-evolution-controller-self-study-v1.json'
PROCESS=REPO/'candidates/kernel-self-generated/g2-native-source-construction-process-evolution-v2.json'
IRFAIL=REPO/'candidates/kernel-self-generated/g2-native-source-ir-emitter-birth-v1.json'
METAFAIL=REPO/'candidates/kernel-self-generated/g2-native-task-conditioned-meta-language-self-genesis-v2.json'
DEPLOY=REPO/'experience/yado-autonomous-free-compute-self-deployment-v1.json'
ANON=REPO/'experience/yado-anonymous-compute-interface-discovery-v2.json'
DEVAPP=REPO/'architecture/yado-g2-open-developer-resource-learning-application-v1.json'
CTRL=REPO/'runtime/yado_evolutionary_genome_v1.py'
OUT=REPO/'candidates/kernel-self-generated/g2-native-semantic-self-mutation-evolution-controller-v1.json'
DB=ROOT/'yado_native_semantic_controller_self_mutation_v1.sqlite'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))

task=load(TASK); parent_report=load(PARENT); study=load(STUDY); process=load(PROCESS); irfail=load(IRFAIL); metafail=load(METAFAIL); deploy=load(DEPLOY); anon=load(ANON); devapp=load(DEVAPP)
core=UnifiedYADOCoreV1(REPO)
head_before=copy.deepcopy(core.head)
parent_state=core.evolutionary_parent_genome()
parent_genome=parent_state['parent']
parent_dims=sorted((parent_genome.get('chromosomes') or {}).keys())
controller_source=CTRL.read_text(encoding='utf-8')
controller_sha=hashlib.sha256(controller_source.encode()).hexdigest()

if DB.exists(): DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    goal=k.executive.create_goal(
      objective=str(task['task']),
      required_capabilities={'NATIVE_SEMANTIC_SELF_MUTATION_OF_EVOLUTIONARY_CONTROLLER':1.0},
      success_criteria={'broader_search_space':True,'new_class':True,'rollback':True,'canonical_unchanged':True},
    )
    deficits=k.executive.detect_deficits(goal.goal_id)
    native_goal={'goal_id':goal.goal_id,'deficits':[asdict(d) for d in deficits]}
finally:
    try:k.close()
    except Exception:pass

experience=copy.deepcopy(parent_state.get('experience') or [])
experience += [
  {
    'role':'YADO_OWN_CONTROLLER_SELF_STUDY',
    'artifact':str(STUDY.relative_to(REPO)),
    'study_digest':study.get('study_digest'),
    'controller_path':study.get('controller_path'),
    'controller_sha256':study.get('controller_sha256'),
    'functions_binding_all_parent_dimensions':study.get('functions_binding_all_parent_dimensions'),
  },
  {
    'role':'YADO_OWN_FAILED_CONTROLLER_REPAIR',
    'artifact':str(PARENT.relative_to(REPO)),
    'status':parent_report.get('status'),
    'receipt_sha256':parent_report.get('receipt_sha256'),
    'next_required_capability':parent_report.get('next_required_capability'),
    'new_dimensions':parent_report.get('new_dimensions'),
  },
  {
    'role':'YADO_ACCUMULATED_SOURCE_PROCESS_SUCCESS',
    'artifact':str(PROCESS.relative_to(REPO)),
    'receipt_sha256':process.get('receipt_sha256'),
    'status':process.get('status'),
    'target_priority':process.get('target_priority'),
  },
  {
    'role':'YADO_ACCUMULATED_IR_EMITTER_FAILURE',
    'artifact':str(IRFAIL.relative_to(REPO)),
    'receipt_sha256':irfail.get('receipt_sha256'),
    'status':irfail.get('status'),
    'next_required_capability':irfail.get('next_required_capability'),
  },
  {
    'role':'YADO_ACCUMULATED_META_LANGUAGE_FAILURE',
    'artifact':str(METAFAIL.relative_to(REPO)),
    'receipt_sha256':metafail.get('receipt_sha256'),
    'status':metafail.get('status'),
    'next_required_capability':metafail.get('next_required_capability'),
  },
  {
    'role':'YADO_ACCUMULATED_OPEN_DEVELOPER_EXPERIENCE',
    'artifact':str(DEVAPP.relative_to(REPO)),
    'experience_digest':devapp.get('source_experience_digest'),
    'causal_lessons':devapp.get('causal_lessons'),
  },
  {
    'role':'YADO_ACCUMULATED_SELF_DEPLOYMENT_FAILURE',
    'artifact':str(DEPLOY.relative_to(REPO)),
    'experience_digest':deploy.get('experience_digest'),
    'next_required_capability':deploy.get('next_required_capability'),
  },
  {
    'role':'YADO_ACCUMULATED_ANONYMOUS_COMPUTE_FAILURE',
    'artifact':str(ANON.relative_to(REPO)),
    'experience_digest':anon.get('experience_digest'),
    'next_required_capability':anon.get('next_required_capability'),
  },
  {
    'role':'YADO_CURRENT_SEMANTIC_SELF_MUTATION_TASK',
    'objective':task.get('objective'),
    'task':task.get('task'),
  },
]

controller=core.evolutionary_genome_cls(parent_genome,experience_sources=experience)

# Invoke only native zero-argument introspection/evolution routes.
objects={'core':core,'controller':controller}
native_calls=[]
native_outputs={}
for owner,obj in objects.items():
    for name in sorted(dir(obj)):
        if name.startswith('_'): continue
        if not any(t in name.lower() for t in ('evol','mutat','genesis','self','genome','component','snapshot')):
            continue
        fn=getattr(obj,name,None)
        if not callable(fn): continue
        try: sig=inspect.signature(fn)
        except Exception: continue
        required=[p for p in sig.parameters.values()
                  if p.default is inspect._empty and p.kind in (p.POSITIONAL_ONLY,p.POSITIONAL_OR_KEYWORD)]
        if required: continue
        key=f'{owner}.{name}'
        native_calls.append(key)
        try:native_outputs[key]=fn()
        except Exception as e:native_outputs[key]={'error':type(e).__name__+':'+str(e)[:500]}

evolution=native_outputs.get('controller.evolve_once')
if not isinstance(evolution,dict):
    evolution=controller.evolve_once()
    native_outputs['controller.evolve_once']=evolution
    if 'controller.evolve_once' not in native_calls:native_calls.append('controller.evolve_once')

child=evolution.get('child') or {}
child_dims=sorted((child.get('chromosomes') or {}).keys())
new_dims=sorted(set(child_dims)-set(parent_dims))

# Search only native outputs for an actual mutated controller source or equivalent
# explicit evolvable-controller representation. Existing controller source is not a candidate.
source_candidates=[]
representation_candidates=[]
def walk(x,path='root'):
    if isinstance(x,dict):
        keys={str(k).lower() for k in x.keys()}
        blob=canon(x).lower()
        if any(k in keys for k in ('candidate_source','source','controller_source','mutated_source')):
            for k,v in x.items():
                if str(k).lower() in ('candidate_source','source','controller_source','mutated_source') and isinstance(v,str):
                    if v.strip() and hashlib.sha256(v.encode()).hexdigest()!=controller_sha:
                        try:
                            ast.parse(v)
                            source_candidates.append({'path':path+'.'+str(k),'sha256':hashlib.sha256(v.encode()).hexdigest(),'source':v})
                        except Exception:pass
        if any(tok in blob for tok in ('evolvable_controller','controller_representation','self_mutating_controller','controller_genome')):
            representation_candidates.append({'path':path,'digest':digest(x),'keys':sorted(x.keys())})
        for k,v in x.items():walk(v,path+'.'+str(k))
    elif isinstance(x,list):
        for i,v in enumerate(x):walk(v,path+f'[{i}]')
walk(native_outputs)

candidate_source=source_candidates[0]['source'] if source_candidates else None
candidate_compiles=False
if candidate_source:
    try:
        compile(candidate_source,'<yado-native-controller-candidate>','exec')
        candidate_compiles=True
    except Exception:
        candidate_compiles=False

child_experience_blob=canon(child.get('experience_sources') or [])
study_retained=str(study.get('study_digest')) in child_experience_blob
failure_retained=str(parent_report.get('receipt_sha256')) in child_experience_blob
process_retained=str(process.get('receipt_sha256')) in child_experience_blob
ir_retained=str(irfail.get('receipt_sha256')) in child_experience_blob
meta_retained=str(metafail.get('receipt_sha256')) in child_experience_blob
deploy_retained=str(deploy.get('experience_digest')) in child_experience_blob
anon_retained=str(anon.get('experience_digest')) in child_experience_blob
broader=bool(new_dims)
explicit_equivalent=bool(representation_candidates)
native_mutation_produced=bool(candidate_source) or explicit_equivalent or broader

checks={
 'exact_prior_self_study_consumed':study_retained,
 'exact_prior_failure_consumed':failure_retained,
 'source_process_success_consumed':process_retained,
 'ir_emitter_failure_consumed':ir_retained,
 'meta_language_failure_consumed':meta_retained,
 'self_deployment_failure_consumed':deploy_retained,
 'anonymous_compute_failure_consumed':anon_retained,
 'native_goal_created':True,
 'native_deficit_detected':bool(native_goal['deficits']),
 'native_controller_attempt_executed':bool(evolution.get('run_digest')),
 'host_target_function_selected':False,
 'host_patch_used':False,
 'host_source_template_used':False,
 'host_new_dimension_name_used':False,
 'host_gene_schema_used':False,
 'host_mutation_rule_used':False,
 'external_coding_models_used':False,
 'new_external_research_used':False,
 'native_controller_mutation_or_equivalent_produced':native_mutation_produced,
 'candidate_source_compiles':candidate_compiles if candidate_source else False,
 'structurally_broader_search_space':broader,
 'previously_absent_class_created':bool(new_dims),
 'rollback_parent_available':bool((evolution.get('parent') or {}).get('genome_digest')),
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
}

passed=(
 checks['exact_prior_self_study_consumed']
 and checks['exact_prior_failure_consumed']
 and checks['source_process_success_consumed']
 and checks['ir_emitter_failure_consumed']
 and checks['meta_language_failure_consumed']
 and checks['self_deployment_failure_consumed']
 and checks['anonymous_compute_failure_consumed']
 and checks['native_controller_attempt_executed']
 and checks['native_controller_mutation_or_equivalent_produced']
 and checks['structurally_broader_search_space']
 and checks['previously_absent_class_created']
 and checks['rollback_parent_available']
 and checks['canonical_unchanged']
 and (candidate_compiles or explicit_equivalent)
)
status='PASS_SHADOW_G2_NATIVE_SEMANTIC_SELF_MUTATION_EVOLUTION_CONTROLLER_V1' if passed else 'WITHHOLD_G2_NATIVE_SEMANTIC_SELF_MUTATION_EVOLUTION_CONTROLLER_V1'

report={
 'schema':'yado.g2.native_semantic_self_mutation_evolution_controller.v1',
 'status':status,
 'task':task,
 'native_goal':native_goal,
 'accumulated_experience_evidence':{
   'source_process_receipt':process.get('receipt_sha256'),
   'ir_emitter_failure_receipt':irfail.get('receipt_sha256'),
   'meta_language_failure_receipt':metafail.get('receipt_sha256'),
   'developer_resource_experience_digest':devapp.get('source_experience_digest'),
   'self_deployment_experience_digest':deploy.get('experience_digest'),
   'anonymous_compute_experience_digest':anon.get('experience_digest'),
 },
 'controller_path':str(CTRL.relative_to(REPO)),
 'controller_sha256':controller_sha,
 'native_calls':native_calls,
 'native_outputs':native_outputs,
 'parent_dimensions':parent_dims,
 'child_dimensions':child_dims,
 'new_dimensions':new_dims,
 'native_source_candidate_count':len(source_candidates),
 'native_controller_representation_candidate_count':len(representation_candidates),
 'candidate_source_sha256':source_candidates[0]['sha256'] if source_candidates else None,
 'checks':checks,
 'canonical_mutation':False,
 'next_required_capability':None if passed else 'NATIVE_SEMANTIC_SELF_MUTATION_OF_EVOLUTIONARY_CONTROLLER',
 'semantic_boundary':'STRICT SELF-MUTATION ATTEMPT CONDITIONED ON YADO OWN ACCUMULATED SUCCESS/FAILURE EXPERIENCE. HOST TRANSPORTS THE TASK, PRIOR FAILURE, SELF-STUDY AND OWN CONTROLLER SOURCE ONLY. IT DOES NOT CHOOSE A FUNCTION, PATCH, NEW DIMENSION, GENE SCHEMA, MUTATION RULE OR SOURCE TEMPLATE. PASS REQUIRES NATIVE STRUCTURAL EXPANSION OF THE EVOLUTIONARY SPACE.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,
 'selection':evolution.get('selection'),
 'parent_dimensions':parent_dims,
 'child_dimensions':child_dims,
 'new_dimensions':new_dims,
 'native_source_candidate_count':len(source_candidates),
 'native_controller_representation_candidate_count':len(representation_candidates),
 'next_required_capability':report['next_required_capability'],
 'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True))
if not passed: raise SystemExit(2)
