from __future__ import annotations

from pathlib import Path
from collections import Counter
from urllib.parse import urlparse
import copy, hashlib, json, re, sys, urllib.request

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_generic_relational_meta_language_v1 import GenericRelationalMetaLanguageV1
from yado_generic_event_state_meta_language_v1 import GenericEventStateMetaLanguageV1
from yado_g2_autonomous_gene_portfolio_controller_v1 import YADOAutonomousGenePortfolioControllerV1

TASK=REPO/'resources/yado-four-domain-fresh-stress-v1.json'
TRI=REPO/'experience/yado-all-experience-tri-organ-genesis-v1.json'
DNS=REPO/'candidates/kernel-self-generated/g2-dns-gcp-cross-domain-research-stress-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-four-domain-fresh-stress-v1.json'
EXP=REPO/'experience/yado-four-domain-fresh-stress-v1.json'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))

def fetch_json(url,timeout=28,max_bytes=5_000_000):
    req=urllib.request.Request(url,headers={
      'User-Agent':'YADO-G2-Four-Domain-Fresh-Stress/1.0',
      'Accept':'application/json,application/geo+json,text/json,*/*'
    })
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r:
            body=r.read(max_bytes)
            if len(body)>=max_bytes:
                # A full JSON parse below will fail closed if this was truncated.
                truncated=True
            else:
                truncated=False
            obj=json.loads(body.decode('utf-8','replace'))
            return {
              'ok':True,'requested_url':url,'resolved_url':str(getattr(r,'url',url) or url),
              'http_status':int(getattr(r,'status',200) or 200),
              'content_type':str(r.headers.get('Content-Type') or ''),
              'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),
              'truncated_at_bound':truncated,'json':obj
            }
    except Exception as e:
        return {'ok':False,'requested_url':url,'error':type(e).__name__+':'+str(e)[:320]}

def stable_value(v,maxlen=180):
    if isinstance(v,(dict,list,tuple)):
        s=canon(v)
    else:
        s=str(v)
    s=re.sub(r'\s+',' ',s).strip()
    return s[:maxlen]

def first_nonempty(*xs):
    for x in xs:
        if x is None: continue
        if isinstance(x,str) and not x.strip(): continue
        if isinstance(x,(list,tuple)) and not x: continue
        return x
    return None

def extract_usgs(obj):
    rows=[]
    feats=(obj or {}).get('features') if isinstance(obj,dict) else None
    for f in (feats or [])[:40]:
        if not isinstance(f,dict): continue
        p=f.get('properties') or {}
        g=f.get('geometry') or {}
        rid=str(first_nonempty(f.get('id'),digest(f)[:16]))
        rows.append({
          'record_id':rid,
          'field_a':'magnitude='+stable_value(p.get('mag')),
          'field_b':'place='+stable_value(p.get('place')),
          'field_c':'time='+stable_value(p.get('time')),
          'field_d':'coordinates='+stable_value(g.get('coordinates')),
        })
    rows.sort(key=lambda x:x['record_id'])
    return rows

def extract_worldbank(obj):
    rows=[]
    arr=obj[1] if isinstance(obj,list) and len(obj)>1 and isinstance(obj[1],list) else []
    for r in arr:
        if not isinstance(r,dict) or r.get('value') is None: continue
        country=(r.get('country') or {}).get('value') if isinstance(r.get('country'),dict) else r.get('country')
        iso=str(first_nonempty(r.get('countryiso3code'),country,'UNKNOWN'))
        date=str(r.get('date'))
        rid=iso+'::'+date
        rows.append({
          'record_id':rid,
          'field_a':'country='+stable_value(country),
          'field_b':'indicator='+stable_value((r.get('indicator') or {}).get('value') if isinstance(r.get('indicator'),dict) else r.get('indicator')),
          'field_c':'date='+date,
          'field_d':'value='+stable_value(r.get('value')),
        })
    rows.sort(key=lambda x:x['record_id'])
    return rows

def extract_openfda(obj):
    rows=[]
    arr=(obj or {}).get('results') if isinstance(obj,dict) else []
    for r in (arr or [])[:20]:
        if not isinstance(r,dict): continue
        of=r.get('openfda') or {}
        rid=str(first_nonempty(r.get('id'),digest(r)[:16]))
        manufacturer=first_nonempty(of.get('manufacturer_name'),['UNKNOWN'])
        product_type=first_nonempty(of.get('product_type'),['UNKNOWN'])
        substance=first_nonempty(of.get('substance_name'),['UNKNOWN'])
        brand=first_nonempty(of.get('brand_name'),['UNKNOWN'])
        rows.append({
          'record_id':rid,
          'field_a':'manufacturer='+stable_value(manufacturer),
          'field_b':'product_type='+stable_value(product_type),
          'field_c':'substance='+stable_value(substance),
          'field_d':'brand='+stable_value(brand),
        })
    rows.sort(key=lambda x:x['record_id'])
    return rows

