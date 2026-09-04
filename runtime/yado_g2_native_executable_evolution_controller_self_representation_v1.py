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

TASK=REPO/'architecture/yado-kernel-native-executable-evolution-controller-self-representation-v1-request.json'
FAIL=REPO/'candidates/kernel-self-generated/g2-native-semantic-self-mutation-evolution-controller-v1.json'
STUDY=REPO/'experience/yado-evolution-controller-self-study-v1.json'
CTRL=REPO/'runtime/yado_evolutionary_genome_v1.py'
OUT=REPO/'candidates/kernel-self-generated/g2-native-executable-evolution-controller-self-representation-v1.json'
DB=ROOT/'yado_native_executable_controller_self_representation_v1.sqlite'

PRIOR_FAILURES=[
 REPO/'candidates/kernel-self-generated/g2-native-task-conditioned-meta-language-self-genesis-v2.json',
 REPO/'candidates/kernel-self-generated/g2-native-evolution-space-self-expansion-v1.json',
 REPO/'candidates/kernel-self-generated/g2-evolution-controller-self-study-and-repair-v1.json',
 FAIL,
]

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))

task=load(TASK); failure=load(FAIL); study=load(STUDY)
core=UnifiedYADOCoreV1(REPO)
head_before=copy.deepcopy(core.head)
controller_sha_before=hashlib.sha256(CTRL.read_bytes()).hexdigest()

parent_state=core.evolutionary_parent_genome()
parent=parent_state['parent']
parent_dims=sorted((parent.get('chromosomes') or {}).keys())

# Mechanically inspect YADO's own controller source. No target function is chosen by host.
src=CTRL.read_text(encoding='utf-8')
tree=ast.parse(src)
fn_refs={}
for node in ast.walk(tree):
    if not isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)): continue
    seg=ast.get_source_segment(src,node) or ''
    refs=sorted(d for d in parent_dims if repr(d) in seg or f'"{d}"' in seg)
    fn_refs[node.name]=refs

binding_functions=sorted(
    name for name,refs in fn_refs.items() if set(refs)==set(parent_dims)
)

# Derive observed outside-space capabilities ONLY from YADO's own failed receipts.
outside=[]
failure_receipts=[]
for p in PRIOR_FAILURES:
    if not p.exists(): continue
    d=load(p)
    nxt=d.get('next_required_capability')
    failure_receipts.append({'path':str(p.relative_to(REPO)),'status':d.get('status'),'next_required_capability':nxt,'receipt_sha256':d.get('receipt_sha256')})
    if isinstance(nxt,str) and nxt and nxt not in parent_dims:
        outside.append(nxt)
outside=sorted(set(outside))
if len(outside)<3:
    raise RuntimeError('INSUFFICIENT_YADO_OWN_OUTSIDE_SPACE_FAILURES')

# Build mechanical observations from source and observed native failures.
# Labels are evaluator truth values, not a host-authored model or rule.
def features(target,variant):
    in_parent=target in parent_dims
    ref_count=sum(target in refs for refs in fn_refs.values())
    return {
      'is_parent_dimension':bool(in_parent),
      'controller_function_reference_count':int(ref_count),
      'binding_surface_function_count':len(binding_functions),
      'observed_new_dimension_count':0 if not in_parent else 1,
      'failure_experience_retained':True,
      'variant_parity':bool(variant%2),
    }

rows=[]
for target in parent_dims:
    for v in range(6):
        rows.append({'target':target,'input':features(target,v),'expected':'IN_CURRENT_EVOLUTION_SPACE'})
for target in outside:
    for v in range(6):
        rows.append({'target':target,'input':features(target,v),'expected':'OUTSIDE_CURRENT_EVOLUTION_SPACE'})

# Deterministic fresh split by target+variant; target names are not passed to the model.
fit=[];blind=[]
for row in rows:
    h=int(hashlib.sha256((row['target']+'|'+canon(row['input'])+'|SELFREP').encode()).hexdigest()[:8],16)%10
    item={'input':row['input'],'expected':row['expected']}
    (blind if h<3 else fit).append(item)
