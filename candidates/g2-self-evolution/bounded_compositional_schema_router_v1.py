from __future__ import annotations
from collections import Counter,defaultdict

class BoundedCompositionalSchemaRouterV1:
    COMPONENT_ID="ALG-G2-BOUNDED-COMPOSITIONAL-SCHEMA-ROUTER-V1"
    MAX_FIELDS=16
    MAX_OUTPUTS=8
    MAX_TRIGGERS_PER_OUTPUT=8
    MAX_ALIGNMENT_ROWS=64
    MIN_TRIGGER_PRECISION=.995
    MIN_TRIGGER_SUPPORT=4

    @staticmethod
    def _outputs(y):
        if isinstance(y,str):return {y}
        if isinstance(y,(list,tuple,set)):return {str(z) for z in y}
        raise ValueError("UNSUPPORTED_OUTPUT")

    @classmethod
    def fit(cls,cases,fallback_output):
        if not cases:raise ValueError("EMPTY_CASES")
        fields=sorted(set().union(*(set(z["input"]) for z in cases)))[:cls.MAX_FIELDS]
        outputs=sorted(set().union(*(cls._outputs(z["expected"]) for z in cases)))[:cls.MAX_OUTPUTS]
        if fallback_output not in outputs:outputs=[fallback_output]+outputs
        triggers=defaultdict(list)
        for f in fields:
            values=[]
            for z in cases:
                v=z["input"].get(f)
                if isinstance(v,(bool,str,int,float)) and v not in values:values.append(v)
            if len(values)>8:continue
            for v in values:
                covered=[z for z in cases if z["input"].get(f)==v]
                if len(covered)<cls.MIN_TRIGGER_SUPPORT:continue
                for out in outputs:
                    if out==fallback_output:continue
                    yes=sum(out in cls._outputs(z["expected"]) for z in covered)
                    precision=yes/len(covered)
                    if precision>=cls.MIN_TRIGGER_PRECISION:
                        triggers[out].append((len(covered),precision,f,v))
        clean={}
        for out in outputs:
            if out==fallback_output:continue
            xs=sorted(triggers.get(out,[]),key=lambda q:(-q[1],-q[0],q[2],str(q[3])))[:cls.MAX_TRIGGERS_PER_OUTPUT]
            clean[out]=[{"field":f,"value":v,"support":n,"precision":p} for n,p,f,v in xs]
        return {"kind":"COMPOSITIONAL_TRIGGER_ROUTER","fields":fields,"outputs":outputs,"fallback_output":fallback_output,"triggers":clean}

    @classmethod
    def route(cls,model,x):
        selected=[]
        for out in model["outputs"]:
            if out==model["fallback_output"]:continue
            rules=model["triggers"].get(out,[])
            if any(r["field"] in x and x[r["field"]]==r["value"] for r in rules):
                selected.append(out)
        return tuple(sorted(selected)) if selected else (model["fallback_output"],)

    @classmethod
    def fit_schema_alignment(cls,reference_rows,alias_rows):
        refs=list(reference_rows)[:cls.MAX_ALIGNMENT_ROWS];als=list(alias_rows)[:cls.MAX_ALIGNMENT_ROWS]
        if not refs or len(refs)!=len(als):return {"kind":"WITHHOLD","reason":"PAIRED_ALIGNMENT_REQUIRED","map":{}}
        rf=sorted(set().union(*(set(x) for x in refs)))[:cls.MAX_FIELDS]
        af=sorted(set().union(*(set(x) for x in als)))[:cls.MAX_FIELDS]
        rs={f:tuple(x.get(f,None) for x in refs) for f in rf}
        ass={f:tuple(x.get(f,None) for x in als) for f in af}
        amap={}
        used=set()
        for a in af:
            matches=[r for r in rf if ass[a]==rs[r] and r not in used]
            if len(matches)!=1:
                return {"kind":"WITHHOLD","reason":"AMBIGUOUS_OR_UNIDENTIFIED_SCHEMA_ROLE","map":{}}
            amap[a]=matches[0];used.add(matches[0])
        return {"kind":"EXACT_PAIRED_SCHEMA_ALIGNMENT","map":amap}

    @staticmethod
    def apply_schema_alignment(alignment,x):
        if alignment.get("kind")=="WITHHOLD":raise ValueError("AMBIGUOUS_SCHEMA")
        return {alignment["map"].get(k,k):v for k,v in x.items()}

    @classmethod
    def route_aligned(cls,model,alignment,x):
        return cls.route(model,cls.apply_schema_alignment(alignment,x))
