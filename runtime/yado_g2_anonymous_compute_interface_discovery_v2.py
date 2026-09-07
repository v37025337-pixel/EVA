from __future__ import annotations
from pathlib import Path
from urllib.parse import urlparse,unquote
import hashlib,html,json,re,sys,urllib.request,urllib.error

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
from yado_unified_core_v1 import UnifiedYADOCoreV1

TASK=REPO/'resources/yado-anonymous-compute-interface-discovery-task-v2.json'
OUT=REPO/'candidates/kernel-self-generated/g2-anonymous-compute-interface-discovery-v2.json'
EXP=REPO/'experience/yado-anonymous-compute-interface-discovery-v2.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))

def fetch(url,timeout=14,max_bytes=800000,method='GET',data=None,headers=None):
    h={'User-Agent':'YADO-G2-Anonymous-Compute-Discovery/2.0','Accept':'text/plain,text/html,application/json,*/*'}
    if headers:h.update(headers)
    req=urllib.request.Request(url,data=data,method=method,headers=h)
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r:
            body=r.read(max_bytes)
            ct=str(r.headers.get('Content-Type') or '')
            txt=body.decode('utf-8','replace')
            if 'html' in ct.lower() or '<html' in txt[:500].lower():
                txt=re.sub(r'(?is)<script.*?</script>|<style.*?</style>',' ',txt)
                txt=re.sub(r'(?s)<[^>]+>',' ',txt);txt=html.unescape(txt)
            return {'ok':True,'status':int(getattr(r,'status',200) or 200),'url':str(getattr(r,'url',url) or url),
                    'content_type':ct,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),'text':txt}
    except urllib.error.HTTPError as e:
        body=e.read(120000)
        return {'ok':False,'status':int(e.code),'url':url,'error':'HTTPError','body':body.decode('utf-8','replace')[:4000]}
    except Exception as e:
        return {'ok':False,'status':None,'url':url,'error':type(e).__name__+':'+str(e)[:240]}

task=load(TASK);core=UnifiedYADOCoreV1(REPO);head_before=core.head.get('canonical_head_digest')
catalogs=[]
for u in task['discovery_sources']:
    r=fetch(u)
    catalogs.append({k:v for k,v in r.items() if k!='text'})
    if not r.get('ok'):continue
    txt=r['text']
    # collect markdown links whose surrounding context suggests remote code execution / compiler APIs
    for m in re.finditer(r'\[([^\]]{1,120})\]\((https?://[^)\s]+)\)',txt):
        label=m.group(1);url=m.group(2).rstrip('.,;')
        ctx=txt[max(0,m.start()-260):min(len(txt),m.end()+320)]
        low=(label+' '+ctx).lower()
        terms=('code execution','compiler','compile','sandbox','playground','run code','execute code','online ide')
        if not any(t in low for t in terms):continue
        auth_negative=any(t in low for t in ('no auth','no authentication','no api key','no key','without authentication'))
        globals().setdefault('_candidates',[]).append({'label':label,'url':url,'context':re.sub(r'\s+',' ',ctx)[:900],'explicit_no_auth_context':auth_negative})

cands=[]
seen=set()
for c in globals().get('_candidates',[]):
    host=(urlparse(c['url']).hostname or '').lower()
    if not host or host in seen:continue
    seen.add(host);cands.append(c)
cands=cands[:30]

researched=[]
for c in cands:
    r=fetch(c['url'],max_bytes=350000)
    txt=r.get('text','')
    low=txt.lower()
    no_auth=any(t in low for t in ('no authentication','no api key','without authentication','no auth required','authentication: no'))
    exec_evidence=any(t in low for t in ('execute code','code execution','compile code','run code','compiler api','execute endpoint'))
    api_evidence=any(t in low for t in ('api','curl','post '))
    links=re.findall(r'https?://[^\s<>"\']+',txt)[:200]
    researched.append({
      'label':c['label'],'url':c['url'],'host':(urlparse(c['url']).hostname or '').lower(),
      'fetch_ok':bool(r.get('ok')),'http_status':r.get('status'),
      'explicit_no_auth':bool(no_auth or c['explicit_no_auth_context']),
      'remote_execution_evidence':exec_evidence,'api_evidence':api_evidence,
      'candidate_endpoints':[x.rstrip(').,;') for x in links if any(k in x.lower() for k in ('execute','compile','api'))][:20],
      'doc_sha256':r.get('sha256'),'excerpt':txt[:2600] if r.get('ok') else None,'error':r.get('error')
    })

researched.sort(key=lambda x:(-(int(x['explicit_no_auth'])*8+int(x['remote_execution_evidence'])*6+int(x['api_evidence'])*3+int(x['fetch_ok'])),x['host']))
selected=next((x for x in researched if x['explicit_no_auth'] and x['remote_execution_evidence'] and x['api_evidence']),None)

