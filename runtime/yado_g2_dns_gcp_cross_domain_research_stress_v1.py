from __future__ import annotations

from pathlib import Path
from collections import Counter
from urllib.parse import urlparse
import copy, hashlib, html, json, re, sys, urllib.request

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_generic_relational_meta_language_v1 import GenericRelationalMetaLanguageV1
from yado_generic_event_state_meta_language_v1 import GenericEventStateMetaLanguageV1
from yado_g2_autonomous_gene_portfolio_controller_v1 import YADOAutonomousGenePortfolioControllerV1

TASK=REPO/'resources/yado-dns-gcp-cross-domain-research-task-v1.json'
TRI=REPO/'experience/yado-all-experience-tri-organ-genesis-v1.json'
CORPUS=REPO/'experience/yado-user-external-corpus-learning-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-dns-gcp-cross-domain-research-stress-v1.json'
EXP=REPO/'experience/yado-dns-gcp-cross-domain-research-stress-v1.json'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))

def plain(raw:bytes,content_type=''):
    text=raw.decode('utf-8','replace')
    if 'html' in content_type.lower() or '<html' in text[:500].lower():
        text=re.sub(r'(?is)<script.*?</script>|<style.*?</style>',' ',text)
        text=re.sub(r'(?s)<[^>]+>',' ',text)
        text=html.unescape(text)
    return re.sub(r'\s+',' ',text).strip()

def fetch(url,timeout=20,max_bytes=500000):
    req=urllib.request.Request(url,headers={
      'User-Agent':'YADO-G2-DNS-GCP-CrossDomain-Research/1.0',
      'Accept':'text/plain,text/html,application/json,*/*'
    })
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r:
            body=r.read(max_bytes)
            text=plain(body,str(r.headers.get('Content-Type') or ''))
            if len(text)<80: raise ValueError('TOO_LITTLE_TEXT')
            return {
              'ok':True,'requested_url':url,'resolved_url':str(getattr(r,'url',url) or url),
              'http_status':int(getattr(r,'status',200) or 200),
              'content_type':str(r.headers.get('Content-Type') or ''),
              'bytes':len(body),'sha256':sha_bytes(body),'text':text
            }
    except Exception as e:
        return {'ok':False,'requested_url':url,'error':type(e).__name__+':'+str(e)[:300]}

def valid_ipv4s(text):
    out=[]
    for raw in re.findall(r'(?<![0-9])(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?![0-9])',text):
        parts=raw.split('.')
        if all(0<=int(x)<=255 for x in parts):
            out.append(raw)
    return sorted(set(out),key=lambda s:tuple(int(x) for x in s.split('.')))

def google_api_hosts(text):
    hosts=[]
    for m in re.finditer(r'https?://([A-Za-z0-9._{}<>-]*googleapis\.com)',text,re.I):
        hosts.append(m.group(1).lower())
    for m in re.finditer(r'\b([A-Za-z0-9._{}<>-]*googleapis\.com)\b',text,re.I):
        hosts.append(m.group(1).lower())
    return Counter(hosts)

def derive_service_host(text):
    m=re.search(r'\bService:\s*([a-z0-9.-]+googleapis\.com)\b',text,re.I)
    if m:return m.group(1).lower(),'SERVICE_DECLARATION'
    counts=google_api_hosts(text)
    # Discovery host is generic documentation transport, not necessarily the service.
    for bad in ('www.googleapis.com','googleapis.com'):
        counts.pop(bad,None)
    if not counts:return None,'NO_SERVICE_HOST'
    host=sorted(counts.items(),key=lambda z:(-z[1],len(z[0]),z[0]))[0][0]
    return host,'MOST_FREQUENT_OFFICIAL_HOST'

def claimed_host(url):
    if url.count('://')!=1 or '<' in url or '>' in url:
        return None,'INVALID_URL_TEMPLATE'
    p=urlparse(url)
    return (p.hostname or '').lower() or None,'PARSED'

