from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(PKG))

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_g2_contextual_stream_capability_adapter_v1 import ContextualStreamCapabilityAdapterV1

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
CORE=REPO/'canonical'/'yado-unified-core-v1.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
META=REPO/'candidates'/'g2-development'/'contextual-stream-capability-adapter-v1.json'
RUNTIME=REPO/'runtime'/'yado_unified_core_v1.py'
ADMIT=REPO/'receipts'/'yado-context-adapter-dependency-fresh-admission-v1-run-33437271855.json'
CANON_META=REPO/'canonical'/'yado-contextual-stream-capability-adapter-v1.json'
OUT=ROOT/'yado_context_adapter_canonical_integration_v1_receipt.json'

CID='ALG-G2-CONTEXTUAL-STREAM-CAPABILITY-ADAPTER-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);core=load(CORE);ledger=load(LEDGER);meta=load(META);admit=load(ADMIT)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['SHADOW_CONTEXT_ADAPTER_CANONICAL_INTEGRATION_V1']:raise RuntimeError('UNEXPECTED_FRONTIER')
if admit.get('status')!='PASS_CONTEXT_ADAPTER_DEPENDENCY_FRESH_ADMISSION_V1':raise RuntimeError('FRESH_ADMISSION_NOT_PASS')
if meta.get('canonical_active') is not False:raise RuntimeError('ADAPTER_ALREADY_CANONICAL')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')

runtime_text=RUNTIME.read_text(encoding='utf-8')
old_guard="'shadow_context_not_smuggled_canonical':self.shadow_context.get('canonical_active') is False,"
new_guard="'context_adapter_binding_coherent':((CID in active_components)==(self.shadow_context.get('canonical_active') is True)),"
# CID is not defined inside yado_unified_core_v1.py; use literal in the patched source.
new_guard=new_guard.replace("CID","'ALG-G2-CONTEXTUAL-STREAM-CAPABILITY-ADAPTER-V1'")
if old_guard not in runtime_text:raise RuntimeError('UNIFIED_CORE_SHADOW_GUARD_PATTERN_MISSING')
patched_runtime=runtime_text.replace(old_guard,new_guard)

fresh_checks={
 'adapter_score':admit.get('adapter_score')==1.0,
 'base_score_low':float(admit.get('base_score',1.0))<=0.40,
 'memory_ablation_low':float(admit.get('memory_ablation_score',1.0))<=0.40,
 'causal_drop':float(admit.get('causal_drop',0.0))>=0.55,
 'fresh_gate_checks':all(admit.get('checks',{}).values()),
}
identity_ok=ContextualStreamCapabilityAdapterV1.component().get('component_digest')==meta.get('component',{}).get('component_digest')
runtime_patch_ok=(
 old_guard not in patched_runtime and
 'context_adapter_binding_coherent' in patched_runtime and
 'ContextualStreamCapabilityAdapterV1' in patched_runtime
)

# Build prospective metadata and manifest before mutating.
new_meta=copy.deepcopy(meta)
new_meta['canonical_active']=True
new_meta['state']='CANONICAL_ACTIVE_G2'
new_meta['canonical_admission']={
  'gate_run_id':str(os.getenv('GITHUB_RUN_ID') or 'LOCAL'),
  'fresh_admission_receipt_sha256':admit['receipt_sha256'],
  'adapter_score':admit['adapter_score'],
  'base_score':admit['base_score'],
  'memory_ablation_score':admit['memory_ablation_score'],
  'causal_drop':admit['causal_drop'],
}
new_meta['canonical_source_sha256']=fsha(REPO/'runtime'/'yado_g2_contextual_stream_capability_adapter_v1.py')

new_core=copy.deepcopy(core);new_core.pop('core_digest',None)
mem=next(x for x in new_core['planes'] if x.get('plane_id')=='MEMORY_AND_EXPERIENCE')
mem['active_components']=sorted(set(mem.get('active_components',[])+[CID]))
mem['shadow_components']=[x for x in mem.get('shadow_components',[]) if x!=CID]
mem['responsibilities']=sorted(set(mem.get('responsibilities',[])+['bounded_context_conditioned_stream_routing']))
new_core['active_runtime_sources']=sorted(set(new_core.get('active_runtime_sources',[])+['runtime/yado_g2_contextual_stream_capability_adapter_v1.py']))
new_core['shadow_runtime_sources']=[x for x in new_core.get('shadow_runtime_sources',[]) if x!='runtime/yado_g2_contextual_stream_capability_adapter_v1.py']
new_core['contextual_stream_adapter']={
  'component_id':CID,
  'candidate_digest':meta.get('candidate_digest'),
  'source_sha256':new_meta['canonical_source_sha256'],
  'fresh_admission_receipt_sha256':admit['receipt_sha256'],
  'fresh_score':admit['adapter_score'],
  'base_score':admit['base_score'],
  'memory_ablation_score':admit['memory_ablation_score'],
  'mode':'ACTIVE_BOUNDED_STREAM_CONTEXT_MAP',
  'max_stream_contexts':meta.get('component',{}).get('max_stream_contexts'),
  'gate_run_id':str(os.getenv('GITHUB_RUN_ID') or 'LOCAL'),
}
new_core['current_frontier']='UNIFIED_CORE_POST_CONTEXT_ADAPTER_SELF_AUDIT_V1'

