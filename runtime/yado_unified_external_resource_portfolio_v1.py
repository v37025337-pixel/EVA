from __future__ import annotations
from pathlib import Path
import copy, hashlib, json, os, re, sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

SEED=REPO/'resources'/'yado-unified-external-resource-seed-v1.json'
FREE=REPO/'receipts'/'yado-free-for-dev-capability-scout-v1-latest.json'
CONSC=REPO/'receipts'/'yado-rc8-v36-consciousness-theory-research-latest.json'
ARCH=REPO/'receipts'/'yado-shadow-meta-architecture-study-v1-latest.json'
OLD_BUDGET=REPO/'receipts'/'yado-budget-aware-sequence-transform-v1-latest.json'
BUDGET_GATE=REPO/'receipts'/'yado-experiment-compute-budget-gate-v1-latest.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
HEAD=REPO/'canonical'/'yado-main-head-g1-s2.json'
OUT=REPO/'resources'
OUT.mkdir(exist_ok=True)

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o): return hashlib.sha256(canon(o).encode()).hexdigest()

seed=json.loads(SEED.read_text())
free=json.loads(FREE.read_text())
consc=json.loads(CONSC.read_text())
arch=json.loads(ARCH.read_text())
old_budget=json.loads(OLD_BUDGET.read_text())
budget_gate=json.loads(BUDGET_GATE.read_text())
ledger=json.loads(LEDGER.read_text())
head=json.loads(HEAD.read_text())
validate_ledger_v2(ledger)
if ledger['current_head']!='G1_CANDIDATE_S2':
    raise RuntimeError('EXPECTED_G1_CURRENT_HEAD')
if head.get('canonical_head_digest')!=ledger.get('current_head_digest'):
    raise RuntimeError('HEAD_DIGEST_MISMATCH')

records={}
def key_for(r):
    loc=str(r.get('locator') or r.get('url') or r.get('name') or r.get('id')).strip()
    return loc.lower()

def add(r,source,verified=False):
    x=copy.deepcopy(r)
    x.setdefault('capabilities',[])
    x.setdefault('policy','ELIGIBLE')
    x.setdefault('kind','unknown')
    x.setdefault('provenance',source)
    x['evidence_sources']=sorted(set(list(x.get('evidence_sources',[]))+[source]))
    if verified:
        x['verification_state']='VERIFIED_REPO_EVIDENCE'
    else:
        x.setdefault('verification_state','PRIOR_REFERENCE_NOT_LIVE_REVERIFIED')
    k=key_for(x)
    if k in records:
        old=records[k]
        old['capabilities']=sorted(set(old.get('capabilities',[])+x.get('capabilities',[])))
        old['evidence_sources']=sorted(set(old.get('evidence_sources',[])+x.get('evidence_sources',[])))
        if verified: old['verification_state']='VERIFIED_REPO_EVIDENCE'
        if old.get('policy')!='EXCLUDED_DURABLE_IDENTITY_RECOVERY':
            old['policy']=x.get('policy',old.get('policy','ELIGIBLE'))
    else:
        records[k]=x

for r in seed['resources']:
    add(r,'resources/yado-unified-external-resource-seed-v1.json',False)

# Upgrade exact arXiv records already fetched by YADO.
for receipt_name,receipt in [
    ('receipts/yado-rc8-v36-consciousness-theory-research-latest.json',consc),
    ('receipts/yado-shadow-meta-architecture-study-v1-latest.json',arch),
]:
    for s in receipt.get('sources',[]):
        add({
          'id':s.get('id'),
          'kind':'research_paper',
          'locator':s.get('url'),
          'capabilities':['RESEARCH_EVIDENCE','ARCHITECTURE_RESEARCH'],
          'content_sha256':s.get('sha256'),
          'text_chars':s.get('text_chars'),
          'policy':'ELIGIBLE',
        },receipt_name,True)

# First-class local developmental evidence. These are always cheaper and more causally
# relevant than going back to the network for a problem YADO has already observed.
for local in [
    {
      'id':'LOCAL_EVOLUTION_LEDGER',
      'kind':'local_evidence',
      'locator':'architecture/evolution-ledger.json',
      'capabilities':['CAUSAL_LINEAGE','COUNTEREXAMPLE_HISTORY','DEVELOPMENTAL_STATE'],
      'description':'Append-only causal history including PASS/WITHHOLD and generation transitions.',
    },
    {
      'id':'LOCAL_BUDGET_SEQUENCE_WITHHOLD',
      'kind':'local_evidence',
      'locator':'receipts/yado-budget-aware-sequence-transform-v1-latest.json',
      'capabilities':['BUDGET_AWARE_SEARCH','COUNTEREXAMPLE_HISTORY','SEQUENCE_TRANSFORMATION'],
      'description':'Historical budget-aware sequence transform WITHHOLD; fresh exact 0.25.',
      'content_sha256':old_budget.get('receipt_sha256'),
    },
    {
      'id':'LOCAL_COMPUTE_BUDGET_GATE',
      'kind':'local_evidence',
      'locator':'receipts/yado-experiment-compute-budget-gate-v1-latest.json',
      'capabilities':['BUDGET_AWARE_SEARCH','RESOURCE_LIMITS','TIMEOUT_CONTROL'],
      'description':'Observed over-budget experiment cancellations and budget semantics.',
    },
    {
      'id':'LOCAL_ACCESS_CONTROL_REPAIR_LINEAGE',
      'kind':'local_evidence',
      'locator':'receipts/yado-g1-external-resource-assisted-access-control-repair-v1-run-33348693351.json',
      'capabilities':['COUNTEREXAMPLE_LEARNING','RESOURCE_ASSISTED_ALGORITHM_GENESIS'],
      'description':'Successful resource-assisted algorithm genesis after preserved WITHHOLD attempts.',
    },
]:
    add(local,local['locator'],True)

