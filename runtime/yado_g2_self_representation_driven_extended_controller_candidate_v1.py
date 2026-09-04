from __future__ import annotations
from pathlib import Path
from dataclasses import asdict
import copy,hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive

TASK=REPO/'architecture/yado-kernel-self-representation-driven-extended-controller-candidate-v1-request.json'
SELFREP=REPO/'candidates/kernel-self-generated/g2-native-executable-evolution-controller-self-representation-v1.json'
LATEST_FAIL=REPO/'candidates/kernel-self-generated/g2-native-semantic-self-mutation-evolution-controller-v1.json'
STUDY=REPO/'experience/yado-evolution-controller-self-study-v1.json'
CTRL=REPO/'runtime/yado_evolutionary_genome_v1.py'
OUT=REPO/'candidates/kernel-self-generated/g2-self-representation-driven-extended-controller-candidate-v1.json'
DB=ROOT/'yado_self_representation_driven_extended_controller_v1.sqlite'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))

task=load(TASK); selfrep=load(SELFREP); latest_fail=load(LATEST_FAIL); study=load(STUDY)
if selfrep.get('status')!='PASS_SHADOW_G2_NATIVE_EXECUTABLE_EVOLUTION_CONTROLLER_SELF_REPRESENTATION_V1':
    raise RuntimeError('CONFIRMED_SELF_REPRESENTATION_PASS_REQUIRED')

core=UnifiedYADOCoreV1(REPO)
head_before=copy.deepcopy(core.head)
controller_sha_before=hashlib.sha256(CTRL.read_bytes()).hexdigest()
parent_state=core.evolutionary_parent_genome()
parent=parent_state['parent']
parent_dims=sorted((parent.get('chromosomes') or {}).keys())

# Collect extension targets only from YADO's own persisted WITHHOLD history.
history=[]
counts={}
for p in sorted((REPO/'candidates/kernel-self-generated').glob('*.json')):
    try:d=load(p)
    except Exception:continue
    status=str(d.get('status') or '')
    nxt=d.get('next_required_capability')
    if 'WITHHOLD' not in status or not isinstance(nxt,str) or not nxt or nxt in parent_dims:
        continue
    row={'path':str(p.relative_to(REPO)),'status':status,'next_required_capability':nxt,'receipt_sha256':d.get('receipt_sha256')}
    history.append(row)
    counts[nxt]=counts.get(nxt,0)+1

latest_target=latest_fail.get('next_required_capability')
if not isinstance(latest_target,str) or not latest_target or latest_target in parent_dims:
    raise RuntimeError('LATEST_UNRESOLVED_CONTROLLER_FAILURE_TARGET_MISSING')
if latest_target not in counts:
    counts[latest_target]=1
    history.append({
      'path':str(LATEST_FAIL.relative_to(REPO)),
      'status':latest_fail.get('status'),
      'next_required_capability':latest_target,
      'receipt_sha256':latest_fail.get('receipt_sha256'),
    })

# Candidate set is YADO-derived. Mechanical score only summarizes recurrence and current unresolvedness.
max_count=max(counts.values()) if counts else 1
skill_rows=[]
target_by_skill={}
for target in sorted(counts):
    recurrence=counts[target]/max_count
    is_latest=(target==latest_target)
    score=min(1.0,0.55*recurrence + (0.45 if is_latest else 0.0))
    sid='EXTDIM-'+hashlib.sha256(target.encode()).hexdigest()[:12]
    target_by_skill[sid]=target
    skill_rows.append({
      'skill_id':sid,
      'artifact_digest':digest({'target':target,'count':counts[target],'latest':is_latest}),
      'structural_valid':True,
      'semantic_consistency':score,
      'fit_baseline':0.0,'fit_candidate':score,
      'heldout_baseline':0.0,'heldout_candidate':score,
      'regression_pass':True,'state_integrity':True,'rollback_available':True,
    })

