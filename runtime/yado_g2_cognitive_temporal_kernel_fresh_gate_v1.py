from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_bounded_capability_router_v1 import BoundedCapabilityRouterLearnerV1
from yado_conjunctive_rule_inducer_v1 import ConjunctiveRuleInducerV1
from yado_g2_typed_recurrent_capability_graph_runtime_v1 import G2TypedRecurrentCapabilityGraphRuntimeV1
from yado_g2_unified_execution_fabric_v1 import CAP_LOGIC_V2,CAP_THINK_V2,CAP_INTEL_V3
from yado_g2_unified_execution_fabric_v2 import CAP_API_EXEC_V1
from yado_g2_unified_execution_fabric_v3 import G2UnifiedExecutionFabricV3
from yado_g2_openapi_contract_capability_v1 import G2OpenAPIContractCapabilityV1

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()

def desc(cap):
    d={'budget_limited':False,'quota_limited':False,'external_evidence_needed':False,'relation_needed':False,'disjunction_needed':False}
    if cap==CAP_BUD:d['budget_limited']=True
    elif cap==CAP_RES:d['external_evidence_needed']=True
    elif cap==CAP_REL:d['relation_needed']=True
    return d

def make_fabric(temporal_state=None):
    core=UnifiedYADOCoreV1(REPO)
    route=[]
    for i in range(24):
        for cap in [CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES]:
            route.append({'input':desc(cap)|{'nonce':i%3},'expected':cap})
    router=BoundedCapabilityRouterLearnerV1.synthesize(route,route,CAP_CONJ,min_support=4)
    rows=[]
    for a in [False,True]:
      for b in [False,True]:
        for c in [False,True]:
          for _ in range(4):rows.append({'input':{'condition_a':a,'condition_b':b,'condition_c':c},'expected':'PASS' if a and b and c else 'HOLD'})
    scalar=ConjunctiveRuleInducerV1.synthesize('TEMPORAL_SCALAR','LOGIC',rows,min_support=2,max_rules=12)
    class Rel:
        def execute(self,x):return 'ALLOW' if x.get('allow') else 'DENY'
    base=G2TypedRecurrentCapabilityGraphRuntimeV1(core.architecture,router,scalar,Rel(),core.portfolio)
    return core,G2UnifiedExecutionFabricV3(base,temporal_state=temporal_state)

core,fabric=make_fabric()
checks={}
evidence={}

# 1) Monotonic global ticks and episode/predecessor continuity.
logic_rows=[]
for a in [False,True]:
  for b in [False,True]:
    for _ in range(5):logic_rows.append({'input':{'a':a,'b':b},'expected':'EVEN' if a==b else 'ODD'})
model=core.learn_symmetric_logic(logic_rows)
r1=fabric.execute_capability(CAP_LOGIC_V2,{
  'operation':'predict_symmetric','model':model,'payload':{'a':True,'b':False},
  'stream_id':'TIME-A','goal_id':'GOAL-A','memory_id':'MEM-A','prediction':'ODD',
  'progress_token':{'deficit':'A','state':1}
})
r2=fabric.execute_capability(CAP_LOGIC_V2,{
  'operation':'predict_symmetric','model':model,'payload':{'a':False,'b':False},
  'stream_id':'TIME-A','goal_id':'GOAL-A','memory_id':'MEM-A','prediction':'EVEN',
  'progress_token':{'deficit':'A','state':2}
})
r3=fabric.execute_capability(CAP_LOGIC_V2,{
  'operation':'predict_symmetric','model':model,'payload':{'a':True,'b':True},
  'stream_id':'TIME-B','goal_id':'GOAL-B','progress_token':{'deficit':'B','state':1}
})
checks['global_ticks_monotonic']=r1['temporal']['tick_id']<r2['temporal']['tick_id']<r3['temporal']['tick_id']
checks['episode_time_per_stream']=r1['temporal']['episode_tick']==1 and r2['temporal']['episode_tick']==2 and r3['temporal']['episode_tick']==1
checks['predecessor_same_stream']=r2['temporal']['predecessor_tick']==r1['temporal']['tick_id'] and r1['temporal']['predecessor_tick'] is None
checks['different_stream_no_false_predecessor']=r3['temporal']['predecessor_tick'] is None
checks['predictions_and_results_bound']=all(
    x.get('status')=='CLOSED' and x.get('prediction') is not None and x.get('observed_result_digest')
    for x in fabric.temporal_causal_chain('TIME-A')
)
evidence['time_a_chain']=fabric.temporal_causal_chain('TIME-A')

# 2) Entity age/tick_last_used.
age0=fabric.temporal_entity_age('GOAL-A')
for i in range(3):
    fabric.execute_capability(CAP_LOGIC_V2,{
      'operation':'predict_symmetric','model':model,'payload':{'a':bool(i%2),'b':False},
      'stream_id':'AGE-NOISE-'+str(i),'progress_token':{'n':i}
    })
