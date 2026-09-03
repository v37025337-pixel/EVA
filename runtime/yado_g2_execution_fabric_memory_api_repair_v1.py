from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,random,subprocess,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_bounded_capability_router_v1 import BoundedCapabilityRouterLearnerV1
from yado_conjunctive_rule_inducer_v1 import ConjunctiveRuleInducerV1
from yado_g2_typed_recurrent_capability_graph_runtime_v1 import G2TypedRecurrentCapabilityGraphRuntimeV1
from yado_g2_contextual_stream_capability_adapter_v1 import ContextualStreamCapabilityAdapterV1
from yado_g2_composite_transfer_repair_adapter_v1 import G2CompositeTransferRepairAdapterV1
from yado_g2_unified_execution_fabric_v1 import G2UnifiedExecutionFabricV1
from yado_g2_openapi_contract_capability_v1 import G2OpenAPIContractCapabilityV1
from yado_coverage_pruned_compositional_schema_router_v3 import CoveragePrunedCompositionalSchemaRouterV3
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
ARCH=REPO/'canonical/yado-g2-architecture-v1.json'
PORT=REPO/'resources/yado-unified-external-resource-portfolio-v1.json'
CTX_CAND=REPO/'candidates/g2-development/contextual-stream-capability-adapter-v1.json'
UNIFIED=ROOT/'yado_unified_core_v1.py'
FABRIC_SRC=ROOT/'yado_g2_unified_execution_fabric_v1.py'
API_SRC=ROOT/'yado_g2_openapi_contract_capability_v1.py'
API_SUBSTRATE=PKG/'yado_openapi_adapter_runtime.py'
CTX_SRC=ROOT/'yado_g2_contextual_stream_capability_adapter_v1.py'
COMPOSITE_SRC=ROOT/'yado_g2_composite_transfer_repair_adapter_v1.py'
GUARD=ROOT/'yado_canonical_invariant_guard_v1.py'
SELF_AUDIT=ROOT/'yado_unified_core_deep_self_audit_v1.py'
FABRIC_CANON=REPO/'canonical/yado-g2-unified-execution-fabric-v1.json'
API_CANON=REPO/'canonical/yado-g2-openapi-contract-capability-v1.json'
PATCH_CANON=REPO/'canonical/yado-g2-active-patch-registry-v1.json'
MEM_EVID=REPO/'resources/yado-context-adapter-fresh-readmission-v2.json'
OUT=ROOT/'yado_g2_execution_fabric_memory_api_repair_v1_receipt.json'

FRONT='KERNEL_G2_RAW_REPRESENTATION_V5_CANONICAL_ADMISSION_V1'
FABRIC_ID='RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V1'
API_ID='ALG-G2-OPENAPI-CONTRACT-CAPABILITY-V1'
LOGIC_V2='ALG-G2-BUDGET-ADAPTIVE-COMPOSITIONAL-LOGIC-V2'
THINK_V2='ALG-G2-WORK-BUDGET-ADAPTIVE-CONTINGENT-PLANNER-V2'
INTEL_V3='ALG-G2-COVERAGE-PRUNED-COMPOSITIONAL-SCHEMA-ROUTER-V3'
CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):
    x=copy.deepcopy(o);x.pop(field,None);return h(x)
def desc(cap,amb=False,nonce=0):
    d={'budget_limited':False,'quota_limited':False,'external_evidence_needed':False,'relation_needed':False,'disjunction_needed':False,'context_ambiguous':amb,'repair_nonce':nonce}
    if not amb:
        if cap==CAP_BUD:d['budget_limited']=True
        elif cap==CAP_RES:d['external_evidence_needed']=True
        elif cap==CAP_REL:d['relation_needed']=True
    return d

head,core,prov,ledger,arch,portfolio,ctxcand=map(load,[HEAD,CORE,PROV,LEDGER,ARCH,PORT,CTX_CAND])
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=[FRONT]:raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if head.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')
if head.get('architecture_family')!='TYPED_RECURRENT_CAPABILITY_GRAPH':raise RuntimeError('ARCHITECTURE_FAMILY_DRIFT')

# ---------- Fresh deterministic base runtime ----------
def route_cases(seed,n):
    r=random.Random(seed);out=[]
    caps=[CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES]
    for i in range(n):
        cap=caps[i%4]
        out.append({'input':desc(cap,False,r.randrange(10**9)),'expected':cap})
    return out
router=BoundedCapabilityRouterLearnerV1.synthesize(route_cases(26090301,800),route_cases(26090302,320),CAP_CONJ,min_support=5)

