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
CAND_SRC=REPO/'candidates'/'g2-self-evolution'/'bounded_adaptive_contingent_planner_v1.py'
CAND_META=REPO/'candidates'/'g2-self-evolution'/'bounded_adaptive_contingent_planner_v1.json'
ADMIT=REPO/'receipts'/'yado-thinking-architectural-ceiling-fresh-admission-v1-run-33441762902.json'
TARGET=REPO/'runtime'/'yado_bounded_adaptive_contingent_planner_v1.py'
OUT=ROOT/'yado_thinking_architectural_ceiling_canonical_integration_v1_receipt.json'
CID='ALG-G2-BOUNDED-ADAPTIVE-CONTINGENT-PLANNER-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);core=load(CORE);ledger=load(LEDGER);state=load(STATE);meta=load(CAND_META);admit=load(ADMIT)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['THINKING_ARCHITECTURAL_CEILING_CANONICAL_INTEGRATION_V1']:raise RuntimeError('UNEXPECTED_FRONTIER')
if admit.get('status')!='PASS_THINKING_ARCHITECTURAL_CEILING_FRESH_ADMISSION_V1':raise RuntimeError('FRESH_ADMISSION_NOT_PASS')
if meta.get('state')!='AUTHORIZED_FOR_SHADOW_ADMISSION':raise RuntimeError('CANDIDATE_NOT_AUTHORIZED')
if fsha(CAND_SRC)!=meta.get('candidate_source_sha256'):raise RuntimeError('SOURCE_DRIFT')
if admit.get('candidate_source_sha256')!=meta.get('candidate_source_sha256'):raise RuntimeError('ADMISSION_SOURCE_DRIFT')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
arch_sha=fsha(ARCH)

candidate_code=CAND_SRC.read_text(encoding='utf-8')
TARGET.write_text(candidate_code,encoding='utf-8')

src=UNIFIED.read_text(encoding='utf-8')
import_anchor='from yado_bounded_scientific_data_reasoner_v1 import BoundedScientificDataReasonerV1'
import_line=import_anchor+'\nfrom yado_bounded_adaptive_contingent_planner_v1 import BoundedAdaptiveContingentPlannerV1, ContingentStage'
patched=src if 'from yado_bounded_adaptive_contingent_planner_v1 import' in src else src.replace(import_anchor,import_line)

init_anchor='        self.scientific_data_reasoner=BoundedScientificDataReasonerV1'
init_line=init_anchor+'\n        self.adaptive_contingent_planner=BoundedAdaptiveContingentPlannerV1'
if 'self.adaptive_contingent_planner=BoundedAdaptiveContingentPlannerV1' not in patched:
    patched=patched.replace(init_anchor,init_line)

method_anchor='    def repair_program(self,source:str,function_name:str,train_examples:list[tuple[tuple[Any,...],Any]],max_candidates:int=10000)->dict[str,Any]:'
methods='''    @staticmethod
    def _contingent_stage_from_dict(x:dict[str,Any])->ContingentStage:
        return ContingentStage(
            str(x["stage_id"]),float(x["cost"]),float(x["expected_gain"]),int(x.get("quota_remaining",1)),
            bool(x.get("available",True)),float(x.get("latency",1.0)),bool(x.get("attempted",False)),
            tuple(str(z) for z in x.get("requires",()))
        )

    def plan_contingent(self,current_confidence:float,target_confidence:float,remaining_budget:float,stages:list[dict[str,Any]],completed=()):
        xs=[self._contingent_stage_from_dict(x) for x in stages]
        return self.adaptive_contingent_planner.plan(current_confidence,target_confidence,remaining_budget,xs,completed=completed)

    def update_contingent_plan(self,current_confidence:float,target_confidence:float,remaining_budget:float,stages:list[dict[str,Any]],completed_stage_id:str,observed_gain:float,completed=()):
        xs=[self._contingent_stage_from_dict(x) for x in stages]
        return self.adaptive_contingent_planner.next_after_observation(
            current_confidence,target_confidence,remaining_budget,xs,completed_stage_id,observed_gain,completed=completed
        )

'''
if '    def plan_contingent(' not in patched:
    patched=patched.replace(method_anchor,methods+method_anchor)

