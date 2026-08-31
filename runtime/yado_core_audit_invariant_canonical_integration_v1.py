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
RUNTIME=REPO/'runtime'/'yado_unified_core_v1.py'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
CAND=REPO/'candidates'/'g2-self-evolution'/'unified_core_audit_invariant_v2.py'
META=REPO/'candidates'/'g2-self-evolution'/'unified_core_audit_invariant_v2.json'
ADMIT=REPO/'receipts'/'yado-core-audit-invariant-fresh-admission-v1-run-33397076738.json'
OUT=ROOT/'yado_core_audit_invariant_canonical_integration_v1_receipt.json'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p): return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);core=load(CORE);ledger=load(LEDGER);meta=load(META);admit=load(ADMIT)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['CORE_AUDIT_INVARIANT_CANONICAL_INTEGRATION_V1']:
    raise RuntimeError('UNEXPECTED_FRONTIER')
if admit.get('status')!='PASS_CORE_AUDIT_INVARIANT_FRESH_ADMISSION_V1':
    raise RuntimeError('FRESH_ADMISSION_NOT_PASS')
if meta.get('state')!='AUTHORIZED_FOR_SHADOW_ADMISSION':
    raise RuntimeError('CANDIDATE_NOT_AUTHORIZED')
if fsha(CAND)!=meta.get('candidate_source_sha256'):
    raise RuntimeError('CANDIDATE_DRIFT')
if fsha(RUNTIME)!=meta.get('source_runtime_sha256'):
    raise RuntimeError('SOURCE_RUNTIME_DRIFT')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):
    raise RuntimeError('HEAD_LEDGER_MISMATCH')

old=RUNTIME.read_text(encoding='utf-8')
new=CAND.read_text(encoding='utf-8')
old_lines=old.splitlines();new_lines=new.splitlines()
diff=[(i+1,a,b) for i,(a,b) in enumerate(zip(old_lines,new_lines)) if a!=b]
if len(old_lines)!=len(new_lines):
    raise RuntimeError('UNEXPECTED_LINE_COUNT_CHANGE')
expected_old="'raw_grounding_frontier_preserved':self.manifest.get('current_frontier')=='G2_RAW_TASK_REPRESENTATION_AND_GROUNDING_V1'"
expected_new="'developmental_frontier_coherent':bool(self.manifest.get('current_frontier')) and self.manifest.get('current_frontier')==self.head.get('current_frontier') and isinstance(self.ledger.get('open_deficits'),list) and len(self.ledger.get('open_deficits'))>=1"
bounded=(len(diff)==1 and expected_old in diff[0][1] and expected_new in diff[0][2])

# Fresh execute candidate against current canonical state.
tmp=ROOT/'_audit_invariant_candidate_gate.py'
tmp.write_text(new,encoding='utf-8')
try:
    sp=importlib.util.spec_from_file_location('_audit_invariant_candidate_gate',tmp)
    mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod)
    obj=mod.UnifiedYADOCoreV1(REPO)
    audit=obj.audit()
    snap=obj.snapshot()
finally:
    try: tmp.unlink()
    except FileNotFoundError: pass

checks={
 'bounded_single_line_audit_diff':bounded,
 'fresh_admission_all_checks':all(admit.get('checks',{}).values()),
 'candidate_current_audit_pass':audit.get('pass') is True,
 'general_frontier_check_present':'developmental_frontier_coherent' in audit.get('checks',{}),
 'old_hardcoded_frontier_check_absent':'raw_grounding_frontier_preserved' not in audit.get('checks',{}),
 'head_ledger_coherent':ledger.get('current_head_digest')==head.get('canonical_head_digest'),
}
passed=all(checks.values())

