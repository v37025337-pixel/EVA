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

TASK=REPO/'architecture/yado-kernel-evolution-controller-self-study-and-repair-v1-request.json'
FAIL=REPO/'candidates/kernel-self-generated/g2-native-evolution-space-self-expansion-v1.json'
CTRL=REPO/'runtime/yado_evolutionary_genome_v1.py'
OUT=REPO/'candidates/kernel-self-generated/g2-evolution-controller-self-study-and-repair-v1.json'
STUDY=REPO/'experience/yado-evolution-controller-self-study-v1.json'
DB=ROOT/'yado_evolution_controller_self_study_v1.sqlite'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))

task=load(TASK); failure=load(FAIL)
core=UnifiedYADOCoreV1(REPO)
head_before=copy.deepcopy(core.head)

parent_state=core.evolutionary_parent_genome()
parent=parent_state['parent']
parent_dims=sorted((parent.get('chromosomes') or {}).keys())

# Study the controller mechanically from its own source; no target function is supplied.
src=CTRL.read_text(encoding='utf-8')
tree=ast.parse(src)
funcs=[]
for node in ast.walk(tree):
    if not isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)): continue
    segment=ast.get_source_segment(src,node) or ''
    refs={d for d in parent_dims if repr(d) in segment or f'"{d}"' in segment}
    funcs.append({
      'name':node.name,'lineno':node.lineno,'end_lineno':getattr(node,'end_lineno',None),
      'parent_dimension_refs':sorted(refs),
      'ref_count':len(refs),
      'source_sha256':hashlib.sha256(segment.encode()).hexdigest(),
    })
funcs.sort(key=lambda r:(-r['ref_count'],r['lineno'],r['name']))
fixed_surface=[r for r in funcs if r['ref_count']==len(parent_dims)]

study={
 'schema':'yado.g2.evolution_controller_self_study.v1',
 'source_failure_receipt':failure.get('receipt_sha256'),
 'failure_status':failure.get('status'),
 'failure_next_required_capability':failure.get('next_required_capability'),
 'parent_dimensions':parent_dims,
 'controller_path':str(CTRL.relative_to(REPO)),
 'controller_sha256':hashlib.sha256(src.encode()).hexdigest(),
 'function_structure':funcs,
 'functions_binding_all_parent_dimensions':fixed_surface,
 'observation':{
   'parent_dimension_count':len(parent_dims),
   'child_dimension_count':int((failure.get('checks') or {}).get('child_chromosome_count') or 0),
   'new_dimension_count':len(failure.get('new_chromosomes') or []),
   'failure_retained_experience':bool((failure.get('checks') or {}).get('prior_failure_consumed_as_experience')),
 },
 'semantic_boundary':'MECHANICAL SELF-SOURCE STUDY ONLY. FUNCTION STRUCTURE AND DIMENSION REFERENCES ARE EXTRACTED FROM YADO OWN CONTROLLER SOURCE AND PRIOR FAILURE. NO TARGET FUNCTION, PATCH, NEW DIMENSION NAME, GENE SCHEMA OR MUTATION RULE IS SUPPLIED BY THE HOST.'
}
study['study_digest']=digest(study)
STUDY.parent.mkdir(parents=True,exist_ok=True)
STUDY.write_text(json.dumps(study,indent=2,sort_keys=True)+'\n',encoding='utf-8')

if DB.exists():DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    goal=k.executive.create_goal(
      objective=str(task['instruction']),
      required_capabilities={'EVOLUTIONARY_CONTROLLER_SELF_REPRESENTATION_AND_MUTATION':1.0},
      success_criteria={'broader_search_space':True,'native_origin':True,'rollback':True},
    )
    deficits=k.executive.detect_deficits(goal.goal_id)
    native_goal={'goal_id':goal.goal_id,'deficits':[asdict(d) for d in deficits]}
finally:
    try:k.close()
    except Exception:pass

