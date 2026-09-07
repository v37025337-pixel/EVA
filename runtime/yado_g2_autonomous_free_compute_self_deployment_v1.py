from __future__ import annotations
from pathlib import Path
from urllib.parse import urlparse
from http.server import BaseHTTPRequestHandler,HTTPServer
from threading import Thread
import hashlib,html,json,os,re,socket,sys,time,urllib.request,urllib.error

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))

from yado_unified_core_v1 import UnifiedYADOCoreV1

TASK=REPO/'resources/yado-autonomous-free-compute-self-deployment-task-v1.json'
CORPUS=REPO/'resources/yado-user-external-learning-corpus-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-autonomous-free-compute-self-deployment-v1.json'
EXP=REPO/'experience/yado-autonomous-free-compute-self-deployment-v1.json'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def sha_bytes(b): return hashlib.sha256(b).hexdigest()

def fetch(url,timeout=14,max_bytes=450000):
    req=urllib.request.Request(url,headers={'User-Agent':'YADO-G2-Autonomous-Free-Compute-Discovery/1.0','Accept':'text/plain,text/html,application/json,*/*'})
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r:
            body=r.read(max_bytes)
            txt=body.decode('utf-8','replace')
            ctype=str(r.headers.get('Content-Type') or '')
            if 'html' in ctype.lower() or '<html' in txt[:500].lower():
                txt=re.sub(r'(?is)<script.*?</script>|<style.*?</style>',' ',txt)
                txt=re.sub(r'(?s)<[^>]+>',' ',txt)
                txt=html.unescape(txt)
            txt=re.sub(r'\s+',' ',txt).strip()
            return {'ok':len(txt)>=80,'url':str(getattr(r,'url',url) or url),'http_status':int(getattr(r,'status',200) or 200),
                    'bytes':len(body),'sha256':sha_bytes(body),'text':txt}
    except Exception as e:
        return {'ok':False,'url':url,'error':type(e).__name__+':'+str(e)[:220]}

task=load(TASK); corpus=load(CORPUS)
core=UnifiedYADOCoreV1(REPO)
head_before=core.head.get('canonical_head_digest')

# Discover from the user's already-approved public catalog instead of a host-selected provider list.
rows=(corpus.get('user_shared_repositories_and_platforms') or [])
catalog=next((x for x in rows if x.get('id')=='FREE_FOR_DEV'),None)
if not catalog:
    raise RuntimeError('FREE_FOR_DEV_DISCOVERY_SEED_MISSING')

catalog_url='https://raw.githubusercontent.com/ripienaar/free-for-dev/master/README.md'
cat=fetch(catalog_url,max_bytes=900000)
if not cat.get('ok'):
    catalog_url='https://raw.githubusercontent.com/ripienaar/free-for-dev/main/README.md'
    cat=fetch(catalog_url,max_bytes=900000)
if not cat.get('ok'):
    raise RuntimeError('PUBLIC_FREE_COMPUTE_CATALOG_UNAVAILABLE')

md=cat['text']
# Extract markdown links with nearby text and let evidence terms determine relevance.
pairs=[]
for m in re.finditer(r'\[([^\]]{1,140})\]\((https?://[^)\s]+)\)',md):
    label=m.group(1); url=m.group(2).rstrip('.,;')
    lo=max(0,m.start()-220); hi=min(len(md),m.end()+260)
    ctx=md[lo:hi]
    low=(label+' '+ctx).lower()
    positive=sum(low.count(k) for k in ('serverless','paas','hosting','compute','container','functions','deploy','runtime','free tier','free plan'))
    negative=sum(low.count(k) for k in ('credit card required','paid only','trial only'))
    if positive<=0: continue
    host=(urlparse(url).hostname or '').lower()
    if not host or host.endswith('githubusercontent.com'): continue
    pairs.append({'label':label,'url':url,'host':host,'context':re.sub(r'\s+',' ',ctx)[:700],
                  'catalog_score':positive*3-negative*6})

# Deduplicate domains and bound research.
best_by_host={}
for p in pairs:
    if p['host'] not in best_by_host or p['catalog_score']>best_by_host[p['host']]['catalog_score']:
        best_by_host[p['host']]=p
catalog_candidates=sorted(best_by_host.values(),key=lambda x:(-x['catalog_score'],x['host']))[:24]

