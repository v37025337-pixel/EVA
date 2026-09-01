from __future__ import annotations
from pathlib import Path
import copy,hashlib,importlib.util,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
CORE=REPO/'canonical'/'yado-unified-core-v1.json'
ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
STATE=REPO/'architecture'/'yado-g2-lti-ceiling-state-v1.json'
UNIFIED=REPO/'runtime'/'yado_unified_core_v1.py'
SRC=REPO/'candidates'/'g2-self-evolution'/'work_budget_adaptive_contingent_planner_v2.py'
META=REPO/'candidates'/'g2-self-evolution'/'work_budget_adaptive_contingent_planner_v2.json'
ADMIT=REPO/'receipts'/'yado-thinking-plateau-fresh-admission-v1-run-33503208649.json'
TARGET=REPO/'runtime'/'yado_work_budget_adaptive_contingent_planner_v2.py'
OUT=ROOT/'yado_thinking_plateau_canonical_integration_v1_receipt.json'

OLD='ALG-G2-BOUNDED-ADAPTIVE-CONTINGENT-PLANNER-V1'
CID='ALG-G2-WORK-BUDGET-ADAPTIVE-CONTINGENT-PLANNER-V2'
OLD_SOURCE='runtime/yado_bounded_adaptive_contingent_planner_v1.py'
NEW_SOURCE='runtime/yado_work_budget_adaptive_contingent_planner_v2.py'
NEXT='LTI_CODE_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V6'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);core=load(CORE);ledger=load(LEDGER);state=load(STATE);meta=load(META);admit=load(ADMIT)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['THINKING_PLATEAU_CANONICAL_INTEGRATION_V1']:raise RuntimeError('UNEXPECTED_FRONTIER')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
if admit.get('status')!='PASS_THINKING_PLATEAU_FRESH_ADMISSION_V1':raise RuntimeError('FRESH_ADMISSION_NOT_PASS')
if meta.get('state')!='AUTHORIZED_FOR_SHADOW_ADMISSION':raise RuntimeError('CANDIDATE_NOT_AUTHORIZED')
if fsha(SRC)!=meta.get('candidate_source_sha256'):raise RuntimeError('SOURCE_DRIFT')
if admit.get('candidate_digest')!=meta.get('candidate_digest'):raise RuntimeError('ADMISSION_CANDIDATE_DRIFT')
arch_sha=fsha(ARCH)

TARGET.write_text(SRC.read_text(encoding='utf-8'),encoding='utf-8')
src=UNIFIED.read_text(encoding='utf-8')
old_import='from yado_bounded_adaptive_contingent_planner_v1 import BoundedAdaptiveContingentPlannerV1, ContingentStage'
new_import='from yado_work_budget_adaptive_contingent_planner_v2 import WorkBudgetAdaptiveContingentPlannerV2, ContingentStage'
if old_import not in src:raise RuntimeError('THINKING_IMPORT_ANCHOR_MISSING')
patched=src.replace(old_import,new_import)
patched=patched.replace(
 '        self.adaptive_contingent_planner=BoundedAdaptiveContingentPlannerV1',
 '        self.adaptive_contingent_planner=WorkBudgetAdaptiveContingentPlannerV2'
)
patch_ok=(patched.count(new_import)==1 and
          patched.count('self.adaptive_contingent_planner=WorkBudgetAdaptiveContingentPlannerV2')==1 and
          old_import not in patched)

new_core=copy.deepcopy(core);new_core.pop('core_digest',None)
think=next(x for x in new_core['planes'] if x.get('plane_id')=='THINKING_AND_PLANNING')
think['active_components']=[x for x in think.get('active_components',[]) if x!=OLD]
think['active_components']=sorted(set(think['active_components']+[CID]))
think['responsibilities']=sorted(set(think.get('responsibilities',[])+[
 'work_budget_adaptive_planning','beam_pruned_contingent_search',
 'stage_record_work_budget','search_node_work_budget'
]))
new_core['active_runtime_sources']=sorted(set(
 [x for x in new_core.get('active_runtime_sources',[]) if x!=OLD_SOURCE]+[NEW_SOURCE]
))
new_core.setdefault('superseded_components',[])
if not any(x.get('component_id')==OLD and x.get('superseded_by')==CID for x in new_core['superseded_components']):
    new_core['superseded_components'].append({
      'component_id':OLD,'superseded_by':CID,
      'reason':'THINKING_PLATEAU_REPLACED_FIXED_8_STAGE_8_DEPTH_GEOMETRY_WITH_EXPLICIT_WORK_BUDGETS',
      'historical_evidence_retained':True
    })
