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
CAND_SRC=CAND_DIR/'unified_core_deep_self_audit_v4.py'
CAND_META=CAND_DIR/'unified_core_deep_self_audit_v4.json'
LATEST_AUDIT=REPO/'receipts'/'yado-unified-core-deep-self-audit-v1-run-33417920560.json'
OUT=ROOT/'yado_real_world_evidence_audit_self_evolution_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);ledger=load(LEDGER);old_receipt=load(LATEST_AUDIT)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['REAL_WORLD_GENERALIZATION_SCOPE']:raise RuntimeError('UNEXPECTED_FRONTIER')
if old_receipt.get('self_selected_next_step')!='REAL_WORLD_GENERALIZATION_SCOPE':raise RuntimeError('STALE_AUDIT_NOT_REPRODUCED')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')

old=SOURCE.read_text(encoding='utf-8')
new=old
anchor="REAL=REAL_LATEST if REAL_LATEST.exists() else REAL_LEGACY\n"
insert=anchor+"REAL_NATIVE_V2=REPO/'architecture'/'yado-real-world-generalization-state-v2.json'\n"
if "REAL_NATIVE_V2=" not in new:new=new.replace(anchor,insert)
load_anchor="burn=load(BURN);work=load(WORK);dev=load(DEV);real=load(REAL);legacy_real=load(REAL_LEGACY);post=load(POST);consol=load(CONSOL);recon=load(RECON)\n"
load_new="burn=load(BURN);work=load(WORK);dev=load(DEV);real=load(REAL);legacy_real=load(REAL_LEGACY);post=load(POST);consol=load(CONSOL);recon=load(RECON)\nnative_v2=load(REAL_NATIVE_V2) if REAL_NATIVE_V2.exists() else {}\n"
if "native_v2=load(REAL_NATIVE_V2)" not in new:new=new.replace(load_anchor,load_new)

start=new.index("# Prior audit boundaries remain relevant.")
end=new.index("# ---------- self-audit and repair plane ----------",start)
replacement="""# Current native-only transfer evidence supersedes stale pre-integration capability claims.
native_pass=native_v2.get('domain_pass',{}) if isinstance(native_v2,dict) else {}
math_bound=ccore.get('mathematical_reasoning',{}).get('mode')=='ACTIVE_BOUNDED_SEMANTIC_EXPRESSION_SYNTHESIS'
program_bound=ccore.get('program_execution',{}).get('mode')=='ACTIVE_BOUNDED_SINGLE_FUNCTION_REPAIR'
raw_proven=native_pass.get('REAL_UNSTRUCTURED_INPUT_TRANSFER') is True
math_proven=(native_pass.get('REAL_MATHEMATICAL_REASONING_TRANSFER') is True and math_bound)
program_proven=(program_bound and float(ccore.get('program_execution',{}).get('fresh_score',0.0))>=1.0)
science_proven=(native_pass.get('REAL_SCIENCE_DATA_TRANSFER') is True and bool(ccore.get('science_reasoning')))
remaining=[]
if not raw_proven:remaining.append('REAL_UNSTRUCTURED_INPUT_TRANSFER')
if not math_proven:remaining.append('REAL_MATHEMATICAL_REASONING_TRANSFER')
if not program_proven:remaining.append('REAL_PROGRAM_EXECUTION_TRANSFER')
if not science_proven:remaining.append('REAL_SCIENCE_DATA_TRANSFER')
host_scaffold_dependence=not science_proven

add('REAL_WORLD_GENERALIZATION_SCOPE','REPRESENTATION_AND_GROUNDING','MEDIUM' if remaining else 'INFO',
    'PARTIAL' if remaining else 'PASS',
    {'remaining_native_domains':remaining,'raw_proven':raw_proven,'math_proven':math_proven,
     'program_proven':program_proven,'science_proven':science_proven,
     'host_scaffold_dependence':host_scaffold_dependence,
     'native_v2_state_source':str(REAL_NATIVE_V2.relative_to(REPO)).replace('\\\\','/')},
    'Continue only on native capabilities still missing; do not reopen capabilities already admitted through canonical gates.',
    False)

add('REAL_SCIENCE_DATA_TRANSFER_NATIVE_EVOLUTION_V1','RESOURCE_AND_EVIDENCE','HIGH' if not science_proven else 'INFO',
    'FAIL' if not science_proven else 'PASS',
    {'public_data_download_seen':native_v2.get('domain_scores',{}).get('REAL_SCIENCE_DATA_TRANSFER') is not None,
     'native_scientific_reasoning_present':science_proven,
     'program_capability_now_canonical':program_bound,'mathematics_capability_now_canonical':math_bound},
    'Create and independently admit a bounded native scientific-data reasoning capability over fresh public datasets.',
    not science_proven)

"""
new=new[:start]+replacement+new[end:]
CAND_DIR.mkdir(parents=True,exist_ok=True);CAND_SRC.write_text(new,encoding='utf-8')