post_head=None;post_core=None
if passed:
    RUNTIME.write_text(new,encoding='utf-8')
    runtime_sha=fsha(RUNTIME)

    new_core=copy.deepcopy(core);new_core.pop('core_digest',None)
    new_core['runtime_sha256']=runtime_sha
    new_core['audit_invariant']={
      'id':'HEAD_MANIFEST_CONSISTENT_WITH_LEDGER',
      'candidate_digest':meta['candidate_digest'],
      'fresh_admission_receipt_sha256':admit['receipt_sha256'],
      'canonical_integration_run_id':str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
    }
    if 'runtime/yado_core_audit_invariant_self_evolution_v1.py' not in new_core.get('active_runtime_sources',[]):
        new_core['active_runtime_sources']=sorted(set(new_core.get('active_runtime_sources',[])+[
          'runtime/yado_core_audit_invariant_self_evolution_v1.py'
        ]))
    new_core['core_digest']=h(new_core)
    CORE.write_text(json.dumps(new_core,indent=2,sort_keys=True)+'\n')

    new_head=copy.deepcopy(head);new_head.pop('canonical_head_digest',None)
    new_head['unified_core']['runtime_sha256']=runtime_sha
    new_head['unified_core']['core_digest']=new_core['core_digest']
    new_head['unified_core']['audit_invariant']='HEAD_MANIFEST_CONSISTENT_WITH_LEDGER'
    new_head['canonical_head_digest']=h(new_head)
    HEAD.write_text(json.dumps(new_head,indent=2,sort_keys=True)+'\n')
    post_head=new_head['canonical_head_digest'];post_core=new_core['core_digest']
    status='PASS_CORE_AUDIT_INVARIANT_CANONICAL_INTEGRATION_V1'
    next_cap='LEGACY_EXPERIENCE_RETRIEVAL_CANONICAL_INTEGRATION_V1'
else:
    status='WITHHOLD_CORE_AUDIT_INVARIANT_CANONICAL_INTEGRATION_V1'
    next_cap='CORE_AUDIT_INVARIANT_EVOLUTION_REPAIR_V2'

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
 'schema':'yado.g2.core_audit_invariant_canonical_integration.v1',
 'status':status,'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),
 'candidate_digest':meta['candidate_digest'],'fresh_admission_receipt':admit['receipt_sha256'],
 'diff':[{'line':i,'old':a,'new':b} for i,a,b in diff],
 'fresh_audit':audit,'checks':checks,
 'canonical_mutation':passed,'promotion_applied':False,'generation_transition':False,
 'post_core_digest':post_core,'post_head_digest':post_head,
 'next_required_capability':next_cap,
 'semantic_boundary':'SAME-GENERATION CANONICALIZATION OF A SELF-EVOLVED AUDIT INVARIANT. ONLY ONE AUDIT CHECK LINE MAY CHANGE; COGNITIVE ALGORITHMS ARE UNCHANGED.'
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),
   'event_id':f"E{len(ledger['events'])+1:04d}_G2_CORE_AUDIT_INVARIANT_CANONICAL_INTEGRATION",
   'event_type':'GENERATION_INTERNAL_SELF_EVOLVED_AUDIT_ADMISSION',
   'status':'PASS' if passed else 'WITHHOLD','generation':ledger['current_head'],
   'deficit':'CORE_AUDIT_INVARIANT_CANONICAL_INTEGRATION_V1',
   'effect':'SELF_EVOLVED_GENERAL_FRONTIER_AUDIT_INVARIANT_CANONICAL' if passed else 'AUDIT_INVARIANT_CANONICAL_INTEGRATION_WITHHELD',
   'source_path':f'receipts/yado-core-audit-invariant-canonical-integration-v1-run-{run_id}.json',
   'source_digest':receipt['receipt_sha256'],'run_id':run_id,
   'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':passed,
   'promotion_applied':False,'generation_transition':False}
if passed:
    e['previous_head_digest']=ledger['current_head_digest'];e['new_head_digest']=post_head
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
if passed: ledger['current_head_digest']=post_head
ledger['open_deficits']=[next_cap]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({'status':status,'checks':checks,'post_head_digest':post_head,
 'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed: raise SystemExit('AUDIT_INVARIANT_CANONICAL_INTEGRATION_WITHHELD')
