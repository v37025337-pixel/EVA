from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,subprocess,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
EXP=REPO/'canonical/yado-unified-experience-registry-v1.json'
PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
CTX=REPO/'canonical/yado-unified-context-kernel-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
QMAN=REPO/'quarantine/yado-g2-quarantine-manifest-v1.json'
REQ=REPO/'architecture/yado-g2-physical-branch-closure-verify-v1-request.json'
OUT=ROOT/'yado_g2_physical_branch_closure_verify_v1_receipt.json'
GUARD=ROOT/'yado_canonical_invariant_guard_v1.py'
FRONT='KERNEL_G2_RAW_REPRESENTATION_V5_CANONICAL_ADMISSION_V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,f):x=copy.deepcopy(o);x.pop(f,None);return h(x)
def git(*args):
    p=subprocess.run(['git',*args],cwd=REPO,capture_output=True,text=True,timeout=60)
    if p.returncode!=0:raise RuntimeError('GIT_FAILED:'+repr(args)+':'+p.stderr[-2000:])
    return p.stdout.strip()

head,core,exp,prov,ctx,ledger,qman,req=map(load,[HEAD,CORE,EXP,PROV,CTX,LEDGER,QMAN,REQ])
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=[FRONT]:raise RuntimeError('UNEXPECTED_FRONTIER')
merge_sha=req['physical_closure_merge_commit']
legacy=[b for b in exp.get('branches',[]) if b.get('mode')=='EXPERIENCE_ONLY']
active=[b for b in exp.get('branches',[]) if b.get('mode')=='ACTIVE_LINEAGE']
if len(legacy)!=13 or len(active)!=1:raise RuntimeError('BRANCH_REGISTRY_DRIFT')

git('fetch','--all','--prune')
parents=git('rev-list','--parents','-n','1',merge_sha).split()
if not parents or parents[0]!=merge_sha:raise RuntimeError('MERGE_COMMIT_NOT_FOUND')
parent_set=set(parents[1:])
registered_legacy_tips={b['head_sha'] for b in legacy}
missing_parents=sorted(registered_legacy_tips-parent_set)
if missing_parents:raise RuntimeError('LEGACY_HEADS_NOT_IN_MERGE_PARENTS:'+json.dumps(missing_parents))

remote_lines=git('ls-remote','--heads','origin').splitlines()
remote={}
for line in remote_lines:
    sha,ref=line.split()[:2]
    remote[ref.removeprefix('refs/heads/')]=sha
operational=[b.get('branch') for b in exp.get('branches',[])]
missing_refs=[b for b in operational if b not in remote]
legacy_not_on_merge=[b for b in operational if b!=active[0]['branch'] and remote.get(b)!=merge_sha]
if missing_refs or legacy_not_on_merge:
    raise RuntimeError('PHYSICAL_REF_PREVERIFY_FAILED:'+json.dumps({'missing':missing_refs,'legacy_not_on_merge':legacy_not_on_merge}))

# The active branch may already be ahead by metadata commits; the merge commit must remain its ancestor.
active_ref=active[0]['branch']
ancestor=subprocess.run(['git','merge-base','--is-ancestor',merge_sha,'HEAD'],cwd=REPO)
if ancestor.returncode!=0:raise RuntimeError('CLOSURE_MERGE_NOT_ANCESTOR_OF_ACTIVE_HEAD')

# Mark the verified physical closure in canonical metadata. History remains retrievable by registered immutable SHA.
qman['status']='PHYSICAL_REF_CONVERGENCE_VERIFIED'
qman['physical_ref_closure']={
 'closure_merge_commit':merge_sha,
 'legacy_registered_heads_in_merge_parent_set':13,
 'legacy_named_refs_at_closure_commit':13,
 'active_branch':active_ref,
 'verification':'GIT_PARENT_SET_PLUS_REMOTE_REF_READBACK',
 'final_metadata_ref_sync_required':True
}
qman['manifest_digest']=cdig(qman,'manifest_digest');write(QMAN,qman)

for b in legacy:
    b['physical_ref_closure_verified']=True
    b['physical_ref_closure_merge_commit']=merge_sha
exp.setdefault('closure',{})['physical_ref_convergence']='VERIFIED'
exp['closure']['physical_ref_closure_merge_commit']=merge_sha
exp['policy']['physical_branch_ref_convergence_required']=False
exp['registry_digest']=cdig(exp,'registry_digest');write(EXP,exp)

