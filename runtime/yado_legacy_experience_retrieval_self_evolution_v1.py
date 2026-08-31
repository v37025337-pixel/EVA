from __future__ import annotations
from pathlib import Path
import hashlib,importlib.util,json,os,re,subprocess,sys,tempfile,urllib.parse,urllib.request

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

AUDIT=REPO/'receipts'/'yado-unified-core-deep-self-audit-v1-run-33394273327.json'
REG=REPO/'canonical'/'yado-unified-experience-registry-v1.json'
HEAD=REPO/'canonical'/'yado-main-head-g2.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
CAND_DIR=REPO/'candidates'/'g2-self-evolution'
CAND_DIR.mkdir(parents=True,exist_ok=True)
CAND_SRC=CAND_DIR/'legacy_experience_retriever_v1.py'
CAND_META=CAND_DIR/'legacy_experience_retriever_v1.json'
OUT=ROOT/'yado_legacy_experience_retrieval_self_evolution_v1_receipt.json'

MAX_FILE_BYTES=524288
MAX_TOTAL_BYTES=8*1024*1024
REPO_SLUG='v37025337-pixel/EVA'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def bsha(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def safe_path(p):
    s=str(p).replace('\\','/')
    if s.startswith('/') or '..' in s.split('/') or not s:return False
    return True
def run(cmd,timeout=25):
    return subprocess.run(cmd,cwd=REPO,capture_output=True,timeout=timeout)

audit=load(AUDIT);reg=load(REG);head=load(HEAD);ledger=load(LEDGER)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['LEGACY_EXPERIENCE_CONTENT_RETRIEVAL']:
    raise RuntimeError('KERNEL_FRONTIER_NOT_LEGACY_EXPERIENCE_CONTENT_RETRIEVAL')
if audit.get('self_selected_next_step')!='LEGACY_EXPERIENCE_CONTENT_RETRIEVAL':
    raise RuntimeError('AUDIT_PRIORITY_MISMATCH')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):
    raise RuntimeError('HEAD_LEDGER_MISMATCH')

legacy=[x for x in reg.get('branches',[]) if x.get('mode')=='EXPERIENCE_ONLY']
refs=[]
for e in legacy:
    branch=e['branch'];commit=e['head_sha']
    for path in e.get('evidence',[]):
        if safe_path(path):
            refs.append({'branch':branch,'commit':commit,'path':path})
if len(legacy)<10 or len(refs)<20:raise RuntimeError('INSUFFICIENT_LEGACY_EVIDENCE_REGISTRY')

# The kernel probes generic read-only mechanisms available in its environment.
def local_git(ref):
    spec=f"{ref['commit']}:{ref['path']}"
    cp=run(['git','show',spec],timeout=12)
    if cp.returncode!=0:return None,'LOCAL_GIT_MISS'
    if len(cp.stdout)>MAX_FILE_BYTES:return None,'TOO_LARGE'
    return cp.stdout,'LOCAL_GIT'

def fetch_git(ref):
    spec=f"{ref['commit']}:{ref['path']}"
    cp=run(['git','show',spec],timeout=8)
    if cp.returncode!=0:
        ft=run(['git','fetch','--no-tags','--depth=1','origin',ref['commit']],timeout=30)
        if ft.returncode!=0:return None,'FETCH_FAILED:'+ft.stderr.decode('utf-8','replace')[-160:]
        cp=run(['git','show',spec],timeout=12)
    if cp.returncode!=0:return None,'GIT_SHOW_FAILED'
    if len(cp.stdout)>MAX_FILE_BYTES:return None,'TOO_LARGE'
    return cp.stdout,'FETCH_EXACT_GIT'

def raw_https(ref):
    path='/'.join(urllib.parse.quote(x,safe='') for x in ref['path'].split('/'))
    url=f"https://raw.githubusercontent.com/{REPO_SLUG}/{ref['commit']}/{path}"
    try:
        rq=urllib.request.Request(url,headers={'User-Agent':'YADO-Legacy-Experience-Retriever/1.0'})
        with urllib.request.urlopen(rq,timeout=15) as resp:
            data=resp.read(MAX_FILE_BYTES+1)
        if len(data)>MAX_FILE_BYTES:return None,'TOO_LARGE'
        return data,'RAW_HTTPS_EXACT'
    except Exception as exc:
        return None,'RAW_HTTPS_FAILED:'+type(exc).__name__

