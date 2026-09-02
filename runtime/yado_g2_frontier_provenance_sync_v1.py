from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,subprocess,sys

REPO=Path(__file__).resolve().parents[1]; ROOT=REPO/'runtime'
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
REQ=REPO/'architecture/yado-g2-frontier-provenance-sync-v1-request.json'
OUT=ROOT/'yado_g2_frontier_provenance_sync_v1_receipt.json'
GUARD=ROOT/'yado_canonical_invariant_guard_v1.py'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):
    x=copy.deepcopy(o);x.pop(field,None);return h(x)

head,core,prov,ledger,req=map(load,[HEAD,CORE,PROV,LEDGER,REQ])
validate_ledger_v2(ledger)
front=(ledger.get('open_deficits') or [None])[0]
if not front or ledger.get('open_deficits')!=[front]:raise RuntimeError('EXPECTED_ONE_FRONTIER')
if req.get('expected_frontier')!=front:raise RuntimeError('REQUEST_FRONTIER_MISMATCH')
if head.get('current_frontier')!=front or core.get('current_frontier')!=front:raise RuntimeError('HEAD_CORE_FRONTIER_MISMATCH')
if head.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')

prev_head=head['canonical_head_digest'];prev_prov=prov['registry_digest']
prov['current_g2_binding']={
 'active_runtime_class':req['active_runtime_class'],
 'current_execution_label':req['current_execution_label'],
 'frontier':front,
 'frontier_native_method':req['frontier_native_method'],
 'frontier_native_owner':req['frontier_native_owner'],
 'generation':head['generation_id'],
 'historical_origin_label':req['historical_origin_label'],
 'frontier_binding_semantics':'CURRENT_DEVELOPMENTAL_FRONTIER_CONSUMER_NOT_GLOBAL_RUNTIME_IDENTITY'
}
prov['registry_digest']=cdig(prov,'registry_digest');write(PROV,prov)

core['algorithm_provenance_registry_digest']=prov['registry_digest']
core['current_frontier']=front
core['core_digest']=cdig(core,'core_digest');write(CORE,core)

head['algorithm_provenance_registry']['current_execution_label']=req['current_execution_label']
head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest']
head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest']
head['unified_core']['core_digest']=core['core_digest']
head['current_frontier']=front
head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)

ledger['current_head_digest']=head['canonical_head_digest']
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
idx=len(ledger['events'])
receipt_base={
 'schema':'yado.g2.frontier_provenance_sync.receipt.v1','status':'PASS_G2_FRONTIER_PROVENANCE_SYNC_V1',
 'generation':head['generation_id'],'frontier':front,'previous_head_digest':prev_head,'new_head_digest':head['canonical_head_digest'],
 'previous_registry_digest':prev_prov,'new_registry_digest':prov['registry_digest'],
 'binding':prov['current_g2_binding'],'canonical_mutation':True,'architecture_mutation':False,'generation_transition':False,'g3_genesis_performed':False
}
source_digest=h(receipt_base)
e={
 'index':idx,'event_id':f"E{idx+1:04d}_G2_FRONTIER_PROVENANCE_SYNC_V1",
 'event_type':'G2_FRONTIER_PROVENANCE_CANONICAL_SYNC','status':'PASS','generation':ledger['current_head'],
 'deficit':'G2_FRONTIER_PROVENANCE_SYNC_V1',
 'effect':f"FRONTIER={front}; METHOD={req['frontier_native_method']}; OWNER={req['frontier_native_owner']}; NEXT={front}",
 'source_path':f'receipts/yado-g2-frontier-provenance-sync-v1-run-{run_id}.json','source_digest':source_digest,'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':True,'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':prev_head,'new_head_digest':head['canonical_head_digest']
}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['open_deficits']=[front]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);write(LEDGER,ledger)

cp=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=60)
if cp.returncode!=0:raise RuntimeError('POST_SYNC_GUARD_FAILED:'+cp.stdout[-3000:]+cp.stderr[-1000:])
receipt={**receipt_base,'github_run_id':run_id,'guard_output':cp.stdout[-4000:]}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)
print(json.dumps(receipt,indent=2,sort_keys=True))
