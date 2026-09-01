from __future__ import annotations
from pathlib import Path
import copy,hashlib,importlib.util,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
CORE=REPO/'canonical'/'yado-unified-core-v1.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json'
STATE=REPO/'architecture'/'yado-g2-lti-ceiling-state-v1.json'
UNIFIED=REPO/'runtime'/'yado_unified_core_v1.py'
G2RUNTIME=REPO/'runtime'/'yado_g2_typed_recurrent_capability_graph_runtime_v1.py'
CAND_SRC=REPO/'candidates'/'g2-self-evolution'/'bounded_capability_set_coordinator_v1.py'
CAND_META=REPO/'candidates'/'g2-self-evolution'/'bounded_capability_set_coordinator_v1.json'
ADMIT=REPO/'receipts'/'yado-intelligence-multi-dispatch-fresh-admission-v1-run-33466446714.json'
TARGET=REPO/'runtime'/'yado_bounded_capability_set_coordinator_v1.py'
OUT=ROOT/'yado_intelligence_multi_dispatch_canonical_integration_v1_receipt.json'
CID='ALG-G2-BOUNDED-CAPABILITY-SET-COORDINATOR-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);core=load(CORE);ledger=load(LEDGER);state=load(STATE);meta=load(CAND_META);admit=load(ADMIT)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['INTELLIGENCE_MULTI_DISPATCH_CANONICAL_INTEGRATION_V1']:raise RuntimeError('UNEXPECTED_FRONTIER')
if admit.get('status')!='PASS_INTELLIGENCE_MULTI_DISPATCH_FRESH_ADMISSION_V1':raise RuntimeError('FRESH_ADMISSION_NOT_PASS')
if meta.get('state')!='AUTHORIZED_FOR_SHADOW_ADMISSION':raise RuntimeError('CANDIDATE_NOT_AUTHORIZED')
if fsha(CAND_SRC)!=meta.get('candidate_source_sha256'):raise RuntimeError('SOURCE_DRIFT')
if admit.get('candidate_source_sha256')!=meta.get('candidate_source_sha256'):raise RuntimeError('ADMISSION_SOURCE_DRIFT')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
arch_sha=fsha(ARCH)

TARGET.write_text(CAND_SRC.read_text(encoding='utf-8'),encoding='utf-8')

# Patch existing typed runtime without changing its graph architecture.
runtime_src=G2RUNTIME.read_text(encoding='utf-8')
import_anchor='from yado_neutral_evidence_profile_selector_v1 import NeutralEvidenceProfileSelectorV1,EvidenceCandidate'
runtime_patched=runtime_src if 'from yado_bounded_capability_set_coordinator_v1 import BoundedCapabilitySetCoordinatorV1' in runtime_src else runtime_src.replace(
 import_anchor,import_anchor+'\nfrom yado_bounded_capability_set_coordinator_v1 import BoundedCapabilitySetCoordinatorV1'
)
method_anchor='    def select_architecture_candidate(self,candidates):'
runtime_method='''    def run_capability_set(self,selected_capabilities,capability_tasks):
        return BoundedCapabilitySetCoordinatorV1.run(self,selected_capabilities,capability_tasks)

'''
if '    def run_capability_set(' not in runtime_patched:
    runtime_patched=runtime_patched.replace(method_anchor,runtime_method+method_anchor)
runtime_patch_ok=(
 runtime_patched.count('from yado_bounded_capability_set_coordinator_v1 import BoundedCapabilitySetCoordinatorV1')==1 and
 runtime_patched.count('def run_capability_set(')==1
)

# Patch unified entrypoint.
unified_src=UNIFIED.read_text(encoding='utf-8')
uanchor='from yado_bounded_compositional_schema_router_v1 import BoundedCompositionalSchemaRouterV1'
unified_patched=unified_src if 'from yado_bounded_capability_set_coordinator_v1 import BoundedCapabilitySetCoordinatorV1' in unified_src else unified_src.replace(
 uanchor,uanchor+'\nfrom yado_bounded_capability_set_coordinator_v1 import BoundedCapabilitySetCoordinatorV1'
)
ianchor='        self.compositional_schema_router=BoundedCompositionalSchemaRouterV1'
if 'self.capability_set_coordinator=BoundedCapabilitySetCoordinatorV1' not in unified_patched:
    unified_patched=unified_patched.replace(ianchor,ianchor+'\n        self.capability_set_coordinator=BoundedCapabilitySetCoordinatorV1')
manchor='    def fit_compositional_capability_router(self,cases:list[dict[str,Any]],fallback_output:str)->dict[str,Any]:'
umethod='''    def execute_capability_set(self,runtime,selected_capabilities,capability_tasks):
        return self.capability_set_coordinator.run(runtime,selected_capabilities,capability_tasks)

'''
if '    def execute_capability_set(' not in unified_patched:
    unified_patched=unified_patched.replace(manchor,umethod+manchor)
