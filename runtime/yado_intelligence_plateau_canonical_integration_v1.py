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
SRC=REPO/'candidates'/'g2-self-evolution'/'coverage_pruned_compositional_schema_router_v3.py'
META=REPO/'candidates'/'g2-self-evolution'/'coverage_pruned_compositional_schema_router_v3.json'
FUNC=REPO/'receipts'/'yado-intelligence-plateau-fresh-admission-v2-run-33477399296.json'
CAUSAL=REPO/'receipts'/'yado-intelligence-plateau-causal-readmission-v1-run-33477648759.json'
TARGET=REPO/'runtime'/'yado_coverage_pruned_compositional_schema_router_v3.py'
OUT=ROOT/'yado_intelligence_plateau_canonical_integration_v1_receipt.json'

OLD='ALG-G2-BOUNDED-COMPOSITIONAL-SCHEMA-ROUTER-V1'
MID='ALG-G2-BUDGET-ADAPTIVE-COMPOSITIONAL-SCHEMA-ROUTER-V2'
CID='ALG-G2-COVERAGE-PRUNED-COMPOSITIONAL-SCHEMA-ROUTER-V3'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p): return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);core=load(CORE);ledger=load(LEDGER);state=load(STATE)
meta=load(META);functional=load(FUNC);causal=load(CAUSAL)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['INTELLIGENCE_PLATEAU_CANONICAL_INTEGRATION_V1']: raise RuntimeError('UNEXPECTED_FRONTIER')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'): raise RuntimeError('HEAD_LEDGER_MISMATCH')
if meta.get('state')!='AUTHORIZED_FOR_SHADOW_ADMISSION': raise RuntimeError('CANDIDATE_NOT_AUTHORIZED')
if fsha(SRC)!=meta.get('candidate_source_sha256'): raise RuntimeError('SOURCE_DRIFT')
if causal.get('status')!='PASS_INTELLIGENCE_PLATEAU_CAUSAL_READMISSION_V1': raise RuntimeError('CAUSAL_READMISSION_NOT_PASS')
if causal.get('candidate_digest')!=meta.get('candidate_digest'): raise RuntimeError('CAUSAL_CANDIDATE_MISMATCH')
fresh_vals=list((functional.get('fresh_families') or {}).values())
if not fresh_vals or min(float(x) for x in fresh_vals)<.99: raise RuntimeError('FUNCTIONAL_FRESH_NOT_GREEN')
arch_sha=fsha(ARCH);head_sha=fsha(HEAD)

TARGET.write_text(SRC.read_text(encoding='utf-8'),encoding='utf-8')

src=UNIFIED.read_text(encoding='utf-8')
old_import='from yado_bounded_compositional_schema_router_v1 import BoundedCompositionalSchemaRouterV1'
new_import='from yado_coverage_pruned_compositional_schema_router_v3 import CoveragePrunedCompositionalSchemaRouterV3'
if new_import not in src:
    if old_import not in src: raise RuntimeError('UNIFIED_ROUTER_IMPORT_ANCHOR_MISSING')
    patched=src.replace(old_import,new_import)
else:
    patched=src
patched=patched.replace(
    '        self.compositional_schema_router=BoundedCompositionalSchemaRouterV1',
    '        self.compositional_schema_router=CoveragePrunedCompositionalSchemaRouterV3'
)
patch_ok=(
    patched.count(new_import)==1 and
    patched.count('self.compositional_schema_router=CoveragePrunedCompositionalSchemaRouterV3')==1 and
    old_import not in patched
)

new_core=copy.deepcopy(core);new_core.pop('core_digest',None)
plane=next(x for x in new_core['planes'] if x.get('plane_id')=='INTELLIGENCE_AND_META_SELECTION')
plane['active_components']=[x for x in plane.get('active_components',[]) if x!=OLD]
plane['active_components']=sorted(set(plane['active_components']+[CID]))
plane['responsibilities']=sorted(set(plane.get('responsibilities',[])+[
    'work_budget_adaptive_capability_routing',
    'bounded_pairwise_trigger_composition',
    'positive_cover_trigger_pruning',
    'distribution_shift_spurious_trigger_suppression'
]))
sources=[x for x in new_core.get('active_runtime_sources',[]) if x!='runtime/yado_bounded_compositional_schema_router_v1.py']
new_core['active_runtime_sources']=sorted(set(sources+['runtime/yado_coverage_pruned_compositional_schema_router_v3.py']))
new_core.setdefault('superseded_components',[])
if not any(x.get('component_id')==OLD for x in new_core['superseded_components']):
    new_core['superseded_components'].append({
        'component_id':OLD,'superseded_by':CID,
        'reason':'PLATEAU_FRONTIER_REQUIRED_WORK_BUDGET_FIELDS_PAIRWISE_COMPOSITION_AND_COVERAGE_PRUNING',
        'historical_evidence_retained':True
    })
