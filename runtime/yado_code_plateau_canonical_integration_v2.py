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
SRC=REPO/'candidates'/'g2-self-evolution'/'ambiguity_aware_program_repair_v11.py'
META=REPO/'candidates'/'g2-self-evolution'/'ambiguity_aware_program_repair_v11.json'
ADMIT=REPO/'receipts'/'yado-code-plateau-fresh-admission-v9-run-33491923703.json'
TARGET=REPO/'runtime'/'yado_ambiguity_aware_program_repair_v11.py'
OUT=ROOT/'yado_code_plateau_canonical_integration_v2_receipt.json'

OLD='ALG-G2-BOUNDED-COMPOSITIONAL-PROGRAM-REPAIR-V3'
CID='ALG-G2-AMBIGUITY-AWARE-PROGRAM-REPAIR-V11'
OLD_SOURCE='runtime/yado_bounded_compositional_program_repair_v3.py'
NEW_SOURCE='runtime/yado_ambiguity_aware_program_repair_v11.py'
NEXT='LTI_CODE_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V5'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);core=load(CORE);ledger=load(LEDGER);state=load(STATE);meta=load(META);admit=load(ADMIT)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['CODE_PLATEAU_CANONICAL_INTEGRATION_V2']:raise RuntimeError('UNEXPECTED_FRONTIER')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
if admit.get('status')!='PASS_CODE_PLATEAU_FRESH_ADMISSION_V9':raise RuntimeError('FRESH_ADMISSION_NOT_PASS')
if meta.get('state')!='AUTHORIZED_FOR_SHADOW_ADMISSION':raise RuntimeError('CANDIDATE_NOT_AUTHORIZED')
if fsha(SRC)!=meta.get('candidate_source_sha256'):raise RuntimeError('SOURCE_DRIFT')
if admit.get('candidate_digest')!=meta.get('candidate_digest'):raise RuntimeError('ADMISSION_CANDIDATE_DRIFT')
arch_sha=fsha(ARCH)

TARGET.write_text(SRC.read_text(encoding='utf-8'),encoding='utf-8')
src=UNIFIED.read_text(encoding='utf-8')
old_import='from yado_bounded_compositional_program_repair_v3 import BoundedCompositionalProgramRepairV3'
new_import='from yado_ambiguity_aware_program_repair_v11 import AmbiguityAwareProgramRepairV11'
if old_import not in src:raise RuntimeError('OLD_IMPORT_ANCHOR_MISSING')
patched=src.replace(old_import,new_import)
patched=patched.replace(
 '        self.bounded_program_repair=BoundedCompositionalProgramRepairV3',
 '        self.bounded_program_repair=AmbiguityAwareProgramRepairV11'
)
patch_ok=(patched.count(new_import)==1 and
          patched.count('self.bounded_program_repair=AmbiguityAwareProgramRepairV11')==1 and
          old_import not in patched)

new_core=copy.deepcopy(core);new_core.pop('core_digest',None)
think=next(x for x in new_core['planes'] if x.get('plane_id')=='THINKING_AND_PLANNING')
repair=next(x for x in new_core['planes'] if x.get('plane_id')=='SELF_AUDIT_AND_REPAIR')
think['active_components']=[x for x in think.get('active_components',[]) if x!=OLD]
think['active_components']=sorted(set(think['active_components']+[CID]))
think['responsibilities']=sorted(set(think.get('responsibilities',[])+[
 'ambiguity_aware_program_repair','evidence_guided_structural_synthesis',
 'recursive_partitioned_patch_synthesis','fail_closed_underdetermined_patch_withhold'
]))
repair['active_components']=[x for x in repair.get('active_components',[]) if x!=OLD]
repair['active_components']=sorted(set(repair['active_components']+[CID]))
repair['responsibilities']=sorted(set(repair.get('responsibilities',[])+[
 'ambiguity_aware_self_code_candidate_repair','evidence_resolution_before_commit',
 'support_ranked_branch_model_selection','observed_boundary_split_policy'
]))
new_core['active_runtime_sources']=sorted(set(
 [x for x in new_core.get('active_runtime_sources',[]) if x!=OLD_SOURCE]+[NEW_SOURCE]
))
new_core.setdefault('superseded_components',[])
if not any(x.get('component_id')==OLD and x.get('superseded_by')==CID for x in new_core['superseded_components']):
    new_core['superseded_components'].append({
      'component_id':OLD,'superseded_by':CID,
      'reason':'CODE_PLATEAU_COUNTEREXAMPLES_REQUIRED_STRUCTURAL_SYNTHESIS_RECURSIVE_PARTITION_SUPPORT_RANKING_AND_AMBIGUITY_WITHHOLD',
      'historical_evidence_retained':True
    })
