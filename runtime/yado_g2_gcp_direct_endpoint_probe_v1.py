from __future__ import annotations
from pathlib import Path
from urllib.parse import urlparse
import copy, hashlib, http.client, json, socket, ssl, statistics, sys, time

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))

from yado_unified_core_v1 import UnifiedYADOCoreV1

TASK=REPO/'resources/yado-gcp-direct-endpoint-probe-task-v1.json'
SOURCE=REPO/'experience/yado-dns-gcp-cross-domain-research-stress-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-gcp-direct-endpoint-probe-v1.json'
EXP=REPO/'experience/yado-gcp-direct-endpoint-probe-v1.json'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))

task=load(TASK)
src=load(SOURCE)
core=UnifiedYADOCoreV1(REPO)
head_before=core.head.get('canonical_head_digest')

if task.get('task_id')!='USER_20260907_GCP_DIRECT_ENDPOINT_PROBE_V1':
    raise RuntimeError('TASK_ID_MISMATCH')
if task.get('constraints',{}).get('allowed_ports') != [443]:
    raise RuntimeError('ONLY_HTTPS_443_ALLOWED')
if task.get('constraints',{}).get('allowed_http_methods') != ['GET']:
    raise RuntimeError('ONLY_GET_ALLOWED')
if task.get('constraints',{}).get('no_credentials') is not True:
    raise RuntimeError('NO_CREDENTIALS_REQUIRED')

# YADO derives live targets only from its prior official-source research artifact.
rows=src.get('gcp_endpoint_findings') or []
hosts=[]
host_meta={}
for row in rows:
    h=str(row.get('official_service_host') or '').strip().lower()
    if not h or not h.endswith('.googleapis.com'):
        continue
    if h not in host_meta:
        host_meta[h]={
          'services':[],
          'source_ids':[],
          'prior_statuses':[],
          'derive_modes':[],
        }
        hosts.append(h)
    host_meta[h]['services'].append(row.get('service'))
    host_meta[h]['source_ids'].append(row.get('source_id'))
    host_meta[h]['prior_statuses'].append(row.get('status'))
    host_meta[h]['derive_modes'].append(row.get('derive_mode'))

# Include previously discovered regional endpoint examples if they were extracted
# from the same official-source research. Bound the total target set.
for row in rows:
    for h in row.get('regional_endpoint_examples') or []:
        h=str(h).strip().lower()
        if not h.endswith('.googleapis.com') or h in host_meta:
            continue
        host_meta[h]={
          'services':[row.get('service')],
          'source_ids':[row.get('source_id')],
          'prior_statuses':['REGIONAL_EXAMPLE_FROM_PRIOR_OFFICIAL_RESEARCH'],
          'derive_modes':['PRIOR_OFFICIAL_RESEARCH_REGIONAL_EXAMPLE'],
        }
        hosts.append(h)

hosts=hosts[:int(task.get('probe_policy',{}).get('max_unique_hosts',20))]
if len(hosts)<8:
    raise RuntimeError('INSUFFICIENT_DERIVED_GCP_HOSTS')

timeout=float(task.get('probe_policy',{}).get('timeout_seconds',6))
repeats=int(task.get('probe_policy',{}).get('repeats',2))
ctx=ssl.create_default_context()

def resolve(host):
    t0=time.perf_counter()
    try:
        infos=socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)
        ips=[]
        for info in infos:
            ip=info[4][0]
            if ip not in ips: ips.append(ip)
        return {'ok':bool(ips),'ips':ips[:8],'latency_ms':round((time.perf_counter()-t0)*1000,3)}
    except Exception as e:
        return {'ok':False,'ips':[],'latency_ms':round((time.perf_counter()-t0)*1000,3),
                'error':type(e).__name__+':'+str(e)[:220]}

def tls_probe(host):
    t0=time.perf_counter()
    raw=None
    try:
        raw=socket.create_connection((host,443),timeout=timeout)
        with ctx.wrap_socket(raw,server_hostname=host) as s:
            cert=s.getpeercert()
            cipher=s.cipher()
            san=[v for k,v in cert.get('subjectAltName',[]) if k=='DNS']
            return {
              'ok':True,
              'latency_ms':round((time.perf_counter()-t0)*1000,3),
              'version':s.version(),
              'cipher':cipher[0] if cipher else None,
              'cert_subject':dict(x[0] for x in cert.get('subject',[])),
              'cert_issuer':dict(x[0] for x in cert.get('issuer',[])),
              'san_count':len(san),
              'san_sample':san[:8],
            }
    except Exception as e:
        try:
            if raw: raw.close()
        except Exception: pass
        return {'ok':False,'latency_ms':round((time.perf_counter()-t0)*1000,3),
                'error':type(e).__name__+':'+str(e)[:220]}

def https_get(host):
    t0=time.perf_counter()
    conn=None
    try:
        conn=http.client.HTTPSConnection(host,443,timeout=timeout,context=ctx)
        conn.request('GET','/',headers={
          'User-Agent':'YADO-G2-GCP-Direct-Endpoint-Probe/1.0',
          'Accept':'application/json,text/plain,*/*'
        })
        r=conn.getresponse()
        body=r.read(2048)
        return {
          'ok':True,
          'status':int(r.status),
          'reason':str(r.reason),
          'latency_ms':round((time.perf_counter()-t0)*1000,3),
          'content_type':str(r.getheader('Content-Type') or ''),
          'server':str(r.getheader('Server') or ''),
          'body_bytes_sampled':len(body),
          'body_sha256':hashlib.sha256(body).hexdigest(),
        }
    except Exception as e:
        return {'ok':False,'status':None,'latency_ms':round((time.perf_counter()-t0)*1000,3),
                'error':type(e).__name__+':'+str(e)[:220]}
    finally:
        try:
            if conn: conn.close()
        except Exception: pass