# Execute candidate as a script in an isolated module namespace; it writes only its runtime receipt and ledger,
# so use temporary ledger backup/restore to prevent shadow evaluation from mutating canonical development state.
ledger_bytes=LEDGER.read_bytes()
out_path=ROOT/'yado_unified_core_deep_self_audit_v1_receipt.json'
old_out=out_path.read_bytes() if out_path.exists() else None
try:
    sp=importlib.util.spec_from_file_location('_audit_v4_shadow',CAND_SRC)
    mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod)
    candidate_receipt=load(out_path)
finally:
    LEDGER.write_bytes(ledger_bytes)
    if old_out is None:
        try:out_path.unlink()
        except FileNotFoundError:pass
    else:out_path.write_bytes(old_out)

rw=next((x for x in candidate_receipt.get('findings',[]) if x.get('code')=='REAL_WORLD_GENERALIZATION_SCOPE'),{})
science=next((x for x in candidate_receipt.get('findings',[]) if x.get('code')=='REAL_SCIENCE_DATA_TRANSFER_NATIVE_EVOLUTION_V1'),{})
checks={
 'candidate_executes':candidate_receipt.get('status')=='PASS_YADO_UNIFIED_CORE_DEEP_SELF_AUDIT_V1',
 'math_not_reopened':rw.get('evidence',{}).get('math_proven') is True,
 'program_not_reopened':rw.get('evidence',{}).get('program_proven') is True,
 'science_remains_unproven':rw.get('evidence',{}).get('science_proven') is False,
 'science_specific_blocker_present':science.get('blocking') is True and science.get('status')=='FAIL',
 'next_step_specific':candidate_receipt.get('self_selected_next_step')=='REAL_SCIENCE_DATA_TRANSFER_NATIVE_EVOLUTION_V1',
 'canonical_head_immutable':ledger.get('current_head_digest')==head.get('canonical_head_digest'),
}
passed=all(checks.values())
candidate_digest=h({'source_sha256':fsha(CAND_SRC),'checks':checks,'next':candidate_receipt.get('self_selected_next_step')})
meta={
 'schema':'yado.g2.deep_self_audit_evidence_selector_candidate.v4',
 'component_id':'ALG-G2-DEEP-SELF-AUDIT-V1','implementation_version':4,
 'candidate_digest':candidate_digest,'candidate_source_sha256':fsha(CAND_SRC),
 'source_runtime_sha256':fsha(SOURCE),'generation':ledger['current_head'],'parent_head_digest':head['canonical_head_digest'],
 'source_counterexample_receipt':old_receipt['receipt_sha256'],'checks':checks,
 'canonical_active':False,'promotion_applied':False,
 'state':'AUTHORIZED_FOR_SHADOW_ADMISSION' if passed else 'WITHHELD_AUDIT_EVOLUTION_V4',
 'semantic_boundary':'SELF-AUDIT EVIDENCE-SELECTION REPAIR. UPDATES WHICH VERIFIED TRANSFER EVIDENCE IS CURRENT; DOES NOT CREATE NEW COGNITIVE CAPABILITY.'
}
CAND_META.write_text(json.dumps(meta,indent=2,sort_keys=True)+'\n')
next_cap='REAL_WORLD_EVIDENCE_AUDIT_FRESH_ADMISSION_V1' if passed else 'REAL_WORLD_EVIDENCE_AUDIT_SELF_EVOLUTION_V2'
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.real_world_evidence_audit_self_evolution.v1',
 'status':'PASS_REAL_WORLD_EVIDENCE_AUDIT_SELF_EVOLUTION_V1' if passed else 'WITHHOLD_REAL_WORLD_EVIDENCE_AUDIT_SELF_EVOLUTION_V1',
 'candidate_digest':candidate_digest,'candidate_source_sha256':fsha(CAND_SRC),'checks':checks,
 'candidate_next_step':candidate_receipt.get('self_selected_next_step'),
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,'semantic_boundary':meta['semantic_boundary']}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

ledger=load(LEDGER)
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_REAL_WORLD_EVIDENCE_AUDIT_SELF_EVOLUTION",
 'event_type':'KERNEL_SELF_AUDIT_EVIDENCE_SELECTOR_EVOLUTION','status':'PASS_SHADOW' if passed else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'REAL_WORLD_GENERALIZATION_SCOPE',
 'effect':f"AUDIT_STALE_EVIDENCE_REPAIR; NEXT={next_cap}",
 'source_path':f'receipts/yado-real-world-evidence-audit-self-evolution-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'checks':checks,'candidate_next_step':candidate_receipt.get('self_selected_next_step'),'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('AUDIT_EVIDENCE_SELF_EVOLUTION_WITHHELD')
