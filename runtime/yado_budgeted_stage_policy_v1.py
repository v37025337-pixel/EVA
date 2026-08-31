from __future__ import annotations
from dataclasses import dataclass
from itertools import permutations
import hashlib,json

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()

@dataclass(frozen=True)
class SearchStage:
    stage_id:str
    cost:float
    expected_gain:float
    quota_remaining:int
    available:bool=True
    latency:float=1.0
    attempted:bool=False

@dataclass
class StagePlan:
    action:str
    sequence:list[str]
    expected_confidence:float
    total_cost:float
    feasible:bool
    reason:str
    def canonical(self):
        return {
          'action':self.action,'sequence':self.sequence,
          'expected_confidence':self.expected_confidence,'total_cost':self.total_cost,
          'feasible':self.feasible,'reason':self.reason,
        }

class BudgetedStagePolicyV1:
    MAX_STAGES=6
    MAX_PLAN_DEPTH=4

    @classmethod
    def plan(cls,current_confidence,target_confidence,remaining_budget,stages,
             ignore_budget=False,ignore_attempted=False):
        current=float(current_confidence);target=float(target_confidence);budget=float(remaining_budget)
        if current>=target:
            return StagePlan('STOP',[],current,0.0,True,'TARGET_ALREADY_MET')
        xs=list(stages)[:cls.MAX_STAGES]
        usable=[
          s for s in xs
          if s.available and s.quota_remaining>0 and (ignore_attempted or not s.attempted)
        ]
        if not usable:
            return StagePlan('WITHHOLD',[],current,0.0,False,'NO_USABLE_STAGE')

        candidates=[]
        max_depth=min(cls.MAX_PLAN_DEPTH,len(usable))
        for depth in range(1,max_depth+1):
            for seq in permutations(usable,depth):
                cost=sum(max(0.0,float(s.cost)) for s in seq)
                if not ignore_budget and cost>budget+1e-12:
                    continue
                conf=min(1.0,current+sum(max(0.0,float(s.expected_gain)) for s in seq))
                latency=sum(max(0.0,float(s.latency)) for s in seq)
                reaches=conf>=target
                key=(
                  0 if reaches else 1,
                  cost if reaches else -conf,
                  depth,
                  latency,
                  tuple(s.stage_id for s in seq),
                )
                candidates.append((key,seq,cost,conf,reaches))
        if not candidates:
            return StagePlan('WITHHOLD',[],current,0.0,False,'BUDGET_OR_QUOTA_BLOCKED')
        candidates.sort(key=lambda z:z[0])
        _,seq,cost,conf,reaches=candidates[0]
        ids=[s.stage_id for s in seq]
        return StagePlan(
          ids[0],ids,conf,cost,True,
          'MIN_COST_PLAN_REACHES_TARGET' if reaches else 'BEST_REACHABLE_EVIDENCE_WITHIN_BUDGET'
        )

    @classmethod
    def next_after_observation(cls,current_confidence,target_confidence,remaining_budget,stages,
                               completed_stage_id,observed_gain,
                               ignore_budget=False,ignore_attempted=False):
        new_conf=min(1.0,float(current_confidence)+max(0.0,float(observed_gain)))
        spent=0.0
        updated=[]
        for s in stages:
            if s.stage_id==completed_stage_id:
                spent=max(0.0,float(s.cost))
                updated.append(SearchStage(
                  s.stage_id,s.cost,s.expected_gain,max(0,s.quota_remaining-1),
                  s.available,s.latency,False if ignore_attempted else True
                ))
            else:
                updated.append(s)
        new_budget=float(remaining_budget)-spent
        return cls.plan(
          new_conf,target_confidence,new_budget,updated,
          ignore_budget=ignore_budget,ignore_attempted=ignore_attempted
        )
