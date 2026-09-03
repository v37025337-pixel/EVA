from __future__ import annotations
import math,re
from collections import Counter
from typing import Mapping,Sequence

STOP=set('a an the and or for to of in on with from by is are be this that it as your my our their use using find need via into'.split())

def tokenize(s:str):
    return [x for x in re.findall(r'[a-z0-9]+',str(s).lower()) if len(x)>1 and x not in STOP]

def trigrams(x:str):
    if len(x)<3:return {x}
    return {x[i:i+3] for i in range(len(x)-2)}

def token_soft(a:str,b:str)->float:
    if a==b:return 1.0
    A=trigrams(a);B=trigrams(b)
    return len(A&B)/(len(A|B) or 1)

class OpenAccessSourceRouter:
    FEATURE_NAMES=('TOKEN','IDF_TOKEN','CHAR_TRIGRAM','TOKEN_SOFT')
    def __init__(self,profiles:Mapping[str,Mapping[str,object]]):
        self.profiles=dict(profiles)
        self.docs={k:str(v.get('summary','')) for k,v in self.profiles.items()}
        self.dt={k:tokenize(v) for k,v in self.docs.items()}
        self.df=Counter()
        for ts in self.dt.values():
            for t in set(ts):self.df[t]+=1
    def idf(self,t:str)->float:
        return math.log((len(self.docs)+1)/(self.df[t]+1))+1.0
    def features(self,q:str,rid:str):
        qt=tokenize(q);qs=set(qt);ds=set(self.dt[rid])
        token=len(qs&ds)/(len(qs) or 1)
        idf=sum(self.idf(x) for x in qs&ds)/(sum(self.idf(x) for x in qs) or 1.0)
        qg=set().union(*(trigrams(x) for x in qs)) if qs else set()
        dg=set().union(*(trigrams(x) for x in ds)) if ds else set()
        tri=len(qg&dg)/(len(qg|dg) or 1)
        soft=[]
        for x in qt:
            soft.append(max((token_soft(x,y) for y in ds),default=0.0))
        return {'TOKEN':token,'IDF_TOKEN':idf,'CHAR_TRIGRAM':tri,'TOKEN_SOFT':sum(soft)/(len(soft) or 1)}
    def rank(self,q:str,features:Sequence[str]):
        rows=[]
        for rid in self.docs:
            f=self.features(q,rid);score=sum(f[n] for n in features)/max(1,len(features))
            rows.append((score,rid))
        return sorted(rows,key=lambda z:(z[0],z[1]),reverse=True)
    def route(self,q:str,features:Sequence[str],margin_min:float=0.0,historical_ok:bool=False):
        rows=self.rank(q,features)
        if not historical_ok:
            rows=[row for row in rows if self.profiles[row[1]].get('status')!='RETIRED_ARCHIVE']
        top=rows[0] if rows else (0.0,None); second=rows[1] if len(rows)>1 else (0.0,None)
        margin=top[0]-second[0]
        if top[1] is None or margin < margin_min:
            return {'action':'SEEK_MORE_EVIDENCE','margin':margin,'top':top[1],'ranking':rows[:5]}
        p=self.profiles[top[1]]
        return {'action':'USE_SOURCE','source_id':top[1],'margin':margin,'ranking':rows[:5],
                'use_policy':p.get('use_policy'),'authority':bool(p.get('authority',False)),
                'auto_execute':bool(p.get('auto_execute',False))}
