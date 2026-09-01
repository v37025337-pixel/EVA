from __future__ import annotations
import copy, hashlib, json, re

_HEX64=re.compile(r'^[0-9a-f]{64}$')
_NEXT=re.compile(r'(?:^|[; ])NEXT=([A-Z0-9_]+)(?:$|[; ])')

def canon(o):
    return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)

def digest(o):
    return hashlib.sha256(canon(o).encode()).hexdigest()

def event_hash(event):
    x=copy.deepcopy(event)
    x.pop('event_hash',None)
    return digest(x)

def validate_ledger_v2(ledger):
    prev='GENESIS'
    seen=set()
    events=ledger.get('events',[])
    for i,e in enumerate(events):
        if e.get('index')!=i: raise ValueError(f'BAD_INDEX:{i}')
        if e.get('parent_event_hash')!=prev: raise ValueError(f'BAD_PARENT_HASH:{i}')
        if e.get('event_hash')!=event_hash(e): raise ValueError(f'BAD_EVENT_HASH:{i}')
        if e.get('event_id') in seen: raise ValueError(f'DUPLICATE_EVENT_ID:{e.get("event_id")}')
        seen.add(e.get('event_id')); prev=e.get('event_hash')
    if ledger.get('tail_event_hash')!=prev: raise ValueError('BAD_TAIL')
    if ledger.get('event_count')!=len(events): raise ValueError('BAD_EVENT_COUNT')

    stored_ledger_digest=ledger.get('ledger_digest')
    if stored_ledger_digest:
        computed=digest({k:v for k,v in ledger.items() if k!='ledger_digest'})
        if stored_ledger_digest!=computed:
            raise ValueError('BAD_LEDGER_DIGEST')

    current=ledger.get('current_head')
    if not current: raise ValueError('MISSING_CURRENT_HEAD')
    transitions=[e for e in events if e.get('promotion_applied') is True]
    if not transitions: raise ValueError('NO_PROMOTED_HEAD_HISTORY')
    latest=transitions[-1]
    latest_target=latest.get('to_generation') or latest.get('generation')
    if latest_target!=current: raise ValueError(f'CURRENT_HEAD_NOT_LATEST_PROMOTION:{latest_target}!={current}')
    if ledger.get('current_head_event_id') and ledger['current_head_event_id']!=latest.get('event_id'):
        raise ValueError('CURRENT_HEAD_EVENT_MISMATCH')

    head_digest=str(ledger.get('current_head_digest') or '')
    if not _HEX64.match(head_digest):
        raise ValueError('BAD_CURRENT_HEAD_DIGEST')
    mutations=[e for e in events if e.get('canonical_mutation') is True and e.get('new_head_digest')]
    if mutations and mutations[-1].get('new_head_digest')!=head_digest:
        raise ValueError('CURRENT_HEAD_DIGEST_NOT_LATEST_CANONICAL_MUTATION')

    deficits=ledger.get('open_deficits')
    if not isinstance(deficits,list) or not deficits or any(not isinstance(x,str) or not x for x in deficits):
        raise ValueError('BAD_OPEN_DEFICITS')
    if events:
        m=_NEXT.search(str(events[-1].get('effect') or ''))
        if m and deficits!=[m.group(1)]:
            raise ValueError(f'OPEN_DEFICIT_NOT_LAST_EVENT_NEXT:{deficits}!={[m.group(1)]}')

    return {
      'valid':True,
      'historical_promotion_count':len(transitions),
      'canonical_mutation_count':len(mutations),
      'current_head':current,
      'current_head_event_id':latest.get('event_id'),
      'current_head_digest':head_digest,
      'open_deficits':copy.deepcopy(deficits),
      'tail_event_hash':prev,
      'ledger_digest_verified':bool(stored_ledger_digest),
    }
