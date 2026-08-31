from __future__ import annotations
from dataclasses import dataclass
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
    StrategySpec('LAST_STREAM_CAPABILITY',0.22,0.04,0.75),
    StrategySpec('GLOBAL_LAST_CAPABILITY',0.16,0.18,0.35),
    StrategySpec('RESOURCE_FIRST_ON_AMBIGUITY',0.14,0.22,0.25),
]

class ContextualStreamCapabilityAdapterV1:
    """Bounded temporal adapter over the canonical G2 runtime.
    It does not modify the parent runtime. It can reuse the most recent
    capability selected for the same stream only when the current routing
    descriptor is intentionally ambiguous.
    """
    MAX_LOOKBACK=128

    def __init__(self,runtime,strategy_id='LAST_STREAM_CAPABILITY'):
        self.runtime=runtime
        self.strategy_id=str(strategy_id)

    @staticmethod
    def _ambiguous(desc):
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
        if self.strategy_id=='GLOBAL_LAST_CAPABILITY':
            return self._global_last_capability() or self.runtime.router.execute(desc)
        if self.strategy_id=='RESOURCE_FIRST_ON_AMBIGUITY':
            return CAP_RES
        raise ValueError('UNKNOWN_CONTEXT_STRATEGY:'+self.strategy_id)

    def run(self,task,ablated_context=False):
        selected=self.runtime.router.execute(task.get('descriptor',{})) if ablated_context else self.choose(task)
        shadow=copy.deepcopy(task)
        shadow['descriptor']=self._explicit_descriptor(selected)
        out=self.runtime.run(shadow)
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
          'parent_runtime_modified':False,
          'canonical_active':False,
        }
        x['component_digest']=digest(x)
        return x
