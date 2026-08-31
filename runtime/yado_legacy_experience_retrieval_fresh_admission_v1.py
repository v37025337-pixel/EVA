from __future__ import annotations
from pathlib import Path
import hashlib,importlib.util,json,os,subprocess,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

REG=REPO/'canonical'/'yado-unified-experience-registry-v1.json'
HEAD=REPO/'canonical'/'yado-main-head-g2.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
META=REPO/'candidates'/'g2-self-evolution'/'legacy_experience_retriever_v1.json'
SRC=REPO/'candidates'/'g2-self-evolution'/'legacy_experience_retriever_v1.py'
OUT=ROOT/'yado_legacy_experience_retrieval_fresh_admission_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def bsha(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def run(cmd,timeout=25):return subprocess.run(cmd,cwd=REPO,capture_output=True,timeout=timeout)

reg=load(REG);head=load(HEAD);ledger=load(LEDGER);meta=load(META)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['LEGACY_EXPERIENCE_RETRIEVAL_FRESH_ADMISSION_V1']:
    raise RuntimeError('UNEXPECTED_FRONTIER')
if meta.get('state')!='AUTHORIZED_FOR_SHADOW_ADMISSION':
    raise RuntimeError('CANDIDATE_NOT_READY')
if hashlib.sha256(SRC.read_bytes()).hexdigest()!=meta.get('candidate_source_sha256'):
    raise RuntimeError('CANDIDATE_SOURCE_DRIFT')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):
    raise RuntimeError('HEAD_LEDGER_MISMATCH')

sp=importlib.util.spec_from_file_location('legacy_retriever_candidate_fresh',SRC)
mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod)
retr=mod.LegacyExperienceRetrieverV1(REPO,reg)

legacy=[x for x in reg['branches'] if x.get('mode')=='EXPERIENCE_ONLY']
refs=[{'branch':e['branch'],'commit':e['head_sha'],'path':p}
      for e in legacy for p in e.get('evidence',[])]

# Independent oracle uses exact registered commit through Git, not the candidate transport.
def git_oracle(ref):
    spec=f"{ref['commit']}:{ref['path']}"
    cp=run(['git','show',spec],8)
    if cp.returncode!=0:
        ft=run(['git','fetch','--no-tags','--depth=1','origin',ref['commit']],30)
        if ft.returncode!=0:return None
        cp=run(['git','show',spec],12)
    return cp.stdout if cp.returncode==0 else None

rows=[];ok=0
for ref in refs:
    try:
        item=retr.read_registered(ref['branch'],ref['path'])
        oracle=git_oracle(ref)
        match=oracle is not None and bsha(oracle)==item['sha256'] and len(oracle)==item['bytes']
        ok+=match
        rows.append(ref|{'ok':match,'candidate_sha256':item['sha256'],
                         'oracle_sha256':bsha(oracle) if oracle is not None else None,
                         'bytes':item['bytes'],'transport':item['transport']})
    except Exception as exc:
        rows.append(ref|{'ok':False,'error':type(exc).__name__+':'+str(exc)[:180]})
accuracy=ok/max(1,len(refs))

# Fresh content queries never used during evolution.
queries={
 'migration candidate rollback regression':'yado-rc8-candidate',
 'external evidence internet training':'yado-rc8-v35-training',
 'causal broadcast temporal continuity':'yado-rc8-digital-consciousness-v1',
 'split brain consistency external verification':'yado-rc8-v37-digital-consciousness',
 'bootstrap reconstruction integrity':'yado-v28-runtime',
}
query_rows={}
for q,expected in queries.items():
    res=retr.search_content(q,limit=10)
    query_rows[q]={
      'expected_branch':expected,'found':any(x['branch']==expected for x in res),
      'top':[{'branch':x['branch'],'path':x['path'],'score':x['score'],'sha256':x['sha256']} for x in res[:5]]
    }

