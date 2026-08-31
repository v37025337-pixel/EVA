from __future__ import annotations
from pathlib import Path
import hashlib,importlib.util,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
SOURCE=REPO/'runtime'/'yado_unified_core_deep_self_audit_v1.py'
CAND=REPO/'candidates'/'g2-self-evolution'/'unified_core_deep_self_audit_v4.py'
META=REPO/'candidates'/'g2-self-evolution'/'unified_core_deep_self_audit_v4.json'
OUT=ROOT/'yado_real_world_evidence_audit_fresh_admission_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);ledger=load(LEDGER);meta=load(META)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['REAL_WORLD_EVIDENCE_AUDIT_FRESH_ADMISSION_V1']:raise RuntimeError('UNEXPECTED_FRONTIER')
if meta.get('state')!='AUTHORIZED_FOR_SHADOW_ADMISSION':raise RuntimeError('CANDIDATE_NOT_AUTHORIZED')
if fsha(CAND)!=meta.get('candidate_source_sha256'):raise RuntimeError('CANDIDATE_DRIFT')
if fsha(SOURCE)!=meta.get('source_runtime_sha256'):raise RuntimeError('SOURCE_RUNTIME_DRIFT')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')

old=SOURCE.read_text(encoding='utf-8');new=CAND.read_text(encoding='utf-8')
source_checks={
 'native_state_bound':"REAL_NATIVE_V2=REPO/'architecture'/'yado-real-world-generalization-state-v2.json'" in new,
 'native_load_present':'native_v2=load(REAL_NATIVE_V2)' in new,
 'science_specific_finding':"add('REAL_SCIENCE_DATA_TRANSFER_NATIVE_EVOLUTION_V1'" in new,
 'old_high_unproven_logic_removed':"high_unproven=[x for x in limits" not in new,
 'no_generation_transition_logic_added':'G3' not in (new[len(old):] if len(new)>len(old) else ''),
}

ledger_bytes=LEDGER.read_bytes()
audit_out=ROOT/'yado_unified_core_deep_self_audit_v1_receipt.json'
old_out=audit_out.read_bytes() if audit_out.exists() else None
tmp=ROOT/'_audit_v4_fresh_candidate.py'
tmp.write_text(new,encoding='utf-8')
try:
    sp=importlib.util.spec_from_file_location('_audit_v4_fresh',tmp)
    mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod)
    rec=load(audit_out)
finally:
    try:tmp.unlink()
    except FileNotFoundError:pass
    LEDGER.write_bytes(ledger_bytes)
    if old_out is None:
        try:audit_out.unlink()
        except FileNotFoundError:pass
    else:audit_out.write_bytes(old_out)

rw=next((x for x in rec.get('findings',[]) if x.get('code')=='REAL_WORLD_GENERALIZATION_SCOPE'),{})
sci=next((x for x in rec.get('findings',[]) if x.get('code')=='REAL_SCIENCE_DATA_TRANSFER_NATIVE_EVOLUTION_V1'),{})
checks={
 'candidate_audit_pass':rec.get('status')=='PASS_YADO_UNIFIED_CORE_DEEP_SELF_AUDIT_V1',
 'math_current':rw.get('evidence',{}).get('math_proven') is True,
 'program_current':rw.get('evidence',{}).get('program_proven') is True,
 'science_not_falsely_promoted':rw.get('evidence',{}).get('science_proven') is False,
 'general_scope_nonblocking':rw.get('blocking') is False,
 'science_blocking':sci.get('blocking') is True and sci.get('status')=='FAIL',
 'specific_next_step':rec.get('self_selected_next_step')=='REAL_SCIENCE_DATA_TRANSFER_NATIVE_EVOLUTION_V1',
 'source_constraints':all(source_checks.values()),
 'canonical_head_immutable':load(LEDGER).get('current_head_digest')==head.get('canonical_head_digest'),
}
passed=all(checks.values())
next_cap='REAL_WORLD_EVIDENCE_AUDIT_CANONICAL_INTEGRATION_V1' if passed else 'REAL_WORLD_EVIDENCE_AUDIT_SELF_EVOLUTION_V2'
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.real_world_evidence_audit_fresh_admission.v1',
 'status':'PASS_REAL_WORLD_EVIDENCE_AUDIT_FRESH_ADMISSION_V1' if passed else 'WITHHOLD_REAL_WORLD_EVIDENCE_AUDIT_FRESH_ADMISSION_V1',
 'candidate_digest':meta['candidate_digest'],'candidate_source_sha256':meta['candidate_source_sha256'],
 'checks':checks,'source_checks':source_checks,'candidate_next_step':rec.get('self_selected_next_step'),
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,'semantic_boundary':meta['semantic_boundary']}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

ledger=load(LEDGER)
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_REAL_WORLD_EVIDENCE_AUDIT_FRESH_ADMISSION",
 'event_type':'SELF_AUDIT_EVIDENCE_SELECTOR_FRESH_ADMISSION','status':'PASS_SHADOW' if passed else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'REAL_WORLD_EVIDENCE_AUDIT_FRESH_ADMISSION_V1',
 'effect':f"AUDIT_V4_FRESH_ADMISSION; NEXT={next_cap}",
 'source_path':f'receipts/yado-real-world-evidence-audit-fresh-admission-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'checks':checks,'candidate_next_step':rec.get('self_selected_next_step'),'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('AUDIT_V4_FRESH_ADMISSION_WITHHELD')
