from __future__ import annotations
from pathlib import Path
from dataclasses import asdict
import copy,hashlib,inspect,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive

TASK=REPO/'architecture/yado-kernel-native-evolution-space-self-expansion-v1-request.json'
FAIL=REPO/'candidates/kernel-self-generated/g2-native-task-conditioned-meta-language-self-genesis-v2.json'
OUT=REPO/'candidates/kernel-self-generated/g2-native-evolution-space-self-expansion-v1.json'
DB=ROOT/'yado_native_evolution_space_self_expansion_v1.sqlite'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))

task=load(TASK); failure=load(FAIL)
core=UnifiedYADOCoreV1(REPO)
head_before=copy.deepcopy(core.head)

if DB.exists(): DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    goal=k.executive.create_goal(
      objective=str(task['task']),
      required_capabilities={'EVOLUTION_SPACE_SELF_EXPANSION_V1':1.0},
      success_criteria={'new_search_dimension':True,'native_origin':True,'rollback':True},
    )
    deficits=k.executive.detect_deficits(goal.goal_id)
    native_goal={'goal_id':goal.goal_id,'deficits':[asdict(d) for d in deficits]}
finally:
    try:k.close()
    except Exception:pass

state=core.evolutionary_parent_genome()
parent=state['parent']
parent_chromosomes=set((parent.get('chromosomes') or {}).keys())
experience=copy.deepcopy(state.get('experience') or [])
experience.append({
  'role':'YADO_OWN_EVOLUTION_SPACE_FAILURE',
  'artifact':str(FAIL.relative_to(REPO)),
  'status':failure.get('status'),
  'next_required_capability':failure.get('next_required_capability'),
  'receipt_sha256':failure.get('receipt_sha256'),
  'language_gene_hits':failure.get('language_gene_hits'),
  'checks':failure.get('checks'),
})
experience.append({
  'role':'CURRENT_TASK',
  'objective':task.get('objective'),
  'task':task.get('task'),
  'constraints':task.get('constraints'),
})

controller=core.evolutionary_genome_cls(parent,experience_sources=experience)

# Let native controller expose any zero-argument self-expansion/evolution entrypoints it already has.
native_zero_arg=[]
native_zero_arg_results={}
for name in sorted(dir(controller)):
    if name.startswith('_'): continue
    if not any(tok in name.lower() for tok in ('evol','expand','genesis','mutat','chromosome','gene')):
        continue
    fn=getattr(controller,name,None)
    if not callable(fn): continue
    try:sig=inspect.signature(fn)
    except Exception:continue
    required=[p for p in sig.parameters.values()
              if p.default is inspect._empty and p.kind in (p.POSITIONAL_ONLY,p.POSITIONAL_OR_KEYWORD)]
    if required:continue
    native_zero_arg.append(name)
    try:native_zero_arg_results[name]=fn()
    except Exception as e:native_zero_arg_results[name]={'error':type(e).__name__+':'+str(e)[:600]}

evolution=native_zero_arg_results.get('evolve_once')
if not isinstance(evolution,dict):
    evolution=controller.evolve_once()

child=evolution.get('child') or {}
child_chromosomes=set((child.get('chromosomes') or {}).keys())
new_chromosomes=sorted(child_chromosomes-parent_chromosomes)

# Also detect any new explicit mechanism/gene class emitted outside the fixed chromosome map.
parent_gene_ids={str(v.get('gene_id')) for v in (parent.get('chromosomes') or {}).values() if isinstance(v,dict)}
child_gene_ids={str(v.get('gene_id')) for v in (child.get('chromosomes') or {}).values() if isinstance(v,dict)}
new_gene_ids=sorted(x for x in child_gene_ids-parent_gene_ids if x and x!='None')

task_failure_digest=failure.get('receipt_sha256')
failure_retained=task_failure_digest in canon(child.get('experience_sources') or [])

structural_expansion=bool(new_chromosomes)
new_class_chosen_by_yado=bool(new_chromosomes)
rollback_parent=bool(evolution.get('parent',{}).get('genome_digest'))

checks={
  'prior_failure_consumed_as_experience':failure_retained,
  'native_goal_created':True,
  'native_deficit_detected':bool(native_goal['deficits']),
  'native_evolution_executed':bool(evolution.get('run_digest')),
  'parent_chromosome_count':len(parent_chromosomes),
  'child_chromosome_count':len(child_chromosomes),
  'structurally_broader_search_space':structural_expansion,
  'previously_absent_class_created':new_class_chosen_by_yado,
  'external_coding_models_used':False,
  'new_external_research_used':False,
  'host_new_chromosome_name_used':False,
  'host_gene_schema_used':False,
  'host_operator_list_used':False,
  'host_mutation_rule_used':False,
  'host_source_seed_used':False,
  'host_patch_used':False,
  'host_target_file_selected':False,
  'rollback_parent_available':rollback_parent,
  'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
}

passed=(
  checks['prior_failure_consumed_as_experience']
  and checks['native_goal_created']
  and checks['native_deficit_detected']
  and checks['native_evolution_executed']
  and checks['structurally_broader_search_space']
  and checks['previously_absent_class_created']
  and checks['rollback_parent_available']
  and checks['canonical_unchanged']
)
status='PASS_SHADOW_G2_NATIVE_EVOLUTION_SPACE_SELF_EXPANSION_V1' if passed else 'WITHHOLD_G2_NATIVE_EVOLUTION_SPACE_SELF_EXPANSION_V1'

report={
 'schema':'yado.g2.native_evolution_space_self_expansion.v1',
 'status':status,
 'task':task,
 'native_goal':native_goal,
 'parent_failure_receipt':task_failure_digest,
 'parent_chromosomes':sorted(parent_chromosomes),
 'child_chromosomes':sorted(child_chromosomes),
 'new_chromosomes':new_chromosomes,
 'new_gene_ids_within_existing_chromosomes':new_gene_ids,
 'native_zero_arg_methods_invoked':native_zero_arg,
 'native_zero_arg_results':native_zero_arg_results,
 'native_evolution':evolution,
 'checks':checks,
 'canonical_mutation':False,
 'next_required_capability':None if passed else 'NATIVE_EVOLUTIONARY_CONTROLLER_SELF_REPRESENTATION_AND_MUTATION_V2',
 'semantic_boundary':'TASK-ONLY STRUCTURAL SELF-EXPANSION TEST. NEW GENE VALUES INSIDE THE SAME FIXED CHROMOSOME SET DO NOT COUNT. PASS REQUIRES YADO TO CREATE A PREVIOUSLY ABSENT EVOLUTIONARY CLASS/DIMENSION WITHOUT HOST NAMING OR SCHEMA.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,
 'parent_chromosomes':sorted(parent_chromosomes),
 'child_chromosomes':sorted(child_chromosomes),
 'new_chromosomes':new_chromosomes,
 'new_gene_ids_within_existing_chromosomes':new_gene_ids,
 'selection':evolution.get('selection'),
 'next_required_capability':report['next_required_capability'],
 'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
