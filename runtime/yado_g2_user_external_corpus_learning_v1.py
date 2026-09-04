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
            cnt=Counter(tokens(txt))
            out['text_chars']=len(txt)
            out['top_terms']=[{'token':t,'count':n} for t,n in cnt.most_common(40)]
            out['text_excerpt']=txt[:14000]
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
 'semantic_boundary':'PUBLIC EXTERNAL EVIDENCE INGESTION AND GENERIC CONTENT INDEXING ONLY. NO SOURCE IS COPIED AS A READY YADO ARCHITECTURE OR REPAIR. NO THIRD-PARTY CODE IS EXECUTED.'
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