# Let YADO consume its own study and failure as experience, then make its native attempt.
experience=copy.deepcopy(parent_state.get('experience') or [])
experience += [
  {
    'role':'YADO_OWN_EVOLUTION_CONTROLLER_SELF_STUDY',
    'artifact':str(STUDY.relative_to(REPO)),
    'study_digest':study['study_digest'],
    'source_failure_receipt':failure.get('receipt_sha256'),
    'fixed_surface':fixed_surface,
  },
  {
    'role':'YADO_OWN_EVOLUTION_SPACE_FAILURE',
    'artifact':str(FAIL.relative_to(REPO)),
    'receipt_sha256':failure.get('receipt_sha256'),
    'status':failure.get('status'),
    'new_chromosomes':failure.get('new_chromosomes'),
    'checks':failure.get('checks'),
  },
]
controller=core.evolutionary_genome_cls(parent,experience_sources=experience)
evolution=controller.evolve_once()

child=evolution.get('child') or {}
child_dims=sorted((child.get('chromosomes') or {}).keys())
new_dims=sorted(set(child_dims)-set(parent_dims))
study_retained=study['study_digest'] in canon(child.get('experience_sources') or [])
failure_retained=str(failure.get('receipt_sha256')) in canon(child.get('experience_sources') or [])

checks={
 'exact_failed_result_studied':study['source_failure_receipt']==failure.get('receipt_sha256'),
 'controller_source_studied':bool(funcs),
 'self_study_retained_as_experience':study_retained,
 'failure_retained_as_experience':failure_retained,
 'native_goal_created':True,
 'native_deficit_detected':bool(native_goal['deficits']),
 'native_attempt_after_study':bool(evolution.get('run_digest')),
 'parent_dimension_count':len(parent_dims),
 'child_dimension_count':len(child_dims),
 'structurally_broader_search_space':len(new_dims)>0,
 'previously_absent_class_created':len(new_dims)>0,
 'external_coding_models_used':False,
 'new_external_research_used':False,
 'host_target_function_selected':False,
 'host_new_chromosome_name_used':False,
 'host_gene_schema_used':False,
 'host_mutation_rule_used':False,
 'host_patch_used':False,
 'host_source_template_used':False,
 'rollback_parent_available':bool((evolution.get('parent') or {}).get('genome_digest')),
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
}
passed=(
 checks['exact_failed_result_studied'] and checks['controller_source_studied']
 and checks['self_study_retained_as_experience'] and checks['failure_retained_as_experience']
 and checks['native_attempt_after_study'] and checks['structurally_broader_search_space']
 and checks['previously_absent_class_created'] and checks['rollback_parent_available']
 and checks['canonical_unchanged']
)
status='PASS_SHADOW_G2_EVOLUTION_CONTROLLER_SELF_STUDY_AND_REPAIR_V1' if passed else 'WITHHOLD_G2_EVOLUTION_CONTROLLER_SELF_STUDY_AND_REPAIR_V1'

report={
 'schema':'yado.g2.evolution_controller_self_study_and_repair.v1',
 'status':status,'task':task,'native_goal':native_goal,
 'study_artifact':str(STUDY.relative_to(REPO)),'study_digest':study['study_digest'],
 'self_study_summary':study,
 'native_evolution':evolution,
 'parent_dimensions':parent_dims,'child_dimensions':child_dims,'new_dimensions':new_dims,
 'checks':checks,'canonical_mutation':False,
 'next_required_capability':None if passed else 'NATIVE_SEMANTIC_SELF_MUTATION_OF_EVOLUTIONARY_CONTROLLER',
 'semantic_boundary':'YADO STUDIES ITS OWN FAILED RESULT AND CONTROLLER SOURCE, RETAINS THAT STUDY AS EXPERIENCE, THEN RE-RUNS ITS NATIVE EVOLUTIONARY CONTROLLER. THE HOST DOES NOT CHOOSE A TARGET FUNCTION OR WRITE A PATCH. PASS REQUIRES A REAL NEW EVOLUTIONARY DIMENSION; REPEATING NEW GENES INSIDE THE SAME FIXED DIMENSIONS IS WITHHOLD.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,
 'studied_functions_binding_all_dimensions':[x['name'] for x in fixed_surface],
 'study_retained':study_retained,
 'failure_retained':failure_retained,
 'selection':evolution.get('selection'),
 'parent_dimensions':parent_dims,
 'child_dimensions':child_dims,
 'new_dimensions':new_dims,
 'next_required_capability':report['next_required_capability'],
 'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True))
if not passed: raise SystemExit(2)
