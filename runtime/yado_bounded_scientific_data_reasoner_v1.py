from __future__ import annotations
import math

class BoundedScientificDataReasonerV1:
    COMPONENT_ID="ALG-G2-BOUNDED-SCIENTIFIC-DATA-REASONER-V1"
    MISSING={"",None,"NA","NaN","nan","null","None"}

    @classmethod
    def _float(cls,v):
        if v in cls.MISSING:return None
        try:
            x=float(v)
            return x if math.isfinite(x) else None
        except (TypeError,ValueError):return None

    @classmethod
    def infer_schema(cls,rows):
        if not rows:return {"columns":[],"numeric":[],"categorical":[]}
        cols=list(rows[0].keys());numeric=[];categorical=[]
        for c in cols:
            vals=[r.get(c) for r in rows if r.get(c) not in cls.MISSING]
            parsed=[cls._float(v) for v in vals]
            if len(vals)>=2 and all(v is not None for v in parsed):numeric.append(c)
            else:categorical.append(c)
        return {"columns":cols,"numeric":numeric,"categorical":categorical}

    @classmethod
    def numeric_summary(cls,rows,col):
        vals=[cls._float(r.get(col)) for r in rows];vals=[v for v in vals if v is not None]
        if not vals:return None
        n=len(vals);mean=sum(vals)/n
        var=sum((v-mean)**2 for v in vals)/(n-1) if n>1 else 0.0
        return {"count":n,"mean":mean,"stdev":math.sqrt(var),"min":min(vals),"max":max(vals)}

    @classmethod
    def pearson(cls,rows,x,y):
        pairs=[]
        for r in rows:
            a=cls._float(r.get(x));b=cls._float(r.get(y))
            if a is not None and b is not None:pairs.append((a,b))
        if len(pairs)<3:return None
        ax=sum(a for a,_ in pairs)/len(pairs);by=sum(b for _,b in pairs)/len(pairs)
        num=sum((a-ax)*(b-by) for a,b in pairs)
        da=sum((a-ax)**2 for a,_ in pairs);db=sum((b-by)**2 for _,b in pairs)
        if da<=0 or db<=0:return None
        return num/math.sqrt(da*db)

    @classmethod
    def linear_fit(cls,rows,x,y):
        pairs=[]
        for r in rows:
            a=cls._float(r.get(x));b=cls._float(r.get(y))
            if a is not None and b is not None:pairs.append((a,b))
        if len(pairs)<3:return None
        mx=sum(a for a,_ in pairs)/len(pairs);my=sum(b for _,b in pairs)/len(pairs)
        den=sum((a-mx)**2 for a,_ in pairs)
        if den<=0:return None
        slope=sum((a-mx)*(b-my) for a,b in pairs)/den
        intercept=my-slope*mx
        corr=cls.pearson(rows,x,y)
        return {"n":len(pairs),"slope":slope,"intercept":intercept,"r2":None if corr is None else corr*corr}

    @classmethod
    def group_means(cls,rows,category,numeric,max_groups=12):
        groups={}
        for r in rows:
            g=r.get(category);v=cls._float(r.get(numeric))
            if g in cls.MISSING or v is None:continue
            groups.setdefault(str(g),[]).append(v)
        if not groups or len(groups)>max_groups:return None
        return {g:{"count":len(vs),"mean":sum(vs)/len(vs)} for g,vs in sorted(groups.items())}

    @classmethod
    def analyze(cls,rows,enable=("summary","correlation","group","linear")):
        schema=cls.infer_schema(rows);out={"row_count":len(rows),"schema":schema}
        if "summary" in enable:
            out["numeric_summary"]={c:cls.numeric_summary(rows,c) for c in schema["numeric"]}
        if "correlation" in enable:
            corr={}
            nums=schema["numeric"]
            for i,x in enumerate(nums):
                for y in nums[i+1:]:
                    v=cls.pearson(rows,x,y)
                    if v is not None:corr[f"{x}|{y}"]=v
            out["correlations"]=corr
            out["strongest_numeric_pair"]=None
            if corr:
                key=max(corr,key=lambda k:(abs(corr[k]),k))
                out["strongest_numeric_pair"]={"pair":key.split("|"),"correlation":corr[key]}
        if "group" in enable:
            gm={}
            for cat in schema["categorical"]:
                for num in schema["numeric"]:
                    v=cls.group_means(rows,cat,num)
                    if v is not None and 2<=len(v)<=12:gm[f"{cat}|{num}"]=v
            out["group_means"]=gm
        if "linear" in enable:
            fits={}
            nums=schema["numeric"]
            for i,x in enumerate(nums):
                for y in nums[i+1:]:
                    f=cls.linear_fit(rows,x,y)
                    if f is not None:fits[f"{x}|{y}"]=f
            out["linear_fits"]=fits
        return out

    @classmethod
    def evaluate_hypothesis(cls,rows,spec):
        kind=spec.get("type")
        if kind=="CORRELATION_ABS_AT_LEAST":
            obs=cls.pearson(rows,spec["x"],spec["y"])
            return {"type":kind,"observed":obs,"threshold":float(spec["threshold"]),
                    "supported":obs is not None and abs(obs)>=float(spec["threshold"])}
        if kind=="GROUP_MEAN_ORDER":
            gm=cls.group_means(rows,spec["category"],spec["numeric"])
            lo=str(spec["lower_group"]);hi=str(spec["higher_group"])
            ok=gm is not None and lo in gm and hi in gm
            return {"type":kind,"group_means":gm,"supported":bool(ok and gm[lo]["mean"]<gm[hi]["mean"])}
        if kind=="LINEAR_R2_AT_LEAST":
            fit=cls.linear_fit(rows,spec["x"],spec["y"])
            thr=float(spec["threshold"])
            return {"type":kind,"fit":fit,"threshold":thr,
                    "supported":fit is not None and fit["r2"] is not None and fit["r2"]>=thr}
        raise ValueError("UNKNOWN_HYPOTHESIS_TYPE")

__all__=["BoundedScientificDataReasonerV1"]
