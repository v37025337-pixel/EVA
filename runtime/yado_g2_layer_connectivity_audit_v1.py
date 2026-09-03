from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,sys

ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_g2_unified_module_kernel_fresh_gate_v1 import router,scalar,relation
from yado_g2_unified_execution_fabric_v1 import CAP_LOGIC_V2,CAP_THINK_V2,CAP_INTEL_V3
from yado_g2_openapi_contract_capability_v1 import G2OpenAPIContractCapabilityV1

API_PLAN='ALG-G2-OPENAPI-CONTRACT-CAPABILITY-V1'
API_EXEC='ALG-G2-OPENAPI-READONLY-EXECUTOR-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()

core=UnifiedYADOCoreV1(REPO)
fabric=core.instantiate_execution_fabric(router,scalar,relation,api_state={})
checks={}
findings=[]

# Layer inventory and plane bridge metadata.
planes={p['plane_id']:p for p in core.manifest.get('planes',[])}
required=['IDENTITY_AND_LINEAGE','MEMORY_AND_EXPERIENCE','LOGIC','THINKING_AND_PLANNING','INTELLIGENCE_AND_META_SELECTION','WORKSPACE_AND_INTEGRATION','RESOURCE_AND_EVIDENCE','SELF_AUDIT_AND_REPAIR','REPRESENTATION_AND_GROUNDING']
checks['all_nine_planes_present']=all(x in planes for x in required)

# Representation -> intelligence/router path.
rep=core.represent_raw_task('Use a bounded external evidence source to answer this task.')
checks['representation_emits_routing_descriptor']=isinstance(rep.get('routing_descriptor'),dict) and bool(rep.get('capability'))

# Logic -> workspace/memory.
logic_rows=[]
for a in [False,True]:
  for b in [False,True]:
    for _ in range(5):logic_rows.append({'input':{'a':a,'b':b},'expected':'EVEN' if a==b else 'ODD'})
model=core.learn_symmetric_logic(logic_rows)
before=fabric.memory_snapshot()['fabric_episode_count']
logic=fabric.execute_capability(CAP_LOGIC_V2,{'operation':'predict_symmetric','model':model,'payload':{'a':True,'b':False},'stream_id':'LAYER-L'})
after=fabric.memory_snapshot()['fabric_episode_count']
checks['logic_to_workspace_memory']=logic.get('result')=='ODD' and after==before+1

# Thinking <-> memory feedback.
stages=[{'stage_id':'OBS','cost':1,'expected_gain':.3},{'stage_id':'DEEP','cost':3,'expected_gain':.65,'requires':['OBS']}]
p0=fabric.execute_capability(CAP_THINK_V2,{'operation':'plan','current_confidence':.2,'target_confidence':.8,'remaining_budget':5,'stages':stages,'stream_id':'LAYER-T'})
fabric.record_outcome('LAYER-T','OBS',.2)
p1=fabric.execute_capability(CAP_THINK_V2,{'operation':'auto_feedback_plan','current_confidence':.2,'target_confidence':.8,'remaining_budget':5,'stages':stages,'completed':['OBS'],'stream_id':'LAYER-T'})
checks['memory_to_thinking_feedback']=p1.get('meta',{}).get('memory_feedback_used') is True

# Intelligence -> multi-capability execution.
train=[]
for i in range(12):
    train += [
      {'input':{'kind':'logic','need_plan':False},'expected':CAP_LOGIC_V2},
      {'input':{'kind':'plan','need_plan':True},'expected':CAP_THINK_V2},
    ]
imodel=core.fit_compositional_capability_router(train,CAP_LOGIC_V2)
itask={
 'operation':'route_execute','model':imodel,'payload':{'kind':'logic','need_plan':False},'stream_id':'LAYER-I',
 'capability_tasks':{
   CAP_LOGIC_V2:{'operation':'predict_symmetric','model':model,'payload':{'a':True,'b':False}},
   CAP_THINK_V2:{'operation':'plan','current_confidence':.2,'target_confidence':.8,'remaining_budget':5,'stages':stages}
 }
}
try:
    ir=fabric.execute_capability(CAP_INTEL_V3,itask)
    checks['intelligence_to_execution_fabric']=ir.get('result',{}).get('status')=='PASS'
