from __future__ import annotations
from dataclasses import dataclass
from itertools import combinations
from collections import Counter,defaultdict
import hashlib,json

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()

@dataclass(frozen=True)
class RouterAtom:
    field:str
    value:object
    def match(self,x):return self.field in x and x[self.field]==self.value
    def canonical(self):return {'op':'EQ','field':self.field,'value':self.value}

@dataclass
class RouterClause:
    atoms:list[RouterAtom]
    output:str
    support:int
    confidence:float
    def match(self,x):return all(a.match(x) for a in self.atoms)
    def canonical(self):return {'atoms':[a.canonical() for a in self.atoms],'output':self.output,'support':self.support,'confidence':self.confidence}

@dataclass
class CapabilityRouterProgram:
    clauses:list[RouterClause]
    fallback_output:str
    source_digest:str
    def execute(self,x,ablated=False):
        if ablated:return self.fallback_output
        for c in self.clauses:
            if c.match(x):return c.output
        return self.fallback_output
    def canonical(self):
        d={'schema':'yado.capability_router_program.v1','clauses':[c.canonical() for c in self.clauses],
           'fallback_output':self.fallback_output,'source_digest':self.source_digest}
        d['digest']=digest(d);return d

class BoundedCapabilityRouterLearnerV1:
    MAX_FIELDS=16
    MAX_WIDTH=4
    MAX_ATOMS=32
    MAX_CLAUSES=16
    MIN_TRAIN_PRECISION=.995
    MIN_VALIDATION_PRECISION=.98

    @classmethod
    def synthesize(cls,cases,validation_cases,fallback_output,min_support=5):
        if not cases or not validation_cases:raise ValueError('TRAIN_AND_VALIDATION_REQUIRED')
        labels=set(e['expected'] for e in cases)
        if fallback_output not in labels:raise ValueError('FALLBACK_NOT_OBSERVED')
        fields=sorted(set().union(*(set(e['input']) for e in cases)))[:cls.MAX_FIELDS]
        atoms=[]
        for f in fields:
            vals=[]
            for e in cases:
                v=e['input'].get(f)
                if isinstance(v,(str,bool,int,float)) and v not in vals:vals.append(v)
            # Router descriptors are categorical; suppress high-cardinality noise.
            if 1 < len(vals) <= 8:
                for v in vals:atoms.append(RouterAtom(f,v))
        atoms=atoms[:cls.MAX_ATOMS]

        candidates=defaultdict(list)
        min_val_support=max(3,int(len(validation_cases)*.01))
        for width in range(1,cls.MAX_WIDTH+1):
            for combo in combinations(atoms,width):
                fs=[a.field for a in combo]
                if len(fs)!=len(set(fs)):continue
                covered=[i for i,e in enumerate(cases) if all(a.match(e['input']) for a in combo)]
                if len(covered)<min_support:continue
                cnt=Counter(cases[i]['expected'] for i in covered)
                out,n=cnt.most_common(1)[0]
                if out==fallback_output:continue
                conf=n/len(covered)
                if conf<cls.MIN_TRAIN_PRECISION:continue
                vm=[e for e in validation_cases if all(a.match(e['input']) for a in combo)]
                if len(vm)<min_val_support:continue
                vconf=sum(e['expected']==out for e in vm)/len(vm)
                if vconf<cls.MIN_VALIDATION_PRECISION:continue
                good={i for i in covered if cases[i]['expected']==out}
                candidates[out].append((len(good),len(vm),vconf,-width,canon([a.canonical() for a in combo]),combo,good,conf))

        clauses=[]
        for out in sorted(labels-{fallback_output}):
            positives={i for i,e in enumerate(cases) if e['expected']==out}
            uncovered=set(positives)
            cands=sorted(candidates.get(out,[]),reverse=True,key=lambda z:(z[2],z[1],z[0],z[3],z[4]))
            while uncovered and len(clauses)<cls.MAX_CLAUSES:
                best=None
                for z in cands:
                    gain=len(z[6]&uncovered)
                    if gain<=0:continue
                    key=(gain,z[2],z[1],z[0],z[3],z[4])
                    if best is None or key>best[0]:best=(key,z)
                if best is None:break
                z=best[1];clauses.append(RouterClause(list(z[5]),out,z[0],z[7]));uncovered-=z[6]

        # Specific guarded routes first, broad emergency/priority routes last.
        clauses.sort(key=lambda c:(-len(c.atoms),-c.support,c.output))
        return CapabilityRouterProgram(clauses,fallback_output,digest(cases))

def router_acc(program,cases,ablated=False):
    return sum(program.execute(e['input'],ablated=ablated)==e['expected'] for e in cases)/len(cases)