scalar_rows=[]
for a in [False,True]:
    for b in [False,True]:
        for c in [False,True]:
            for _ in range(8):
                scalar_rows.append({'input':{'condition_a':a,'condition_b':b,'condition_c':c},'expected':'PASS' if a and b and c else 'HOLD'})
scalar=ConjunctiveRuleInducerV1.synthesize('G2_FABRIC_FRESH_SCALAR','LOGIC',scalar_rows,min_support=2,max_rules=12)

class RelationStub:
    def execute(self,x):return 'ALLOW' if x.get('allow') else 'DENY'
relation=RelationStub()

def make_base():
    return G2TypedRecurrentCapabilityGraphRuntimeV1(arch,router,scalar,relation,portfolio)

# ---------- Memory adapter fresh re-admission ----------
def memory_eval(ablated=False):
    base=make_base();adapter=ContextualStreamCapabilityAdapterV1(base,'BOUNDED_STREAM_CONTEXT_MAP')
    caps=[CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES];correct=0;total=0
    for i in range(240):
        cap=caps[(i*3)%4];sid=f'MEM_{i}'
        if cap==CAP_CONJ:
            task={'kind':'scalar','descriptor':desc(cap,False,i),'stream_id':sid,'payload':{'condition_a':True,'condition_b':True,'condition_c':True}}
        elif cap==CAP_REL:
            task={'kind':'relation','descriptor':desc(cap,False,i),'stream_id':sid,'payload':{'allow':True}}
        elif cap==CAP_BUD:
            task={'kind':'budget','descriptor':desc(cap,False,i),'stream_id':sid,'current_confidence':.2,'target_confidence':.7,'remaining_budget':5.0,
                  'stages':[{'stage_id':f'A_{i}','cost':1.0,'expected_gain':.2,'quota_remaining':1,'available':True,'latency':1.0},
                            {'stage_id':f'B_{i}','cost':3.0,'expected_gain':.6,'quota_remaining':1,'available':True,'latency':2.0}]}
        else:
            keys=sorted(portfolio.get('routes_for_current_open_deficits',{}));key=keys[i%len(keys)]
            task={'kind':'resource','descriptor':desc(cap,False,i),'stream_id':sid,'route_key':key,'payload':{}}
        first=adapter.run(task)
        follow=copy.deepcopy(task);follow['descriptor']=desc(cap,True,i+100000)
        out=adapter.run(follow,ablated_context=ablated)
        total+=1;correct+=out['context_selected_capability']==cap
    return correct/total

memory_score=memory_eval(False)
memory_ablation=memory_eval(True)
memory_drop=memory_score-memory_ablation
memory_checks={
 'fresh_score':memory_score>=.99,
 'ablation_low':memory_ablation<=.40,
 'causal_drop':memory_drop>=.50,
 'source_changed_since_old_admission':fsha(CTX_SRC)!=ctxcand.get('canonical_source_sha256'),
}
mem_evidence={
 'schema':'yado.g2.context_adapter.fresh_readmission.v2',
 'status':'PASS' if all(memory_checks.values()) else 'WITHHOLD',
 'source_sha256':fsha(CTX_SRC),
 'previous_canonical_source_sha256':ctxcand.get('canonical_source_sha256'),
 'fresh_score':memory_score,'memory_ablation_score':memory_ablation,'causal_drop':memory_drop,
 'checks':memory_checks,'seed_family':'260903XX',
 'semantic_boundary':'FRESH SAME-G2 RE-ADMISSION OF BOUNDED STREAM CONTEXT MEMORY AFTER FUNCTIONAL SOURCE CHANGES. NOT AUTOBIOGRAPHICAL MEMORY OR CONSCIOUSNESS.'
}
mem_evidence['evidence_digest']=cdig(mem_evidence,'evidence_digest')
write(MEM_EVID,mem_evidence)

# ---------- Unified fabric fresh contour ----------
base=make_base();fabric=G2UnifiedExecutionFabricV1(base)

logic_rows=[]
for n in range(4):
    for _ in range(6):
        logic_rows.append({'input':{'a':bool(n&1),'b':bool(n&2)},'expected':'EVEN' if bin(n).count('1')%2==0 else 'ODD'})
logic_model=fabric.logic.learn_symmetric_boolean(logic_rows)

