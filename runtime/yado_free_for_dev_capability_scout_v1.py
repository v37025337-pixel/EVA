from __future__ import annotations
from pathlib import Path
import copy, hashlib, json, os, re, ssl, urllib.request, urllib.error, sys

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

LEDGER=ROOT.parent/'architecture'/'evolution-ledger.json'
HEAD=ROOT.parent/'canonical'/'yado-main-head-g1-s2.json'
OUT=ROOT/'free_for_dev_capability_scout_v1'
OUT.mkdir(exist_ok=True)

SOURCE_REPO='ripienaar/free-for-dev'
SOURCE_COMMIT='40b332b89c287b0d201eb02a8e5fdd5b34fa6292'
EXPECTED_README_BLOB='fde554cf899815faf7d5c258e96ce12a17a0ccdb'
RAW=f'https://raw.githubusercontent.com/{SOURCE_REPO}/{SOURCE_COMMIT}/README.md'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def git_blob_sha(text):
    b=text.encode()
    return hashlib.sha1(f'blob {len(b)}\0'.encode()+b).hexdigest()

ledger=json.loads(LEDGER.read_text()); head=json.loads(HEAD.read_text())
v=validate_ledger_v2(ledger)
if v['current_head']!='G1_CANDIDATE_S2':raise RuntimeError('G1_NOT_CURRENT_HEAD')
if head.get('status')!='HEAD' or head.get('canonical_head_digest')!=ledger.get('current_head_digest'):
    raise RuntimeError('CANONICAL_HEAD_ARTIFACT_MISMATCH')

req=urllib.request.Request(RAW,headers={'User-Agent':'YADO-FreeForDev-Scout/1.0'})
with urllib.request.urlopen(req,timeout=20) as r:
    text=r.read().decode('utf-8','replace')
blob=git_blob_sha(text)
if blob!=EXPECTED_README_BLOB:
    raise RuntimeError(f'PINNED_README_BLOB_MISMATCH:{blob}')

entries=[];category=''
for line in text.splitlines():
    hm=re.match(r'^##\s+(.+)$',line)
    if hm:
        category=hm.group(1).strip();continue
    m=re.match(r'^\s*[*-]\s+\[([^\]]+)\]\((https?://[^)]+)\)\s*(?:-\s*)?(.*)$',line)
    if m:
        entries.append({'category':category,'name':m.group(1).strip(),'url':m.group(2).strip(),'description':m.group(3).strip()})

def score_entry(e,deficit):
    s=0.0
    cat=e['category'].lower();txt=(e['name']+' '+e['description']).lower()
    if deficit=='ACCESS_CONTROL_HIGHER_EXPRESSIVENESS_COUNTEREXAMPLE':
        if e['category']=='Authentication, Authorization, and User Management':s+=6
        if e['category']=='Security and PKI':s+=2
        kws={'authorization':3,'access control':3,'rbac':4,'abac':4,'rebac':5,'policy':3,'permission':3,'identity':1.5,'authz':3,'fine-grained':4}
    else:
        if e['category'] in {'Cloud management solutions','CI and CD','Monitoring','APIs, Data, and ML','PaaS','IaaS','Major Cloud Providers'}:s+=2
        kws={'cost':4,'budget':4,'free tier':2,'requests':1,'monitor':2,'observability':2,'search':2,'api':1,'pipeline':1.5,'resource':1.5,'rate limit':2,'credits':1.5,'serverless':1.5}
    for k,w in kws.items():
        if k in txt:s+=w
    if 'no card required' in txt or 'no credit card' in txt:s+=1
    if 'open-source' in txt or 'open source' in txt:s+=.7
    if 'credit card required' in txt:s-=1.5
    if 'possibly taken down' in txt:s-=5
    return round(s,3)

def shortlist(deficit,n=8):
    scored=[]
    for e in entries:
        s=score_entry(e,deficit)
        if s>0:scored.append((s,e['name'].lower(),e))
    scored.sort(key=lambda z:(-z[0],z[1]))
    return [dict(x[2],score=x[0]) for x in scored[:n]]

def probe(url):
    # Public reachability only. No signup, no credentials, no POST.
    try:
        q=urllib.request.Request(url,headers={'User-Agent':'YADO-Resource-Probe/1.0','Accept':'text/html,*/*'})
        with urllib.request.urlopen(q,timeout=7,context=ssl.create_default_context()) as r:
            return {'reachable':True,'http_status':getattr(r,'status',None),'final_url':r.geturl()}
    except urllib.error.HTTPError as e:
        return {'reachable':e.code<500,'http_status':e.code,'final_url':e.geturl()}
    except Exception as e:
        return {'reachable':False,'error_type':type(e).__name__}

def classify(e):
    t=(e['description']+' '+e['name']).lower()
    if 'no account' in t or 'without signup' in t or 'no api key required' in t:
        return 'PUBLIC_OR_NO_ACCOUNT_CANDIDATE'
    if 'no card required' in t or 'no credit card' in t:
        return 'FREE_ACCOUNT_OR_KEY_LIKELY'
    if 'api' in t or 'free tier' in t or 'free plan' in t:
        return 'REQUIRES_PROVIDER_VALIDATION_OR_ACCOUNT'
    return 'RESEARCH_REFERENCE'

deficits=[
 'ACCESS_CONTROL_HIGHER_EXPRESSIVENESS_COUNTEREXAMPLE',
 'BUDGET_AWARE_SEARCH_AND_STAGED_ESCALATION',
]
selected={}
for d in deficits:
    arr=shortlist(d)
    for x in arr:
        x['access_class']=classify(x)
    selected[d]=arr

