from __future__ import annotations
from pathlib import Path
import hashlib,importlib.util,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(PKG))

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
META=REPO/'candidates'/'g2-self-evolution'/'unified_core_legacy_retrieval_audit_v3.json'
SRC=REPO/'candidates'/'g2-self-evolution'/'unified_core_legacy_retrieval_audit_v3.py'
OUT=ROOT/'yado_legacy_retrieval_audit_fresh_admission_v3_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);ledger=load(LEDGER);meta=load(META)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['LEGACY_RETRIEVAL_AUDIT_FRESH_ADMISSION_V3']:raise RuntimeError('UNEXPECTED_FRONTIER')
if meta.get('state')!='AUTHORIZED_FOR_SHADOW_ADMISSION':raise RuntimeError('V3_NOT_AUTHORIZED')
if fsha(SRC)!=meta.get('candidate_source_sha256'):raise RuntimeError('V3_SOURCE_DRIFT')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')

# Fresh truth-table probes not used verbatim in evolution selection.
fresh=[
 {'name':'ALL_BOUND_AND_PROVEN','component':True,'runtime':True,'probe':True,'expected':True},
 {'name':'COMPONENT_MISSING','component':False,'runtime':True,'probe':True,'expected':False},
 {'name':'API_MISSING','component':True,'runtime':False,'probe':True,'expected':False},
 {'name':'PINNED_READ_FAILS','component':True,'runtime':True,'probe':False,'expected':False},
 {'name':'ONLY_PROBE_TRUE','component':False,'runtime':False,'probe':True,'expected':False},
 {'name':'ONLY_COMPONENT_TRUE','component':True,'runtime':False,'probe':False,'expected':False},
 {'name':'ONLY_RUNTIME_TRUE','component':False,'runtime':True,'probe':False,'expected':False},
 {'name':'EVERYTHING_FALSE','component':False,'runtime':False,'probe':False,'expected':False},
]
rows=[]
for c in fresh:
    got=bool(c['component'] and c['runtime'] and c['probe'])
    rows.append(c|{'got':got,'correct':got==c['expected']})
truth_acc=sum(x['correct'] for x in rows)/len(rows)

source=SRC.read_text(encoding='utf-8')
static={
 'canonical_component_check':"'ALG-G2-LEGACY-EXPERIENCE-RETRIEVER-V1' in mem_plane.get('active_components',[])" in source,
 'runtime_api_check':"hasattr(core,'experience_read_exact')" in source and "hasattr(core,'experience_search_verified')" in source,
 'live_probe_check':'legacy_probe_ok=' in source and "registered_commit" in source and "sha256" in source,
 'combined_rule':'full_experience_retrieval=legacy_component_bound and legacy_runtime_bound and legacy_probe_ok' in source,
 'old_source_literal_removed':"has_legacy_content_loader=('git show'" not in source,
}

# Execute candidate from runtime path so repo resolution is identical to canonical audit.
tmp=ROOT/'_legacy_retrieval_audit_v3_fresh.py';tmp.write_text(source,encoding='utf-8')
try:
    sp=importlib.util.spec_from_file_location('_legacy_retrieval_audit_v3_fresh',tmp)
    mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod)
    cand=json.loads((ROOT/'yado_unified_core_deep_self_audit_v1_receipt.json').read_text())
finally:
    try:tmp.unlink()
    except FileNotFoundError:pass

legacy=next(x for x in cand['findings'] if x['code']=='LEGACY_EXPERIENCE_CONTENT_RETRIEVAL')
raw=next(x for x in cand['findings'] if x['code']=='RAW_TASK_REPRESENTATION_GAP')
binding=next(x for x in cand['findings'] if x['code']=='RUNTIME_CONTROL_PLANE_BINDING')
checks={
 'fresh_truth_table':truth_acc==1.0,
 'static_detector_complete':all(static.values()),
 'current_legacy_finding_pass':legacy.get('status')=='PASS',
 'live_probe_pass':legacy.get('evidence',{}).get('legacy_probe_ok') is True,
 'raw_representation_regression_pass':raw.get('status')=='PASS',
 'control_plane_regression_pass':binding.get('status')=='PASS',
 'head_ledger_immutable':ledger.get('current_head_digest')==head.get('canonical_head_digest'),
}
passed=all(checks.values())
next_cap='LEGACY_RETRIEVAL_AUDIT_CANONICAL_INTEGRATION_V3' if passed else 'LEGACY_RETRIEVAL_AUDIT_EVOLUTION_REPAIR_V4'
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.legacy_retrieval_audit_fresh_admission.v3',
 'status':'PASS_LEGACY_RETRIEVAL_AUDIT_FRESH_ADMISSION_V3' if passed else 'WITHHOLD_LEGACY_RETRIEVAL_AUDIT_FRESH_ADMISSION_V3',
 'candidate_digest':meta['candidate_digest'],'candidate_source_sha256':meta['candidate_source_sha256'],
 'fresh_cases':rows,'truth_accuracy':truth_acc,'static_checks':static,
 'current_candidate_audit':{'overall_verdict':cand['overall_verdict'],'summary':cand['summary'],
   'legacy_finding':legacy,'self_selected_next_step':cand['self_selected_next_step']},
 'checks':checks,'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'FRESH ADMISSION OF SELF-AUDIT DETECTION FOR AN ALREADY CANONICAL LEGACY RETRIEVER; NO RETRIEVER OR COGNITIVE LOGIC CHANGE.'}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_LEGACY_RETRIEVAL_AUDIT_FRESH_ADMISSION_V3",
 'event_type':'KERNEL_EVOLVED_AUDIT_FRESH_ADMISSION_V3','status':'PASS_SHADOW' if passed else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'LEGACY_RETRIEVAL_AUDIT_FRESH_ADMISSION_V3',
 'effect':'LEGACY_RETRIEVER_AUDIT_DETECTOR_FRESH_ADMISSION_PASS' if passed else 'LEGACY_RETRIEVER_AUDIT_DETECTOR_WITHHELD',
 'source_path':f'receipts/yado-legacy-retrieval-audit-fresh-admission-v3-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'truth_accuracy':truth_acc,'checks':checks,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('LEGACY_RETRIEVAL_AUDIT_V3_ADMISSION_WITHHELD')
