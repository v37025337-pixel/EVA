from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,sys
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_unified_core_v1 import UnifiedYADOCoreV1

PARENT=REPO/'candidates/kernel-self-generated/g2-goal-autonomous-source-creation-readiness-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-goal-autonomous-source-creation-readiness-v2.json'
EXP=REPO/'experience/yado-goal-autonomous-source-creation-readiness-v2.json'

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
p=load(PARENT)
if p.get('status')!='WITHHOLD_G2_GOAL_AUTONOMOUS_SOURCE_CREATION_READINESS_V1':raise RuntimeError('V1_WITHHOLD_REQUIRED')
core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)

db=ROOT/'yado_goal_autonomy_readiness_v2.sqlite'
if db.exists():db.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(db))
try:
 ex=k.executive
 g=ex.create_goal(
   objective='Create task-conditioned source and autonomously continue until validated.',
   required_capabilities={'TASK_CONDITIONED_NATIVE_SOURCE_EMISSION':1.0},
   success_criteria={'new_source':True,'compile':True,'fresh':True,'ablation':True,'regression':True}
 )
 before={'goal_status':ex.goals[g.goal_id].status,'deficit_count':len(ex.deficits),'candidate_count':len(ex.candidates),'capability_score':getattr(ex.capabilities.get('TASK_CONDITIONED_NATIVE_SOURCE_EMISSION'),'score',None)}
 first=ex.run_cycle(g.goal_id)
 mid={'goal_status':ex.goals[g.goal_id].status,'deficit_count':len(ex.deficits),'candidate_count':len(ex.candidates),'capability_score':getattr(ex.capabilities.get('TASK_CONDITIONED_NATIVE_SOURCE_EMISSION'),'score',None)}
 second=ex.run_cycle(g.goal_id)
 after={'goal_status':ex.goals[g.goal_id].status,'deficit_count':len(ex.deficits),'candidate_count':len(ex.candidates),'capability_score':getattr(ex.capabilities.get('TASK_CONDITIONED_NATIVE_SOURCE_EMISSION'),'score',None)}
finally:
 try:k.close()
 except Exception:pass

first_candidate=(first.get('candidate') or {}).get('candidate_id')
second_candidate=(second.get('candidate') or {}).get('candidate_id')
self_progress=(
 after['capability_score'] is not None and after['capability_score']>=1.0
 and after['goal_status']!='OPEN'
)
duplicate_candidate_without_progress=(
 first.get('state')=='CANDIDATE_READY' and second.get('state')=='CANDIDATE_READY'
 and first_candidate and second_candidate and first_candidate!=second_candidate
 and before['capability_score']==mid['capability_score']==after['capability_score']
 and after['goal_status']=='OPEN'
)
checks={
 'v1_task_conditioning_failure_preserved':p.get('checks',{}).get('goal_conditioning_visible_for_both') is False and p.get('same_source_for_different_goals') is True,
 'run_cycle_method_exists':True,
 'run_cycle_returns_external_experiment_handoff':first.get('next_action')=='run_bounded_experiment_then_submit_metrics',
 'second_cycle_without_metrics_does_not_progress':duplicate_candidate_without_progress,
 'native_self_continuing_goal_loop':self_progress,
 'host_submitted_experiment_metrics':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
}
missing=['TASK_CONDITIONED_NATIVE_SOURCE_EMISSION_V1']
if not checks['native_self_continuing_goal_loop']:missing.append('NATIVE_PERSISTENT_GOAL_LOOP_CONTROLLER_V1')
status='PASS_SHADOW_G2_GOAL_AUTONOMOUS_SOURCE_CREATION_READINESS_V2' if checks['v1_task_conditioning_failure_preserved'] is False and checks['native_self_continuing_goal_loop'] else 'WITHHOLD_G2_GOAL_AUTONOMOUS_SOURCE_CREATION_READINESS_V2'
exp={'schema':'yado.g2.goal_autonomous_source_creation_readiness.experience.v2','status':'PASS' if status.startswith('PASS') else 'WITHHOLD',
 'before':before,'first_cycle':first,'mid':mid,'second_cycle':second,'after':after,
 'checks':checks,'missing_capabilities':missing,'canonical_mutation':False,
 'semantic_boundary':'V2 CORRECTS THE V1 LOOP DETECTOR. run_cycle EXISTS, BUT ONE CALL STOPS AT CANDIDATE_READY AND EXPLICITLY HANDS OFF TO AN EXTERNAL BOUNDED EXPERIMENT/METRICS SUBMISSION. A SECOND CALL WITHOUT THAT EXTERNAL STEP CREATES ANOTHER CANDIDATE AND DOES NOT ADVANCE THE GOAL.'}
exp['experience_digest']=digest(exp);EXP.parent.mkdir(parents=True,exist_ok=True);EXP.write_text(json.dumps(exp,indent=2,sort_keys=True,default=str)+'\n')
report={'schema':'yado.g2.goal_autonomous_source_creation_readiness.v2','status':status,
 'v1_receipt':p.get('receipt_sha256'),'before':before,'first_cycle':first,'mid':mid,'second_cycle':second,'after':after,
 'checks':checks,'missing_capabilities':missing,'canonical_mutation':False,
 'next_required_capability':'+'.join(missing),'semantic_boundary':exp['semantic_boundary']}
report['receipt_sha256']=digest(report);OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps({'status':status,'first_cycle':first,'second_cycle':second,'before':before,'after':after,'checks':checks,'missing_capabilities':missing,'receipt_sha256':report['receipt_sha256']},indent=2,sort_keys=True,default=str))
if not status.startswith('PASS'):raise SystemExit(2)