unified_patch_ok=(
 unified_patched.count('from yado_bounded_capability_set_coordinator_v1 import BoundedCapabilitySetCoordinatorV1')==1 and
 unified_patched.count('self.capability_set_coordinator=BoundedCapabilitySetCoordinatorV1')==1 and
 unified_patched.count('def execute_capability_set(')==1
)

# Temporarily expose patched runtime to verify the exact canonical API before persistence.
old_runtime=G2RUNTIME.read_bytes()
G2RUNTIME.write_text(runtime_patched,encoding='utf-8')
api_ok=False;audit_ok=False
try:
    # clear potentially cached module
    sys.modules.pop('yado_g2_typed_recurrent_capability_graph_runtime_v1',None)
    tsp=importlib.util.spec_from_file_location('_unified_multi_candidate',UNIFIED)
    # compile patched unified under temp file so imports use patched actual runtime
    tmp=ROOT/'_unified_multi_candidate.py';tmp.write_text(unified_patched,encoding='utf-8')
    sp=importlib.util.spec_from_file_location('_unified_multi_candidate',tmp)
    mod=importlib.util.module_from_spec(sp);sys.modules[sp.name]=mod;sp.loader.exec_module(mod)
    obj=mod.UnifiedYADOCoreV1(REPO);audit_ok=obj.audit().get('pass') is True

    class DR:
        fallback_output='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
        def execute(self,x):return self.fallback_output
    class DS:
        def execute(self,x):return 'S'
    class DL:
        def execute(self,x):return 'R'
    rtmod=sys.modules['yado_g2_typed_recurrent_capability_graph_runtime_v1']
    rt=rtmod.G2TypedRecurrentCapabilityGraphRuntimeV1(
      load(ARCH),DR(),DS(),DL(),load(REPO/'resources'/'yado-unified-external-resource-portfolio-v1.json')
    )
    bud='ALG-BUDGETED-STAGE-POLICY-V1';rel='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
    tasks={
      bud:{'kind':'budget','stream_id':'B','descriptor':{},'current_confidence':.3,'target_confidence':.7,'remaining_budget':3,
           'stages':[{'stage_id':'s','cost':1,'expected_gain':.5,'quota_remaining':1,'available':True}]},
      rel:{'kind':'relation','stream_id':'R','descriptor':{},'payload':{},'requires_capabilities':[bud]},
    }
    direct=rt.run_capability_set((rel,bud),tasks)
    via=obj.execute_capability_set(rt,(rel,bud),tasks)
    api_ok=direct.get('status')=='PASS' and direct.get('order')==[bud,rel] and via.get('status')=='PASS'
finally:
    G2RUNTIME.write_bytes(old_runtime)
    try:tmp.unlink()
    except Exception:pass
    sys.modules.pop('yado_g2_typed_recurrent_capability_graph_runtime_v1',None)

new_core=copy.deepcopy(core);new_core.pop('core_digest',None)
plane=next(x for x in new_core['planes'] if x.get('plane_id')=='INTELLIGENCE_AND_META_SELECTION')
plane['active_components']=sorted(set(plane.get('active_components',[])+[CID]))
plane['responsibilities']=sorted(set(plane.get('responsibilities',[])+[
 'bounded_multi_capability_runtime_execution','dependency_aware_capability_coordination','capability_set_fail_closed_execution'
]))
new_core['active_runtime_sources']=sorted(set(new_core.get('active_runtime_sources',[])+['runtime/yado_bounded_capability_set_coordinator_v1.py']))
new_core['intelligence_multi_dispatch']={
 'component_id':CID,'candidate_digest':meta['candidate_digest'],'source_sha256':fsha(TARGET),
 'fresh_admission_receipt_sha256':admit['receipt_sha256'],'fresh_score':admit['fresh_score'],
 'causal':admit['causal'],'architecture_sha256':arch_sha,
 'mode':'ACTIVE_FIXED_ARCHITECTURE_MULTI_CAPABILITY_RUNTIME_COORDINATION',
 'max_capabilities':4,'max_dependency_edges':8,
 'gate_run_id':str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
}
new_core['current_frontier']='LTI_ARCHITECTURAL_CEILING_RECHECK_V5'