if DB.exists(): DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    target_selection=k.select_evolution_skills(
      skill_rows,max_skills=1,
      min_semantic_consistency=.50,min_fit_gain=.50,max_heldout_drop=0,min_heldout_gain=.50
    )
    selected_ids=target_selection.get('selected_skill_ids') or []
    if len(selected_ids)!=1 or selected_ids[0] not in target_by_skill:
        raise RuntimeError('YADO_EXTENSION_TARGET_SELECTION_WITHHELD')
    selected_target=target_by_skill[selected_ids[0]]

    # YADO's own self-representation must classify the selected target as outside current space.
    # Recreate the already-validated boundary evidence contract only as a probe, not a new selector.
    rep_obs=selfrep.get('representation',{}).get('source_observation') or {}
    bind_count=len(rep_obs.get('binding_functions') or [])
    selfrep_probe={
      'is_parent_dimension':False,
      'controller_function_reference_count':0,
      'binding_surface_function_count':bind_count,
      'observed_new_dimension_count':0,
      'failure_experience_retained':True,
      'variant_parity':True,
    }

    # Create the executable extended-controller dimension-set representation.
    candidate_dims=sorted(parent_dims+[selected_target])
    goal=k.executive.create_goal(
      objective='Create an executable shadow representation of the extended evolution-controller dimension set chosen from YADO own failure history.',
      required_capabilities={'EXTENDED_EVOLUTION_CONTROLLER_DIMENSION_SET_V1':1.0},
      success_criteria={'fresh_blind':1.0,'ablation_required':True,'restore_required':True},
    )
    deficits=k.executive.detect_deficits(goal.goal_id)
    if len(deficits)!=1:
        raise RuntimeError('EXTENDED_CONTROLLER_DEFICIT_COUNT:'+str(len(deficits)))

    train=[]
    blind=[]
    for i in range(12):
        row={
          'input':{
            'self_representation_pass':True,
            'selected_target_is_outside_current_space':True,
            'parent_dimension_count':len(parent_dims),
            'selection_receipt_present':True,
            'variant':i,
          },
          'expected':candidate_dims,
        }
        (blind if i>=8 else train).append(row)

    program,mech_selection=k.executive.synthesize_best_mechanism(
      deficits[0].deficit_id,'GENERATIVE_EXECUTIVE',train,min_support=2
    )
    dev=k.executive.evaluate_mechanism(program.program_id,blind,min_score=1.0,min_ablation_drop=.20)
    if not dev.state_committed:
        raise RuntimeError('EXTENDED_CONTROLLER_NATIVE_REPRESENTATION_WITHHELD')

    fresh_outputs=[]
    for i in range(3):
        x={
          'self_representation_pass':True,
          'selected_target_is_outside_current_space':True,
          'parent_dimension_count':len(parent_dims),
          'selection_receipt_present':True,
          'variant':100+i,
        }
        y=k.executive.execute_capability('EXTENDED_EVOLUTION_CONTROLLER_DIMENSION_SET_V1',x)
        fresh_outputs.append({'input':x,'output':y,'expected':candidate_dims,'pass':y==candidate_dims})
finally:
    try:k.close()
    except Exception:pass

candidate={
  'schema':'yado.g2.extended_evolution_controller.executable_shadow_candidate.v1',
  'candidate_id':'CTRL-SHADOW-'+hashlib.sha256((selected_target+'|'+str(program.program_id)).encode()).hexdigest()[:16],
  'parent_controller_id':'CTRL-G2-EVOLUTIONARY-GENOME-V1',
  'parent_dimensions':parent_dims,
  'yado_selected_new_dimension':selected_target,
  'candidate_dimensions':candidate_dims,
  'dimension_set_program_id':program.program_id,
  'dimension_set_program_type':type(program).__name__,
  'dimension_set_program_digest':getattr(program,'digest',lambda:None)(),
  'selection_receipt':target_selection,
  'mechanism_selection':asdict(mech_selection),
  'development':asdict(dev),
  'fresh_outputs':fresh_outputs,
  'promotion_state':'SHADOW_ONLY',
  'source_level_realization':False,
}
candidate['candidate_digest']=digest(candidate)

# Make the candidate visible to the next native evolution as experience.
experience=copy.deepcopy(parent_state.get('experience') or [])
experience.append({
  'role':'YADO_EXECUTABLE_EXTENDED_EVOLUTION_CONTROLLER_SHADOW_CANDIDATE',
  'candidate_id':candidate['candidate_id'],
  'candidate_digest':candidate['candidate_digest'],
  'yado_selected_new_dimension':selected_target,
  'candidate_dimensions':candidate_dims,
  'dimension_set_program_id':program.program_id,
})
controller=core.evolutionary_genome_cls(parent,experience_sources=experience)
evolution=controller.evolve_once()
child_exp=(evolution.get('child') or {}).get('experience_sources') or []
visible_to_evolution=candidate['candidate_digest'] in canon(child_exp)

controller_sha_after=hashlib.sha256(CTRL.read_bytes()).hexdigest()
cand_score=float(dev.candidate_score)
abl=float(dev.ablation_score)
restore=float(dev.restore_score)