# Add all concrete free-for-dev choices, retaining cost/quota text as pinned catalog evidence.
for deficit,arr in free.get('selected_resources',{}).items():
    for item in arr:
        caps=['RESOURCE_DISCOVERY']
        if 'BUDGET' in deficit:
            caps+=['COST_QUOTA_AWARENESS','BUDGET_AWARE_SEARCH']
        if 'ACCESS_CONTROL' in deficit:
            caps+=['AUTHORIZATION_POLICY','ACCESS_CONTROL']
        add({
          'id':'FREEDEV_'+re.sub(r'[^A-Z0-9]+','_',item['name'].upper()).strip('_'),
          'name':item['name'],
          'kind':'service_or_tool',
          'locator':item['url'],
          'description':item.get('description',''),
          'access_class':item.get('access_class'),
          'capabilities':caps,
          'policy':'ELIGIBLE',
        },'receipts/yado-free-for-dev-capability-scout-v1-latest.json',True)

def access_tier(r):
    if r.get('policy','').startswith('EXCLUDED'): return 99
    if r.get('kind')=='local_evidence' and r.get('verification_state')=='VERIFIED_REPO_EVIDENCE': return 0
    if r.get('verification_state')=='VERIFIED_REPO_EVIDENCE' and r.get('kind')=='research_paper': return 0
    k=r.get('kind','')
    ac=str(r.get('access_class',''))
    if k in ('code_repository','documentation','catalog') and r.get('verification_state')=='VERIFIED_REPO_EVIDENCE': return 0
    if k in ('documentation','research_paper','code_repository','catalog','code_platform','api_catalog'): return 1
    if ac=='PUBLIC_OR_NO_ACCOUNT_CANDIDATE': return 1
    if k in ('research_tool','developer_tool','search_tool','security_tool','knowledge_tool'): return 2
    if 'REQUIRES_PROVIDER_VALIDATION_OR_ACCOUNT' in ac or 'FREE_ACCOUNT' in ac: return 3
    if k in ('deployment','workspace_reference'): return 3
    return 2

def estimated_cost(tier):
    return {0:0.05,1:0.2,2:0.7,3:2.0,99:999.0}[tier]

def score_for(deficit,r):
    if r.get('policy','').startswith('EXCLUDED'): return -999.0
    txt=' '.join([
      str(r.get('id','')),str(r.get('name','')),str(r.get('kind','')),
      str(r.get('description','')),' '.join(r.get('capabilities',[]))
    ]).upper()
    score=0.0
    if 'BUDGET' in deficit:
        for token,w in {
          'BUDGET':6,'COST':5,'QUOTA':5,'FREE':1.5,'SEARCH':2.5,'API':1,
          'OBSERV':1.5,'RESOURCE':1.5,'CI':1,'SERVERLESS':1,'CREDIT':1.5
        }.items():
            if token in txt: score+=w
    elif 'ACCESS_CONTROL' in deficit:
        for token,w in {'AUTHORIZATION':6,'ACCESS_CONTROL':6,'RBAC':5,'ABAC':5,'REBAC':5,'POLICY':3,'IDENTITY':2}.items():
            if token in txt: score+=w
    else:
        for token,w in {
          'RESEARCH':2,'ARCHITECTURE':2,'PROGRAMMING':2,'DATASET':2,'EVIDENCE':2,
          'WORLD_MODEL':2,'LOGIC':2,'REPOSITORY':1,'CODE':1
        }.items():
            if token in txt: score+=w
    if r.get('verification_state')=='VERIFIED_REPO_EVIDENCE': score+=2
    if r.get('kind')=='local_evidence': score+=8
    score-=estimated_cost(access_tier(r))*0.4
    return round(score,3)

items=[]
for r in records.values():
    x=copy.deepcopy(r)
    x['access_tier']=access_tier(x)
    x['estimated_access_cost']=estimated_cost(x['access_tier'])
    items.append(x)
items.sort(key=lambda r:(r['access_tier'],str(r.get('id',''))))