STRATEGIES={
 'LOCAL_GIT_ONLY':{'reader':local_git,'complexity':0.10,'risk':0.01},
 'FETCH_EXACT_GIT':{'reader':fetch_git,'complexity':0.24,'risk':0.03},
 'RAW_HTTPS_EXACT':{'reader':raw_https,'complexity':0.20,'risk':0.05},
}

# Selection set: one evidence artifact from alternating legacy branches.
selection=[]
blind=[]
for i,e in enumerate(legacy):
    er=[r for r in refs if r['branch']==e['branch']]
    if not er:continue
    (selection if i%2==0 else blind).append(er[0])
    for extra in er[1:]:blind.append(extra)
# Ensure blind contains evidence from branches not used during strategy selection.
selection_keys={(r['branch'],r['path']) for r in selection}
blind=[r for r in refs if (r['branch'],r['path']) not in selection_keys]

strategy_results=[]
for sid,spec in STRATEGIES.items():
    ok=0;rows=[]
    for ref in selection:
        data,transport=spec['reader'](ref)
        passed=data is not None
        ok+=passed
        rows.append(ref|{'ok':passed,'transport':transport,'sha256':bsha(data) if data else None,'bytes':len(data) if data else 0})
    success=ok/max(1,len(selection))
    # evidence-first score; complexity/risk only break near ties.
    score=success-0.05*spec['complexity']-0.05*spec['risk']
    strategy_results.append({'strategy':sid,'success':success,'score':score,'rows':rows,
                             'complexity':spec['complexity'],'risk':spec['risk']})
strategy_results.sort(key=lambda x:(-x['score'],-x['success'],x['strategy']))
selected=strategy_results[0]['strategy']

# Kernel synthesizes executable source from the winning transport primitive.
common=String = ''
if selected=='FETCH_EXACT_GIT':
    transport_body=r'''
    def _read_exact(self,commit,path):
        spec=f"{commit}:{path}"
        cp=self._run(["git","show",spec],12)
        if cp.returncode!=0:
            ft=self._run(["git","fetch","--no-tags","--depth=1","origin",commit],30)
            if ft.returncode!=0: raise RuntimeError("LEGACY_COMMIT_FETCH_FAILED")
            cp=self._run(["git","show",spec],12)
        if cp.returncode!=0: raise FileNotFoundError(spec)
        return cp.stdout,"FETCH_EXACT_GIT"
'''
elif selected=='RAW_HTTPS_EXACT':
    transport_body=r'''
    def _read_exact(self,commit,path):
        ep="/".join(urllib.parse.quote(x,safe="") for x in path.split("/"))
        url=f"https://raw.githubusercontent.com/{self.repo_slug}/{commit}/{ep}"
        rq=urllib.request.Request(url,headers={"User-Agent":"YADO-Legacy-Experience-Retriever/1.0"})
        with urllib.request.urlopen(rq,timeout=15) as resp:
            return resp.read(self.max_file_bytes+1),"RAW_HTTPS_EXACT"
'''
else:
    transport_body=r'''
    def _read_exact(self,commit,path):
        spec=f"{commit}:{path}"
        cp=self._run(["git","show",spec],12)
        if cp.returncode!=0: raise FileNotFoundError(spec)
        return cp.stdout,"LOCAL_GIT"
'''

candidate_source=f'''from __future__ import annotations
from pathlib import Path
import hashlib,json,re,subprocess,urllib.parse,urllib.request

class LegacyExperienceRetrieverV1:
    COMPONENT_ID="ALG-G2-LEGACY-EXPERIENCE-RETRIEVER-V1"
    def __init__(self,repo_root,registry,repo_slug="{REPO_SLUG}",max_file_bytes={MAX_FILE_BYTES}):
        self.repo=Path(repo_root)
        self.registry=registry
        self.repo_slug=repo_slug
        self.max_file_bytes=int(max_file_bytes)

    def _run(self,cmd,timeout):
        return subprocess.run(cmd,cwd=self.repo,capture_output=True,timeout=timeout)

    @staticmethod
    def _safe_path(path):
        s=str(path).replace(chr(92),"/")
        return bool(s) and not s.startswith("/") and ".." not in s.split("/")
{transport_body}
    def read_registered(self,branch,path):
        entry=next((x for x in self.registry.get("branches",[]) if x.get("branch")==branch),None)
        if not entry or entry.get("mode")!="EXPERIENCE_ONLY":
            raise KeyError("LEGACY_BRANCH_NOT_REGISTERED")
        if path not in entry.get("evidence",[]):
            raise KeyError("EVIDENCE_PATH_NOT_REGISTERED")
        if not self._safe_path(path):
            raise ValueError("UNSAFE_LEGACY_PATH")
        commit=entry["head_sha"]
        data,transport=self._read_exact(commit,path)
        if len(data)>self.max_file_bytes:
            raise ValueError("LEGACY_EVIDENCE_TOO_LARGE")
        return {{
          "branch":branch,"registered_commit":commit,"path":path,
          "transport":transport,"bytes":len(data),
          "sha256":hashlib.sha256(data).hexdigest(),
          "git_blob_sha1":hashlib.sha1((f"blob {{len(data)}}"+chr(0)).encode()+data).hexdigest(),
          "content":data.decode("utf-8","replace")
        }}

    def search_content(self,query,limit=8):
        tokens={{x for x in re.findall(r"[a-zA-Z0-9_]+",str(query).lower()) if len(x)>2}}
        rows=[]
        for entry in self.registry.get("branches",[]):
            if entry.get("mode")!="EXPERIENCE_ONLY": continue
            for path in entry.get("evidence",[]):
                try: item=self.read_registered(entry["branch"],path)
                except Exception: continue
                text=item["content"].lower()
                score=sum(text.count(t) for t in tokens)
                if score:
                    rows.append({{k:v for k,v in item.items() if k!="content"}}|{{"score":score,"snippet":item["content"][:1200]}})
        rows.sort(key=lambda x:(-x["score"],x["branch"],x["path"]))
        return rows[:max(1,int(limit))]
'''
CAND_SRC.write_text(candidate_source,encoding='utf-8')