prov['current_g2_binding'].update({
 'current_execution_label':'G2_SINGLE_LINEAGE_PHYSICALLY_CLOSED_WITH_APPLIED_EXPERIENCE',
 'physical_branch_closure_merge_commit':merge_sha,
 'quarantine_manifest_digest':qman['manifest_digest']
})
prov['registry_digest']=cdig(prov,'registry_digest');write(PROV,prov)

core['experience_registry_digest']=exp['registry_digest']
core['algorithm_provenance_registry_digest']=prov['registry_digest']
core['quarantine']['manifest_digest']=qman['manifest_digest']
core['quarantine']['physical_ref_convergence']='VERIFIED'
core['quarantine']['physical_ref_closure_merge_commit']=merge_sha
core['core_digest']=cdig(core,'core_digest');write(CORE,core)

ctx['branch_policy']['physical_branch_ref_convergence_required']=False
ctx['branch_policy']['physical_branch_ref_convergence']='VERIFIED'
ctx['branch_policy']['physical_branch_closure_merge_commit']=merge_sha
ctx['branch_policy']['all_historical_heads_preserved_in_g2_ancestry']=True
write(CTX,ctx)

prev=head['canonical_head_digest']
head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest']
head['algorithm_provenance_registry']['current_execution_label']=prov['current_g2_binding']['current_execution_label']
head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest']
head['unified_core']['experience_registry_digest']=exp['registry_digest']
head['unified_core']['core_digest']=core['core_digest']
head['quarantine']['manifest_digest']=qman['manifest_digest']
head['branch_history_closure']['physical_ref_convergence_required']=False
head['branch_history_closure']['physical_ref_convergence']='VERIFIED'
head['branch_history_closure']['physical_branch_closure_merge_commit']=merge_sha
head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)

ledger['current_head_digest']=head['canonical_head_digest']
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
 'schema':'yado.g2.physical_branch_closure_verify.receipt.v1',
 'status':'PASS_G2_PHYSICAL_BRANCH_CLOSURE_VERIFY_V1',
 'closure_merge_commit':merge_sha,
 'registered_legacy_heads_in_parent_set':len(registered_legacy_tips),
 'legacy_named_refs_verified_at_merge_commit':len(legacy),
 'active_merge_ancestor_verified':True,
 'quarantine_manifest_digest':qman['manifest_digest'],
 'experience_registry_digest':exp['registry_digest'],
 'frontier_unchanged':FRONT,
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest'],
 'canonical_mutation':True,'canonical_mechanism_mutation':False,'architecture_mutation':False,
 'generation_transition':False,'g3_genesis_performed':False,
 'semantic_boundary':'ALL HISTORICAL YADO BRANCH HEADS ARE PRESERVED AS PARENTS OF ONE G2 CLOSURE MERGE; LEGACY CONTROL-PLANE WORKFLOWS ARE QUARANTINED; REGISTERED HISTORICAL EVIDENCE REMAINS READ-ONLY.'
}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)
e={
 'index':len(ledger['events']),
 'event_id':f"E{len(ledger['events'])+1:04d}_G2_PHYSICAL_BRANCH_CLOSURE_VERIFY_V1",
 'event_type':'G2_PHYSICAL_BRANCH_CLOSURE_VERIFICATION',
 'status':'PASS','generation':ledger['current_head'],
 'deficit':'G2_PHYSICAL_BRANCH_DIVERGENCE',
 'effect':f"CLOSURE_MERGE={merge_sha}; LEGACY_HEAD_PARENTS=13; LEGACY_REFS_VERIFIED=13; FRONTIER_UNCHANGED={FRONT}",
 'source_path':f'receipts/yado-g2-physical-branch-closure-verify-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':True,'canonical_mechanism_mutation':False,'architecture_mutation':False,
 'promotion_applied':False,'generation_transition':False,'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']
}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);write(LEDGER,ledger)

post=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=60)
if post.returncode!=0:raise RuntimeError('POST_PHYSICAL_CLOSURE_GUARD_FAILED:'+post.stdout[-5000:]+post.stderr[-2000:])
print(json.dumps({'status':receipt['status'],'closure_merge_commit':merge_sha,'legacy_heads':13,'legacy_refs':13,'frontier':FRONT},indent=2,sort_keys=True))
