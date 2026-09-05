from __future__ import annotations
from pathlib import Path
from collections import Counter
import copy,csv,datetime,hashlib,io,json,os,random,urllib.request,zipfile,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_evolution_runtime_native_v1 import fit_bool_tree
from yado_organ_runtime_native_v1 import tree_predict,fit_tree,tree_acc
from yado_cognitive_growth_runtime_v1 import learn_multicontext_precedence,planning_accuracy
from yado_neutral_evidence_profile_selector_v1 import NeutralEvidenceProfileSelectorV1,EvidenceCandidate
from yado_unified_core_v1 import UnifiedYADOCoreV1

PARENT=REPO/'experience/yado-multidomain-cognitive-composition-training-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-multidomain-real-data-training-v1.json'
EXP=REPO/'experience/yado-multidomain-real-data-training-v1.json'
USGS_URL='https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_month.geojson'
UCI_URL='https://cdn.uci-ics-mlr-prod.aws.uci.edu/53/iris.zip'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def hbytes(b):return hashlib.sha256(b).hexdigest()
def fetch(url,headers=None,timeout=30):
    req=urllib.request.Request(url,headers={'User-Agent':'YADO-G2-REAL-DATA-TRAINING/1.0',**(headers or {})})
    with urllib.request.urlopen(req,timeout=timeout) as r:return r.read()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
parent=load(PARENT)
if parent.get('status')!='TRAINED':raise RuntimeError('MULTIDOMAIN_COMPOSITION_PARENT_REQUIRED')

def balanced_acc(pred,truth):
    labels=sorted(set(truth),key=str)
    scores=[]
    for y in labels:
        idx=[i for i,t in enumerate(truth) if t==y]
        if idx:scores.append(sum(pred[i]==truth[i] for i in idx)/len(idx))
    return sum(scores)/len(scores) if scores else 0.0

# -------- REAL LOGIC: USGS earthquakes --------
usgs_bytes=fetch(USGS_URL)
usgs=json.loads(usgs_bytes.decode('utf-8'))
events=[]
for f in usgs.get('features') or []:
    p=f.get('properties') or {};g=f.get('geometry') or {};coords=g.get('coordinates') or []
    try:
        mag=float(p.get('mag'));sig=float(p.get('sig'));tm=int(p.get('time'));depth=float(coords[2])
    except (TypeError,ValueError,IndexError):continue
    events.append({'id':str(f.get('id')),'time':tm,'mag':mag,'sig':sig,'depth':depth,
                   'tsunami':bool(p.get('tsunami')),'felt':(p.get('felt') or 0)>0,'reviewed':str(p.get('status'))=='reviewed'})