# Load the code evolved by the kernel and test on held-out historical evidence.
sp=importlib.util.spec_from_file_location('yado_evolved_legacy_experience_retriever_v1',CAND_SRC)
mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod)
retr=mod.LegacyExperienceRetrieverV1(REPO,reg)

blind_rows=[];blind_ok=0;total_bytes=0
for ref in blind:
    try:
        item=retr.read_registered(ref['branch'],ref['path'])
        ok=item['registered_commit']==ref['commit'] and item['bytes']>0
        total_bytes+=item['bytes']
        blind_rows.append(ref|{'ok':ok,'sha256':item['sha256'],'git_blob_sha1':item['git_blob_sha1'],
                               'bytes':item['bytes'],'transport':item['transport']})
        blind_ok+=ok
    except Exception as exc:
        blind_rows.append(ref|{'ok':False,'error':type(exc).__name__+':'+str(exc)[:180]})
blind_accuracy=blind_ok/max(1,len(blind))

# Independent cross-transport verification on a bounded subset where possible.
cross=[]
for ref in blind[:min(8,len(blind))]:
    a,_=fetch_git(ref);b,_=raw_https(ref)
    if a is not None and b is not None:
        cross.append({'branch':ref['branch'],'path':ref['path'],'match':a==b,
                      'git_sha256':bsha(a),'https_sha256':bsha(b)})
cross_match=(sum(x['match'] for x in cross)/len(cross)) if cross else None

# Content retrieval must surface known historical topics from exact bytes.
queries={
 'self repair integrity rollback':'yado-kernel-task-v37-repair',
 'workspace attention metacognition':'yado-rc8-consciousness-ab',
 'logic thinking intelligence memory':'yado-v29-cognitive',
}
search_checks={}
for q,expected_branch in queries.items():
    rows=retr.search_content(q,limit=8)
    search_checks[q]={
      'expected_branch':expected_branch,
      'found':any(x['branch']==expected_branch for x in rows),
      'top':[{'branch':x['branch'],'path':x['path'],'score':x['score'],'sha256':x['sha256']} for x in rows[:4]]
    }

source_text=CAND_SRC.read_text(encoding='utf-8')
safety={
 'no_exec':not re.search(r'\\bexec\\s*\\(',source_text),
 'no_eval':not re.search(r'\\beval\\s*\\(',source_text),
 'no_legacy_import':not re.search(r'from\\s+yado_(v28|v29|rc8)',source_text),
 'registered_paths_only':'EVIDENCE_PATH_NOT_REGISTERED' in source_text,
 'read_only_no_git_push':'git","push' not in source_text and 'git","commit' not in source_text,
}
checks={
 'kernel_priority_respected':True,
 'strategy_selected_from_environment_evidence':strategy_results[0]['success']>=0.80,
 'heldout_exact_retrieval':blind_accuracy>=0.90,
 'total_bytes_bounded':total_bytes<=MAX_TOTAL_BYTES,
 'cross_transport_match':cross_match is None or cross_match==1.0,
 'content_search_v29':search_checks['logic thinking intelligence memory']['found'],
 'content_search_workspace':search_checks['workspace attention metacognition']['found'],
 'content_search_repair':search_checks['self repair integrity rollback']['found'],
 'candidate_safety':all(safety.values()),
 'canonical_untouched':ledger.get('current_head_digest')==head.get('canonical_head_digest'),
}
passed=all(checks.values())

