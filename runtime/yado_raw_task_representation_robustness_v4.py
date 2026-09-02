from __future__ import annotations
import re,copy
from yado_raw_task_representation_candidate_v3 import RawTaskRepresentationRuntimeV3

def _tokens(s):
    return re.findall(r"[A-Za-z0-9_]+",str(s))

def _segments(text):
    parts=[p.strip() for p in re.split(r"(?<=[.!?;:])\s+",str(text)) if p.strip()]
    return parts or [str(text).strip()]

def bracketless(text):
    return re.sub(r"\[[^\]]{0,160}\]"," ",str(text)).strip()

def edge_delimiterless(text):
    t=str(text).strip()
    # Generic edge metadata removal only: short balanced delimiter blocks at the beginning/end.
    patterns=[
      (r"^\([^\)]{0,80}\)\s*",""),
      (r"^\{[^\}]{0,80}\}\s*",""),
      (r"^<[^>]{0,80}>\s*",""),
      (r"\s*<[^>]{0,80}>$",""),
      (r"\s*\{[^\}]{0,80}\}$",""),
      (r"\s*\([^\)]{0,80}\)$",""),
    ]
    prev=None
    while prev!=t:
        prev=t
        for pat,repl in patterns:t=re.sub(pat,repl,t).strip()
    return bracketless(t)

def core_view(text):
    t=edge_delimiterless(text)
    seg=_segments(t)
    if len(seg)>=2 and len(_tokens(seg[0]))<=4:
        seg=seg[1:]
    if len(seg)>=2 and len(_tokens(seg[-1]))<=4:
        seg=seg[:-1]
    out=" ".join(seg).strip()
    return out or t

def longest_view(text):
    seg=_segments(bracketless(text))
    if not seg:return str(text)
    return max(seg,key=lambda s:(len(_tokens(s)),len(s)))

def wrapper_signal(text):
    t=str(text)
    if re.search(r"\[[^\]]{0,160}\]",t):return True
    seg=_segments(t)
    return len(seg)>=2 and (len(_tokens(seg[0]))<=4 or len(_tokens(seg[-1]))<=4)

def wrapper_signal_v2(text):
    t=str(text).strip()
    if wrapper_signal(t):return True
    if re.match(r"^(\([^\)]{0,80}\)|\{[^\}]{0,80}\}|<[^>]{0,80}>)\s*",t):return True
    if re.search(r"\s*(<[^>]{0,80}>|\{[^\}]{0,80}\}|\([^\)]{0,80}\))$",t):return True
    return False

class RobustRawTaskRepresentationRuntimeV4:
    COMPONENT_ID="ALG-G2-RAW-TASK-REPRESENTATION-V4"
    def __init__(self,v3_artifact,mode):
        self.parent=RawTaskRepresentationRuntimeV3(v3_artifact)
        self.mode=str(mode)

    def predict_capability(self,text):
        if self.mode=="CORE_IF_WRAPPER":
            return self.parent.predict_capability(core_view(text) if wrapper_signal(text) else text)
        if self.mode=="MULTIVIEW_TIE_CORE":
            views=[str(text),bracketless(text),core_view(text),longest_view(text)]
            preds=[self.parent.predict_capability(v) for v in views]
            counts={p:preds.count(p) for p in set(preds)}
            best=max(counts.values())
            winners=sorted([p for p,n in counts.items() if n==best])
            if len(winners)==1:return winners[0]
            cp=self.parent.predict_capability(core_view(text))
            if cp in winners:return cp
            return winners[0]
        if self.mode=="EDGE_WRAPPER_CORE":
            return self.parent.predict_capability(core_view(text) if wrapper_signal_v2(text) else text)
        if self.mode=="MULTIVIEW_EDGE_TIE_CORE":
            views=[str(text),bracketless(text),edge_delimiterless(text),core_view(text),longest_view(edge_delimiterless(text))]
            preds=[self.parent.predict_capability(v) for v in views]
            counts={p:preds.count(p) for p in set(preds)}
            best=max(counts.values());winners=sorted([p for p,n in counts.items() if n==best])
            if len(winners)==1:return winners[0]
            cp=self.parent.predict_capability(core_view(text))
            if cp in winners:return cp
            return winners[0]
        if self.mode=="CORE_ALWAYS":
            return self.parent.predict_capability(core_view(text))
        if self.mode=="PARENT_V3":
            return self.parent.predict_capability(text)
        raise ValueError("UNKNOWN_ROBUST_V4_MODE:"+self.mode)

    def descriptor(self,text):
        label=self.predict_capability(text)
        d={"budget_limited":False,"quota_limited":False,"external_evidence_needed":False,"relation_needed":False,"disjunction_needed":False}
        if label=="ALG-BUDGETED-STAGE-POLICY-V1":d["budget_limited"]=True
        elif label=="RESOURCE-PORTFOLIO-V1":d["external_evidence_needed"]=True
        elif label=="ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1":d["relation_needed"]=True
        return {"capability":label,"routing_descriptor":d,"raw_text":text,"robustness_mode":self.mode}

def component(mode,parent_digest):
    return {
      "schema":"yado.g2.raw_task_representation_robustness_v4.component.v1",
      "component_id":RobustRawTaskRepresentationRuntimeV4.COMPONENT_ID,
      "parent_component_id":"ALG-G2-RAW-TASK-REPRESENTATION-V3",
      "parent_component_digest":parent_digest,
      "mode":mode,
      "generic_wrapper_invariance":True,
      "class_specific_rules":False,
      "parent_model_retrained":False,
      "canonical_active":False,
    }

__all__=["RobustRawTaskRepresentationRuntimeV4","core_view","bracketless","edge_delimiterless","longest_view","wrapper_signal","wrapper_signal_v2","component"]