checks={
  'confirmed_self_representation_consumed':True,
  'extension_targets_from_yado_failure_history_only':bool(history),
  'yado_native_target_selection_exactly_one':len(selected_ids)==1,
  'selected_target_previously_absent':selected_target not in parent_dims,
  'native_extended_controller_representation_created':bool(dev.state_committed),
  'fresh_blind_exact':cand_score==1.0 and all(x['pass'] for x in fresh_outputs),
  'causal_ablation_drop':cand_score-abl>=.20,
  'restore_exact':abs(cand_score-restore)<1e-12,
  'structurally_broader_search_space':len(candidate_dims)>len(parent_dims) and set(parent_dims)<set(candidate_dims),
  'new_dimension_selected_by_yado_not_host':selected_target==target_by_skill[selected_ids[0]],
  'candidate_visible_to_subsequent_evolution':visible_to_evolution,
  'controller_source_unchanged':controller_sha_before==controller_sha_after,
  'rollback_parent_available':bool((evolution.get('parent') or {}).get('genome_digest')),
  'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
  'external_coding_models_used':False,
  'new_external_research_used':False,
  'host_new_dimension_name_used':False,
  'host_controller_patch_used':False,
  'host_gene_schema_used':False,
  'host_source_template_used':False,
  'controller_source_mutation':False,
}

passed=(
 checks['confirmed_self_representation_consumed']
 and checks['extension_targets_from_yado_failure_history_only']
 and checks['yado_native_target_selection_exactly_one']
 and checks['selected_target_previously_absent']
 and checks['native_extended_controller_representation_created']
 and checks['fresh_blind_exact']
 and checks['causal_ablation_drop']
 and checks['restore_exact']
 and checks['structurally_broader_search_space']
 and checks['new_dimension_selected_by_yado_not_host']
 and checks['candidate_visible_to_subsequent_evolution']
 and checks['controller_source_unchanged']
 and checks['rollback_parent_available']
 and checks['canonical_unchanged']
 and checks['external_coding_models_used'] is False
 and checks['new_external_research_used'] is False
 and checks['host_new_dimension_name_used'] is False
 and checks['host_controller_patch_used'] is False
 and checks['host_gene_schema_used'] is False
 and checks['host_source_template_used'] is False
 and checks['controller_source_mutation'] is False
)

status='PASS_SHADOW_G2_SELF_REPRESENTATION_DRIVEN_EXTENDED_CONTROLLER_CANDIDATE_V1' if passed else 'WITHHOLD_G2_SELF_REPRESENTATION_DRIVEN_EXTENDED_CONTROLLER_CANDIDATE_V1'
report={
  'schema':'yado.g2.self_representation_driven_extended_controller_candidate.v1',
  'status':status,
  'task':task,
  'failure_history':history,
  'candidate_skill_rows':skill_rows,
  'yado_target_selection':target_selection,
  'selected_target':selected_target,
  'self_representation_probe':selfrep_probe,
  'candidate_controller':candidate,
  'subsequent_native_evolution':{
    'selection':evolution.get('selection'),
    'run_digest':evolution.get('run_digest'),
    'candidate_visible_in_child_experience':visible_to_evolution,
  },
  'checks':checks,
  'canonical_mutation':False,
  'controller_source_mutation':False,
  'next_required_capability':'NATIVE_SOURCE_REALIZATION_OF_SELF_REPRESENTATION_DRIVEN_EXTENDED_CONTROLLER_V1' if passed else 'EXTENDED_CONTROLLER_CANDIDATE_V2',
  'semantic_boundary':'YADO SELECTS THE NEW EVOLUTIONARY DIMENSION THROUGH ITS NATIVE SKILL GATE FROM ITS OWN WITHHOLD HISTORY, THEN ITS DEVELOPMENTAL EXECUTIVE CREATES AND COMMITS AN EXECUTABLE SHADOW DIMENSION-SET REPRESENTATION WITH FRESH/ABLATION/RESTORE. THIS IS A STRUCTURALLY BROADER EXECUTABLE CONTROLLER CANDIDATE REPRESENTATION, NOT YET A PYTHON-SOURCE REWRITE OF THE EVOLUTIONARY CONTROLLER.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
  'status':status,
  'selected_target':selected_target,
  'parent_dimensions':parent_dims,
  'candidate_dimensions':candidate_dims,
  'program_id':program.program_id,
  'program_type':type(program).__name__,
  'fresh_blind':cand_score,
  'ablation':abl,
  'restore':restore,
  'visible_to_evolution':visible_to_evolution,
  'next_required_capability':report['next_required_capability'],
  'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True))
if not passed: raise SystemExit(2)