if not any(x.get('component_id')==MID for x in new_core['superseded_components']):
    new_core['superseded_components'].append({
        'component_id':MID,'superseded_by':CID,
        'reason':'SHADOW_STEPPING_STONE_REPAIRED_AFTER_WIDTH22_DISTRIBUTION_SHIFT_COUNTEREXAMPLE',
        'historical_evidence_retained':True,'was_canonical':False
    })
new_core['intelligence_plateau_v3']={
    'component_id':CID,
    'candidate_digest':meta['candidate_digest'],
    'source_sha256':fsha(TARGET),
    'compute_contract':meta['compute_contract'],
    'functional_fresh_receipt_sha256':functional['receipt_sha256'],
    'functional_fresh_score':functional['fresh_score'],
    'causal_readmission_receipt_sha256':causal['receipt_sha256'],
    'causal_differentiator':causal['differentiator'],
    'repair_of_receipt':meta.get('repair_of_receipt'),
    'mode':'ACTIVE_FIXED_ARCHITECTURE_COVERAGE_PRUNED_BUDGET_ADAPTIVE_ROUTING',
    'supersedes':OLD,
    'gate_run_id':str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
}
if 'intelligence_ceiling' in new_core:
    new_core['intelligence_ceiling']['status']='SUPERSEDED_BY_INTELLIGENCE_PLATEAU_V3'
new_core['current_frontier']='LTI_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V3'

tmp=ROOT/'_unified_intelligence_v3_candidate.py'
tmp.write_text(patched,encoding='utf-8')
api_ok=False;audit_ok=False
try:
    sp=importlib.util.spec_from_file_location('_unified_intelligence_v3_candidate',tmp)
    mod=importlib.util.module_from_spec(sp);sys.modules[sp.name]=mod;sp.loader.exec_module(mod)
    obj=mod.UnifiedYADOCoreV1(REPO)
    audit_ok=obj.audit().get('pass') is True
    cases=[]
    for a in (False,True):
      for b in (False,True):
        for s in (False,True):
          out=[]
          if s or (a and b): out.append('REL')
          if not out: out=['BASE']
          for _ in range(8): cases.append({'input':{'a':a,'b':b,'s':s},'expected':tuple(out)})
    rm=obj.fit_compositional_capability_router(cases,'BASE')
    route_ok=(
      obj.route_capability_set(rm,{'a':True,'b':True,'s':False})==('REL',) and
      obj.route_capability_set(rm,{'a':False,'b':False,'s':False})==('BASE',)
    )
    refs=[{'a':False,'b':False},{'a':True,'b':False},{'a':False,'b':True},{'a':True,'b':True}]
    aliases=[{'u':z['a'],'v':z['b']} for z in refs]
    al=obj.fit_capability_schema_alignment(refs,aliases)
    align_ok=al.get('kind')=='EXACT_PAIRED_SCHEMA_ALIGNMENT_V3'
    api_ok=route_ok and align_ok
finally:
    try: tmp.unlink()
    except FileNotFoundError: pass

