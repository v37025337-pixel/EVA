from __future__ import annotations
from itertools import combinations
from collections import defaultdict

class BudgetAdaptiveCompositionalSchemaRouterV2:
    COMPONENT_ID="ALG-G2-BUDGET-ADAPTIVE-COMPOSITIONAL-SCHEMA-ROUTER-V2"
    MAX_FIELD_CELLS=262144
    MAX_ALIGNMENT_CELLS=131072
    MAX_OUTPUTS=8
    MAX_TRIGGER_WIDTH=2
    MAX_TRIGGER_CANDIDATES=4096
    MAX_TRIGGERS_PER_OUTPUT=32
    MIN_TRIGGER_PRECISION=.995
    MIN_TRIGGER_SUPPORT=4

    @staticmethod
    def _outputs(y):
        if isinstance(y,str):return {y}
        if isinstance(y,(list,tuple,set)):return {str(z) for z in y}
        raise ValueError("UNSUPPORTED_OUTPUT")

    @classmethod
    def fit(cls,cases,fallback_output,max_trigger_width=None):
        if not cases:raise ValueError("EMPTY_CASES")
        fields=sorted(set().union(*(set(z["input"]) for z in cases)))
        if len(cases)*max(1,len(fields))>cls.MAX_FIELD_CELLS:
            return {"kind":"WITHHOLD","reason":"FIELD_WORK_BUDGET","fields":[],"outputs":[],"fallback_output":fallback_output,"triggers":{}}
        outputs=sorted(set().union(*(cls._outputs(z["expected"]) for z in cases)))
        if fallback_output not in outputs:outputs=[fallback_output]+outputs
        outputs=sorted(set(outputs))
        if len(outputs)>cls.MAX_OUTPUTS:
            return {"kind":"WITHHOLD","reason":"OUTPUT_BUDGET","fields":fields,"outputs":[],"fallback_output":fallback_output,"triggers":{}}
        atoms=[]
        for f in fields:
            vals=[]
            for z in cases:
                v=z["input"].get(f)
                if isinstance(v,(bool,str,int,float)) and v not in vals:vals.append(v)
            if 1 < len(vals) <= 8:
                for v in vals:atoms.append((f,v))
        width=min(cls.MAX_TRIGGER_WIDTH,int(max_trigger_width or cls.MAX_TRIGGER_WIDTH))
        combos=[(a,) for a in atoms]
        if width>=2:
            for a,b in combinations(atoms,2):
                if a[0]!=b[0]:combos.append((a,b))
        if len(combos)>cls.MAX_TRIGGER_CANDIDATES:
            return {"kind":"WITHHOLD","reason":"TRIGGER_CANDIDATE_BUDGET","fields":fields,"outputs":outputs,"fallback_output":fallback_output,"triggers":{}}
        triggers=defaultdict(list)
        for combo in combos:
            covered=[z for z in cases if all(a[0] in z["input"] and z["input"][a[0]]==a[1] for a in combo)]
            if len(covered)<cls.MIN_TRIGGER_SUPPORT:continue
            for out in outputs:
                if out==fallback_output:continue
                precision=sum(out in cls._outputs(z["expected"]) for z in covered)/len(covered)
                if precision>=cls.MIN_TRIGGER_PRECISION:
                    triggers[out].append({
                      "atoms":[{"field":a[0],"value":a[1]} for a in combo],
                      "support":len(covered),"precision":precision
                    })
        clean={}
        for out in outputs:
            if out==fallback_output:continue
            xs=triggers.get(out,[])
            xs=sorted(xs,key=lambda r:(-r["precision"],len(r["atoms"]),-r["support"],str(r["atoms"])))
            clean[out]=xs[:cls.MAX_TRIGGERS_PER_OUTPUT]
        return {"kind":"BUDGET_ADAPTIVE_COMPOSITIONAL_TRIGGER_ROUTER_V2","fields":fields,"outputs":outputs,
                "fallback_output":fallback_output,"triggers":clean,"candidate_count":len(combos)}

    @classmethod
    def route(cls,model,x):
        if model.get("kind")=="WITHHOLD":raise ValueError(model.get("reason","ROUTER_WITHHOLD"))
        selected=[]
        for out in model["outputs"]:
            if out==model["fallback_output"]:continue
            for rule in model["triggers"].get(out,[]):
                if all(a["field"] in x and x[a["field"]]==a["value"] for a in rule["atoms"]):
                    selected.append(out);break
        return tuple(sorted(selected)) if selected else (model["fallback_output"],)

    @classmethod
    def fit_schema_alignment(cls,reference_rows,alias_rows):
        refs=list(reference_rows);als=list(alias_rows)
        if not refs or len(refs)!=len(als):return {"kind":"WITHHOLD","reason":"PAIRED_ALIGNMENT_REQUIRED","map":{}}
        rf=sorted(set().union(*(set(x) for x in refs)));af=sorted(set().union(*(set(x) for x in als)))
        if len(refs)*max(1,len(rf)+len(af))>cls.MAX_ALIGNMENT_CELLS:
            return {"kind":"WITHHOLD","reason":"ALIGNMENT_WORK_BUDGET","map":{}}
        rs={f:tuple(x.get(f,None) for x in refs) for f in rf};ass={f:tuple(x.get(f,None) for x in als) for f in af}
        amap={};used=set()
        for a in af:
            matches=[r for r in rf if ass[a]==rs[r] and r not in used]
            if len(matches)!=1:return {"kind":"WITHHOLD","reason":"AMBIGUOUS_OR_UNIDENTIFIED_SCHEMA_ROLE","map":{}}
            amap[a]=matches[0];used.add(matches[0])
        return {"kind":"EXACT_PAIRED_SCHEMA_ALIGNMENT_V2","map":amap}

    @staticmethod
    def apply_schema_alignment(alignment,x):
        if alignment.get("kind")=="WITHHOLD":raise ValueError(alignment.get("reason","AMBIGUOUS_SCHEMA"))
        return {alignment["map"].get(k,k):v for k,v in x.items()}

    @classmethod
    def route_aligned(cls,model,alignment,x):
        return cls.route(model,cls.apply_schema_alignment(alignment,x))
