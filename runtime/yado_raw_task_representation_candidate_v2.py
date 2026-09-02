from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
import hashlib,json,math,re

def _words(text):
    return re.findall(r"[a-zA-Z0-9_]+",str(text).lower())

def _norm_sparse(d):
    z=math.sqrt(sum(float(v)*float(v) for v in d.values())) or 1.0
    return {int(k):float(v)/z for k,v in d.items() if v}

def _hash_feature(s,dim):
    return int(hashlib.sha256(s.encode("utf-8")).hexdigest()[:16],16)%int(dim)

def _features(text,mode,dim=4096):
    ws=_words(text);c=Counter()
    if mode in ("WORD_BIGRAM","HYBRID"):
        for w in ws:c[_hash_feature("w:"+w,dim)]+=1.0
        for a,b in zip(ws,ws[1:]):c[_hash_feature("b:"+a+"|"+b,dim)]+=1.0
    if mode in ("CHAR45","HYBRID"):
        s=" ".join(ws)
        for n in (4,5):
            if len(s)>=n:
                for i in range(len(s)-n+1):c[_hash_feature(f"c{n}:"+s[i:i+n],dim)]+=0.5
    return _norm_sparse(c)

def _dot(w,x):
    return sum(float(w.get(str(k),w.get(k,0.0)))*v for k,v in x.items())

@dataclass
class RawTaskRepresentationSpecV2:
    family:str
    labels:list[str]
    payload:dict

    def predict(self,text):
        if self.family.startswith("HASHED_") and self.family.endswith("_PERCEPTRON"):
            mode=self.payload["mode"];dim=int(self.payload["dim"]);x=_features(text,mode,dim)
            scores=[]
            for label in self.labels:
                scores.append((_dot(self.payload["weights"].get(label,{}),x)+float(self.payload["bias"].get(label,0.0)),label))
            scores.sort(key=lambda z:(-z[0],z[1]))
            return scores[0][1]
        if self.family=="TFIDF_HYBRID_CENTROID":
            mode=self.payload["mode"];dim=int(self.payload["dim"]);x=_features(text,mode,dim)
            idf=self.payload["idf"]
            x={k:v*float(idf.get(str(k),idf.get(k,1.0))) for k,v in x.items()};x=_norm_sparse(x)
            scores=[]
            for label in self.labels:
                scores.append((_dot(self.payload["centroids"].get(label,{}),x),label))
            scores.sort(key=lambda z:(-z[0],z[1]))
            return scores[0][1]
        raise ValueError("UNKNOWN_V2_FAMILY:"+self.family)

def _predict_weights(labels,weights,bias,x):
    scores=[(_dot(weights.get(label,{}),x)+float(bias.get(label,0.0)),label) for label in labels]
    scores.sort(key=lambda z:(-z[0],z[1]))
    return scores[0][1]

def fit_hashed_perceptron(rows,mode,dim=4096,epochs=28):
    labels=sorted({y for _,y in rows})
    w={l:{} for l in labels};b={l:0.0 for l in labels}
    ordered=sorted(list(rows),key=lambda r:hashlib.sha256((r[0]+"|"+r[1]).encode()).hexdigest())
    for ep in range(int(epochs)):
        seq=sorted(ordered,key=lambda r:hashlib.sha256((str(ep)+"|"+r[0]+"|"+r[1]).encode()).hexdigest())
        eta=1.0/(1.0+0.04*ep)
        for text,y in seq:
            x=_features(text,mode,dim);p=_predict_weights(labels,w,b,x)
            if p==y:continue
            wy=w[y];wp=w[p]
            for k,v in x.items():
                sk=str(k);wy[sk]=float(wy.get(sk,0.0))+eta*v;wp[sk]=float(wp.get(sk,0.0))-eta*v
            b[y]+=0.10*eta;b[p]-=0.10*eta
    return RawTaskRepresentationSpecV2("HASHED_"+mode+"_PERCEPTRON",labels,{"mode":mode,"dim":dim,"epochs":epochs,"weights":w,"bias":b})

def fit_tfidf_hybrid_centroid(rows,dim=4096):
    labels=sorted({y for _,y in rows});docs=[];df=Counter()
    for text,y in rows:
        x=_features(text,"HYBRID",dim);docs.append((x,y))
        for k in x:df[k]+=1
    n=max(1,len(docs));idf={str(k):math.log((1+n)/(1+v))+1.0 for k,v in df.items()}
    sums={l:Counter() for l in labels};cnt=Counter()
    for x,y in docs:
        z={k:v*float(idf.get(str(k),1.0)) for k,v in x.items()};z=_norm_sparse(z)
        sums[y].update(z);cnt[y]+=1
    cent={}
    for l in labels:
        c={str(k):float(v)/max(1,cnt[l]) for k,v in sums[l].items()}
        z=math.sqrt(sum(v*v for v in c.values())) or 1.0
        cent[l]={k:v/z for k,v in c.items()}
    return RawTaskRepresentationSpecV2("TFIDF_HYBRID_CENTROID",labels,{"mode":"HYBRID","dim":dim,"idf":idf,"centroids":cent})

def fit_family(rows,family):
    if family=="HASHED_WORD_BIGRAM_PERCEPTRON":return fit_hashed_perceptron(rows,"WORD_BIGRAM")
    if family=="HASHED_CHAR45_PERCEPTRON":return fit_hashed_perceptron(rows,"CHAR45")
    if family=="HASHED_HYBRID_PERCEPTRON":return fit_hashed_perceptron(rows,"HYBRID")
    if family=="TFIDF_HYBRID_CENTROID":return fit_tfidf_hybrid_centroid(rows)
    raise ValueError("UNKNOWN_V2_FAMILY:"+family)

class RawTaskRepresentationRuntimeV2:
    COMPONENT_ID="ALG-G2-RAW-TASK-REPRESENTATION-V2"
    def __init__(self,artifact):
        m=artifact.get("model") or {}
        self.spec=RawTaskRepresentationSpecV2(m["family"],list(m["labels"]),m["payload"])
        self.artifact=artifact
    def predict_capability(self,text):
        return self.spec.predict(text)
    def descriptor(self,text):
        label=self.predict_capability(text)
        d={"budget_limited":False,"quota_limited":False,"external_evidence_needed":False,"relation_needed":False,"disjunction_needed":False}
        if label=="ALG-BUDGETED-STAGE-POLICY-V1":d["budget_limited"]=True
        elif label=="RESOURCE-PORTFOLIO-V1":d["external_evidence_needed"]=True
        elif label=="ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1":d["relation_needed"]=True
        return {"capability":label,"routing_descriptor":d,"raw_text":text}

def spec_to_json(spec):
    return {"family":spec.family,"labels":spec.labels,"payload":spec.payload}

__all__=["RawTaskRepresentationSpecV2","RawTaskRepresentationRuntimeV2","fit_family","spec_to_json"]
