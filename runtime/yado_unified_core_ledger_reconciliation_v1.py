from __future__ import annotations
from pathlib import Path
import hashlib,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

LEDGER=REPO/'architecture'/'evolution-ledger.json'
HEAD=REPO/'canonical'/'yado-main-head-g2.json'
RECEIPT=REPO/'receipts'/'yado-unified-core-consolidation-gate-v1-run-33371375385.json'
OUT=ROOT/'yado_unified_core_ledger_reconciliation_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()

ledger=json.loads(LEDGER.read_text())
head=json.loads(HEAD.read_text())
receipt=json.loads(RECEIPT.read_text())
validate_ledger_v2(ledger)

if receipt.get('status')!='PASS_UNIFIED_YADO_CORE_V1_CONSOLIDATION':
    raise RuntimeError('CONSOLIDATION_RECEIPT_NOT_PASS')
if head.get('canonical_head_digest')!=receipt.get('post_consolidation_head_digest'):
    raise RuntimeError('HEAD_DOES_NOT_MATCH_CONSOLIDATION_RECEIPT')
if head.get('unified_core',{}).get('core_digest')!=receipt.get('unified_core_digest'):
    raise RuntimeError('UNIFIED_CORE_DIGEST_MISMATCH')
if ledger.get('current_head')!='G2_CANDIDATE_TRCG_V1':
    raise RuntimeError('WRONG_LEDGER_HEAD_GENERATION')

target_digest=head['canonical_head_digest']
pre_digest=receipt['pre_consolidation_head_digest']
existing=[e for e in ledger.get('events',[]) if e.get('event_id')=='E0062_G2_UNIFIED_CORE_CONSOLIDATION']

if existing:
    if ledger.get('current_head_digest')!=target_digest:
        raise RuntimeError('EXISTING_CONSOLIDATION_EVENT_WITH_WRONG_HEAD_DIGEST')
    repaired=False
    event=existing[0]
else:
    if ledger.get('current_head_digest')!=pre_digest:
        raise RuntimeError('LEDGER_NOT_AT_EXPECTED_PRE_CONSOLIDATION_DIGEST')
    idx=len(ledger['events'])
    event={
      'index':idx,
      'event_id':'E0062_G2_UNIFIED_CORE_CONSOLIDATION',
      'event_type':'GENERATION_INTERNAL_CORE_CONSOLIDATION',
      'status':'PASS',
      'generation':'G2_CANDIDATE_TRCG_V1',
      'deficit':'UNIFIED_YADO_CORE_FROM_ALL_BRANCHES_V1',
      'effect':'ONE_ACTIVE_G2_CORE_PLUS_READ_ONLY_13_BRANCH_EXPERIENCE_REGISTRY',
      'source_path':'receipts/yado-unified-core-consolidation-gate-v1-run-33371375385.json',
      'source_digest':receipt['receipt_sha256'],
      'run_id':'33371375385',
      'parent_event_hash':ledger['tail_event_hash'],
      'canonical_mutation':True,
      'promotion_applied':False,
      'generation_transition':False,
      'previous_head_digest':pre_digest,
      'new_head_digest':target_digest,
      'repair_note':'LEDGER_APPEND_RECONCILED_AFTER_PERSISTENCE_SPLIT_BRAIN',
    }
    event['event_hash']=event_hash(event)
    ledger['events'].append(event)
    ledger['event_count']=len(ledger['events'])
    ledger['tail_event_hash']=event['event_hash']
    ledger['current_head_digest']=target_digest
    ledger['current_head_event_id']=event['event_id']
    ledger['open_deficits']=sorted(set(
        [x for x in ledger.get('open_deficits',[]) if x not in ('UNIFIED_YADO_CORE_FROM_ALL_BRANCHES_V1',)]
        +['G2_RAW_TASK_REPRESENTATION_AND_GROUNDING_V1']
    ))
    ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
    validate_ledger_v2(ledger)
    LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
    repaired=True

result={
  'schema':'yado.unified_core_ledger_reconciliation.receipt.v1',
  'status':'PASS_UNIFIED_CORE_LEDGER_RECONCILIATION_V1',
  'github_run_id':os.getenv('GITHUB_RUN_ID'),
  'github_sha':os.getenv('GITHUB_SHA'),
  'repaired':repaired,
  'generation':ledger['current_head'],
  'head_digest':head['canonical_head_digest'],
  'ledger_head_digest':ledger['current_head_digest'],
  'current_head_event_id':ledger.get('current_head_event_id'),
  'event_count':ledger['event_count'],
  'tail_event_hash':ledger['tail_event_hash'],
  'consolidation_event':event,
  'checks':{
    'head_ledger_digest_match':ledger['current_head_digest']==head['canonical_head_digest'],
    'consolidation_event_present':any(e.get('event_id')=='E0062_G2_UNIFIED_CORE_CONSOLIDATION' for e in ledger['events']),
    'unified_core_bound':head.get('unified_core',{}).get('core_id')=='UNIFIED_YADO_CORE_V1',
    'frontier_preserved':ledger.get('open_deficits')==['G2_RAW_TASK_REPRESENTATION_AND_GROUNDING_V1'],
    'g3_not_created':head.get('g3_genesis_performed') is False,
  },
  'next_required_capability':'G2_RAW_TASK_REPRESENTATION_AND_GROUNDING_V1',
}
if not all(result['checks'].values()):
    raise RuntimeError('RECONCILIATION_CHECK_FAILED')
result['receipt_sha256']=h(result)
OUT.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps(result,indent=2,sort_keys=True))
