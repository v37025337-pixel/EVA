from __future__ import annotations
from collections import Counter
from pathlib import Path
import hashlib,importlib.util,json,math,os,re,subprocess,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

REG=REPO/'canonical'/'yado-unified-experience-registry-v1.json'
HEAD=REPO/'canonical'/'yado-main-head-g2.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
META=REPO/'candidates'/'g2-self-evolution'/'legacy_experience_retriever_v2.json'
SRC=REPO/'candidates'/'g2-self-evolution'/'legacy_experience_retriever_v2.py'
OUT=ROOT/'yado_legacy_experience_retrieval_fresh_admission_v2_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def bsha(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def toks(s):return [x for x in re.findall(r"[a-zA-Z0-9_]+",str(s).lower()) if len(x)>3]
def run(cmd,timeout=25):return subprocess.run(cmd,cwd=REPO,capture_output=True,timeout=timeout)

reg=load(REG);head=load(HEAD);ledger=load(LEDGER);meta=load(META)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['LEGACY_EXPERIENCE_RETRIEVAL_FRESH_ADMISSION_V2']:
    raise RuntimeError('UNEXPECTED_FRONTIER')
if meta.get('state')!='AUTHORIZED_FOR_SHADOW_ADMISSION':
    raise RuntimeError('V2_NOT_AUTHORIZED')
if hashlib.sha256(SRC.read_bytes()).hexdigest()!=meta['candidate_source_sha256']:
    raise RuntimeError('V2_SOURCE_DRIFT')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):
    raise RuntimeError('HEAD_LEDGER_MISMATCH')

sp=importlib.util.spec_from_file_location('legacy_retriever_v2_admission',SRC)
mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod)
retr=mod.LegacyExperienceRetrieverV1(REPO,reg)

legacy=[e for e in reg['branches'] if e.get('mode')=='EXPERIENCE_ONLY']
# Exact bytes and content corpus.
branch_content={}
exact=[]
for e in legacy:
    parts=[];ok=True
    for path in e.get('evidence',[]):
        item=retr.read_registered(e['branch'],path);parts.append(item['content'])
        spec=f"{e['head_sha']}:{path}"
        cp=run(['git','show',spec],8)
        if cp.returncode!=0:
            ft=run(['git','fetch','--no-tags','--depth=1','origin',e['head_sha']],30)
            cp=run(['git','show',spec],12) if ft.returncode==0 else cp
        match=cp.returncode==0 and bsha(cp.stdout)==item['sha256']
        exact.append({'branch':e['branch'],'path':path,'match':match,'sha256':item['sha256']})
        ok=ok and match
    branch_content[e['branch']]='\n'.join(parts)

# Build fresh blind queries from distinctive CONTENT tokens only.
STOP={'this','that','with','from','true','false','none','return','import','runtime','yado','receipt','latest','status','pass','branch','candidate','canonical','self','core','json','schema','version','python'}
per={b:Counter(t for t in toks(txt) if t not in STOP and not t.isdigit()) for b,txt in branch_content.items()}
df=Counter()
for c in per.values():
    for t in c:df[t]+=1
queries=[]
n=len(per)
for b,c in sorted(per.items()):
    ranked=[]
    for t,tf in c.items():
        idf=math.log((n+1)/(df[t]+0.5))
        ranked.append((tf*idf,t))
    ranked.sort(key=lambda x:(-x[0],x[1]))
    chosen=[]
    for _,t in ranked:
        if t not in chosen:
            chosen.append(t)
        if len(chosen)>=4:break
    if len(chosen)>=2:
        queries.append({'query':' '.join(chosen),'expected_branch':b,'source':'CONTENT_TFIDF_DERIVED'})

rows=[];hits=0;top3=0
for q in queries:
    res=retr.search_content(q['query'],limit=8)
    found=any(x['branch']==q['expected_branch'] for x in res)
    in_top3=any(x['branch']==q['expected_branch'] for x in res[:3])
    hits+=found;top3+=in_top3
    rows.append(q|{'found':found,'top3':in_top3,'top':[{'branch':x['branch'],'path':x['path'],'score':x['score']} for x in res[:5]]})
blind_acc=hits/max(1,len(rows));top3_acc=top3/max(1,len(rows))

