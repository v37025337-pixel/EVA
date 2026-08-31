from __future__ import annotations
from dataclasses import dataclass
from itertools import combinations
from collections import Counter,defaultdict
import hashlib,json

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()

@dataclass(frozen=True)
class Atom:
    op:str
    field:str
    value:object=None
    other_field:str|None=None
    def match(self,x):
        if self.op=='EQ': return self.field in x and x[self.field]==self.value
        if self.op=='FIELD_EQ': return self.field in x and self.other_field in x and x[self.field]==x[self.other_field]
        if self.op=='FIELD_NEQ': return self.field in x and self.other_field in x and x[self.field]!=x[self.other_field]
        return False
    def canonical(self):
        d={'op':self.op,'field':self.field}
        if self.op=='EQ':d['value']=self.value
        else:d['other_field']=self.other_field
        return d

@dataclass
class Clause:
    atoms:list[Atom]
    output:object
    support:int
    confidence:float
    def match(self,x):return all(a.match(x) for a in self.atoms)
    def canonical(self):
        return {'atoms':[a.canonical() for a in self.atoms],'output':self.output,'support':self.support,'confidence':self.confidence}

@dataclass
class DNFPolicy:
    program_id:str
    target_capability:str
    target_organ:str
    clauses:list[Clause]
    default_output:object
    training_count:int
    source_digest:str
    status:str='SHADOW'
    def execute(self,x,ablated=False):
        if ablated:return self.default_output
        for c in self.clauses:
            if c.match(x):return c.output
        return self.default_output
    def canonical(self):
        d={'program_id':self.program_id,'target_capability':self.target_capability,'target_organ':self.target_organ,
           'clauses':[c.canonical() for c in self.clauses],'default_output':self.default_output,
           'training_count':self.training_count,'source_digest':self.source_digest,'status':self.status}
        d['digest']=digest(d)
        return d