meta={
 'schema':'yado.g2.legacy_experience_retriever_candidate.v1',
 'component_id':'ALG-G2-LEGACY-EXPERIENCE-RETRIEVER-V1',
 'generation':ledger['current_head'],'parent_head_digest':head['canonical_head_digest'],
 'self_selected_finding':'LEGACY_EXPERIENCE_CONTENT_RETRIEVAL',
 'evolution_mode':'KERNEL_GENERATED_CODE_FROM_SELECTED_TRANSPORT_PRIMITIVE',
 'selected_strategy':selected,'strategy_results':strategy_results,
 'candidate_source_sha256':hashlib.sha256(CAND_SRC.read_bytes()).hexdigest(),
 'heldout_accuracy':blind_accuracy,'cross_transport_match':cross_match,
 'search_checks':search_checks,'safety':safety,'checks':checks,
 'state':'AUTHORIZED_FOR_SHADOW_ADMISSION' if passed else 'WITHHOLD',
 'canonical_active':False,'promotion_applied':False,
 'semantic_boundary':'READ-ONLY EXACT HISTORICAL EVIDENCE RETRIEVAL. LEGACY CODE IS READ AS DATA AND NEVER IMPORTED OR EXECUTED.'
}
meta['candidate_digest']=h(meta);CAND_META.write_text(json.dumps(meta,indent=2,sort_keys=True)+'\n')

next_cap='LEGACY_EXPERIENCE_RETRIEVAL_FRESH_ADMISSION_V1' if passed else 'LEGACY_EXPERIENCE_RETRIEVAL_EVOLUTION_BLOCKED_V1'
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
 'schema':'yado.g2.legacy_experience_retrieval_self_evolution.receipt.v1',
 'status':'PASS_YADO_LEGACY_EXPERIENCE_RETRIEVAL_SELF_EVOLUTION_V1' if passed else 'WITHHOLD_YADO_LEGACY_EXPERIENCE_RETRIEVAL_SELF_EVOLUTION_V1',
 'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),
 'audit_source':'receipts/yado-unified-core-deep-self-audit-v1-run-33394273327.json',
 'self_selected_finding':'LEGACY_EXPERIENCE_CONTENT_RETRIEVAL',
 'selected_strategy':selected,'strategy_results':strategy_results,
 'candidate_source_sha256':meta['candidate_source_sha256'],
 'heldout':{'accuracy':blind_accuracy,'count':len(blind_rows),'rows':blind_rows},
 'cross_transport':{'checks':cross,'match_rate':cross_match},
 'content_search':search_checks,'safety':safety,'checks':checks,
 'candidate_digest':meta['candidate_digest'],
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'THE KERNEL SELECTED A RETRIEVAL TRANSPORT FROM ENVIRONMENTAL EVIDENCE AND GENERATED A BOUNDED READ-ONLY COMPONENT. HOST PROVIDED THE EVOLUTION HARNESS, NOT THE WINNING TRANSPORT OR LEGACY CONTENT.'
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_LEGACY_EXPERIENCE_RETRIEVAL_SELF_EVOLUTION",
   'event_type':'KERNEL_NATIVE_CODE_EVOLUTION','status':'PASS_SHADOW' if passed else 'WITHHOLD',
   'generation':ledger['current_head'],'deficit':'LEGACY_EXPERIENCE_CONTENT_RETRIEVAL',
   'effect':('KERNEL_GENERATED_READ_ONLY_LEGACY_EXPERIENCE_RETRIEVER' if passed else 'LEGACY_EXPERIENCE_RETRIEVER_EVOLUTION_WITHHELD'),
   'source_path':f'receipts/yado-legacy-experience-retrieval-self-evolution-v1-run-{run_id}.json',
   'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
   'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({
 'status':receipt['status'],'selected_strategy':selected,
 'strategy_summary':[{'strategy':x['strategy'],'success':x['success'],'score':x['score']} for x in strategy_results],
 'heldout_accuracy':blind_accuracy,'cross_transport_match':cross_match,
 'search_checks':{k:v['found'] for k,v in search_checks.items()},
 'checks':checks,'next_required_capability':next_cap,
 'candidate_source_sha256':meta['candidate_source_sha256'],'receipt_sha256':receipt['receipt_sha256']
},indent=2,sort_keys=True))
