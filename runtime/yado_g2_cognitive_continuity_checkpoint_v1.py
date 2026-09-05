from __future__ import annotations

from pathlib import Path
import copy,hashlib,json,tempfile,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_bounded_capability_router_v1 import BoundedCapabilityRouterLearnerV1
from yado_conjunctive_rule_inducer_v1 import ConjunctiveRuleInducerV1
from yado_g2_typed_recurrent_capability_graph_runtime_v1 import G2TypedRecurrentCapabilityGraphRuntimeV1
from yado_g2_unified_execution_fabric_v1 import CAP_BUD,CAP_THINK_V2
from yado_g2_unified_execution_fabric_v4 import G2UnifiedExecutionFabricV4,_digest_v4

OUT=REPO/'candidates/kernel-self-generated/g2-cognitive-continuity-checkpoint-v1.json'

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()

def desc(cap):
    d={'budget_limited':False,'quota_limited':False,'external_evidence_needed':False,'relation_needed':False,'disjunction_needed':False}
    if cap==CAP_BUD:d['budget_limited']=True
    elif cap==CAP_RES:d['external_evidence_needed']=True
    elif cap==CAP_REL:d['relation_needed']=True
    return d

def programs():
    route=[]
    for i in range(20):
        for cap in [CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES]:
            route.append({'input':desc(cap)|{'nonce':i%3},'expected':cap})
    router=BoundedCapabilityRouterLearnerV1.synthesize(route,route,CAP_CONJ,min_support=4)
    rows=[]
    for a in [False,True]:
      for b in [False,True]:
        for c in [False,True]:
          for _ in range(4):
            rows.append({'input':{'condition_a':a,'condition_b':b,'condition_c':c},'expected':'PASS' if a and b and c else 'HOLD'})
    scalar=ConjunctiveRuleInducerV1.synthesize('CONTINUITY_SCALAR','LOGIC',rows,min_support=2,max_rules=12)
    class Rel:
        def execute(self,x):return 'ALLOW' if x.get('allow') else 'DENY'
    return router,scalar,Rel()

core=UnifiedYADOCoreV1(REPO)
head_before=copy.deepcopy(core.head)
router,scalar,relation=programs()

def make_base():
    return G2TypedRecurrentCapabilityGraphRuntimeV1(
        core.architecture,router,scalar,relation,core.portfolio
    )

tmpdir=Path(tempfile.mkdtemp(prefix='yado-continuity-'))
checkpoint=tmpdir/'cognitive-continuity.json'
stream='RESTART-CONTINUITY'
stages=[
  {'stage_id':'FAILED_A','cost':1.0,'expected_gain':.5,'quota_remaining':1,'available':True,'latency':1.0},
  {'stage_id':'NEXT_B','cost':2.0,'expected_gain':.6,'quota_remaining':1,'available':True,'latency':1.0},
]

fabric=G2UnifiedExecutionFabricV4(make_base(),api_state={},checkpoint_path=checkpoint)

initial=fabric.execute_capability(CAP_BUD,{
  'kind':'budget','descriptor':desc(CAP_BUD),'stream_id':stream,
  'current_confidence':.2,'target_confidence':.7,'remaining_budget':4.0,'stages':stages,
  'goal_id':'GOAL-RESTART','deficit_id':'DEFICIT-RESTART'
})
recorded=fabric.record_outcome(stream,'FAILED_A',0.0)

budget_before=fabric.execute_capability(CAP_BUD,{
  'kind':'budget','descriptor':desc(CAP_BUD),'stream_id':stream,
  'current_confidence':.2,'target_confidence':.7,'remaining_budget':4.0,'stages':stages,
  'goal_id':'GOAL-RESTART','deficit_id':'DEFICIT-RESTART'
})
thinking_before=fabric.execute_capability(CAP_THINK_V2,{
  'operation':'auto_feedback_plan','stream_id':stream,
  'current_confidence':.2,'target_confidence':.7,'remaining_budget':4.0,
  'stages':stages,'completed':(),
  'goal_id':'GOAL-RESTART','deficit_id':'DEFICIT-RESTART'
})

