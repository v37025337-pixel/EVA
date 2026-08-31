from __future__ import annotations
from pathlib import Path
import csv,hashlib,importlib.util,io,json,math,os,sys,urllib.request

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
META=REPO/'candidates'/'g2-self-evolution'/'bounded_scientific_data_reasoner_v1.json'
SRC=REPO/'candidates'/'g2-self-evolution'/'bounded_scientific_data_reasoner_v1.py'
OUT=ROOT/'yado_science_data_native_fresh_admission_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def fetch_csv(url):
    rq=urllib.request.Request(url,headers={'User-Agent':'YADO-Science-Fresh-Admission/1.0'})
    with urllib.request.urlopen(rq,timeout=20) as resp:data=resp.read()
    return data,list(csv.DictReader(io.StringIO(data.decode('utf-8'))))
def fv(v):
    try:return float(v)
    except:return None
def ref_corr(rows,x,y):
    pairs=[]
    for r in rows:
        a=fv(r.get(x));b=fv(r.get(y))
        if a is not None and b is not None and math.isfinite(a) and math.isfinite(b):pairs.append((a,b))
    if len(pairs)<3:return None
    mx=sum(a for a,_ in pairs)/len(pairs);my=sum(b for _,b in pairs)/len(pairs)
    num=sum((a-mx)*(b-my) for a,b in pairs)
    den=(sum((a-mx)**2 for a,_ in pairs)*sum((b-my)**2 for _,b in pairs))**0.5
    return None if den==0 else num/den
def ref_group_mean(rows,cat,num,group):
    vals=[fv(r.get(num)) for r in rows if r.get(cat)==group]
    vals=[x for x in vals if x is not None and math.isfinite(x)]
    return sum(vals)/len(vals) if vals else None

head=load(HEAD);ledger=load(LEDGER);meta=load(META)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['REAL_SCIENCE_DATA_TRANSFER_FRESH_ADMISSION_V1']:raise RuntimeError('UNEXPECTED_FRONTIER')
if meta.get('state')!='AUTHORIZED_FOR_SHADOW_ADMISSION':raise RuntimeError('CANDIDATE_NOT_AUTHORIZED')
if fsha(SRC)!=meta.get('candidate_source_sha256'):raise RuntimeError('SOURCE_DRIFT')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')

sp=importlib.util.spec_from_file_location('bounded_science_fresh',SRC)
mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod)
Reasoner=mod.BoundedScientificDataReasonerV1

datasets=[
 ('PENGUINS','https://raw.githubusercontent.com/mwaskom/seaborn-data/master/penguins.csv'),
 ('TIPS','https://raw.githubusercontent.com/mwaskom/seaborn-data/master/tips.csv'),
]
loaded={}
for name,url in datasets:
    data,rows=fetch_csv(url);loaded[name]={'url':url,'data':data,'rows':rows,'sha256':hashlib.sha256(data).hexdigest()}

results=[]
# Penguins: unseen dataset with missing values.
pr=loaded['PENGUINS']['rows'];pa=Reasoner.analyze(pr)
pc=Reasoner.pearson(pr,'flipper_length_mm','body_mass_g');pcref=ref_corr(pr,'flipper_length_mm','body_mass_g')
pg=Reasoner.group_means(pr,'species','body_mass_g')
p_ref_adelie=ref_group_mean(pr,'species','body_mass_g','Adelie');p_ref_gentoo=ref_group_mean(pr,'species','body_mass_g','Gentoo')
ph=[
 Reasoner.evaluate_hypothesis(pr,{"type":"CORRELATION_ABS_AT_LEAST","x":"flipper_length_mm","y":"body_mass_g","threshold":0.80}),
 Reasoner.evaluate_hypothesis(pr,{"type":"GROUP_MEAN_ORDER","category":"species","numeric":"body_mass_g","lower_group":"Adelie","higher_group":"Gentoo"}),
 Reasoner.evaluate_hypothesis(pr,{"type":"LINEAR_R2_AT_LEAST","x":"flipper_length_mm","y":"body_mass_g","threshold":0.70}),
]
results.append({
 'dataset':'PENGUINS','row_count':len(pr),'schema':pa['schema'],'strongest':pa.get('strongest_numeric_pair'),
 'corr':pc,'corr_reference':pcref,'group_means':pg,'hypotheses':ph,
 'checks':{
   'row_count':len(pr)==344,
   'numeric_schema':set(pa['schema']['numeric'])=={'bill_length_mm','bill_depth_mm','flipper_length_mm','body_mass_g'},
   'categorical_schema':{'species','island','sex'}.issubset(set(pa['schema']['categorical'])),
   'strongest_pair':set((pa.get('strongest_numeric_pair') or {}).get('pair',[]))=={'flipper_length_mm','body_mass_g'},
   'reference_corr_match':pc is not None and pcref is not None and abs(pc-pcref)<1e-12,
   'reference_group_match':pg is not None and abs(pg['Adelie']['mean']-p_ref_adelie)<1e-12 and abs(pg['Gentoo']['mean']-p_ref_gentoo)<1e-12,
   'all_hypotheses_supported':all(x.get('supported') is True for x in ph),
 }
})