age1=fabric.temporal_entity_age('GOAL-A')
fabric.execute_capability(CAP_LOGIC_V2,{
  'operation':'predict_symmetric','model':model,'payload':{'a':True,'b':False},
  'stream_id':'TIME-A','goal_id':'GOAL-A','progress_token':{'deficit':'A','state':3}
})
age2=fabric.temporal_entity_age('GOAL-A')
checks['entity_age_advances']=age1['age_ticks']>age0['age_ticks']
checks['entity_last_used_updates']=age2['tick_last_used']>age1['tick_last_used'] and age2['use_count']>age1['use_count']
evidence['goal_age']={'initial':age0,'after_idle':age1,'after_reuse':age2}

# 3) Stage observation gets its own tick and feeds Thinking.
stages=[
 {'stage_id':'OBS','cost':1,'expected_gain':.3},
 {'stage_id':'DEEP','cost':3,'expected_gain':.65,'requires':['OBS']},
]
p0=fabric.execute_capability(CAP_THINK_V2,{
  'operation':'plan','current_confidence':.2,'target_confidence':.8,'remaining_budget':5,
  'stages':stages,'stream_id':'TIME-T','goal_id':'GOAL-T'
})
obs=fabric.record_outcome('TIME-T','OBS',.25)
p1=fabric.execute_capability(CAP_THINK_V2,{
  'operation':'auto_feedback_plan','current_confidence':.2,'target_confidence':.8,'remaining_budget':5,
  'stages':stages,'completed':['OBS'],'stream_id':'TIME-T','goal_id':'GOAL-T'
})
checks['observation_has_logical_tick']=obs.get('temporal',{}).get('tick_id')>p0['temporal']['tick_id']
checks['thinking_after_observation_is_later']=p1['temporal']['tick_id']>obs['temporal']['tick_id']
checks['thinking_memory_feedback_survives_temporal_layer']=p1.get('meta',{}).get('memory_feedback_used') is True
evidence['thinking_chain']=fabric.temporal_causal_chain('TIME-T')

# 4) Nested Intelligence -> Logic creates parent tick relationship.
train=[]
for i in range(16):
    train += [
      {'input':{'kind':'logic','need_plan':False,'noise':i%2},'expected':CAP_LOGIC_V2},
      {'input':{'kind':'plan','need_plan':True,'noise':i%2},'expected':CAP_THINK_V2},
    ]
imodel=core.fit_compositional_capability_router(train,CAP_LOGIC_V2)
intel=fabric.execute_capability(CAP_INTEL_V3,{
  'operation':'route_execute','model':imodel,'payload':{'kind':'logic','need_plan':False,'noise':True},
  'stream_id':'TIME-I','goal_id':'GOAL-I',
  'capability_tasks':{
    CAP_LOGIC_V2:{'operation':'predict_symmetric','model':model,'payload':{'a':True,'b':False}}
  }
})
ichain=fabric.temporal_causal_chain('TIME-I')
outer=next(x for x in ichain if x['action']==CAP_INTEL_V3)
inner=next(x for x in ichain if x['action']==CAP_LOGIC_V2)
checks['intelligence_nested_tick_parentage']=inner.get('parent_tick')==outer['tick_id']
checks['intelligence_subcall_predecessor']=inner.get('predecessor_tick')==outer['tick_id']
checks['intelligence_route_execute_pass']=intel.get('result',{}).get('status')=='PASS'
evidence['intelligence_chain']=ichain

# 5) Real external API action gets a tick and wall time while causal ordering stays logical.
api_state={'policy_tree':{'label':'ALLOW'},'contract_registry':{
 'GET_REPO':{'source_id':'TEMPORAL_LIVE','source_sha':'temporal-v1','method':'GET','path':'/repos/v37025337-pixel/EVA','required':[],'redirect_semantic':False}
}}
plan=G2OpenAPIContractCapabilityV1(api_state).compile_plan('GET_REPO')
api=fabric.execute_capability(CAP_API_EXEC_V1,{
  'plan':plan,'base_url':'https://api.github.com','allowed_hosts':['api.github.com'],
  'max_bytes':262144,'timeout':10,'stream_id':'TIME-API','goal_id':'GOAL-API',
  'prediction':{'status':200},'progress_token':{'external_evidence':'repo-metadata'}
})
apichain=fabric.temporal_causal_chain('TIME-API')
arec=apichain[-1]
checks['api_action_temporally_bound']=api.get('result',{}).get('status')==200 and arec['action']==CAP_API_EXEC_V1
checks['wall_time_recorded']=bool(arec.get('wall_time_started')) and bool(arec.get('wall_time_finished'))
checks['wall_time_not_causal_order_source']=G2UnifiedExecutionFabricV3.component()['temporal_kernel']['wall_time_not_used_for_causal_ordering'] is True
evidence['api_tick']={k:v for k,v in arec.items() if k!='observed_result'}

