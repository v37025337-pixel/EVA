from __future__ import annotations

from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
from urllib.parse import urlencode
import copy
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import urllib.request

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_g2_all_experience_tri_organ_runtime_v1 import G2AllExperienceTriOrganRuntimeV1
from yado_generic_relational_meta_language_v1 import GenericRelationalMetaLanguageV1
from yado_generic_event_state_meta_language_v1 import GenericEventStateMetaLanguageV1
from yado_g2_experience_conditioned_cognitive_layer_v4 import G2ExperienceConditionedCognitiveLayerV4
from yado_evolution_runtime_native_v1 import fit_bool_tree
from yado_organ_runtime_native_v1 import tree_predict
from yado_unified_core_v1 import UnifiedYADOCoreV1

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
TRI=REPO/'canonical/yado-g2-all-experience-tri-organ-v1.json'
COG=REPO/'canonical/yado-g2-experience-conditioned-cognitive-layer-v4.json'
OLD_REAL=REPO/'experience/yado-multidomain-real-data-training-v1.json'
OLD_FOUR=REPO/'experience/yado-four-domain-fresh-stress-v1.json'
REQ=REPO/'architecture/yado-g2-fresh-real-data-cognitive-transfer-v1-request.json'
OUT=ROOT/'yado_g2_fresh_real_data_cognitive_transfer_v1_receipt.json'
CAND=REPO/'candidates/kernel-self-generated/g2-portable-usgs-real-data-specialist-repair-v1.json'

USGS_WEEK='https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_week.geojson'
WORLDBANK='https://api.worldbank.org/v2/country/FRA;JPN;BRA/indicator/NY.GDP.MKTP.CD?format=json&per_page=100&date=2021:2024'
CISA='https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json'
OPENFDA='https://api.fda.gov/drug/enforcement.json?limit=20'


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))

def canon(o):
    return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)

def digest(o):
    return hashlib.sha256(canon(o).encode()).hexdigest()

def hbytes(b):
    return hashlib.sha256(b).hexdigest()

def fetch(url,headers=None,timeout=35,max_bytes=20_000_000):
    req=urllib.request.Request(url,headers={'User-Agent':'YADO-G2-Fresh-Real-Data-Transfer/1.0',**(headers or {})})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        body=r.read(max_bytes+1)
        if len(body)>max_bytes:raise RuntimeError('SOURCE_BYTE_BUDGET:'+url)
        return body,str(getattr(r,'url',url) or url),int(getattr(r,'status',200) or 200),str(r.headers.get('Content-Type') or '')

def stable(v,maxlen=160):
    if isinstance(v,(dict,list,tuple)):s=canon(v)
    else:s=str(v)
    return re.sub(r'\s+',' ',s).strip()[:maxlen]

def balanced_acc(pred,truth):
    labels=sorted(set(truth),key=str);scores=[]
    for y in labels:
        idx=[i for i,t in enumerate(truth) if t==y]
        if idx:scores.append(sum(pred[i]==truth[i] for i in idx)/len(idx))
    return sum(scores)/len(scores) if scores else 0.0

