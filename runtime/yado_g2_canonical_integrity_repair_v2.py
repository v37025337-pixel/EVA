from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,subprocess,sys

REPO=Path(__file__).resolve().parents[1]
ROOT=REPO/'runtime'
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
HISTORY=REPO/'architecture/yado-v3-cancelled-run-history-v1.json'
ART=REPO/'architecture/yado-g2-canonical-integrity-repair-v2.json'
OUT=ROOT/'yado_g2_canonical_integrity_repair_v2_receipt.json'
UNIFIED=ROOT/'yado_unified_core_v1.py'
AUDIT=ROOT/'yado_unified_core_deep_self_audit_v1.py'
GUARD=ROOT/'yado_canonical_invariant_guard_v1.py'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):
    x=copy.deepcopy(o);x.pop(field,None);return h(x)

head,core,prov,ledger=map(load,[HEAD,CORE,PROV,LEDGER])
validate_ledger_v2(ledger)
front='KERNEL_SCALE_CONDITIONAL_SUCCESSOR_HIGH_SCALE_REPAIR_V3'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if head.get('generation_id')!='G2_CANDIDATE_TRCG_V1':raise RuntimeError('NOT_G2')
if head.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')

previous_head_digest=head['canonical_head_digest']
previous_core_digest=core['core_digest']
previous_prov_digest=prov['registry_digest']

# Import cancelled V3 attempts as negative causal experience only.
cancelled_runs=[
 {
  'run_id':'33607506029','workflow':'YADO G2 High Scale Repair V3','outcome':'CANCELLED_BEFORE_EVIDENCE_PERSISTENCE',
  'admission_evidence':False,'fresh10_opened':False,
  'diagnostic':'FIRST_V3_ATTEMPT_CANCELLED; NO_RECEIPT_PERSISTED'
 },
 {
  'run_id':'33610098317','workflow':'YADO G2 High Scale Repair V3','outcome':'RESOURCE_TIMEOUT_25_MINUTES',
  'admission_evidence':False,'fresh10_opened':False,
  'diagnostic':{
    'pair_knn_holdout':0.967654986522911,
    'triple_knn_holdout':0.9582210242587601,
    'native_rc5_returned':False,
    'native_rc5_runtime_before_cancel_seconds':1152
  }
 },
 {
  'run_id':'33622894988','workflow':'YADO G2 High Scale Repair V3','outcome':'RESOURCE_TIMEOUT_60_MINUTES',
  'admission_evidence':False,'fresh10_opened':False,
  'diagnostic':{
    'native_rc5_returned':False,
    'native_rc5_runtime_before_cancel_seconds_gt':3060,
    'selection_protocol_changed':False
  }
 }
]
history_art={
 'schema':'yado.g2.v3_cancelled_execution_history.v1',
 'generation':head['generation_id'],'frontier':front,
 'source_class':'VERIFIED_GITHUB_ACTIONS_EXECUTION_HISTORY_IMPORT',
 'semantic_rule':'CANCELLED_OR_TIMEOUT_RUNS_ARE_NEGATIVE_RESOURCE_EXPERIENCE_ONLY_AND_NEVER_CAPABILITY_ADMISSION_EVIDENCE',
 'runs':cancelled_runs,'g3_genesis_performed':False,
}
history_art['artifact_digest']=cdig(history_art,'artifact_digest')
write(HISTORY,history_art)

known={str(e.get('run_id')) for e in ledger.get('events',[])}
for item in cancelled_runs:
    if item['run_id'] in known:continue
    idx=len(ledger['events'])
    e={
      'index':idx,'event_id':f"E{idx+1:04d}_G2_V3_RESOURCE_FAILURE_{item['run_id']}",
      'event_type':'G2_EXECUTION_RESOURCE_FAILURE_EXPERIENCE',
      'status':'WITHHOLD','generation':ledger['current_head'],'deficit':front,
      'effect':f"RUN={item['run_id']}; OUTCOME={item['outcome']}; ADMISSION_EVIDENCE=False; FRESH10_OPENED=False; NEXT={front}",
      'source_path':'architecture/yado-v3-cancelled-run-history-v1.json',
      'source_digest':history_art['artifact_digest'],'run_id':item['run_id'],
      'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':False,'promotion_applied':False,'generation_transition':False,
    }
    e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
    ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
    validate_ledger_v2(ledger)