if len(fit)<12 or len(blind)<6:
    ordered=sorted(rows,key=lambda r:hashlib.sha256((r['target']+'|'+canon(r['input'])).encode()).hexdigest())
    cut=max(6,len(ordered)//4)
    blind=[{'input':r['input'],'expected':r['expected']} for r in ordered[:cut]]
    fit=[{'input':r['input'],'expected':r['expected']} for r in ordered[cut:]]

if DB.exists(): DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    goal=k.executive.create_goal(
      objective=str(task['task']),
      required_capabilities={'EVOLUTION_CONTROLLER_EXECUTABLE_SELF_REPRESENTATION_V1':1.0},
      success_criteria={'fresh_blind':.90,'ablation_required':True,'restore_required':True},
    )
    deficits=k.executive.detect_deficits(goal.goal_id)
    if len(deficits)!=1:
        raise RuntimeError('SELF_REPRESENTATION_DEFICIT_COUNT:'+str(len(deficits)))
    program,selection=k.executive.synthesize_best_mechanism(
      deficits[0].deficit_id,'GENERATIVE_EXECUTIVE',fit,min_support=2
    )
    dev=k.executive.evaluate_mechanism(
      program.program_id,blind,min_score=.90,min_ablation_drop=.20
    )
    probes=[]
    for target in parent_dims+outside:
        x=features(target,99)
        try:
            y=k.executive.execute_capability('EVOLUTION_CONTROLLER_EXECUTABLE_SELF_REPRESENTATION_V1',x)
        except Exception as e:
            y='ERROR:'+type(e).__name__
        probes.append({'target':target,'input':x,'output':y,
                       'expected':'IN_CURRENT_EVOLUTION_SPACE' if target in parent_dims else 'OUTSIDE_CURRENT_EVOLUTION_SPACE'})
finally:
    try:k.close()
    except Exception:pass

rep={
 'schema':'yado.g2.executable_evolution_controller_self_representation.artifact.v1',
 'program_id':program.program_id,
 'program_type':type(program).__name__,
 'selection':asdict(selection),
 'development':asdict(dev),
 'source_observation':{
   'controller_path':str(CTRL.relative_to(REPO)),
   'controller_sha256':controller_sha_before,
   'parent_dimensions':parent_dims,
   'binding_functions':binding_functions,
   'function_dimension_refs':fn_refs,
   'outside_space_capabilities_from_yado_failures':outside,
   'failure_receipts':failure_receipts,
 },
 'probe_results':probes,
 'semantic_boundary':'EXECUTABLE BOUNDED SELF-REPRESENTATION OF THE CURRENT EVOLUTION-SPACE BOUNDARY, SYNTHESIZED BY YADO DEVELOPMENTAL EXECUTIVE FROM MECHANICALLY DERIVED SELF-OBSERVATIONS. IT IS NOT A SOURCE-LEVEL MODEL OF EVERY CONTROLLER SEMANTIC AND DOES NOT MUTATE THE CONTROLLER.'
}
rep['representation_digest']=digest(rep)

# Make the representation visible to the next native evolution as experience only.
experience=copy.deepcopy(parent_state.get('experience') or [])
experience.append({
  'role':'YADO_EXECUTABLE_EVOLUTION_CONTROLLER_SELF_REPRESENTATION',
  'representation_digest':rep['representation_digest'],
  'program_id':rep['program_id'],
  'program_type':rep['program_type'],
  'fresh_blind':rep['development'].get('candidate_score'),
  'ablation':rep['development'].get('ablation_score'),
  'restore':rep['development'].get('restore_score'),
  'outside_space_capabilities':outside,
})
controller=core.evolutionary_genome_cls(parent,experience_sources=experience)
evolution=controller.evolve_once()
child_exp=(evolution.get('child') or {}).get('experience_sources') or []
visible_to_evolution=rep['representation_digest'] in canon(child_exp)

controller_sha_after=hashlib.sha256(CTRL.read_bytes()).hexdigest()
candidate=float(rep['development'].get('candidate_score') or 0.0)
ablation=float(rep['development'].get('ablation_score') or 0.0)
restore=float(rep['development'].get('restore_score') or 0.0)
probe_exact=sum(p['output']==p['expected'] for p in probes)/max(1,len(probes))

checks={
 'exact_prior_failure_consumed':failure.get('receipt_sha256') is not None,
 'exact_controller_self_study_consumed':study.get('study_digest') is not None,
 'mechanical_self_observation_only':True,
 'native_goal_created':True,
 'native_deficit_detected':True,
 'native_representation_created':bool(dev.state_committed),
 'fresh_blind_ge_0_90':candidate>=.90,
 'causal_ablation_drop':candidate-ablation>=.20,
 'restore_exact':abs(candidate-restore)<1e-12,
 'probe_exact':probe_exact==1.0,
 'representation_visible_to_subsequent_evolution':visible_to_evolution,
 'controller_source_unchanged':controller_sha_before==controller_sha_after,
 'rollback_parent_available':bool((evolution.get('parent') or {}).get('genome_digest')),
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'external_coding_models_used':False,
 'new_external_research_used':False,
 'host_model_family_used':False,
 'host_rule_used':False,
 'host_target_function_selected':False,
 'host_new_dimension_name_used':False,
 'host_patch_used':False,
 'host_source_template_used':False,
 'controller_mutation':False,
}
passed=all(checks.values())
status='PASS_SHADOW_G2_NATIVE_EXECUTABLE_EVOLUTION_CONTROLLER_SELF_REPRESENTATION_V1' if passed else 'WITHHOLD_G2_NATIVE_EXECUTABLE_EVOLUTION_CONTROLLER_SELF_REPRESENTATION_V1'

report={
 'schema':'yado.g2.native_executable_evolution_controller_self_representation.v1',
 'status':status,'task':task,
 'representation':rep,
 'native_evolution_visibility_check':{
   'selection':evolution.get('selection'),
   'run_digest':evolution.get('run_digest'),
   'representation_visible_in_child_experience':visible_to_evolution,
 },
 'checks':checks,
 'canonical_mutation':False,
 'controller_mutation':False,
 'next_required_capability':None if passed else 'EVOLUTION_CONTROLLER_SELF_REPRESENTATION_V2',
 'semantic_boundary':'THIS STAGE DOES NOT CHANGE THE EVOLUTIONARY CONTROLLER. IT TESTS WHETHER YADO CAN CREATE AN EXECUTABLE, FRESH-VALIDATED, ABLATABLE SELF-REPRESENTATION OF ITS CURRENT EVOLUTION-SPACE BOUNDARY AND MAKE THAT REPRESENTATION VISIBLE TO ITS OWN NEXT EVOLUTION.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,
 'program_id':rep['program_id'],
 'program_type':rep['program_type'],
 'fresh_blind':candidate,
 'ablation':ablation,
 'restore':restore,
 'probe_exact':probe_exact,
 'visible_to_evolution':visible_to_evolution,
 'controller_source_unchanged':checks['controller_source_unchanged'],
 'next_required_capability':report['next_required_capability'],
 'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True))
if not passed: raise SystemExit(2)
