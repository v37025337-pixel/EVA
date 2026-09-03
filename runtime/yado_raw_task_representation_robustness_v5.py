from __future__ import annotations
import re
from yado_raw_task_representation_candidate_v3 import RawTaskRepresentationRuntimeV3
from yado_raw_task_representation_robustness_v4 import (
    RobustRawTaskRepresentationRuntimeV4, bracketless, edge_delimiterless,
    core_view, longest_view, wrapper_signal_v2
)

def _tokens(s):
    return re.findall(r"[A-Za-z0-9_]+",str(s))

def short_edge_signal(text):
    t=str(text).strip()
    parts=[p.strip() for p in re.split(r"(?<=[.!?;:])\s+",t) if p.strip()]
    return len(parts)>=2 and (len(_tokens(parts[0]))<=5 or len(_tokens(parts[-1]))<=5)

def normalized_view(text):
    t=edge_delimiterless(str(text))
    t=re.sub(r"\s+"," ",t).strip()
    return t

def _majority(preds,tie):
    counts={p:preds.count(p) for p in set(preds)}
    best=max(counts.values())
    winners=sorted([p for p,n in counts.items() if n==best])
    if len(winners)==1:return winners[0]
    if tie in winners:return tie
    return winners[0]

class RobustRawTaskRepresentationRuntimeV5:
    COMPONENT_ID="ALG-G2-RAW-TASK-REPRESENTATION-V5"
    def __init__(self,v3_artifact,v4_artifact,mode):
        self.v3=RawTaskRepresentationRuntimeV3(v3_artifact)
        self.v4=RobustRawTaskRepresentationRuntimeV4(v3_artifact,v4_artifact["selected_mode"])
        self.mode=str(mode)

    def predict_capability(self,text):
        if self.mode=="PARENT_V4":
            return self.v4.predict_capability(text)

        if self.mode=="CORE_GUARDED":
            if wrapper_signal_v2(text) or short_edge_signal(text):
                return self.v3.predict_capability(core_view(text))
            return self.v4.predict_capability(text)

        if self.mode=="CONSENSUS_CORE":
            p4=self.v4.predict_capability(text)
            views=[core_view(text),edge_delimiterless(text),longest_view(edge_delimiterless(text))]
            ps=[self.v3.predict_capability(v) for v in views]
            if ps.count(ps[0])==len(ps):return ps[0]
            return _majority([p4]+ps,p4)

        if self.mode=="DUAL_MAJORITY":
            views=[
                str(text), bracketless(text), edge_delimiterless(text), core_view(text),
                longest_view(edge_delimiterless(text)), normalized_view(text),
                core_view(normalized_view(text))
            ]
            ps=[self.v3.predict_capability(v) for v in views]
            return _majority(ps,self.v4.predict_capability(text))

        if self.mode=="V4_PLUS_CORE_VOTE":
            p4=self.v4.predict_capability(text)
            views=[core_view(text),edge_delimiterless(text),core_view(normalized_view(text)),longest_view(edge_delimiterless(text))]
            ps=[p4]+[self.v3.predict_capability(v) for v in views]
            return _majority(ps,p4)

        raise ValueError("UNKNOWN_ROBUST_V5_MODE:"+self.mode)

    def descriptor(self,text):
        label=self.predict_capability(text)
        d={"budget_limited":False,"quota_limited":False,"external_evidence_needed":False,"relation_needed":False,"disjunction_needed":False}
        if label=="ALG-BUDGETED-STAGE-POLICY-V1":d["budget_limited"]=True
        elif label=="RESOURCE-PORTFOLIO-V1":d["external_evidence_needed"]=True
        elif label=="ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1":d["relation_needed"]=True
        return {"capability":label,"routing_descriptor":d,"raw_text":text,"robustness_mode":self.mode}

def component(mode,parent_digest):
    return {
        "schema":"yado.g2.raw_task_representation_robustness_v5.component.v1",
        "component_id":RobustRawTaskRepresentationRuntimeV5.COMPONENT_ID,
        "parent_component_id":"ALG-G2-RAW-TASK-REPRESENTATION-V4",
        "parent_component_digest":parent_digest,
        "mode":mode,
        "generic_sequence_wrapper_robustness":True,
        "class_specific_rules":False,
        "parent_model_retrained":False,
        "canonical_active":False
    }

__all__=["RobustRawTaskRepresentationRuntimeV5","component"]
