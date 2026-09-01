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
SRC=REPO/'candidates'/'g2-self-evolution'/'bounded_compositional_program_repair_v3.py'
META=REPO/'candidates'/'g2-self-evolution'/'bounded_compositional_program_repair_v3.json'
ADMIT=REPO/'receipts'/'yado-code-plateau-fresh-readmission-v1-run-33486231448.json'
TARGET=REPO/'runtime'/'yado_bounded_compositional_program_repair_v3.py'
OUT=ROOT/'yado_code_plateau_canonical_integration_v1_receipt.json'

OLD='ALG-G2-BOUNDED-PROGRAM-REPAIR-V2'
CID='ALG-G2-BOUNDED-COMPOSITIONAL-PROGRAM-REPAIR-V3'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);core=load(CORE);ledger=load(LEDGER);state=load(STATE);meta=load(META);admit=load(ADMIT)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['CODE_PLATEAU_CANONICAL_INTEGRATION_V1']:raise RuntimeError('UNEXPECTED_FRONTIER')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
if admit.get('status')!='PASS_CODE_PLATEAU_FRESH_READMISSION_V1':raise RuntimeError('READMISSION_NOT_PASS')
if meta.get('state')=='WITHHOLD' and admit.get('classification')!='PRIOR_FRESH_ORACLE_OUTSIDE_DECLARED_TWO_EDIT_TARGET_CLASS':raise RuntimeError('WITHHOLD_NOT_SUPERSEDED_BY_VALID_READMISSION')
if meta.get('state') not in {'AUTHORIZED_FOR_SHADOW_ADMISSION','WITHHOLD'}:raise RuntimeError('CANDIDATE_STATE_INVALID')
if fsha(SRC)!=meta.get('candidate_source_sha256'):raise RuntimeError('SOURCE_DRIFT')
if admit.get('candidate_digest')!=meta.get('candidate_digest'):raise RuntimeError('ADMISSION_CANDIDATE_DRIFT')
arch_sha=fsha(ARCH)

TARGET.write_text(SRC.read_text(encoding='utf-8'),encoding='utf-8')

src=UNIFIED.read_text(encoding='utf-8')
old_import='from yado_bounded_program_repair_v2 import BoundedProgramRepairV1'
new_import='from yado_bounded_compositional_program_repair_v3 import BoundedCompositionalProgramRepairV3'
if new_import not in src:
    if old_import not in src:raise RuntimeError('PROGRAM_REPAIR_IMPORT_ANCHOR_MISSING')
    patched=src.replace(old_import,new_import)
else:
    patched=src
patched=patched.replace(
    '        self.bounded_program_repair=BoundedProgramRepairV1',
    '        self.bounded_program_repair=BoundedCompositionalProgramRepairV3'
)
patch_ok=(
    patched.count(new_import)==1 and
    patched.count('self.bounded_program_repair=BoundedCompositionalProgramRepairV3')==1 and
    old_import not in patched
)

new_core=copy.deepcopy(core);new_core.pop('core_digest',None)
think=next(x for x in new_core['planes'] if x.get('plane_id')=='THINKING_AND_PLANNING')
think['active_components']=[x for x in think.get('active_components',[]) if x!=OLD]
think['active_components']=sorted(set(think['active_components']+[CID]))
think['responsibilities']=sorted(set(think.get('responsibilities',[])+[
 'bounded_compositional_program_repair','two_edit_ast_search','safe_structural_expression_repair'
]))
repair=next(x for x in new_core['planes'] if x.get('plane_id')=='SELF_AUDIT_AND_REPAIR')
repair['active_components']=sorted(set(repair.get('active_components',[])+[CID]))
repair['responsibilities']=sorted(set(repair.get('responsibilities',[])+[
 'bounded_self_code_candidate_repair','multi_edit_patch_synthesis','safe_structural_patch_synthesis',
 'repair_candidate_fail_closed_search_budget'
]))
sources=[x for x in new_core.get('active_runtime_sources',[]) if x!='runtime/yado_bounded_program_repair_v2.py']
new_core['active_runtime_sources']=sorted(set(sources+['runtime/yado_bounded_compositional_program_repair_v3.py']))
new_core.setdefault('superseded_components',[])
if not any(x.get('component_id')==OLD for x in new_core['superseded_components']):
    new_core['superseded_components'].append({
      'component_id':OLD,'superseded_by':CID,
      'reason':'CODE_PLATEAU_REQUIRED_COMPOSED_AST_EDITS_AND_SAFE_STRUCTURAL_REPAIR',
      'historical_evidence_retained':True
    })
new_core['program_execution']={
 'component_id':CID,
 'candidate_digest':meta['candidate_digest'],
 'source_sha256':fsha(TARGET),
 'fresh_admission_receipt_sha256':admit['receipt_sha256'],
 'fresh_score':admit['fresh_score'],
 'predecessor_ablation':admit['predecessor_ablation'],
 'causal_gap':admit['causal_gap'],
 'compute_contract':meta['compute_contract'],
 'mode':'ACTIVE_BOUNDED_COMPOSITIONAL_SINGLE_FUNCTION_REPAIR',
 'self_repair_binding':'ACTIVE_SELF_AUDIT_AND_REPAIR_PLANE',
 'supersedes':OLD,
 'gate_run_id':str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
}
new_core['current_frontier']='LTI_CODE_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V4'

