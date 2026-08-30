from 
  {
    'event_id':'E0011_EXPERIMENT_COMPUTE_BUDGET_GATE',
    'event_type':'CONTROL_PLANE_RESULT',
    'status':'PASS',
    'generation':'G0_RC8_V36',
    'deficit':'UNBOUNDED_EVOLUTION_SEARCH',
    'effect':'FOUR_OVERBUDGET_EXPERIMENTS_CANCELLED; FUTURE_SEARCH_MUST_BE_BOUNDED',
    'source_path':'receipts/yado-experiment-compute-budget-gate-v1-latest.json',
    'run_id':'33307348264',
  },__future__ import annotations
from pathlib import Path
import copy,hashlib,json

ROOT=Path(__file__).resolve().parents[1]
LEDGER=ROOT/'architecture'/'evolution-ledger.json'

def canon(o):
    return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)

def h(o):
    return hashlib.sha256(canon(o).encode()).hexdigest()

def loadj(p):
    return json.loads((ROOT/p).read_text())

def source_digest(obj):
    for k in ('receipt_sha256','report_digest','manifest_digest','bundle_digest'):
        if obj.get(k):
            return str(obj[k])
    return hashlib.sha256(canon(obj).encode()).hexdigest()

def event_hash(e):
    x=copy.deepcopy(e);x.pop('event_hash',None)
    return h(x)

sources=[
  {
    'event_id':'E0001_G0_VERIFIED_ROOT',
    'event_type':'GENERATION_HEAD',
    'status':'VERIFIED',
    'generation':'G0_RC8_V36',
    'deficit':None,
    'effect':'ESTABLISH_VERIFIED_DEVELOPMENTAL_ROOT',
    'source_path':None,
    'source_digest':'7ecfd384d48bfd5c39312fa4c54a8feb49f4473b171902c8190a6b276beda9d1',
    'run_id':'33266617685',
  },
  {
    'event_id':'E0002_ALGORITHM_GENESIS_COMPONENTS',
    'event_type':'EXPERIMENT_RESULT',
    'status':'PASS',
    'generation':'G0_RC8_V36',
    'deficit':'COGNITIVE_COMPONENT_GENERATION',
    'effect':'SHADOW_COGNITIVE_COMPONENT_BUNDLE_AVAILABLE',
    'source_path':'receipts/yado-rc8-algorithm-genesis-uplift-v3-latest.json',
    'run_id':'33278052092',
  },
  {
    'event_id':'E0003_SUCCESSOR_RUNTIME_ADAPTER',
    'event_type':'EXPERIMENT_RESULT',
    'status':'PASS',
    'generation':'G0_RC8_V36',
    'deficit':'SAFE_SUCCESSOR_EXECUTION',
    'effect':'SAFE_EPHEMERAL_SUCCESSOR_RUNTIME_AVAILABLE',
    'source_path':'receipts/yado-safe-rc8-successor-runtime-adapter-v1-latest.json',
    'run_id':'33301266811',
  },
  {
    'event_id':'E0004_S1_BURNIN',
    'event_type':'EXPERIMENT_RESULT',
    'status':'WITHHOLD',
    'generation':'CANDIDATE_S1',
    'deficit':'FRESH_GENERALIZATION_AND_BOUNDARY_REASONING',
    'effect':'S1_REJECTED_AS_GENERATION; COUNTEREXAMPLES_PRESERVED',
    'source_path':'receipts/yado-s1-burnin-10rounds-v1-recovered.json',
    'run_id':'33301460805',
  },
  {
    'event_id':'E0005_REAL_LINEAGE_RECONSTRUCTION',
    'event_type':'CONTROL_PLANE_RESULT',
    'status':'PASS',
    'generation':'G0_RC8_V36',
    'deficit':'DISCONNECTED_VERSION_HISTORY',
    'effect':'G0_HEAD_AND_S1_REJECTED_STEPPING_STONE_RECONSTRUCTED',
    'source_path':'receipts/yado-real-developmental-lineage-v1-latest.json',
    'run_id':'33302653581',
  },
  {
    'event_id':'E0006_G0_AUTONOMOUS_METACOGNITION',
    'event_type':'LIVE_KERNEL_RESULT',
    'status':'PASS',
    'generation':'G0_RC8_V36',
    'deficit':'DEVELOPMENTAL_GOVERNANCE',
    'effect':'LINEAGE_CONTROL_EXECUTE; S1_PROMOTION_WITHHOLD; S2_REPAIR_WITHHOLD',
    'source_path':'receipts/yado-live-g0-autonomous-metacognitive-v1-latest.json',
    'run_id':'33303519492',
  },
  {
    'event_id':'E0007_ONE_HEAD_CONTROL_PLANE',
    'event_type':'CONTROL_PLANE_RESULT',
    'status':'PASS',
    'generation':'G0_RC8_V36',
    'deficit':'BRANCH_PROLIFERATION',
    'effect':'EXACTLY_ONE_DEVELOPMENTAL_HEAD',
    'source_path':'receipts/yado-developmental-head-control-plane-v1-latest.json',
    'run_id':'33303618094',
  },
  {
    'event_id':'E0008_DEVELOPMENTAL_SELF_MODEL_BINDER',
    'event_type':'SELF_MODEL_RESULT',
    'status':'PASS_SHADOW',
    'generation':'G0_RC8_V36',
    'deficit':'STALE_DEVELOPMENT_PRIORITY',
    'effect':'VERIFIED_EVIDENCE_VISIBLE_AS_EFFECTIVE_PRIORITY_WITHOUT_PARENT_MUTATION',
    'source_path':'receipts/yado-developmental-self-model-binder-v1-latest.json',
    'run_id':'33303725219',
  },
  {
    'event_id':'E0009_KERNEL_NATIVE_BINDER',
    'event_type':'EXPERIMENT_RESULT',
    'status':'WITHHOLD',
    'generation':'G0_RC8_V36',
    'deficit':'NATIVE_SEQUENCE_TRANSFORMATION',
    'effect':'ORDERING_ALONE_CANNOT_REMOVE_RESOLVED_DEFICITS',
    'source_path':'receipts/yado-kernel-native-developmental-self-model-binding-v1-latest.json',
    'run_id':'33303817979',
  },
  {
    'event_id':'E0010_BUDGET_SEQUENCE_TRANSFORM',
    'event_type':'EXPERIMENT_RESULT',
    'status':'WITHHOLD',
    'generation':'G0_RC8_V36',
    'deficit':'CONDITIONAL_FILTERING_OF_PRIORITIES',
    'effect':'ORDER_SOLVED; FILTER_REMAINS_LIMITING',
    'source_path':'receipts/yado-budget-aware-sequence-transform-v1-latest.json',
    'run_id':'33304206212',
  },
]