# Fresh paraphrased cross-topic queries not present in V2 selection.
cross=[
 ('historical boot package reconstruction checksum','yado-v28-runtime'),
 ('older cognitive learning loop memory strategy','yado-v29-cognitive'),
 ('migration overlay regression candidate state','yado-rc8-candidate'),
 ('internet research evidence evolution source','yado-rc8-v33-evolution'),
 ('training internet developmental evidence','yado-rc8-v35-training'),
 ('attention workspace functional ablation metacognition','yado-rc8-consciousness-ab'),
 ('causal workspace broadcast source monitoring','yado-rc8-digital-consciousness-v1'),
 ('consistency split brain external verification audit','yado-rc8-v37-digital-consciousness'),
 ('integrity repair rollback diagnosis fail closed','yado-kernel-task-v37-repair'),
]
cross_rows=[]
for q,b in cross:
    res=retr.search_content(q,limit=8)
    cross_rows.append({'query':q,'expected_branch':b,'found':any(x['branch']==b for x in res),
                       'top':[{'branch':x['branch'],'path':x['path'],'score':x['score']} for x in res[:5]]})
cross_acc=sum(x['found'] for x in cross_rows)/len(cross_rows)

# Negative and safety controls.
negative=[]
for b,p in [
 ('yado-v35-training','../secret'),
 ('yado-v35-training','nonregistered.txt'),
 ('yado-architecture-shadow-search','architecture/evolution-ledger.json'),
 ('unknown-branch','x.py'),
]:
    refused=False
    try:retr.read_registered(b,p)
    except Exception:refused=True
    negative.append({'branch':b,'path':p,'refused':refused})

checks={
 'exact_bytes_all_registered':all(x['match'] for x in exact),
 'content_derived_blind':blind_acc>=.85,
 'content_derived_top3':top3_acc>=.65,
 'fresh_cross_queries':cross_acc>=.88,
 'negative_controls':all(x['refused'] for x in negative),
 'source_unchanged':hashlib.sha256(SRC.read_bytes()).hexdigest()==meta['candidate_source_sha256'],
 'canonical_head_immutable':ledger.get('current_head_digest')==head.get('canonical_head_digest'),
}
passed=all(checks.values())
next_cap='LEGACY_EXPERIENCE_RETRIEVAL_CANONICAL_INTEGRATION_V1' if passed else 'LEGACY_EXPERIENCE_SEARCH_EVOLUTION_REPAIR_V3'

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
 'schema':'yado.g2.legacy_experience_retrieval_fresh_admission.v2',
 'status':'PASS_LEGACY_EXPERIENCE_RETRIEVAL_FRESH_ADMISSION_V2' if passed else 'WITHHOLD_LEGACY_EXPERIENCE_RETRIEVAL_FRESH_ADMISSION_V2',
 'candidate_digest':meta['candidate_digest'],'candidate_source_sha256':meta['candidate_source_sha256'],
 'metrics':{'exact_accuracy':sum(x['match'] for x in exact)/len(exact),'content_blind_accuracy':blind_acc,
            'content_top3_accuracy':top3_acc,'cross_query_accuracy':cross_acc},
 'content_blind':rows,'cross_queries':cross_rows,'negative_controls':negative,'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'FRESH V2 ADMISSION USES CONTENT-DERIVED BLIND QUERIES AND INDEPENDENT EXACT-BYTE ORACLE. HISTORICAL CODE REMAINS DATA ONLY.'
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_LEGACY_EXPERIENCE_RETRIEVAL_FRESH_ADMISSION_V2",
   'event_type':'KERNEL_EVOLVED_CODE_FRESH_ADMISSION_V2','status':'PASS_SHADOW' if passed else 'WITHHOLD',
   'generation':ledger['current_head'],'deficit':'LEGACY_EXPERIENCE_RETRIEVAL_FRESH_ADMISSION_V2',
   'effect':'SELF_EVOLVED_V2_LEGACY_RETRIEVER_ADMISSION_PASS' if passed else 'SELF_EVOLVED_V2_LEGACY_RETRIEVER_WITHHELD',
   'source_path':f'receipts/yado-legacy-experience-retrieval-fresh-admission-v2-run-{run_id}.json',
   'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
   'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({'status':receipt['status'],'metrics':receipt['metrics'],'checks':checks,
 'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('LEGACY_EXPERIENCE_V2_ADMISSION_WITHHELD')
