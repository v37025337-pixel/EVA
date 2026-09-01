from __future__ import annotations
from pathlib import Path
from fractions import Fraction
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
CAND_SRC=REPO/'candidates'/'g2-self-evolution'/'budget_adaptive_compositional_logic_v2.py'
CAND_META=REPO/'candidates'/'g2-self-evolution'/'budget_adaptive_compositional_logic_v2.json'
ADMIT=REPO/'receipts'/'yado-logic-plateau-fresh-admission-v1-run-33476434272.json'
TARGET=REPO/'runtime'/'yado_budget_adaptive_compositional_logic_v2.py'
OUT=ROOT/'yado_logic_plateau_canonical_integration_v1_receipt.json'
OLD='ALG-G2-BOUNDED-COMPOSITIONAL-LOGIC-V1'
CID='ALG-G2-BUDGET-ADAPTIVE-COMPOSITIONAL-LOGIC-V2'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);core=load(CORE);ledger=load(LEDGER);state=load(STATE);meta=load(CAND_META);admit=load(ADMIT)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['LOGIC_PLATEAU_CANONICAL_INTEGRATION_V1']:raise RuntimeError('UNEXPECTED_FRONTIER')
if admit.get('status')!='PASS_LOGIC_PLATEAU_FRESH_ADMISSION_V1':raise RuntimeError('FRESH_ADMISSION_NOT_PASS')
if meta.get('state')!='AUTHORIZED_FOR_SHADOW_ADMISSION':raise RuntimeError('CANDIDATE_NOT_AUTHORIZED')
if fsha(CAND_SRC)!=meta.get('candidate_source_sha256'):raise RuntimeError('SOURCE_DRIFT')
if admit.get('candidate_source_sha256')!=meta.get('candidate_source_sha256'):raise RuntimeError('ADMISSION_SOURCE_DRIFT')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
arch_sha=fsha(ARCH)

TARGET.write_text(CAND_SRC.read_text(encoding='utf-8'),encoding='utf-8')

src=UNIFIED.read_text(encoding='utf-8')
old_import='from yado_bounded_compositional_logic_v1 import BoundedCompositionalLogicV1'
new_import='from yado_budget_adaptive_compositional_logic_v2 import BudgetAdaptiveCompositionalLogicV2'
if new_import not in src:
    if old_import not in src:raise RuntimeError('UNIFIED_LOGIC_IMPORT_ANCHOR_MISSING')
    patched=src.replace(old_import,new_import)
else:
    patched=src
patched=patched.replace('        self.compositional_logic=BoundedCompositionalLogicV1','        self.compositional_logic=BudgetAdaptiveCompositionalLogicV2')
patched=patched.replace('    def fit_polynomial_logic(self,rows:list[dict[str,Any]],max_degree:int=3)->dict[str,Any]:',
                        '    def fit_polynomial_logic(self,rows:list[dict[str,Any]],max_degree:int=8)->dict[str,Any]:')
patch_ok=(
 patched.count(new_import)==1 and
 patched.count('self.compositional_logic=BudgetAdaptiveCompositionalLogicV2')==1 and
 'self.compositional_logic=BoundedCompositionalLogicV1' not in patched
)

new_core=copy.deepcopy(core);new_core.pop('core_digest',None)
plane=next(x for x in new_core['planes'] if x.get('plane_id')=='LOGIC')
plane['active_components']=[x for x in plane.get('active_components',[]) if x!=OLD]
plane['active_components']=sorted(set(plane['active_components']+[CID]))
plane['responsibilities']=sorted(set(plane.get('responsibilities',[])+[
 'work_budget_adaptive_symmetric_logic',
 'term_budget_exact_polynomial_induction',
 'compute_budget_fail_closed_logic'
]))
sources=[x for x in new_core.get('active_runtime_sources',[]) if x!='runtime/yado_bounded_compositional_logic_v1.py']
new_core['active_runtime_sources']=sorted(set(sources+['runtime/yado_budget_adaptive_compositional_logic_v2.py']))
new_core.setdefault('superseded_components',[])
if not any(x.get('component_id')==OLD for x in new_core['superseded_components']):
    new_core['superseded_components'].append({
      'component_id':OLD,'superseded_by':CID,
      'reason':'PLATEAU_CONTRACT_FRONTIER_REPLACED_FIXED_DIMENSION_CAPS_WITH_TOTAL_WORK_BUDGETS',
      'historical_evidence_retained':True
    })
new_core['logic_plateau_v2']={
 'component_id':CID,'candidate_digest':meta['candidate_digest'],'source_sha256':fsha(TARGET),
 'fresh_admission_receipt_sha256':admit['receipt_sha256'],'fresh_score':admit['fresh_score'],
 'causal':admit['causal'],'compute_contract':meta['compute_contract'],'architecture_sha256':arch_sha,
 'mode':'ACTIVE_FIXED_ARCHITECTURE_WORK_BUDGET_ADAPTIVE_LOGIC',
 'supersedes':OLD,'gate_run_id':str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
}
if 'logic_ceiling' in new_core:new_core['logic_ceiling']['status']='SUPERSEDED_BY_LOGIC_PLATEAU_V2'
new_core['current_frontier']='LTI_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V2'