# Negative controls: it must refuse paths/branches not registered as experience.
negative=[]
tests=[
 ('yado-v29-cognitive','../../etc/passwd'),
 ('yado-v29-cognitive','README.md'),
 ('yado-architecture-shadow-search','canonical/yado-main-head-g2.json'),
 ('DOES_NOT_EXIST','runtime/x.py'),
]
for branch,path in tests:
    refused=False;err=None
    try:retr.read_registered(branch,path)
    except Exception as exc:
        refused=True;err=type(exc).__name__
    negative.append({'branch':branch,'path':path,'refused':refused,'error':err})

# Repeatability on exact same pinned content.
repeat_refs=refs[::max(1,len(refs)//7)][:7]
repeat=[]
for ref in repeat_refs:
    a=retr.read_registered(ref['branch'],ref['path'])
    b=retr.read_registered(ref['branch'],ref['path'])
    repeat.append({'branch':ref['branch'],'path':ref['path'],'same':a['sha256']==b['sha256'] and a['bytes']==b['bytes']})

checks={
 'all_registered_exact_bytes':accuracy==1.0,
 'fresh_content_queries':all(x['found'] for x in query_rows.values()),
 'negative_controls_refused':all(x['refused'] for x in negative),
 'repeatable_pinned_reads':all(x['same'] for x in repeat),
 'candidate_source_unchanged':hashlib.sha256(SRC.read_bytes()).hexdigest()==meta['candidate_source_sha256'],
 'canonical_head_immutable':ledger.get('current_head_digest')==head.get('canonical_head_digest'),
}
passed=all(checks.values())
next_cap='LEGACY_EXPERIENCE_RETRIEVAL_CANONICAL_INTEGRATION_V1' if passed else 'LEGACY_EXPERIENCE_RETRIEVAL_EVOLUTION_REPAIR_V1'

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
 'schema':'yado.g2.legacy_experience_retrieval_fresh_admission.receipt.v1',
 'status':'PASS_LEGACY_EXPERIENCE_RETRIEVAL_FRESH_ADMISSION_V1' if passed else 'WITHHOLD_LEGACY_EXPERIENCE_RETRIEVAL_FRESH_ADMISSION_V1',
 'candidate_digest':meta['candidate_digest'],'candidate_source_sha256':meta['candidate_source_sha256'],
 'exact_retrieval':{'accuracy':accuracy,'count':len(rows),'rows':rows},
 'fresh_queries':query_rows,'negative_controls':negative,'repeatability':repeat,'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'FRESH ADMISSION OF READ-ONLY HISTORICAL EVIDENCE RETRIEVAL AGAINST AN INDEPENDENT GIT ORACLE. LEGACY SOURCE IS DATA ONLY AND IS NOT EXECUTED.'
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_LEGACY_EXPERIENCE_RETRIEVAL_FRESH_ADMISSION",
   'event_type':'KERNEL_EVOLVED_CODE_FRESH_ADMISSION','status':'PASS_SHADOW' if passed else 'WITHHOLD',
   'generation':ledger['current_head'],'deficit':'LEGACY_EXPERIENCE_RETRIEVAL_FRESH_ADMISSION_V1',
   'effect':'SELF_EVOLVED_LEGACY_RETRIEVER_FRESH_ADMISSION_PASS' if passed else 'SELF_EVOLVED_LEGACY_RETRIEVER_FRESH_ADMISSION_WITHHELD',
   'source_path':f'receipts/yado-legacy-experience-retrieval-fresh-admission-v1-run-{run_id}.json',
   'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
   'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({'status':receipt['status'],'exact_accuracy':accuracy,
 'fresh_queries':{k:v['found'] for k,v in query_rows.items()},
 'negative_controls':all(x['refused'] for x in negative),
 'repeatability':all(x['same'] for x in repeat),'checks':checks,
 'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('LEGACY_EXPERIENCE_FRESH_ADMISSION_WITHHELD')