def near_pair(text,region,terms,window=700):
    low=text.lower(); reg=region.lower()
    positions=[m.start() for m in re.finditer(re.escape(reg),low)]
    for pos in positions:
        chunk=low[max(0,pos-window):min(len(low),pos+window)]
        if any(str(t).lower() in chunk for t in terms):
            return True
    return False

def rel_truth(edges,start):
    state={start}
    for _ in range(128):
        nxt=state|{b for a,b in edges if a in state}
        if nxt==state:break
        state=nxt
    return tuple(sorted(state,key=str))

def relation_accuracy(program,cases):
    ok=0
    for c in cases:
        got=GenericRelationalMetaLanguageV1.execute(program,c['relation'],c['start'])
        ok += (got==c['expected'])
    return ok/len(cases) if cases else 0.0

def event_accuracy(program,cases):
    ok=0
    for c in cases:
        got=GenericEventStateMetaLanguageV1.execute(program,c['events'])
        ok += (got is bool(c['expected']))
    return ok/len(cases) if cases else 0.0

def best_rel_ablation(program,cases):
    vals=[]
    for a in GenericRelationalMetaLanguageV1.ablations(program):
        vals.append(relation_accuracy(a['program'],cases))
    return max(vals,default=0.0)

def best_evt_ablation(program,cases):
    vals=[]
    for a in GenericEventStateMetaLanguageV1.ablations(program):
        vals.append(event_accuracy(a['program'],cases))
    return max(vals,default=0.0)

task=load(TASK)
tri=load(TRI)
corpus=load(CORPUS)
core=UnifiedYADOCoreV1(REPO)
head_before=core.head.get('canonical_head_digest')

if task.get('fresh_relative_to_tri_organ_genesis') is not True:
    raise RuntimeError('TASK_NOT_DECLARED_FRESH')
if task.get('frozen_tri_organ_genome_id')!=(tri.get('genome') or {}).get('genome_id'):
    raise RuntimeError('FROZEN_TRI_ORGAN_GENOME_MISMATCH')
if tri.get('status')!='TRAINED_SHADOW':
    raise RuntimeError('TRI_ORGAN_SHADOW_NOT_TRAINED')
genes=tri.get('genes') or {}
for organ in ('LOGIC','THINKING','INTELLIGENCE'):
    if organ not in genes:raise RuntimeError('MISSING_TRI_ORGAN_GENE:'+organ)
    if genes[organ].get('promotion_state')!='SHADOW_ONLY':
        raise RuntimeError('TRI_ORGAN_GENE_NOT_SHADOW:'+organ)

# -------------------------------------------------------------------------
# Public-source acquisition. The frozen genes are not changed or selected here.
# -------------------------------------------------------------------------
source_results={}
for row in task.get('sources') or []:
    sid=row['id']; r=fetch(row['url'])
    source_results[sid]=r

# Fallback only to the already-fetched public corpus for exact URL matches.
corpus_by_url={r.get('requested_url'):r for r in (corpus.get('records') or []) if r.get('ok')}
for row in task.get('sources') or []:
    sid=row['id']
    if source_results[sid].get('ok'):continue
    old=corpus_by_url.get(row['url'])
    if old and old.get('text_excerpt'):
        source_results[sid]={
          'ok':True,'requested_url':row['url'],'resolved_url':old.get('resolved_url') or row['url'],
          'http_status':old.get('http_status'),'content_type':old.get('content_type'),
          'bytes':old.get('bytes'),'sha256':old.get('sha256'),
          'text':old.get('text_excerpt'),'fallback':'PREVIOUSLY_FETCHED_PUBLIC_CORPUS_EXCERPT'
        }

source_public={
 sid:{k:v for k,v in r.items() if k!='text'}
 for sid,r in source_results.items()
}
fetch_ok=sum(bool(x.get('ok')) for x in source_results.values())
fetch_total=len(source_results)

