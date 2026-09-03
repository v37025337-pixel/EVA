from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple
import hashlib, json, math


def canonical_json(x: Any) -> str:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest_obj(x: Any) -> str:
    return hashlib.sha256(canonical_json(x).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EvolutionVariant:
    variant_id: str
    parent_id: Optional[str]
    lineage_id: str
    artifact_digest: str
    task_scores: Mapping[str, float] = field(default_factory=dict)
    constraints: Mapping[str, bool] = field(default_factory=dict)
    traits: Mapping[str, float] = field(default_factory=dict)
    failure_tags: Sequence[str] = field(default_factory=tuple)
    status: str = "EVALUATED"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def canonical(self) -> Dict[str, Any]:
        d=asdict(self)
        d["task_scores"]={str(k):float(v) for k,v in sorted(self.task_scores.items())}
        d["constraints"]={str(k):bool(v) for k,v in sorted(self.constraints.items())}
        d["traits"]={str(k):float(v) for k,v in sorted(self.traits.items())}
        d["failure_tags"]=sorted(map(str,self.failure_tags))
        d["metadata"]={str(k):self.metadata[k] for k in sorted(self.metadata)}
        return d


class EvolutionArchiveRuntime:
    """Bounded archive/lineage selector derived from external research principles.

    The runtime does not edit code or execute third-party artifacts. It stores evaluated
    variants, enforces hard admission constraints, preserves stepping stones, and emits
    a bounded operation suggestion (CLONAL, REACTION_NORM, CROSS_LINEAGE) from recorded
    task evidence. All mutation/execution remains outside this class and must pass the
    caller's existing verification/rollback gates.
    """
    REQUIRED_CONSTRAINTS=("regression_pass","state_integrity","rollback_available")

    def __init__(self, variants: Iterable[EvolutionVariant]=()):
        self._variants: Dict[str,EvolutionVariant]={}
        for v in variants:
            self.add(v)

    def add(self,v:EvolutionVariant)->None:
        if not v.variant_id or not v.lineage_id or not v.artifact_digest:
            raise ValueError("variant_id, lineage_id and artifact_digest are required")
        if v.variant_id in self._variants and self._variants[v.variant_id].canonical()!=v.canonical():
            raise ValueError("variant_id collision with different content")
        self._variants[v.variant_id]=v

    def variants(self)->List[EvolutionVariant]:
        return [self._variants[k] for k in sorted(self._variants)]

    def admitted(self,v:EvolutionVariant)->bool:
        return all(bool(v.constraints.get(k,False)) for k in self.REQUIRED_CONSTRAINTS)

    def archive_digest(self)->str:
        return digest_obj([v.canonical() for v in self.variants()])

    @staticmethod
    def _mean(xs:Sequence[float])->float:
        return sum(xs)/len(xs) if xs else 0.0

    def reaction_norm(self,variant_id:str, failure_threshold:float=0.5)->Dict[str,Any]:
        v=self._variants[variant_id]
        weak=sorted(k for k,s in v.task_scores.items() if float(s)<failure_threshold)
        recurring=sorted(set(weak)&set(map(str,v.failure_tags)))
        return {
            "variant_id":variant_id,
            "weak_tasks":weak,
            "recurring_failure_tags":recurring,
            "multi_task_weakness":len(weak)>=2,
            "mean_task_score":self._mean([float(x) for x in v.task_scores.values()]),
        }

    def cross_lineage_reference(self,target_variant_id:str,target_task:str)->Optional[Dict[str,Any]]:
        t=self._variants[target_variant_id]
        base=float(t.task_scores.get(target_task,0.0))
        rows=[]
        for v in self.variants():
            if v.lineage_id==t.lineage_id or not self.admitted(v):
                continue
            score=float(v.task_scores.get(target_task,0.0))
            if score<=base: continue
            mean=self._mean([float(x) for x in v.task_scores.values()])
            rows.append((score,mean,-len(v.failure_tags),v.variant_id,v))
        if not rows:return None
        _,_,_,_,v=max(rows)
        return {"variant_id":v.variant_id,"lineage_id":v.lineage_id,"target_task":target_task,
                "target_score":float(v.task_scores.get(target_task,0.0)),"target_base":base}

    def select_parent(self,target_task:str,trait_preferences:Optional[Mapping[str,float]]=None)->Dict[str,Any]:
        prefs={str(k):float(v) for k,v in (trait_preferences or {}).items()}
        rows=[]
        for v in self.variants():
            if not self.admitted(v):continue
            target=float(v.task_scores.get(target_task,0.0))
            mean=self._mean([float(x) for x in v.task_scores.values()])
            trait=sum(float(v.traits.get(k,0.0))*w for k,w in prefs.items())
            # target evidence dominates; mean guards against narrow overfit; traits are bounded tie-break evidence.
            utility=0.70*target+0.25*mean+0.05*trait
            rows.append((utility,target,mean,trait,-len(v.failure_tags),v.variant_id,v))
        if not rows:return {"action":"SEEK_MORE_EVIDENCE","reason":"NO_ADMITTED_VARIANTS"}
        row=max(rows)
        v=row[-1]
        return {"action":"SELECT_PARENT","variant_id":v.variant_id,"lineage_id":v.lineage_id,
                "utility":row[0],"target_score":row[1],"mean_score":row[2],"trait_score":row[3],
                "archive_digest":self.archive_digest()}

    def propose_operation(self,target_variant_id:str,target_task:str)->Dict[str,Any]:
        rn=self.reaction_norm(target_variant_id)
        if rn["multi_task_weakness"]:
            return {"operation":"REACTION_NORM","variant_id":target_variant_id,
                    "evidence":{"weak_tasks":rn["weak_tasks"],"mean_task_score":rn["mean_task_score"]}}
        ref=self.cross_lineage_reference(target_variant_id,target_task)
        if ref:
            return {"operation":"CROSS_LINEAGE","variant_id":target_variant_id,"reference":ref}
        return {"operation":"CLONAL","variant_id":target_variant_id,"target_task":target_task}

    def pareto_stepping_stones(self, objectives:Sequence[Tuple[str,str]])->List[str]:
        """Return non-dominated admitted variants. Objective kind is task:<name> or trait:<name>, direction max/min."""
        vs=[v for v in self.variants() if self.admitted(v)]
        def val(v:EvolutionVariant,key:str)->float:
            kind,name=key.split(':',1)
            return float(v.task_scores.get(name,0.0) if kind=='task' else v.traits.get(name,0.0))
        keep=[]
        for a in vs:
            dominated=False
            for b in vs:
                if a.variant_id==b.variant_id:continue
                weak=True;strict=False
                for key,direction in objectives:
                    av,bv=val(a,key),val(b,key)
                    if direction=='max':
                        weak &= bv>=av; strict |= bv>av
                    elif direction=='min':
                        weak &= bv<=av; strict |= bv<av
                    else: raise ValueError('direction must be max or min')
                if weak and strict:
                    dominated=True;break
            if not dominated:keep.append(a.variant_id)
        return sorted(keep)

    def snapshot(self)->Dict[str,Any]:
        return {"schema":"yado.evolution_archive.runtime.v1","variant_count":len(self._variants),
                "admitted_count":sum(self.admitted(v) for v in self._variants.values()),
                "archive_digest":self.archive_digest(),"variants":[v.canonical() for v in self.variants()]}

__all__=['EvolutionVariant','EvolutionArchiveRuntime','canonical_json','digest_obj']
