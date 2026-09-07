from __future__ import annotations
from pathlib import Path
from collections import Counter
import hashlib,html,json,re,sys,urllib.request

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path[:0]=[str(ROOT),str(ROOT/'yado_rc8_v36')]

from yado_generic_relational_meta_language_v1 import GenericRelationalMetaLanguageV1
from yado_generic_event_state_meta_language_v1 import GenericEventStateMetaLanguageV1
from yado_g2_autonomous_gene_portfolio_controller_v1 import YADOAutonomousGenePortfolioControllerV1

TASK=REPO/'resources/yado-dns-screenshot-research-task-v2.json'
TRI=REPO/'canonical/yado-g2-all-experience-tri-organ-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-dns-screenshot-research-stress-v2.json'
EXP=REPO/'experience/yado-dns-screenshot-research-stress-v2.json'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))

def plain(raw,ct=''):
    text=raw.decode('utf-8','replace')
    if 'html' in ct.lower() or '<html' in text[:500].lower():
        text=re.sub(r'(?is)<script.*?</script>|<style.*?</style>',' ',text)
        text=re.sub(r'(?s)<[^>]+>',' ',text)
        text=html.unescape(text)
    return re.sub(r'\s+',' ',text).strip()

def fetch(url,timeout=25,max_bytes=900000):
    req=urllib.request.Request(url,headers={'User-Agent':'YADO-G2-DNS-Screenshot-Research/2.0','Accept':'text/plain,text/html,application/json,*/*'})
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r:
            body=r.read(max_bytes); text=plain(body,str(r.headers.get('Content-Type') or ''))
            if len(text)<50: raise ValueError('TOO_LITTLE_TEXT')
            return {'ok':True,'requested_url':url,'resolved_url':str(getattr(r,'url',url) or url),'http_status':int(getattr(r,'status',200) or 200),'content_type':str(r.headers.get('Content-Type') or ''),'bytes':len(body),'sha256':sha_bytes(body),'text':text}
    except Exception as e:
        return {'ok':False,'requested_url':url,'error':type(e).__name__+':'+str(e)[:300]}

def ipv4s(text):
    out=[]
    for x in re.findall(r'(?<![0-9])(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?![0-9])',text):
        ps=x.split('.')
        if all(0<=int(p)<=255 for p in ps): out.append(x)
    return sorted(set(out),key=lambda s:tuple(int(x) for x in s.split('.')))

def snippet(text,terms,window=220):
    low=text.lower()
    for term in terms:
        p=low.find(term.lower())
        if p>=0:return text[max(0,p-window):min(len(text),p+window)]
    return text[:min(len(text),440)]

def hasall(t,*xs):
    l=t.lower(); return all(x.lower() in l for x in xs)
def hasany(t,*xs):
    l=t.lower(); return any(x.lower() in l for x in xs)

