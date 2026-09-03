from __future__ import annotations
import math
from collections import Counter
from typing import Mapping,Any

class HostCapabilityRelationRouter:
    """Bounded content router for the learned observable ChatGPT capability model."""
    def __init__(self, model:Mapping[str,Any]):
        self.model=dict(model or {})
        self.n=int(self.model.get('ngram_n',4))
        self.top_min=float(self.model.get('top_min',1.1))
        self.margin_min=float(self.model.get('margin_min',1.1))
        self.profiles=dict(self.model.get('profiles') or {})
    @staticmethod
    def grams(text:str,n:int):
        s=' '.join(str(text).lower().split()); pad=' '+s+' '
        return Counter(pad[i:i+n] for i in range(max(0,len(pad)-n+1)))
    @staticmethod
    def cosine(a,b):
        if not a or not b:return 0.0
        dot=sum(v*b.get(k,0) for k,v in a.items())
        na=math.sqrt(sum(v*v for v in a.values())); nb=math.sqrt(sum(v*v for v in b.values()))
        return 0.0 if na==0 or nb==0 else dot/(na*nb)
    def route(self,query:str):
        if not self.profiles:
            return {'action':'SEEK_MORE_EVIDENCE','reason':'NO_DURABLE_HOST_CAPABILITY_PROFILES'}
        g=self.grams(query,self.n)
        rows=sorted(((self.cosine(g,self.grams(text,self.n)),label) for label,text in self.profiles.items()),reverse=True)
        top,label=rows[0]; second=rows[1][0] if len(rows)>1 else 0.0; margin=top-second
        accepted=top>=self.top_min and margin>=self.margin_min
        return {'action':label if accepted else 'SEEK_MORE_EVIDENCE','top_candidate':label,'top_score':top,'margin':margin,'top_min':self.top_min,'margin_min':self.margin_min,'accepted':accepted,'top3':[{'label':lab,'score':score} for score,lab in rows[:3]]}

__all__=['HostCapabilityRelationRouter']
