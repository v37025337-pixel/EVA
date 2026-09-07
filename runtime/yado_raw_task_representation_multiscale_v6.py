from __future__ import annotations
from collections import Counter
from functools import lru_cache
import hashlib,re

from yado_raw_task_representation_candidate_v2 import RawTaskRepresentationSpecV2,_features,_dot

class RawTaskRepresentationMultiscaleRuntimeV6:
    COMPONENT_ID="ALG-G2-RAW-TASK-REPRESENTATION-MULTISCALE-V6"

    def __init__(self,parent_model,expanded_spec):
        self.parent=RawTaskRepresentationSpecV2(parent_model["family"],list(parent_model["labels"]),parent_model["payload"])
        self.labels=list(self.parent.labels)
        self.spec={
          "widths":[int(x) for x in expanded_spec["widths"]],
          "aggregation":str(expanded_spec["aggregation"]),
          "stride_div":int(expanded_spec["stride_div"]),
          "topk":int(expanded_spec.get("topk",3)),
        }
        self._score_cache={}
        self._window_cache={}

    def _raw_scores(self,text):
        text=str(text)
        if text in self._score_cache:return self._score_cache[text]
        mode=self.parent.payload["mode"];dim=int(self.parent.payload["dim"]);x=_features(text,mode,dim)
        rows=[]
        for label in self.labels:
            s=_dot(self.parent.payload["weights"].get(label,{}),x)+float(self.parent.payload["bias"].get(label,0.0))
            rows.append((float(s),label))
        rows.sort(key=lambda z:(-z[0],z[1]))
        self._score_cache[text]=rows
        return rows

    def _token_windows(self,text,width,stride):
        key=(str(text),int(width),int(stride))
        if key in self._window_cache:return self._window_cache[key]
        toks=re.findall(r"[a-zA-Z0-9_]+",str(text))
        if not toks:out=[str(text)]
        elif len(toks)<=width:out=[' '.join(toks)]
        else:
            out=[]
            for i in range(0,max(1,len(toks)-width+1),max(1,stride)):
                out.append(' '.join(toks[i:i+width]))
            tail=' '.join(toks[-width:])
            if not out or out[-1]!=tail:out.append(tail)
        self._window_cache[key]=out
        return out

    def predict_capability(self,text):
        widths=self.spec["widths"];stride_div=self.spec["stride_div"];mode=self.spec["aggregation"];topk=self.spec["topk"]
        segments=[str(text)]
        for w in widths:
            segments.extend(self._token_windows(text,w,max(1,w//stride_div)))
        seen=set();uniq=[]
        for z in segments:
            h=hashlib.sha256(z.encode()).hexdigest()
            if h not in seen:
                seen.add(h);uniq.append(z)
        scored=[]
        for idx,z in enumerate(uniq):
            rs=self._raw_scores(z);margin=rs[0][0]-rs[1][0] if len(rs)>1 else 0.0
            scored.append({"label":rs[0][1],"margin":float(margin),"score":float(rs[0][0]),"index":idx})
        if mode=="MAX_MARGIN":
            q=sorted(scored,key=lambda r:(-r["margin"],-r["score"],r["label"],r["index"]))[0]
            return q["label"]
        if mode=="TOPK_MARGIN_VOTE":
            q=sorted(scored,key=lambda r:(-r["margin"],-r["score"],r["label"],r["index"]))[:max(1,topk)]
            sums=Counter()
            for r in q:sums[r["label"]]+=max(1e-9,r["margin"])
            return sorted(sums.items(),key=lambda z:(-z[1],z[0]))[0][0]
        if mode=="ALL_MARGIN_VOTE":
            sums=Counter()
            for r in scored:sums[r["label"]]+=max(1e-9,r["margin"])
            return sorted(sums.items(),key=lambda z:(-z[1],z[0]))[0][0]
        raise ValueError("UNKNOWN_AGGREGATION:"+mode)

    def descriptor(self,text):
        label=self.predict_capability(text)
        d={"budget_limited":False,"quota_limited":False,"external_evidence_needed":False,"relation_needed":False,"disjunction_needed":False}
        if label=="ALG-BUDGETED-STAGE-POLICY-V1":d["budget_limited"]=True
        elif label=="RESOURCE-PORTFOLIO-V1":d["external_evidence_needed"]=True
        elif label=="ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1":d["relation_needed"]=True
        return {"capability":label,"routing_descriptor":d,"raw_text":text}

__all__=["RawTaskRepresentationMultiscaleRuntimeV6"]
