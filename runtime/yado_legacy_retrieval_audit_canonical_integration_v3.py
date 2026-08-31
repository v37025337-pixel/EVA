from __future__ import annotations
from pathlib import Path
import copy,hashlib,importlib.util,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(PKG))

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
CORE=REPO/'canonical'/'yado-unified-core-v1.json'
AUDIT_RUNTIME=REPO/'runtime'/'yado_unified_core_deep_self_audit_v1.py'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
SRC=REPO/'candidates'/'g2-self-evolution'/'unified_core_legacy_retrieval_audit_v3.py'
META=REPO/'candidates'/'g2-self-evolution'/'unified_core_legacy_retrieval_audit_v3.json'
ADMIT=REPO/'receipts'/'yado-legacy-retrieval-audit-fresh-admission-v3-run-33404677304.json'
OUT=ROOT/'yado_legacy_retrieval_audit_canonical_integration_v3_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);core=load(CORE);ledger=load(LEDGER);meta=load(META);admit=load(ADMIT)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['LEGACY_RETRIEVAL_AUDIT_CANONICAL_INTEGRATION_V3']:raise RuntimeError('UNEXPECTED_FRONTIER')
if admit.get('status')!='PASS_LEGACY_RETRIEVAL_AUDIT_FRESH_ADMISSION_V3':raise RuntimeError('V3_ADMISSION_NOT_PASS')
if meta.get('state')!='AUTHORIZED_FOR_SHADOW_ADMISSION':raise RuntimeError('V3_NOT_AUTHORIZED')
if fsha(SRC)!=meta.get('candidate_source_sha256'):raise RuntimeError('V3_SOURCE_DRIFT')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')

current=AUDIT_RUNTIME.read_text(encoding='utf-8');candidate=SRC.read_text(encoding='utf-8')
start="# Is the experience actually retrievable, or only summarized metadata?"
end="# ---------- capability/evidence scope ----------"
if start not in current or end not in current or start not in candidate or end not in candidate:raise RuntimeError('AUDIT_MARKERS_MISSING')
cprefix,crest=current.split(start,1);csection,csuffix=crest.split(end,1)
nprefix,nrest=candidate.split(start,1);nsection,nsuffix=nrest.split(end,1)
bounded=(cprefix==nprefix and csuffix==nsuffix and csection!=nsection)

# Fresh execute admitted candidate against current canonical state.
tmp=ROOT/'_legacy_retrieval_audit_v3_canonical_gate.py';tmp.write_text(candidate,encoding='utf-8')
try:
    sp=importlib.util.spec_from_file_location('_legacy_retrieval_audit_v3_canonical_gate',tmp)
    mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod)
    cand=json.loads((ROOT/'yado_unified_core_deep_self_audit_v1_receipt.json').read_text())
finally:
    try:tmp.unlink()
    except FileNotFoundError:pass