intel_cases=[]
for _ in range(8):
    intel_cases.extend([
      {'input':{'task_family':'CYCLE','mode':'FULL'},'expected':[LOGIC_V2,THINK_V2]},
      {'input':{'task_family':'LOGIC','mode':'LOCAL'},'expected':[LOGIC_V2]},
      {'input':{'task_family':'PLAN','mode':'LOCAL'},'expected':[THINK_V2]},
    ])
intel_model=CoveragePrunedCompositionalSchemaRouterV3.fit(intel_cases,'NOOP_FALLBACK')

cap_tasks={
 LOGIC_V2:{
   'operation':'predict_symmetric','model':logic_model,'payload':{'a':True,'b':False},
   'stream_id':'CYCLE_1'
 },
 THINK_V2:{
   'operation':'plan','requires_capabilities':[LOGIC_V2],
   'current_confidence':.20,'target_confidence':.75,'remaining_budget':5.0,
   'stages':[{'stage_id':'S1','cost':1.0,'expected_gain':.25},{'stage_id':'S2','cost':3.0,'expected_gain':.60}],
   'stream_id':'CYCLE_1'
 }
}
cycle=fabric.execute_capability(INTEL_V3,{
 'operation':'route_execute','model':intel_model,'payload':{'task_family':'CYCLE','mode':'FULL'},
 'capability_tasks':cap_tasks,'stream_id':'CYCLE_1'
})
cycle_result=cycle['result']
logic_result=cycle_result.get('results',{}).get(LOGIC_V2,{})
think_result=cycle_result.get('results',{}).get(THINK_V2,{})

fabric.record_outcome('CYCLE_1','S1',.35)
feedback=fabric.execute_capability(THINK_V2,{
 'operation':'auto_feedback_plan','current_confidence':.20,'target_confidence':.80,'remaining_budget':5.0,
 'stages':[{'stage_id':'S1','cost':1.0,'expected_gain':.25},{'stage_id':'S2','cost':3.0,'expected_gain':.60}],
 'stream_id':'CYCLE_1'
})
feedback_used=bool(feedback.get('meta',{}).get('memory_feedback_used'))
memory_snapshot=fabric.memory_snapshot()

fabric_checks={
 'intelligence_route_execute_pass':cycle_result.get('status')=='PASS',
 'logic_v2_dispatched':logic_result.get('selected_capability')==LOGIC_V2 and logic_result.get('result')=='ODD',
 'thinking_v2_dispatched':think_result.get('selected_capability')==THINK_V2 and isinstance(think_result.get('result'),dict) and bool(think_result['result'].get('feasible')),
 'memory_feedback_consumed_automatically':feedback_used,
 'feedback_record_present':memory_snapshot.get('stage_outcome_count',0)>=1,
 'fabric_episode_memory_present':memory_snapshot.get('fabric_episode_count',0)>=3,
}

# Legacy execution through same fabric.
legacy_task={'kind':'scalar','descriptor':desc(CAP_CONJ,False,91),'stream_id':'LEGACY_FABRIC','payload':{'condition_a':True,'condition_b':True,'condition_c':True}}
legacy_out=fabric.execute_capability(CAP_CONJ,legacy_task)
fabric_checks['legacy_capability_same_fabric']=legacy_out.get('result')=='PASS'

# ---------- OpenAPI bounded capability fresh admission ----------
api_state={
 'policy_tree':{'label':'ALLOW'},
 'contract_registry':{
   'GET_X':{'source_id':'DOC','source_sha':'fresh-doc-sha','method':'GET','path':'/x','required':[{'in':'query','name':'id','type':'string'}],'redirect_semantic':False},
   'POST_X':{'source_id':'DOC','source_sha':'fresh-doc-sha','method':'POST','path':'/x','required':[{'in':'body','name':'payload','type':'object'}],'redirect_semantic':False},
 }
}
api_cap=G2OpenAPIContractCapabilityV1(api_state)
get_plan=api_cap.compile_plan('GET_X');post_plan=api_cap.compile_plan('POST_X');unknown=api_cap.compile_plan('UNKNOWN')
api_checks={
 'get_contract_compiles':get_plan.get('contract_id')=='GET_X' and get_plan.get('read_only_candidate') is True,
 'post_contract_compiles':post_plan.get('contract_id')=='POST_X' and post_plan.get('read_only_candidate') is False,
 'network_execute_false_get':get_plan.get('network_execute') is False,
 'network_execute_false_post':post_plan.get('network_execute') is False,
 'unknown_withholds':unknown.get('action')=='SEEK_MORE_EVIDENCE' and unknown.get('network_execute') is False,
}