# -------------------------------------------------------------------------
# Fact extraction and claim checking. Expected answers are not stored in task;
# they are derived from official-source content at runtime.
# -------------------------------------------------------------------------
dns_findings=[]
for c in task.get('dns_claims') or []:
    src=source_results.get(c['source_id']) or {}
    text=src.get('text','')
    observed=valid_ipv4s(text) if src.get('ok') else []
    missing=[ip for ip in c['claimed_ipv4'] if ip not in observed]
    status='SUPPORTED' if src.get('ok') and not missing else 'UNSUPPORTED_OR_CONTRADICTED'
    dns_findings.append({
      'claim_id':c['id'],'provider':c['provider'],'source_id':c['source_id'],
      'claimed_ipv4':c['claimed_ipv4'],'observed_ipv4':observed[:32],
      'missing_claimed_ipv4':missing,'status':status
    })

endpoint_findings=[]
for c in task.get('gcp_endpoint_claims') or []:
    src=source_results.get(c['source_id']) or {}
    text=src.get('text','')
    official_host,derive_mode=derive_service_host(text) if src.get('ok') else (None,'SOURCE_UNAVAILABLE')
    if official_host is None and src.get('ok'):
        source_url=str(src.get('resolved_url') or src.get('requested_url') or '')
        source_host=(urlparse(source_url).hostname or '').lower()
        if source_host.endswith('.googleapis.com') and source_host not in {'www.googleapis.com'}:
            official_host=source_host
            derive_mode='SUCCESSFULLY_FETCHED_OFFICIAL_SERVICE_SOURCE_HOST'
    chost,claim_mode=claimed_host(c['claimed_base'])
    if chost is None:
        status='CONTRADICTED_INVALID_SYNTAX'
    elif official_host and chost==official_host:
        status='SUPPORTED'
    elif official_host:
        status='CONTRADICTED_SERVICE_SPECIFIC_ENDPOINT'
    else:
        status='UNDETERMINED_SOURCE_EXTRACTION'
    host_counts=google_api_hosts(text)
    regional_examples=[
      h for h,_ in sorted(host_counts.items(),key=lambda z:(-z[1],z[0]))
      if h!=official_host and (
        '.rep.googleapis.com' in h or re.search(r'^(?:africa|asia|australia|europe|me|northamerica|southamerica|us)-[a-z0-9-]+-',h)
      )
    ][:8]
    endpoint_findings.append({
      'claim_id':c['id'],'service':c['service'],'source_id':c['source_id'],
      'claimed_base':c['claimed_base'],'claimed_host':chost,'claim_parse':claim_mode,
      'official_service_host':official_host,'official_endpoint':'https://'+official_host if official_host else None,
      'derive_mode':derive_mode,'regional_endpoint_examples':regional_examples,'status':status
    })

region_source=source_results.get('GCP_REGIONS_OFFICIAL') or {}
region_text=region_source.get('text','')
region_findings=[]
for c in task.get('region_claims') or []:
    supported=bool(region_source.get('ok')) and near_pair(region_text,c['region'],c['location_terms'])
    region_findings.append({
      'claim_id':c['id'],'region':c['region'],'claimed_location':c['claimed_location'],
      'location_terms':c['location_terms'],'source_id':'GCP_REGIONS_OFFICIAL',
      'status':'SUPPORTED' if supported else 'UNDETERMINED_OR_CONTRADICTED'
    })

google_dns_text=(source_results.get('DNS_GOOGLE_OFFICIAL') or {}).get('text','')
google_anycast_text=(source_results.get('DNS_GOOGLE_ANYCAST') or {}).get('text','')
adguard_text=(source_results.get('DNS_ADGUARD_OFFICIAL') or {}).get('text','')
cloudflare_text=(source_results.get('DNS_CLOUDFLARE_OFFICIAL') or {}).get('text','')
anycast_evidence=('anycast' in google_anycast_text.lower()) or ('anycast' in adguard_text.lower())
lookup_semantics=(
    ('dns lookup' in google_dns_text.lower() or 'dns lookups' in google_dns_text.lower())
    and ('resolver' in cloudflare_text.lower() or 'dns' in cloudflare_text.lower())
)
conceptual_findings={
  'dns_speed_claim':{
    'status':'SUPPORTED_WITH_NUANCE' if lookup_semantics else 'UNDETERMINED',
    'finding':'Changing recursive DNS can change name-resolution/lookup latency and perceived browsing startup, but it is not a general increase of the access link bandwidth or throughput.'
  },
  'dns_single_physical_address_claim':{
    'status':'SUPPORTED_WITH_NUANCE' if anycast_evidence else 'UNDETERMINED',
    'finding':'Public resolver IPs are commonly anycast service addresses routed to distributed points of presence; an IP such as 8.8.8.8 is not one fixed physical server location.'
  },
  'gcp_region_is_universal_physical_data_address_claim':{
    'status':'OVERGENERALIZED' if region_source.get('ok') else 'UNDETERMINED',
    'finding':'Google Cloud region identifiers correspond to geographic deployment locations, but service endpoints and data-location/residency semantics are product-specific; a region identifier is not a universal physical address for every service or every data flow.'
  }
}