legacy=next(x for x in cand['findings'] if x['code']=='LEGACY_EXPERIENCE_CONTENT_RETRIEVAL')
raw=next(x for x in cand['findings'] if x['code']=='RAW_TASK_REPRESENTATION_GAP')
checks={
 'bounded_experience_audit_section_only':bounded,
 'fresh_admission_checks':all(admit.get('checks',{}).values()),
 'current_legacy_finding_pass':legacy.get('status')=='PASS',
 'live_probe_pass':legacy.get('evidence',{}).get('legacy_probe_ok') is True,
 'raw_regression_pass':raw.get('status')=='PASS',
 'candidate_next_is_real_world':cand.get('self_selected_next_step')=='REAL_WORLD_GENERALIZATION_SCOPE',
 'head_ledger_coherent':ledger.get('current_head_digest')==head.get('canonical_head_digest'),
}
passed=all(checks.values())
post_head=None;post_core=None
if passed:
    AUDIT_RUNTIME.write_text(candidate,encoding='utf-8')
    audit_sha=fsha(AUDIT_RUNTIME)

    new_core=copy.deepcopy(core);new_core.pop('core_digest',None)
    plane=next(x for x in new_core['planes'] if x.get('plane_id')=='SELF_AUDIT_AND_REPAIR')
    plane['active_components']=sorted(set(plane.get('active_components',[])+['ALG-G2-DEEP-SELF-AUDIT-V1']))
    new_core['active_runtime_sources']=sorted(set(new_core.get('active_runtime_sources',[])+['runtime/yado_unified_core_deep_self_audit_v1.py']))
    new_core['deep_self_audit']={
      'component_id':'ALG-G2-DEEP-SELF-AUDIT-V1',
      'source_sha256':audit_sha,
      'legacy_retrieval_detector':'MANIFEST_PLUS_RUNTIME_BEHAVIOR',
      'candidate_digest':meta['candidate_digest'],
      'fresh_admission_receipt_sha256':admit['receipt_sha256'],
      'canonical_integration_run_id':str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
    }
    new_core['current_frontier']='UNIFIED_CORE_POST_SELF_AUDIT_V3'
    new_core['core_digest']=h(new_core);CORE.write_text(json.dumps(new_core,indent=2,sort_keys=True)+'\n')

    new_head=copy.deepcopy(head);new_head.pop('canonical_head_digest',None)
    new_head['new_capabilities']=sorted(set(new_head.get('new_capabilities',[])+['ALG-G2-DEEP-SELF-AUDIT-V1']))
    new_head['unified_core']['core_digest']=new_core['core_digest']
    new_head['unified_core']['deep_self_audit_source_sha256']=audit_sha
    new_head['current_frontier']='UNIFIED_CORE_POST_SELF_AUDIT_V3'
    new_head['canonical_head_digest']=h(new_head);HEAD.write_text(json.dumps(new_head,indent=2,sort_keys=True)+'\n')
    post_head=new_head['canonical_head_digest'];post_core=new_core['core_digest']
    status='PASS_LEGACY_RETRIEVAL_AUDIT_CANONICAL_INTEGRATION_V3'
    next_cap='UNIFIED_CORE_POST_SELF_AUDIT_V3'
else:
    status='WITHHOLD_LEGACY_RETRIEVAL_AUDIT_CANONICAL_INTEGRATION_V3'
    next_cap='LEGACY_RETRIEVAL_AUDIT_EVOLUTION_REPAIR_V4'

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.legacy_retrieval_audit_canonical_integration.v3','status':status,
 'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),
 'candidate_digest':meta['candidate_digest'],'fresh_admission_receipt':admit['receipt_sha256'],
 'checks':checks,'canonical_mutation':passed,'promotion_applied':False,'generation_transition':False,
 'post_head_digest':post_head,'post_core_digest':post_core,'next_required_capability':next_cap,
 'semantic_boundary':'SAME-GENERATION CANONICALIZATION OF SELF-EVOLVED DEEP SELF-AUDIT DETECTION. RETRIEVER AND COGNITIVE ALGORITHMS ARE UNCHANGED.'}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_LEGACY_RETRIEVAL_AUDIT_CANONICAL_INTEGRATION_V3",
 'event_type':'GENERATION_INTERNAL_SELF_EVOLVED_AUDIT_ADMISSION_V3','status':'PASS' if passed else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'LEGACY_RETRIEVAL_AUDIT_CANONICAL_INTEGRATION_V3',
 'effect':'DEEP_SELF_AUDIT_CANONICAL_WITH_LIVE_LEGACY_RETRIEVAL_PROBE' if passed else 'LEGACY_RETRIEVAL_AUDIT_CANONICAL_WITHHELD',
 'source_path':f'receipts/yado-legacy-retrieval-audit-canonical-integration-v3-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':passed,'promotion_applied':False,'generation_transition':False}
if passed:e['previous_head_digest']=ledger['current_head_digest'];e['new_head_digest']=post_head
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
if passed:ledger['current_head_digest']=post_head
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':status,'checks':checks,'post_head_digest':post_head,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('LEGACY_RETRIEVAL_AUDIT_V3_CANONICAL_WITHHELD')