# ---------- Active patch verification ----------
receipt_by_digest={}
for p in (REPO/'receipts').glob('*.json'):
    try:
        x=load(p);d=x.get('receipt_sha256')
        if d:receipt_by_digest[d]=p.relative_to(REPO).as_posix()
    except Exception:pass

def evidence(d):return {'digest':d,'path':receipt_by_digest.get(d),'verified':d in receipt_by_digest}
patches=[
 {'patch_id':'PROGRAM_REPAIR_V11','component_id':'ALG-G2-AMBIGUITY-AWARE-PROGRAM-REPAIR-V11','source':'runtime/yado_ambiguity_aware_program_repair_v11.py',
  'source_sha256':fsha(ROOT/'yado_ambiguity_aware_program_repair_v11.py'),'expected_source_sha256':core.get('program_execution',{}).get('source_sha256'),
  'evidence':[evidence(core.get('program_execution',{}).get('fresh_admission_receipt_sha256'))]},
 {'patch_id':'COMPOSITE_TRANSFER_REPAIR','component_id':'ALG-G2-COMPOSITE-TRANSFER-REPAIR-ADAPTER-V1','source':'runtime/yado_g2_composite_transfer_repair_adapter_v1.py',
  'source_sha256':fsha(COMPOSITE_SRC),'expected_source_sha256':core.get('composite_executable_successor_v1',{}).get('runtime_sha256'),
  'evidence':[evidence('c439c09b04c66902a2a0c24698966539950573d69d27746e4597ac242ac3fd73'),evidence('8d74cf03d9066c0a08fd976633a309ea04b85267dd75d222cd62a10c2d517931'),evidence('9e19959d9a7eb32bf876ea70ea8c4b8096e5eccf206f6047d8947a83f65428ac')]},
 {'patch_id':'CONTEXT_MEMORY_ADAPTER','component_id':'ALG-G2-CONTEXTUAL-STREAM-CAPABILITY-ADAPTER-V1','source':'runtime/yado_g2_contextual_stream_capability_adapter_v1.py',
  'source_sha256':fsha(CTX_SRC),'expected_source_sha256':fsha(CTX_SRC),'evidence':[{'digest':mem_evidence['evidence_digest'],'path':MEM_EVID.relative_to(REPO).as_posix(),'verified':mem_evidence['status']=='PASS'}]},
 {'patch_id':'LOGIC_V2','component_id':LOGIC_V2,'source':'runtime/yado_budget_adaptive_compositional_logic_v2.py',
  'source_sha256':fsha(ROOT/'yado_budget_adaptive_compositional_logic_v2.py'),'expected_source_sha256':core.get('logic_plateau_v2',{}).get('source_sha256'),
  'evidence':[evidence(core.get('logic_plateau_v2',{}).get('fresh_admission_receipt_sha256'))]},
 {'patch_id':'THINKING_V2','component_id':THINK_V2,'source':'runtime/yado_work_budget_adaptive_contingent_planner_v2.py',
  'source_sha256':fsha(ROOT/'yado_work_budget_adaptive_contingent_planner_v2.py'),'expected_source_sha256':core.get('thinking_plateau_v2',{}).get('source_sha256'),
  'evidence':[evidence(core.get('thinking_plateau_v2',{}).get('fresh_admission_receipt_sha256'))]},
 {'patch_id':'INTELLIGENCE_V3','component_id':INTEL_V3,'source':'runtime/yado_coverage_pruned_compositional_schema_router_v3.py',
  'source_sha256':fsha(ROOT/'yado_coverage_pruned_compositional_schema_router_v3.py'),'expected_source_sha256':core.get('intelligence_plateau_v3',{}).get('source_sha256'),
  'evidence':[evidence(core.get('intelligence_plateau_v3',{}).get('functional_fresh_receipt_sha256'))]},
]
for p in patches:
    p['source_hash_ok']=p['source_sha256']==p['expected_source_sha256']
    p['evidence_ok']=all(x.get('verified') for x in p['evidence'])
    p['status']='PASS' if p['source_hash_ok'] and p['evidence_ok'] else 'WITHHOLD'

# Fresh functional patch smoke.
base2=make_base();comp=G2CompositeTransferRepairAdapterV1(base2)
comp_smoke=comp.run({'kind':'scalar','descriptor':desc(CAP_CONJ,False,808),'stream_id':'PATCH_SMOKE','payload':{'condition_a':True,'condition_b':True,'condition_c':True}})
repair_smoke=comp_smoke.get('result')=='PASS'