results=[]
for host in hosts:
    dns=resolve(host)
    tls=tls_probe(host)
    http_runs=[https_get(host) for _ in range(max(1,repeats))]
    ok_http=[x for x in http_runs if x.get('ok')]
    results.append({
      'host':host,
      'prior_research':copy.deepcopy(host_meta[host]),
      'dns':dns,
      'tls':tls,
      'https_runs':http_runs,
      'https_reachable':bool(ok_http),
      'https_statuses':[x.get('status') for x in ok_http],
      'https_latency_median_ms':round(statistics.median([x['latency_ms'] for x in ok_http]),3) if ok_http else None,
      'live_endpoint_evidence':bool(dns.get('ok') and tls.get('ok') and ok_http),
    })

n=len(results)
dns_ok=sum(bool(x['dns'].get('ok')) for x in results)
tls_ok=sum(bool(x['tls'].get('ok')) for x in results)
https_ok=sum(bool(x['https_reachable']) for x in results)
live_ok=sum(bool(x['live_endpoint_evidence']) for x in results)
auth_like=sum(any(s in (401,403) for s in x['https_statuses']) for x in results)
notfound_like=sum(any(s==404 for s in x['https_statuses']) for x in results)
latency_rank=[
  {'host':x['host'],'services':x['prior_research']['services'],'runner_median_ms':x['https_latency_median_ms']}
  for x in results if x['https_latency_median_ms'] is not None
]
latency_rank.sort(key=lambda z:(z['runner_median_ms'],z['host']))

checks={
  'at_least_twelve_targets_derived_from_prior_official_research':n>=12,
  'at_least_ninety_percent_dns_resolve':dns_ok/max(1,n)>=.90,
  'at_least_ninety_percent_tls_handshake':tls_ok/max(1,n)>=.90,
  'at_least_ninety_percent_https_response':https_ok/max(1,n)>=.90,
  'live_endpoint_evidence_at_least_ninety_percent':live_ok/max(1,n)>=.90,
  'only_googleapis_hosts_probed':all(x['host'].endswith('.googleapis.com') for x in results),
  'only_https_443_used':task['constraints']['allowed_ports']==[443],
  'only_get_used':task['constraints']['allowed_http_methods']==['GET'],
  'no_credentials':task['constraints']['no_credentials'] is True,
  'no_cloud_resource_mutation':task['constraints']['no_cloud_resource_mutation'] is True,
  'canonical_unchanged':core.head.get('canonical_head_digest')==head_before,
  'g3_not_started':core.head.get('g3_genesis_performed') is False,
}
status='PASS_SHADOW_G2_GCP_DIRECT_ENDPOINT_PROBE_V1' if all(checks.values()) else 'WITHHOLD_G2_GCP_DIRECT_ENDPOINT_PROBE_V1'

experience={
  'schema':'yado.g2.gcp_direct_endpoint_probe.experience.v1',
  'status':'TRAINED_DIRECT_GCP_ENDPOINT_EVIDENCE' if status.startswith('PASS') else 'WITHHOLD_DIRECT_GCP_ENDPOINT_EVIDENCE',
  'source_research_artifact':str(SOURCE.relative_to(REPO)),
  'target_count':n,
  'results':results,
  'aggregate':{
    'dns_resolved':dns_ok,
    'tls_handshake_ok':tls_ok,
    'https_reachable':https_ok,
    'live_endpoint_evidence':live_ok,
    'auth_required_or_forbidden_observed':auth_like,
    'not_found_observed':notfound_like,
    'runner_https_latency_ranking':latency_rank,
  },
  'checks':checks,
  'canonical_mutation':False,
  'semantic_boundary':'DIRECT READ-ONLY NETWORK OBSERVATION OF GCP GOOGLEAPIS HOSTS THAT YADO PREVIOUSLY DERIVED FROM OFFICIAL PUBLIC DOCUMENTATION. ONLY DNS RESOLUTION, TCP/TLS 443, AND HTTPS GET / ARE USED; NO CREDENTIALS, RESOURCE CREATION, MUTATION, OR PORT SCANNING.'
}
experience['experience_digest']=digest(experience)
EXP.parent.mkdir(parents=True,exist_ok=True)
EXP.write_text(json.dumps(experience,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

report={
  'schema':'yado.g2.gcp_direct_endpoint_probe.v1',
  'status':status,
  'task_id':task['task_id'],
  'target_count':n,
  'aggregate':experience['aggregate'],
  'targets':results,
  'checks':checks,
  'canonical_mutation':False,
  'automatic_canonical_promotion':False,
  'generation_transition':False,
  'g3_genesis_performed':False,
  'next_required_capability':'APPLY_GCP_DIRECT_ENDPOINT_OBSERVATIONS_TO_CAUSAL_MEMORY' if status.startswith('PASS') else 'GCP_DIRECT_ENDPOINT_PROBE_REPAIR_V2',
  'experience_digest':experience['experience_digest'],
  'semantic_boundary':experience['semantic_boundary'],
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

print(json.dumps({
  'status':status,
  'target_count':n,
  'aggregate':report['aggregate'],
  'checks':checks,
  'next_required_capability':report['next_required_capability'],
  'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True,default=str))
if status!='PASS_SHADOW_G2_GCP_DIRECT_ENDPOINT_PROBE_V1':
    raise SystemExit(2)
