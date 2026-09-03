from __future__ import annotations
from pathlib import Path
import hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_bounded_capability_router_v1 import BoundedCapabilityRouterLearnerV1
from yado_conjunctive_rule_inducer_v1 import ConjunctiveRuleInducerV1
from yado_g2_unified_execution_fabric_v1 import CAP_LOGIC_V2

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'
CLOCK='RUNTIME-G2-COGNITIVE-TEMPORAL-KERNEL-V1'
FABRIC='RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V3'

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
    for i in range(24):
        for cap in [CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES]:
            route.append({'input':desc(cap)|{'nonce':i%3},'expected':cap})
    router=BoundedCapabilityRouterLearnerV1.synthesize(route,route,CAP_CONJ,min_support=4)
    rows=[]
    for a in [False,True]:
      for b in [False,True]:
        for c in [False,True]:
          for _ in range(4):rows.append({'input':{'condition_a':a,'condition_b':b,'condition_c':c},'expected':'PASS' if a and b and c else 'HOLD'})
    scalar=ConjunctiveRuleInducerV1.synthesize('POST_TEMPORAL_SCALAR','LOGIC',rows,min_support=2,max_rules=12)
    class Rel:
        def execute(self,x):return 'ALLOW' if x.get('allow') else 'DENY'
    return router,scalar,Rel()

core=UnifiedYADOCoreV1(REPO)
router,scalar,relation=programs()
fabric=core.instantiate_execution_fabric(router,scalar,relation,api_state={})

logic_rows=[]
for a in [False,True]:
  for b in [False,True]:
    for _ in range(5):logic_rows.append({'input':{'a':a,'b':b},'expected':'EVEN' if a==b else 'ODD'})
model=core.learn_symmetric_logic(logic_rows)

first=fabric.execute_capability(CAP_LOGIC_V2,{
  'operation':'predict_symmetric','model':model,'payload':{'a':True,'b':False},
  'stream_id':'POST-TIME','goal_id':'POST-GOAL','progress_token':{'state':1}
})
second=fabric.execute_capability(CAP_LOGIC_V2,{
  'operation':'predict_symmetric','model':model,'payload':{'a':False,'b':False},
  'stream_id':'POST-TIME','goal_id':'POST-GOAL','progress_token':{'state':2}
})

# Produce a real temporal stall and use it as a bounded trigger for shadow evolution.
for i in range(21):
    stalled=fabric.execute_capability(CAP_LOGIC_V2,{
      'operation':'predict_symmetric','model':model,'payload':{'a':True,'b':False},
      'stream_id':'POST-STALL','goal_id':'POST-STALL-GOAL','deficit_id':'POST-STALL-DEFICIT',
      'progress_token':{'deficit':'POST-STALL-DEFICIT','state':'UNCHANGED'}
    })
signal=fabric.temporal_evolution_signal('POST-STALL')
evolution=core.temporal_evolution_on_stall(fabric,'POST-STALL')

# Explicit checkpoint/reconstruction through the canonical core entry point.
state=core.export_cognitive_temporal_state(fabric)
last_tick=state['tick_id']
router2,scalar2,relation2=programs()
fabric2=core.instantiate_execution_fabric(router2,scalar2,relation2,api_state={},temporal_state=state)
continued=fabric2.execute_capability(CAP_LOGIC_V2,{
  'operation':'predict_symmetric','model':model,'payload':{'a':True,'b':True},
  'stream_id':'POST-TIME','goal_id':'POST-GOAL','progress_token':{'state':3}
})

active=set(core.head.get('active_capabilities',[]))
child_ids={x['gene_id'] for x in evolution.get('evolution',{}).get('child',{}).get('chromosomes',{}).values()}
checks={
 'canonical_fabric_v3_active':FABRIC in active and core.manifest.get('execution_fabric_v3',{}).get('status')=='CANONICAL_ACTIVE',
 'fabric_v2_not_active':'RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V2' not in active,
 'clock_embedded_not_separate':CLOCK not in active and core.manifest.get('cognitive_temporal_kernel_v1',{}).get('status')=='CANONICAL_EMBEDDED',
 'monotonic_ticks':second['temporal']['tick_id']>first['temporal']['tick_id'],
 'same_stream_predecessor':second['temporal']['predecessor_tick']==first['temporal']['tick_id'],
 'stall_reaches_threshold':signal.get('no_progress_ticks')==20 and signal.get('mechanism_change_required') is True,
 'stall_recommends_evolution':signal.get('recommended_action')=='EVOLVE_MECHANISM',
 'temporal_stall_triggers_shadow_evolution':evolution.get('status')=='SHADOW_EVOLUTION_TRIGGERED' and evolution.get('evolution',{}).get('selection')=='CHILD',
 'temporal_evolution_never_auto_promotes':evolution.get('promotion_authorized') is False and evolution.get('evolution',{}).get('promotion_authorized') is False,
 'shadow_child_genes_not_active':not (child_ids & active),
 'checkpoint_digest_present':bool(state.get('state_digest')),
 'checkpoint_restore_continues_tick':continued['temporal']['tick_id']==last_tick+1,
 'checkpoint_restore_preserves_predecessor':continued['temporal']['predecessor_tick']==state['streams']['POST-TIME']['last_tick'],
 'recurrent_temporal_memory_live':fabric.memory_snapshot().get('temporal_transition_count',0)>0 and fabric.memory_snapshot().get('temporal_stall_signal_count',0)>=1,
 'frontier_preserved':core.head.get('current_frontier')=='KERNEL_G2_RAW_REPRESENTATION_V5_CANONICAL_ADMISSION_V1',
 'g3_not_started':core.head.get('g3_genesis_performed') is False,
}
status='PASS_G2_COGNITIVE_TEMPORAL_KERNEL_POST_ADMISSION_V1' if all(checks.values()) else 'WITHHOLD_G2_COGNITIVE_TEMPORAL_KERNEL_POST_ADMISSION_V1'
report={
 'schema':'yado.g2.cognitive_temporal_kernel.post_admission.v1',
 'status':status,'checks':checks,
 'temporal_signal':signal,
 'evolution_projection':{
   'status':evolution.get('status'),
   'selection':evolution.get('evolution',{}).get('selection'),
   'child_genome_digest':evolution.get('evolution',{}).get('child',{}).get('genome_digest'),
   'promotion_authorized':evolution.get('promotion_authorized'),
 },
 'checkpoint_projection':{
   'tick_before':last_tick,'tick_after':continued['temporal']['tick_id'],
   'state_digest':state.get('state_digest'),
 },
 'active_capability_count':len(active),
 'canonical_mutation':False,'architecture_mutation':False,
 'generation_transition':False,'g3_genesis_performed':False,
 'semantic_boundary':'POST-ADMISSION VERIFICATION OF EMBEDDED LOGICAL TIME AND TEMPORAL-STALL-TO-SHADOW-EVOLUTION BRIDGE. TEMPORAL CONTINUITY DOES NOT BY ITSELF CLAIM CONSCIOUSNESS.'
}
report['receipt_sha256']=digest(report)
out=REPO/'audits/yado-g2-cognitive-temporal-kernel-post-admission-v1.json'
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2,sort_keys=True,default=str))
if not all(checks.values()):raise SystemExit(2)
