from __future__ import annotations
from pathlib import Path
import csv,hashlib,importlib.util,io,json,os,sys,urllib.request

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
AUDIT=REPO/'receipts'/'yado-unified-core-deep-self-audit-v1-run-33418891086.json'
CAND_DIR=REPO/'candidates'/'g2-self-evolution'
CAND_SRC=CAND_DIR/'bounded_scientific_data_reasoner_v1.py'
CAND_META=CAND_DIR/'bounded_scientific_data_reasoner_v1.json'
OUT=ROOT/'yado_science_data_native_self_evolution_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def fetch_csv(url):
    rq=urllib.request.Request(url,headers={'User-Agent':'YADO-Science-Evolution/1.0'})
    with urllib.request.urlopen(rq,timeout=20) as resp:data=resp.read()
    return data,list(csv.DictReader(io.StringIO(data.decode('utf-8'))))

head=load(HEAD);ledger=load(LEDGER);audit=load(AUDIT)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['REAL_SCIENCE_DATA_TRANSFER_NATIVE_EVOLUTION_V1']:raise RuntimeError('UNEXPECTED_FRONTIER')
if audit.get('self_selected_next_step')!='REAL_SCIENCE_DATA_TRANSFER_NATIVE_EVOLUTION_V1':raise RuntimeError('SCIENCE_NOT_SELF_SELECTED')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')

candidate_code=r'''from __future__ import annotations
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
'''
CAND_DIR.mkdir(parents=True,exist_ok=True);CAND_SRC.write_text(candidate_code,encoding='utf-8')

sp=importlib.util.spec_from_file_location('bounded_science_candidate',CAND_SRC)
mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod)
Reasoner=mod.BoundedScientificDataReasonerV1

iris_url='https://raw.githubusercontent.com/mwaskom/seaborn-data/master/iris.csv'
data,rows=fetch_csv(iris_url)
analysis=Reasoner.analyze(rows)
hyps=[
 Reasoner.evaluate_hypothesis(rows,{"type":"CORRELATION_ABS_AT_LEAST","x":"petal_length","y":"petal_width","threshold":0.95}),
 Reasoner.evaluate_hypothesis(rows,{"type":"GROUP_MEAN_ORDER","category":"species","numeric":"petal_length","lower_group":"setosa","higher_group":"virginica"}),
 Reasoner.evaluate_hypothesis(rows,{"type":"LINEAR_R2_AT_LEAST","x":"petal_length","y":"petal_width","threshold":0.90}),
]
checks={
 'live_public_dataset_loaded':len(rows)==150 and hashlib.sha256(data).hexdigest()=='9cc1c345c71bcc9b486b74cbf6063fa66f4bb5e0f603a4b3c3471ec2e5e8e355',
 'schema_inferred':set(analysis['schema']['numeric'])=={'sepal_length','sepal_width','petal_length','petal_width'} and 'species' in analysis['schema']['categorical'],
 'strongest_pair_correct':set((analysis.get('strongest_numeric_pair') or {}).get('pair',[]))=={'petal_length','petal_width'},
 'all_hypotheses_supported':all(x.get('supported') is True for x in hyps),
 'bounded_claim_surface':all(k in candidate_code for k in ['CORRELATION_ABS_AT_LEAST','GROUP_MEAN_ORDER','LINEAR_R2_AT_LEAST']),
 'no_network_inside_candidate':all(x not in candidate_code for x in ['urllib','requests','aiohttp','socket']),
 'canonical_head_immutable':ledger.get('current_head_digest')==head.get('canonical_head_digest'),
}
# Causal feature ablation: removing correlation analysis must remove strongest-pair output while preserving schema.
ablated=Reasoner.analyze(rows,enable=("summary","group","linear"))
causal_ablation=('strongest_numeric_pair' not in ablated and ablated.get('schema')==analysis.get('schema'))
checks['causal_analysis_ablation']=causal_ablation
passed=all(checks.values())

candidate_digest=h({'component_id':Reasoner.COMPONENT_ID,'source_sha256':fsha(CAND_SRC),'checks':checks})
meta={'schema':'yado.g2.bounded_scientific_data_reasoner_candidate.v1','component_id':Reasoner.COMPONENT_ID,
 'candidate_digest':candidate_digest,'candidate_source_sha256':fsha(CAND_SRC),'generation':ledger['current_head'],
 'parent_head_digest':head['canonical_head_digest'],'source_self_audit_receipt':audit['receipt_sha256'],
 'training_dataset':{'url':iris_url,'sha256':hashlib.sha256(data).hexdigest(),'rows':len(rows)},
 'checks':checks,'canonical_active':False,'promotion_applied':False,
 'state':'AUTHORIZED_FOR_SHADOW_ADMISSION' if passed else 'WITHHELD_SCIENCE_EVOLUTION_V1',
 'semantic_boundary':'BOUNDED TABULAR DESCRIPTIVE STATISTICS, PEARSON CORRELATION, SIMPLE LINEAR FIT, GROUP MEANS, AND THREE EXPLICIT HYPOTHESIS FORMS. NOT CAUSAL INFERENCE OR GENERAL SCIENTIFIC REASONING.'}
CAND_META.write_text(json.dumps(meta,indent=2,sort_keys=True)+'\n')
next_cap='REAL_SCIENCE_DATA_TRANSFER_FRESH_ADMISSION_V1' if passed else 'REAL_SCIENCE_DATA_TRANSFER_NATIVE_EVOLUTION_V2'
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.science_data_native_self_evolution.v1',
 'status':'PASS_SCIENCE_DATA_NATIVE_SELF_EVOLUTION_V1' if passed else 'WITHHOLD_SCIENCE_DATA_NATIVE_SELF_EVOLUTION_V1',
 'candidate_digest':candidate_digest,'candidate_source_sha256':fsha(CAND_SRC),
 'dataset':meta['training_dataset'],'analysis':analysis,'hypotheses':hyps,'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,'semantic_boundary':meta['semantic_boundary']}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_SCIENCE_DATA_NATIVE_SELF_EVOLUTION",
 'event_type':'KERNEL_SELF_EVOLVED_SCIENCE_DATA_REASONER','status':'PASS_SHADOW' if passed else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'REAL_SCIENCE_DATA_TRANSFER_NATIVE_EVOLUTION_V1',
 'effect':f"BOUNDED_SCIENCE_DATA_REASONER; NEXT={next_cap}",
 'source_path':f'receipts/yado-science-data-native-self-evolution-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'checks':checks,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('SCIENCE_DATA_NATIVE_SELF_EVOLUTION_WITHHELD')