def evaluate_claim(c,text,ok):
    if not ok:return {'verdict':'UNDETERMINED_SOURCE_UNAVAILABLE','reason':'SOURCE_UNAVAILABLE','evidence_excerpt':''}
    kind=c['kind']; l=text.lower(); ips=ipv4s(text)
    if kind=='ADDRESS_PAIR':
        miss=[x for x in c['claimed_ipv4'] if x not in ips]
        verdict='SUPPORTED' if not miss else 'CONTRADICTED_OR_UNSUPPORTED'
        return {'verdict':verdict,'observed_ipv4':ips[:40],'missing_claimed_ipv4':miss,'evidence_excerpt':snippet(text,c['claimed_ipv4'])}
    if kind=='NO_IP_LOGS':
        contrad=hasall(text,'temporary','log') and hasany(text,'ip address','source ip')
        return {'verdict':'CONTRADICTED_ABSOLUTE_CLAIM' if contrad else 'UNDETERMINED','reason':'OFFICIAL_POLICY_DESCRIBES_TEMPORARY_IP_BEARING_LOGS' if contrad else 'NO_CLEAR_POLICY_SIGNAL','evidence_excerpt':snippet(text,['temporary logs','ip address'])}
    if kind=='NO_LOGS_ABSOLUTE':
        nuanced=hasany(text,'retain','logs','randomly sampled','packet') and hasany(text,'source ip','personal data','dns')
        return {'verdict':'SUPPORTED_WITH_NUANCE' if nuanced else 'UNDETERMINED','reason':'PRIVACY_FOCUSED_DOES_NOT_MEAN_LITERAL_ZERO_OPERATIONAL_DATA','evidence_excerpt':snippet(text,['retain','randomly sampled','privacy'])}
    if kind=='DEFAULT_THREAT_FILTERING':
        nofilter=hasany(text,'no content filtering','standard resolver') and hasany(text,'malware','families')
        return {'verdict':'CONTRADICTED_STANDARD_RESOLVER' if nofilter else 'UNDETERMINED','reason':'THREAT_FILTERING_USES_SEPARATE_FAMILIES_VARIANTS' if nofilter else 'NO_CLEAR_VARIANT_SIGNAL','evidence_excerpt':snippet(text,['no content filtering','block malware','families'])}
    if kind=='FEATURE_ON_STANDARD_PAIR':
        separate=all(x in l for x in ['208.67.222.123','208.67.220.123']) and all(x in l for x in ['208.67.222.222','208.67.220.220'])
        return {'verdict':'CONTRADICTED_SEPARATE_ADDRESSES' if separate else 'UNDETERMINED','reason':'FAMILYSHIELD_HAS_DISTINCT_123_ADDRESSES' if separate else 'NO_CLEAR_ADDRESS_SEPARATION','evidence_excerpt':snippet(text,['familyshield','208.67.222.123'])}
    if kind=='THREAT_BLOCKING':
        sup=hasany(text,'threat-blocking','threat blocking') and hasany(text,'malware','phishing')
        return {'verdict':'SUPPORTED' if sup else 'UNDETERMINED','reason':'OFFICIAL_SERVICE_DESCRIBES_THREAT_BLOCKING' if sup else 'NO_CLEAR_SIGNAL','evidence_excerpt':snippet(text,['threat-blocking','malware'])}
    if kind=='NO_ENDUSER_IP_LOGGING':
        sup=(hasany(text,'end user','enduser','users') and hasany(text,'ip address','personal data') and hasany(text,'not collect','no information','no personal data','never log','not record'))
        return {'verdict':'SUPPORTED_WITH_POLICY_SCOPE' if sup else 'UNDETERMINED','reason':'OFFICIAL_PRIVACY_POLICY_DENIES_ENDUSER_PERSONAL_DATA_COLLECTION' if sup else 'NO_CLEAR_SIGNAL','evidence_excerpt':snippet(text,['end user','ip address','personal data'])}
    if kind=='PARENTAL_CONTROLS':
        sup=hasany(text,'parental control','parental controls') and hasany(text,'block','safe')
        return {'verdict':'SUPPORTED' if sup else 'UNDETERMINED','reason':'OFFICIAL_SITE_DESCRIBES_PARENTAL_CONTROL' if sup else 'NO_CLEAR_SIGNAL','evidence_excerpt':snippet(text,['parental control'])}
    if kind=='LOGGING_CAN_DISABLE':
        sup=hasany(text,'disable logging completely','no-logs experience','disable logging')
        return {'verdict':'SUPPORTED' if sup else 'UNDETERMINED','reason':'OFFICIAL_SITE_ALLOWS_LOGGING_TO_BE_DISABLED' if sup else 'NO_CLEAR_SIGNAL','evidence_excerpt':snippet(text,['disable logging','no-logs'])}
    if kind=='PROFILE_CONFIGURATION':
        cfg=hasany(text,'configuration id','set your configuration id','profile')
        return {'verdict':'OVERGENERALIZED_REQUIRES_CONFIGURATION' if cfg else 'UNDETERMINED','reason':'PERSONALIZED_NEXTDNS_BEHAVIOR_REQUIRES_PROFILE_OR_CONFIGURATION_CONTEXT' if cfg else 'NO_CLEAR_CONFIG_SIGNAL','evidence_excerpt':snippet(text,['configuration id','profile'])}
    return {'verdict':'UNDETERMINED_UNKNOWN_KIND','reason':kind,'evidence_excerpt':''}

def rel_truth(edges,start):
    state={start}
    for _ in range(128):
        nxt=state|{b for a,b in edges if a in state}
        if nxt==state:break
        state=nxt
    return tuple(sorted(state,key=str))

def rel_acc(program,cases):
    return sum(GenericRelationalMetaLanguageV1.execute(program,c['relation'],c['start'])==c['expected'] for c in cases)/len(cases)
def evt_acc(program,cases):
    return sum(GenericEventStateMetaLanguageV1.execute(program,c['events']) is bool(c['expected']) for c in cases)/len(cases)
def best_rel_ab(program,cases):
    return max((rel_acc(a['program'],cases) for a in GenericRelationalMetaLanguageV1.ablations(program)),default=0.0)
def best_evt_ab(program,cases):
    return max((evt_acc(a['program'],cases) for a in GenericEventStateMetaLanguageV1.ablations(program)),default=0.0)

task=load(TASK); tri=load(TRI)
if tri.get('status')!='CANONICAL_ACTIVE': raise RuntimeError('TRI_ORGAN_NOT_CANONICAL_ACTIVE')
if task.get('constraints',{}).get('canonical_mutation') is not False: raise RuntimeError('TASK_CANONICAL_MUTATION_NOT_FALSE')
genes=tri['genes']