patch_ok=(
 patched.count('from yado_bounded_adaptive_contingent_planner_v1 import BoundedAdaptiveContingentPlannerV1, ContingentStage')==1 and
 patched.count('self.adaptive_contingent_planner=BoundedAdaptiveContingentPlannerV1')==1 and
 patched.count('def plan_contingent(')==1 and patched.count('def update_contingent_plan(')==1
)

# Prospective manifest.
new_core=copy.deepcopy(core);new_core.pop('core_digest',None)
plane=next(x for x in new_core['planes'] if x.get('plane_id')=='THINKING_AND_PLANNING')
plane['active_components']=sorted(set(plane.get('active_components',[])+[CID]))
plane['responsibilities']=sorted(set(plane.get('responsibilities',[])+[
    'bounded_contingent_planning','signed_evidence_update','prerequisite_aware_planning','bounded_long_horizon_search'
]))
new_core['active_runtime_sources']=sorted(set(new_core.get('active_runtime_sources',[])+['runtime/yado_bounded_adaptive_contingent_planner_v1.py']))
new_core['thinking_ceiling']={
 'component_id':CID,'candidate_digest':meta['candidate_digest'],'source_sha256':fsha(TARGET),
 'selected_strategy':meta['selected_strategy'],'selected_features':meta['selected_features'],
 'fresh_admission_receipt_sha256':admit['receipt_sha256'],'fresh_score':admit['fresh_score'],
 'causal':admit['causal'],'architecture_sha256':arch_sha,
 'mode':'ACTIVE_FIXED_ARCHITECTURE_ADAPTIVE_CONTINGENT_PLANNING',
 'gate_run_id':str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
}
new_core['current_frontier']='LTI_ARCHITECTURAL_CEILING_RECHECK_V2'

# Verify patched unified API against the candidate before mutation.
tmp=ROOT/'_unified_thinking_integration_candidate.py';tmp.write_text(patched,encoding='utf-8')
try:
    sp=importlib.util.spec_from_file_location('_unified_thinking_integration_candidate',tmp)
    mod=importlib.util.module_from_spec(sp);sys.modules[sp.name]=mod;sp.loader.exec_module(mod)
    obj=mod.UnifiedYADOCoreV1(REPO)
    audit=obj.audit()
    stages=[
      {'stage_id':'A','cost':1,'expected_gain':.1,'quota_remaining':1,'available':True,'requires':[]},
      {'stage_id':'B','cost':1,'expected_gain':.4,'quota_remaining':1,'available':False,'requires':['A']},
    ]
    p=obj.update_contingent_plan(.3,.75,3,stages,'A',.1)
    api_ok=(p.action=='B' and p.expected_confidence>=.75-1e-9)
finally:
    try:tmp.unlink()
    except FileNotFoundError:pass

checks={
 'fresh_admission_all_checks':all(admit.get('checks',{}).values()),
 'fresh_score_one':float(admit.get('fresh_score',0))>=.99,
 'candidate_source_exact':fsha(TARGET)==meta.get('candidate_source_sha256'),
 'unified_patch_bounded':patch_ok,
 'unified_api_fresh_probe':api_ok,
 'unified_audit_pass':audit.get('pass') is True,
 'thinking_plane_binding':CID in plane.get('active_components',[]),
 'architecture_file_immutable':fsha(ARCH)==arch_sha,
 'head_ledger_coherent':ledger.get('current_head_digest')==head.get('canonical_head_digest'),
 'g3_not_started':head.get('g3_genesis_performed') is False and core.get('g3_genesis_performed') is False,
}
passed=all(checks.values())

