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
TARGET=REPO/'runtime'/'yado_unified_core_deep_self_audit_v1.py'
CAND=REPO/'candidates'/'g2-self-evolution'/'unified_core_deep_self_audit_v4.py'
META=REPO/'candidates'/'g2-self-evolution'/'unified_core_deep_self_audit_v4.json'
ADMIT=REPO/'receipts'/'yado-real-world-evidence-audit-fresh-admission-v1-run-33418518590.json'
OUT=ROOT/'yado_real_world_evidence_audit_canonical_integration_v1_receipt.json'
AUDIT_OUT=ROOT/'yado_unified_core_deep_self_audit_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);core=load(CORE);ledger=load(LEDGER);meta=load(META);admit=load(ADMIT)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['REAL_WORLD_EVIDENCE_AUDIT_CANONICAL_INTEGRATION_V1']:raise RuntimeError('UNEXPECTED_FRONTIER')
if admit.get('status')!='PASS_REAL_WORLD_EVIDENCE_AUDIT_FRESH_ADMISSION_V1':raise RuntimeError('FRESH_ADMISSION_NOT_PASS')
if meta.get('state')!='AUTHORIZED_FOR_SHADOW_ADMISSION':raise RuntimeError('CANDIDATE_NOT_AUTHORIZED')
if fsha(CAND)!=meta.get('candidate_source_sha256'):raise RuntimeError('CANDIDATE_DRIFT')
if fsha(TARGET)!=meta.get('source_runtime_sha256'):raise RuntimeError('SOURCE_RUNTIME_DRIFT')
if admit.get('candidate_source_sha256')!=meta.get('candidate_source_sha256'):raise RuntimeError('ADMISSION_SOURCE_DRIFT')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')

candidate_code=CAND.read_text(encoding='utf-8')
source_checks={
 'native_v2_evidence_bound':"REAL_NATIVE_V2=REPO/'architecture'/'yado-real-world-generalization-state-v2.json'" in candidate_code,
 'science_specific_blocker':"REAL_SCIENCE_DATA_TRANSFER_NATIVE_EVOLUTION_V1" in candidate_code,
 'old_stale_high_unproven_selector_absent':"high_unproven=[x for x in limits" not in candidate_code,
 'same_component':meta.get('component_id')=='ALG-G2-DEEP-SELF-AUDIT-V1',
 'implementation_v4':meta.get('implementation_version')==4,
}

# Execute exact candidate against current state without allowing its audit event to survive this admission test.
ledger_bytes=LEDGER.read_bytes()
old_audit_out=AUDIT_OUT.read_bytes() if AUDIT_OUT.exists() else None
tmp=ROOT/'_audit_v4_canonical_gate_candidate.py'
tmp.write_text(candidate_code,encoding='utf-8')
try:
    sp=importlib.util.spec_from_file_location('_audit_v4_canonical_gate',tmp)
    mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod)
    rec=load(AUDIT_OUT)
finally:
    try:tmp.unlink()
    except FileNotFoundError:pass
    LEDGER.write_bytes(ledger_bytes)
    if old_audit_out is None:
        try:AUDIT_OUT.unlink()
        except FileNotFoundError:pass
    else:AUDIT_OUT.write_bytes(old_audit_out)

rw=next((x for x in rec.get('findings',[]) if x.get('code')=='REAL_WORLD_GENERALIZATION_SCOPE'),{})
sci=next((x for x in rec.get('findings',[]) if x.get('code')=='REAL_SCIENCE_DATA_TRANSFER_NATIVE_EVOLUTION_V1'),{})
checks={
 'fresh_admission_all_checks':all(admit.get('checks',{}).values()),
 'candidate_audit_pass':rec.get('status')=='PASS_YADO_UNIFIED_CORE_DEEP_SELF_AUDIT_V1',
 'math_preserved_current':rw.get('evidence',{}).get('math_proven') is True,
 'program_preserved_current':rw.get('evidence',{}).get('program_proven') is True,
 'science_remains_unproven':rw.get('evidence',{}).get('science_proven') is False,
 'generic_scope_nonblocking':rw.get('blocking') is False,
 'science_specific_blocker':sci.get('blocking') is True and sci.get('status')=='FAIL',
 'specific_next_step':rec.get('self_selected_next_step')=='REAL_SCIENCE_DATA_TRANSFER_NATIVE_EVOLUTION_V1',
 'source_constraints':all(source_checks.values()),
 'head_ledger_coherent':load(LEDGER).get('current_head_digest')==head.get('canonical_head_digest'),
}
passed=all(checks.values())

