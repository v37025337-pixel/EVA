from __future__ import annotations
from pathlib import Path
import hashlib,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2

LEDGER=REPO/'architecture/evolution-ledger.json'
HEAD=REPO/'canonical/yado-main-head-g2.json'
HISTORICAL_RECEIPT=REPO/'receipts/yado-unified-core-consolidation-gate-v1-run-33371375385.json'
OUT=ROOT/'yado_unified_core_ledger_reconciliation_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()

ledger=json.loads(LEDGER.read_text(encoding='utf-8'))
head=json.loads(HEAD.read_text(encoding='utf-8'))
historical=json.loads(HISTORICAL_RECEIPT.read_text(encoding='utf-8'))
validate_ledger_v2(ledger)

if historical.get('status')!='PASS_UNIFIED_YADO_CORE_V1_CONSOLIDATION':
    raise RuntimeError('HISTORICAL_CONSOLIDATION_RECEIPT_NOT_PASS')
if ledger.get('current_head')!='G2_CANDIDATE_TRCG_V1':
    raise RuntimeError('WRONG_LEDGER_HEAD_GENERATION')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):
    raise RuntimeError('CURRENT_HEAD_LEDGER_DIGEST_MISMATCH')
if len(ledger.get('open_deficits',[]))!=1:
    raise RuntimeError('EXPECTED_ONE_CURRENT_FRONTIER')
if head.get('current_frontier')!=ledger['open_deficits'][0]:
    raise RuntimeError('CURRENT_FRONTIER_SPLIT_BRAIN')

event=next((e for e in ledger.get('events',[]) if e.get('event_id')=='E0062_G2_UNIFIED_CORE_CONSOLIDATION'),None)
if event is None:
    raise RuntimeError('HISTORICAL_CONSOLIDATION_EVENT_MISSING')

result={
  'schema':'yado.unified_core_ledger_reconciliation.receipt.v2',
  'status':'PASS_CURRENT_G2_LEDGER_RECONCILIATION_VERIFIER',
  'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),
  'repaired':False,'historical_reconciliation_only':True,
  'generation':ledger['current_head'],'head_digest':head['canonical_head_digest'],
  'ledger_head_digest':ledger['current_head_digest'],'current_head_event_id':ledger.get('current_head_event_id'),
  'event_count':ledger['event_count'],'tail_event_hash':ledger['tail_event_hash'],
  'historical_consolidation_event':event,
  'checks':{
    'head_ledger_digest_match':ledger['current_head_digest']==head['canonical_head_digest'],
    'historical_consolidation_event_present':event is not None,
    'generation_promotion_event_preserved':ledger.get('current_head_event_id')=='E0044_G2_PROMOTION',
    'unified_core_bound':head.get('unified_core',{}).get('core_id')=='UNIFIED_YADO_CORE_V1',
    'frontier_current_and_preserved':head.get('current_frontier')==ledger['open_deficits'][0],
    'frontier_is_not_rewritten_by_reconciliation':True,
    'g3_not_created':head.get('g3_genesis_performed') is False,
  },
  'next_required_capability':ledger['open_deficits'][0],
  'semantic_boundary':'CURRENT-STATE VERIFIER ONLY. THIS HISTORICAL RECONCILIATION TOOL MUST NEVER REWRITE A MODERN G2 FRONTIER.'
}
if not all(result['checks'].values()):
    raise RuntimeError('RECONCILIATION_CHECK_FAILED')
result['receipt_sha256']=h(result)
OUT.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps(result,indent=2,sort_keys=True))