post_head=post_core=None
if passed:
    UNIFIED.write_text(patched,encoding='utf-8');runtime_sha=fsha(UNIFIED)
    new_core['runtime_sha256']=runtime_sha
    new_core['core_digest']=h(new_core);CORE.write_text(json.dumps(new_core,indent=2,sort_keys=True)+'\n')
    new_head=copy.deepcopy(head);new_head.pop('canonical_head_digest',None)
    new_head['new_capabilities']=sorted(set(new_head.get('new_capabilities',[])+[CID]))
    new_head['unified_core']['runtime_sha256']=runtime_sha
    new_head['unified_core']['core_digest']=new_core['core_digest']
    new_head['unified_core']['thinking_ceiling_source_sha256']=fsha(TARGET)
    new_head['current_frontier']='LTI_ARCHITECTURAL_CEILING_RECHECK_V2'
    new_head['canonical_head_digest']=h(new_head);HEAD.write_text(json.dumps(new_head,indent=2,sort_keys=True)+'\n')
    post_head=new_head['canonical_head_digest'];post_core=new_core['core_digest']
    state['planes']['THINKING']['canonical_score']=admit['fresh_score']
    state['planes']['THINKING']['canonical_component']=CID
    state['candidate_history'].append({'round':1,'plane':'THINKING','candidate_digest':meta['candidate_digest'],'status':'CANONICAL_ACTIVE','fresh_score':admit['fresh_score'],'gate_run_id':str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')})
    state['next_required_capability']='LTI_ARCHITECTURAL_CEILING_RECHECK_V2'
    state['state_digest']=h({k:v for k,v in state.items() if k!='state_digest'});STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')
    status='PASS_THINKING_ARCHITECTURAL_CEILING_CANONICAL_INTEGRATION_V1';next_cap='LTI_ARCHITECTURAL_CEILING_RECHECK_V2'
else:
    try:TARGET.unlink()
    except FileNotFoundError:pass
    status='WITHHOLD_THINKING_ARCHITECTURAL_CEILING_CANONICAL_INTEGRATION_V1';next_cap='THINKING_ARCHITECTURAL_CEILING_SELF_EVOLUTION_V2'

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.thinking_architectural_ceiling_canonical_integration.v1','status':status,
 'component_id':CID,'candidate_digest':meta['candidate_digest'],'fresh_admission_receipt':admit['receipt_sha256'],
 'checks':checks,'architecture_sha256':arch_sha,'architecture_mutation':False,
 'canonical_mutation':passed,'promotion_applied':False,'generation_transition':False,'g3_genesis_performed':False,
 'post_head_digest':post_head,'post_core_digest':post_core,'next_required_capability':next_cap,
 'semantic_boundary':'SAME-GENERATION BINDING OF A NEW THINKING ALGORITHM TO THE EXISTING THINKING PLANE; G2 GRAPH TOPOLOGY REMAINS BYTE-IDENTICAL.'
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_THINKING_CEILING_CANONICAL_INTEGRATION",
 'event_type':'FIXED_ARCHITECTURE_THINKING_CAPABILITY_ADMISSION','status':'PASS' if passed else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'THINKING_ARCHITECTURAL_CEILING_CANONICAL_INTEGRATION_V1',
 'effect':'ADAPTIVE_CONTINGENT_PLANNER_BOUND_TO_EXISTING_THINKING_PLANE' if passed else 'THINKING_CEILING_INTEGRATION_WITHHELD',
 'source_path':f'receipts/yado-thinking-architectural-ceiling-canonical-integration-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':passed,'promotion_applied':False,'generation_transition':False}
if passed:e['previous_head_digest']=ledger['current_head_digest'];e['new_head_digest']=post_head
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
if passed:ledger['current_head_digest']=post_head
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':status,'checks':checks,'post_head_digest':post_head,'architecture_sha256':arch_sha,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('THINKING_CEILING_CANONICAL_INTEGRATION_WITHHELD')
