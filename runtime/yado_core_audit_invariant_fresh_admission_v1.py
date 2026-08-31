from __future__ import annotations
from pathlib import Path
import copy,hashlib,importlib.util,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(PKG))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
META=REPO/'candidates'/'g2-self-evolution'/'unified_core_audit_invariant_v2.json'
SRC=REPO/'candidates'/'g2-self-evolution'/'unified_core_audit_invariant_v2.py'
OUT=ROOT/'yado_core_audit_invariant_fresh_admission_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);ledger=load(LEDGER);meta=load(META)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['CORE_AUDIT_INVARIANT_FRESH_ADMISSION_V1']:
    raise RuntimeError('UNEXPECTED_FRONTIER')
if meta.get('state')!='AUTHORIZED_FOR_SHADOW_ADMISSION':
    raise RuntimeError('AUDIT_CANDIDATE_NOT_AUTHORIZED')
if hashlib.sha256(SRC.read_bytes()).hexdigest()!=meta.get('candidate_source_sha256'):
    raise RuntimeError('AUDIT_CANDIDATE_SOURCE_DRIFT')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):
    raise RuntimeError('HEAD_LEDGER_MISMATCH')

sp=importlib.util.spec_from_file_location('unified_core_audit_candidate_fresh',SRC)
mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod)
obj=mod.UnifiedYADOCoreV1(REPO)

base_manifest=copy.deepcopy(obj.manifest)
base_head=copy.deepcopy(obj.head)
base_ledger=copy.deepcopy(obj.ledger)

cases=[
 {'name':'CURRENT','mf':base_manifest['current_frontier'],'hf':base_head['current_frontier'],
  'open':['CORE_AUDIT_INVARIANT_FRESH_ADMISSION_V1'],'expected_frontier_check':True},
 {'name':'FRESH_UNKNOWN_BUT_COHERENT','mf':'FUTURE_UNSEEN_FRONTIER_X91','hf':'FUTURE_UNSEEN_FRONTIER_X91',
  'open':['FUTURE_UNSEEN_FRONTIER_X91'],'expected_frontier_check':True},
 {'name':'MANIFEST_EMPTY','mf':'','hf':'FUTURE_UNSEEN_FRONTIER_X92',
  'open':['FUTURE_UNSEEN_FRONTIER_X92'],'expected_frontier_check':False},
 {'name':'HEAD_EMPTY','mf':'FUTURE_UNSEEN_FRONTIER_X93','hf':'',
  'open':['FUTURE_UNSEEN_FRONTIER_X93'],'expected_frontier_check':False},
 {'name':'HEAD_MANIFEST_SPLIT','mf':'FUTURE_A','hf':'FUTURE_B',
  'open':['FUTURE_A'],'expected_frontier_check':False},
 {'name':'EMPTY_LEDGER_BACKLOG','mf':'FUTURE_C','hf':'FUTURE_C',
  'open':[],'expected_frontier_check':False},
 {'name':'DIFFERENT_LEDGER_ITEM_BUT_NONEMPTY','mf':'FUTURE_D','hf':'FUTURE_D',
  'open':['DEPENDENCY_FOR_FUTURE_D'],'expected_frontier_check':True},
]
rows=[]
for c in cases:
    obj.manifest=copy.deepcopy(base_manifest);obj.head=copy.deepcopy(base_head);obj.ledger=copy.deepcopy(base_ledger)
    obj.manifest['current_frontier']=c['mf'];obj.head['current_frontier']=c['hf'];obj.ledger['open_deficits']=list(c['open'])
    a=obj.audit()
    got=a['checks'].get('developmental_frontier_coherent')
    rows.append({'name':c['name'],'expected':c['expected_frontier_check'],'got':got,'correct':got==c['expected_frontier_check']})

# Restore exact canonical objects and require full audit to pass.
obj.manifest=base_manifest;obj.head=base_head;obj.ledger=base_ledger
current_audit=obj.audit()

source=SRC.read_text(encoding='utf-8')
checks={
 'all_fresh_cases':all(x['correct'] for x in rows),
 'unseen_coherent_frontier_passes':next(x for x in rows if x['name']=='FRESH_UNKNOWN_BUT_COHERENT')['got'] is True,
 'split_brain_rejected':next(x for x in rows if x['name']=='HEAD_MANIFEST_SPLIT')['got'] is False,
 'empty_ledger_rejected':next(x for x in rows if x['name']=='EMPTY_LEDGER_BACKLOG')['got'] is False,
 'current_full_audit_pass':current_audit.get('pass') is True,
 'old_exact_frontier_literal_removed':"'raw_grounding_frontier_preserved'" not in source,
 'head_ledger_immutable':ledger.get('current_head_digest')==head.get('canonical_head_digest'),
}
passed=all(checks.values())
next_cap='CORE_AUDIT_INVARIANT_CANONICAL_INTEGRATION_V1' if passed else 'CORE_AUDIT_INVARIANT_EVOLUTION_REPAIR_V2'

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
 'schema':'yado.g2.core_audit_invariant_fresh_admission.receipt.v1',
 'status':'PASS_CORE_AUDIT_INVARIANT_FRESH_ADMISSION_V1' if passed else 'WITHHOLD_CORE_AUDIT_INVARIANT_FRESH_ADMISSION_V1',
 'candidate_digest':meta['candidate_digest'],'candidate_source_sha256':meta['candidate_source_sha256'],
 'selected_rule':meta['selected_rule'],'fresh_cases':rows,'current_audit':current_audit,'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'FRESH ADMISSION OF A GENERAL DEVELOPMENTAL-FRONTIER COHERENCE INVARIANT. HEAD/LEDGER, INTEGRITY, AND G3 CHECKS REMAIN UNCHANGED.'
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_CORE_AUDIT_INVARIANT_FRESH_ADMISSION",
   'event_type':'KERNEL_EVOLVED_AUDIT_FRESH_ADMISSION','status':'PASS_SHADOW' if passed else 'WITHHOLD',
   'generation':ledger['current_head'],'deficit':'CORE_AUDIT_INVARIANT_FRESH_ADMISSION_V1',
   'effect':'EVOLVED_FRONTIER_AUDIT_INVARIANT_FRESH_ADMISSION_PASS' if passed else 'EVOLVED_FRONTIER_AUDIT_INVARIANT_WITHHELD',
   'source_path':f'receipts/yado-core-audit-invariant-fresh-admission-v1-run-{run_id}.json',
   'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
   'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'fresh_cases':rows,'checks':checks,
 'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('CORE_AUDIT_INVARIANT_FRESH_ADMISSION_WITHHELD')