state_before=G2UnifiedExecutionFabricV4.load_continuity_checkpoint(checkpoint)
pre_tick=int(state_before['cross_layer']['temporal_tick_id'])
pre_sequence=int(state_before['cross_layer']['recurrent_sequence'])
pre_stream_last=int(state_before['temporal_state']['streams'][stream]['last_tick'])
pre_episode_count=len(state_before['recurrent_memory_state']['episodes'])
pre_stage_outcomes=sum(1 for e in state_before['recurrent_memory_state']['episodes'] if e.get('kind')=='STAGE_OUTCOME')
pre_attempts=list(state_before['recurrent_memory_state']['stream_attempts'].get(stream,[]))
checkpoint_digest=state_before['checkpoint_digest']

del fabric

fabric2=G2UnifiedExecutionFabricV4(make_base(),api_state={},checkpoint_path=checkpoint)
restored=fabric2.continuity_snapshot()
restore_memory=fabric2.memory_snapshot()
restored_tick=fabric2.clock.tick_id
restored_sequence=fabric2.base.sequence
restored_attempts=list(fabric2.base.stream_attempts.get(stream,[]))
restored_episode_count=len(fabric2.base.episodes)
restored_stage_outcomes=sum(1 for e in fabric2.base.episodes if e.get('kind')=='STAGE_OUTCOME')

thinking_after=fabric2.execute_capability(CAP_THINK_V2,{
  'operation':'auto_feedback_plan','stream_id':stream,
  'current_confidence':.2,'target_confidence':.7,'remaining_budget':4.0,
  'stages':stages,'completed':(),
  'goal_id':'GOAL-RESTART','deficit_id':'DEFICIT-RESTART'
})
budget_after=fabric2.execute_capability(CAP_BUD,{
  'kind':'budget','descriptor':desc(CAP_BUD),'stream_id':stream,
  'current_confidence':.2,'target_confidence':.7,'remaining_budget':4.0,'stages':stages,
  'goal_id':'GOAL-RESTART','deficit_id':'DEFICIT-RESTART'
})

state_after=G2UnifiedExecutionFabricV4.load_continuity_checkpoint(checkpoint)

# Fail closed if recurrent memory is tampered while the outer checkpoint digest is recomputed.
tampered=copy.deepcopy(state_before)
tampered['recurrent_memory_state']['stream_attempts'][stream]=[]
tampered['checkpoint_digest']=_digest_v4({k:v for k,v in tampered.items() if k!='checkpoint_digest'})
tamper_rejected=False
try:
    G2UnifiedExecutionFabricV4(make_base(),api_state={},continuity_state=tampered)
except ValueError:
    tamper_rejected=True

# Fail closed if cross-layer temporal transition identity is forged with internally recomputed section digests.
cross_tampered=copy.deepcopy(state_before)
changed=False
for e in reversed(cross_tampered['recurrent_memory_state']['episodes']):
    if e.get('kind')=='TEMPORAL_TRANSITION':
        e['tick_digest']='0'*64
        e['episode_digest']=_digest_v4({k:v for k,v in e.items() if k!='episode_digest'})
        changed=True
        break
if changed:
    rm=cross_tampered['recurrent_memory_state']
    rm['memory_state_digest']=_digest_v4({k:v for k,v in rm.items() if k!='memory_state_digest'})
    cross_tampered['checkpoint_digest']=_digest_v4({k:v for k,v in cross_tampered.items() if k!='checkpoint_digest'})
cross_layer_tamper_rejected=False
try:
    G2UnifiedExecutionFabricV4(make_base(),api_state={},continuity_state=cross_tampered)
except ValueError:
    cross_layer_tamper_rejected=True