all_checks={
 'memory_readmission':all(memory_checks.values()),
 'execution_fabric':all(fabric_checks.values()),
 'api_contract_capability':all(api_checks.values()),
 'patch_registry':all(p['status']=='PASS' for p in patches),
 'composite_functional_smoke':repair_smoke,
 'architecture_family_unchanged':head.get('architecture_family')=='TYPED_RECURRENT_CAPABILITY_GRAPH',
 'frontier_preserved':ledger.get('open_deficits')==[FRONT],
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
admit=all(all_checks.values())
if not admit:
    receipt={
      'schema':'yado.g2.execution_fabric_memory_api_repair.receipt.v1','status':'WITHHOLD_G2_EXECUTION_FABRIC_MEMORY_API_REPAIR_V1',
      'checks':all_checks,'memory':mem_evidence,'fabric_checks':fabric_checks,'api_checks':api_checks,'patches':patches,
      'canonical_mutation':False,'architecture_mutation':False,'generation_transition':False,'g3_genesis_performed':False,
      'frontier_unchanged':FRONT
    }
    receipt['receipt_sha256']=h(receipt);write(OUT,receipt)
    print(json.dumps(receipt,indent=2,sort_keys=True,default=str))
    raise SystemExit('G2_EXECUTION_FABRIC_REPAIR_WITHHELD')

# ---------- Canonical same-G2 integration ----------
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
fabric_component=G2UnifiedExecutionFabricV1.component()
fabric_canon={
 'schema':'yado.g2.unified_execution_fabric.canonical.v1','status':'CANONICAL_ACTIVE',
 'component_id':FABRIC_ID,'component':fabric_component,'runtime_source':'runtime/yado_g2_unified_execution_fabric_v1.py',
 'runtime_sha256':fsha(FABRIC_SRC),'formal_generation':head.get('generation_id'),'architecture_family':head.get('architecture_family'),
 'fresh_checks':fabric_checks,'memory_feedback':'STAGE_OUTCOME_MEMORY_TO_AUTO_FEEDBACK_PLAN',
 'architecture_mutation':False,
 'semantic_boundary':'SAME-G2 UNIFIED DISPATCH FABRIC FOR EXISTING LOGIC/THINKING/INTELLIGENCE/MEMORY CAPABILITIES. NO NEW FORMAL GENERATION.'
}
fabric_canon['canonical_component_digest']=cdig(fabric_canon,'canonical_component_digest');write(FABRIC_CANON,fabric_canon)

api_component=G2OpenAPIContractCapabilityV1.component()
api_canon={
 'schema':'yado.g2.openapi_contract_capability.canonical.v1','status':'CANONICAL_ACTIVE',
 'component_id':API_ID,'component':api_component,'runtime_source':'runtime/yado_g2_openapi_contract_capability_v1.py',
 'runtime_sha256':fsha(API_SRC),'substrate_source':'runtime/yado_rc8_v36/yado_openapi_adapter_runtime.py',
 'substrate_sha256':fsha(API_SUBSTRATE),'fresh_checks':api_checks,'network_execute':False,
 'architecture_mutation':False,
 'semantic_boundary':'CANONICAL BOUNDED OPENAPI CONTRACT CLASSIFICATION/PLAN CAPABILITY. NETWORK EXECUTION REMAINS DISABLED AND REQUIRES A SEPARATE FRESH ADMISSION.'
}
api_canon['canonical_component_digest']=cdig(api_canon,'canonical_component_digest');write(API_CANON,api_canon)

patch_registry={
 'schema':'yado.g2.active_patch_registry.v1','status':'CANONICAL_ACTIVE',
 'generation':head.get('generation_id'),'patches':patches,
 'all_active_patch_bindings_verified':all(p['status']=='PASS' for p in patches),
 'context_memory_latest_readmission_evidence_digest':mem_evidence['evidence_digest'],
 'semantic_boundary':'ACTIVE PATCH/REPAIR SOURCE AND EVIDENCE BINDINGS. HISTORICAL/SHADOW PATCHES ARE NOT ACTIVE BY PRESENCE ALONE.'
}
patch_registry['registry_digest']=cdig(patch_registry,'registry_digest');write(PATCH_CANON,patch_registry)

# Rebind context adapter to its current source after fresh re-admission.
ctxcand['canonical_source_sha256']=fsha(CTX_SRC)
ctxcand.setdefault('canonical_admission',{})['latest_fresh_readmission_evidence_digest']=mem_evidence['evidence_digest']
ctxcand['canonical_admission']['latest_fresh_readmission_run_id']=run_id
ctxcand['canonical_admission']['adapter_score']=memory_score
ctxcand['canonical_admission']['memory_ablation_score']=memory_ablation
ctxcand['canonical_admission']['causal_drop']=memory_drop
ctxcand['state']='CANONICAL_ACTIVE_G2_REBOUND_V2'
ctxcand['candidate_digest']=cdig(ctxcand,'candidate_digest');write(CTX_CAND,ctxcand)

# Patch unified core runtime source only after fresh gates have passed.
src=UNIFIED.read_text(encoding='utf-8')
anchor='from yado_bounded_capability_set_coordinator_v1 import BoundedCapabilitySetCoordinatorV1\n'
imports=anchor+'from yado_g2_unified_execution_fabric_v1 import G2UnifiedExecutionFabricV1\nfrom yado_g2_openapi_contract_capability_v1 import G2OpenAPIContractCapabilityV1\n'
if 'from yado_g2_unified_execution_fabric_v1 import G2UnifiedExecutionFabricV1' not in src:
    if anchor not in src:raise RuntimeError('UNIFIED_IMPORT_ANCHOR_MISSING')
    src=src.replace(anchor,imports)
init_anchor='        self.capability_set_coordinator=BoundedCapabilitySetCoordinatorV1\n'
init_repl=init_anchor+'        self.execution_fabric_cls=G2UnifiedExecutionFabricV1\n        self.openapi_contract_capability_cls=G2OpenAPIContractCapabilityV1\n'
if 'self.execution_fabric_cls=G2UnifiedExecutionFabricV1' not in src:
    if init_anchor not in src:raise RuntimeError('UNIFIED_INIT_ANCHOR_MISSING')
    src=src.replace(init_anchor,init_repl)
method_anchor='    def snapshot(self)->dict[str,Any]:\n'
methods='''    def instantiate_execution_fabric(self,router_program,scalar_program,relation_program,api_state=None):
        base=G2TypedRecurrentCapabilityGraphRuntimeV1(
            self.architecture,router_program,scalar_program,relation_program,self.portfolio
        )
        return self.execution_fabric_cls(base,api_state=api_state)

    def compile_openapi_contract_plan(self,state_section:dict[str,Any],contract_id:str)->dict[str,Any]:
        return self.openapi_contract_capability_cls(state_section).compile_plan(contract_id)

'''
if 'def instantiate_execution_fabric(' not in src:
    if method_anchor not in src:raise RuntimeError('UNIFIED_METHOD_ANCHOR_MISSING')
    src=src.replace(method_anchor,methods+method_anchor)

old_exec="""    def execute_capability_set(self,runtime,selected_capabilities,capability_tasks):
        return self.capability_set_coordinator.run(runtime,selected_capabilities,capability_tasks)
"""
new_exec="""    def execute_capability_set(self,runtime,selected_capabilities,capability_tasks):
        if isinstance(runtime,G2UnifiedExecutionFabricV1):
            return runtime.run_capability_set(selected_capabilities,capability_tasks)
        fabric=self.execution_fabric_cls(runtime)
        return fabric.run_capability_set(selected_capabilities,capability_tasks)
"""
if old_exec in src:
    src=src.replace(old_exec,new_exec)
elif new_exec not in src:
    raise RuntimeError('UNIFIED_EXECUTE_CAPABILITY_SET_ANCHOR_MISSING')
UNIFIED.write_text(src,encoding='utf-8')
unified_sha=fsha(UNIFIED)

# Canonical plane bindings.
def plane(pid):
    p=next((x for x in core.get('planes',[]) if x.get('plane_id')==pid),None)
    if p is None:raise RuntimeError('MISSING_PLANE:'+pid)
    return p

workspace=plane('WORKSPACE_AND_INTEGRATION')
workspace['active_components']=sorted(set(workspace.get('active_components',[])+[FABRIC_ID]))
workspace['responsibilities']=sorted(set(workspace.get('responsibilities',[])+['unified_logic_thinking_intelligence_dispatch','outcome_feedback_to_memory']))

memory_plane=plane('MEMORY_AND_EXPERIENCE')
memory_plane['responsibilities']=sorted(set(memory_plane.get('responsibilities',[])+['stage_outcome_memory','automatic_planning_feedback_source']))

resource_plane=plane('RESOURCE_AND_EVIDENCE')
resource_plane['active_components']=sorted(set(resource_plane.get('active_components',[])+[API_ID]))
resource_plane['responsibilities']=sorted(set(resource_plane.get('responsibilities',[])+['bounded_openapi_contract_planning','network_execution_disabled']))

repair_plane=plane('SELF_AUDIT_AND_REPAIR')
repair_path='canonical/yado-g2-active-patch-registry-v1.json'
repair_plane['active_components']=list(dict.fromkeys(repair_plane.get('active_components',[])+[repair_path]))
repair_plane['responsibilities']=sorted(set(repair_plane.get('responsibilities',[])+['active_patch_source_evidence_binding']))

core['contextual_stream_adapter']['source_sha256']=fsha(CTX_SRC)
core['contextual_stream_adapter']['candidate_digest']=ctxcand['candidate_digest']
core['contextual_stream_adapter']['latest_fresh_readmission_evidence_digest']=mem_evidence['evidence_digest']
core['contextual_stream_adapter']['latest_fresh_readmission_run_id']=run_id
core['contextual_stream_adapter']['fresh_score']=memory_score
core['contextual_stream_adapter']['memory_ablation_score']=memory_ablation
core['contextual_stream_adapter']['causal_drop']=memory_drop
core['execution_fabric_v1']={
 'status':'CANONICAL_ACTIVE','component_id':FABRIC_ID,'canonical_component_digest':fabric_canon['canonical_component_digest'],
 'runtime_sha256':fsha(FABRIC_SRC),'fresh_checks':fabric_checks,'architecture_mutation':False
}
core['openapi_contract_capability_v1']={
 'status':'CANONICAL_ACTIVE','component_id':API_ID,'canonical_component_digest':api_canon['canonical_component_digest'],
 'runtime_sha256':fsha(API_SRC),'substrate_sha256':fsha(API_SUBSTRATE),'network_execute':False,'fresh_checks':api_checks
}
core['active_patch_registry']={'artifact':repair_path,'registry_digest':patch_registry['registry_digest'],'status':'CANONICAL_ACTIVE'}
core.setdefault('composite_executable_successor_v1',{})['evidence_chain']=[x for x in patches if x['patch_id']=='COMPOSITE_TRANSFER_REPAIR'][0]['evidence']

active_sources=set(core.get('active_runtime_sources',[]))
active_sources.update([
 'runtime/yado_g2_unified_execution_fabric_v1.py',
 'runtime/yado_g2_openapi_contract_capability_v1.py',
 'runtime/yado_rc8_v36/yado_openapi_adapter_runtime.py',
])
core['active_runtime_sources']=sorted(active_sources)

rim=core.get('runtime_integrity_manifest')
if not isinstance(rim,dict) or not isinstance(rim.get('sources'),dict):raise RuntimeError('RUNTIME_INTEGRITY_MANIFEST_MISSING')
rim['sources']['runtime/yado_unified_core_v1.py']=unified_sha if 'runtime/yado_unified_core_v1.py' in core['active_runtime_sources'] else rim['sources'].get('runtime/yado_unified_core_v1.py')
# yado_unified_core_v1 is bound separately by canonical guard and historically absent from active_runtime_sources.
if rim['sources'].get('runtime/yado_unified_core_v1.py') is None:
    rim['sources'].pop('runtime/yado_unified_core_v1.py',None)
rim['sources']['runtime/yado_g2_contextual_stream_capability_adapter_v1.py']=fsha(CTX_SRC)
rim['sources']['runtime/yado_g2_unified_execution_fabric_v1.py']=fsha(FABRIC_SRC)
rim['sources']['runtime/yado_g2_openapi_contract_capability_v1.py']=fsha(API_SRC)
rim['sources']['runtime/yado_rc8_v36/yado_openapi_adapter_runtime.py']=fsha(API_SUBSTRATE)
# Exact manifest must cover exactly active_runtime_sources.
rim['sources']={rel:fsha(REPO/rel) for rel in core['active_runtime_sources']}
rim['manifest_digest']=h(rim['sources'])
core['runtime_sha256']=unified_sha

prev=head['canonical_head_digest']

prov['current_g2_binding'].update({
 'current_execution_label':'G2_UNIFIED_EXECUTION_FABRIC_MEMORY_API_BOUND_V1',
 'frontier':FRONT,'execution_fabric_component':FABRIC_ID,'openapi_contract_component':API_ID,
 'context_memory_source_sha256':fsha(CTX_SRC),'active_patch_registry_digest':patch_registry['registry_digest']
})
prov['registry_digest']=cdig(prov,'registry_digest');write(PROV,prov)

core['algorithm_provenance_registry_digest']=prov['registry_digest']
core['current_frontier']=FRONT
core['core_digest']=cdig(core,'core_digest');write(CORE,core)

head['active_capabilities']=sorted(set(head.get('active_capabilities',[])+[FABRIC_ID,API_ID]))
head['new_capabilities']=sorted(set(head.get('new_capabilities',[])+[FABRIC_ID,API_ID]))
head['execution_fabric_v1']={'status':'CANONICAL_ACTIVE','component_id':FABRIC_ID,'canonical_component_digest':fabric_canon['canonical_component_digest'],'fresh_checks':fabric_checks}
head['openapi_contract_capability_v1']={'status':'CANONICAL_ACTIVE','component_id':API_ID,'canonical_component_digest':api_canon['canonical_component_digest'],'network_execute':False}
head['active_patch_registry']={'registry_digest':patch_registry['registry_digest'],'status':'CANONICAL_ACTIVE'}
head['context_memory_rebinding_v2']={'source_sha256':fsha(CTX_SRC),'evidence_digest':mem_evidence['evidence_digest'],'fresh_score':memory_score,'causal_drop':memory_drop}
head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest']
head['algorithm_provenance_registry']['current_execution_label']=prov['current_g2_binding']['current_execution_label']
head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest']
head['unified_core']['core_digest']=core['core_digest']
head['unified_core']['runtime_sha256']=unified_sha
head['unified_core']['runtime_integrity_manifest_digest']=rim['manifest_digest']
head['current_frontier']=FRONT
head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)

