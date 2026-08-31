from __future__ import annotations
from pathlib import Path
import hashlib,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
CORE=REPO/'canonical'/'yado-unified-core-v1.json'
RUNTIME=REPO/'runtime'/'yado_unified_core_v1.py'
AUDIT=REPO/'receipts'/'yado-unified-core-deep-self-audit-v1-run-33389049600.json'
CAND=REPO/'candidates'/'g2-self-repair'/'raw-task-representation-v1.json'
ADMIT=REPO/'receipts'/'yado-raw-task-representation-fresh-admission-v1-run-33391307653.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
OUT=ROOT/'yado_raw_task_representation_canonical_admission_gate_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

head=load(HEAD);core=load(CORE);audit=load(AUDIT);cand=load(CAND);admit=load(ADMIT);ledger=load(LEDGER)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['G2_RAW_TASK_REPRESENTATION_CANONICAL_ADMISSION_GATE_V1']:
    raise RuntimeError('UNEXPECTED_CANONICAL_ADMISSION_FRONTIER')
if admit.get('status')!='PASS_G2_RAW_TASK_REPRESENTATION_FRESH_ADMISSION_V1':
    raise RuntimeError('FRESH_ADMISSION_NOT_PASS')
if cand.get('state')!='AUTHORIZED_FOR_SHADOW_REPAIR':
    raise RuntimeError('RAW_CANDIDATE_NOT_SHADOW_AUTHORIZED')

runtime_text=RUNTIME.read_text(encoding='utf-8')
runtime_manifest_canonical="canonical/yado-unified-core-v1.json" in runtime_text
runtime_experience_canonical="canonical/yado-unified-experience-registry-v1.json" in runtime_text
runtime_candidate_manifest="candidates/unified-core-v1/manifest.json" in runtime_text
runtime_candidate_experience="candidates/unified-core-v1/experience-registry.json" in runtime_text

audit_binding=next((x for x in audit.get('findings',[]) if x.get('code')=='RUNTIME_CONTROL_PLANE_BINDING'),None)
binding_ready=bool(
    runtime_manifest_canonical and runtime_experience_canonical
    and not runtime_candidate_manifest and not runtime_candidate_experience
    and audit_binding and audit_binding.get('status')=='PASS'
)

checks={
 'fresh_admission_pass':True,
 'candidate_shadow_authorized':True,
 'runtime_control_plane_ready':binding_ready,
 'canonical_head_ledger_coherent':ledger.get('current_head_digest')==head.get('canonical_head_digest'),
 'g3_not_created':head.get('g3_genesis_performed') is False,
}

# Fail closed: do not mutate canonical core while the core itself says its control-plane binding is wrong.
passed=all(checks.values())
next_cap='G2_RAW_TASK_REPRESENTATION_CANONICAL_INTEGRATION_V1' if passed else 'RUNTIME_CONTROL_PLANE_BINDING_REPAIR_V1'

receipt={
 'schema':'yado.g2.raw_task_representation_canonical_admission_gate.v1',
 'status':'PASS_G2_RAW_TASK_REPRESENTATION_CANONICAL_ADMISSION_GATE_V1' if passed else 'WITHHOLD_G2_RAW_TASK_REPRESENTATION_CANONICAL_ADMISSION_GATE_V1',
 'candidate_digest':cand['candidate_digest'],
 'fresh_admission_receipt':admit['receipt_sha256'],
 'dependency_analysis':{
   'runtime_manifest_canonical':runtime_manifest_canonical,
   'runtime_experience_canonical':runtime_experience_canonical,
   'runtime_candidate_manifest':runtime_candidate_manifest,
   'runtime_candidate_experience':runtime_candidate_experience,
   'self_audit_binding_finding':audit_binding,
 },
 'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'FAIL-CLOSED CANONICAL ADMISSION. A RAW-TEXT CANDIDATE THAT PASSES FRESH TESTS IS NOT INTEGRATED WHILE THE UNIFIED RUNTIME CONTROL PLANE IS BOUND TO CANDIDATE RATHER THAN CANONICAL CONFIGURATION.'
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_RAW_REPRESENTATION_CANONICAL_ADMISSION",
   'event_type':'KERNEL_NATIVE_CANONICAL_ADMISSION_GATE','status':'PASS_SHADOW' if passed else 'WITHHOLD',
   'generation':ledger['current_head'],'deficit':'G2_RAW_TASK_REPRESENTATION_CANONICAL_ADMISSION_GATE_V1',
   'effect':'RAW_REPRESENTATION_READY_FOR_CANONICAL_INTEGRATION' if passed else 'CANONICAL_ADMISSION_BLOCKED_BY_RUNTIME_CONTROL_PLANE_BINDING',
   'source_path':f'receipts/yado-raw-task-representation-canonical-admission-gate-v1-run-{run_id}.json',
   'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
   'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({'status':receipt['status'],'dependency_analysis':receipt['dependency_analysis'],
 'checks':checks,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