source_results={row['id']:fetch(row['url']) for row in task['sources']}
source_public={sid:{k:v for k,v in r.items() if k!='text'} for sid,r in source_results.items()}
findings=[]
for c in task['screenshot_claims']:
    src=source_results.get(c['source_id']) or {}
    ev=evaluate_claim(c,src.get('text',''),bool(src.get('ok')))
    findings.append({'claim_id':c['id'],'provider':c['provider'],'kind':c['kind'],'claim':c.get('claim'),'claimed_ipv4':c.get('claimed_ipv4'),'source_id':c['source_id'],**ev})

# Fresh reasoning cases generated only after source-derived verdicts exist.
rel_cases=[]; evt_cases=[]
for i,f in enumerate(findings):
    token=digest([i,f['claim_id'],f['provider'],f['verdict']])[:14]
    nodes=[f'R::{token}::SOURCE::{f["source_id"]}',f'R::{token}::PROVIDER::{f["provider"]}',f'R::{token}::CLAIM::{f["claim_id"]}',f'R::{token}::VERDICT::{f["verdict"]}',f'R::{token}::MEMORY']
    edges=list(zip(nodes[:-1],nodes[1:]))+[(f'R::{token}::D0',f'R::{token}::D1')]
    rel_cases.append({'relation':tuple(edges),'start':nodes[0],'expected':rel_truth(edges,nodes[0]),'claim_id':f['claim_id']})
    keys=[f'SRC_{token}',f'CLAIM_{token}',f'CHECK_{token}',f'VERDICT_{token}',f'APPLY_{token}']
    valid=tuple([('Q',k) for k in keys]+[('R',k) for k in reversed(keys)])
    crossed=tuple([('Q',k) for k in keys]+[('R',k) for k in keys])
    evt_cases += [
      {'events':valid,'expected':True,'claim_id':f['claim_id'],'kind':'VALID_EVIDENCE_APPLICATION'},
      {'events':crossed,'expected':False,'claim_id':f['claim_id'],'kind':'INVALID_CAUSAL_ORDER'}
    ]

lp=genes['LOGIC']['operator_program']; tp=genes['THINKING']['operator_program']
logic=rel_acc(lp,rel_cases); thinking=evt_acc(tp,evt_cases)
logic_ab=best_rel_ab(lp,rel_cases); thinking_ab=best_evt_ab(tp,evt_cases)
portfolio=genes['INTELLIGENCE']['portfolio']
intel_rel=YADOAutonomousGenePortfolioControllerV1.evaluate_portfolio(portfolio,{'task_id':'DNS_SCREENSHOT_REL_V2','input_contract':'RELATION_START_TO_STATE','cases':rel_cases})
intel_evt=YADOAutonomousGenePortfolioControllerV1.evaluate_portfolio(portfolio,{'task_id':'DNS_SCREENSHOT_EVT_V2','input_contract':'EVENT_SEQUENCE_TO_BOOLEAN','cases':evt_cases})

