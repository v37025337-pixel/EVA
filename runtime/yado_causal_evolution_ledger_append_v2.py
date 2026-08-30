from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os

ROOT=Path(__file__).resolve().parents[1]
LEDGER=ROOT/'architecture'/'evolution-ledger.json'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def event_hash(e):
    x=copy.deepcopy(e);x.pop('event_hash',None);return h(x)
def load(path): return json.loads((ROOT/path).read_text())

ledger=json.loads(LEDGER.read_text())

# Verify chain before append.
prev='GENESIS';seen=set()
for i,e in enumerate(ledger['events']):
    assert e['index']==i
    assert e['parent_event_hash']==prev
    assert e['event_hash']==event_hash(e)
    assert e['event_id'] not in seen
    seen.add(e['event_id']);prev=e['event_hash']

sources=[
  ('E0013_CONJUNCTIVE_EXTENDED_TRANSFER','EXPERIMENT_RESULT','WITHHOLD','G0_RC8_V36',
   'CONJUNCTIVE_RULE_INDUCTION_GENERALIZATION',
   'FOUR_OF_FIVE_NEW_DOMAINS_PASS; ACCESS_CONTROL_RETAINED_AS_COUNTEREXAMPLE',
   'receipts/yado-conjunctive-rule-inducer-extended-transfer-v1-latest.json','33313603775'),
  ('E0014_G0_CONJUNCTIVE_READMISSION','LIVE_KERNEL_RESULT','PASS','G0_RC8_V36',
   'ALGORITHM_BANK_ADMISSION',
   'G0_DECISION_WITHHOLD_TO_EXECUTE_AFTER_EXTENDED_EVIDENCE',
   'receipts/yado-g0-conjunctive-algorithm-readmission-v2-latest.json','33313727864'),
  ('E0015_SHADOW_ALGORITHM_BANK_ADMISSION','CONTROL_PLANE_RESULT','PASS','G0_RC8_V36',
   'SHADOW_ALGORITHM_BANK_ENTRY',
   'CONJUNCTIVE_RULE_INDUCER_REGISTERED_SHADOW_ONLY',
   'receipts/yado-shadow-algorithm-bank-admission-v1-latest.json','33313830992'),
  ('E0016_FRESH_META_SELECTION','EXPERIMENT_RESULT','PASS','G0_RC8_V36',
   'ALGORITHM_META_SELECTION',
   'EXISTING_WINS_SIMPLE_UNARY; CONJUNCTIVE_WINS_FIVE_HARDER_TASKS_ALL_BLIND_1_0',
   'receipts/yado-fresh-meta-selection-conjunctive-vs-existing-v1-latest.json','33313898337'),
  ('E0017_G0_META_SELECTION_ADMISSION','LIVE_KERNEL_RESULT','PASS','G0_RC8_V36',
   'SHADOW_META_SELECTION_ACTIVATION',
   'G0_EXECUTE_ENABLE_SHADOW_META_SELECTION',
   'receipts/yado-g0-meta-selection-admission-decision-v1-latest.json','33314014798'),
]

def source_digest(obj):
    for k in ('receipt_sha256','report_digest','manifest_digest'):
        if obj.get(k): return str(obj[k])
    return h(obj)

for event_id,event_type,status,generation,deficit,effect,path,run_id in sources:
    if event_id in seen: continue
    obj=load(path)
    payload={
      'index':len(ledger['events']),
      'event_id':event_id,'event_type':event_type,'status':status,
      'generation':generation,'deficit':deficit,'effect':effect,
      'source_path':path,'source_digest':source_digest(obj),'run_id':run_id,
      'parent_event_hash':prev,'canonical_mutation':False,'promotion_applied':False,
    }
    payload['event_hash']=event_hash(payload)
    ledger['events'].append(payload);seen.add(event_id);prev=payload['event_hash']

ledger['event_count']=len(ledger['events'])
ledger['tail_event_hash']=prev
ledger['current_head']='G0_RC8_V36'
ledger['current_head_digest']='7ecfd384d48bfd5c39312fa4c54a8feb49f4473b171902c8190a6b276beda9d1'
ledger['open_deficits']=[
  'THINKING_BOUNDARY_REASONING',
  'INTELLIGENCE_BOUNDARY_REASONING',
  'REPRESENTATION_INVARIANCE',
  'BUDGET_AWARE_SEARCH_AND_STAGED_ESCALATION',
  'ACCESS_CONTROL_HIGHER_EXPRESSIVENESS_COUNTEREXAMPLE',
  'LIVE_SHADOW_META_SELECTION_VALIDATION',
]
ledger['resolved_deficits']=sorted(set(ledger.get('resolved_deficits',[])+[
  'NATIVE_ALGORITHM_BANK_ADMISSION_AND_META_SELECTION',
  'CONDITIONAL_FILTERING_OF_PRIORITIES',
]))
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})

# Replay.
prev='GENESIS'
for i,e in enumerate(ledger['events']):
    assert e['index']==i and e['parent_event_hash']==prev and e['event_hash']==event_hash(e)
    prev=e['event_hash']
assert prev==ledger['tail_event_hash']
assert sum(bool(e.get('promotion_applied')) for e in ledger['events'])==1

LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
report={
 'schema':'yado.causal_evolution_ledger.append_v2.receipt',
 'status':'PASS_CAUSAL_EVOLUTION_LEDGER_APPEND_V2',
 'event_count':ledger['event_count'],'current_head':ledger['current_head'],
 'tail_event_hash':ledger['tail_event_hash'],'ledger_digest':ledger['ledger_digest'],
 'one_head_invariant':True,'append_only_chain_valid':True,
 'appended_event_ids':[x[0] for x in sources],
}
report['receipt_sha256']=h(report)
(ROOT/'runtime'/'yado_causal_evolution_ledger_append_v2_receipt.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
print(json.dumps(report,indent=2,sort_keys=True))