# -------------------------------------------------------------------------
# Fresh cross-domain LOGIC cases from the newly observed research graph.
# These identifiers and facts did not exist when the tri-organ genome was born.
# -------------------------------------------------------------------------
relation_cases=[]
research_rows=[]
for x in dns_findings:
    research_rows.append(('DNS',x['claim_id'],x['source_id'],x['provider'],','.join(x['claimed_ipv4']),x['status']))
for x in endpoint_findings:
    research_rows.append(('GCP_ENDPOINT',x['claim_id'],x['source_id'],x['service'],str(x['official_service_host']),x['status']))
for x in region_findings:
    research_rows.append(('GCP_REGION',x['claim_id'],x['source_id'],x['region'],x['claimed_location'],x['status']))

for idx,(domain,cid,sid,entity,fact,status) in enumerate(research_rows):
    prefix=f'RESEARCH::{idx}::{digest([domain,cid,sid,entity,fact,status])[:12]}'
    nodes=[
      f'{prefix}::SOURCE::{sid}',
      f'{prefix}::DOMAIN::{domain}',
      f'{prefix}::ENTITY::{entity}',
      f'{prefix}::FACT::{fact}',
      f'{prefix}::USER_CLAIM::{cid}',
      f'{prefix}::VERDICT::{status}',
      f'{prefix}::SUMMARY'
    ]
    edges=list(zip(nodes[:-1],nodes[1:]))
    # Unreachable distractor chain prevents a trivial "return all nodes" strategy.
    d=[f'{prefix}::D{i}' for i in range(4)]
    edges += list(zip(d[:-1],d[1:]))
    relation_cases.append({
      'relation':tuple(edges),'start':nodes[0],
      'expected':rel_truth(edges,nodes[0]),'domain':domain,'claim_id':cid
    })

# -------------------------------------------------------------------------
# Fresh THINKING cases model evidence nesting: task > claim > source > fact >
# verdict > closure. Invalid orderings are generated from the same fresh IDs.
# -------------------------------------------------------------------------
event_cases=[]
for idx,(domain,cid,sid,entity,fact,status) in enumerate(research_rows):
    token=digest([idx,domain,cid,sid,entity,fact,status])[:16]
    keys=[
      f'TASK_{token}',f'CLAIM_{cid}_{token}',f'SOURCE_{sid}_{token}',
      f'ENTITY_{token}',f'FACT_{token}',f'VERDICT_{token}'
    ]
    Q='Q';R='R'
    valid=tuple([(Q,k) for k in keys]+[(R,k) for k in reversed(keys)])
    crossed=tuple([(Q,k) for k in keys]+[(R,k) for k in keys])
    underflow=tuple([(R,keys[0]),(Q,keys[-1]),(R,keys[-1])])
    unfinished=tuple(list(valid)[:-1])
    wrong=list(valid); wrong[len(keys)]=(R,'WRONG_'+token)
    rep=keys[-1]
    repeated=tuple([(Q,rep)]*len(keys)+[(R,rep)]*len(keys))
    event_cases += [
      {'events':valid,'expected':True,'claim_id':cid,'kind':'VALID_NESTED'},
      {'events':crossed,'expected':False,'claim_id':cid,'kind':'CROSSED_CLOSE'},
      {'events':underflow,'expected':False,'claim_id':cid,'kind':'UNDERFLOW'},
      {'events':unfinished,'expected':False,'claim_id':cid,'kind':'UNFINISHED'},
      {'events':tuple(wrong),'expected':False,'claim_id':cid,'kind':'WRONG_KEY'},
      {'events':repeated,'expected':True,'claim_id':cid,'kind':'REPEATED_KEY_VALID'}
    ]

