from __future__ import annotations
from pathlib import Path
import hashlib,json,subprocess,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
BASE=REPO/'experience/yado-global-experience-corpus-v1.json'
OUT=REPO/'experience/yado-global-historical-experience-corpus-v2.json'
REPORT=REPO/'candidates/kernel-self-generated/g2-global-historical-experience-census-v2.json'

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def sha256(b):return hashlib.sha256(b).hexdigest()

base=load(BASE)
base_shas={str(r.get('sha256')) for r in base.get('rows') or [] if r.get('sha256')}

def first_recursive(obj,keys):
    if isinstance(obj,dict):
        for k in keys:
            if k in obj and isinstance(obj[k],(str,int,float,bool)) or (isinstance(obj,dict) and k in obj and obj[k] is None):
                return obj[k]
        for k in sorted(obj):
            v=first_recursive(obj[k],keys)
            if v is not None:return v
    elif isinstance(obj,list):
        for v0 in obj:
            v=first_recursive(v0,keys)
            if v is not None:return v
    return None

def top_status(obj):
    if not isinstance(obj,dict):return None
    for k in ('status','verdict','result'):
        v=obj.get(k)
        if isinstance(v,str):return v
    return None

def outcome(st):
    u=str(st or '').upper()
    if not u:return None
    if any(u.startswith(x) for x in ('PASS','COMMIT','EXECUTE','VERIFIED','SUCCESS')) or u=='TRAINED':return 'PASS'
    if any(u.startswith(x) for x in ('WITHHOLD','FAIL','ROLLBACK','BLOCKED','ERROR','REJECT')) or u=='WITHHOLD':return 'WITHHOLD'
    return None

def domain_of(text):
    s=str(text or '').lower()
    rules=[
      ('CODE',('code','source','repair','program','compiler','ast','function')),
      ('REPRESENTATION',('representation','schema','raw','mapper','language','rml','semantic')),
      ('COGNITIVE',('cognitive','logic','thinking','intelligence','conscious','workspace','reasoning')),
      ('EXECUTION',('execution','fabric','api','runtime','network','resource','executor')),
      ('MEMORY',('memory','experience','legacy','history','ledger')),
      ('EVOLUTION',('evolution','genome','mutation','gene','self-evolution')),
    ]
    for name,toks in rules:
        if any(t in s for t in toks):return name
    return 'GENERAL'

raw=subprocess.run(['git','rev-list','--all','--objects'],cwd=REPO,capture_output=True,text=True,check=True).stdout
pairs=[]
for line in raw.splitlines():
    if ' ' not in line:continue
    obj,path=line.split(' ',1)
    if not path.endswith('.json'):continue
    if not (path.startswith('receipts/') or path.startswith('experience/') or path.startswith('candidates/kernel-self-generated/')):continue
    pairs.append((obj,path))
pairs=sorted(set(pairs))

rows=[];fail=[];seen_sha=set()
for obj,path in pairs:
    try:
        b=subprocess.run(['git','cat-file','blob',obj],cwd=REPO,capture_output=True,check=True).stdout
        h=sha256(b)
        if h in seen_sha:continue
        seen_sha.add(h)
        data=json.loads(b.decode('utf-8'))
        st=top_status(data);oc=outcome(st)
        nxt=first_recursive(data,('next_required_capability','next_action'))
        rows.append({
          'git_object':obj,'path':path,'sha256':h,'status':st,'outcome':oc,
          'next_required_capability':str(nxt) if nxt is not None else None,
          'domain':domain_of(path+' '+str(nxt or '')),'next_domain':domain_of(nxt) if nxt else None,
          'present_in_global_corpus_v1':h in base_shas,
        })
    except Exception as e:
        fail.append({'object':obj,'path':path,'error':type(e).__name__+':'+str(e)[:180]})

new_rows=[r for r in rows if not r['present_in_global_corpus_v1']]
new_outcome=[r for r in new_rows if r.get('outcome') in ('PASS','WITHHOLD')]
terminal=[r for r in new_outcome if not r.get('next_required_capability')]
terminal_pass=[r for r in terminal if r['outcome']=='PASS']
terminal_withhold=[r for r in terminal if r['outcome']=='WITHHOLD']
by_class={}
for r in new_outcome:
    by_class[r['outcome']]=by_class.get(r['outcome'],0)+1
by_domain={}
for r in new_outcome:
    by_domain[r['domain']]=by_domain.get(r['domain'],0)+1

artifact={
 'schema':'yado.g2.global_historical_experience_corpus.v2',
 'base_corpus_digest':base.get('corpus_digest'),
 'git_object_path_pair_count':len(pairs),'unique_json_blob_count':len(rows),
 'parse_failure_count':len(fail),'parse_failures':fail,
 'new_historical_blob_count':len(new_rows),'new_historical_outcome_count':len(new_outcome),
 'new_outcome_by_class':by_class,'new_outcome_by_domain':by_domain,
 'new_terminal_count':len(terminal),'new_terminal_pass_count':len(terminal_pass),'new_terminal_withhold_count':len(terminal_withhold),
 'rows':new_rows,
 'source_policy':'ALL_REACHABLE_GIT_OBJECTS_UNDER_RECEIPTS_EXPERIENCE_AND_SELF_GENERATED_CANDIDATES_NOT_PRESENT_BY_SHA256_IN_GLOBAL_CORPUS_V1',
}
artifact['corpus_digest']=digest(artifact)
OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(artifact,indent=2,sort_keys=True)+'\n')

checks={
 'git_history_scanned':len(pairs)>0,
 'new_historical_blobs_found':len(new_rows)>0,
 'new_outcome_evidence_found':len(new_outcome)>0,
 'terminal_transfer_material':len(terminal)>=10,
 'terminal_both_classes_present':len(terminal_pass)>=4 and len(terminal_withhold)>=4,
 'parse_failures_bounded':len(fail)<=max(2,int(.02*max(1,len(pairs)))),
}
passed=all(checks.values())
report={
 'schema':'yado.g2.global_historical_experience_census.v2',
 'status':'PASS_G2_GLOBAL_HISTORICAL_EXPERIENCE_CENSUS_V2' if passed else 'WITHHOLD_G2_GLOBAL_HISTORICAL_EXPERIENCE_CENSUS_V2',
 'counts':{k:artifact[k] for k in ('git_object_path_pair_count','unique_json_blob_count','parse_failure_count','new_historical_blob_count','new_historical_outcome_count','new_terminal_count','new_terminal_pass_count','new_terminal_withhold_count')},
 'new_outcome_by_class':by_class,'new_outcome_by_domain':by_domain,'checks':checks,
 'corpus_digest':artifact['corpus_digest'],
 'next_required_capability':'GLOBAL_EXPERIENCE_TERMINAL_LOGIC_HISTORICAL_TRANSFER_V1' if passed else 'GLOBAL_HISTORICAL_EXPERIENCE_CENSUS_REPAIR_V3',
}
report['receipt_sha256']=digest(report)
REPORT.parent.mkdir(parents=True,exist_ok=True);REPORT.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
print(json.dumps(report,indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