open_deficits=ledger.get('open_deficits',[])
routes={}
for deficit in open_deficits:
    ranked=[]
    for r in items:
        s=score_for(deficit,r)
        if s<=0: continue
        ranked.append((s,r['access_tier'],str(r.get('id','')),r))
    ranked.sort(key=lambda z:(z[1],-z[0],z[2]))
    chosen=[]
    kind_counts={}
    for s,t,_,r in ranked:
        kind=r.get('kind','unknown')
        if kind_counts.get(kind,0)>=3: continue
        chosen.append({
          'resource_id':r.get('id'),
          'locator':r.get('locator'),
          'kind':kind,
          'access_tier':t,
          'estimated_access_cost':r['estimated_access_cost'],
          'score':s,
          'verification_state':r.get('verification_state'),
          'policy':r.get('policy'),
        })
        kind_counts[kind]=kind_counts.get(kind,0)+1
        if len(chosen)>=12: break
    routes[deficit]=chosen

stats={
 'total_unique_resources':len(items),
 'verified_repo_evidence':sum(r.get('verification_state')=='VERIFIED_REPO_EVIDENCE' for r in items),
 'prior_reference_not_live_reverified':sum(r.get('verification_state')=='PRIOR_REFERENCE_NOT_LIVE_REVERIFIED' for r in items),
 'excluded':sum(r.get('policy','').startswith('EXCLUDED') for r in items),
 'research_papers':sum(r.get('kind')=='research_paper' for r in items),
 'concrete_free_for_dev_entries':sum('receipts/yado-free-for-dev-capability-scout-v1-latest.json' in r.get('evidence_sources',[]) and r.get('kind')=='service_or_tool' for r in items),
}

portfolio={
 'schema':'yado.unified_external_resource_portfolio.v1',
 'generation':ledger['current_head'],
 'generation_head_digest':ledger['current_head_digest'],
 'resource_count':len(items),
 'stats':stats,
 'routing_policy':{
   'priority':['LOCAL_VERIFIED_EVIDENCE','PINNED_PUBLIC_DOCS_AND_RESEARCH','PUBLIC_TOOLS','ACCOUNT_OR_KEY_REQUIRED'],
   'excluded_policy':'NEVER_AUTO_SELECT_EXCLUDED_RESOURCES',
   'no_auto_signup':True,
   'no_secret_transmission':True,
   'selection_rule':'MAXIMIZE_DEFICIT_RELEVANCE_MINUS_ACCESS_COST_WITH_KIND_DIVERSITY',
 },
 'resources':items,
 'routes_for_current_open_deficits':routes,
}
portfolio['portfolio_digest']=h(portfolio)
(OUT/'yado-unified-external-resource-portfolio-v1.json').write_text(json.dumps(portfolio,indent=2,sort_keys=True)+'\n')

report={
 'schema':'yado.unified_external_resource_portfolio.receipt.v1',
 'status':'PASS_UNIFIED_EXTERNAL_RESOURCE_PORTFOLIO_V1',
 'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),
 'generation':ledger['current_head'],'generation_head_digest':ledger['current_head_digest'],
 'stats':stats,
 'open_deficits':open_deficits,
 'route_sizes':{k:len(v) for k,v in routes.items()},
 'portfolio_digest':portfolio['portfolio_digest'],
 'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'G1_BUDGET_AWARE_SEARCH_REPAIR_V1',
 'semantic_boundary':'PORTFOLIO INDEXES ALL RECOVERABLE PRIOR RESOURCES. PRIOR-SESSION REFERENCES ARE NOT TREATED AS CURRENTLY VERIFIED UNTIL LIVE RECHECKED. EXCLUDED TEMPORARY SERVICES ARE NEVER AUTO-SELECTED.'
}
report['receipt_sha256']=h(report)
(ROOT/'yado_unified_external_resource_portfolio_v1_receipt.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')

e={
 'index':len(ledger['events']),
 'event_id':f"E{len(ledger['events'])+1:04d}_G1_UNIFIED_EXTERNAL_RESOURCE_PORTFOLIO",
 'event_type':'RESOURCE_INTELLIGENCE_PORTFOLIO',
 'status':'PASS',
 'generation':ledger['current_head'],
 'deficit':'FRAGMENTED_EXTERNAL_RESOURCE_MEMORY',
 'effect':'ALL_RECOVERABLE_PRIOR_RESOURCES_UNIFIED_AND_ROUTED_BY_DEFICIT_COST_ACCESS_AND_EVIDENCE_STATE',
 'source_path':f"receipts/yado-unified-external-resource-portfolio-v1-run-{os.getenv('GITHUB_RUN_ID') or 'LOCAL'}.json",
 'source_digest':report['receipt_sha256'],
 'run_id':str(os.getenv('GITHUB_RUN_ID') or 'LOCAL'),
 'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'promotion_applied':False,
}
e['event_hash']=event_hash(e)
ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['resolved_deficits']=sorted(set(ledger.get('resolved_deficits',[])+['FRAGMENTED_EXTERNAL_RESOURCE_MEMORY']))
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger)
LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({
 'status':report['status'],
 'stats':stats,
 'route_sizes':report['route_sizes'],
 'next_required_capability':report['next_required_capability'],
 'portfolio_digest':portfolio['portfolio_digest'],
 'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True))
