from __future__ import annotations
from dataclasses import dataclass
from collections import defaultdict
from typing import Iterable,Mapping,Any
import hashlib,json,math

NATIVE_PROVENANCE={
 'kind':'BOUNDED_NATIVE_REDERIVATION_FROM_EXTERNAL_RESEARCH_PRINCIPLES',
 'research':'yado_rc8_metacognitive_training_research_v1.json',
 'external_code_copied_verbatim':False,
 'foundation_weights_modified':False,
}

@dataclass(frozen=True)
class CapabilityObservation:
    capability:str
    difficulty:float
    success:bool

@dataclass(frozen=True)
class MetacognitiveTask:
    task_id:str
    capability:str
    difficulty:float
    verbal_confidence:float
    evidence_coverage:float
    novelty:float=0.0
    framework_conflict:bool=False

@dataclass(frozen=True)
class MetacognitiveDecision:
    action:str
    effective_confidence:float
    profile_confidence:float
    self_disagreement:float
    reason:str

class CapabilityBoundaryProfile:
    def __init__(self, prior_success:float=1.0, prior_failure:float=1.0):
        self.prior_success=float(prior_success); self.prior_failure=float(prior_failure)
        self._bins=defaultdict(lambda:[0,0])
    @staticmethod
    def _bin(difficulty:float)->int:
        x=max(0.0,min(1.0,float(difficulty)))
        return min(3,int(x*4))
    def update(self, obs:CapabilityObservation):
        k=(obs.capability.upper(),self._bin(obs.difficulty))
        self._bins[k][0 if obs.success else 1]+=1
    def fit(self, observations:Iterable[CapabilityObservation]):
        for o in observations:self.update(o)
        return self
    def confidence(self, capability:str,difficulty:float)->float:
        cap=capability.upper(); b=self._bin(difficulty)
        # Borrow neighboring bins with distance weighting so unseen difficulty slices fail soft.
        succ=fail=0.0
        for j in range(4):
            s,f=self._bins.get((cap,j),(0,0)); w=1.0/(1.0+abs(j-b))
            succ+=w*s; fail+=w*f
        return (self.prior_success+succ)/(self.prior_success+self.prior_failure+succ+fail)
    def snapshot(self)->dict[str,Any]:
        rows={f'{c}:{b}':{'success':s,'failure':f} for (c,b),(s,f) in sorted(self._bins.items())}
        return {'prior_success':self.prior_success,'prior_failure':self.prior_failure,'bins':rows}

class MetacognitiveController:
    def __init__(self, execute_threshold:float=0.66, evidence_threshold:float=0.45, disagreement_threshold:float=0.20):
        self.execute_threshold=float(execute_threshold)
        self.evidence_threshold=float(evidence_threshold)
        self.disagreement_threshold=float(disagreement_threshold)
    def decide(self,task:MetacognitiveTask,profile:CapabilityBoundaryProfile)->MetacognitiveDecision:
        v=max(0.0,min(1.0,float(task.verbal_confidence)))
        e=max(0.0,min(1.0,float(task.evidence_coverage)))
        n=max(0.0,min(1.0,float(task.novelty)))
        p=profile.confidence(task.capability,task.difficulty)
        d=abs(v-p)
        if task.framework_conflict:
            return MetacognitiveDecision('ROUTE_FRAMEWORK',min(v,p),p,d,'EPISTEMIC_FRAMEWORK_CONFLICT')
        if e < self.evidence_threshold:
            return MetacognitiveDecision('SEEK_EVIDENCE',min(v,p,e),p,d,'INSUFFICIENT_EVIDENCE')
        score=0.25*v+0.55*p+0.20*e
        score-=0.30*max(0.0,d-self.disagreement_threshold)
        score-=0.16*n
        score=max(0.0,min(1.0,score))
        if score >= self.execute_threshold:
            return MetacognitiveDecision('EXECUTE',score,p,d,'CAPABILITY_AND_EVIDENCE_ALIGNED')
        return MetacognitiveDecision('WITHHOLD',score,p,d,'CAPABILITY_BOUNDARY_OR_DISTRIBUTION_SHIFT')
    @staticmethod
    def feedback(profile:CapabilityBoundaryProfile,task:MetacognitiveTask,success:bool):
        profile.update(CapabilityObservation(task.capability,task.difficulty,bool(success)))

class VerbalOnlyBaseline:
    def __init__(self,execute_threshold:float=0.58,evidence_threshold:float=0.45):
        self.execute_threshold=execute_threshold; self.evidence_threshold=evidence_threshold
    def decide(self,task:MetacognitiveTask)->str:
        if task.evidence_coverage < self.evidence_threshold:return 'SEEK_EVIDENCE'
        return 'EXECUTE' if task.verbal_confidence>=self.execute_threshold else 'WITHHOLD'

def decision_digest(decisions:Iterable[MetacognitiveDecision])->str:
    rows=[d.__dict__ for d in decisions]
    raw=json.dumps(rows,sort_keys=True,separators=(',',':')).encode()
    return hashlib.sha256(raw).hexdigest()

__all__=['CapabilityObservation','MetacognitiveTask','MetacognitiveDecision','CapabilityBoundaryProfile','MetacognitiveController','VerbalOnlyBaseline','decision_digest','NATIVE_PROVENANCE']