# V2 deliberately refuses to invent a provider-specific POST schema. It searches docs for a complete
# curl+JSON example. If not derivable generically, the exact deficit becomes document/API comprehension.
schema_derived=False
derived_endpoint=None
derived_payload_keys=[]
if selected:
    text=selected.get('excerpt') or ''
    urls=re.findall(r'https?://[^\s<>"\']+',text)
    for u in urls:
        if any(k in u.lower() for k in ('execute','compile')):
            derived_endpoint=u.rstrip(').,;');break
    # evidence only: infer common JSON field names mentioned near examples
    for key in ('language','version','files','source','code','stdin','args'):
        if re.search(r'["\']'+re.escape(key)+r'["\']\s*:',text,re.I):
            derived_payload_keys.append(key)
    schema_derived=bool(derived_endpoint and ('code' in derived_payload_keys or 'files' in derived_payload_keys) and ('language' in derived_payload_keys))

snapshot={'task_id':task['task_id'],'head':core.head.get('canonical_head_digest'),'generation':core.head.get('generation_id'),'frontier':core.head.get('current_frontier')}
continuity_digest=digest(snapshot)
remote_attempted=False;remote_pass=False;remote_result=None
# Generic safe execution only when complete schema evidence can be derived. V2 still does not guess values.
if schema_derived:
    remote_result={'status':'WITHHOLD_SCHEMA_VALUES_NOT_SAFELY_DERIVED','endpoint':derived_endpoint,'payload_keys':derived_payload_keys}

checks={
 'catalogs_researched':sum(1 for x in catalogs if x.get('ok'))>=1,
 'candidate_discovery_nonempty':len(researched)>0,
 'provider_selection_evidence_based':selected is not None,
 'no_account_created':True,'no_credentials_used':True,'no_payment_used':True,
 'no_third_party_code_executed':True,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before,
 'g3_not_started':core.head.get('g3_genesis_performed') is False,
}
status='PASS_SHADOW_G2_ANONYMOUS_COMPUTE_INTERFACE_DISCOVERY_V2' if remote_pass else 'WITHHOLD_G2_ANONYMOUS_COMPUTE_INTERFACE_DISCOVERY_V2'
if selected is None:
    next_cap='ANONYMOUS_REMOTE_EXECUTION_PROVIDER_WITH_EXPLICIT_NO_AUTH_EVIDENCE'
elif not schema_derived:
    next_cap='DOCUMENT_API_SCHEMA_COMPREHENSION_AND_SAFE_REQUEST_SYNTHESIS_V1'
else:
    next_cap='SAFE_ANONYMOUS_REMOTE_EXECUTION_REQUEST_SYNTHESIS_V3'

experience={'schema':'yado.g2.anonymous_compute_interface_discovery.experience.v2','status':status,
 'catalogs':catalogs,'candidates':researched,'selected_provider':selected,'schema_derived':schema_derived,
 'derived_endpoint':derived_endpoint,'derived_payload_keys':derived_payload_keys,'continuity_digest':continuity_digest,
 'remote_attempted':remote_attempted,'remote_pass':remote_pass,'remote_result':remote_result,'next_required_capability':next_cap,
 'canonical_mutation':False,'semantic_boundary':'AUTONOMOUS DISCOVERY OF PUBLIC NO-ACCOUNT REMOTE EXECUTION OPTIONS. YADO DOES NOT CREATE ACCOUNTS OR GUESS WRITE-API SCHEMAS. IF DOCUMENTED REQUEST STRUCTURE CANNOT BE DERIVED FROM PUBLIC EVIDENCE, IT WITHHOLDS AND IDENTIFIES DOCUMENT/API COMPREHENSION AS THE NEXT CAPABILITY.'}
experience['experience_digest']=digest(experience)
EXP.parent.mkdir(parents=True,exist_ok=True);EXP.write_text(json.dumps(experience,indent=2,sort_keys=True,default=str)+'\n')
report={'schema':'yado.g2.anonymous_compute_interface_discovery.v2','status':status,'task_id':task['task_id'],
 'candidate_count':len(researched),'selected_provider':selected,'schema_derived':schema_derived,'derived_endpoint':derived_endpoint,
 'derived_payload_keys':derived_payload_keys,'remote_attempted':remote_attempted,'remote_pass':remote_pass,
 'next_required_capability':next_cap,'checks':checks,'experience_digest':experience['experience_digest'],
 'canonical_mutation':False,'automatic_canonical_promotion':False,'g3_genesis_performed':False,'semantic_boundary':experience['semantic_boundary']}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps(report,indent=2,sort_keys=True,default=str))
if status!='PASS_SHADOW_G2_ANONYMOUS_COMPUTE_INTERFACE_DISCOVERY_V2':raise SystemExit(2)