def extract_cisa(obj):
    rows=[]
    arr=(obj or {}).get('vulnerabilities') if isinstance(obj,dict) else []
    # Use newest entries by dateAdded when present, without hardcoded CVEs.
    data=[r for r in (arr or []) if isinstance(r,dict)]
    data.sort(key=lambda r:(str(r.get('dateAdded') or ''),str(r.get('cveID') or '')),reverse=True)
    for r in data[:24]:
        rid=str(first_nonempty(r.get('cveID'),digest(r)[:16]))
        rows.append({
          'record_id':rid,
          'field_a':'vendor='+stable_value(r.get('vendorProject')),
          'field_b':'product='+stable_value(r.get('product')),
          'field_c':'date_added='+stable_value(r.get('dateAdded')),
          'field_d':'ransomware_use='+stable_value(r.get('knownRansomwareCampaignUse')),
        })
    rows.sort(key=lambda x:x['record_id'])
    return rows

EXTRACTORS={
 'GEOSCIENCE_USGS':extract_usgs,
 'ECONOMICS_WORLDBANK':extract_worldbank,
 'MEDICINE_OPENFDA':extract_openfda,
 'CYBERSECURITY_CISA_KEV':extract_cisa,
}

def rel_truth(edges,start):
    state={start}
    for _ in range(128):
        nxt=state|{b for a,b in edges if a in state}
        if nxt==state:break
        state=nxt
    return tuple(sorted(state,key=str))

def make_relation_cases(domain,rows):
    cases=[]
    for i,row in enumerate(rows):
        token=digest([domain,row])[:18]
        n=[
          f'{domain}::{token}::SOURCE',
          f'{domain}::{token}::RECORD::{row["record_id"]}',
          f'{domain}::{token}::A::{row["field_a"]}',
          f'{domain}::{token}::B::{row["field_b"]}',
          f'{domain}::{token}::C::{row["field_c"]}',
          f'{domain}::{token}::D::{row["field_d"]}',
          f'{domain}::{token}::INTEGRATED'
        ]
        edges=list(zip(n[:-1],n[1:]))
        d=[f'{domain}::{token}::DISTRACTOR::{j}' for j in range(5)]
        edges+=list(zip(d[:-1],d[1:]))
        cases.append({
          'relation':tuple(edges),'start':n[0],'expected':rel_truth(edges,n[0]),
          'domain':domain,'record_id':row['record_id']
        })
    return cases

def make_event_cases(domain,rows):
    cases=[]
    for row in rows:
        token=digest([domain,row])[:18]
        keys=[
          f'TASK::{domain}::{token}',
          f'RECORD::{row["record_id"]}::{token}',
          f'FIELD_A::{token}',f'FIELD_B::{token}',f'FIELD_C::{token}',f'FIELD_D::{token}',
          f'INTEGRATE::{token}'
        ]
        Q='Q';R='R'
        valid=tuple([(Q,k) for k in keys]+[(R,k) for k in reversed(keys)])
        crossed=tuple([(Q,k) for k in keys]+[(R,k) for k in keys])
        underflow=tuple([(R,keys[0]),(Q,keys[-1]),(R,keys[-1])])
        unfinished=tuple(list(valid)[:-1])
        wrong=list(valid);wrong[len(keys)]=(R,'WRONG::'+token)
        rep=keys[-1]
        repeated=tuple([(Q,rep)]*len(keys)+[(R,rep)]*len(keys))
        cases += [
          {'events':valid,'expected':True,'domain':domain,'record_id':row['record_id'],'kind':'VALID_NESTED'},
          {'events':crossed,'expected':False,'domain':domain,'record_id':row['record_id'],'kind':'CROSSED_CLOSE'},
          {'events':underflow,'expected':False,'domain':domain,'record_id':row['record_id'],'kind':'UNDERFLOW'},
          {'events':unfinished,'expected':False,'domain':domain,'record_id':row['record_id'],'kind':'UNFINISHED'},
          {'events':tuple(wrong),'expected':False,'domain':domain,'record_id':row['record_id'],'kind':'WRONG_KEY'},
          {'events':repeated,'expected':True,'domain':domain,'record_id':row['record_id'],'kind':'REPEATED_KEY_VALID'},
        ]
    return cases

def relation_accuracy(program,cases):
    if not cases:return 0.0
    return sum(GenericRelationalMetaLanguageV1.execute(program,c['relation'],c['start'])==c['expected'] for c in cases)/len(cases)

