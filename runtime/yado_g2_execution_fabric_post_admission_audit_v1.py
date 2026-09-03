from __future__ import annotations
from pathlib import Path
import hashlib,json,subprocess,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_bounded_capability_router_v1 import BoundedCapabilityRouterLearnerV1
from yado_conjunctive_rule_inducer_v1 import ConjunctiveRuleInducerV1
from yado_g2_typed_recurrent_capability_graph_runtime_v1 import G2TypedRecurrentCapabilityGraphRuntimeV1

OUT=REPO/'audits/yado-g2-execution-fabric-post-admission-audit-v1.json'
HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
PATCH=REPO/'canonical/yado-g2-active-patch-registry-v1.json'
CTX=REPO/'candidates/g2-development/contextual-stream-capability-adapter-v1.json'
FRONT='KERNEL_G2_RAW_REPRESENTATION_V5_CANONICAL_ADMISSION_V1'
FABRIC='RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V1'
API='ALG-G2-OPENAPI-CONTRACT-CAPABILITY-V1'
LOGIC='ALG-G2-BUDGET-ADAPTIVE-COMPOSITIONAL-LOGIC-V2'
THINK='ALG-G2-WORK-BUDGET-ADAPTIVE-CONTINGENT-PLANNER-V2'
CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'

def load(p):return json.loads(p.read_text(encoding='utf-8'))
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

head,core,ledger,patch,ctx=map(load,[HEAD,CORE,LEDGER,PATCH,CTX])
checks={};details={}
guard=subprocess.run([sys.executable,str(ROOT/'yado_canonical_invariant_guard_v1.py')],cwd=REPO,capture_output=True,text=True,timeout=60)
checks['canonical_guard']=guard.returncode==0
checks['frontier_preserved']=head.get('current_frontier')==FRONT and ledger.get('open_deficits')==[FRONT]
checks['g3_not_started']=head.get('g3_genesis_performed') is False

planes={p['plane_id']:p for p in core.get('planes',[])}
checks['fabric_bound_to_workspace']=FABRIC in planes.get('WORKSPACE_AND_INTEGRATION',{}).get('active_components',[])
checks['api_bound_to_resource_plane']=API in planes.get('RESOURCE_AND_EVIDENCE',{}).get('active_components',[])
checks['fabric_and_api_active_caps']=FABRIC in head.get('active_capabilities',[]) and API in head.get('active_capabilities',[])
checks['context_source_rebound']=core.get('contextual_stream_adapter',{}).get('source_sha256')==fsha(ROOT/'yado_g2_contextual_stream_capability_adapter_v1.py')==ctx.get('canonical_source_sha256')
checks['context_candidate_rebound']=core.get('contextual_stream_adapter',{}).get('candidate_digest')==ctx.get('candidate_digest')
checks['patch_registry_pass']=patch.get('all_active_patch_bindings_verified') is True and all(x.get('status')=='PASS' for x in patch.get('patches',[]))

# No tracked bytecode remains.
ls=subprocess.run(['git','ls-files'],cwd=REPO,capture_output=True,text=True,timeout=30).stdout.splitlines()
tracked=[x for x in ls if x.endswith('.pyc') or '/__pycache__/' in x]
checks['no_tracked_python_cache']=not tracked
details['tracked_python_cache']=tracked

# Fresh runtime construction through UnifiedYADOCoreV1.
def desc(cap):
    d={'budget_limited':False,'quota_limited':False,'external_evidence_needed':False,'relation_needed':False,'disjunction_needed':False}
    if cap==CAP_BUD:d['budget_limited']=True
    elif cap==CAP_RES:d['external_evidence_needed']=True
    elif cap==CAP_REL:d['relation_needed']=True
    return d

routes=[]
for i in range(20):
    for cap in [CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES]:
        routes.append({'input':desc(cap)|{'nonce':i%3},'expected':cap})