# Tips: second unseen dataset, different schema and domain.
tr=loaded['TIPS']['rows'];ta=Reasoner.analyze(tr)
tc=Reasoner.pearson(tr,'total_bill','tip');tcref=ref_corr(tr,'total_bill','tip')
tg=Reasoner.group_means(tr,'time','total_bill')
t_ref_lunch=ref_group_mean(tr,'time','total_bill','Lunch');t_ref_dinner=ref_group_mean(tr,'time','total_bill','Dinner')
th=[
 Reasoner.evaluate_hypothesis(tr,{"type":"CORRELATION_ABS_AT_LEAST","x":"total_bill","y":"tip","threshold":0.60}),
 Reasoner.evaluate_hypothesis(tr,{"type":"GROUP_MEAN_ORDER","category":"time","numeric":"total_bill","lower_group":"Lunch","higher_group":"Dinner"}),
 Reasoner.evaluate_hypothesis(tr,{"type":"LINEAR_R2_AT_LEAST","x":"total_bill","y":"tip","threshold":0.40}),
]
results.append({
 'dataset':'TIPS','row_count':len(tr),'schema':ta['schema'],'strongest':ta.get('strongest_numeric_pair'),
 'corr':tc,'corr_reference':tcref,'group_means':tg,'hypotheses':th,
 'checks':{
   'row_count':len(tr)==244,
   'numeric_schema':{'total_bill','tip','size'}.issubset(set(ta['schema']['numeric'])),
   'categorical_schema':{'sex','smoker','day','time'}.issubset(set(ta['schema']['categorical'])),
   'strongest_pair':set((ta.get('strongest_numeric_pair') or {}).get('pair',[]))=={'total_bill','tip'},
   'reference_corr_match':tc is not None and tcref is not None and abs(tc-tcref)<1e-12,
   'reference_group_match':tg is not None and abs(tg['Lunch']['mean']-t_ref_lunch)<1e-12 and abs(tg['Dinner']['mean']-t_ref_dinner)<1e-12,
   'all_hypotheses_supported':all(x.get('supported') is True for x in th),
 }
})

# Feature ablations on fresh data.
p_no_corr=Reasoner.analyze(pr,enable=("summary","group","linear"))
t_no_group=Reasoner.analyze(tr,enable=("summary","correlation","linear"))
ablation={
 'correlation_removed_from_penguins':'correlations' not in p_no_corr and 'strongest_numeric_pair' not in p_no_corr,
 'group_removed_from_tips':'group_means' not in t_no_group,
}
source=SRC.read_text(encoding='utf-8')
checks={
 'two_fresh_public_datasets_loaded':all(len(loaded[k]['data'])>1000 for k in loaded),
 'all_dataset_checks':all(all(r['checks'].values()) for r in results),
 'causal_feature_ablation':all(ablation.values()),
 'source_unchanged':fsha(SRC)==meta['candidate_source_sha256'],
 'candidate_has_no_network':all(x not in source for x in ['urllib','requests','aiohttp','socket']),
 'canonical_head_immutable':ledger.get('current_head_digest')==head.get('canonical_head_digest'),
}
passed=all(checks.values())
next_cap='REAL_SCIENCE_DATA_TRANSFER_CANONICAL_INTEGRATION_V1' if passed else 'REAL_SCIENCE_DATA_TRANSFER_NATIVE_EVOLUTION_V2'
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.science_data_native_fresh_admission.v1',
 'status':'PASS_SCIENCE_DATA_NATIVE_FRESH_ADMISSION_V1' if passed else 'WITHHOLD_SCIENCE_DATA_NATIVE_FRESH_ADMISSION_V1',
 'candidate_digest':meta['candidate_digest'],'candidate_source_sha256':meta['candidate_source_sha256'],
 'datasets':{k:{'url':v['url'],'sha256':v['sha256'],'rows':len(v['rows'])} for k,v in loaded.items()},
 'fresh_results':results,'ablation':ablation,'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,'semantic_boundary':meta['semantic_boundary']}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_SCIENCE_DATA_NATIVE_FRESH_ADMISSION",
 'event_type':'SCIENCE_DATA_REASONER_FRESH_PUBLIC_TRANSFER','status':'PASS_SHADOW' if passed else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'REAL_SCIENCE_DATA_TRANSFER_FRESH_ADMISSION_V1',
 'effect':f"FRESH_PENGUINS_TIPS_TRANSFER; PASS={passed}; NEXT={next_cap}",
 'source_path':f'receipts/yado-science-data-native-fresh-admission-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'checks':checks,'ablation':ablation,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('SCIENCE_DATA_NATIVE_FRESH_ADMISSION_WITHHELD')
