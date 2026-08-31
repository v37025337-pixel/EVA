from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
CORE=REPO/'canonical'/'yado-unified-core-v1.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
OUT=ROOT/'yado_head_capability_core_binding_reconciliation_v1_receipt.json'

CID='COUNTEREXAMPLE_LINEAGE_MEMORY_V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);core=load(CORE);ledger=load(LEDGER)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['HEAD_CAPABILITY_TO_CORE_BINDING']:raise RuntimeError('UNEXPECTED_FRONTIER')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')

head_caps=set(head.get('inherited_capabilities',[]))|set(head.get('new_capabilities',[]))
active=set()
for plane in core.get('planes',[]):active.update(plane.get('active_components',[]))
unbound=sorted(head_caps-active)

withholds=[e for e in ledger.get('events',[]) if str(e.get('status','')).startswith('WITHHOLD')]
receipt_backed=[e for e in ledger.get('events',[]) if e.get('source_path') and str(e.get('source_path')).startswith('receipts/')]
existing_receipts=[e for e in receipt_backed if (REPO/e['source_path']).exists()]
recent_counterexamples=[e for e in withholds if e.get('source_path') and (REPO/e['source_path']).exists()][-8:]

checks={
 'exact_unbound_capability':unbound==[CID],
 'head_claim_present':CID in head_caps,
 'persistence_invariant_present':'RECEIPTS_AND_COUNTEREXAMPLES_ARE_PERSISTENT_EXPERIENCE' in core.get('invariants',[]),
 'withhold_history_present':len(withholds)>=5,
 'receipt_lineage_present':len(receipt_backed)>=20,
 'readable_counterexample_receipts':len(recent_counterexamples)>=2,
 'not_already_bound':CID not in active,
 'g3_not_started':head.get('g3_genesis_performed') is False and core.get('g3_genesis_performed') is False,
}
passed=all(checks.values())

post_head=None;post_core=None
if passed:
    new_core=copy.deepcopy(core);new_core.pop('core_digest',None)
    mem=next(x for x in new_core['planes'] if x.get('plane_id')=='MEMORY_AND_EXPERIENCE')
    mem['active_components']=sorted(set(mem.get('active_components',[])+[CID]))
    mem['responsibilities']=sorted(set(mem.get('responsibilities',[])+['persistent_counterexample_lineage_memory']))
    new_core['counterexample_lineage_memory']={
      'component_id':CID,
      'mode':'ACTIVE_LEDGER_AND_RECEIPT_BOUND_MEMORY',
      'ledger':'architecture/evolution-ledger.json',
      'receipt_namespace':'receipts/',
      'withhold_event_count_at_binding':len(withholds),
      'receipt_backed_event_count_at_binding':len(receipt_backed),
      'verified_readable_counterexample_samples':[
        {'event_id':e.get('event_id'),'source_path':e.get('source_path'),'source_digest':e.get('source_digest')}
        for e in recent_counterexamples
      ],
      'gate_run_id':str(os.getenv('GITHUB_RUN_ID') or 'LOCAL'),
      'semantic_boundary':'PERSISTENT CAUSAL LEDGER/RECEIPT MEMORY OF FAILURES, WITHHOLDS, AND COUNTEREXAMPLES; NOT GENERAL EPISODIC OR SEMANTIC MEMORY.'
    }
    new_core['current_frontier']='UNIFIED_CORE_POST_HEAD_CAPABILITY_BINDING_AUDIT_V1'
    new_core['core_digest']=h(new_core);CORE.write_text(json.dumps(new_core,indent=2,sort_keys=True)+'\n')

    new_head=copy.deepcopy(head);new_head.pop('canonical_head_digest',None)
    new_head['unified_core']['core_digest']=new_core['core_digest']
    new_head['unified_core']['counterexample_lineage_memory_binding']='architecture/evolution-ledger.json+receipts/'
    new_head['current_frontier']='UNIFIED_CORE_POST_HEAD_CAPABILITY_BINDING_AUDIT_V1'
    new_head['canonical_head_digest']=h(new_head);HEAD.write_text(json.dumps(new_head,indent=2,sort_keys=True)+'\n')
    post_head=new_head['canonical_head_digest'];post_core=new_core['core_digest']
    status='PASS_HEAD_CAPABILITY_CORE_BINDING_RECONCILIATION_V1'
    next_cap='UNIFIED_CORE_POST_HEAD_CAPABILITY_BINDING_AUDIT_V1'
else:
    status='WITHHOLD_HEAD_CAPABILITY_CORE_BINDING_RECONCILIATION_V1'
    next_cap='HEAD_CAPABILITY_TO_CORE_BINDING'

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
 'schema':'yado.g2.head_capability_core_binding_reconciliation.v1','status':status,
 'unbound_before':unbound,'checks':checks,'withhold_event_count':len(withholds),
 'receipt_backed_event_count':len(receipt_backed),'readable_receipt_count':len(existing_receipts),
 'sample_counterexamples':[{'event_id':e.get('event_id'),'source_path':e.get('source_path')} for e in recent_counterexamples],
 'canonical_mutation':passed,'promotion_applied':False,'generation_transition':False,'g3_genesis_performed':False,
 'post_head_digest':post_head,'post_core_digest':post_core,'next_required_capability':next_cap,
 'semantic_boundary':'RECONCILES AN EXISTING HEAD CAPABILITY CLAIM WITH ITS ACTUAL LEDGER/RECEIPT IMPLEMENTATION; DOES NOT ADD A NEW COGNITIVE CAPABILITY.'
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_HEAD_CAPABILITY_CORE_BINDING_RECONCILIATION",
 'event_type':'CONTROL_PLANE_CAPABILITY_BINDING_RECONCILIATION','status':'PASS' if passed else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'HEAD_CAPABILITY_TO_CORE_BINDING',
 'effect':'COUNTEREXAMPLE_LINEAGE_MEMORY_BOUND_TO_LEDGER_AND_RECEIPTS' if passed else 'HEAD_CAPABILITY_BINDING_WITHHELD',
 'source_path':f'receipts/yado-head-capability-core-binding-reconciliation-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':passed,'promotion_applied':False,'generation_transition':False}
if passed:
    e['previous_head_digest']=ledger['current_head_digest'];e['new_head_digest']=post_head
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
if passed:ledger['current_head_digest']=post_head
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':status,'unbound_before':unbound,'checks':checks,'post_head_digest':post_head,
 'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('HEAD_CAPABILITY_CORE_BINDING_RECONCILIATION_WITHHELD')
