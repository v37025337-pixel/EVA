from __future__ import annotations
from pathlib import Path
import hashlib,json,os,re,time,urllib.request,urllib.error

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent

RAW_BASE='https://raw.githubusercontent.com/vava-nessa/free-coding-models/main/'
API_COMMIT='https://api.github.com/repos/vava-nessa/free-coding-models/commits/main'
OUT=REPO/'candidates'/'kernel-self-generated'/'g2-fcm-external-coding-resource-study-v1.json'

FILES=['README.md','sources.js','package.json','SECURITY.md','docs/development.md']

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def sha_bytes(b): return hashlib.sha256(b).hexdigest()

def fetch(url,timeout=20):
    req=urllib.request.Request(url,headers={'User-Agent':'YADO-G2-External-Resource-Study/1.0','Accept':'application/vnd.github+json, text/plain, */*'})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        body=r.read()
        return {'status':int(getattr(r,'status',200) or 200),'headers':dict(r.headers.items()),'body':body}

def decode(b): return b.decode('utf-8','replace')

def parse_model_arrays(src):
    arrays={}
    pat=re.compile(r'export\s+const\s+([A-Za-z0-9_]+)\s*=\s*\[(.*?)\n\]',re.S)
    for m in pat.finditer(src):
        name=m.group(1);body=m.group(2)
        ids=re.findall(r"\[\s*['\"]([^'\"]+)['\"]\s*,",body)
        if ids: arrays[name]=ids
    return arrays

def parse_sources(src):
    providers={}
    in_sources=False; current=None
    for line in src.splitlines():
        if re.search(r'export\s+const\s+sources\s*=\s*\{',line):
            in_sources=True; continue
        if not in_sources: continue
        if current is None and re.match(r'^\s*}\s*;?\s*$',line):
            break
        m=re.match(r"^\s*(?:'([^']+)'|([A-Za-z0-9_-]+))\s*:\s*\{\s*$",line)
        if m:
            key=m.group(1) or m.group(2)
            current={'provider_key':key};providers[key]=current;continue
        if current is None: continue
        if re.match(r'^\s*}\s*,?\s*$',line):
            current=None;continue
        for field in ('name','url','quota','quotaCode'):
            mm=re.match(r"^\s*"+field+r"\s*:\s*['\"]([^'\"]*)['\"]",line)
            if mm: current[field]=mm.group(1)
        mm=re.match(r'^\s*models\s*:\s*([A-Za-z0-9_]+)',line)
        if mm: current['models_var']=mm.group(1)
        if re.match(r'^\s*noKeyNeeded\s*:\s*true',line):
            current['no_key_needed']=True
        if re.match(r'^\s*zenOnly\s*:\s*true',line):
            current['zen_only']=True
    return providers

def tier_score(label):
    t=(label or '').upper()
    return {'S+':1.0,'S':.92,'A+':.85,'A':.78,'A-':.72,'B+':.64,'B':.58,'C':.45}.get(t,.5)

def parse_tiers(src,arrays):
    out={}
    for var,ids in arrays.items():
        # Local slice is enough to map tuple metadata without executing JS.
        pos=src.find('export const '+var)
        if pos<0: continue
        nextpos=src.find('\n]',pos)
        chunk=src[pos:nextpos+2] if nextpos>pos else src[pos:pos+10000]
        rows={}
        for m in re.finditer(r"\[\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]*)['\"]\s*,\s*['\"]([^'\"]*)['\"]\s*,\s*['\"]([^'\"]*)['\"]\s*,\s*['\"]([^'\"]*)['\"]",chunk):
            rows[m.group(1)]={'label':m.group(2),'tier':m.group(3),'swe_score':m.group(4),'ctx':m.group(5)}
        out[var]=rows
    return out