if isinstance(new_core.get('thinking_ceiling'),dict):
    new_core['thinking_ceiling']['status']='SUPERSEDED_BY_THINKING_PLATEAU_V2'
new_core['thinking_plateau_v2']={
 'component_id':CID,'candidate_digest':meta['candidate_digest'],'source_sha256':fsha(TARGET),
 'fresh_admission_receipt_sha256':admit['receipt_sha256'],'fresh_score':admit['fresh_score'],
 'causal_width_ablation':admit.get('causal',{}).get('width_ablation') is True,
 'compute_contract':meta['compute_contract'],'mode':'ACTIVE_WORK_BUDGET_ADAPTIVE_CONTINGENT_PLANNING',
 'supersedes':OLD,'gate_run_id':str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
}
new_core['current_frontier']=NEXT

tmp=ROOT/'_unified_thinking_v2_candidate.py';tmp.write_text(patched,encoding='utf-8')
api_ok=audit_ok=width_ok=dep_ok=signed_ok=False
try:
    sp=importlib.util.spec_from_file_location('_unified_thinking_v2_candidate',tmp)
    mod=importlib.util.module_from_spec(sp);sys.modules[sp.name]=mod;sp.loader.exec_module(mod)
    obj=mod.UnifiedYADOCoreV1(REPO)
    audit_ok=obj.audit().get('pass') is True

    st=[{'stage_id':f'w{i}','cost':1,'expected_gain':.09,'quota_remaining':1,'available':True} for i in range(11)]
    p=obj.plan_contingent(.01,1.0,11.0,st)
    width_ok=p.expected_confidence>=.999 and len(p.sequence)==11

    dep=[{'stage_id':'d0','cost':1,'expected_gain':.01,'quota_remaining':1,'available':True}]
    for i in range(1,12):
        dep.append({'stage_id':f'd{i}','cost':1,'expected_gain':.09,'quota_remaining':1,'available':True,'requires':[f'd{i-1}']})
    q=obj.update_contingent_plan(.0,1.0,12.0,dep,'d0',.01)
    dep_ok=q.expected_confidence>=.999 and len(q.sequence)>=11

    rec=[
      {'stage_id':'a','cost':1,'expected_gain':.25,'quota_remaining':1,'available':True},
      {'stage_id':'b','cost':1,'expected_gain':.25,'quota_remaining':1,'available':True,'requires':['a']},
      {'stage_id':'c','cost':1,'expected_gain':.25,'quota_remaining':1,'available':True,'requires':['b']},
      {'stage_id':'d','cost':1,'expected_gain':.25,'quota_remaining':1,'available':True,'requires':['c']},
    ]
    s=obj.update_contingent_plan(.85,.9,4.0,rec,'a',-.4)
    signed_ok=s.expected_confidence>=.9
    api_ok=width_ok and dep_ok and signed_ok
finally:
    try:tmp.unlink()
    except FileNotFoundError:pass