tmp=ROOT/'_unified_logic_v2_candidate.py';tmp.write_text(patched,encoding='utf-8')
try:
    sp=importlib.util.spec_from_file_location('_unified_logic_v2_candidate',tmp)
    mod=importlib.util.module_from_spec(sp);sys.modules[sp.name]=mod;sp.loader.exec_module(mod)
    obj=mod.UnifiedYADOCoreV1(REPO);audit=obj.audit()
    rows=[]
    n=20
    for c in range(n+1):
        x={f'q{i:02d}':i<c for i in range(n)}
        rows.append({'input':x,'expected':'YES' if c%3==2 else 'NO'})
    bm=obj.learn_symmetric_logic(rows)
    bool_ok=all(obj.predict_symmetric_logic(bm,z['input'])==z['expected'] for z in rows)
    pts=[(x,y) for x in range(-3,4) for y in range(-3,4)]
    pr=[{'x':x,'y':y,'expected':x**4+2*x*y+y*y+1} for x,y in pts]
    pm=obj.fit_polynomial_logic(pr,max_degree=4)
    poly_ok=pm.get('kind')!='WITHHOLD' and all(obj.predict_polynomial_logic(pm,z['x'],z['y'])==Fraction(z['expected']) for z in pr)
    api_ok=bool_ok and poly_ok
finally:
    try:tmp.unlink()
    except FileNotFoundError:pass

checks={
 'fresh_admission_all_checks':all(admit.get('checks',{}).values()),
 'fresh_score_one':float(admit.get('fresh_score',0))>=.99,
 'candidate_source_exact':fsha(TARGET)==meta.get('candidate_source_sha256'),
 'unified_patch_exact':patch_ok,
 'unified_api_fresh_probe':api_ok,
 'unified_audit_pass':audit.get('pass') is True,
 'old_component_removed_from_active_logic':OLD not in plane.get('active_components',[]),
 'new_component_active_logic':CID in plane.get('active_components',[]),
 'old_source_removed_from_active_sources':'runtime/yado_bounded_compositional_logic_v1.py' not in new_core.get('active_runtime_sources',[]),
 'architecture_file_immutable':fsha(ARCH)==arch_sha,
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
    new_head['unified_core']['runtime_sha256']=runtime_sha;new_head['unified_core']['core_digest']=new_core['core_digest']
    new_head['unified_core']['logic_ceiling_source_sha256']=fsha(TARGET)
    new_head['unified_core']['logic_active_component']=CID
    new_head['current_frontier']='LTI_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V2'
    new_head['canonical_head_digest']=h(new_head);HEAD.write_text(json.dumps(new_head,indent=2,sort_keys=True)+'\n')
    post_head=new_head['canonical_head_digest'];post_core=new_core['core_digest']
    state['candidate_history'].append({'round':state.get('round',8),'plane':'LOGIC','candidate_digest':meta['candidate_digest'],'status':'CANONICAL_ACTIVE','fresh_score':admit['fresh_score'],'gate_run_id':str(os.getenv('GITHUB_RUN_ID') or 'LOCAL'),'component_id':CID})
    state['next_required_capability']='LTI_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V2'
    state['status']='PLATEAU_SEARCH'
    state['state_digest']=h({k:v for k,v in state.items() if k!='state_digest'})
    STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')
    status='PASS_LOGIC_PLATEAU_CANONICAL_INTEGRATION_V1';next_cap='LTI_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V2'
else:
    try:TARGET.unlink()
    except FileNotFoundError:pass
    status='WITHHOLD_LOGIC_PLATEAU_CANONICAL_INTEGRATION_V1';next_cap='LOGIC_PLATEAU_SELF_EVOLUTION_V2'

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.logic_plateau_canonical_integration.v1','status':status,'component_id':CID,'superseded_component_id':OLD,
 'candidate_digest':meta['candidate_digest'],'fresh_admission_receipt':admit['receipt_sha256'],'checks':checks,'architecture_sha256':arch_sha,
 'architecture_mutation':False,'canonical_mutation':passed,'promotion_applied':False,'generation_transition':False,'g3_genesis_performed':False,
 'post_head_digest':post_head,'post_core_digest':post_core,'next_required_capability':next_cap,
 'semantic_boundary':'SAME-G2 REPLACEMENT OF ACTIVE LOGIC IMPLEMENTATION V1 BY WORK-BUDGET-ADAPTIVE V2 INSIDE THE EXISTING LOGIC PLANE. GRAPH TOPOLOGY REMAINS BYTE-IDENTICAL.'}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_LOGIC_PLATEAU_CANONICAL_INTEGRATION_V1",
 'event_type':'FIXED_ARCHITECTURE_LOGIC_IMPLEMENTATION_REPLACEMENT','status':'PASS' if passed else 'WITHHOLD','generation':ledger['current_head'],
 'deficit':'LOGIC_PLATEAU_CANONICAL_INTEGRATION_V1','effect':'ACTIVE_LOGIC_V1_SUPERSEDED_BY_WORK_BUDGET_V2' if passed else 'LOGIC_V2_INTEGRATION_WITHHELD',
 'source_path':f'receipts/yado-logic-plateau-canonical-integration-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':passed,'promotion_applied':False,'generation_transition':False}
if passed:e['previous_head_digest']=ledger['current_head_digest'];e['new_head_digest']=post_head
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
if passed:ledger['current_head_digest']=post_head
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':status,'checks':checks,'post_head_digest':post_head,'architecture_sha256':arch_sha,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('LOGIC_PLATEAU_CANONICAL_INTEGRATION_WITHHELD')