head=load(HEAD);core_before=load(CORE);head_before=copy.deepcopy(head)
tri_art=load(TRI);cog_art=load(COG);old_real=load(OLD_REAL);old_four=load(OLD_FOUR);req=load(REQ)
if req.get('expected_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('STALE_HEAD')
if req.get('expected_frontier')!=head.get('current_frontier'):raise RuntimeError('STALE_FRONTIER')
if int(req.get('expected_active_capability_count',-1))!=len(head.get('active_capabilities',[])):raise RuntimeError('STALE_CAPABILITIES')
if head.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')

# ---------------------------------------------------------------------------
# Fetch current public data. No external ML model is used.
# ---------------------------------------------------------------------------
sources={}
for name,url in [('USGS_WEEK',USGS_WEEK),('WORLDBANK_GDP',WORLDBANK),('CISA_KEV',CISA),('OPENFDA_ENFORCEMENT',OPENFDA)]:
    body,resolved,status,ctype=fetch(url)
    sources[name]={'requested_url':url,'resolved_url':resolved,'http_status':status,'content_type':ctype,'bytes':len(body),'sha256':hbytes(body)}
    sources[name]['json']=json.loads(body.decode('utf-8','replace'))

# ---------------------------------------------------------------------------
# 1. Frozen raw-USGS specialist portability audit.
# ---------------------------------------------------------------------------
old_logic=(cog_art.get('real_data_genes') or {}).get('LOGIC') or {}
model_feature=str((old_logic.get('model') or {}).get('feature') or '')
raw_feature_contract=old_logic.get('feature_transform') or old_logic.get('preprocessing') or old_logic.get('input_contract')
training_usgs=(old_real.get('sources') or {}).get('USGS') or {}
prior_week_usgs=((old_four.get('source_meta') or {}).get('GEOSCIENCE_USGS') or {})
frozen_usgs_portability={
  'task':old_logic.get('task'),
  'model_feature':model_feature,
  'training_source_sha256':training_usgs.get('sha256'),
  'current_source_sha256':sources['USGS_WEEK']['sha256'],
  'source_changed':sources['USGS_WEEK']['sha256']!=prior_week_usgs.get('sha256'),
  'prior_week_source_sha256':prior_week_usgs.get('sha256'),
  'preprocessing_bound_in_canonical':bool(raw_feature_contract),
  'raw_portability_status':'PASS' if raw_feature_contract else 'WITHHOLD_RAW_PORTABILITY_MISSING_PREPROCESSING_PROVENANCE',
}
if model_feature=='mag_ge_q75' and raw_feature_contract:
    # Current schema has no supported evaluator for a bound transform object yet.
    frozen_usgs_portability['raw_portability_status']='WITHHOLD_RAW_PORTABILITY_TRANSFORM_EXECUTOR_UNAVAILABLE'

# ---------------------------------------------------------------------------
# 2. Shadow portable USGS repair: fit on older events, test on newer events.
# Explicit train-derived thresholds are part of the candidate.
# ---------------------------------------------------------------------------
usgs=sources['USGS_WEEK']['json'];events=[]
for f in usgs.get('features') or []:
    p=f.get('properties') or {};g=f.get('geometry') or {};coords=g.get('coordinates') or []
    try:
        mag=float(p.get('mag'));sig=float(p.get('sig'));tm=int(p.get('time'));depth=float(coords[2])
    except (TypeError,ValueError,IndexError):continue
    events.append({
      'id':str(f.get('id')),'time':tm,'mag':mag,'sig':sig,'depth':depth,
      'tsunami':bool(p.get('tsunami')),'felt':(p.get('felt') or 0)>0,'reviewed':str(p.get('status'))=='reviewed'
    })
events=sorted(events,key=lambda x:(x['time'],x['id']))
if len(events)<300:raise RuntimeError('USGS_TOO_FEW_EVENTS:'+str(len(events)))
n=len(events);a=int(n*.60);b=int(n*.80)
fit0,val0,blind0=events[:a],events[a:b],events[b:]
mags=sorted(x['mag'] for x in fit0);sigs=sorted(x['sig'] for x in fit0)
mag_q75=mags[int(.75*(len(mags)-1))];sig_q75=sigs[int(.75*(len(sigs)-1))]
def usgs_x(x):
    return {
      'mag_ge_q75':x['mag']>=mag_q75,
      'shallow':x['depth']<70.0,
      'very_shallow':x['depth']<20.0,
      'tsunami':x['tsunami'],
      'felt_any':x['felt'],
      'reviewed':x['reviewed'],
    }
def usgs_y(x):return x['sig']>=sig_q75
fit=[(usgs_x(x),usgs_y(x)) for x in fit0];val=[(usgs_x(x),usgs_y(x)) for x in val0];blind=[(usgs_x(x),usgs_y(x)) for x in blind0]
trials=[]
for depth in (1,2,3,4,5,6):
    m=fit_bool_tree(fit,depth)
    pr=[bool(tree_predict(m,x)) for x,_ in val];truth=[y for _,y in val]
    acc=balanced_acc(pr,truth)
    trials.append((acc-.004*depth,acc,-depth,depth,m))
trials.sort(reverse=True,key=lambda z:(z[0],z[1],z[2]))
_,val_acc,_,depth,portable_model=trials[0]
blind_pred=[bool(tree_predict(portable_model,x)) for x,_ in blind];blind_truth=[y for _,y in blind]
portable_blind=balanced_acc(blind_pred,blind_truth)
maj=Counter(y for _,y in fit+val).most_common(1)[0][0]
portable_ablation=balanced_acc([maj]*len(blind_truth),blind_truth)
portable_drop=portable_blind-portable_ablation
portable_candidate={
  'schema':'yado.g2.portable_usgs_real_data_specialist_repair.v1',
  'status':'SHADOW_READY' if portable_blind>=.90 and portable_drop>=.25 else 'WITHHOLD',
  'task':'USGS_EARTHQUAKE_SIGNIFICANCE_PORTABLE_V1',
  'parent_task':old_logic.get('task'),
  'source_url':USGS_WEEK,
  'source_sha256':sources['USGS_WEEK']['sha256'],
  'temporal_split':{'fit':len(fit),'validation':len(val),'blind_newer':len(blind)},
  'feature_transform':{
    'schema':'yado.real_data.feature_transform.usgs.v1',
    'threshold_source':'FIT_PARTITION_ONLY',
    'mag_q75':mag_q75,
    'depth_shallow_lt':70.0,
    'depth_very_shallow_lt':20.0,
    'boolean_fields':['tsunami','felt_any','reviewed'],
    'output_features':['mag_ge_q75','shallow','very_shallow','tsunami','felt_any','reviewed'],
  },
  'target_contract':{
    'field':'sig','operator':'>=','threshold_source':'FIT_PARTITION_ONLY','sig_q75':sig_q75
  },
  'model':portable_model,
  'selected_depth':depth,
  'validation_balanced':val_acc,
  'blind_newer_balanced':portable_blind,
  'majority_ablation_balanced':portable_ablation,
  'causal_gain':portable_drop,
  'automatic_canonical_promotion':False,
  'canonical_mutation':False,
}
portable_candidate['candidate_digest']=digest(portable_candidate)
CAND.parent.mkdir(parents=True,exist_ok=True)
CAND.write_text(json.dumps(portable_candidate,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

# ---------------------------------------------------------------------------
# 3. Frozen GitHub thinking specialist on runs created after its training commit.
# ---------------------------------------------------------------------------
try:
    train_commit_time=subprocess.check_output(
      ['git','log','-1','--format=%cI','--','experience/yado-multidomain-real-data-training-v1.json'],
      cwd=REPO,text=True
    ).strip()
    cutoff=datetime.fromisoformat(train_commit_time.replace('Z','+00:00'))
except Exception as e:
    raise RuntimeError('REAL_DATA_TRAINING_COMMIT_TIME_UNAVAILABLE') from e
repo_name=os.getenv('GITHUB_REPOSITORY','v37025337-pixel/EVA')
headers={'Accept':'application/vnd.github+json'}
token=os.getenv('GITHUB_TOKEN') or ''
if token:headers['Authorization']='Bearer '+token
gh_body,gh_resolved,gh_status,gh_type=fetch(f'https://api.github.com/repos/{repo_name}/actions/runs?per_page=100',headers=headers,max_bytes=8_000_000)
sources['GITHUB_ACTIONS']={'requested_url':f'https://api.github.com/repos/{repo_name}/actions/runs?per_page=100','resolved_url':gh_resolved,'http_status':gh_status,'content_type':gh_type,'bytes':len(gh_body),'sha256':hbytes(gh_body),'training_commit_time':train_commit_time}
runs=[]
for r in (json.loads(gh_body.decode('utf-8')).get('workflow_runs') or []):
    con=str(r.get('conclusion') or '')
    if con not in ('success','failure'):continue
    try:created=datetime.fromisoformat(str(r.get('created_at')).replace('Z','+00:00'))
    except Exception:continue
    if created<=cutoff:continue
    runs.append({'id':str(r.get('id')),'name':str(r.get('name') or ''),'conclusion':con,'event':str(r.get('event') or ''),'created_at':str(r.get('created_at') or '')})
runs=sorted(runs,key=lambda x:(x['created_at'],x['id']))
roles=['OBSERVE','VERIFY','DIAGNOSE','REPAIR','RETRY','ARCHIVE','CHECK_DEPENDENCY','MONITOR']
success_order=['OBSERVE','VERIFY','ARCHIVE','MONITOR','CHECK_DEPENDENCY','DIAGNOSE','REPAIR','RETRY']
failure_order=['OBSERVE','DIAGNOSE','REPAIR','RETRY','VERIFY','CHECK_DEPENDENCY','ARCHIVE','MONITOR']
layer=G2ExperienceConditionedCognitiveLayerV4(cog_art)
gh_results=[];class_counts={'success':0,'failure':0}
for r in runs:
    class_counts[r['conclusion']]+=1
    actions=[{'id':f'{r["id"]}-{i}','role':role} for i,role in enumerate(roles)]
    random.Random(int(r['id'])%100000).shuffle(actions)
    payload={
      'task_id':'YADO_GITHUB_ACTIONS_RESPONSE_PLANNING',
      'context':{'success':r['conclusion']=='success','failure':r['conclusion']=='failure','manual_dispatch':r['event']=='workflow_dispatch'},
      'actions':actions,
    }
    out=layer.decide('THINKING',payload)
    ids=out.get('decision') if isinstance(out.get('decision'),list) else []
    by_id={str(a['id']):str(a['role']) for a in actions}
    got=[by_id.get(str(i)) for i in ids]
    expected=success_order if r['conclusion']=='success' else failure_order
    gh_results.append(got==expected)
github_temporal_accuracy=sum(gh_results)/len(gh_results) if gh_results else 0.0

# ---------------------------------------------------------------------------
# 4. New-domain generic tri-organ transfer over real records.
# ---------------------------------------------------------------------------
def extract_worldbank(obj):
    arr=obj[1] if isinstance(obj,list) and len(obj)>1 and isinstance(obj[1],list) else []
    rows=[]
    for r in arr:
        if not isinstance(r,dict) or r.get('value') is None:continue
        country=(r.get('country') or {}).get('value') if isinstance(r.get('country'),dict) else r.get('country')
        rows.append({
          'record_id':str(r.get('countryiso3code'))+'::'+str(r.get('date')),
          'a':'country='+stable(country),'b':'indicator='+stable((r.get('indicator') or {}).get('value') if isinstance(r.get('indicator'),dict) else r.get('indicator')),
          'c':'date='+stable(r.get('date')),'d':'value='+stable(r.get('value'))
        })
    return sorted(rows,key=lambda x:x['record_id'])

def extract_cisa(obj):
    data=[r for r in (obj.get('vulnerabilities') or []) if isinstance(r,dict)]
    data.sort(key=lambda r:(str(r.get('dateAdded') or ''),str(r.get('cveID') or '')),reverse=True)
    # Previous four-domain stress used the newest slice. Skip deep into history.
    data=data[64:80]
    return [{
      'record_id':str(r.get('cveID') or digest(r)[:16]),
      'a':'vendor='+stable(r.get('vendorProject')),'b':'product='+stable(r.get('product')),
      'c':'date_added='+stable(r.get('dateAdded')),'d':'ransomware_use='+stable(r.get('knownRansomwareCampaignUse'))
    } for r in data]

def extract_fda(obj):
    rows=[]
    for r in (obj.get('results') or [])[:20]:
        if not isinstance(r,dict):continue
        rid=str(r.get('event_id') or r.get('recall_number') or digest(r)[:16])
        rows.append({
          'record_id':rid,
          'a':'classification='+stable(r.get('classification')),
          'b':'status='+stable(r.get('status')),
          'c':'country='+stable(r.get('country')),
          'd':'reason='+stable(r.get('reason_for_recall')),
        })
    return rows

def extract_usgs_rows(obj):
    rows=[]
    for f in (obj.get('features') or [])[:20]:
        p=f.get('properties') or {};g=f.get('geometry') or {}
        rows.append({
          'record_id':str(f.get('id') or digest(f)[:16]),
          'a':'magnitude='+stable(p.get('mag')),'b':'place='+stable(p.get('place')),
          'c':'time='+stable(p.get('time')),'d':'coordinates='+stable(g.get('coordinates'))
        })
    return rows

real_rows={
  'GEOSCIENCE_USGS_NEW':extract_usgs_rows(sources['USGS_WEEK']['json']),
  'ECONOMICS_WORLDBANK_NEW_QUERY':extract_worldbank(sources['WORLDBANK_GDP']['json']),
  'CYBERSECURITY_CISA_HISTORICAL_SLICE':extract_cisa(sources['CISA_KEV']['json']),
  'MEDICINE_OPENFDA_ENFORCEMENT_NEW_ENDPOINT':extract_fda(sources['OPENFDA_ENFORCEMENT']['json']),
}

tri=G2AllExperienceTriOrganRuntimeV1(tri_art)
def closure_truth(edges,start):
    state={start}
    for _ in range(64):
        nxt=state|{b for a,b in edges if a in state}
        if nxt==state:break
        state=nxt
    return tuple(sorted(state,key=lambda x:(str(type(x)),str(x))))

def relation_case(domain,row):
    t=digest([domain,row])[:16]
    n=[f'{domain}::{t}::{k}' for k in ('SOURCE','RECORD','A','B','C','D','INTEGRATED')]
    q=[f'{domain}::{t}::DISTRACTOR::{i}' for i in range(4)]
    edges=[(n[0],n[1]),(n[1],n[2]),(n[2],n[3]),(n[3],n[4]),(n[4],n[5]),(n[5],n[6]),(n[1],n[4]),(q[0],q[1]),(q[1],q[2]),(q[2],q[3])]
    return {'relation':edges,'start':n[0],'expected':closure_truth(edges,n[0])}

def event_cases(domain,row):
    t=digest([domain,row])[:16];keys=[f'{domain}:{t}:{x}' for x in ('A','B','C','D')]
    return [
      {'events':[('Q',k) for k in keys]+[('R',k) for k in reversed(keys)],'expected':True},
      {'events':[('Q',keys[0]),('Q',keys[1]),('R',keys[0]),('R',keys[1])],'expected':False},
      {'events':[('R',keys[0])],'expected':False},
      {'events':[('Q',keys[0]),('Q',keys[1]),('R',keys[1])],'expected':False},
    ]

domain_results={}
for domain,rows in real_rows.items():
    if len(rows)<6:raise RuntimeError('DOMAIN_TOO_FEW_ROWS:'+domain+':'+str(len(rows)))
    rel=[relation_case(domain,r) for r in rows[:12]]
    evt=[e for r in rows[:12] for e in event_cases(domain,r)]
    la=[tri.logic(c['relation'],c['start'])['result']==c['expected'] for c in rel]
    ta=[tri.thinking(c['events'])['result'] is c['expected'] for c in evt]
    ia=[]
    for c in rel:
        z=tri.intelligence({'input_contract':'RELATION_START_TO_STATE','relation':c['relation'],'start':c['start']})
        ia.append(z['status']=='PASS_TRI_ORGAN_INTELLIGENCE_ROUTE' and z['result']==c['expected'])
    for c in evt[:12]:
        z=tri.intelligence({'input_contract':'EVENT_SEQUENCE_TO_BOOLEAN','events':c['events']})
        ia.append(z['status']=='PASS_TRI_ORGAN_INTELLIGENCE_ROUTE' and z['result'] is c['expected'])
    lacc=sum(la)/len(la);tacc=sum(ta)/len(ta);iacc=sum(ia)/len(ia)
    labl=max((sum(GenericRelationalMetaLanguageV1.execute(a['program'],c['relation'],c['start'])==c['expected'] for c in rel)/len(rel) for a in GenericRelationalMetaLanguageV1.ablations(tri.logic_program)),default=0.0)
    tabl=max((sum(GenericEventStateMetaLanguageV1.execute(a['program'],c['events']) is c['expected'] for c in evt)/len(evt) for a in GenericEventStateMetaLanguageV1.ablations(tri.thinking_program)),default=0.0)
    domain_results[domain]={
      'record_count':len(rows),'relation_cases':len(rel),'event_cases':len(evt),
      'logic_accuracy':lacc,'thinking_accuracy':tacc,'intelligence_route_accuracy':iacc,
      'logic_best_ablation':labl,'logic_causal_drop':lacc-labl,
      'thinking_best_ablation':tabl,'thinking_causal_drop':tacc-tabl,
      'sample_record_ids':[r['record_id'] for r in rows[:4]],
    }

# Cognitive workspace integrates observed organ states but does not alter the specialists.
composition=[]
for domain,r in domain_results.items():
    sig={
      'logic_accept':r['logic_accuracy']==1.0,
      'thinking_cautious':r['thinking_causal_drop']<.50,
      'intelligence_robust':r['intelligence_route_accuracy']==1.0,
    }
    out=layer.compose(sig)
    composition.append({'domain':domain,'signals':sig,'decision':out.get('decision'),'gate':out.get('gate')})
composition_pass=all(x['gate']=='SPECIALIST_PASS_THROUGH' and x['decision'] in {'VERIFY','ACT_WITH_GUARD','ACT','REPLAN','WITHHOLD'} for x in composition)

old_worldbank=((old_four.get('source_meta') or {}).get('ECONOMICS_WORLDBANK') or {}).get('requested_url')
old_fda=((old_four.get('source_meta') or {}).get('MEDICINE_OPENFDA') or {}).get('requested_url')
checks={
  'current_usgs_week_source_changed_since_prior_stress':frozen_usgs_portability['source_changed'],
  'legacy_usgs_raw_portability_gap_detected':frozen_usgs_portability['raw_portability_status'].startswith('WITHHOLD_RAW_PORTABILITY'),
  'portable_usgs_candidate_shadow_ready':portable_candidate['status']=='SHADOW_READY',
  'portable_usgs_newer_blind_ge_0_90':portable_blind>=.90,
  'portable_usgs_gain_ge_0_25':portable_drop>=.25,
  'portable_usgs_preprocessing_bound':bool(portable_candidate.get('feature_transform')),
  'github_post_training_runs_ge_12':len(runs)>=12,
  'github_post_training_has_both_classes':all(class_counts[k]>=2 for k in ('success','failure')),
  'github_frozen_thinking_temporal_accuracy_ge_0_95':github_temporal_accuracy>=.95,
  'worldbank_query_new':WORLDBANK!=old_worldbank,
  'openfda_endpoint_new':OPENFDA!=old_fda,
  'four_new_domain_transfers':len(domain_results)==4,
  'all_domain_logic_exact':all(v['logic_accuracy']==1.0 for v in domain_results.values()),
  'all_domain_thinking_exact':all(v['thinking_accuracy']==1.0 for v in domain_results.values()),
  'all_domain_intelligence_exact':all(v['intelligence_route_accuracy']==1.0 for v in domain_results.values()),
  'all_domain_logic_causal_drop_ge_0_20':all(v['logic_causal_drop']>=.20 for v in domain_results.values()),
  'all_domain_thinking_causal_drop_ge_0_10':all(v['thinking_causal_drop']>=.10 for v in domain_results.values()),
  'cognitive_workspace_composition_pass':composition_pass,
  'canonical_head_unchanged':load(HEAD).get('canonical_head_digest')==head_before.get('canonical_head_digest'),
  'canonical_core_unchanged':load(CORE)==core_before,
  'active_capabilities_31':len(load(HEAD).get('active_capabilities',[]))==31,
  'frontier_unchanged':load(HEAD).get('current_frontier')==req.get('expected_frontier'),
  'g3_not_started':load(HEAD).get('g3_genesis_performed') is False,
  'automatic_canonical_promotion_false':portable_candidate['automatic_canonical_promotion'] is False,
}
passed=all(checks.values())
status='PASS_WITH_LIMITATIONS_SHADOW_G2_FRESH_REAL_DATA_COGNITIVE_TRANSFER_V1' if passed else 'WITHHOLD_G2_FRESH_REAL_DATA_COGNITIVE_TRANSFER_V1'

# Strip fetched JSON bodies from receipt while preserving hashes and identities.
source_meta={k:{kk:vv for kk,vv in v.items() if kk!='json'} for k,v in sources.items()}
receipt={
  'schema':'yado.g2.fresh_real_data_cognitive_transfer.receipt.v1',
  'status':status,
  'generation':head.get('generation_id'),
  'frontier':head.get('current_frontier'),
  'canonical_head_digest':head.get('canonical_head_digest'),
  'active_capability_count':len(head.get('active_capabilities',[])),
  'sources':source_meta,
  'frozen_usgs_portability':frozen_usgs_portability,
  'portable_usgs_shadow_repair':{
    'candidate_path':'candidates/kernel-self-generated/g2-portable-usgs-real-data-specialist-repair-v1.json',
    'candidate_digest':portable_candidate['candidate_digest'],
    'validation_balanced':val_acc,'newer_blind_balanced':portable_blind,
    'ablation_balanced':portable_ablation,'causal_gain':portable_drop,
    'feature_transform_bound':True,'automatic_canonical_promotion':False,
  },
  'github_temporal_transfer':{
    'training_commit_time':train_commit_time,'post_training_run_count':len(runs),
    'class_counts':class_counts,'accuracy':github_temporal_accuracy,
  },
  'domain_results':domain_results,
  'cognitive_composition':composition,
  'checks':checks,
  'canonical_mutation':False,
  'retraining_of_canonical_components':False,
  'promotion_applied':False,
  'generation_transition':False,
  'g3_genesis_performed':False,
  'next_required_capability':'G2_PORTABLE_REAL_DATA_SPECIALIST_FRESH_READMISSION_V2' if passed else 'G2_FRESH_REAL_DATA_TRANSFER_DEFICIT_REPAIR_V2',
  'limitations':[
    'LEGACY_USGS_SPECIALIST_CANNOT_BE REPRODUCED FROM RAW USGS DATA BECAUSE TRAIN-DERIVED mag_q75 PREPROCESSING VALUE WAS NOT BOUND INTO ITS CANONICAL ARTIFACT.',
    'GENERIC TRI-ORGAN REAL-DATA TRANSFER TESTS STRUCTURAL RELATION/EVENT REASONING OVER REAL RECORD CONTENT; IT DOES NOT CLAIM FULL SEMANTIC UNDERSTANDING OF EACH DOMAIN.',
  ],
  'semantic_boundary':'LIVE PUBLIC DATA TRANSFER TEST. FROZEN GITHUB THINKING IS TESTED ON POST-TRAINING RUNS. FOUR REAL DATA DOMAINS EXERCISE FROZEN TRI-ORGAN GENERIC MECHANISMS. A PORTABLE USGS SHADOW REPAIR BINDS TRAIN-DERIVED PREPROCESSING EXPLICITLY AND IS TESTED ON NEWER TEMPORAL HOLDOUT. NO CANONICAL PROMOTION OR G3 TRANSITION.',
}
receipt['receipt_sha256']=digest(receipt)
OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps(receipt,indent=2,sort_keys=True,default=str))