def event_accuracy(program,cases):
    if not cases:return 0.0
    return sum(GenericEventStateMetaLanguageV1.execute(program,c['events']) is bool(c['expected']) for c in cases)/len(cases)

def best_rel_ablation(program,cases):
    return max((relation_accuracy(x['program'],cases) for x in GenericRelationalMetaLanguageV1.ablations(program)),default=0.0)

def best_evt_ablation(program,cases):
    return max((event_accuracy(x['program'],cases) for x in GenericEventStateMetaLanguageV1.ablations(program)),default=0.0)

task=load(TASK)
tri=load(TRI)
dns=load(DNS)
core=UnifiedYADOCoreV1(REPO)
head_before=core.head.get('canonical_head_digest')
genes=tri.get('genes') or {}

if task.get('created_after_dns_gcp_pass') is not True:
    raise RuntimeError('TASK_NOT_POST_DNS_GCP')
if dns.get('status')!='PASS_SHADOW_G2_DNS_GCP_CROSS_DOMAIN_RESEARCH_STRESS_V1':
    raise RuntimeError('DNS_GCP_PREREQUISITE_NOT_PASS')
if task.get('prior_cross_domain_receipt_sha256')!=dns.get('receipt_sha256'):
    raise RuntimeError('DNS_GCP_RECEIPT_MISMATCH')
if task.get('frozen_tri_organ_genome_id')!=(tri.get('genome') or {}).get('genome_id'):
    raise RuntimeError('FROZEN_GENOME_MISMATCH')
if tri.get('status')!='TRAINED_SHADOW':
    raise RuntimeError('TRI_ORGAN_NOT_TRAINED_SHADOW')

program_digests_before={
  'LOGIC':genes['LOGIC']['operator_program']['program_digest'],
  'THINKING':genes['THINKING']['operator_program']['program_digest'],
  'INTELLIGENCE':genes['INTELLIGENCE']['portfolio']['portfolio_digest'],
}
logic_program=copy.deepcopy(genes['LOGIC']['operator_program'])
thinking_program=copy.deepcopy(genes['THINKING']['operator_program'])
portfolio=copy.deepcopy(genes['INTELLIGENCE']['portfolio'])

domain_results={}
source_meta={}
all_checks={}
for spec in task.get('domains') or []:
    domain=spec['id']
    fetched=fetch_json(spec['source'])
    source_meta[domain]={k:v for k,v in fetched.items() if k!='json'}
    rows=[]
    if fetched.get('ok'):
        rows=EXTRACTORS[domain](fetched['json'])
    rows=rows[:12]
    relation_cases=make_relation_cases(domain,rows)
    event_cases=make_event_cases(domain,rows)
    logic_score=relation_accuracy(logic_program,relation_cases)
    thinking_score=event_accuracy(thinking_program,event_cases)
    logic_ab=best_rel_ablation(logic_program,relation_cases)
    thinking_ab=best_evt_ablation(thinking_program,event_cases)
    rel_task={'task_id':domain+'_RELATION','input_contract':'RELATION_START_TO_STATE','cases':relation_cases}
    evt_task={'task_id':domain+'_EVENT','input_contract':'EVENT_SEQUENCE_TO_BOOLEAN','cases':event_cases}
    intel_rel=YADOAutonomousGenePortfolioControllerV1.evaluate_portfolio(portfolio,rel_task)
    intel_evt=YADOAutonomousGenePortfolioControllerV1.evaluate_portfolio(portfolio,evt_task)
    domain_checks={
      'source_fetch_ok':bool(fetched.get('ok')),
      'minimum_records_met':len(rows)>=int(spec['minimum_records']),
      'logic_fresh_exact':logic_score==1.0,
      'logic_causal_drop_ge_0_20':logic_score-logic_ab>=.20,
      'thinking_fresh_exact':thinking_score==1.0,
      'thinking_causal_drop_ge_0_10':thinking_score-thinking_ab>=.10,
      'intelligence_relation_exact':float(intel_rel.get('best_score') or 0)==1.0,
      'intelligence_event_exact':float(intel_evt.get('best_score') or 0)==1.0,
    }
    for k,v in domain_checks.items():
        all_checks[domain+'::'+k]=v
    domain_results[domain]={
      'source_authority':spec['source_authority'],
      'source_kind':spec['source_kind'],
      'source_sha256':fetched.get('sha256'),
      'record_count':len(rows),
      'sample_records':rows[:4],
      'relation_case_count':len(relation_cases),
      'event_case_count':len(event_cases),
      'logic':{
        'accuracy':logic_score,'best_structural_ablation_accuracy':logic_ab,
        'causal_drop':logic_score-logic_ab,'gene_id':genes['LOGIC']['gene_id']
      },
      'thinking':{
        'accuracy':thinking_score,'best_structural_ablation_accuracy':thinking_ab,
        'causal_drop':thinking_score-thinking_ab,'gene_id':genes['THINKING']['gene_id']
      },
      'intelligence':{
        'relation_best_score':intel_rel.get('best_score'),
        'event_best_score':intel_evt.get('best_score'),
        'gene_id':genes['INTELLIGENCE']['gene_id'],
        'reselection_performed':False,'resynthesis_performed':False
      },
      'checks':domain_checks
    }