ledger['current_head_digest']=head['canonical_head_digest']
receipt={
 'schema':'yado.g2.execution_fabric_memory_api_repair.receipt.v1',
 'status':'PASS_G2_EXECUTION_FABRIC_MEMORY_API_REPAIR_V1',
 'checks':all_checks,'memory_readmission':mem_evidence,'fabric_checks':fabric_checks,'api_checks':api_checks,
 'patch_registry_digest':patch_registry['registry_digest'],'patches':patches,
 'execution_fabric_component_digest':fabric_canon['canonical_component_digest'],
 'openapi_component_digest':api_canon['canonical_component_digest'],
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest'],
 'canonical_mutation':True,'canonical_mechanism_mutation':True,'architecture_mutation':False,
 'generation_transition':False,'g3_genesis_performed':False,'frontier_unchanged':FRONT,
 'network_execution_enabled':False,
 'semantic_boundary':'SAME-G2 RUNTIME INTEGRATION REPAIR. LOGIC V2, THINKING V2, INTELLIGENCE V3 AND MEMORY FEEDBACK SHARE ONE EXECUTION FABRIC. OPENAPI CONTRACT PLANNING IS ACTIVE BUT NETWORK EXECUTION REMAINS DISABLED.'
}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)

e={
 'index':len(ledger['events']),
 'event_id':f"E{len(ledger['events'])+1:04d}_G2_EXECUTION_FABRIC_MEMORY_API_REPAIR_V1",
 'event_type':'G2_EXECUTION_FABRIC_MEMORY_API_INTEGRATION_REPAIR','status':'PASS_CANONICAL',
 'generation':ledger['current_head'],'deficit':'G2_CONTOUR_DISPATCH_MEMORY_FEEDBACK_PATCH_API_BINDING_GAPS',
 'effect':f"FABRIC={FABRIC_ID}; API={API_ID}; MEMORY_FRESH={memory_score:.6f}; MEMORY_ABLATION={memory_ablation:.6f}; PATCHES={len(patches)}; NETWORK_EXECUTION=False; FRONTIER_UNCHANGED={FRONT}",
 'source_path':f'receipts/yado-g2-execution-fabric-memory-api-repair-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':True,'canonical_mechanism_mutation':True,'architecture_mutation':False,'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']
}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);write(LEDGER,ledger)

ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=FRONT:raise RuntimeError('POST_REPAIR_CONTEXT_FRONTIER_DRIFT')
post=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=60)
if post.returncode!=0:raise RuntimeError('POST_REPAIR_CANONICAL_GUARD_FAILED:'+post.stdout[-5000:]+post.stderr[-1500:])

print(json.dumps({
 'status':receipt['status'],'memory_score':memory_score,'memory_ablation':memory_ablation,
 'fabric_checks':fabric_checks,'api_checks':api_checks,'patch_statuses':{p['patch_id']:p['status'] for p in patches},
 'frontier':FRONT,'network_execution_enabled':False
},indent=2,sort_keys=True,default=str))