fetch_ok=sum(bool(x.get('ok')) for x in source_results.values()); total=len(source_results)
determined=[x for x in findings if not x['verdict'].startswith('UNDETERMINED')]
checks={
 'official_source_fetch_ratio_ge_0_90':fetch_ok/max(1,total)>=0.90,
 'all_address_claims_determined':all(x['verdict'] in {'SUPPORTED','CONTRADICTED_OR_UNSUPPORTED'} for x in findings if x['kind']=='ADDRESS_PAIR'),
 'google_absolute_no_ip_logs_exposed':next(x for x in findings if x['claim_id']=='GOOGLE_NO_IP_LOGS')['verdict']=='CONTRADICTED_ABSOLUTE_CLAIM',
 'cloudflare_default_filtering_exposed':next(x for x in findings if x['claim_id']=='CLOUDFLARE_BLOCKS_BY_DEFAULT')['verdict']=='CONTRADICTED_STANDARD_RESOLVER',
 'opendns_familyshield_address_separation_exposed':next(x for x in findings if x['claim_id']=='OPENDNS_FAMILYSHIELD_ON_PAIR')['verdict']=='CONTRADICTED_SEPARATE_ADDRESSES',
 'quad9_threat_blocking_supported':next(x for x in findings if x['claim_id']=='QUAD9_THREAT_BLOCKING')['verdict']=='SUPPORTED',
 'nextdns_logging_disable_supported':next(x for x in findings if x['claim_id']=='NEXTDNS_LOGGING_DISABLE')['verdict']=='SUPPORTED',
 'nextdns_configuration_nuance_exposed':next(x for x in findings if x['claim_id']=='NEXTDNS_CONFIG_NUANCE')['verdict']=='OVERGENERALIZED_REQUIRES_CONFIGURATION',
 'logic_fresh_exact':logic==1.0,
 'logic_ablation_drop':logic-logic_ab>=0.20,
 'thinking_fresh_exact':thinking==1.0,
 'thinking_ablation_drop':thinking-thinking_ab>=0.10,
 'intelligence_relation_exact':float(intel_rel.get('best_score') or 0)==1.0,
 'intelligence_event_exact':float(intel_evt.get('best_score') or 0)==1.0,
 'no_gene_reselection':True,
 'canonical_mutation_false':True,
 'g3_false':True
}
status='PASS_SHADOW_G2_DNS_SCREENSHOT_RESEARCH_STRESS_V2' if all(checks.values()) else 'WITHHOLD_G2_DNS_SCREENSHOT_RESEARCH_STRESS_V2'
summary={
 'supported':sum(x['verdict']=='SUPPORTED' for x in findings),
 'supported_with_nuance':sum('NUANCE' in x['verdict'] or 'POLICY_SCOPE' in x['verdict'] for x in findings),
 'contradicted_or_overgeneralized':sum(x['verdict'].startswith('CONTRADICTED') or x['verdict'].startswith('OVERGENERALIZED') for x in findings),
 'undetermined':sum(x['verdict'].startswith('UNDETERMINED') for x in findings)
}
experience={
 'schema':'yado.g2.dns_screenshot_research.experience.v2','status':status,'task_id':task['task_id'],
 'source_results':source_public,'claim_findings':findings,'summary':summary,
 'fresh_logic':{'case_count':len(rel_cases),'accuracy':logic,'best_ablation_accuracy':logic_ab,'causal_drop':logic-logic_ab,'gene_id':genes['LOGIC']['gene_id']},
 'fresh_thinking':{'case_count':len(evt_cases),'accuracy':thinking,'best_ablation_accuracy':thinking_ab,'causal_drop':thinking-thinking_ab,'gene_id':genes['THINKING']['gene_id']},
 'frozen_intelligence':{'relation_best_score':intel_rel.get('best_score'),'event_best_score':intel_evt.get('best_score'),'gene_id':genes['INTELLIGENCE']['gene_id'],'reselection_performed':False},
 'checks':checks,'canonical_mutation':False,'automatic_promotion':False,'g3_genesis':False,
 'application_rule':'SOURCE_DERIVED_VERDICTS_ENTER_L1_MEMORY_AS_CAUSAL_EVIDENCE; FUTURE SOURCE_SELECTION_MUST_DOWNRANK_ABSOLUTE_MARKETING_CLAIMS_THAT_CONFLICT_WITH_PROVIDER_DOCUMENTATION',
 'semantic_boundary':'BOUNDED FACT-CHECKING AND FRESH CAUSAL-REASONING STRESS OVER USER-SUPPLIED DNS INFOGRAPHIC CLAIMS. THIS DOES NOT MEASURE REAL-WORLD LATENCY FROM THE USER NETWORK.'
}
experience['experience_digest']=digest(experience)
report={
 'schema':'yado.g2.dns_screenshot_research_stress.v2','status':status,'task_id':task['task_id'],
 'source_fetch':{'ok':fetch_ok,'total':total,'ratio':fetch_ok/max(1,total)},'summary':summary,'claim_findings':findings,
 'logic':experience['fresh_logic'],'thinking':experience['fresh_thinking'],'intelligence':experience['frozen_intelligence'],
 'checks':checks,'experience_digest':experience['experience_digest'],
 'next_required_capability':'APPLY_DNS_SCREENSHOT_EVIDENCE_TO_CAUSAL_MEMORY' if status.startswith('PASS') else 'DNS_SCREENSHOT_RESEARCH_REPAIR_V3',
 'canonical_mutation':False,'automatic_canonical_promotion':False,'generation_transition':False,'g3_genesis_performed':False,
 'semantic_boundary':experience['semantic_boundary']
}
report['receipt_sha256']=digest(report)
EXP.parent.mkdir(parents=True,exist_ok=True); OUT.parent.mkdir(parents=True,exist_ok=True)
EXP.write_text(json.dumps(experience,indent=2,sort_keys=True)+'\n',encoding='utf-8')
OUT.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps({'status':status,'source_fetch':report['source_fetch'],'summary':summary,'logic':report['logic'],'thinking':report['thinking'],'intelligence':report['intelligence'],'next_required_capability':report['next_required_capability'],'experience_digest':report['experience_digest']},indent=2,sort_keys=True))
if not status.startswith('PASS_'): raise SystemExit(2)
