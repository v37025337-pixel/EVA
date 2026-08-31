from __future__ import annotations
from pathlib import Path
import hashlib,importlib.util,json,os,re,sys,tempfile,types

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
CORE=REPO/'canonical'/'yado-unified-core-v1.json'
EXP=REPO/'canonical'/'yado-unified-experience-registry-v1.json'
SOURCE=REPO/'runtime'/'yado_unified_core_v1.py'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
CAND=REPO/'candidates'/'g2-self-repair'/'runtime-control-plane-binding-v1.py'
META=REPO/'candidates'/'g2-self-repair'/'runtime-control-plane-binding-v1.json'
CAND.parent.mkdir(parents=True,exist_ok=True)
OUT=ROOT/'yado_runtime_control_plane_binding_self_repair_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);core=load(CORE);exp=load(EXP);ledger=load(LEDGER)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['RUNTIME_CONTROL_PLANE_BINDING_REPAIR_V1']:
    raise RuntimeError('UNEXPECTED_FRONTIER')
if core.get('core_id')!='UNIFIED_YADO_CORE_V1' or not core.get('canonical_active'):
    raise RuntimeError('CANONICAL_CORE_NOT_ACTIVE')
if exp.get('activation_mode')!='READ_ONLY_EXPERIENCE' or not exp.get('canonical_active'):
    raise RuntimeError('CANONICAL_EXPERIENCE_NOT_ACTIVE')
head_before=fsha(HEAD)

src=SOURCE.read_text(encoding='utf-8')
# Derive target paths from canonical state rather than from a task-specific patch dictionary.
canonical_manifest_rel=str(CORE.relative_to(REPO)).replace('\\','/')
canonical_experience_rel=core.get('experience_registry')
if canonical_experience_rel!=str(EXP.relative_to(REPO)).replace('\\','/'):
    raise RuntimeError('CANONICAL_EXPERIENCE_PATH_MISMATCH')

candidate_paths=sorted(set(re.findall(r"candidates/unified-core-v1/[A-Za-z0-9_.\-/]+\.json",src)))
replacements={}
for old in candidate_paths:
    if old.endswith('/manifest.json'):
        replacements[old]=canonical_manifest_rel
    elif old.endswith('/experience-registry.json'):
        replacements[old]=canonical_experience_rel

patched=src
for old,new in replacements.items():
    patched=patched.replace(old,new)

# The repair is bounded: only registered control-plane path literals may differ.
def normalized_without_paths(text):
    x=text
    for old,new in replacements.items():
        x=x.replace(new,'<CONTROL_PLANE_PATH>').replace(old,'<CONTROL_PLANE_PATH>')
    return x
bounded_diff=normalized_without_paths(src)==normalized_without_paths(patched)
no_candidate_control_paths='candidates/unified-core-v1/' not in patched
canonical_paths_present=canonical_manifest_rel in patched and canonical_experience_rel in patched

# Execute the candidate from a temporary file under runtime so __file__ resolves to the same repo layout.
tmp=ROOT/'_candidate_unified_core_binding_v1.py'
tmp.write_text(patched,encoding='utf-8')
try:
    spec=importlib.util.spec_from_file_location('_candidate_unified_core_binding_v1',tmp)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    obj=mod.UnifiedYADOCoreV1(REPO)
    audit=obj.audit()
    q1=obj.experience_search(['logic','thinking','intelligence'],limit=5)
    q2=obj.experience_search(['self_repair','integrity','fail_closed'],limit=5)
    snapshot=obj.snapshot()
finally:
    try:tmp.unlink()
    except FileNotFoundError:pass

runtime_binding_pass=(
    obj.manifest.get('canonical_active') is True
    and obj.experience.get('canonical_active') is True
    and obj.manifest.get('experience_registry')==canonical_experience_rel
)
retrieval_pass=any(x.get('branch')=='yado-v29-cognitive' for x in q1) and any(x.get('branch')=='yado-kernel-task-v37-repair' for x in q2)

checks={
 'bounded_path_only_patch':bounded_diff,
 'no_candidate_control_plane_paths':no_candidate_control_paths,
 'canonical_paths_present':canonical_paths_present,
 'candidate_runtime_loads':True,
 'candidate_runtime_binds_canonical_control_plane':runtime_binding_pass,
 'candidate_core_audit_pass':audit.get('pass') is True,
 'experience_retrieval_survives':retrieval_pass,
 'canonical_head_immutable':fsha(HEAD)==head_before and ledger.get('current_head_digest')==head.get('canonical_head_digest'),
}
passed=all(checks.values())

CAND.write_text(patched,encoding='utf-8')
meta={
 'schema':'yado.g2.runtime_control_plane_binding_candidate.v1',
 'generation':ledger['current_head'],'parent_head_digest':head['canonical_head_digest'],
 'source_runtime_sha256':fsha(SOURCE),'candidate_runtime_sha256':fsha(CAND),
 'replacements':replacements,'checks':checks,
 'state':'AUTHORIZED_FOR_SHADOW_REPAIR' if passed else 'WITHHOLD',
 'canonical_active':False,'promotion_applied':False,
 'semantic_boundary':'BOUNDED CONTROL-PLANE PATH REBINDING ONLY; NO COGNITIVE ALGORITHM OR CAPABILITY LOGIC CHANGE.'
}
meta['candidate_digest']=h(meta);META.write_text(json.dumps(meta,indent=2,sort_keys=True)+'\n')

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
next_cap='RUNTIME_CONTROL_PLANE_BINDING_CANONICAL_GATE_V1' if passed else 'RUNTIME_CONTROL_PLANE_BINDING_REPAIR_BLOCKED_V1'
receipt={
 'schema':'yado.g2.runtime_control_plane_binding_self_repair.receipt.v1',
 'status':'PASS_RUNTIME_CONTROL_PLANE_BINDING_REPAIR_V1' if passed else 'WITHHOLD_RUNTIME_CONTROL_PLANE_BINDING_REPAIR_V1',
 'replacements':replacements,'checks':checks,'candidate_digest':meta['candidate_digest'],
 'candidate_runtime_sha256':meta['candidate_runtime_sha256'],
 'candidate_audit':audit,'candidate_snapshot':snapshot,
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'KERNEL-NATIVE BOUNDED SELF-REPAIR OF ITS OWN CONTROL-PLANE PATH BINDING; HOST DID NOT SELECT THE LITERAL OLD/NEW PATH PAIR, WHICH WAS DERIVED FROM CANONICAL MANIFEST STATE.'
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_RUNTIME_CONTROL_PLANE_SELF_REPAIR",
   'event_type':'KERNEL_NATIVE_SELF_REPAIR_ATTEMPT','status':'PASS_SHADOW' if passed else 'WITHHOLD',
   'generation':ledger['current_head'],'deficit':'RUNTIME_CONTROL_PLANE_BINDING_REPAIR_V1',
   'effect':'CANONICAL_CONTROL_PLANE_BINDING_CANDIDATE_PASS' if passed else 'CONTROL_PLANE_BINDING_REPAIR_BLOCKED',
   'source_path':f'receipts/yado-runtime-control-plane-binding-self-repair-v1-run-{run_id}.json',
   'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
   'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({'status':receipt['status'],'replacements':replacements,'checks':checks,
 'candidate_runtime_sha256':meta['candidate_runtime_sha256'],'next_required_capability':next_cap,
 'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