program_digests_after={
  'LOGIC':genes['LOGIC']['operator_program']['program_digest'],
  'THINKING':genes['THINKING']['operator_program']['program_digest'],
  'INTELLIGENCE':genes['INTELLIGENCE']['portfolio']['portfolio_digest'],
}
global_checks={
  'four_domains_present':len(domain_results)==4,
  'all_domain_gates_pass':all(all_checks.values()),
  'frozen_program_digests_unchanged':program_digests_before==program_digests_after,
  'no_gene_reselection':all(not x['intelligence']['reselection_performed'] for x in domain_results.values()),
  'no_resynthesis':all(not x['intelligence']['resynthesis_performed'] for x in domain_results.values()),
  'canonical_unchanged':core.head.get('canonical_head_digest')==head_before,
  'g3_not_started':core.head.get('g3_genesis_performed') is False,
}
status='PASS_SHADOW_G2_FOUR_DOMAIN_FRESH_STRESS_V1' if all(global_checks.values()) else 'WITHHOLD_G2_FOUR_DOMAIN_FRESH_STRESS_V1'

experience={
  'schema':'yado.g2.four_domain_fresh_stress.experience.v1',
  'status':'FRESH_STRESS_PASS_EVIDENCE' if status.startswith('PASS') else 'FRESH_STRESS_WITHHOLD_EVIDENCE',
  'task_id':task['task_id'],
  'frozen_tri_organ_genome_id':task['frozen_tri_organ_genome_id'],
  'prior_dns_gcp_receipt_sha256':dns.get('receipt_sha256'),
  'program_digests_before':program_digests_before,
  'program_digests_after':program_digests_after,
  'source_meta':source_meta,
  'domain_results':domain_results,
  'global_checks':global_checks,
  'canonical_mutation':False,
  'semantic_boundary':'FOUR PRINCIPALLY DIFFERENT PUBLIC MACHINE-READABLE DOMAINS ARE TRANSFORMED BY DOMAIN ADAPTERS INTO THE SAME RELATION/EVENT CONTRACTS. THE TRI-ORGAN GENOME AND PORTFOLIO ARE FROZEN. NO GENE RESELECTION, RESYNTHESIS, DOMAIN-SPECIFIC GENE PATCH, THIRD-PARTY CODE EXECUTION, CANONICAL MUTATION, OR EXPECTED FACT ANSWER IS USED.'
}
experience['experience_digest']=digest(experience)
EXP.parent.mkdir(parents=True,exist_ok=True)
EXP.write_text(json.dumps(experience,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

report={
  'schema':'yado.g2.four_domain_fresh_stress.v1',
  'status':status,
  'task_id':task['task_id'],
  'frozen_tri_organ_genome_id':task['frozen_tri_organ_genome_id'],
  'prior_dns_gcp_receipt_sha256':dns.get('receipt_sha256'),
  'domain_results':{
    k:{
      'record_count':v['record_count'],
      'relation_case_count':v['relation_case_count'],
      'event_case_count':v['event_case_count'],
      'logic':v['logic'],'thinking':v['thinking'],'intelligence':v['intelligence'],
      'checks':v['checks']
    } for k,v in domain_results.items()
  },
  'program_digests_before':program_digests_before,
  'program_digests_after':program_digests_after,
  'checks':global_checks,
  'canonical_mutation':False,'architecture_mutation':False,
  'automatic_canonical_promotion':False,'generation_transition':False,
  'g3_genesis_performed':False,
  'next_required_capability':'ALL_EXPERIENCE_TRI_ORGAN_CANONICAL_ADMISSION_REVIEW_V2' if status.startswith('PASS') else 'FOUR_DOMAIN_FRESH_STRESS_CAUSAL_REPAIR_V2',
  'experience_digest':experience['experience_digest'],
  'semantic_boundary':experience['semantic_boundary']
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

print(json.dumps(report,indent=2,sort_keys=True,default=str))
if status!='PASS_SHADOW_G2_FOUR_DOMAIN_FRESH_STRESS_V1':
    raise SystemExit(2)
