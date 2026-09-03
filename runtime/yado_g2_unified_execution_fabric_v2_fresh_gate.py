from __future__ import annotations
from pathlib import Path
import hashlib,json,sys

ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_g2_typed_recurrent_capability_graph_runtime_v1 import G2TypedRecurrentCapabilityGraphRuntimeV1
from yado_g2_unified_execution_fabric_v2 import G2UnifiedExecutionFabricV2,CAP_API_EXEC_V1
from yado_bounded_capability_router_v1 import BoundedCapabilityRouterLearnerV1
from yado_conjunctive_rule_inducer_v1 import ConjunctiveRuleInducerV1
from yado_g2_openapi_contract_capability_v1 import G2OpenAPIContractCapabilityV1

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'
CAP_INTEL='ALG-G2-COVERAGE-PRUNED-COMPOSITIONAL-SCHEMA-ROUTER-V3'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()

def desc(cap):
    d={'budget_limited':False,'quota_limited':False,'external_evidence_needed':False,'relation_needed':False,'disjunction_needed':False}
    if cap==CAP_BUD:d['budget_limited']=True
    elif cap==CAP_RES:d['external_evidence_needed']=True
    elif cap==CAP_REL:d['relation_needed']=True
    return d

core=UnifiedYADOCoreV1(REPO)
route_cases=[]
for i in range(24):
    for cap in [CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES]:
        route_cases.append({'input':desc(cap)|{'nonce':i%3},'expected':cap})
router=BoundedCapabilityRouterLearnerV1.synthesize(route_cases,route_cases,CAP_CONJ,min_support=4)
rows=[]
for a in [False,True]:
  for b in [False,True]:
    for c in [False,True]:
      for _ in range(4):rows.append({'input':{'condition_a':a,'condition_b':b,'condition_c':c},'expected':'PASS' if a and b and c else 'HOLD'})
scalar=ConjunctiveRuleInducerV1.synthesize('FABRIC_V2_SCALAR','LOGIC',rows,min_support=2,max_rules=12)
class Rel:
    def execute(self,x):return 'ALLOW' if x.get('allow') else 'DENY'
base=G2TypedRecurrentCapabilityGraphRuntimeV1(core.architecture,router,scalar,Rel(),core.portfolio)
fabric=G2UnifiedExecutionFabricV2(base)

api_state={'policy_tree':{'label':'ALLOW'},'contract_registry':{
 'GET_REPO':{'source_id':'GITHUB_PUBLIC_API','source_sha':'fabric-v2','method':'GET','path':'/repos/v37025337-pixel/EVA','required':[],'redirect_semantic':False}
}}
plan=G2OpenAPIContractCapabilityV1(api_state).compile_plan('GET_REPO')
before=fabric.memory_snapshot()
live=fabric.execute_capability(CAP_API_EXEC_V1,{
  'plan':plan,'base_url':'https://api.github.com','allowed_hosts':['api.github.com'],
  'max_bytes':262144,'timeout':10,'stream_id':'FABRIC-V2-DIRECT'
})
after=fabric.memory_snapshot()

# Fresh Intelligence V3 -> API executor dispatch through the same fabric.
train=[]
for i in range(18):
    train += [
      {'input':{'kind':'api','need_live':True,'nonce':i%3},'expected':CAP_API_EXEC_V1},
      {'input':{'kind':'logic','need_live':False,'nonce':i%3},'expected':CAP_CONJ},
    ]
model=core.fit_compositional_capability_router(train,CAP_CONJ)
intel_task={
 'operation':'route_execute','model':model,'payload':{'kind':'api','need_live':True,'nonce':1},'stream_id':'FABRIC-V2-INTEL',
 'capability_tasks':{
   CAP_API_EXEC_V1:{'plan':plan,'base_url':'https://api.github.com','allowed_hosts':['api.github.com'],'max_bytes':262144,'timeout':10}
 }
}
intel=fabric.execute_capability(CAP_INTEL,intel_task)
snap=fabric.memory_snapshot()

# Memory ablation: execution may still succeed, but external evidence must not be stored.
abl_base=G2TypedRecurrentCapabilityGraphRuntimeV1(core.architecture,router,scalar,Rel(),core.portfolio)
abl=G2UnifiedExecutionFabricV2(abl_base)
abl_before=abl.memory_snapshot()
abl_out=abl.execute_capability(CAP_API_EXEC_V1,{
  'plan':plan,'base_url':'https://api.github.com','allowed_hosts':['api.github.com'],
  'max_bytes':262144,'timeout':10,'stream_id':'FABRIC-V2-ABL'
},ablated_memory=True)
abl_after=abl.memory_snapshot()

checks={
 'direct_api_dispatch':live.get('selected_capability')==CAP_API_EXEC_V1 and live.get('result',{}).get('status')==200,
 'external_evidence_recorded':after.get('external_evidence_count',0)==before.get('external_evidence_count',0)+1,
 'fabric_episode_recorded':after.get('fabric_episode_count',0)==before.get('fabric_episode_count',0)+1,
 'memory_metadata_only':all('body_text' not in e for e in base.episodes if e.get('kind')=='EXTERNAL_EVIDENCE'),
 'intelligence_routes_api_executor':intel.get('result',{}).get('status')=='PASS' and CAP_API_EXEC_V1 in tuple(intel.get('result',{}).get('selected',())),
 'intelligence_api_execution_200':intel.get('result',{}).get('results',{}).get(CAP_API_EXEC_V1,{}).get('result',{}).get('status')==200,
 'intelligence_api_evidence_recorded':snap.get('external_evidence_count',0)>=2,
 'memory_ablation_prevents_evidence_write':abl_out.get('result',{}).get('status')==200 and abl_after.get('external_evidence_count',0)==abl_before.get('external_evidence_count',0),
 'component_declares_readonly_network':G2UnifiedExecutionFabricV2.component().get('network_execution',{}).get('read_only_only') is True,
}
status='PASS_SHADOW_G2_UNIFIED_EXECUTION_FABRIC_V2' if all(checks.values()) else 'WITHHOLD_G2_UNIFIED_EXECUTION_FABRIC_V2'
report={
 'schema':'yado.g2.unified_execution_fabric.v2.fresh_gate','status':status,'checks':checks,
 'component':G2UnifiedExecutionFabricV2.component(),
 'direct_live':{k:v for k,v in live.get('result',{}).items() if k!='body_text'},
 'intelligence_result':{
   'status':intel.get('result',{}).get('status'),
   'selected':intel.get('result',{}).get('selected'),
   'order':intel.get('result',{}).get('order'),
 },
 'memory_before':before,'memory_after':after,'memory_final':snap,
 'ablated_memory_before':abl_before,'ablated_memory_after':abl_after,
 'canonical_mutation':False,'architecture_mutation':False,'generation_transition':False,'g3_genesis_performed':False,
 'semantic_boundary':'FRESH LIVE SHADOW GATE FOR UNIFIED FABRIC V2. API READ-ONLY NETWORK EXECUTION MUST BE DISPATCHABLE BY INTELLIGENCE AND WRITE BOUNDED METADATA-ONLY EXTERNAL EVIDENCE TO RECURRENT MEMORY.'
}
report['receipt_sha256']=digest(report)
out=REPO/'candidates/kernel-self-generated/g2-unified-execution-fabric-v2.json'
out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({'status':status,'checks':checks,'receipt_sha256':report['receipt_sha256']},indent=2,sort_keys=True))
if not all(checks.values()):raise SystemExit(2)