# Probe only top four per deficit to keep network use bounded.
probes={}
for d,arr in selected.items():
    for e in arr[:4]:
        key=e['name']
        if key not in probes:probes[key]=probe(e['url'])

# Derive mechanism hypotheses from evidence characteristics, not brand names.
access_text=' '.join((e['name']+' '+e['description']).lower() for e in selected[deficits[0]])
mechanism_hypotheses=[]
if all(k in access_text for k in ('rbac','abac','rebac')):
    mechanism_hypotheses.append({
      'deficit':deficits[0],
      'hypothesis':'CURRENT_CONJUNCTIVE_POLICY_FAMILY_IS_TOO_NARROW; ADD_BOUNDED_DISJUNCTIVE_AND_RELATIONAL_POLICY_COMPOSITION',
      'candidate_algorithm_family':'BOUNDED_DNF_PLUS_RELATION_POLICY_INDUCTION',
      'evidence_terms':['RBAC','ABAC','ReBAC'],
    })
budget_text=' '.join((e['name']+' '+e['description']).lower() for e in selected[deficits[1]])
if 'cost' in budget_text and ('free tier' in budget_text or 'credits' in budget_text):
    mechanism_hypotheses.append({
      'deficit':deficits[1],
      'hypothesis':'SEARCH_SHOULD_MODEL_RESOURCE_COST_AND_QUOTA_AS_FIRST_CLASS_STATE_AND_ESCALATE_ONLY_AFTER_CHEAPER_STAGE_FAILS',
      'candidate_algorithm_family':'BUDGETED_STAGE_POLICY',
      'evidence_terms':['cost','quota/free-tier','staged execution'],
    })

source={
 'schema':'yado.external_resource_source.v1',
 'source_repo':SOURCE_REPO,'source_commit':SOURCE_COMMIT,'readme_git_blob_sha1':blob,
 'readme_sha256':hashlib.sha256(text.encode()).hexdigest(),
 'entry_count':len(entries),'category_count':len(set(e['category'] for e in entries)),
 'retrieval_mode':'PINNED_PUBLIC_GITHUB_RAW_READ_ONLY',
}
source['source_digest']=h(source)
(ROOT.parent/'resources').mkdir(exist_ok=True)
(ROOT.parent/'resources'/'free-for-dev-source-v1.json').write_text(json.dumps(source,indent=2,sort_keys=True)+'\n')

report={
 'schema':'yado.free_for_dev.capability_scout.v1',
 'status':'PASS_FREE_FOR_DEV_CAPABILITY_SCOUT_V1',
 'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),
 'generation':ledger['current_head'],'generation_head_digest':ledger['current_head_digest'],
 'source':source,'open_deficits_scoped':deficits,
 'selected_resources':selected,'public_reachability_probes':probes,
 'mechanism_hypotheses':mechanism_hypotheses,
 'selection_policy':'RANK BY DEFICIT/CATEGORY/TEXT MATCH; FAVOR FREE/NO-CARD/OPEN-SOURCE; PENALIZE CARD-REQUIRED OR STALE; DO NOT AUTO-SIGNUP OR TRANSMIT SECRETS',
 'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'G1_EXTERNAL_RESOURCE_ASSISTED_ACCESS_CONTROL_REPAIR_V1',
 'semantic_boundary':'FREE-FOR-DEV IS USED AS A RESOURCE DISCOVERY CATALOG. LISTING DOES NOT PROVE CURRENT TERMS, SECURITY, OR SUITABILITY; PROVIDER USE REQUIRES LIVE VALIDATION AND ANY REQUIRED USER AUTHORIZATION',
}
report['receipt_sha256']=h(report)
(ROOT/'yado_free_for_dev_capability_scout_v1_receipt.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
(ROOT.parent/'resources'/'free-for-dev-selected-v1.json').write_text(json.dumps({
 'source_digest':source['source_digest'],'generation':ledger['current_head'],'selected_resources':selected,
 'mechanism_hypotheses':mechanism_hypotheses
},indent=2,sort_keys=True)+'\n')

e={
 'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G1_FREE_FOR_DEV_RESOURCE_SCOUT",
 'event_type':'EXTERNAL_RESOURCE_CATALOG_INGESTION','status':'PASS','generation':ledger['current_head'],
 'deficit':'EXTERNAL_RESOURCE_DISCOVERY_FOR_OPEN_CAPABILITY_GAPS',
 'effect':'PINNED_FREE_FOR_DEV_CATALOG_SCOUTED; ACCESS_CONTROL_AND_BUDGETED_SEARCH_MECHANISM_HYPOTHESES_CREATED',
 'source_path':'receipts/yado-free-for-dev-capability-scout-v1-latest.json','source_digest':report['receipt_sha256'],
 'run_id':str(os.getenv('GITHUB_RUN_ID') or 'LOCAL'),'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'promotion_applied':False,
}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=sorted(set(ledger.get('open_deficits',[])+['G1_EXTERNAL_RESOURCE_ASSISTED_ACCESS_CONTROL_REPAIR_V1']))
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger)
LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({
 'status':report['status'],'source_commit':SOURCE_COMMIT,'entry_count':len(entries),
 'access_top':[x['name'] for x in selected[deficits[0]][:5]],
 'budget_top':[x['name'] for x in selected[deficits[1]][:5]],
 'mechanism_hypotheses':[x['candidate_algorithm_family'] for x in mechanism_hypotheses],
 'next_required_capability':report['next_required_capability'],
 'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True))