def probe_openai(provider,model):
    url=provider.get('url')
    if not url or not provider.get('no_key_needed'):
        return {'attempted':False,'reason':'KEY_REQUIRED_OR_NO_URL'}
    payload={
      'model':model,
      'messages':[{'role':'user','content':'Synthetic coding connectivity check. Reply with only this exact text: return a + b'}],
      'temperature':0,
      'max_tokens':32,
    }
    data=json.dumps(payload).encode()
    req=urllib.request.Request(url,data=data,method='POST',headers={
      'Content-Type':'application/json',
      'Accept':'application/json',
      'User-Agent':'YADO-G2-External-Resource-Study/1.0',
    })
    t0=time.monotonic()
    try:
        with urllib.request.urlopen(req,timeout=18) as r:
            body=r.read(200000)
            dt=time.monotonic()-t0
            status=int(getattr(r,'status',200) or 200)
            text=decode(body)
            content=''
            try:
                j=json.loads(text)
                content=str((((j.get('choices') or [{}])[0].get('message') or {}).get('content') or ''))
            except Exception:
                pass
            norm=re.sub(r'\s+',' ',content).strip().lower()
            coding_ok='return a + b' in norm or 'return a+b' in norm
            return {
              'attempted':True,'http_status':status,'latency_seconds':round(dt,4),
              'response_json':bool(content),'synthetic_coding_check_pass':coding_ok,
              'response_digest':sha_bytes(body),
            }
    except urllib.error.HTTPError as e:
        body=e.read(100000)
        return {'attempted':True,'http_status':int(e.code),'error_type':'HTTPError','response_digest':sha_bytes(body)}
    except Exception as e:
        return {'attempted':True,'http_status':None,'error_type':type(e).__name__,'error':str(e)[:300]}

# Fetch only text evidence; never install/execute third-party code.
evidence={}
for rel in FILES:
    try:
        r=fetch(RAW_BASE+rel)
        evidence[rel]={'status':r['status'],'sha256':sha_bytes(r['body']),'bytes':len(r['body']),'text':decode(r['body'])}
    except Exception as e:
        evidence[rel]={'status':None,'error':type(e).__name__+':'+str(e)[:300]}

try:
    cr=fetch(API_COMMIT)
    cj=json.loads(decode(cr['body']))
    upstream_commit={'sha':cj.get('sha'),'html_url':cj.get('html_url'),'commit_message':((cj.get('commit') or {}).get('message') or '')[:500]}
except Exception as e:
    upstream_commit={'sha':None,'error':type(e).__name__+':'+str(e)[:300]}

required_ok=all(evidence.get(x,{}).get('status')==200 for x in ('README.md','sources.js','package.json'))
src=evidence.get('sources.js',{}).get('text','')
arrays=parse_model_arrays(src) if src else {}
providers=parse_sources(src) if src else {}
tiers=parse_tiers(src,arrays) if src else {}

for p in providers.values():
    var=p.get('models_var')
    p['model_count']=len(arrays.get(var,[]))
    p['model_ids']=arrays.get(var,[])
    p['no_key_needed']=bool(p.get('no_key_needed',False))

package={}
try: package=json.loads(evidence.get('package.json',{}).get('text','{}'))
except Exception: package={}

# Kernel evaluates no-key candidates from the upstream catalog only.
probes=[]
for key,p in sorted(providers.items()):
    if not p.get('no_key_needed') or not p.get('model_ids'):
        continue
    # Prefer strongest declared tier within that provider, without trusting benchmark as proof.
    rows=tiers.get(p.get('models_var'),{})
    ranked=sorted(p['model_ids'],key=lambda mid:(-tier_score((rows.get(mid) or {}).get('tier')),mid))
    model=ranked[0]
    pr=probe_openai(p,model)
    meta=rows.get(model,{})
    probes.append({
      'provider_key':key,'provider_name':p.get('name'),'url':p.get('url'),
      'model_id':model,'declared_tier':meta.get('tier'),'declared_swe_score':meta.get('swe_score'),
      'declared_ctx':meta.get('ctx'),'probe':pr,
    })

