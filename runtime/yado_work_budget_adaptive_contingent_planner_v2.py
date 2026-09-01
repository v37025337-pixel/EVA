from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable

@dataclass(frozen=True)
class ContingentStage:
    stage_id:str
    cost:float
    expected_gain:float
    quota_remaining:int=1
    available:bool=True
    latency:float=1.0
    attempted:bool=False
    requires:tuple[str,...]=()

@dataclass
class ContingentPlan:
    action:str
    sequence:list[str]
    expected_confidence:float
    total_cost:float
    feasible:bool
    reason:str

class WorkBudgetAdaptiveContingentPlannerV2:
    COMPONENT_ID="ALG-G2-WORK-BUDGET-ADAPTIVE-CONTINGENT-PLANNER-V2"
    MAX_STAGE_RECORDS=64
    MAX_PLAN_STEPS=32
    MAX_SEARCH_NODES=24000
    BEAM_WIDTH=256
    SIGNED_OBSERVATION=True
    DEPENDENCY_AWARE=True

    @classmethod
    def _usable(cls,s,done):
        if s.attempted or s.quota_remaining<=0:return False
        if s.requires and cls.DEPENDENCY_AWARE:return all(x in done for x in s.requires)
        return bool(s.available)

    @classmethod
    def _state_key(cls,seq,cost,conf,target):
        reaches=conf>=target
        ids=tuple(x.stage_id for x in seq)
        return (0,cost,len(seq),-conf,ids) if reaches else (1,-conf,cost,len(seq),ids)

    @classmethod
    def plan(cls,current_confidence,target_confidence,remaining_budget,stages:Iterable[ContingentStage],completed=()):
        current=max(0.0,min(1.0,float(current_confidence)));target=float(target_confidence);budget=float(remaining_budget)
        xs=list(stages)
        if len(xs)>cls.MAX_STAGE_RECORDS:
            return ContingentPlan("WITHHOLD",[],current,0.0,False,"STAGE_RECORD_WORK_BUDGET")
        done0=frozenset(str(x) for x in completed)
        if current>=target:return ContingentPlan("STOP",[],current,0.0,True,"TARGET_ALREADY_MET")

        frontier=[([],done0,0.0,current)]
        candidates=[];nodes=0
        max_steps=min(cls.MAX_PLAN_STEPS,len(xs))

        for _depth in range(max_steps):
            nxt=[]
            for seq,seen,cost,conf in frontier:
                for s in xs:
                    if s.stage_id in seen or not cls._usable(s,seen):continue
                    nc=cost+max(0.0,float(s.cost))
                    if nc>budget+1e-12:continue
                    ng=max(0.0,float(s.expected_gain))
                    nconf=max(0.0,min(1.0,conf+ng))
                    nseq=seq+[s];nseen=seen|{s.stage_id}
                    nodes+=1
                    if nodes>cls.MAX_SEARCH_NODES:
                        if candidates:
                            candidates.sort(key=lambda z:z[0])
                            _,best,cost2,conf2,reaches=candidates[0]
                            return ContingentPlan(best[0].stage_id,[x.stage_id for x in best],conf2,cost2,True,
                                "TARGET_REACHABLE_WORK_BUDGET" if reaches else "BEST_REACHABLE_WORK_BUDGET")
                        return ContingentPlan("WITHHOLD",[],current,0.0,False,"SEARCH_WORK_BUDGET")
                    key=cls._state_key(nseq,nc,nconf,target)
                    candidates.append((key,nseq,nc,nconf,nconf>=target))
                    nxt.append((nseq,nseen,nc,nconf))
            if not nxt:break
            nxt.sort(key=lambda z:cls._state_key(z[0],z[2],z[3],target))
            frontier=nxt[:cls.BEAM_WIDTH]

        if not candidates:return ContingentPlan("WITHHOLD",[],current,0.0,False,"NO_FEASIBLE_PLAN")
        candidates.sort(key=lambda z:z[0]);_,seq,cost,conf,reaches=candidates[0]
        return ContingentPlan(seq[0].stage_id,[x.stage_id for x in seq],conf,cost,True,
            "TARGET_REACHABLE" if reaches else "BEST_REACHABLE")

    @classmethod
    def next_after_observation(cls,current_confidence,target_confidence,remaining_budget,stages,completed_stage_id,observed_gain,completed=()):
        xs=list(stages);spent=0.0;updated=[]
        for s in xs:
            if s.stage_id==completed_stage_id:
                spent=max(0.0,float(s.cost))
                updated.append(ContingentStage(s.stage_id,s.cost,s.expected_gain,max(0,s.quota_remaining-1),s.available,s.latency,True,s.requires))
            else:updated.append(s)
        gain=float(observed_gain) if cls.SIGNED_OBSERVATION else max(0.0,float(observed_gain))
        conf=max(0.0,min(1.0,float(current_confidence)+gain))
        return cls.plan(conf,target_confidence,float(remaining_budget)-spent,updated,tuple(set(completed)|{completed_stage_id}))

__all__=["ContingentStage","ContingentPlan","WorkBudgetAdaptiveContingentPlannerV2"]