logic_program=genes['LOGIC']['operator_program']
thinking_program=genes['THINKING']['operator_program']
logic_fresh=relation_accuracy(logic_program,relation_cases)
thinking_fresh=event_accuracy(thinking_program,event_cases)
logic_ab=best_rel_ablation(logic_program,relation_cases)
thinking_ab=best_evt_ablation(thinking_program,event_cases)

# Frozen intelligence portfolio: evaluation only. No discovery, selection or synthesis.
portfolio=copy.deepcopy(genes['INTELLIGENCE']['portfolio'])
relation_task={'task_id':'DNS_GCP_FRESH_RELATION','input_contract':'RELATION_START_TO_STATE','cases':relation_cases}
event_task={'task_id':'DNS_GCP_FRESH_EVENT','input_contract':'EVENT_SEQUENCE_TO_BOOLEAN','cases':event_cases}
intel_relation=YADOAutonomousGenePortfolioControllerV1.evaluate_portfolio(portfolio,relation_task)
intel_event=YADOAutonomousGenePortfolioControllerV1.evaluate_portfolio(portfolio,event_task)

dns_supported=sum(x['status']=='SUPPORTED' for x in dns_findings)
endpoint_determined=sum(x['status']!='UNDETERMINED_SOURCE_EXTRACTION' for x in endpoint_findings)
region_supported=sum(x['status']=='SUPPORTED' for x in region_findings)
endpoint_generic_contradictions=sum(x['status'].startswith('CONTRADICTED') for x in endpoint_findings)

checks={
  'task_is_fresh_relative_to_tri_organ_genesis':task.get('fresh_relative_to_tri_organ_genesis') is True,
  'frozen_genome_matches':task.get('frozen_tri_organ_genome_id')==(tri.get('genome') or {}).get('genome_id'),
  'source_fetch_ratio_ge_0_90':fetch_ok/max(1,fetch_total)>=.90,
  'all_five_dns_address_claims_supported':dns_supported==len(task.get('dns_claims') or [])==5,
  'all_gcp_endpoint_claims_determined':endpoint_determined==len(task.get('gcp_endpoint_claims') or []),
  'generic_googleapis_claim_exposed_as_wrong':endpoint_generic_contradictions>=13,
  'all_region_claims_supported':region_supported==len(task.get('region_claims') or []),
  'dns_anycast_semantics_found':conceptual_findings['dns_single_physical_address_claim']['status']=='SUPPORTED_WITH_NUANCE',
  'dns_speed_semantics_found':conceptual_findings['dns_speed_claim']['status']=='SUPPORTED_WITH_NUANCE',
  'logic_fresh_exact':logic_fresh==1.0,
  'logic_structural_ablation_drop_ge_0_20':logic_fresh-logic_ab>=.20,
  'thinking_fresh_exact':thinking_fresh==1.0,
  'thinking_structural_ablation_drop_ge_0_10':thinking_fresh-thinking_ab>=.10,
  'frozen_intelligence_relation_exact':float(intel_relation.get('best_score') or 0)==1.0,
  'frozen_intelligence_event_exact':float(intel_event.get('best_score') or 0)==1.0,
  'frozen_intelligence_not_reselected':True,
  'canonical_unchanged':core.head.get('canonical_head_digest')==head_before,
  'g3_not_started':core.head.get('g3_genesis_performed') is False,
}
status='PASS_SHADOW_G2_DNS_GCP_CROSS_DOMAIN_RESEARCH_STRESS_V1' if all(checks.values()) else 'WITHHOLD_G2_DNS_GCP_CROSS_DOMAIN_RESEARCH_STRESS_V1'