# Resolve and verify source evidence.
for s in sources:
    if s.get('source_path'):
        obj=loadj(s['source_path'])
        if s['event_id']=='E0004_S1_BURNIN':
            sd=obj['original_logged_receipt_sha256']
            if obj.get('logged_status')!='WITHHOLD_S1_BURNIN':
                raise RuntimeError('RECOVERED_S1_STATUS_MISMATCH')
        else:
            sd=source_digest(obj)
        s['source_digest']=sd

# Load prior append-only ledger if present.
if LEDGER.exists():
    ledger=json.loads(LEDGER.read_text())
else:
    ledger={
      'schema':'yado.causal_evolution_ledger.v1',
      'lineage_id':'YADO_MAIN_LINEAGE',
      'invariant':'APPEND_ONLY_HASH_CHAIN; EXACTLY_ONE_PROMOTED_HEAD',
      'current_head':'G0_RC8_V36',
      'current_head_digest':'7ecfd384d48bfd5c39312fa4c54a8feb49f4473b171902c8190a6b276beda9d1',
      'events':[],
    }

# Verify existing chain before appending.
prev='GENESIS'
seen=set()
for i,e in enumerate(ledger['events']):
    if e['event_id'] in seen:
        raise RuntimeError('DUPLICATE_EVENT_ID:'+e['event_id'])
    seen.add(e['event_id'])
    if e['index']!=i:
        raise RuntimeError('INDEX_GAP')
    if e['parent_event_hash']!=prev:
        raise RuntimeError('PARENT_HASH_MISMATCH:'+e['event_id'])
    if e['event_hash']!=event_hash(e):
        raise RuntimeError('EVENT_HASH_MISMATCH:'+e['event_id'])
    prev=e['event_hash']

# Append only unseen evidence events.
for s in sources:
    if s['event_id'] in seen:
        continue
    payload={
      'index':len(ledger['events']),
      'event_id':s['event_id'],
      'event_type':s['event_type'],
      'status':s['status'],
      'generation':s['generation'],
      'deficit':s['deficit'],
      'effect':s['effect'],
      'source_path':s.get('source_path'),
      'source_digest':s['source_digest'],
      'run_id':s.get('run_id'),
      'parent_event_hash':prev,
      'canonical_mutation':False,
      'promotion_applied':False,
    }
    if s['event_id']=='E0001_G0_VERIFIED_ROOT':
        payload['promotion_applied']=True
        payload['canonical_mutation']=False
    payload['event_hash']=event_hash(payload)
    ledger['events'].append(payload)
    seen.add(payload['event_id'])
    prev=payload['event_hash']

# Derived state is recomputed, not hand-maintained.
promotions=[e for e in ledger['events'] if e.get('promotion_applied')]
if len(promotions)!=1 or promotions[0]['generation']!='G0_RC8_V36':
    raise RuntimeError('ONE_HEAD_INVARIANT_FAIL')
ledger['current_head']='G0_RC8_V36'
ledger['current_head_digest']='7ecfd384d48bfd5c39312fa4c54a8feb49f4473b171902c8190a6b276beda9d1'
ledger['event_count']=len(ledger['events'])
ledger['tail_event_hash']=prev
ledger['open_deficits']=[
  'THINKING_BOUNDARY_REASONING',
  'INTELLIGENCE_BOUNDARY_REASONING',
  'REPRESENTATION_INVARIANCE',
  'CONDITIONAL_FILTERING_OF_PRIORITIES',
]
ledger['resolved_deficits']=[
  'DISCONNECTED_VERSION_HISTORY',
  'BRANCH_PROLIFERATION',
]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})

# Final integrity replay.
prev='GENESIS'
for i,e in enumerate(ledger['events']):
    assert e['index']==i
    assert e['parent_event_hash']==prev
    assert e['event_hash']==event_hash(e)
    prev=e['event_hash']
assert prev==ledger['tail_event_hash']

LEDGER.parent.mkdir(exist_ok=True)
LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
report={
  'schema':'yado.causal_evolution_ledger.receipt.v1',
  'status':'PASS_CAUSAL_EVOLUTION_LEDGER_V1',
  'event_count':ledger['event_count'],
  'current_head':ledger['current_head'],
  'tail_event_hash':ledger['tail_event_hash'],
  'ledger_digest':ledger['ledger_digest'],
  'one_head_invariant':True,
  'append_only_chain_valid':True,
  'recovered_s1_evidence_bound':True,
  'open_deficits':ledger['open_deficits'],
}
report['receipt_sha256']=h(report)
(ROOT/'runtime'/'yado_causal_evolution_ledger_v1_receipt.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
print(json.dumps(report,indent=2,sort_keys=True))
