from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,subprocess,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path[:0]=[str(ROOT),str(ROOT/'yado_rc8_v36')]

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
ART=REPO/'canonical/yado-g2-cognitive-continuity-checkpoint-v1.json'
GUARD=ROOT/'yado_canonical_invariant_guard_v1.py'
OUT=ROOT/'yado_g2_continuity_v5_metadata_digest_rebind_v1_receipt.json'

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def cdig(o,field):
    x=copy.deepcopy(o);x.pop(field,None);return h(x)
def write(p,o):
    Path(p).write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

head,core,prov,ledger,art=map(load,[HEAD,CORE,PROV,LEDGER,ART])
validate_ledger_v2(ledger)
if art.get('component_id')!='RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V5':
    raise RuntimeError('CONTINUITY_ARTIFACT_NOT_V5')
ad=art.get('canonical_component_digest')
if not ad or ad!=cdig(art,'canonical_component_digest'):
    raise RuntimeError('CONTINUITY_ARTIFACT_DIGEST_INVALID')
if core.get('cognitive_continuity_checkpoint_v1',{}).get('component_id')!='RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V5':
    raise RuntimeError('CORE_CONTINUITY_NOT_V5')
if 'RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V5' not in head.get('active_capabilities',[]):
    raise RuntimeError('HEAD_V5_NOT_ACTIVE')

prev=head['canonical_head_digest']
front=head['current_frontier']

prov['current_g2_binding']['cognitive_continuity_canonical_component_digest']=ad
prov['registry_digest']=cdig(prov,'registry_digest')
write(PROV,prov)

core['cognitive_continuity_checkpoint_v1']['canonical_component_digest']=ad
core['algorithm_provenance_registry_digest']=prov['registry_digest']
core['core_digest']=cdig(core,'core_digest')
write(CORE,core)

head.setdefault('cognitive_continuity_checkpoint_v1',{})['canonical_component_digest']=ad
head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest']
head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest']
head['unified_core']['core_digest']=core['core_digest']
head['canonical_head_digest']=cdig(head,'canonical_head_digest')
write(HEAD,head)

ledger['current_head_digest']=head['canonical_head_digest']
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
 'schema':'yado.g2.continuity_v5_metadata_digest_rebind.receipt.v1',
 'status':'PASS_G2_CONTINUITY_V5_METADATA_DIGEST_REBIND_V1',
 'component_id':'RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V5',
 'canonical_component_digest':ad,
 'previous_head_digest':prev,
 'new_head_digest':head['canonical_head_digest'],
 'frontier_unchanged':front,
 'architecture_mutation':False,
 'generation_transition':False,
 'g3_genesis_performed':False,
 'semantic_boundary':'METADATA DIGEST REBIND ONLY. NO RUNTIME BEHAVIOR CHANGE.'
}
receipt['receipt_sha256']=h(receipt)
write(OUT,receipt)
rp=REPO/'receipts'/f'yado-g2-continuity-v5-metadata-digest-rebind-v1-run-{run_id}.json'
write(rp,receipt)

e={
 'index':len(ledger['events']),
 'event_id':f"E{len(ledger['events'])+1:04d}_G2_CONTINUITY_V5_METADATA_DIGEST_REBIND_V1",
 'event_type':'G2_CONTINUITY_V5_METADATA_DIGEST_REBIND','status':'PASS_CANONICAL',
 'generation':ledger['current_head'],
 'deficit':'CONTINUITY_CANONICAL_COMPONENT_DIGEST_STALE_BINDING',
 'effect':f"REBIND_CONTINUITY_CANONICAL_COMPONENT_DIGEST={ad}; RUNTIME_BEHAVIOR_UNCHANGED=True; FRONTIER_UNCHANGED={front}",
 'source_path':str(rp.relative_to(REPO)),'source_digest':receipt['receipt_sha256'],
 'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':True,'canonical_mechanism_mutation':False,
 'architecture_mutation':False,'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']
}
e['event_hash']=event_hash(e)
ledger['events'].append(e)
ledger['event_count']=len(ledger['events'])
ledger['tail_event_hash']=e['event_hash']
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger)
write(LEDGER,ledger)

post=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=90)
if post.returncode!=0:
    raise RuntimeError('POST_METADATA_REBIND_GUARD_FAILED:'+post.stdout[-7000:]+post.stderr[-3000:])
print(json.dumps(receipt,indent=2,sort_keys=True))