# Evidence-based shadow selection. Live synthetic success dominates static catalog rank.
for row in probes:
    pr=row['probe']
    row['selection_score']=(
      (1.0 if pr.get('http_status')==200 else 0.0)*0.60+
      (1.0 if pr.get('synthetic_coding_check_pass') else 0.0)*0.25+
      tier_score(row.get('declared_tier'))*0.15
    )
probes.sort(key=lambda x:(-x['selection_score'],x['provider_key'],x['model_id']))
selected=next((x for x in probes if x['probe'].get('http_status')==200 and x['probe'].get('synthetic_coding_check_pass')),None)

runtime_deps=package.get('dependencies') or {}
scripts=package.get('scripts') or {}
readme=evidence.get('README.md',{}).get('text','')
security=evidence.get('SECURITY.md',{}).get('text','')

checks={
  'required_upstream_text_fetched':required_ok,
  'provider_catalog_parsed':len(providers)>=10,
  'model_catalog_parsed':sum(p.get('model_count',0) for p in providers.values())>=100,
  'no_key_candidates_discovered':len(probes)>=1,
  'third_party_code_not_executed':True,
  'no_user_secrets_used':True,
  'canonical_mutation_false':True,
}
status='PASS_SHADOW_G2_FCM_EXTERNAL_CODING_RESOURCE_STUDY_V1' if all(checks.values()) else 'WITHHOLD_G2_FCM_EXTERNAL_CODING_RESOURCE_STUDY_V1'

report={
  'schema':'yado.g2.fcm_external_coding_resource_study.v1',
  'status':status,
  'upstream':{
    'repository':'vava-nessa/free-coding-models',
    'commit':upstream_commit,
    'file_evidence':{k:{kk:vv for kk,vv in v.items() if kk!='text'} for k,v in evidence.items()},
  },
  'catalog':{
    'provider_count':len(providers),
    'model_count':sum(p.get('model_count',0) for p in providers.values()),
    'no_key_provider_keys':sorted(k for k,p in providers.items() if p.get('no_key_needed')),
    'providers':{k:{kk:vv for kk,vv in p.items() if kk!='model_ids'} for k,p in sorted(providers.items())},
  },
  'package_audit':{
    'name':package.get('name'),'version':package.get('version'),
    'runtime_dependencies':runtime_deps,'runtime_dependency_count':len(runtime_deps),
    'script_names':sorted(scripts),
    'telemetry_disable_documented':('--no-telemetry' in readme or 'FREE_CODING_MODELS_TELEMETRY' in readme),
    'security_policy_fetched':evidence.get('SECURITY.md',{}).get('status')==200,
  },
  'live_no_key_probes':probes,
  'selected_shadow_resource':selected,
  'integration_decision':(
    'SHADOW_CODING_RESOURCE_CANDIDATE_AVAILABLE' if selected else
    'STATIC_RESOURCE_DISCOVERY_ONLY_NO_LIVE_NO_KEY_CANDIDATE'
  ),
  'checks':checks,
  'canonical_mutation':False,
  'architecture_mutation':False,
  'generation_transition':False,
  'g3_genesis_performed':False,
  'semantic_boundary':'READ-ONLY STUDY OF AN EXTERNAL OPEN-SOURCE CATALOG PLUS SYNTHETIC NO-KEY CONNECTIVITY PROBES. NO THIRD-PARTY PACKAGE IS INSTALLED OR EXECUTED, NO USER CODE OR SECRETS ARE SENT, AND ANY USABLE MODEL REMAINS A SHADOW RESOURCE CANDIDATE.',
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
  'status':status,
  'upstream_commit':upstream_commit,
  'provider_count':report['catalog']['provider_count'],
  'model_count':report['catalog']['model_count'],
  'no_key_provider_keys':report['catalog']['no_key_provider_keys'],
  'live_no_key_probes':probes,
  'selected_shadow_resource':selected,
  'integration_decision':report['integration_decision'],
  'checks':checks,
  'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True,default=str))
if status!='PASS_SHADOW_G2_FCM_EXTERNAL_CODING_RESOURCE_STUDY_V1':
    raise SystemExit(2)
