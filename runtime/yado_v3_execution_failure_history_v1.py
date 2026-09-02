from __future__ import annotations
from pathlib import Path
import hashlib,json,os,sys

REPO=Path(__file__).resolve().parents[1]
ROOT=REPO/'runtime'
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

LEDGER=REPO/'architecture/evolution-ledger.json'
OUT=ROOT/'yado_v3_execution_failure_history_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def write(p,o):p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

ledger=json.loads(LEDGER.read_text(encoding='utf-8'))
validate_ledger_v2(ledger)
front='KERNEL_SCALE_CONDITIONAL_SUCCESSOR_HIGH_SCALE_REPAIR_V3'
if ledger.get('open_deficits')!=[front]:
    raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
if any(str(e.get('run_id'))==run_id for e in ledger.get('events',[])):
    print(json.dumps({'status':'ALREADY_RECORDED','run_id':run_id}))
    raise SystemExit(0)

receipt={
 'schema':'yado.g2.v3_execution_failure_history.receipt.v1',
 'status':'WITHHOLD_V3_EXECUTION_FAILURE_RECORDED',
 'generation':ledger['current_head'],'frontier':front,'github_run_id':run_id,
 'outcome':'UNEXPECTED_WORKFLOW_FAILURE_BEFORE_VALID_ADMISSION_RECEIPT',
 'admission_evidence':False,
 'fresh10_status':'UNKNOWN_DUE_ABORT_NOT_CLAIMED_FRESH_OR_SPENT',
 'canonical_mutation':False,'promotion_applied':False,'generation_transition':False,
 'g3_genesis_performed':False,
}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)
idx=len(ledger['events'])
e={
 'index':idx,'event_id':f"E{idx+1:04d}_G2_V3_EXECUTION_FAILURE_{run_id}",
 'event_type':'G2_EXECUTION_FAILURE_EXPERIENCE','status':'WITHHOLD',
 'generation':ledger['current_head'],'deficit':front,
 'effect':f"RUN={run_id}; OUTCOME=UNEXPECTED_WORKFLOW_FAILURE; ADMISSION_EVIDENCE=False; FRESH10_STATUS=UNKNOWN_DUE_ABORT; NEXT={front}",
 'source_path':f'receipts/yado-v3-execution-failure-history-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':False,'promotion_applied':False,'generation_transition':False,
}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);write(LEDGER,ledger)
print(json.dumps(receipt,indent=2,sort_keys=True))