new_core['program_execution']={
 'component_id':CID,
 'candidate_digest':meta['candidate_digest'],
 'source_sha256':fsha(TARGET),
 'fresh_admission_receipt_sha256':admit['receipt_sha256'],
 'fresh_score':admit['fresh_score'],
 'causal_ambiguity_ablation':admit.get('causal',{}).get('ambiguity_ablation') is True,
 'compute_contract':meta['compute_contract'],
 'mode':'ACTIVE_AMBIGUITY_AWARE_BOUNDED_SINGLE_FUNCTION_REPAIR',
 'self_repair_binding':'ACTIVE_SELF_AUDIT_AND_REPAIR_PLANE',
 'ambiguity_policy':'WITHHOLD_IF_TRAIN_EQUIVALENT_THRESHOLDS_DIVERGE_ON_UNOBSERVED_GAP',
 'supersedes':OLD,
 'gate_run_id':str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
}
new_core['current_frontier']=NEXT

tmp=ROOT/'_unified_code_v11_candidate.py';tmp.write_text(patched,encoding='utf-8')
api_ok=audit_ok=ambiguity_ok=resolved_ok=regression_ok=False
try:
    sp=importlib.util.spec_from_file_location('_unified_code_v11_candidate',tmp)
    mod=importlib.util.module_from_spec(sp);sys.modules[sp.name]=mod;sp.loader.exec_module(mod)
    obj=mod.UnifiedYADOCoreV1(REPO)
    audit_ok=obj.audit().get('pass') is True

    amb=[((-7,),-14),((-4,),-8),((0,),0),((1,),1),((4,),13),((8,),25)]
    ra=obj.repair_program('def f(x):\n    return x\n','f',amb,max_candidates=24000)
    ambiguity_ok=ra.get('source') is None and ra.get('reason')=='AMBIGUOUS_UNSEEN_THRESHOLD'

    resolved=amb+[((2,),2),((3,),3)]
    rr=obj.repair_program('def f(x):\n    return x\n','f',resolved,max_candidates=24000)
    resolved_ok=bool(rr.get('source')) and all(
      obj.execute_program_task(rr['source'],'f',args)==exp
      for args,exp in [((-9,),-18),((2,),2),((3,),3),((5,),16),((10,),31)]
    )

    two=[((1,2),6),((2,4),9),((-2,3),4),((0,0),3)]
    rt=obj.repair_program('def f(x,y):\n    return x-y+1\n','f',two,max_candidates=24000)
    regression_ok=bool(rt.get('source')) and all(
      obj.execute_program_task(rt['source'],'f',args)==exp
      for args,exp in [((5,6),14),((-3,-4),-4),((0,7),10)]
    )
    api_ok=ambiguity_ok and resolved_ok and regression_ok
finally:
    try:tmp.unlink()
    except FileNotFoundError:pass