checks={
 'fresh_evidence':all(fresh_checks.values()),
 'component_identity':identity_ok,
 'runtime_guard_patch_bounded':runtime_patch_ok,
 'manifest_active_binding':CID in mem.get('active_components',[]) and CID not in mem.get('shadow_components',[]),
 'runtime_source_promoted':'runtime/yado_g2_contextual_stream_capability_adapter_v1.py' in new_core.get('active_runtime_sources',[]) and 'runtime/yado_g2_contextual_stream_capability_adapter_v1.py' not in new_core.get('shadow_runtime_sources',[]),
 'g3_still_blocked':core.get('g3_genesis_performed') is False and head.get('g3_genesis_performed') is False,
 'canonical_head_coherent':ledger.get('current_head_digest')==head.get('canonical_head_digest'),
}
passed=all(checks.values())

post_head=None;post_core=None
if passed:
    META.write_text(json.dumps(new_meta,indent=2,sort_keys=True)+'\n')
    CANON_META.write_text(json.dumps(new_meta,indent=2,sort_keys=True)+'\n')
    RUNTIME.write_text(patched_runtime,encoding='utf-8')
    runtime_sha=fsha(RUNTIME)
    new_core['runtime_sha256']=runtime_sha
    new_core['core_digest']=h(new_core);CORE.write_text(json.dumps(new_core,indent=2,sort_keys=True)+'\n')

    new_head=copy.deepcopy(head);new_head.pop('canonical_head_digest',None)
    new_head['new_capabilities']=sorted(set(new_head.get('new_capabilities',[])+[CID]))
    new_head['unified_core']['runtime_sha256']=runtime_sha
    new_head['unified_core']['core_digest']=new_core['core_digest']
    new_head['unified_core']['contextual_stream_adapter_source_sha256']=new_meta['canonical_source_sha256']
    new_head['current_frontier']='UNIFIED_CORE_POST_CONTEXT_ADAPTER_SELF_AUDIT_V1'
    new_head['canonical_head_digest']=h(new_head);HEAD.write_text(json.dumps(new_head,indent=2,sort_keys=True)+'\n')
    post_head=new_head['canonical_head_digest'];post_core=new_core['core_digest']
    status='PASS_CONTEXT_ADAPTER_CANONICAL_INTEGRATION_V1'
    next_cap='UNIFIED_CORE_POST_CONTEXT_ADAPTER_SELF_AUDIT_V1'
else:
    status='WITHHOLD_CONTEXT_ADAPTER_CANONICAL_INTEGRATION_V1'
    next_cap='SHADOW_CONTEXT_ADAPTER_SELF_EVOLUTION_V2'

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
 'schema':'yado.g2.context_adapter_canonical_integration.v1','status':status,
 'component_id':CID,'adapter_candidate_digest':meta.get('candidate_digest'),
 'fresh_admission_receipt':admit.get('receipt_sha256'),'fresh_checks':fresh_checks,'checks':checks,
 'canonical_mutation':passed,'promotion_applied':False,'generation_transition':False,'g3_genesis_performed':False,
 'post_head_digest':post_head,'post_core_digest':post_core,'next_required_capability':next_cap,
 'semantic_boundary':'SAME-GENERATION CANONICALIZATION OF BOUNDED STREAM-CONTEXT ROUTING. NOT GENERAL AUTOBIOGRAPHICAL MEMORY, SUBJECTIVE CONTINUITY, CONSCIOUSNESS, OR AGI.'
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_CONTEXT_ADAPTER_CANONICAL_INTEGRATION",
 'event_type':'GENERATION_INTERNAL_CONTEXT_CAPABILITY_ADMISSION','status':'PASS' if passed else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'SHADOW_CONTEXT_ADAPTER_CANONICAL_INTEGRATION_V1',
 'effect':'CONTEXT_ADAPTER_CANONICAL_ACTIVE' if passed else 'CONTEXT_ADAPTER_CANONICAL_INTEGRATION_WITHHELD',
 'source_path':f'receipts/yado-context-adapter-canonical-integration-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':passed,'promotion_applied':False,'generation_transition':False}
if passed:
    e['previous_head_digest']=ledger['current_head_digest'];e['new_head_digest']=post_head
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
if passed:ledger['current_head_digest']=post_head
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':status,'fresh_checks':fresh_checks,'checks':checks,'post_head_digest':post_head,
 'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('CONTEXT_ADAPTER_CANONICAL_INTEGRATION_WITHHELD')