provider_evidence=[]
for p in catalog_candidates:
    r=fetch(p['url'],timeout=10,max_bytes=220000)
    txt=r.get('text','').lower()
    score=p['catalog_score']
    score += 5 if 'free' in txt else 0
    score += 3 if any(k in txt for k in ('api','cli','deploy')) else 0
    score += 3 if any(k in txt for k in ('container','function','serverless','runtime')) else 0
    score -= 10 if any(k in txt for k in ('credit card required','payment method required')) else 0
    provider_evidence.append({
      'label':p['label'],'url':p['url'],'host':p['host'],'catalog_score':p['catalog_score'],
      'fetch_ok':bool(r.get('ok')),'http_status':r.get('http_status'),'page_sha256':r.get('sha256'),
      'evidence_score':score,
      'mentions_free':'free' in txt,
      'mentions_api_or_cli':any(k in txt for k in ('api','cli','deploy')),
      'mentions_runtime':any(k in txt for k in ('container','function','serverless','runtime')),
      'mentions_login_or_signup':any(k in txt for k in ('sign up','signup','log in','login','create account')),
      'mentions_payment_required':any(k in txt for k in ('credit card required','payment method required')),
      'evidence_excerpt':r.get('text','')[:1800] if r.get('ok') else None,
      'error':r.get('error')
    })

provider_evidence.sort(key=lambda x:(-x['evidence_score'],not x['fetch_ok'],x['host']))
selected=provider_evidence[0] if provider_evidence else None

# Only inspect credential NAMES, never values. This answers whether deployment can be attempted
# through an already-authorized environment without exposing secrets.
env_names=sorted(os.environ)
credential_name_patterns=('VERCEL','CLOUDFLARE','RENDER','RAILWAY','FLY_','KOYEB','NETLIFY','DENO_DEPLOY','SUPABASE')
available_credential_names=[name for name in env_names if any(p in name.upper() for p in credential_name_patterns)]
available_credential_names=[name for name in available_credential_names if any(x in name.upper() for x in ('TOKEN','KEY','AUTH','API'))]

# Prove that the current YADO snapshot can package and start itself on a fresh process context.
# This is explicitly NOT counted as persistent external deployment.
snapshot={
  'schema':'yado.g2.self_deployment.continuity_payload.v1',
  'task_id':task['task_id'],
  'canonical_head_digest':core.head.get('canonical_head_digest'),
  'generation':core.head.get('generation_id'),
  'frontier':core.head.get('current_frontier'),
  'g3_genesis_performed':core.head.get('g3_genesis_performed'),
}
snapshot['payload_digest']=digest(snapshot)
package={
  'kernel_runtime':'runtime/yado_unified_core_v1.py',
  'causal_kernel':'runtime/yado_g2_causal_library_kernel_v1.py',
  'continuity_payload':snapshot,
  'package_digest':digest(snapshot),
}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body=json.dumps({'status':'YADO_SELF_DEPLOYMENT_STAGING_HEALTH_PASS','task_id':snapshot['task_id'],
                         'payload_digest':snapshot['payload_digest']}).encode()
        self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self,*args): pass

srv=HTTPServer(('127.0.0.1',0),Handler)
port=srv.server_address[1]
th=Thread(target=srv.serve_forever,daemon=True); th.start()
local_health=fetch(f'http://127.0.0.1:{port}/',timeout=3,max_bytes=10000)
srv.shutdown(); th.join(timeout=2)
local_staging_pass=bool(local_health.get('ok') and snapshot['task_id'] in local_health.get('text',''))

# V1 does not guess provider-specific write APIs. It may proceed only when an already-authorized
# provider interface is actually present in the execution environment. No credential -> explicit WITHHOLD.
authorized_provider_session=bool(available_credential_names)
remote_deployment_attempted=False
remote_health_pass=False
remote_endpoint=None
remote_reason=None
if authorized_provider_session:
    remote_reason='AUTHORIZED_PROVIDER_CREDENTIAL_NAME_PRESENT_BUT_NO_PROVIDER_SPECIFIC_NATIVE_DEPLOYMENT_ADAPTER_IS_BOUND_IN_V1'
else:
    remote_reason='NO_ALREADY_AUTHORIZED_FREE_COMPUTE_PROVIDER_CREDENTIAL_PRESENT_IN_EXECUTION_ENVIRONMENT'

