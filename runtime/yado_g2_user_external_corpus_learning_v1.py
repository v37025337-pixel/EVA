from __future__ import annotations
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
from collections import Counter,defaultdict
from urllib.parse import urlparse
import hashlib,html,json,os,re,urllib.request,urllib.error

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
CORPUS=REPO/'resources/yado-user-external-learning-corpus-v1.json'
OUT=REPO/'experience/yado-user-external-corpus-learning-v1.json'
RECEIPT=ROOT/'yado_g2_user_external_corpus_learning_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(b):return hashlib.sha256(b).hexdigest()

STOP=set('the a an and or of to in for on with from by is are be as at this that it its you your we our can use using into not no if then than via about over under after before will may do does done their they them have has had'.split())

# Public documentation can contain intentionally leaked/test credentials.
# Keep source provenance/hash intact, but never persist credential-shaped literals
# into the learned text/index. The security audit remains fail-closed.
SECRET_LIKE_PATTERNS=[
    (re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'), '[REDACTED_PRIVATE_KEY_HEADER]'),
    (re.compile(r'\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b'), '[REDACTED_GITHUB_TOKEN]'),
    (re.compile(r'\bgithub_pat_[A-Za-z0-9_]{20,}\b'), '[REDACTED_GITHUB_PAT]'),
    (re.compile(r'\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b'), '[REDACTED_OPENAI_KEY]'),
    (re.compile(r'\bAKIA[0-9A-Z]{16}\b'), '[REDACTED_AWS_ACCESS_KEY]'),
    (re.compile(r'\bAIza[0-9A-Za-z_-]{35}\b'), '[REDACTED_GOOGLE_API_KEY]'),
]
def sanitize_public_text(text):
    redactions=0
    for rx,replacement in SECRET_LIKE_PATTERNS:
        text,n=rx.subn(replacement,text)
        redactions+=n
    return text,redactions
def plain(raw:bytes,content_type=''):
    text=raw.decode('utf-8','replace')
    if 'html' in content_type.lower() or '<html' in text[:500].lower():
        text=re.sub(r'(?is)<script.*?</script>|<style.*?</style>',' ',text)
        text=re.sub(r'(?s)<[^>]+>',' ',text)
        text=html.unescape(text)
    return re.sub(r'\s+',' ',text).strip()

def tokens(text):
    xs=[x.lower() for x in re.findall(r"[A-Za-z][A-Za-z0-9_\-]{2,}",text)]
    return [x for x in xs if x not in STOP and not x.startswith('http')]

def fetch(url,timeout=16,max_bytes=350000):
    original=url
    parsed=urlparse(url)
    candidates=[url]
    if parsed.netloc.lower()=='github.com':
        parts=[x for x in parsed.path.split('/') if x]
        if len(parts)>=2:
            candidates=[
              f'https://raw.githubusercontent.com/{parts[0]}/{parts[1]}/HEAD/README.md',
              f'https://raw.githubusercontent.com/{parts[0]}/{parts[1]}/main/README.md',
              f'https://raw.githubusercontent.com/{parts[0]}/{parts[1]}/master/README.md',
              url,
            ]
    last=None
    for u in candidates:
        req=urllib.request.Request(u,headers={'User-Agent':'YADO-G2-User-External-Corpus-Learning/1.0','Accept':'text/plain,text/html,application/json,*/*'})
        try:
            with urllib.request.urlopen(req,timeout=timeout) as r:
                body=r.read(max_bytes)
                ct=str(r.headers.get('Content-Type') or '')
                txt=plain(body,ct)
                if len(txt)<80: raise ValueError('TOO_LITTLE_TEXT')
                return {'ok':True,'requested_url':original,'resolved_url':str(getattr(r,'url',u) or u),
                        'http_status':int(getattr(r,'status',200) or 200),'content_type':ct,
                        'bytes':len(body),'sha256':sha(body),'text':txt}
        except Exception as e:
            last=type(e).__name__+':'+str(e)[:220]
    return {'ok':False,'requested_url':original,'error':last}

def read_internal(rel_path,max_bytes=350000):
    rel=str(rel_path or '').strip()
    if not rel:
        return {'ok':False,'requested_url':'internal:','error':'EMPTY_INTERNAL_PATH'}
    p=(REPO/rel).resolve()
    try:
        p.relative_to(REPO.resolve())
    except Exception:
        return {'ok':False,'requested_url':'internal:'+rel,'error':'INTERNAL_PATH_ESCAPE'}
    if not p.is_file():
        return {'ok':False,'requested_url':'internal:'+rel,'error':'INTERNAL_FILE_MISSING'}
    try:
        body=p.read_bytes()[:max_bytes]
        txt=plain(body,'text/plain')
        if len(txt)<20:
            raise ValueError('TOO_LITTLE_INTERNAL_TEXT')
        return {
          'ok':True,'requested_url':'internal:'+rel,'resolved_url':rel,
          'content_type':'text/plain','bytes':len(body),'sha256':sha(body),'text':txt,
          'ids':[rel],'kinds':['internal_project_evidence'],'origins':['INTERNAL_PROJECT']
        }
    except Exception as e:
        return {'ok':False,'requested_url':'internal:'+rel,'resolved_url':rel,
                'error':type(e).__name__+':'+str(e)[:220],
                'ids':[rel],'kinds':['internal_project_evidence'],'origins':['INTERNAL_PROJECT']}

c=load(CORPUS)
sources={}
def add(row,origin):
    u=str(row.get('url') or '').strip()
    if not u:return
    x=sources.setdefault(u,{'url':u,'origins':[],'ids':[],'kinds':[]})
    x['origins'].append(origin)
    if row.get('id'):x['ids'].append(str(row['id']))
    if row.get('kind'):x['kinds'].append(str(row['kind']))

for row in c.get('user_screenshot_recovered_public_sources',[]):add(row,'USER_SCREENSHOT')
for row in c.get('user_shared_repositories_and_platforms',[]):add(row,'USER_LINK')
for u in c.get('user_shared_arxiv',[]):add({'url':u,'id':u.rsplit('/',1)[-1],'kind':'research_paper'},'USER_ARXIV')

records=[]
with ThreadPoolExecutor(max_workers=8) as ex:
    fut={ex.submit(fetch,u):u for u in sorted(sources)}
    for f in as_completed(fut):
        u=fut[f];meta=sources[u]
        try:r=f.result()
        except Exception as e:r={'ok':False,'requested_url':u,'error':type(e).__name__+':'+str(e)[:220]}
        out={k:v for k,v in r.items() if k!='text'}
        out.update({'ids':sorted(set(meta['ids'])),'kinds':sorted(set(meta['kinds'])),'origins':sorted(set(meta['origins']))})
        if r.get('ok'):
            txt=r['text']
            safe_txt,redaction_count=sanitize_public_text(txt)
            cnt=Counter(tokens(safe_txt))
            out['text_chars']=len(txt)
            out['top_terms']=[{'token':t,'count':n} for t,n in cnt.most_common(40)]
            out['text_excerpt']=safe_txt[:14000]
            if redaction_count:
                out['secret_like_redactions']=redaction_count
            out['learnable_unit_digest']=digest({'sha256':out['sha256'],'terms':out['top_terms'],'excerpt':out['text_excerpt']})
        records.append(out)

# Internal project evidence is actual training evidence, not merely a pointer list.
# It is read-only, bounded, sanitized with the same secret-like filters, and indexed
# into the same experience graph as public evidence.
for rel in c.get('internal_project_evidence_to_reuse',[]):
    r=read_internal(rel)
    out={k:v for k,v in r.items() if k!='text'}
    if r.get('ok'):
        txt=r['text']
        safe_txt,redaction_count=sanitize_public_text(txt)
        cnt=Counter(tokens(safe_txt))
        out['text_chars']=len(txt)
        out['top_terms']=[{'token':t,'count':n} for t,n in cnt.most_common(40)]
        out['text_excerpt']=safe_txt[:14000]
        if redaction_count:
            out['secret_like_redactions']=redaction_count
        out['learnable_unit_digest']=digest({'sha256':out['sha256'],'terms':out['top_terms'],'excerpt':out['text_excerpt']})
    records.append(out)

records.sort(key=lambda x:x.get('requested_url',''))
ok=[x for x in records if x.get('ok')]
fail=[x for x in records if not x.get('ok')]

# Generic, domain-neutral co-occurrence graph. This is only corpus indexing;
# no target mechanism, repair rule, or architecture label is encoded.
term_docs=defaultdict(set)
for i,r in enumerate(ok):
    for z in r.get('top_terms',[])[:25]:term_docs[z['token']].add(i)
edges=[]
terms=sorted(term_docs)
for i,a in enumerate(terms):
    da=term_docs[a]
    if len(da)<2:continue
    for b in terms[i+1:]:
        db=term_docs[b]
        inter=len(da&db)
        if inter<2:continue
        union=len(da|db)
        j=inter/union
        if j>=0.25:edges.append({'a':a,'b':b,'shared_docs':inter,'jaccard':round(j,6)})
edges.sort(key=lambda z:(-z['jaccard'],-z['shared_docs'],z['a'],z['b']))
edges=edges[:1200]

experience={
 'schema':'yado.user_external_corpus_learning.v1',
 'status':'LEARNED_EXTERNAL_CORPUS' if len(ok)>=20 else 'WITHHOLD_EXTERNAL_CORPUS',
 'corpus_digest':digest(c),
 'source_count':len(records),'fetched_count':len(ok),'failed_count':len(fail),
 'records':records,
 'generic_cooccurrence_graph':{'edge_count':len(edges),'edges':edges},
 'internal_project_evidence_to_reuse':c.get('internal_project_evidence_to_reuse',[]),
 'excluded_private_screenshot_classes':c.get('excluded_private_screenshot_classes',[]),
 'construction_instruction':c.get('construction_instruction'),
 'canonical_mutation':False,
 'semantic_boundary':'PUBLIC EXTERNAL AND REPOSITORY-LOCAL EVIDENCE INGESTION WITH GENERIC CONTENT INDEXING ONLY. NO SOURCE IS COPIED AS A READY YADO ARCHITECTURE OR REPAIR. NO THIRD-PARTY CODE IS EXECUTED.'
}
experience['experience_digest']=digest(experience)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(experience,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
receipt={
 'schema':'yado.g2.user_external_corpus_learning.receipt.v1',
 'status':'PASS_G2_USER_EXTERNAL_CORPUS_LEARNING_V1' if experience['status']=='LEARNED_EXTERNAL_CORPUS' else 'WITHHOLD_G2_USER_EXTERNAL_CORPUS_LEARNING_V1',
 'source_count':len(records),'fetched_count':len(ok),'failed_count':len(fail),
 'experience_digest':experience['experience_digest'],
 'failure_sample':[{'url':x.get('requested_url'),'error':x.get('error')} for x in fail[:12]],
 'third_party_code_executed':False,'canonical_mutation':False,
 'next_required_capability':'YADO_NATIVE_SELF_CREATED_CONSTRUCTOR_FROM_LEARNED_CORPUS_V1',
 'semantic_boundary':experience['semantic_boundary']
}
receipt['receipt_sha256']=digest(receipt)
RECEIPT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps(receipt,indent=2,sort_keys=True))
if receipt['status']!='PASS_G2_USER_EXTERNAL_CORPUS_LEARNING_V1':raise SystemExit(2)