# Synchronize semantic provenance to the actual current frontier.
rc5=next((m for m in prov.get('mechanisms',[]) if m.get('mechanism_id')=='RC5_ALGORITHM_CONSTRUCTOR'),None)
if not rc5:raise RuntimeError('RC5_PROVENANCE_MISSING')
prov['current_g2_binding']={
 'active_runtime_class':'UnifiedYADOKernelV30RC8ExternalCognitive',
 'current_execution_label':'G2_NATIVE_RC5_CONSTRUCTOR_COMPETITIVE_REPAIR',
 'frontier':front,
 'frontier_native_method':'synthesize_intelligence_algorithm_component',
 'frontier_native_owner':'UnifiedYADOKernelV30RC5AlgorithmGenesis',
 'generation':head['generation_id'],
 'historical_origin_label':'RC5_ALGORITHM_GENESIS',
 'frontier_binding_semantics':'CURRENT_DEVELOPMENTAL_FRONTIER_CONSUMER_NOT_GLOBAL_RUNTIME_IDENTITY'
}
prov['registry_digest']=cdig(prov,'registry_digest')
write(PROV,prov)

# Bind the exact currently executable runtime and every active runtime source.
guard_rel='runtime/yado_canonical_invariant_guard_v1.py'
ars=list(core.get('active_runtime_sources',[]))
if guard_rel not in ars:ars.append(guard_rel)
core['active_runtime_sources']=sorted(dict.fromkeys(ars))
source_hashes={}
for rel in core['active_runtime_sources']:
    p=REPO/rel
    if not p.exists():raise RuntimeError('ACTIVE_RUNTIME_SOURCE_MISSING:'+rel)
    source_hashes[rel]=fsha(p)
runtime_manifest={'algorithm':'SHA256','sources':source_hashes}
runtime_manifest['manifest_digest']=h(source_hashes)

core['runtime_sha256']=fsha(UNIFIED)
core['deep_self_audit']['source_sha256']=fsha(AUDIT)
core['deep_self_audit']['implementation_version']=7
core['algorithm_provenance_registry_digest']=prov['registry_digest']
core['runtime_integrity_manifest']=runtime_manifest
core['canonical_write_guard']={
 'guard_id':'G2_CANONICAL_INVARIANT_GUARD_V1',
 'runtime':guard_rel,'source_sha256':fsha(GUARD),
 'required_before_active_development_and_after_canonical_mutation':True,
 'policy':'FAIL_CLOSED_ON_RUNTIME_OR_PROVENANCE_OR_HEAD_LEDGER_DRIFT'
}
core['current_frontier']=front
core['frontier_source']='architecture/evolution-ledger.json:open_deficits'
core['core_digest']=cdig(core,'core_digest')
write(CORE,core)

# Separate historical appearance from current active capability set.
active_caps=sorted({
 str(x) for plane in core.get('planes',[]) for x in plane.get('active_components',[])
 if isinstance(x,str) and '/' not in x and not x.endswith('.json')
})
head['active_capabilities']=active_caps
head['capability_semantics']={
 'inherited_capabilities':'HISTORICAL_INHERITANCE_AT_GENERATION_CONSTRUCTION',
 'new_capabilities':'HISTORICAL_CAPABILITIES_INTRODUCED_DURING_G2',
 'active_capabilities':'CURRENT_CANONICAL_ACTIVE_COMPONENTS_ONLY'
}
head['algorithm_provenance_registry']['current_execution_label']=prov['current_g2_binding']['current_execution_label']
head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest']
head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest']
head['unified_core']['runtime_sha256']=core['runtime_sha256']
head['unified_core']['deep_self_audit_source_sha256']=core['deep_self_audit']['source_sha256']
head['unified_core']['runtime_integrity_manifest_digest']=runtime_manifest['manifest_digest']
head['unified_core']['canonical_write_guard_source_sha256']=core['canonical_write_guard']['source_sha256']
head['unified_core']['core_digest']=core['core_digest']
head['current_frontier']=front
head['frontier_source']='architecture/evolution-ledger.json:open_deficits'
head['canonical_head_digest']=cdig(head,'canonical_head_digest')
write(HEAD,head)