# 6) 20 no-progress repeats cause a mechanism-change signal.
stall_rows=[]
for i in range(21):
    x=fabric.execute_capability(CAP_LOGIC_V2,{
      'operation':'predict_symmetric','model':model,'payload':{'a':True,'b':False},
      'stream_id':'STALL-1','goal_id':'GOAL-STALL','deficit_id':'DEFICIT-STALLED',
      'progress_token':{'deficit':'DEFICIT-STALLED','state':'UNCHANGED'}
    })
    stall_rows.append(x['temporal'])
stall_state=fabric.temporal_stream_state('STALL-1')
snap=fabric.memory_snapshot()
checks['no_progress_ticks_reach_20']=stall_state['no_progress_ticks']==20
checks['mechanism_change_required_at_threshold']=stall_state['mechanism_change_required'] is True and stall_rows[-1]['mechanism_change_required'] is True
checks['stall_signal_written_to_recurrent_memory']=snap['temporal_stall_signal_count']>=1 and any(
    e.get('kind')=='TEMPORAL_STALL_SIGNAL' and e.get('stream_id')=='STALL-1' and e.get('mechanism_change_required') is True
    for e in fabric.base.episodes
)
evo_signal=fabric.temporal_evolution_signal('STALL-1')
checks['stall_signal_recommends_evolution']=evo_signal.get('recommended_action')=='EVOLVE_MECHANISM' and evo_signal.get('mechanism_change_required') is True
evidence['stall_state']=stall_state
evidence['evolution_signal']=evo_signal

# 7) Progress resets no-progress counter.
progressed=fabric.execute_capability(CAP_LOGIC_V2,{
  'operation':'predict_symmetric','model':model,'payload':{'a':False,'b':False},
  'stream_id':'STALL-1','goal_id':'GOAL-STALL','deficit_id':'DEFICIT-STALLED',
  'progress_token':{'deficit':'DEFICIT-STALLED','state':'CHANGED'}
})
checks['progress_resets_no_progress']=progressed['temporal']['no_progress_ticks']==0 and fabric.temporal_stream_state('STALL-1')['mechanism_change_required'] is False

# 8) Temporal state survives explicit persistence/reconstruction and continues monotonic time.
state=fabric.export_temporal_state()
last_tick=state['tick_id']
core2,fabric2=make_fabric(temporal_state=state)
after_restore=fabric2.execute_capability(CAP_LOGIC_V2,{
  'operation':'predict_symmetric','model':model,'payload':{'a':True,'b':True},
  'stream_id':'TIME-A','goal_id':'GOAL-A','progress_token':{'deficit':'A','state':4}
})
checks['temporal_state_digest_bound']=bool(state.get('state_digest'))
checks['restore_continues_global_tick']=after_restore['temporal']['tick_id']==last_tick+1
checks['restore_preserves_stream_predecessor']=after_restore['temporal']['predecessor_tick']==state['streams']['TIME-A']['last_tick']
checks['restore_preserves_entity_age']=fabric2.temporal_entity_age('GOAL-A')['tick_created']==state['entities']['GOAL-A']['tick_created']
evidence['restore']={'last_tick_before':last_tick,'after':after_restore['temporal'],'goal_age':fabric2.temporal_entity_age('GOAL-A')}

# 9) Recurrent memory carries temporal transition metadata.
transitions=[e for e in fabric.base.episodes if e.get('kind')=='TEMPORAL_TRANSITION']
checks['temporal_transitions_in_recurrent_memory']=len(transitions)>0 and all(
    'tick_id' in e and 'predecessor_tick' in e and 'no_progress_ticks' in e for e in transitions[-10:]
)
checks['clock_has_no_open_ticks']=fabric.temporal_snapshot()['open_tick_count']==0

status='PASS_SHADOW_G2_COGNITIVE_TEMPORAL_KERNEL_V1' if all(checks.values()) else 'WITHHOLD_G2_COGNITIVE_TEMPORAL_KERNEL_V1'
report={
 'schema':'yado.g2.cognitive_temporal_kernel.fresh_gate.v1',
 'status':status,'checks':checks,'evidence':evidence,
 'clock_component':fabric.clock.component(),
 'fabric_component':G2UnifiedExecutionFabricV3.component(),
 'memory_snapshot':snap,
 'formal_generation':core.head.get('generation_id'),
 'frontier':core.head.get('current_frontier'),
 'canonical_mutation':False,'architecture_mutation':False,
 'generation_transition':False,'g3_genesis_performed':False,
 'semantic_boundary':'FRESH SHADOW TEST OF LOGICAL COGNITIVE TIME. TICKS ESTABLISH ORDER/CAUSAL CONTINUITY BUT DO NOT BY THEMSELVES CLAIM CONSCIOUSNESS OR GENERAL INTELLIGENCE.'
}
report['receipt_sha256']=digest(report)
out=REPO/'candidates/kernel-self-generated/g2-cognitive-temporal-kernel-v1.json'
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
  'status':status,'checks':checks,
  'tick_id':fabric.temporal_snapshot()['tick_id'],
  'stall_state':stall_state,
  'temporal_transition_count':snap['temporal_transition_count'],
  'temporal_stall_signal_count':snap['temporal_stall_signal_count'],
  'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True))
if not all(checks.values()):raise SystemExit(2)