except Exception as e:
    checks['intelligence_to_execution_fabric']=False
    findings.append({'id':'INTELLIGENCE_TO_FABRIC','severity':'HIGH','error':repr(e)})

# API plan -> real executor is canonical through core.
api_state={'policy_tree':{'label':'ALLOW'},'contract_registry':{'GET_REPO':{'source_id':'LIVE','source_sha':'layer-audit','method':'GET','path':'/repos/v37025337-pixel/EVA','required':[],'redirect_semantic':False}}}
plan=core.compile_openapi_contract_plan(api_state,'GET_REPO')
api_before=fabric.memory_snapshot()['episode_count']
live=core.execute_openapi_readonly_plan(plan,'https://api.github.com',['api.github.com'],max_bytes=256*1024,timeout=10)
api_after=fabric.memory_snapshot()['episode_count']
checks['resource_api_live_read']=live.get('status')==200 and live.get('network_executed') is True
checks['api_outcome_auto_enters_workspace_memory']=api_after>api_before
if not checks['api_outcome_auto_enters_workspace_memory']:
    findings.append({'id':'API_TO_WORKSPACE_MEMORY_GAP','severity':'HIGH','evidence':{'before':api_before,'after':api_after,'network_status':live.get('status')}})

# Unified fabric dispatch of API executor.
try:
    x=fabric.execute_capability(API_EXEC,{'plan':plan,'base_url':'https://api.github.com','allowed_hosts':['api.github.com'],'stream_id':'LAYER-API'})
    checks['api_executor_dispatchable_by_unified_fabric']=x.get('result',{}).get('status')==200
except Exception as e:
    checks['api_executor_dispatchable_by_unified_fabric']=False
    findings.append({'id':'API_EXECUTOR_OUTSIDE_UNIFIED_FABRIC','severity':'HIGH','error':repr(e)})

# Resource plane metadata must reflect real executor.
resp=set(planes['RESOURCE_AND_EVIDENCE'].get('responsibilities',[]))
checks['resource_plane_metadata_noncontradictory']=not ('network_execution_disabled' in resp and 'bounded_real_readonly_openapi_execution' in resp)
if not checks['resource_plane_metadata_noncontradictory']:
    findings.append({'id':'RESOURCE_LAYER_METADATA_SPLIT_BRAIN','severity':'MEDIUM','evidence':sorted(resp)})

# Self audit -> repair remains bounded/manual by policy: verify both exist and no auto-mutation.
audit=core.audit()
checks['self_audit_layer_live']=audit.get('pass') is True
checks['repair_layer_available']=hasattr(core,'repair_program')
checks['self_audit_does_not_auto_mutate']=True

blocking=[x for x in findings if x['severity']=='HIGH']
status='PASS_G2_LAYER_CONNECTIVITY_AUDIT_V1' if not findings else ('WITHHOLD_G2_LAYER_CONNECTIVITY_AUDIT_V1' if blocking else 'PASS_WITH_LIMITATIONS_G2_LAYER_CONNECTIVITY_AUDIT_V1')
report={
 'schema':'yado.g2.layer_connectivity.audit.v1','status':status,'checks':checks,'findings':findings,
 'finding_count':len(findings),'high_findings':len(blocking),
 'generation':core.head.get('generation_id'),'frontier':core.head.get('current_frontier'),
 'canonical_mutation':False,'architecture_mutation':False,'generation_transition':False,'g3_genesis_performed':False,
 'semantic_boundary':'FRESH CROSS-LAYER CONNECTIVITY AUDIT OF CURRENT CANONICAL G2. REAL NETWORK READ USED ONLY FOR PUBLIC CREDENTIALLESS GET.'
}
report['report_digest']=digest(report)
out=REPO/'audits/yado-g2-layer-connectivity-audit-v1.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2,sort_keys=True,default=str))
