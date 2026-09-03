from __future__ import annotations
from dataclasses import asdict, dataclass
from collections import defaultdict
from typing import Any, Iterable, Mapping, Sequence
import hashlib, json

NATIVE_PROVENANCE={
  'status':'NATIVE_BOUNDED_TRANSFER_MEMORY_RUNTIME',
  'source':'ACTIVE_YADO_CONTRACTS_PLUS_EXTERNAL_RESEARCH_PRINCIPLES',
  'principles':['PROCEDURAL_MEMORY_CONSOLIDATION','CROSS_DOMAIN_SUPPORT','RETRIEVAL_INTERFERENCE_GUARD','NEGATIVE_TRANSFER_FILTER'],
  'external_code_copied_verbatim':False,
  'foundation_weights_modified':False,
}

def _canonical(x:Any)->str:return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False)
def _digest(x:Any)->str:return hashlib.sha256(_canonical(x).encode()).hexdigest()
def _jaccard(a:set[str],b:set[str])->float:
    u=a|b
    return len(a&b)/len(u) if u else 0.0

@dataclass(frozen=True)
class TransferExperience:
    experience_id:str
    domain:str
    tags:Sequence[str]
    procedure:Sequence[str]
    outcome_score:float
    success:bool=True
    metadata:Mapping[str,Any]|None=None
    def canonical(self)->dict[str,Any]:
        d=asdict(self); d['tags']=sorted(set(map(str,self.tags))); d['procedure']=list(map(str,self.procedure)); d['metadata']=dict(sorted((self.metadata or {}).items())); return d

@dataclass(frozen=True)
class ProceduralMemory:
    memory_id:str
    stable_tags:Sequence[str]
    procedure:Sequence[str]
    support:int
    support_domains:Sequence[str]
    mean_score:float
    failure_rate:float
    source_digest:str
    def canonical(self)->dict[str,Any]:
        d=asdict(self); d['stable_tags']=sorted(set(map(str,self.stable_tags))); d['procedure']=list(map(str,self.procedure)); d['support_domains']=sorted(set(map(str,self.support_domains))); return d

class TransferMemoryRuntime:
    """Consolidate repeated cross-domain experiences into bounded procedural memory.

    Raw trajectories remain evidence, but only procedures with repeated cross-domain
    support and low failure rate are promoted for transfer retrieval.
    """
    def __init__(self, *, min_support:int=3, min_domains:int=2, min_mean_score:float=.75, max_failure_rate:float=.20):
        self.min_support=max(1,int(min_support)); self.min_domains=max(1,int(min_domains)); self.min_mean_score=float(min_mean_score); self.max_failure_rate=float(max_failure_rate)

    def consolidate(self, experiences:Iterable[TransferExperience])->dict[str,Any]:
        groups=defaultdict(list)
        for e in experiences:
            if not e.experience_id or not e.domain or not e.procedure: continue
            groups[tuple(map(str,e.procedure))].append(e)
        memories=[]; rejected=[]
        for proc,grp in sorted(groups.items(),key=lambda kv:repr(kv[0])):
            domains=sorted({str(e.domain) for e in grp})
            scores=[float(e.outcome_score) for e in grp]
            failures=sum(not bool(e.success) for e in grp)
            mean=sum(scores)/len(scores)
            fr=failures/len(grp)
            tagsets=[set(map(str,e.tags)) for e in grp]
            stable=set.intersection(*tagsets) if tagsets else set()
            reasons=[]
            if len(grp)<self.min_support: reasons.append('INSUFFICIENT_SUPPORT')
            if len(domains)<self.min_domains: reasons.append('INSUFFICIENT_DOMAIN_DIVERSITY')
            if mean<self.min_mean_score: reasons.append('LOW_MEAN_OUTCOME')
            if fr>self.max_failure_rate: reasons.append('FAILURE_RATE_TOO_HIGH')
            if not stable: reasons.append('NO_STABLE_TAGS')
            src=[e.canonical() for e in sorted(grp,key=lambda x:x.experience_id)]
            md=_digest(src)
            mid='PM-'+_digest({'procedure':proc,'source':md})[:16]
            if reasons:
                rejected.append({'procedure':list(proc),'support':len(grp),'domains':domains,'mean_score':mean,'failure_rate':fr,'reasons':reasons,'source_digest':md})
            else:
                memories.append(ProceduralMemory(mid,tuple(sorted(stable)),proc,len(grp),tuple(domains),mean,fr,md))
        return {
          'status':'CONSOLIDATED' if memories else 'NO_TRANSFERABLE_MEMORY',
          'memories':memories,'rejected':rejected,'memory_count':len(memories),'group_count':len(groups),
          'consolidation_digest':_digest({'memories':[m.canonical() for m in memories],'rejected':rejected}),
        }

    def retrieve(self, memories:Iterable[ProceduralMemory], query_tags:Sequence[str], *, target_domain:str='', k:int=3)->dict[str,Any]:
        q=set(map(str,query_tags)); rows=[]
        for m in memories:
            tags=set(map(str,m.stable_tags)); sim=_jaccard(q,tags)
            cross=1.0 if target_domain and target_domain not in set(m.support_domains) else 0.0
            reliability=max(0.0,min(1.0,float(m.mean_score)*(1.0-float(m.failure_rate))))
            # Semantic overlap dominates. Reliability protects hard cases; cross-domain
            # support is a small tie-break rather than a license to force transfer.
            utility=.72*sim+.23*reliability+.05*cross
            rows.append((utility,sim,reliability,m.memory_id,m))
        rows.sort(key=lambda r:(-r[0],-r[1],-r[2],r[3]))
        chosen=rows[:max(0,int(k))]
        return {'status':'RETRIEVED' if chosen else 'NO_MEMORY','memory_ids':[r[3] for r in chosen],
                'rows':[{'memory_id':r[3],'utility':r[0],'similarity':r[1],'reliability':r[2],'procedure':list(r[4].procedure),'stable_tags':list(r[4].stable_tags)} for r in chosen]}


def naive_trajectory_retrieve(experiences:Iterable[TransferExperience], query_tags:Sequence[str])->TransferExperience|None:
    q=set(map(str,query_tags)); rows=[]
    for e in experiences:
        sim=_jaccard(q,set(map(str,e.tags)))
        # Common naive behavior: similarity dominates and recency/id resolves ties.
        rows.append((sim,str(e.experience_id),e))
    return max(rows,key=lambda r:(r[0],r[1]))[-1] if rows else None

__all__=['TransferExperience','ProceduralMemory','TransferMemoryRuntime','naive_trajectory_retrieve','NATIVE_PROVENANCE']