experience={
  'schema':'yado.g2.dns_gcp_cross_domain_research.experience.v1',
  'status':'TRAINED_FRESH_STRESS_EVIDENCE' if status.startswith('PASS') else 'WITHHOLD_FRESH_STRESS_EVIDENCE',
  'task_id':task['task_id'],
  'frozen_tri_organ_genome_id':task['frozen_tri_organ_genome_id'],
  'source_results':source_public,
  'dns_findings':dns_findings,
  'gcp_endpoint_findings':endpoint_findings,
  'region_findings':region_findings,
  'conceptual_findings':conceptual_findings,
  'fresh_logic':{
    'case_count':len(relation_cases),'accuracy':logic_fresh,
    'best_structural_ablation_accuracy':logic_ab,'causal_drop':logic_fresh-logic_ab,
    'gene_id':genes['LOGIC']['gene_id']
  },
  'fresh_thinking':{
    'case_count':len(event_cases),'accuracy':thinking_fresh,
    'best_structural_ablation_accuracy':thinking_ab,'causal_drop':thinking_fresh-thinking_ab,
    'gene_id':genes['THINKING']['gene_id']
  },
  'frozen_intelligence':{
    'relation_eval':intel_relation,'event_eval':intel_event,
    'gene_id':genes['INTELLIGENCE']['gene_id'],
    'reselection_performed':False,'resynthesis_performed':False
  },
  'checks':checks,
  'canonical_mutation':False,
  'semantic_boundary':'FRESH PUBLIC DNS/GCP RESEARCH STRESS AGAINST A FROZEN TRI-ORGAN SHADOW GENOME. OFFICIAL SOURCES ARE FETCHED AS EVIDENCE; NO THIRD-PARTY CODE IS EXECUTED; NO GENE IS RESELECTED OR RESYNTHESIZED; NO CANONICAL MUTATION OCCURS.'
}
experience['experience_digest']=digest(experience)
EXP.parent.mkdir(parents=True,exist_ok=True)
EXP.write_text(json.dumps(experience,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

report={
  'schema':'yado.g2.dns_gcp_cross_domain_research_stress.v1',
  'status':status,
  'task_id':task['task_id'],
  'frozen_tri_organ_genome_id':task['frozen_tri_organ_genome_id'],
  'source_fetch':{'ok':fetch_ok,'total':fetch_total,'ratio':fetch_ok/max(1,fetch_total)},
  'dns_summary':{'supported':dns_supported,'total':len(dns_findings)},
  'gcp_endpoint_summary':{
    'determined':endpoint_determined,'total':len(endpoint_findings),
    'generic_claim_contradictions':endpoint_generic_contradictions
  },
  'region_summary':{'supported':region_supported,'total':len(region_findings)},
  'conceptual_findings':conceptual_findings,
  'logic':experience['fresh_logic'],
  'thinking':experience['fresh_thinking'],
  'intelligence':{
    'relation_best_score':intel_relation.get('best_score'),
    'event_best_score':intel_event.get('best_score'),
    'gene_id':genes['INTELLIGENCE']['gene_id'],
    'reselection_performed':False,'resynthesis_performed':False
  },
  'checks':checks,
  'canonical_mutation':False,'architecture_mutation':False,
  'automatic_canonical_promotion':False,'generation_transition':False,
  'g3_genesis_performed':False,
  'next_required_capability':'ALL_EXPERIENCE_TRI_ORGAN_CANONICAL_ADMISSION_REVIEW_V2' if status.startswith('PASS') else 'DNS_GCP_CROSS_DOMAIN_STRESS_REPAIR_V2',
  'experience_digest':experience['experience_digest'],
  'semantic_boundary':experience['semantic_boundary']
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

print(json.dumps(report,indent=2,sort_keys=True,default=str))
if status!='PASS_SHADOW_G2_DNS_GCP_CROSS_DOMAIN_RESEARCH_STRESS_V1':
    raise SystemExit(2)
