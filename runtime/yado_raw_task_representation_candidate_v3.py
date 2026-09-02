from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
import hashlib,math,re

def words(text):
    return re.findall(r"[a-zA-Z0-9_]+",str(text).lower())

def clauses(text):
    return [x.strip() for x in re.split(r"[,;:.!?]+",str(text).lower()) if x.strip()]

def _hi(s,dim):
    return int(hashlib.sha256(s.encode("utf-8")).hexdigest()[:16],16)%int(dim)

def _add_ngram(c,prefix,text,dim,weight=1.0):
    ws=words(text)
    for w in ws:c[_hi(prefix+"w:"+w,dim)]+=weight
    for a,b in zip(ws,ws[1:]):c[_hi(prefix+"b:"+a+"|"+b,dim)]+=weight
    s=" ".join(ws)
    for n in (4,5):
        if len(s)>=n:
            for i in range(len(s)-n+1):c[_hi(prefix+f"c{n}:"+s[i:i+n],dim)]+=0.35*weight

def features(text,mode,dim=6144,pivot=None):
    c=Counter();_add_ngram(c,"F|",text,dim,1.0)
    ws=words(text)
    if mode in ("POSITIONAL","CLAUSE","PIVOT_CLAUSE"):
        q=max(1,(len(ws)+3)//4)
        for i in range(4):
            seg=" ".join(ws[i*q:(i+1)*q])
            if seg:_add_ngram(c,f"P{i}|",seg,dim,.65)
    if mode in ("CLAUSE","PIVOT_CLAUSE"):
        cs=clauses(text)
        for i,seg in enumerate(cs):
            tag="LAST" if i==len(cs)-1 else ("FIRST" if i==0 else "MID")
            _add_ngram(c,tag+"|",seg,dim,.8 if tag=="LAST" else .55)
    if mode=="PIVOT_CLAUSE" and pivot:
        idx=[i for i,w in enumerate(ws) if w==pivot]
        if idx:
            j=idx[-1]
            pre=" ".join(ws[:j]);post=" ".join(ws[j+1:])
            if pre:_add_ngram(c,"PRE|",pre,dim,.45)
            if post:_add_ngram(c,"POST|",post,dim,1.05)
            c[_hi("PIVOT_PRESENT:"+pivot,dim)]+=1.0
    z=math.sqrt(sum(v*v for v in c.values())) or 1.0
    return {int(k):float(v)/z for k,v in c.items()}

def _dot(w,x):
    return sum(float(w.get(str(k),w.get(k,0.0)))*v for k,v in x.items())

def _pred(labels,w,b,x):
    a=[(_dot(w.get(l,{}),x)+float(b.get(l,0.0)),l) for l in labels]
    a.sort(key=lambda z:(-z[0],z[1]));return a[0][1]

@dataclass
class StructuralRawRepresentationSpecV3:
    family:str
    labels:list[str]
    payload:dict
    def predict(self,text):
        x=features(text,self.payload["mode"],int(self.payload["dim"]),self.payload.get("pivot"))
        return _pred(self.labels,self.payload["weights"],self.payload["bias"],x)

def fit_structural_perceptron(rows,mode,pivot=None,dim=6144,epochs=32):
    labels=sorted({y for _,y in rows});w={l:{} for l in labels};b={l:0.0 for l in labels}
    base=sorted(rows,key=lambda r:hashlib.sha256((r[0]+"|"+r[1]).encode()).hexdigest())
    for ep in range(int(epochs)):
        seq=sorted(base,key=lambda r:hashlib.sha256((str(ep)+"|"+r[0]+"|"+r[1]).encode()).hexdigest())
        eta=1.0/(1+.035*ep)
        for text,y in seq:
            x=features(text,mode,dim,pivot);p=_pred(labels,w,b,x)
            if p==y:continue
            for k,v in x.items():
                sk=str(k);w[y][sk]=float(w[y].get(sk,0.0))+eta*v;w[p][sk]=float(w[p].get(sk,0.0))-eta*v
            b[y]+=.08*eta;b[p]-=.08*eta
    fam={"POSITIONAL":"STRUCTURAL_POSITIONAL_PERCEPTRON","CLAUSE":"STRUCTURAL_CLAUSE_PERCEPTRON","PIVOT_CLAUSE":"STRUCTURAL_PIVOT_CLAUSE_PERCEPTRON"}[mode]
    return StructuralRawRepresentationSpecV3(fam,labels,{"mode":mode,"pivot":pivot,"dim":dim,"epochs":epochs,"weights":w,"bias":b})

def discover_pivot_candidates(rows,max_candidates=28,min_df=3):
    df=Counter()
    for text,_ in rows:
        for w in set(words(text)):df[w]+=1
    # Generic discovery: frequent interior tokens only; no hand-authored semantic marker list.
    ranked=sorted([(n,w) for w,n in df.items() if n>=min_df and len(w)>=2],key=lambda z:(-z[0],z[1]))
    return [w for _,w in ranked[:max_candidates]]

class RawTaskRepresentationRuntimeV3:
    def __init__(self,artifact):
        m=artifact.get("model") or {}
        self.spec=StructuralRawRepresentationSpecV3(m["family"],list(m["labels"]),m["payload"])
        self.artifact=artifact
    def predict_capability(self,text):return self.spec.predict(text)
    def descriptor(self,text):
        label=self.predict_capability(text)
        d={"budget_limited":False,"quota_limited":False,"external_evidence_needed":False,"relation_needed":False,"disjunction_needed":False}
        if label=="ALG-BUDGETED-STAGE-POLICY-V1":d["budget_limited"]=True
        elif label=="RESOURCE-PORTFOLIO-V1":d["external_evidence_needed"]=True
        elif label=="ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1":d["relation_needed"]=True
        return {"capability":label,"routing_descriptor":d,"raw_text":text}

def spec_to_json(spec):return {"family":spec.family,"labels":spec.labels,"payload":spec.payload}
__all__=["fit_structural_perceptron","discover_pivot_candidates","RawTaskRepresentationRuntimeV3","spec_to_json"]