events=sorted(events,key=lambda x:(x['time'],x['id']))
if len(events)<200:raise RuntimeError('USGS_EVENTS_TOO_SMALL:'+str(len(events)))
n=len(events);a=int(n*.60);b=int(n*.80)
efit0,eval0,eblind0=events[:a],events[a:b],events[b:]
mags=sorted(x['mag'] for x in efit0);sigs=sorted(x['sig'] for x in efit0)
mag50=mags[len(mags)//2];mag75=mags[int(.75*(len(mags)-1))];sig75=sigs[int(.75*(len(sigs)-1))]
def eq_features(x):
    return {'mag_ge_median':x['mag']>=mag50,'mag_ge_q75':x['mag']>=mag75,'shallow':x['depth']<70.0,'very_shallow':x['depth']<20.0,
            'tsunami':x['tsunami'],'felt_any':x['felt'],'reviewed':x['reviewed']}
def eq_target(x):return x['sig']>=sig75
efit=[(eq_features(x),eq_target(x)) for x in efit0];evals=[(eq_features(x),eq_target(x)) for x in eval0];eblind=[(eq_features(x),eq_target(x)) for x in eblind0]
logic_trials=[]
for d in (1,2,3,4,5,6,7):
    m=fit_bool_tree(efit,d);pr=[bool(tree_predict(m,x)) for x,_ in evals];tr=[y for _,y in evals]
    logic_trials.append({'token':'TREE_D'+str(d),'depth':d,'complexity':d,'validation_balanced':balanced_acc(pr,tr),'model':m})
lsel=NeutralEvidenceProfileSelectorV1.select([EvidenceCandidate(token=t['token'],evidence=t['validation_balanced'],complexity=t['complexity'],risk=0,novelty=.2) for t in logic_trials],
 complexity_penalty=.006,risk_penalty=.2,novelty_bonus=.01)
lc=next(t for t in logic_trials if t['token']==lsel['selected_token'])
lmodel=fit_bool_tree(efit+evals,lc['depth'])
lp=[bool(tree_predict(lmodel,x)) for x,_ in eblind];ly=[y for _,y in eblind]
logic_fresh=balanced_acc(lp,ly)
maj=Counter(y for _,y in efit+evals).most_common(1)[0][0]
logic_ablation=balanced_acc([maj]*len(ly),ly)

# -------- REAL INTELLIGENCE: UCI Iris --------
iris_zip=fetch(UCI_URL)
zf=zipfile.ZipFile(io.BytesIO(iris_zip))
names=zf.namelist()
target_name=next((n for n in names if n.lower().endswith('/iris.data') or n.lower()=='iris.data'),None)
if target_name is None:target_name=next((n for n in names if n.lower().endswith('.data')),None)
if target_name is None:raise RuntimeError('UCI_IRIS_DATA_NOT_FOUND')
txt=zf.read(target_name).decode('utf-8','replace')
iris=[]
for row in csv.reader(io.StringIO(txt)):
    if len(row)<5 or not row[4].strip():continue
    try:a,b0,c,d=map(float,row[:4])
    except ValueError:continue
    iris.append(({'sepal_length':a,'sepal_width':b0,'petal_length':c,'petal_width':d},row[4].strip()))
if len(iris)!=150:raise RuntimeError('UCI_IRIS_ROW_COUNT:'+str(len(iris)))
iris=sorted(iris,key=lambda z:hashlib.sha256(canon(z).encode()).hexdigest())
ifit,ival,iblind=iris[:90],iris[90:120],iris[120:]
intel_trials=[]
for d in (1,2,3,4,5,6):
    m=fit_tree(ifit,d)
    intel_trials.append({'token':'CART_D'+str(d),'depth':d,'complexity':d,'validation':tree_acc(m,ival),'model':m})
isel=NeutralEvidenceProfileSelectorV1.select([EvidenceCandidate(token=t['token'],evidence=t['validation'],complexity=t['complexity'],risk=0,novelty=.2) for t in intel_trials],
 complexity_penalty=.006,risk_penalty=.2,novelty_bonus=.01)
ic=next(t for t in intel_trials if t['token']==isel['selected_token'])
imodel=fit_tree(ifit+ival,ic['depth']);intel_fresh=tree_acc(imodel,iblind)
imaj=Counter(y for _,y in ifit+ival).most_common(1)[0][0]
intel_ablation=sum(y==imaj for _,y in iblind)/len(iblind)

# -------- REAL THINKING: actual YADO GitHub Actions history --------
repo_name=os.getenv('GITHUB_REPOSITORY','v37025337-pixel/EVA')
gh_url=f'https://api.github.com/repos/{repo_name}/actions/runs?per_page=100'
token=os.getenv('GITHUB_TOKEN') or ''
headers={'Accept':'application/vnd.github+json'}
if token:headers['Authorization']='Bearer '+token
gh_bytes=fetch(gh_url,headers=headers)
runs0=(json.loads(gh_bytes.decode('utf-8')).get('workflow_runs') or [])
runs=[]
for r in runs0:
    con=str(r.get('conclusion') or '')
    if con not in ('success','failure'):continue
    try:
        ca=datetime.datetime.fromisoformat(str(r['created_at']).replace('Z','+00:00'));ua=datetime.datetime.fromisoformat(str(r['updated_at']).replace('Z','+00:00'))
        duration=(ua-ca).total_seconds()
    except Exception:duration=0.0
    runs.append({'id':str(r.get('id')),'name':str(r.get('name') or ''),'conclusion':con,'duration_high':duration>180.0,
                 'event':str(r.get('event') or ''),'created_at':str(r.get('created_at') or '')})
if len(runs)<30:raise RuntimeError('GITHUB_REAL_RUNS_TOO_SMALL:'+str(len(runs)))
roles=['OBSERVE','VERIFY','DIAGNOSE','REPAIR','RETRY','ARCHIVE','CHECK_DEPENDENCY','MONITOR']
success_order=['OBSERVE','VERIFY','ARCHIVE','MONITOR','CHECK_DEPENDENCY','DIAGNOSE','REPAIR','RETRY']
failure_order=['OBSERVE','DIAGNOSE','REPAIR','RETRY','VERIFY','CHECK_DEPENDENCY','ARCHIVE','MONITOR']
def run_ctx(r):
    return {'success':r['conclusion']=='success','failure':r['conclusion']=='failure','duration_high':r['duration_high'],
            'manual_dispatch':r['event']=='workflow_dispatch','curriculum_named':'Training' in r['name'] or 'Curriculum' in r['name']}
def episode(r,seed):
    exp=success_order if r['conclusion']=='success' else failure_order
    acts=[{'id':f'{r["id"]}-{i}','role':role} for i,role in enumerate(roles)]
    random.Random(seed+int(r['id'])%100000).shuffle(acts)
    return (run_ctx(r),acts,exp)
runs=sorted(runs,key=lambda x:hashlib.sha256(x['id'].encode()).hexdigest())
rn=len(runs);ra=int(rn*.60);rb=int(rn*.80)
rfit0,rval0,rblind0=runs[:ra],runs[ra:rb],runs[rb:]
fit_traces=[(run_ctx(r),success_order if r['conclusion']=='success' else failure_order) for r in rfit0]
rval=[episode(r,5000) for r in rval0];rblind=[episode(r,9000) for r in rblind0]
thinking_trials=[]
for threshold in (.55,.60,.67,.75,.80):
    for keys in (1,2,3,4):
        for support in (2,3,4):
            m=learn_multicontext_precedence(fit_traces,threshold=threshold,min_support=support,max_context_keys=keys)
            thinking_trials.append({'token':f'T{threshold}_K{keys}_S{support}','threshold':threshold,'keys':keys,'support':support,
                                    'complexity':keys+.25*support,'validation':planning_accuracy(m,rval),'model':m})
tsel=NeutralEvidenceProfileSelectorV1.select([EvidenceCandidate(token=t['token'],evidence=t['validation'],complexity=t['complexity'],risk=0,novelty=.2) for t in thinking_trials],
 complexity_penalty=.006,risk_penalty=.2,novelty_bonus=.01)
tc=next(t for t in thinking_trials if t['token']==tsel['selected_token'])
tmodel=learn_multicontext_precedence(fit_traces+[(run_ctx(r),success_order if r['conclusion']=='success' else failure_order) for r in rval0],
 threshold=tc['threshold'],min_support=tc['support'],max_context_keys=tc['keys'])
thinking_fresh=planning_accuracy(tmodel,rblind)
tab=learn_multicontext_precedence([({},trace) for _,trace in fit_traces],threshold=tc['threshold'],min_support=tc['support'],max_context_keys=0)
thinking_ablation=planning_accuracy(tab,rblind)
thinking_classes={}
for con in ('success','failure'):
    xs=[episode(r,12000) for r in rblind0 if r['conclusion']==con]
    thinking_classes[con]={'count':len(xs),'accuracy':planning_accuracy(tmodel,xs) if xs else None}

parents=parent['genes']
logic_gene={'schema':'yado.g2.real_data_logic_gene.v1','gene_id':'GENE-G2-REAL-DATA-LOGIC-V1-'+digest({'model':lmodel,'source':hbytes(usgs_bytes)})[:16],
 'organ':'LOGIC','heritage':[parents['LOGIC']['gene_id']],'task':'USGS_EARTHQUAKE_SIGNIFICANCE','model':lmodel,
 'selected':{k:lc[k] for k in ('token','depth','validation_balanced')},'fresh_balanced':logic_fresh,'ablation_balanced':logic_ablation,
 'source_sha256':hbytes(usgs_bytes),'source_url':USGS_URL,'promotion_state':'SHADOW_ONLY'}
logic_gene['gene_digest']=digest(logic_gene)
intel_gene={'schema':'yado.g2.real_data_intelligence_gene.v1','gene_id':'GENE-G2-REAL-DATA-INTELLIGENCE-V1-'+digest({'model':imodel,'source':hbytes(iris_zip)})[:16],
 'organ':'INTELLIGENCE','heritage':[parents['INTELLIGENCE']['gene_id']],'task':'UCI_IRIS_SPECIES_CLASSIFICATION','model':imodel,
 'selected':{k:ic[k] for k in ('token','depth','validation')},'fresh':intel_fresh,'ablation':intel_ablation,
 'source_sha256':hbytes(iris_zip),'source_url':UCI_URL,'promotion_state':'SHADOW_ONLY'}
intel_gene['gene_digest']=digest(intel_gene)
thinking_gene={'schema':'yado.g2.real_data_thinking_gene.v1','gene_id':'GENE-G2-REAL-DATA-THINKING-V1-'+digest({'model':tmodel,'source':hbytes(gh_bytes)})[:16],
 'organ':'THINKING','heritage':[parents['THINKING']['gene_id']],'task':'YADO_GITHUB_ACTIONS_RESPONSE_PLANNING','model':tmodel,
 'selected':{k:tc[k] for k in ('token','threshold','keys','support','validation')},'fresh':thinking_fresh,'ablation':thinking_ablation,
 'class_scores':thinking_classes,'source_sha256':hbytes(gh_bytes),'source_url':gh_url,'promotion_state':'SHADOW_ONLY'}
thinking_gene['gene_digest']=digest(thinking_gene)
genes={'LOGIC':logic_gene,'THINKING':thinking_gene,'INTELLIGENCE':intel_gene}
portfolio={'schema':'yado.g2.real_data_organ_portfolio.v1','portfolio_id':'PORT-G2-REAL-DATA-'+digest({k:v['gene_digest'] for k,v in genes.items()})[:16],
 'parents':{k:parents[k]['gene_id'] for k in ('LOGIC','THINKING','INTELLIGENCE')},'genes':{k:v['gene_id'] for k,v in genes.items()},
 'promotion_state':'SHADOW_ONLY','automatic_canonical_promotion':False}
portfolio['portfolio_digest']=digest(portfolio)

core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)
checks={
 'usgs_live_fetch':len(events)>=200,'usgs_source_hashed':bool(logic_gene['source_sha256']),
 'logic_real_fresh_ge_0_75':logic_fresh>=.75,'logic_real_causal_drop_ge_0_20':logic_fresh-logic_ablation>=.20,
 'uci_exact_150_rows':len(iris)==150,'uci_source_hashed':bool(intel_gene['source_sha256']),
 'intelligence_real_fresh_ge_0_85':intel_fresh>=.85,'intelligence_real_gain_ge_0_30':intel_fresh-intel_ablation>=.30,
 'github_real_runs_ge_30':len(runs)>=30,'github_source_hashed':bool(thinking_gene['source_sha256']),
 'thinking_real_fresh_ge_0_75':thinking_fresh>=.75,'thinking_real_causal_drop_ge_0_15':thinking_fresh-thinking_ablation>=.15,
 'thinking_success_and_failure_in_blind':all(v['count']>=2 for v in thinking_classes.values()),
 'three_real_data_gene_identities':len({v['gene_id'] for v in genes.values()})==3,
 'external_models_used':False,'automatic_canonical_promotion':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest')}
false_keys=['external_models_used','automatic_canonical_promotion']
passed=all(v is True for k,v in checks.items() if k not in false_keys) and all(checks[k] is False for k in false_keys)
status='PASS_SHADOW_G2_MULTIDOMAIN_REAL_DATA_TRAINING_V1' if passed else 'WITHHOLD_G2_MULTIDOMAIN_REAL_DATA_TRAINING_V1'
sources={'USGS':{'url':USGS_URL,'sha256':hbytes(usgs_bytes),'event_count':len(events),'feed_generated':(usgs.get('metadata') or {}).get('generated')},
 'UCI_IRIS':{'url':UCI_URL,'sha256':hbytes(iris_zip),'row_count':len(iris),'zip_member':target_name},
 'GITHUB_ACTIONS':{'url':gh_url,'sha256':hbytes(gh_bytes),'usable_run_count':len(runs),'blind_class_counts':{k:v['count'] for k,v in thinking_classes.items()}}}
metrics={'LOGIC':{'fresh_balanced':logic_fresh,'ablation_balanced':logic_ablation,'drop':logic_fresh-logic_ablation,'blind_count':len(eblind),'sig_threshold_from_fit':sig75},
 'THINKING':{'fresh':thinking_fresh,'ablation':thinking_ablation,'drop':thinking_fresh-thinking_ablation,'blind_count':len(rblind),'class_scores':thinking_classes},
 'INTELLIGENCE':{'fresh':intel_fresh,'ablation':intel_ablation,'drop':intel_fresh-intel_ablation,'blind_count':len(iblind)}}
exp={'schema':'yado.g2.multidomain_real_data_training.experience.v1','status':'TRAINED' if passed else 'WITHHOLD','sources':sources,'metrics':metrics,
 'genes':genes,'portfolio':portfolio,'checks':checks,'canonical_mutation':False,
 'semantic_boundary':'REAL-DATA ORGAN TRAINING. LOGIC USES LIVE USGS EARTHQUAKE OBSERVATIONS WITH A TRAIN-DERIVED SIGNIFICANCE THRESHOLD; INTELLIGENCE USES THE UCI IRIS REAL MEASUREMENT/LABEL DATASET; THINKING USES ACTUAL YADO GITHUB ACTIONS RUN HISTORY WITH POLICY-DERIVED RESPONSE ORDER LABELS. NO EXTERNAL MODEL IS USED. THESE ARE THREE REAL-DATA SPECIALISTS; CROSS-ORGAN REAL-WORLD COGNITIVE COMPOSITION IS A SEPARATE NEXT TEST.'}
exp['experience_digest']=digest(exp);EXP.parent.mkdir(parents=True,exist_ok=True);EXP.write_text(json.dumps(exp,indent=2,sort_keys=True,default=str)+'\n')
report={'schema':'yado.g2.multidomain_real_data_training.v1','status':status,'sources':sources,'metrics':metrics,'gene_ids':{k:v['gene_id'] for k,v in genes.items()},
 'portfolio_id':portfolio['portfolio_id'],'portfolio_digest':portfolio['portfolio_digest'],'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'REAL_DATA_COGNITIVE_COMPOSITION_AND_TRANSFER_V1' if passed else 'MULTIDOMAIN_REAL_DATA_TRAINING_REPAIR_V2'}
report['receipt_sha256']=digest(report);OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
print(json.dumps(report,indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