checks={
 'fresh_admission_all_checks':all(admit.get('checks',{}).values()),
 'fresh_score_one':float(admit.get('fresh_score',0))>=.99,
 'candidate_source_exact':fsha(TARGET)==meta.get('candidate_source_sha256'),
 'unified_patch_exact':patch_ok,
 'ambiguity_withhold_probe':ambiguity_ok,
 'resolved_commit_probe':resolved_ok,
 'two_edit_regression_probe':regression_ok,
 'unified_api_probe':api_ok,
 'unified_audit_pass':audit_ok,
 'old_component_removed_from_thinking':OLD not in think.get('active_components',[]),
 'old_component_removed_from_self_repair':OLD not in repair.get('active_components',[]),
 'v11_active_in_thinking':CID in think.get('active_components',[]),
 'v11_active_in_self_repair':CID in repair.get('active_components',[]),
 'old_runtime_source_removed':OLD_SOURCE not in new_core.get('active_runtime_sources',[]),
 'new_runtime_source_active':NEW_SOURCE in new_core.get('active_runtime_sources',[]),
 'architecture_byte_identical':fsha(ARCH)==arch_sha,
 'g3_not_started':head.get('g3_genesis_performed') is False and core.get('g3_genesis_performed') is False
}
passed=all(checks.values())
post_head=post_core=None
if passed:
    UNIFIED.write_text(patched,encoding='utf-8');runtime_sha=fsha(UNIFIED)
    new_core['runtime_sha256']=runtime_sha
    new_core['core_digest']=h(new_core)
    CORE.write_text(json.dumps(new_core,indent=2,sort_keys=True)+'\n')

    new_head=copy.deepcopy(head);new_head.pop('canonical_head_digest',None)
    new_head['new_capabilities']=sorted(set(new_head.get('new_capabilities',[])+[CID]))
    new_head['unified_core']['runtime_sha256']=runtime_sha
    new_head['unified_core']['core_digest']=new_core['core_digest']
    new_head['unified_core']['bounded_program_repair_source_sha256']=fsha(TARGET)
    new_head['unified_core']['code_self_repair_component']=CID
    new_head['current_frontier']=NEXT
    new_head['canonical_head_digest']=h(new_head)
    HEAD.write_text(json.dumps(new_head,indent=2,sort_keys=True)+'\n')
    post_head=new_head['canonical_head_digest'];post_core=new_core['core_digest']

    state['candidate_history'].append({
      'round':state.get('round',18),'plane':'CODE','candidate_digest':meta['candidate_digest'],
      'component_id':CID,'status':'CANONICAL_ACTIVE','fresh_score':admit['fresh_score'],
      'causal_drop':1.0,'gate_run_id':str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
    })
    state['next_required_capability']=NEXT
    state['status']='PLATEAU_SEARCH'
    state['plateau_streak']=0
    state['state_digest']=h({k:v for k,v in state.items() if k!='state_digest'})
    STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')
    status='PASS_CODE_PLATEAU_CANONICAL_INTEGRATION_V2';next_cap=NEXT
else:
    try:TARGET.unlink()
    except FileNotFoundError:pass
    status='WITHHOLD_CODE_PLATEAU_CANONICAL_INTEGRATION_V2';next_cap='CODE_PLATEAU_SELF_EVOLUTION_V10'

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.code_plateau_canonical_integration.v2','status':status,
 'component_id':CID,'superseded_component_id':OLD,'candidate_digest':meta['candidate_digest'],
 'fresh_admission_receipt_sha256':admit['receipt_sha256'],'checks':checks,'architecture_sha256':arch_sha,
 'architecture_mutation':False,'canonical_mutation':passed,'promotion_applied':False,'generation_transition':False,
 'g3_genesis_performed':False,'post_head_digest':post_head,'post_core_digest':post_core,'next_required_capability':next_cap,
 'semantic_boundary':'SAME-G2 REPLACEMENT OF COMPOSITIONAL PROGRAM REPAIR V3 BY AMBIGUITY-AWARE V11 AFTER INDEPENDENT FRESH ADMISSION. STILL BOUNDED TO ONE SAFE PYTHON FUNCTION; CANONICAL CHANGES REQUIRE GATED RECEIPTS.'
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_CODE_PLATEAU_CANONICAL_INTEGRATION_V2",
 'event_type':'FIXED_ARCHITECTURE_CODE_REPAIR_IMPLEMENTATION_REPLACEMENT','status':'PASS' if passed else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'CODE_PLATEAU_CANONICAL_INTEGRATION_V2',
 'effect':'PROGRAM_REPAIR_V3_SUPERSEDED_BY_AMBIGUITY_AWARE_V11' if passed else 'CODE_V11_INTEGRATION_WITHHELD',
 'source_path':f'receipts/yado-code-plateau-canonical-integration-v2-run-{run_id}.json','source_digest':receipt['receipt_sha256'],
 'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':passed,
 'promotion_applied':False,'generation_transition':False}
if passed:
    e['previous_head_digest']=ledger['current_head_digest'];e['new_head_digest']=post_head
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
if passed:ledger['current_head_digest']=post_head
ledger['open_deficits']=[next_cap]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({'status':status,'checks':checks,'post_head_digest':post_head,'architecture_sha256':arch_sha,
 'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('CODE_PLATEAU_CANONICAL_INTEGRATION_V2_WITHHELD')