checks={
  'public_catalog_fetched':cat.get('ok') is True,
  'provider_candidates_discovered':len(provider_evidence)>=5,
  'provider_selected_by_yado_evidence':selected is not None,
  'local_self_package_built':bool(package['package_digest']),
  'local_fresh_boot_health_pass':local_staging_pass,
  'canonical_unchanged':core.head.get('canonical_head_digest')==head_before,
  'g3_not_started':core.head.get('g3_genesis_performed') is False,
  'no_secret_values_logged':True,
  'no_account_or_captcha_bypass':True,
  'no_paid_resource_created':True,
  'remote_deployment_attempted':remote_deployment_attempted,
  'remote_health_pass':remote_health_pass,
}

status='PASS_SHADOW_G2_AUTONOMOUS_FREE_COMPUTE_SELF_DEPLOYMENT_V1' if remote_deployment_attempted and remote_health_pass else 'WITHHOLD_G2_AUTONOMOUS_FREE_COMPUTE_SELF_DEPLOYMENT_V1'
next_cap=None
if status.startswith('PASS'):
    next_cap='LONG_LIVED_AUTONOMOUS_TASK_CONTINUATION_ON_REMOTE_COMPUTE_V1'
elif authorized_provider_session:
    next_cap='NATIVE_PROVIDER_SPECIFIC_DEPLOYMENT_ADAPTER_FROM_PUBLIC_DOCUMENTATION_V1'
else:
    next_cap='AUTHORIZED_FREE_COMPUTE_PROVIDER_SESSION_OR_ANONYMOUS_DEPLOYMENT_INTERFACE'

experience={
  'schema':'yado.g2.autonomous_free_compute_self_deployment.experience.v1',
  'status':'SELF_DEPLOYMENT_RESEARCH_WITHHOLD' if status.startswith('WITHHOLD') else 'SELF_DEPLOYMENT_PASS',
  'discovery_seed':catalog,
  'catalog_url':catalog_url,
  'provider_candidates':provider_evidence,
  'selected_provider':selected,
  'available_authorization_variable_names':available_credential_names,
  'local_staging':{'pass':local_staging_pass,'health_status':local_health.get('http_status'),'package':package},
  'remote':{'attempted':remote_deployment_attempted,'health_pass':remote_health_pass,'endpoint':remote_endpoint,'reason':remote_reason},
  'next_required_capability':next_cap,
  'canonical_mutation':False,
  'semantic_boundary':'YADO AUTONOMOUSLY DISCOVERS FREE-COMPUTE CANDIDATES FROM A USER-APPROVED PUBLIC CATALOG, RESEARCHES THEM, SELECTS BY EVIDENCE, BUILDS A SELF-PACKAGE AND FRESH-BOOT HEALTH PROOF, THEN FAILS CLOSED IF NO ALREADY-AUTHORIZED PROVIDER SESSION OR NATIVE DEPLOYMENT ADAPTER EXISTS. NO ACCOUNT BYPASS OR FAKE REMOTE DEPLOYMENT IS COUNTED.'
}
experience['experience_digest']=digest(experience)
EXP.parent.mkdir(parents=True,exist_ok=True)
EXP.write_text(json.dumps(experience,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

report={
  'schema':'yado.g2.autonomous_free_compute_self_deployment.v1',
  'status':status,
  'task_id':task['task_id'],
  'provider_candidate_count':len(provider_evidence),
  'selected_provider':selected,
  'authorization_variable_names':available_credential_names,
  'authorized_provider_session_present':authorized_provider_session,
  'local_staging_pass':local_staging_pass,
  'remote_deployment_attempted':remote_deployment_attempted,
  'remote_health_pass':remote_health_pass,
  'remote_endpoint':remote_endpoint,
  'remote_reason':remote_reason,
  'checks':checks,
  'next_required_capability':next_cap,
  'experience_digest':experience['experience_digest'],
  'canonical_mutation':False,
  'automatic_canonical_promotion':False,
  'generation_transition':False,
  'g3_genesis_performed':False,
  'semantic_boundary':experience['semantic_boundary']
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2,sort_keys=True,default=str))
if status!='PASS_SHADOW_G2_AUTONOMOUS_FREE_COMPUTE_SELF_DEPLOYMENT_V1':
    raise SystemExit(2)
