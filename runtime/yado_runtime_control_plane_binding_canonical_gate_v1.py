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
CAND=REPO/'candidates'/'g2-self-repair'/'runtime-control-plane-binding-v1.py'
META=REPO/'candidates'/'g2-self-repair'/'runtime-control-plane-binding-v1.json'
REPAIR=REPO/'receipts'/'yado-runtime-control-plane-binding-self-repair-v1-run-33391606240.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
OUT=ROOT/'yado_runtime_control_plane_binding_canonical_gate_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);core=load(CORE);meta=load(META);repair=load(REPAIR);ledger=load(LEDGER)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['RUNTIME_CONTROL_PLANE_BINDING_CANONICAL_GATE_V1']:
    raise RuntimeError('UNEXPECTED_FRONTIER')
if repair.get('status')!='PASS_RUNTIME_CONTROL_PLANE_BINDING_REPAIR_V1':
    raise RuntimeError('SHADOW_REPAIR_NOT_PASS')
if meta.get('state')!='AUTHORIZED_FOR_SHADOW_REPAIR':
    raise RuntimeError('CANDIDATE_NOT_AUTHORIZED')
if fsha(RUNTIME)!=meta.get('source_runtime_sha256'):
    raise RuntimeError('SOURCE_RUNTIME_DRIFT')
if fsha(CAND)!=meta.get('candidate_runtime_sha256'):
    raise RuntimeError('CANDIDATE_RUNTIME_DRIFT')
if not all(meta.get('checks',{}).values()):
    raise RuntimeError('CANDIDATE_CHECKS_NOT_ALL_PASS')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):
    raise RuntimeError('HEAD_LEDGER_MISMATCH')

old_src=RUNTIME.read_text(encoding='utf-8')
new_src=CAND.read_text(encoding='utf-8')
replacements=meta['replacements']
def normalize(text):
    x=text
    for old,new in replacements.items():
        x=x.replace(old,'<CONTROL_PLANE_PATH>').replace(new,'<CONTROL_PLANE_PATH>')
    return x
bounded=normalize(old_src)==normalize(new_src)
if not bounded:raise RuntimeError('UNBOUNDED_RUNTIME_DIFF')

# Fresh candidate execution, independent of previous shadow run.
tmp=ROOT/'_canonical_gate_candidate_unified_core.py'
tmp.write_text(new_src,encoding='utf-8')
try:
    spec=importlib.util.spec_from_file_location('_canonical_gate_candidate_unified_core',tmp)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    obj=mod.UnifiedYADOCoreV1(REPO)
    audit=obj.audit()
    snap=obj.snapshot()
    q_logic=obj.experience_search(['logic','thinking'],limit=4)
    q_repair=obj.experience_search(['self_repair','integrity'],limit=4)
finally:
    try:tmp.unlink()
    except FileNotFoundError:pass

fresh_checks={
 'bounded_diff_only':bounded,
 'candidate_audit_pass':audit.get('pass') is True,
 'canonical_manifest_loaded':obj.manifest.get('canonical_active') is True,
 'canonical_experience_loaded':obj.experience.get('canonical_active') is True,
 'experience_logic_retrieval':any(x.get('branch')=='yado-v29-cognitive' for x in q_logic),
 'experience_repair_retrieval':any(x.get('branch')=='yado-kernel-task-v37-repair' for x in q_repair),
 'no_candidate_control_plane_paths':'candidates/unified-core-v1/' not in new_src,
}
passed=all(fresh_checks.values())
if not passed:
    status='WITHHOLD_RUNTIME_CONTROL_PLANE_BINDING_CANONICAL_GATE_V1'
    next_cap='RUNTIME_CONTROL_PLANE_BINDING_REPAIR_V1'
    canonical_mutation=False
    post_head_digest=None
    post_core_digest=None
else:
    # Apply exactly the verified candidate runtime.
    RUNTIME.write_text(new_src,encoding='utf-8')
    runtime_sha=fsha(RUNTIME)

    new_core=copy.deepcopy(core)
    new_core.pop('core_digest',None)
    new_core['runtime_sha256']=runtime_sha
    new_core['control_plane_binding']='CANONICAL'
    new_core['control_plane_binding_gate_run_id']=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
    new_core['core_digest']=h(new_core)
    CORE.write_text(json.dumps(new_core,indent=2,sort_keys=True)+'\n')

    new_head=copy.deepcopy(head)
    new_head.pop('canonical_head_digest',None)
    new_head['unified_core']['runtime_sha256']=runtime_sha
    new_head['unified_core']['core_digest']=new_core['core_digest']
    new_head['unified_core']['control_plane_binding']='CANONICAL'
    new_head['unified_core']['control_plane_binding_gate_run_id']=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
    new_head['canonical_head_digest']=h(new_head)
    HEAD.write_text(json.dumps(new_head,indent=2,sort_keys=True)+'\n')

    post_head_digest=new_head['canonical_head_digest'];post_core_digest=new_core['core_digest']
    status='PASS_RUNTIME_CONTROL_PLANE_BINDING_CANONICAL_GATE_V1'
    next_cap='UNIFIED_CORE_POST_CONTROL_PLANE_SELF_AUDIT_V1'
    canonical_mutation=True

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
 'schema':'yado.g2.runtime_control_plane_binding_canonical_gate.v1',
 'status':status,'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),
 'source_candidate_digest':meta['candidate_digest'],
 'source_runtime_sha256':meta['source_runtime_sha256'],
 'candidate_runtime_sha256':meta['candidate_runtime_sha256'],
 'fresh_checks':fresh_checks,'candidate_audit':audit,'candidate_snapshot':snap,
 'canonical_mutation':canonical_mutation,'promotion_applied':False,'generation_transition':False,
 'post_core_digest':post_core_digest,'post_head_digest':post_head_digest,
 'next_required_capability':next_cap,
 'semantic_boundary':'INTERNAL SAME-GENERATION G2 CONTROL-PLANE REBINDING. ONLY VERIFIED PATH LITERALS MAY CHANGE IN RUNTIME SOURCE; NO COGNITIVE ALGORITHM CHANGE AND NO G3 GENESIS.'
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_RUNTIME_CONTROL_PLANE_CANONICAL_GATE",
   'event_type':'GENERATION_INTERNAL_SELF_REPAIR_ADMISSION','status':'PASS' if passed else 'WITHHOLD',
   'generation':ledger['current_head'],'deficit':'RUNTIME_CONTROL_PLANE_BINDING_CANONICAL_GATE_V1',
   'effect':'RUNTIME_CONTROL_PLANE_REBOUND_TO_CANONICAL_CONFIG' if passed else 'RUNTIME_CONTROL_PLANE_CANONICAL_GATE_WITHHELD',
   'source_path':f'receipts/yado-runtime-control-plane-binding-canonical-gate-v1-run-{run_id}.json',
   'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
   'canonical_mutation':canonical_mutation,'promotion_applied':False,'generation_transition':False}
if passed:
    e['previous_head_digest']=ledger['current_head_digest']
    e['new_head_digest']=post_head_digest
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
if passed:
    ledger['current_head_digest']=post_head_digest
ledger['open_deficits']=[next_cap]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({'status':status,'fresh_checks':fresh_checks,'post_core_digest':post_core_digest,
 'post_head_digest':post_head_digest,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('CONTROL_PLANE_CANONICAL_GATE_WITHHELD')