checks={
 'fresh_admission_all_checks':all(admit.get('checks',{}).values()),
 'fresh_score_one':float(admit.get('fresh_score',0))>=.99,
 'candidate_source_exact':fsha(TARGET)==meta.get('candidate_source_sha256'),
 'unified_patch_exact':patch_ok,
 'width11_probe':width_ok,'dependency11_probe':dep_ok,'signed_recovery_probe':signed_ok,
 'unified_api_probe':api_ok,'unified_audit_pass':audit_ok,
 'old_planner_removed':OLD not in think.get('active_components',[]),
 'v2_planner_active':CID in think.get('active_components',[]),
 'old_runtime_source_removed':OLD_SOURCE not in new_core.get('active_runtime_sources',[]),
 'new_runtime_source_active':NEW_SOURCE in new_core.get('active_runtime_sources',[]),
 'architecture_byte_identical':fsha(ARCH)==arch_sha,
 'g3_not_started':head.get('g3_genesis_performed') is False and core.get('g3_genesis_performed') is False
}
passed=all(checks.values())
post_head=post_core=None
if passed:
    UNIFIED.write_text(patched,encoding='utf-8');runtime_sha=fsha(UNIFIED)
    new_core['runtime_sha256']=runtime_sha;new_core['core_digest']=h(new_core)
    CORE.write_text(json.dumps(new_core,indent=2,sort_keys=True)+'\n')
    new_head=copy.deepcopy(head);new_head.pop('canonical_head_digest',None)
    new_head['new_capabilities']=sorted(set(new_head.get('new_capabilities',[])+[CID]))
    new_head['unified_core']['runtime_sha256']=runtime_sha
    new_head['unified_core']['core_digest']=new_core['core_digest']
    new_head['unified_core']['thinking_ceiling_source_sha256']=fsha(TARGET)
    new_head['unified_core']['thinking_active_component']=CID
    new_head['current_frontier']=NEXT
    new_head['canonical_head_digest']=h(new_head)
    HEAD.write_text(json.dumps(new_head,indent=2,sort_keys=True)+'\n')
    post_head=new_head['canonical_head_digest'];post_core=new_core['core_digest']

    state['candidate_history'].append({'round':state.get('round',13),'plane':'THINKING','candidate_digest':meta['candidate_digest'],
      'component_id':CID,'status':'CANONICAL_ACTIVE','fresh_score':admit['fresh_score'],
      'causal_drop':meta.get('causal_gain'),'gate_run_id':str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')})
    state['next_required_capability']=NEXT;state['status']='PLATEAU_SEARCH';state['plateau_streak']=0
    state['state_digest']=h({k:v for k,v in state.items() if k!='state_digest'})
    STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')
    status='PASS_THINKING_PLATEAU_CANONICAL_INTEGRATION_V1';next_cap=NEXT
else:
    try:TARGET.unlink()
    except FileNotFoundError:pass
    status='WITHHOLD_THINKING_PLATEAU_CANONICAL_INTEGRATION_V1';next_cap='THINKING_PLATEAU_SELF_EVOLUTION_V2'

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.thinking_plateau_canonical_integration.v1','status':status,
 'component_id':CID,'superseded_component_id':OLD,'candidate_digest':meta['candidate_digest'],
 'fresh_admission_receipt_sha256':admit['receipt_sha256'],'checks':checks,'architecture_sha256':arch_sha,
 'architecture_mutation':False,'canonical_mutation':passed,'promotion_applied':False,'generation_transition':False,
 'g3_genesis_performed':False,'post_head_digest':post_head,'post_core_digest':post_core,'next_required_capability':next_cap,
 'semantic_boundary':'SAME-G2 REPLACEMENT OF FIXED-GEOMETRY CONTINGENT PLANNER V1 BY EXPLICIT WORK-BUDGET BEAM PLANNER V2 AFTER INDEPENDENT FRESH ADMISSION.'
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_THINKING_PLATEAU_CANONICAL_INTEGRATION_V1",
 'event_type':'FIXED_ARCHITECTURE_THINKING_IMPLEMENTATION_REPLACEMENT','status':'PASS' if passed else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'THINKING_PLATEAU_CANONICAL_INTEGRATION_V1',
 'effect':'THINKING_V1_SUPERSEDED_BY_WORK_BUDGET_V2' if passed else 'THINKING_V2_INTEGRATION_WITHHELD',
 'source_path':f'receipts/yado-thinking-plateau-canonical-integration-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],
 'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':passed,'promotion_applied':False,'generation_transition':False}
if passed:
    e['previous_head_digest']=ledger['current_head_digest'];e['new_head_digest']=post_head
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
if passed:ledger['current_head_digest']=post_head
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({'status':status,'checks':checks,'post_head_digest':post_head,'architecture_sha256':arch_sha,
 'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('THINKING_PLATEAU_CANONICAL_INTEGRATION_WITHHELD')
