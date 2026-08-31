from __future__ import annotations
import copy, hashlib, json

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
    for i,e in enumerate(ledger.get('events',[])):
        if e.get('index')!=i: raise ValueError(f'BAD_INDEX:{i}')
        if e.get('parent_event_hash')!=prev: raise ValueError(f'BAD_PARENT_HASH:{i}')
        if e.get('event_hash')!=event_hash(e): raise ValueError(f'BAD_EVENT_HASH:{i}')
        if e.get('event_id') in seen: raise ValueError(f'DUPLICATE_EVENT_ID:{e.get("event_id")}')
        seen.add(e.get('event_id')); prev=e.get('event_hash')
    if ledger.get('tail_event_hash')!=prev: raise ValueError('BAD_TAIL')
    if ledger.get('event_count')!=len(ledger.get('events',[])): raise ValueError('BAD_EVENT_COUNT')
    current=ledger.get('current_head')
    if not current: raise ValueError('MISSING_CURRENT_HEAD')
    transitions=[e for e in ledger.get('events',[]) if e.get('promotion_applied') is True]
    if not transitions: raise ValueError('NO_PROMOTED_HEAD_HISTORY')
    latest=transitions[-1]
    latest_target=latest.get('to_generation') or latest.get('generation')
    if latest_target!=current: raise ValueError(f'CURRENT_HEAD_NOT_LATEST_PROMOTION:{latest_target}!={current}')
    if ledger.get('current_head_event_id') and ledger['current_head_event_id']!=latest.get('event_id'):
        raise ValueError('CURRENT_HEAD_EVENT_MISMATCH')
    return {
      'valid':True,
      'historical_promotion_count':len(transitions),
      'current_head':current,
      'current_head_event_id':latest.get('event_id'),
      'tail_event_hash':prev,
    }