checks={
    'functional_fresh_all_green':bool(fresh_vals) and min(float(x) for x in fresh_vals)>=.99,
    'causal_readmission_pass':causal.get('status')=='PASS_INTELLIGENCE_PLATEAU_CAUSAL_READMISSION_V1',
    'causal_gap_positive':float(causal.get('differentiator',{}).get('gap',0))>=.10,
    'candidate_source_exact':fsha(TARGET)==meta.get('candidate_source_sha256'),
    'unified_patch_exact':patch_ok,
    'unified_api_probe':api_ok,
    'unified_audit_pass':audit_ok,
    'old_active_router_removed':OLD not in plane.get('active_components',[]),
    'v3_active_router_present':CID in plane.get('active_components',[]),
    'old_source_removed':'runtime/yado_bounded_compositional_schema_router_v1.py' not in new_core.get('active_runtime_sources',[]),
    'architecture_byte_identical':fsha(ARCH)==arch_sha,
    'head_ledger_coherent':ledger.get('current_head_digest')==head.get('canonical_head_digest'),
    'g3_not_started':head.get('g3_genesis_performed') is False and core.get('g3_genesis_performed') is False,
}
passed=all(checks.values())
post_head=post_core=None
if passed:
    UNIFIED.write_text(patched,encoding='utf-8')
    runtime_sha=fsha(UNIFIED)
    new_core['runtime_sha256']=runtime_sha
    new_core['core_digest']=h(new_core)
    CORE.write_text(json.dumps(new_core,indent=2,sort_keys=True)+'\n')
    new_head=copy.deepcopy(head);new_head.pop('canonical_head_digest',None)
    new_head['new_capabilities']=sorted(set(new_head.get('new_capabilities',[])+[CID]))
    new_head['unified_core']['runtime_sha256']=runtime_sha
    new_head['unified_core']['core_digest']=new_core['core_digest']
    new_head['unified_core']['intelligence_ceiling_source_sha256']=fsha(TARGET)
    new_head['unified_core']['intelligence_active_router_component']=CID
    new_head['current_frontier']='LTI_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V3'
    new_head['canonical_head_digest']=h(new_head)
    HEAD.write_text(json.dumps(new_head,indent=2,sort_keys=True)+'\n')
    post_head=new_head['canonical_head_digest'];post_core=new_core['core_digest']
    state['candidate_history'].append({
        'round':state.get('round',12),'plane':'INTELLIGENCE',
        'candidate_digest':meta['candidate_digest'],'component_id':CID,
        'status':'CANONICAL_ACTIVE',
        'fresh_score':functional['fresh_score'],
        'causal_drop':causal['differentiator']['gap'],
        'gate_run_id':str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
    })
    state['next_required_capability']='LTI_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V3'
    state['status']='PLATEAU_SEARCH'
    state['state_digest']=h({k:v for k,v in state.items() if k!='state_digest'})
    STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')
    status='PASS_INTELLIGENCE_PLATEAU_CANONICAL_INTEGRATION_V1'
    next_cap='LTI_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V3'
else:
    try: TARGET.unlink()
    except FileNotFoundError: pass
    status='WITHHOLD_INTELLIGENCE_PLATEAU_CANONICAL_INTEGRATION_V1'
    next_cap='INTELLIGENCE_PLATEAU_SELF_EVOLUTION_V3'

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
 'schema':'yado.g2.intelligence_plateau_canonical_integration.v1',
 'status':status,'component_id':CID,'superseded_component_id':OLD,
 'candidate_digest':meta['candidate_digest'],
 'functional_fresh_receipt_sha256':functional['receipt_sha256'],
 'causal_readmission_receipt_sha256':causal['receipt_sha256'],
 'checks':checks,'architecture_sha256':arch_sha,
 'architecture_mutation':False,'canonical_mutation':passed,'promotion_applied':False,
 'generation_transition':False,'g3_genesis_performed':False,
 'post_head_digest':post_head,'post_core_digest':post_core,
 'next_required_capability':next_cap,
 'semantic_boundary':'SAME-G2 REPLACEMENT OF ACTIVE INTELLIGENCE ROUTER V1 BY COVERAGE-PRUNED WORK-BUDGET V3. V2 REMAINS SHADOW EXPERIENCE. GRAPH TOPOLOGY IS UNCHANGED.'
}
receipt['receipt_sha256']=h(receipt)
OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),
 'event_id':f"E{len(ledger['events'])+1:04d}_G2_INTELLIGENCE_PLATEAU_CANONICAL_INTEGRATION_V1",
 'event_type':'FIXED_ARCHITECTURE_INTELLIGENCE_IMPLEMENTATION_REPLACEMENT',
 'status':'PASS' if passed else 'WITHHOLD','generation':ledger['current_head'],
 'deficit':'INTELLIGENCE_PLATEAU_CANONICAL_INTEGRATION_V1',
 'effect':'ACTIVE_INTELLIGENCE_ROUTER_V1_SUPERSEDED_BY_COVERAGE_PRUNED_V3' if passed else 'INTELLIGENCE_V3_INTEGRATION_WITHHELD',
 'source_path':f'receipts/yado-intelligence-plateau-canonical-integration-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':passed,
 'promotion_applied':False,'generation_transition':False}
if passed:
    e['previous_head_digest']=ledger['current_head_digest'];e['new_head_digest']=post_head
e['event_hash']=event_hash(e);ledger['events'].append(e)
ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
if passed: ledger['current_head_digest']=post_head
ledger['open_deficits']=[next_cap]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger)
LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':status,'checks':checks,'post_head_digest':post_head,'architecture_sha256':arch_sha,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed: raise SystemExit('INTELLIGENCE_PLATEAU_CANONICAL_INTEGRATION_WITHHELD')
