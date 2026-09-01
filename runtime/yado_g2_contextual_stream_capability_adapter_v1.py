from __future__ import annotations
from dataclasses import dataclass
from collections import OrderedDict
import copy,hashlib,json

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()

@dataclass(frozen=True)
class StrategySpec:
    strategy_id:str
    complexity:float
    risk:float
    novelty:float

STRATEGIES=[
    StrategySpec('BASE_ROUTER_ONLY',0.10,0.02,0.10),
    StrategySpec('LAST_STREAM_CAPABILITY',0.22,0.04,0.60),
    StrategySpec('BOUNDED_STREAM_CONTEXT_MAP',0.30,0.05,0.95),
    StrategySpec('GLOBAL_LAST_CAPABILITY',0.16,0.18,0.35),
    StrategySpec('RESOURCE_FIRST_ON_AMBIGUITY',0.14,0.22,0.25),
]

class ContextualStreamCapabilityAdapterV1:
    """Bounded temporal adapter over the canonical G2 runtime.
    The first strategy can read the canonical recurrent episode buffer.
    The evolved strategy maintains a separate bounded LRU stream->capability
    associative memory so long-lived interleaved streams do not compete for
    the 128-slot episodic ring buffer.
    """
    MAX_LOOKBACK=128
    MAX_STREAM_CONTEXTS=1024

    def __init__(self,runtime,strategy_id='BOUNDED_STREAM_CONTEXT_MAP'):
        self.runtime=runtime
        self.strategy_id=str(strategy_id)
        self.stream_context=OrderedDict()

    @staticmethod
    def _ambiguous(desc):
        if 'context_ambiguous' in desc:
            return bool(desc.get('context_ambiguous'))
        keys=('budget_limited','quota_limited','external_evidence_needed','relation_needed','disjunction_needed')
        return not any(bool(desc.get(k,False)) for k in keys)

    def _history(self):
        return list(self.runtime.episodes)[-self.MAX_LOOKBACK:]

    def _last_stream_capability(self,stream_id):
        sid=str(stream_id)
        for e in reversed(self._history()):
            if e.get('kind')=='TASK_EPISODE' and str(e.get('stream_id',''))==sid:
                return e.get('selected_capability')
        return None

    def _global_last_capability(self):
        for e in reversed(self._history()):
            if e.get('kind')=='TASK_EPISODE':
                return e.get('selected_capability')
        return None

    def _map_get(self,stream_id):
        sid=str(stream_id)
        if sid not in self.stream_context:
            return None
        value=self.stream_context.pop(sid)
        self.stream_context[sid]=value
        return value

    def _map_put(self,stream_id,capability):
        sid=str(stream_id)
        if not sid:
            return
        if sid in self.stream_context:
            self.stream_context.pop(sid)
        self.stream_context[sid]=capability
        while len(self.stream_context)>self.MAX_STREAM_CONTEXTS:
            self.stream_context.popitem(last=False)

    def clear_context(self):
        self.stream_context.clear()

    @staticmethod
    def _explicit_descriptor(capability):
        d={'budget_limited':False,'quota_limited':False,'external_evidence_needed':False,
           'relation_needed':False,'disjunction_needed':False}
        if capability==CAP_BUD: d['budget_limited']=True
        elif capability==CAP_RES: d['external_evidence_needed']=True
        elif capability==CAP_REL: d['relation_needed']=True
        return d

    def choose(self,task):
        desc=task.get('descriptor',{})
        if not self._ambiguous(desc):
            return self.runtime.router.execute(desc)
        if self.strategy_id=='BASE_ROUTER_ONLY':
            return self.runtime.router.execute(desc)
        if self.strategy_id=='LAST_STREAM_CAPABILITY':
            return self._last_stream_capability(task.get('stream_id','')) or self.runtime.router.execute(desc)
        if self.strategy_id=='BOUNDED_STREAM_CONTEXT_MAP':
            return self._map_get(task.get('stream_id','')) or self.runtime.router.execute(desc)
        if self.strategy_id=='GLOBAL_LAST_CAPABILITY':
            return self._global_last_capability() or self.runtime.router.execute(desc)
        if self.strategy_id=='RESOURCE_FIRST_ON_AMBIGUITY':
            return CAP_RES
        raise ValueError('UNKNOWN_CONTEXT_STRATEGY:'+self.strategy_id)

    def run(self,task,ablated_context=False):
        selected=self.runtime.router.execute(task.get('descriptor',{})) if ablated_context else self.choose(task)
        shadow=copy.deepcopy(task)
        shadow['descriptor']=self._explicit_descriptor(selected)
        try:
            out=self.runtime.run(shadow)
        except (KeyError,ValueError,TypeError) as exc:
            raise RuntimeError('EXECUTION_MISMATCH:'+type(exc).__name__+':'+str(exc)) from exc
        if not ablated_context and not self._ambiguous(task.get('descriptor',{})):
            # Explicitly routed episodes teach the bounded stream context map.
            self._map_put(task.get('stream_id',''),selected)
        out['context_strategy']=self.strategy_id
        out['context_selected_capability']=selected
        return out

    @classmethod
    def component(cls):
        x={
          'schema':'yado.g2.contextual_stream_capability_adapter.v1',
          'component_id':'ALG-G2-CONTEXTUAL-STREAM-CAPABILITY-ADAPTER-V1',
          'family':'RECURRENT_CONTEXT_CONDITIONED_CAPABILITY_ROUTING',
          'max_lookback':cls.MAX_LOOKBACK,
          'max_stream_contexts':cls.MAX_STREAM_CONTEXTS,
          'associative_stream_memory':'BOUNDED_LRU',
          'parent_runtime_modified':False,
          'canonical_active':False,
        }
        x['component_digest']=digest(x)
        return x