router=BoundedCapabilityRouterLearnerV1.synthesize(routes,routes,CAP_CONJ,min_support=3)
rows=[]
for a in [False,True]:
  for b in [False,True]:
    for c in [False,True]:
      for _ in range(5):
        rows.append({'input':{'condition_a':a,'condition_b':b,'condition_c':c},'expected':'PASS' if a and b and c else 'HOLD'})
scalar=ConjunctiveRuleInducerV1.synthesize('POST_FABRIC_SCALAR','LOGIC',rows,min_support=2,max_rules=12)
class Rel:
    def execute(self,x):return 'ALLOW' if x.get('allow') else 'DENY'
relation=Rel()
uc=UnifiedYADOCoreV1(REPO)
base=G2TypedRecurrentCapabilityGraphRuntimeV1(uc.architecture,router,scalar,relation,uc.portfolio)

logic_rows=[]
for n in range(4):
    for _ in range(4):
        logic_rows.append({'input':{'a':bool(n&1),'b':bool(n&2)},'expected':'EVEN' if bin(n).count('1')%2==0 else 'ODD'})
logic_model=uc.learn_symmetric_logic(logic_rows)
cap_tasks={
 LOGIC:{'operation':'predict_symmetric','model':logic_model,'payload':{'a':True,'b':False},'stream_id':'POST'},
 THINK:{'operation':'plan','requires_capabilities':[LOGIC],'current_confidence':.2,'target_confidence':.75,'remaining_budget':5.0,
        'stages':[{'stage_id':'S1','cost':1.0,'expected_gain':.25},{'stage_id':'S2','cost':3.0,'expected_gain':.6}],'stream_id':'POST'}
}
res=uc.execute_capability_set(base,[LOGIC,THINK],cap_tasks)
checks['unified_core_capability_set_uses_fabric']=res.get('status')=='PASS' and LOGIC in res.get('results',{}) and THINK in res.get('results',{})
details['capability_set']=res

fabric=uc.instantiate_execution_fabric(router,scalar,relation)
fabric.record_outcome('POST_FB','S1',.35)
fb=fabric.execute_capability(THINK,{'operation':'auto_feedback_plan','current_confidence':.2,'target_confidence':.8,'remaining_budget':5.0,
 'stages':[{'stage_id':'S1','cost':1.0,'expected_gain':.25},{'stage_id':'S2','cost':3.0,'expected_gain':.6}],'stream_id':'POST_FB'})
checks['memory_feedback_live']=fb.get('meta',{}).get('memory_feedback_used') is True
details['memory_feedback']=fb

api_state={'policy_tree':{'label':'ALLOW'},'contract_registry':{'GET_Z':{'source_id':'D','source_sha':'z','method':'GET','path':'/z','required':[],'redirect_semantic':False}}}
ap=uc.compile_openapi_contract_plan(api_state,'GET_Z')
checks['api_contract_live_network_disabled']=ap.get('contract_id')=='GET_Z' and ap.get('network_execute') is False
details['api_plan']=ap

ok=all(checks.values())
report={
 'schema':'yado.g2.execution_fabric_post_admission_audit.v1',
 'status':'PASS_G2_EXECUTION_FABRIC_POST_ADMISSION_AUDIT_V1' if ok else 'WITHHOLD_G2_EXECUTION_FABRIC_POST_ADMISSION_AUDIT_V1',
 'checks':checks,'details':details,'frontier':FRONT,'g3_genesis_performed':False,
 'semantic_boundary':'POST-ADMISSION SOFTWARE INTEGRITY AUDIT OF UNIFIED G2 EXECUTION FABRIC, MEMORY FEEDBACK, PATCH REGISTRY, AND BOUNDED OPENAPI CONTRACT PLANNING.'
}
OUT.parent.mkdir(exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2,sort_keys=True,default=str))
if not ok:raise SystemExit('POST_ADMISSION_AUDIT_WITHHOLD')