checks={
  'initial_failed_stage_was_selected':initial.get('result')=='FAILED_A',
  'failed_stage_outcome_recorded':recorded.get('stage_id')=='FAILED_A' and float(recorded.get('observed_gain'))==0.0,
  'auto_checkpoint_file_created':checkpoint.exists(),
  'checkpoint_contains_temporal_and_recurrent_state':isinstance(state_before.get('temporal_state'),dict) and isinstance(state_before.get('recurrent_memory_state'),dict),
  'checkpoint_has_atomic_digest':bool(checkpoint_digest),
  'failed_stage_attempt_persisted_before_restart':'FAILED_A' in pre_attempts,
  'stage_outcome_persisted_before_restart':pre_stage_outcomes>=1,
  'budget_decision_before_restart_avoids_failed_stage':budget_before.get('result')=='NEXT_B',
  'thinking_before_restart_uses_memory':thinking_before.get('meta',{}).get('memory_feedback_used') is True,
  'thinking_before_restart_avoids_failed_stage':thinking_before.get('result',{}).get('action')=='NEXT_B',
  'restart_restores_exact_tick':restored_tick==pre_tick,
  'restart_restores_exact_recurrent_sequence':restored_sequence==pre_sequence,
  'restart_restores_episode_count':restored_episode_count==pre_episode_count,
  'restart_restores_stage_outcome_count':restored_stage_outcomes==pre_stage_outcomes,
  'restart_restores_failed_stage_attempt':restored_attempts==pre_attempts and 'FAILED_A' in restored_attempts,
  'restart_binds_original_checkpoint_digest':restored.get('restored_checkpoint_digest')==checkpoint_digest,
  'decision_after_restart_matches_before':thinking_after.get('result',{}).get('action')==thinking_before.get('result',{}).get('action')=='NEXT_B',
  'memory_feedback_after_restart':thinking_after.get('meta',{}).get('memory_feedback_used') is True,
  'budget_after_restart_does_not_retry_failed_stage':budget_after.get('result')=='NEXT_B',
  'first_post_restart_tick_continues_monotonically':thinking_after.get('temporal',{}).get('tick_id')==pre_tick+1,
  'first_post_restart_predecessor_preserved':thinking_after.get('temporal',{}).get('predecessor_tick')==pre_stream_last,
  'auto_checkpoint_advances_after_restart':int(state_after['cross_layer']['temporal_tick_id'])>pre_tick and int(state_after['cross_layer']['recurrent_sequence'])>pre_sequence,
  'tampered_recurrent_memory_rejected':tamper_rejected,
  'cross_layer_forgery_rejected':cross_layer_tamper_rejected,
  'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
  'canonical_mutation_false':True,
  'automatic_canonical_promotion_false':True,
}
status='PASS_SHADOW_G2_COGNITIVE_CONTINUITY_CHECKPOINT_V1' if all(checks.values()) else 'WITHHOLD_G2_COGNITIVE_CONTINUITY_CHECKPOINT_V1'
report={
  'schema':'yado.g2.cognitive_continuity_checkpoint.v1',
  'status':status,
  'component':G2UnifiedExecutionFabricV4.component(),
  'checkpoint_projection':{
    'checkpoint_digest':checkpoint_digest,
    'tick_before_restart':pre_tick,
    'recurrent_sequence_before_restart':pre_sequence,
    'episode_count_before_restart':pre_episode_count,
    'stage_outcome_count_before_restart':pre_stage_outcomes,
    'attempted_stages_before_restart':pre_attempts,
    'restored_tick':restored_tick,
    'restored_recurrent_sequence':restored_sequence,
    'restored_attempted_stages':restored_attempts,
    'post_restart_tick':thinking_after.get('temporal',{}).get('tick_id'),
  },
  'decision_projection':{
    'initial':initial.get('result'),
    'failed_stage':'FAILED_A',
    'budget_before_restart':budget_before.get('result'),
    'thinking_before_restart':thinking_before.get('result',{}).get('action'),
    'thinking_after_restart':thinking_after.get('result',{}).get('action'),
    'budget_after_restart':budget_after.get('result'),
  },
  'checks':checks,
  'canonical_mutation':False,
  'promotion_applied':False,
  'next_required_capability':'COGNITIVE_CONTINUITY_CANONICAL_ADMISSION_V1' if all(checks.values()) else 'COGNITIVE_CONTINUITY_REPAIR_V2',
  'semantic_boundary':'SHADOW RESTART TEST OF ONE ATOMIC TEMPORAL+RECURRENT CHECKPOINT. THE ORIGINAL RUNTIME OBJECT IS DESTROYED AND A FRESH RUNTIME RESTORES THE CHECKPOINT. PASS REQUIRES STAGE OUTCOME, ATTEMPT HISTORY, TEMPORAL PREDECESSOR AND NEXT DECISION TO SURVIVE RESTART, PLUS FAIL-CLOSED DIGEST AND CROSS-LAYER TAMPER CHECKS.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
  'status':status,
  'checkpoint':report['checkpoint_projection'],
  'decisions':report['decision_projection'],
  'checks':checks,
  'next_required_capability':report['next_required_capability'],
  'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True,default=str))
if not all(checks.values()):raise SystemExit(2)