post_head=None;post_core=None
if passed:
    TARGET.write_text(candidate_code,encoding='utf-8')
    audit_sha=fsha(TARGET)

    new_core=copy.deepcopy(core);new_core.pop('core_digest',None)
    new_core['deep_self_audit']={
      'component_id':'ALG-G2-DEEP-SELF-AUDIT-V1',
      'implementation_version':4,
      'candidate_digest':meta['candidate_digest'],
      'source_sha256':audit_sha,
      'fresh_admission_receipt_sha256':admit['receipt_sha256'],
      'canonical_integration_run_id':str(os.getenv('GITHUB_RUN_ID') or 'LOCAL'),
      'evidence_selector':'NATIVE_V2_PLUS_CANONICAL_CAPABILITY_BINDINGS',
      'legacy_retrieval_detector':core.get('deep_self_audit',{}).get('legacy_retrieval_detector','MANIFEST_PLUS_RUNTIME_BEHAVIOR')
    }
    new_core['current_frontier']='UNIFIED_CORE_POST_REAL_WORLD_EVIDENCE_AUDIT_V4'
    new_core['core_digest']=h(new_core);CORE.write_text(json.dumps(new_core,indent=2,sort_keys=True)+'\n')

    new_head=copy.deepcopy(head);new_head.pop('canonical_head_digest',None)
    new_head['unified_core']['deep_self_audit_source_sha256']=audit_sha
    new_head['unified_core']['core_digest']=new_core['core_digest']
    new_head['current_frontier']='UNIFIED_CORE_POST_REAL_WORLD_EVIDENCE_AUDIT_V4'
    new_head['canonical_head_digest']=h(new_head);HEAD.write_text(json.dumps(new_head,indent=2,sort_keys=True)+'\n')
    post_head=new_head['canonical_head_digest'];post_core=new_core['core_digest']
    status='PASS_REAL_WORLD_EVIDENCE_AUDIT_CANONICAL_INTEGRATION_V1'
    next_cap='UNIFIED_CORE_POST_REAL_WORLD_EVIDENCE_AUDIT_V4'
else:
    status='WITHHOLD_REAL_WORLD_EVIDENCE_AUDIT_CANONICAL_INTEGRATION_V1'
    next_cap='REAL_WORLD_EVIDENCE_AUDIT_SELF_EVOLUTION_V2'

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.real_world_evidence_audit_canonical_integration.v1','status':status,
 'candidate_digest':meta['candidate_digest'],'candidate_source_sha256':meta['candidate_source_sha256'],
 'fresh_admission_receipt':admit['receipt_sha256'],'checks':checks,'source_checks':source_checks,
 'canonical_mutation':passed,'promotion_applied':False,'generation_transition':False,'g3_genesis_performed':False,
 'post_head_digest':post_head,'post_core_digest':post_core,'next_required_capability':next_cap,
 'semantic_boundary':'SAME-GENERATION CANONICALIZATION OF SELF-AUDIT EVIDENCE SELECTION V4. IT UPDATES AUDIT FRESHNESS ONLY; IT DOES NOT ESTABLISH NEW DOMAIN COMPETENCE.'}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

ledger=load(LEDGER)
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_REAL_WORLD_EVIDENCE_AUDIT_CANONICAL_INTEGRATION",
 'event_type':'GENERATION_INTERNAL_SELF_AUDIT_ADMISSION','status':'PASS' if passed else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'REAL_WORLD_EVIDENCE_AUDIT_CANONICAL_INTEGRATION_V1',
 'effect':'SELF_AUDIT_V4_EVIDENCE_SELECTOR_CANONICAL' if passed else 'SELF_AUDIT_V4_CANONICAL_INTEGRATION_WITHHELD',
 'source_path':f'receipts/yado-real-world-evidence-audit-canonical-integration-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':passed,'promotion_applied':False,'generation_transition':False}
if passed:
    e['previous_head_digest']=ledger['current_head_digest'];e['new_head_digest']=post_head
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
if passed:ledger['current_head_digest']=post_head
ledger['open_deficits']=[next_cap]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':status,'checks':checks,'post_head_digest':post_head,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('AUDIT_V4_CANONICAL_INTEGRATION_WITHHELD')
