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
CAND_DIR=REPO/'candidates'/'g2-self-evolution'
CAND_SRC=CAND_DIR/'unified_core_deep_self_audit_v5.py'
CAND_META=CAND_DIR/'unified_core_deep_self_audit_v5.json'
COUNTER=REPO/'receipts'/'yado-unified-core-deep-self-audit-v1-run-33436481532.json'
OUT=ROOT/'yado_science_evidence_audit_self_evolution_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);ledger=load(LEDGER);counter=load(COUNTER)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['REAL_SCIENCE_DATA_TRANSFER_NATIVE_EVOLUTION_V1']:raise RuntimeError('UNEXPECTED_FRONTIER')
if counter.get('self_selected_next_step')!='REAL_SCIENCE_DATA_TRANSFER_NATIVE_EVOLUTION_V1':raise RuntimeError('SCIENCE_STALE_COUNTEREXAMPLE_NOT_PRESENT')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')

old=SOURCE.read_text(encoding='utf-8')
needle="science_proven=(native_pass.get('REAL_SCIENCE_DATA_TRANSFER') is True and bool(ccore.get('science_reasoning')))"
replacement="""science_binding=ccore.get('science_reasoning',{}) if isinstance(ccore.get('science_reasoning',{}),dict) else {}
science_bound=science_binding.get('mode')=='ACTIVE_BOUNDED_TABULAR_SCIENTIFIC_REASONING'
science_fresh_receipt=bool(science_binding.get('fresh_admission_receipt_sha256'))
science_fresh_datasets=set(science_binding.get('fresh_datasets',[]))
science_proven=(science_bound and science_fresh_receipt and {'PENGUINS','TIPS'}.issubset(science_fresh_datasets))"""
if needle not in old:raise RuntimeError('SCIENCE_PROVEN_V4_PATTERN_NOT_FOUND')
new=old.replace(needle,replacement)
new=new.replace(
"'native_scientific_reasoning_present':science_proven,",
"'native_scientific_reasoning_present':science_proven,'science_canonical_bound':science_bound,'science_fresh_receipt_bound':science_fresh_receipt,'science_fresh_datasets':sorted(science_fresh_datasets),"
)
CAND_DIR.mkdir(parents=True,exist_ok=True);CAND_SRC.write_text(new,encoding='utf-8')

ledger_bytes=LEDGER.read_bytes()
audit_out=ROOT/'yado_unified_core_deep_self_audit_v1_receipt.json'
old_out=audit_out.read_bytes() if audit_out.exists() else None
tmp=ROOT/'_audit_v5_shadow_candidate.py'
tmp.write_text(new,encoding='utf-8')
try:
    sp=importlib.util.spec_from_file_location('_audit_v5_shadow',tmp)
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
ctx=next((x for x in rec.get('findings',[]) if x.get('code')=='SHADOW_CONTEXT_ADAPTER_DEPENDENCE'),{})
checks={
 'candidate_executes':rec.get('status')=='PASS_YADO_UNIFIED_CORE_DEEP_SELF_AUDIT_V1',
 'science_now_proven':rw.get('evidence',{}).get('science_proven') is True,
 'no_remaining_real_world_domains':rw.get('evidence',{}).get('remaining_native_domains')==[],
 'host_scaffold_science_closed':rw.get('evidence',{}).get('host_scaffold_dependence') is False,
 'science_finding_pass':sci.get('status')=='PASS' and sci.get('blocking') is False,
 'context_dependency_preserved':ctx.get('status')=='FAIL' and ctx.get('blocking') is True,
 'next_step_context_specific':rec.get('self_selected_next_step')=='SHADOW_CONTEXT_ADAPTER_DEPENDENCE',
 'canonical_head_immutable':load(LEDGER).get('current_head_digest')==head.get('canonical_head_digest'),
}
passed=all(checks.values())
candidate_digest=h({'source_sha256':fsha(CAND_SRC),'checks':checks,'next':rec.get('self_selected_next_step')})
meta={
 'schema':'yado.g2.deep_self_audit_evidence_selector_candidate.v5',
 'component_id':'ALG-G2-DEEP-SELF-AUDIT-V1','implementation_version':5,
 'candidate_digest':candidate_digest,'candidate_source_sha256':fsha(CAND_SRC),
 'source_runtime_sha256':fsha(SOURCE),'generation':ledger['current_head'],'parent_head_digest':head['canonical_head_digest'],
 'source_counterexample_receipt':counter['receipt_sha256'],'checks':checks,
 'canonical_active':False,'promotion_applied':False,
 'state':'AUTHORIZED_FOR_SHADOW_ADMISSION' if passed else 'WITHHELD_AUDIT_EVOLUTION_V5',
 'semantic_boundary':'SELF-AUDIT EVIDENCE-SELECTION REPAIR: CANONICAL SCIENCE FRESH-ADMISSION BINDING SUPERSEDES PRE-SCIENCE DIAGNOSTIC FLAGS. DOES NOT CREATE SCIENCE CAPABILITY.'
}
CAND_META.write_text(json.dumps(meta,indent=2,sort_keys=True)+'\n')
next_cap='SCIENCE_EVIDENCE_AUDIT_FRESH_ADMISSION_V1' if passed else 'SCIENCE_EVIDENCE_AUDIT_SELF_EVOLUTION_V2'
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.science_evidence_audit_self_evolution.v1',
 'status':'PASS_SCIENCE_EVIDENCE_AUDIT_SELF_EVOLUTION_V1' if passed else 'WITHHOLD_SCIENCE_EVIDENCE_AUDIT_SELF_EVOLUTION_V1',
 'candidate_digest':candidate_digest,'candidate_source_sha256':fsha(CAND_SRC),'checks':checks,
 'candidate_next_step':rec.get('self_selected_next_step'),
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,'semantic_boundary':meta['semantic_boundary']}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

ledger=load(LEDGER)
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_SCIENCE_EVIDENCE_AUDIT_SELF_EVOLUTION",
 'event_type':'KERNEL_SELF_AUDIT_SCIENCE_EVIDENCE_SELECTOR_EVOLUTION','status':'PASS_SHADOW' if passed else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'REAL_SCIENCE_DATA_TRANSFER_NATIVE_EVOLUTION_V1',
 'effect':f"SCIENCE_CANONICAL_EVIDENCE_SUPERSEDES_PRE_SCIENCE_DIAGNOSTIC; NEXT={next_cap}",
 'source_path':f'receipts/yado-science-evidence-audit-self-evolution-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'checks':checks,'candidate_next_step':rec.get('self_selected_next_step'),'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('SCIENCE_EVIDENCE_AUDIT_SELF_EVOLUTION_WITHHELD')
