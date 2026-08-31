from __future__ import annotations
from dataclasses import dataclass
from itertools import combinations, product
import hashlib, json, math

def canon(o):
    return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)

def digest(o):
    return hashlib.sha256(canon(o).encode()).hexdigest()

def _numeric_keys(rows):
    keys=set()
    for x,_ in rows:
        for k,v in x.items():
            if isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(float(v)):
                keys.add(k)
    return sorted(keys)

@dataclass
class LinearThresholdModel:
    features:list
    weights:list
    threshold:float
    positive_if_ge:bool
    positive_label:object
    negative_label:object
    training_score:float
    def predict(self,x):
        try:s=sum(float(x[f])*w for f,w in zip(self.features,self.weights))
        except Exception:return self.negative_label
        pos=s>=self.threshold if self.positive_if_ge else s<self.threshold
        return self.positive_label if pos else self.negative_label
    def canonical(self):
        return {
          'kind':'BOUNDED_LINEAR_THRESHOLD','features':self.features,'weights':self.weights,
          'threshold':self.threshold,'positive_if_ge':self.positive_if_ge,
          'positive_label':self.positive_label,'negative_label':self.negative_label,
          'training_score':self.training_score,
        }

class BoundedLinearThresholdLearner:
    MAX_FEATURES=3
    WEIGHTS=(-2.0,-1.0,-0.5,0.5,1.0,2.0)
    @classmethod
    def fit(cls,rows,positive_label,negative_label):
        keys=_numeric_keys(rows)
        best=None
        y=[yy==positive_label for _,yy in rows]
        for width in range(1,min(cls.MAX_FEATURES,len(keys))+1):
            for fs in combinations(keys,width):
                for ws in product(cls.WEIGHTS,repeat=width):
                    scores=[]
                    valid=True
                    for x,_ in rows:
                        try:s=sum(float(x[f])*w for f,w in zip(fs,ws))
                        except Exception:valid=False;break
                        scores.append(s)
                    if not valid:continue
                    pairs=sorted(zip(scores,y),key=lambda z:z[0])
                    if not pairs:continue
                    # Prefix scan: O(n log n) per projection instead of rescoring every cut.
                    total_pos=sum(1 for _,yy in pairs if yy); total_neg=len(pairs)-total_pos
                    left_pos=left_neg=0
                    groups=[]
                    j=0
                    while j<len(pairs):
                        s0=pairs[j][0];gp=gn=0
                        while j<len(pairs) and pairs[j][0]==s0:
                            if pairs[j][1]:gp+=1
                            else:gn+=1
                            j+=1
                        groups.append((s0,gp,gn))
                    # threshold before first group
                    candidates=[(groups[0][0]-1e-9,0,0)]
                    lp=ln=0
                    for gi,(sv,gp,gn) in enumerate(groups):
                        lp+=gp;ln+=gn
                        if gi+1<len(groups):
                            t=(sv+groups[gi+1][0])/2
                        else:t=sv+1e-9
                        candidates.append((t,lp,ln))
                    for t,lp,ln in candidates:
                        # GE => positive on right; LT => positive on left.
                        ok_ge=(total_pos-lp)+ln
                        ok_lt=lp+(total_neg-ln)
                        for ge,ok in ((True,ok_ge),(False,ok_lt)):
                            acc=ok/len(rows)
                            cand=(acc,-width,tuple(fs),tuple(ws),t,ge)
                            if best is None or cand>best[0]:
                                best=(cand,LinearThresholdModel(list(fs),list(ws),t,ge,positive_label,negative_label,acc))
        if best is None:raise RuntimeError('NO_LINEAR_THRESHOLD_MODEL')
        return best[1]

@dataclass
class NumericClause:
    predicates:list
    def match(self,x):
        for p in self.predicates:
            try:v=float(x[p['field']])
            except Exception:return False
            if p['op']=='LT':
                if not v<p['threshold']:return False
            else:
                if not v>=p['threshold']:return False
        return True
    def canonical(self):return self.predicates

@dataclass
class DNFModel:
    clauses:list
    positive_label:object
    negative_label:object
    training_score:float
    def predict(self,x):
        return self.positive_label if any(c.match(x) for c in self.clauses) else self.negative_label
    def canonical(self):
        return {'kind':'BOUNDED_NUMERIC_DNF','clauses':[c.canonical() for c in self.clauses],
          'positive_label':self.positive_label,'negative_label':self.negative_label,'training_score':self.training_score}