# Canonical mutation event closes the integrity debt without advancing the frontier.
ledger['current_head_digest']=head['canonical_head_digest']
for deficit in [
 'UNIFIED_RUNTIME_HASH_BINDING',
 'CANONICAL_MUTATION_PRECOMMIT_GUARD',
 'ALGORITHM_PROVENANCE_FRONTIER_FRESHNESS',
 'HEAD_ACTIVE_CAPABILITY_SEMANTICS',
 'V3_CANCELLED_RUN_CAUSAL_HISTORY_IMPORT'
]:
    if deficit not in ledger.setdefault('resolved_deficits',[]):ledger['resolved_deficits'].append(deficit)

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
evidence_digest=h({
 'previous_head_digest':previous_head_digest,'new_head_digest':head['canonical_head_digest'],
 'previous_core_digest':previous_core_digest,'new_core_digest':core['core_digest'],
 'previous_provenance_digest':previous_prov_digest,'new_provenance_digest':prov['registry_digest'],
 'runtime_sha256':core['runtime_sha256'],'runtime_integrity_manifest_digest':runtime_manifest['manifest_digest'],
 'cancelled_history_digest':history_art['artifact_digest'],'frontier':front
})
idx=len(ledger['events'])
event={
 'index':idx,'event_id':f"E{idx+1:04d}_G2_CANONICAL_INTEGRITY_REPAIR_V2",
 'event_type':'G2_CANONICAL_CONTROL_PLANE_INTEGRITY_REPAIR',
 'status':'PASS','generation':ledger['current_head'],'deficit':'G2_CANONICAL_INTEGRITY_REPAIR_V2',
 'effect':f"RUNTIME_REBOUND=True; PROVENANCE_SYNCED=True; ACTIVE_CAPABILITIES_EXPLICIT=True; V3_CANCELLED_RUNS_IMPORTED=3; GUARD=FAIL_CLOSED; NEXT={front}",
 'source_path':f'receipts/yado-g2-canonical-integrity-repair-v2-run-{run_id}.json',
 'source_digest':evidence_digest,'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':True,'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':previous_head_digest,'new_head_digest':head['canonical_head_digest']
}
event['event_hash']=event_hash(event);ledger['events'].append(event);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=event['event_hash']
ledger['open_deficits']=[front]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);write(LEDGER,ledger)

cp=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=60)
if cp.returncode!=0:raise RuntimeError('POST_REPAIR_GUARD_FAILED:'+cp.stdout[-3000:]+cp.stderr[-1000:])

checks={
 'runtime_rebound':core['runtime_sha256']==fsha(UNIFIED)==head['unified_core']['runtime_sha256'],
 'deep_audit_rebound':core['deep_self_audit']['source_sha256']==fsha(AUDIT)==head['unified_core']['deep_self_audit_source_sha256'],
 'provenance_frontier_current':prov['current_g2_binding']['frontier']==front,
 'active_capabilities_explicit':head['active_capabilities']==active_caps,
 'cancelled_runs_imported':all(x['run_id'] in {str(e.get('run_id')) for e in ledger['events']} for x in cancelled_runs),
 'runtime_manifest_complete':set(runtime_manifest['sources'])==set(core['active_runtime_sources']),
 'guard_passed':True,
 'frontier_preserved':ledger['open_deficits']==[front]==[head['current_frontier']]==[core['current_frontier']],
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
if not all(checks.values()):raise RuntimeError('REPAIR_CHECKS_FAILED:'+json.dumps(checks,sort_keys=True))

artifact={
 'schema':'yado.g2.canonical_integrity_repair.v2','status':'PASS_G2_CANONICAL_INTEGRITY_REPAIR_V2',
 'generation':head['generation_id'],'frontier':front,'checks':checks,
 'previous_head_digest':previous_head_digest,'new_head_digest':head['canonical_head_digest'],
 'previous_core_digest':previous_core_digest,'new_core_digest':core['core_digest'],
 'runtime_sha256':core['runtime_sha256'],'runtime_integrity_manifest_digest':runtime_manifest['manifest_digest'],
 'algorithm_provenance_registry_digest':prov['registry_digest'],
 'cancelled_run_history_digest':history_art['artifact_digest'],
 'canonical_mutation':True,'architecture_mutation':False,'generation_transition':False,'g3_genesis_performed':False,
}
artifact['artifact_digest']=cdig(artifact,'artifact_digest');write(ART,artifact)
receipt={**artifact,'schema':'yado.g2.canonical_integrity_repair.receipt.v2','github_run_id':run_id,'guard_output':cp.stdout[-4000:]}
receipt['receipt_sha256']=cdig(receipt,'receipt_sha256');write(OUT,receipt)
print(json.dumps(receipt,indent=2,sort_keys=True))