checks={
 'fresh_admission_all_checks':all(admit.get('checks',{}).values()),
 'fresh_score_one':float(admit.get('fresh_score',0))>=.99,
 'candidate_source_exact':fsha(TARGET)==meta.get('candidate_source_sha256'),
 'typed_runtime_patch_bounded':runtime_patch_ok,
 'unified_patch_bounded':unified_patch_ok,
 'prospective_runtime_api_probe':api_ok,
 'prospective_unified_audit_pass':audit_ok,
 'intelligence_plane_binding':CID in plane.get('active_components',[]),
 'architecture_file_immutable':fsha(ARCH)==arch_sha,
 'head_ledger_coherent':ledger.get('current_head_digest')==head.get('canonical_head_digest'),
 'g3_not_started':head.get('g3_genesis_performed') is False and core.get('g3_genesis_performed') is False,
}
passed=all(checks.values())
post_head=post_core=None
if passed:
    G2RUNTIME.write_text(runtime_patched,encoding='utf-8');g2runtime_sha=fsha(G2RUNTIME)
    UNIFIED.write_text(unified_patched,encoding='utf-8');unified_sha=fsha(UNIFIED)
    new_core['runtime_sha256']=unified_sha
    new_core['intelligence_multi_dispatch']['g2_runtime_sha256']=g2runtime_sha
    new_core['core_digest']=h(new_core);CORE.write_text(json.dumps(new_core,indent=2,sort_keys=True)+'\n')
    new_head=copy.deepcopy(head);new_head.pop('canonical_head_digest',None)
    new_head['new_capabilities']=sorted(set(new_head.get('new_capabilities',[])+[CID]))
    new_head['unified_core']['runtime_sha256']=unified_sha;new_head['unified_core']['core_digest']=new_core['core_digest']
    new_head['unified_core']['g2_runtime_sha256']=g2runtime_sha
    new_head['unified_core']['intelligence_multi_dispatch_source_sha256']=fsha(TARGET)
    new_head['current_frontier']='LTI_ARCHITECTURAL_CEILING_RECHECK_V5'
    new_head['canonical_head_digest']=h(new_head);HEAD.write_text(json.dumps(new_head,indent=2,sort_keys=True)+'\n')
    post_head=new_head['canonical_head_digest'];post_core=new_core['core_digest']
    state['candidate_history'].append({'round':5,'plane':'INTELLIGENCE','candidate_digest':meta['candidate_digest'],'status':'CANONICAL_ACTIVE','fresh_score':admit['fresh_score'],'gate_run_id':str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')})
    state['next_required_capability']='LTI_ARCHITECTURAL_CEILING_RECHECK_V5';state['state_digest']=h({k:v for k,v in state.items() if k!='state_digest'})
    STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')
    status='PASS_INTELLIGENCE_MULTI_DISPATCH_CANONICAL_INTEGRATION_V1';next_cap='LTI_ARCHITECTURAL_CEILING_RECHECK_V5'
else:
    try:TARGET.unlink()
    except FileNotFoundError:pass
    status='WITHHOLD_INTELLIGENCE_MULTI_DISPATCH_CANONICAL_INTEGRATION_V1';next_cap='INTELLIGENCE_ARCHITECTURAL_CEILING_SELF_EVOLUTION_V3'

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.intelligence_multi_dispatch_canonical_integration.v1','status':status,'component_id':CID,
 'candidate_digest':meta['candidate_digest'],'fresh_admission_receipt':admit['receipt_sha256'],'checks':checks,'architecture_sha256':arch_sha,
 'architecture_mutation':False,'canonical_mutation':passed,'promotion_applied':False,'generation_transition':False,'g3_genesis_performed':False,
 'post_head_digest':post_head,'post_core_digest':post_core,'next_required_capability':next_cap,
 'semantic_boundary':'BINDS BOUNDED CAPABILITY-SET COORDINATION INTO THE EXISTING TYPED RECURRENT G2 RUNTIME WITHOUT ALTERING THE CANONICAL GRAPH TOPOLOGY.'}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_INTELLIGENCE_MULTI_DISPATCH_CANONICAL_INTEGRATION",
 'event_type':'FIXED_ARCHITECTURE_RUNTIME_COORDINATION_ADMISSION','status':'PASS' if passed else 'WITHHOLD','generation':ledger['current_head'],
 'deficit':'INTELLIGENCE_MULTI_DISPATCH_CANONICAL_INTEGRATION_V1',
 'effect':'CAPABILITY_SET_COORDINATOR_BOUND_TO_TYPED_RUNTIME' if passed else 'MULTI_DISPATCH_INTEGRATION_WITHHELD',
 'source_path':f'receipts/yado-intelligence-multi-dispatch-canonical-integration-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],
 'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':passed,'promotion_applied':False,'generation_transition':False}
if passed:e['previous_head_digest']=ledger['current_head_digest'];e['new_head_digest']=post_head
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
if passed:ledger['current_head_digest']=post_head
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':status,'checks':checks,'post_head_digest':post_head,'architecture_sha256':arch_sha,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('INTELLIGENCE_MULTI_DISPATCH_CANONICAL_INTEGRATION_WITHHELD')