class BoundedNumericDNFLearner:
    MAX_THRESHOLDS_PER_FEATURE=14
    MAX_CLAUSE_WIDTH=3
    MAX_CLAUSES=3
    MAX_PREDICATES_FOR_CONJUNCTION=16
    @classmethod
    def _predicates(cls,rows):
        keys=_numeric_keys(rows); out=[]
        for k in keys:
            vals=sorted(set(float(x[k]) for x,_ in rows if k in x))
            if len(vals)<2:continue
            label_by={}
            for x,y in rows:
                if k in x: label_by.setdefault(float(x[k]),set()).add(y)
            mids=[]
            for a,b in zip(vals,vals[1:]):
                la=label_by.get(a,set()); lb=label_by.get(b,set())
                if la!=lb or len(la)>1 or len(lb)>1:
                    mids.append((a+b)/2)
            if not mids:mids=[(a+b)/2 for a,b in zip(vals,vals[1:])]
            if len(mids)>cls.MAX_THRESHOLDS_PER_FEATURE:
                idx=[round(i*(len(mids)-1)/(cls.MAX_THRESHOLDS_PER_FEATURE-1)) for i in range(cls.MAX_THRESHOLDS_PER_FEATURE)]
                mids=[mids[i] for i in sorted(set(idx))]
            for t in mids:
                out.append({'field':k,'op':'LT','threshold':t})
                out.append({'field':k,'op':'GE','threshold':t})
        return out
    @classmethod
    def fit(cls,rows,positive_label,negative_label):
        preds=cls._predicates(rows)
        pos_idx={i for i,(_,y) in enumerate(rows) if y==positive_label}
        neg_idx=set(range(len(rows)))-pos_idx
        clauses=[]
        uncovered=set(pos_idx)
        # Generate only perfect-precision clauses; greedily cover positive counterexamples.
        # Rank atomic predicates by positive enrichment so width-3 search stays bounded.
        ranked=[]
        for j,p in enumerate(preds):
            cc=NumericClause([p])
            cov={i for i,(x,_) in enumerate(rows) if cc.match(x)}
            tp=len(cov&pos_idx); fp=len(cov&neg_idx)
            precision=tp/max(1,tp+fp); recall=tp/max(1,len(pos_idx))
            ranked.append((precision*0.7+recall*0.3,tp,-fp,j))
        ranked.sort(reverse=True)
        selected=sorted(z[3] for z in ranked[:cls.MAX_PREDICATES_FOR_CONJUNCTION])
        candidates=[]
        for width in range(1,cls.MAX_CLAUSE_WIDTH+1):
            for inds in combinations(selected,width):
                ps=[preds[i] for i in inds]
                # avoid same field contradictory duplicates except useful bounded intervals.
                c=NumericClause(ps)
                covered={i for i,(x,_) in enumerate(rows) if c.match(x)}
                if not covered or covered & neg_idx:continue
                support=len(covered & pos_idx)
                if support:
                    candidates.append((support,-width,canon(ps),c,covered))
        candidates.sort(reverse=True,key=lambda z:(z[0],z[1],z[2]))
        while uncovered and len(clauses)<cls.MAX_CLAUSES:
            best=None
            for item in candidates:
                gain=len(item[4]&uncovered)
                cand=(gain,item[0],item[1],item[2])
                if gain and (best is None or cand>best[0]):best=(cand,item)
            if best is None:break
            clauses.append(best[1][3]); uncovered-=best[1][4]
        model=DNFModel(clauses,positive_label,negative_label,0.0)
        model.training_score=sum(model.predict(x)==y for x,y in rows)/len(rows)
        return model

class PairedFieldMapperLearner:
    @staticmethod
    def fit(paired_examples,canonical_fields):
        if not paired_examples:raise RuntimeError('NO_MAPPING_EXAMPLES')
        aliases=sorted(set().union(*(set(a) for a,_ in paired_examples)))
        scores={}
        for c in canonical_fields:
            for a in aliases:
                good=0; total=0
                for alias,canonical in paired_examples:
                    if a in alias and c in canonical:
                        total+=1
                        av,cv=alias[a],canonical[c]
                        if isinstance(av,(int,float)) and isinstance(cv,(int,float)):
                            good+=abs(float(av)-float(cv))<=1e-12
                        else:good+=av==cv
                scores[(c,a)]=good/total if total else 0.0
        mapping={}; used=set()
        for c in canonical_fields:
            opts=sorted(((scores[(c,a)],a) for a in aliases if a not in used),reverse=True)
            if not opts or opts[0][0]<0.999:
                raise RuntimeError(f'UNRESOLVED_MAPPING:{c}')
            mapping[c]=opts[0][1]; used.add(opts[0][1])
        return LearnedFieldMapper(mapping)
@dataclass
class LearnedFieldMapper:
    mapping:dict
    def transform(self,x):
        out={}
        for canonical,alias in self.mapping.items():
            if alias not in x:raise KeyError(alias)
            out[canonical]=x[alias]
        return out
    def canonical(self):return {'kind':'PAIRED_CORRELATION_FIELD_MAPPER','mapping':self.mapping}


def predict_linear_spec(spec,x):
    try:s=sum(float(x[f])*float(w) for f,w in zip(spec['features'],spec['weights']))
    except Exception:return spec['negative_label']
    pos=s>=float(spec['threshold']) if spec['positive_if_ge'] else s<float(spec['threshold'])
    return spec['positive_label'] if pos else spec['negative_label']

def predict_dnf_spec(spec,x):
    for clause in spec['clauses']:
        ok=True
        for p in clause:
            try:v=float(x[p['field']])
            except Exception:ok=False;break
            if p['op']=='LT':
                if not v<float(p['threshold']):ok=False;break
            else:
                if not v>=float(p['threshold']):ok=False;break
        if ok:return spec['positive_label']
    return spec['negative_label']