tmp=ROOT/'_unified_code_v3_candidate.py';tmp.write_text(patched,encoding='utf-8')
api_ok=False;audit_ok=False
try:
    sp=importlib.util.spec_from_file_location('_unified_code_v3_candidate',tmp)
    mod=importlib.util.module_from_spec(sp);sys.modules[sp.name]=mod;sp.loader.exec_module(mod)
    obj=mod.UnifiedYADOCoreV1(REPO);audit_ok=obj.audit().get('pass') is True
    tr=[((1,2),6),((2,4),9),((-2,3),4),((0,0),3)]
    r=obj.repair_program('def f(x,y):\n    return x-y+1\n','f',tr,max_candidates=20000)
    two_ok=bool(r.get('source')) and all(obj.execute_program_task(r['source'],'f',args)==exp for args,exp in [((5,6),14),((-3,-4),-4)])
    tr2=[((-4,),0),((-1,),0),((0,),0),((2,),2),((8,),8)]
    r2=obj.repair_program('def f(x):\n    return x\n','f',tr2,max_candidates=20000)
    structural_ok=bool(r2.get('source')) and all(obj.execute_program_task(r2['source'],'f',args)==exp for args,exp in [((-9,),0),((4,),4)])
    api_ok=two_ok and structural_ok
finally:
    try:tmp.unlink()
    except FileNotFoundError:pass

checks={
 'fresh_readmission_all_checks':all(admit.get('checks',{}).values()),
 'fresh_score_one':float(admit.get('fresh_score',0))>=.99,
 'causal_gap_one':float(admit.get('causal_gap',0))>=.99,
 'candidate_source_exact':fsha(TARGET)==meta.get('candidate_source_sha256'),
 'unified_patch_exact':patch_ok,
 'unified_api_probe':api_ok,
 'unified_audit_pass':audit_ok,
 'old_program_repair_removed_from_thinking':OLD not in think.get('active_components',[]),
 'v3_active_in_thinking':CID in think.get('active_components',[]),
 'v3_bound_to_self_repair_plane':CID in repair.get('active_components',[]),
 'old_source_removed':'runtime/yado_bounded_program_repair_v2.py' not in new_core.get('active_runtime_sources',[]),
 'architecture_byte_identical':fsha(ARCH)==arch_sha,
 'head_ledger_coherent':ledger.get('current_head_digest')==head.get('canonical_head_digest'),
 'g3_not_started':head.get('g3_genesis_performed') is False and core.get('g3_genesis_performed') is False,
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
    new_head['unified_core']['bounded_program_repair_source_sha256']=fsha(TARGET)
    new_head['unified_core']['code_self_repair_component']=CID
    new_head['current_frontier']='LTI_CODE_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V4'
    new_head['canonical_head_digest']=h(new_head)
    HEAD.write_text(json.dumps(new_head,indent=2,sort_keys=True)+'\n')
    post_head=new_head['canonical_head_digest'];post_core=new_core['core_digest']
    state['candidate_history'].append({'round':state.get('round',15),'plane':'CODE','candidate_digest':meta['candidate_digest'],
      'component_id':CID,'status':'CANONICAL_ACTIVE','fresh_score':admit['fresh_score'],'causal_drop':admit['causal_gap'],
      'gate_run_id':str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')})
    state['next_required_capability']='LTI_CODE_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V4'
    state['status']='PLATEAU_SEARCH'
    state['state_digest']=h({k:v for k,v in state.items() if k!='state_digest'})
    STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')
    status='PASS_CODE_PLATEAU_CANONICAL_INTEGRATION_V1';next_cap='LTI_CODE_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V4'
else:
    try:TARGET.unlink()
    except FileNotFoundError:pass
    status='WITHHOLD_CODE_PLATEAU_CANONICAL_INTEGRATION_V1';next_cap='CODE_PLATEAU_SELF_EVOLUTION_V2'

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.code_plateau_canonical_integration.v1','status':status,
 'component_id':CID,'superseded_component_id':OLD,'candidate_digest':meta['candidate_digest'],
 'fresh_readmission_receipt_sha256':admit['receipt_sha256'],'checks':checks,'architecture_sha256':arch_sha,
 'architecture_mutation':False,'canonical_mutation':passed,'promotion_applied':False,'generation_transition':False,
 'g3_genesis_performed':False,'post_head_digest':post_head,'post_core_digest':post_core,'next_required_capability':next_cap,
 'semantic_boundary':'SAME-G2 REPLACEMENT OF ONE-EDIT PROGRAM REPAIR V2 BY BOUNDED COMPOSITIONAL V3, ALSO BOUND INTO SELF_AUDIT_AND_REPAIR. CANONICAL CODE CHANGES STILL REQUIRE EXTERNAL GATES/RECEIPTS/ROLLBACK.'
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_CODE_PLATEAU_CANONICAL_INTEGRATION_V1",
 'event_type':'FIXED_ARCHITECTURE_CODE_REPAIR_IMPLEMENTATION_REPLACEMENT','status':'PASS' if passed else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'CODE_PLATEAU_CANONICAL_INTEGRATION_V1',
 'effect':'PROGRAM_REPAIR_V2_SUPERSEDED_BY_COMPOSITIONAL_V3_AND_BOUND_TO_SELF_REPAIR' if passed else 'CODE_V3_INTEGRATION_WITHHELD',
 'source_path':f'receipts/yado-code-plateau-canonical-integration-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],
 'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':passed,'promotion_applied':False,'generation_transition':False}
if passed:e['previous_head_digest']=ledger['current_head_digest'];e['new_head_digest']=post_head
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
if passed:ledger['current_head_digest']=post_head
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':status,'checks':checks,'post_head_digest':post_head,'architecture_sha256':arch_sha,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('CODE_PLATEAU_CANONICAL_INTEGRATION_WITHHELD')
