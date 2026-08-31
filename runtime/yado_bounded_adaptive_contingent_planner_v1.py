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

class BoundedAdaptiveContingentPlannerV1:
    COMPONENT_ID="ALG-G2-BOUNDED-ADAPTIVE-CONTINGENT-PLANNER-V1"
    MAX_STAGES=8
    MAX_PLAN_DEPTH=8
    SIGNED_OBSERVATION=True
    DEPENDENCY_AWARE=True

    @classmethod
    def _usable(cls,s,done):
        if s.attempted or s.quota_remaining<=0:return False
        if s.requires and cls.DEPENDENCY_AWARE:return all(x in done for x in s.requires)
        return bool(s.available)

    @classmethod
    def plan(cls,current_confidence,target_confidence,remaining_budget,stages:Iterable[ContingentStage],completed=()):
        current=max(0.0,min(1.0,float(current_confidence)));target=float(target_confidence);budget=float(remaining_budget)
        xs=list(stages)[:cls.MAX_STAGES];done=set(completed);cand=[]
        if current>=target:return ContingentPlan("STOP",[],current,0.0,True,"TARGET_ALREADY_MET")
        def dfs(seq,seen,cost,conf):
            if seq:
                reaches=conf>=target
                key=(0,cost,len(seq),-conf,tuple(x.stage_id for x in seq)) if reaches else (1,-conf,cost,len(seq),tuple(x.stage_id for x in seq))
                cand.append((key,list(seq),cost,conf,reaches))
            if len(seq)>=cls.MAX_PLAN_DEPTH:return
            for s in xs:
                if s.stage_id in seen or not cls._usable(s,seen):continue
                nc=cost+max(0.0,float(s.cost))
                if nc>budget+1e-12:continue
                dfs(seq+[s],seen|{s.stage_id},nc,max(0.0,min(1.0,conf+max(0.0,float(s.expected_gain)))))
        dfs([],done,0.0,current)
        if not cand:return ContingentPlan("WITHHOLD",[],current,0.0,False,"NO_FEASIBLE_PLAN")
        cand.sort(key=lambda z:z[0]);_,seq,cost,conf,reaches=cand[0]
        return ContingentPlan(seq[0].stage_id,[x.stage_id for x in seq],conf,cost,True,"TARGET_REACHABLE" if reaches else "BEST_REACHABLE")

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
