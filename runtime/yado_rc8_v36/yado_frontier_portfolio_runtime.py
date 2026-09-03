from __future__ import annotations
from typing import Any,Sequence
from yado_stateful_frontier_repair_cycle8 import FrontierPortfolioV4, BeliefDiagnosticSchema
from yado_stateful_frontier_repair_cycle10 import FrontierPortfolioV5, ProbabilisticBeliefSchema
from yado_stateful_frontier_repair_cycle12 import FrontierPortfolioV6, ActiveBeliefSchema

class ValidatedFrontierPortfolio:
    """Instance-local structural router over cumulatively validated bounded families.

    This intentionally does not use V6 as an unconditional wrapper because the
    historical V5 probabilistic portfolio bypasses older non-belief families.
    Routing is based only on observable task shape, not task answers.
    """
    def __init__(self,registry:dict|None=None):
        self.registry=dict(registry or {})
        self.general=FrontierPortfolioV4()       # slice/stateful/factored/guarded/coupled/FSM/latent/belief
        self.prob=FrontierPortfolioV5()          # belief + bounded 2-hypothesis probabilistic
        self.active=FrontierPortfolioV6()        # 3-hypothesis active information gain

    @staticmethod
    def _event_input(cases:Sequence[Any])->bool:
        return bool(cases) and all(isinstance(c.input,list) and all(isinstance(e,dict) and set(e)=={'probe','obs'} for e in c.input) for c in cases)

    @classmethod
    def _branch(cls,cases:Sequence[Any])->str:
        if cls._event_input(cases):
            outs=[y for c in cases for y in (c.expected if isinstance(c.expected,list) else [])]
            if outs and all(isinstance(y,dict) and set(y)=={'decision','next_probe'} for y in outs): return 'active'
            return 'prob'
        return 'general'

    def search(self,cases:Sequence[Any]):
        b=self._branch(cases)
        return (self.active if b=='active' else self.prob if b=='prob' else self.general).search(cases)

    def score(self,schema:Any,cases:Sequence[Any]):
        if isinstance(schema,ActiveBeliefSchema): return self.active.score(schema,cases)
        if isinstance(schema,ProbabilisticBeliefSchema): return self.prob.score(schema,cases)
        if isinstance(schema,BeliefDiagnosticSchema): return self.prob.score(schema,cases)
        return self.general.score(schema,cases)

    def execute(self,schema:Any,value:Any):
        if isinstance(schema,ActiveBeliefSchema): return self.active.execute(schema,value)
        if isinstance(schema,ProbabilisticBeliefSchema): return self.prob.execute(schema,value)
        if isinstance(schema,BeliefDiagnosticSchema): return self.prob.execute(schema,value)
        return self.general.execute(schema,value)

__all__=['ValidatedFrontierPortfolio']
