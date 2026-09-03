from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,random,sys
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;PKG=ROOT/'yado_rc8_v36';sys.path[:0]=[str(ROOT),str(PKG)]
from yado_g2_integrated_execution_fabric_v1 import G2IntegratedExecutionFabricV1,CAP_LOGIC_V2,CAP_THINK_V2,CAP_INTEL_V3
from yado_bounded_capability_set_coordinator_v1 import BoundedCapabilitySetCoordinatorV1
from yado_bounded_capability_router_v1 import BoundedCapabilityRouterLearnerV1
from yado_conjunctive_rule_inducer_v1 import ConjunctiveRuleInducerV1

def load(p):return json.loads(p.read_text())
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
class Rel:
 def execute(self,x):return 'ALLOW' if x.get('allow') else 'DENY'

def desc(cap):return {'capability':cap,'noise':0}
cases=[]
for i in range(36):
 for cap in [CAP_LOGIC_V2,CAP_THINK_V2,CAP_INTEL_V3]:cases.append({'input':{'capability':cap,'noise':i%3},'expected':cap})
router=BoundedCapabilityRouterLearnerV1.synthesize(cases,cases,CAP_LOGIC_V2,min_support=5)
logic_rows=[]
for a in [False,True]:
 for b in [False,True]:
  for _ in range(5):logic_rows.append({'input':{'a':a,'b':b},'expected':'EVEN' if a==b else 'ODD'})
scalar=ConjunctiveRuleInducerV1.synthesize('FABRIC_SCALAR','LOGIC',logic_rows,min_support=2)
fabric=G2IntegratedExecutionFabricV1(load(REPO/'canonical/yado-g2-architecture-v1.json'),router,scalar,Rel(),load(REPO/'resources/yado-unified-external-resource-portfolio-v1.json'))

logic_task={'kind':'logic_v2','descriptor':desc(CAP_LOGIC_V2),'stream_id':'FRESH-L','train_rows':logic_rows,'payload':{'a':True,'b':False}}
logic=fabric.run(logic_task)
plan_task={'kind':'thinking_v2','descriptor':desc(CAP_THINK_V2),'stream_id':'FRESH-P','current_confidence':0.2,'target_confidence':0.8,'remaining_budget':5.0,'stages':[{'stage_id':'OBSERVE','cost':1,'expected_gain':0.4},{'stage_id':'DEEP','cost':3,'expected_gain':0.7,'requires':['OBSERVE']}]}
plan0=fabric.run(plan_task)
fabric.observe_stage_outcome('FRESH-P','OBSERVE',-0.15)
plan1=copy.deepcopy(plan_task);plan1['completed_stage_id']='OBSERVE';plan1['completed']=['OBSERVE'];plan1=fabric.run(plan1)
abl=G2IntegratedExecutionFabricV1(load(REPO/'canonical/yado-g2-architecture-v1.json'),router,scalar,Rel(),load(REPO/'resources/yado-unified-external-resource-portfolio-v1.json'))
plan_abl=copy.deepcopy(plan_task);plan_abl['completed_stage_id']='OBSERVE';plan_abl['completed']=['OBSERVE'];plan_abl=abl.run(plan_abl,ablated_memory=True)
intel_cases=[]
for i in range(12):
 intel_cases += [{'input':{'kind':'logic','urgent':bool(i%2)},'expected':CAP_LOGIC_V2},{'input':{'kind':'plan','urgent':bool(i%2)},'expected':CAP_THINK_V2}]
intel_task={'kind':'intelligence_v3','descriptor':desc(CAP_INTEL_V3),'stream_id':'FRESH-I','train_cases':intel_cases,'fallback_output':CAP_LOGIC_V2,'payload':{'kind':'plan','urgent':True}}
intel=fabric.run(intel_task)

cap_tasks={CAP_LOGIC_V2:logic_task,CAP_THINK_V2:plan_task,CAP_INTEL_V3:intel_task}
capset=BoundedCapabilitySetCoordinatorV1.run(fabric,[CAP_LOGIC_V2,CAP_THINK_V2,CAP_INTEL_V3],cap_tasks)
checks={
 'logic_v2_dispatch':logic['result']=='ODD',
 'thinking_v2_dispatch':plan0['selected_capability']==CAP_THINK_V2 and plan0['meta']['feasible'],
 'intelligence_v3_dispatch':CAP_THINK_V2 in intel['result'],
 'three_capability_coordinator':capset.get('status')=='PASS',
 'memory_feedback_recorded':fabric.memory_snapshot()['semantic_feedback_count']==1,
 'memory_feedback_consumed':plan1['meta'].get('feedback_consumed') is True and abs(plan1['meta'].get('observed_gain',0)+0.15)<1e-12,
 'memory_ablation_removes_feedback':plan_abl['meta'].get('feedback_consumed') is False,
 'architecture_family_unchanged':fabric.architecture.get('architecture_family')=='TYPED_RECURRENT_CAPABILITY_GRAPH',
}
component=G2IntegratedExecutionFabricV1.component(digest(fabric.architecture))
status='PASS_SHADOW_G2_INTEGRATED_EXECUTION_FABRIC_V1' if all(checks.values()) else 'WITHHOLD_G2_INTEGRATED_EXECUTION_FABRIC_V1'
report={'schema':'yado.g2.integrated_execution_fabric.fresh_gate.v1','status':status,'checks':checks,'logic':logic,'thinking_before_feedback':plan0,'thinking_after_feedback':plan1,'thinking_memory_ablated':plan_abl,'intelligence':intel,'capability_set':capset,'memory_snapshot':fabric.memory_snapshot(),'component':component,'canonical_mutation':False,'architecture_mutation':False,'generation_transition':False,'g3_genesis_performed':False,'semantic_boundary':'SHADOW FRESH GATE FOR G2 EXECUTION CONNECTIVITY AND CAUSAL MEMORY FEEDBACK; NOT AGI OR CONSCIOUSNESS.'}
report['receipt_sha256']=digest(report)
out=REPO/'candidates/kernel-self-generated/g2-integrated-execution-fabric-v1.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps({'status':status,'checks':checks,'capability_set_status':capset.get('status'),'receipt_sha256':report['receipt_sha256']},indent=2,sort_keys=True))
if not all(checks.values()):raise SystemExit(2)