class BoundedDNFRelationPolicyInducerV1:
    MAX_FIELDS=12
    MAX_VALUES_PER_FIELD=12
    MAX_CLAUSE_WIDTH=4
    MAX_ATOMS_FOR_COMBINATION=28
    MAX_CLAUSES=12
    MIN_PRECISION=0.995

    @classmethod
    def _atoms(cls,cases):
        fields=sorted(set().union(*(set(e['input']) for e in cases)))[:cls.MAX_FIELDS]
        atoms=[]
        distinct={}
        types={}
        for f in fields:
            vals=[]
            ts=set()
            for e in cases:
                if f not in e['input']: continue
                v=e['input'][f]
                if isinstance(v,(str,bool,int,float)):
                    ts.add(type(v))
                    if v not in vals: vals.append(v)
            distinct[f]=vals
            types[f]=ts
            # Low-cardinality fields are categorical attributes and can be tested literally.
            # High-cardinality fields are treated as identifiers: do not memorize their values.
            if 1 < len(vals) <= 6:
                for v in vals[:cls.MAX_VALUES_PER_FIELD]:
                    atoms.append(Atom('EQ',f,v))

        # Relations are admitted only between identifier-like fields of the same scalar type.
        # This blocks accidental boolean/enum equality such as identity_verified == mfa.
        for a,b in combinations(fields,2):
            if len(distinct.get(a,())) < 7 or len(distinct.get(b,())) < 7:
                continue
            if len(types.get(a,set()))!=1 or types.get(a)!=types.get(b):
                continue
            eq_support=sum(1 for e in cases if a in e['input'] and b in e['input'] and e['input'][a]==e['input'][b])
            neq_support=sum(1 for e in cases if a in e['input'] and b in e['input'] and e['input'][a]!=e['input'][b])
            if eq_support:
                atoms.append(Atom('FIELD_EQ',a,other_field=b))
            if neq_support:
                atoms.append(Atom('FIELD_NEQ',a,other_field=b))
        return atoms

    @classmethod
    def synthesize(cls,target_capability,target_organ,cases,min_support=3,max_clauses=None,validation_cases=None):
        if not cases:raise ValueError('EMPTY_CASES')
        max_clauses=min(max_clauses or cls.MAX_CLAUSES,cls.MAX_CLAUSES)
        labels=Counter(e['expected'] for e in cases)
        default=labels.most_common(1)[0][0]
        atoms=cls._atoms(cases)

        # Rank atoms by label purity/information-like utility, then bound conjunction search.
        ranked=[]
        global_freq={lab:n/len(cases) for lab,n in labels.items()}
        min_atom_support=max(min_support*2,int(len(cases)*0.03))
        for i,a in enumerate(atoms):
            covered=[e for e in cases if a.match(e['input'])]
            if len(covered)<min_atom_support:continue
            cnt=Counter(e['expected'] for e in covered)
            best_gain=-1.0
            best_precision=0.0
            for lab,nlab in cnt.items():
                if lab==default:continue
                precision=nlab/len(covered)
                gain=(precision-global_freq.get(lab,0.0))*(len(covered)**0.5)
                if gain>best_gain:
                    best_gain=gain;best_precision=precision
            ranked.append((best_gain,best_precision,len(covered),-i,a))
        ranked.sort(reverse=True,key=lambda z:(z[0],z[1],z[2],z[3]))

        # Counterexample correction: relational atoms are first-class search primitives.
        # Reserve a bounded part of the pool for FIELD_EQ/FIELD_NEQ so scalar EQ atoms
        # cannot crowd them out. Still rank relations by observed label gain; no field-pair
        # names are supplied by the host.
        rel=[z for z in ranked if z[4].op.startswith('FIELD_') and z[0]>0]
        scalar=[z for z in ranked if z[4].op=='EQ']
        relation_slots=min(12,len(rel),cls.MAX_ATOMS_FOR_COMBINATION//2) if rel else 0
        chosen=rel[:relation_slots]
        remaining=cls.MAX_ATOMS_FOR_COMBINATION-len(chosen)
        chosen+=scalar[:remaining]
        if len(chosen)<cls.MAX_ATOMS_FOR_COMBINATION:
            chosen_ids={id(z[4]) for z in chosen}
            chosen += [z for z in ranked if id(z[4]) not in chosen_ids][:cls.MAX_ATOMS_FOR_COMBINATION-len(chosen)]
        pool=[z[4] for z in chosen]

        candidates=defaultdict(list)
        n=len(cases)
        min_clause_support=max(min_support,int(n*0.015))
        for width in range(1,cls.MAX_CLAUSE_WIDTH+1):
            for combo in combinations(pool,width):
                # Skip duplicate EQ constraints on same field with different values.
                eq_fields=[a.field for a in combo if a.op=='EQ']
                if len(eq_fields)!=len(set(eq_fields)):continue
                covered=[idx for idx,e in enumerate(cases) if all(a.match(e['input']) for a in combo)]
                if len(covered)<min_clause_support:continue
                outcnt=Counter(cases[i]['expected'] for i in covered)
                out,count=outcnt.most_common(1)[0]
                if out==default:continue
                conf=count/len(covered)
                if conf<cls.MIN_PRECISION:continue
                good={i for i in covered if cases[i]['expected']==out}
                bad={i for i in covered if cases[i]['expected']!=out}
                if not good:continue

                val_precision=1.0
                val_support=0
                if validation_cases:
                    vm=[e for e in validation_cases if all(a.match(e['input']) for a in combo)]
                    val_support=len(vm)
                    min_val_support=max(2,int(len(validation_cases)*0.01))
                    if val_support<min_val_support:continue
                    val_precision=sum(e['expected']==out for e in vm)/val_support
                    if val_precision<0.98:continue

                candidates[out].append((
                    len(good),val_support,val_precision,-len(bad),-width,
                    canon([a.canonical() for a in combo]),combo,good,conf
                ))

        clauses=[]
        for out in sorted(candidates,key=lambda x:str(x)):
            positives={i for i,e in enumerate(cases) if e['expected']==out}
            uncovered=set(positives)
            cands=sorted(candidates[out],reverse=True,key=lambda z:(z[2],z[1],z[0],z[3],z[4],z[5]))
            while uncovered and len(clauses)<max_clauses:
                best=None
                for z in cands:
                    gain=len(z[7]&uncovered)
                    if gain<=0:continue
                    key=(gain,z[2],z[1],z[0],z[3],z[4],z[5])
                    if best is None or key>best[0]:best=(key,z)
                if best is None:break
                z=best[1]
                clauses.append(Clause(list(z[6]),out,z[0],z[8]))
                uncovered-=z[7]

        # Order more specific clauses first, then support.
        clauses.sort(key=lambda c:(-len(c.atoms),-c.support,str(c.output)))
        p=DNFPolicy(
          program_id='DNFR-'+digest({'target':target_capability,'cases':cases,'clauses':[c.canonical() for c in clauses]})[:12],
          target_capability=target_capability,target_organ=target_organ,clauses=clauses,
          default_output=default,training_count=n,source_digest=digest(cases)
        )
        return p

def program_acc(p,cases,ablated=False):
    if not cases:return 0.0
    return sum(p.execute(e['input'],ablated=ablated)==e['expected'] for e in cases)/len(cases)
