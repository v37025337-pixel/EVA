from __future__ import annotations
from pathlib import Path
from typing import Any
import hashlib, json, subprocess

REPO=Path(__file__).resolve().parent.parent
INV=REPO/'canonical/yado-remote-branch-inventory-v1.json'
OUT=REPO/'canonical/yado-experience-candidate-raw-index-v1.json'

def canon(o:Any)->str:
    return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)

def digest(o:Any)->str:
    return hashlib.sha256(canon(o).encode()).hexdigest()

def load(p:Path)->dict[str,Any]:
    return json.loads(p.read_text(encoding='utf-8'))

def run(args:list[str],timeout:int=60)->subprocess.CompletedProcess[str]:
    return subprocess.run(args,cwd=REPO,capture_output=True,text=True,timeout=timeout)

def git_show_json(ref:str,path:str)->dict[str,Any]|None:
    cp=run(['git','show',f'{ref}:{path}'],30)
    if cp.returncode!=0:return None
    try:return json.loads(cp.stdout)
    except Exception:return None

def status_tokens(obj:Any)->list[str]:
    out=[]
    def walk(x:Any):
        if isinstance(x,dict):
            for k,v in x.items():
                if k in {'status','verdict','overall_verdict','result'} and isinstance(v,str):out.append(v)
                walk(v)
        elif isinstance(x,list):
            for v in x:walk(v)
    walk(obj)
    return sorted(set(out))

inv=load(INV)
if inv.get('status')!='PASS_COMPLETE_REMOTE_REF_CLASSIFICATION' or not inv.get('coverage_complete'):
    raise RuntimeError('COMPLETE_REMOTE_INVENTORY_REQUIRED')
rows={x['branch']:x for x in inv.get('rows',[])}
candidates=list(inv.get('experience_candidates',[]))
records=[]
for branch in candidates:
    row=rows[branch]; tip=row['head_sha']
    anc=run(['git','merge-base','--is-ancestor',tip,'main'])
    reachable=anc.returncode==0
    tree=run(['git','ls-tree','-r','--name-only',tip],60)
    paths=[x.strip() for x in tree.stdout.splitlines() if x.strip()]
    evidence_paths=[p for p in paths if p.endswith('.json') and (p.startswith('receipts/') or p.startswith('candidates/'))]
    parsed=[]; pass_like=[]; withhold_like=[]
    for p in evidence_paths[:250]:
        obj=git_show_json(tip,p)
        if obj is None:continue
        tokens=status_tokens(obj)
        if not tokens:continue
        parsed.append({'path':p,'statuses':tokens})
        if any(('PASS' in s.upper()) for s in tokens):pass_like.append(p)
        if any((('WITHHOLD' in s.upper()) or ('FAIL' in s.upper())) for s in tokens):withhold_like.append(p)
    classification='RAW_EVIDENCE_INDEXED' if reachable and parsed else 'DEFER_NO_MACHINE_READABLE_EVIDENCE'
    records.append({
        'branch':branch,'tip_sha':tip,'tip_reachable_from_main':reachable,
        'machine_readable_evidence_count':len(parsed),'pass_like_evidence_count':len(pass_like),
        'withhold_or_fail_evidence_count':len(withhold_like),'classification':classification,
        'evidence':parsed[:80],
        'claim_boundary':'Indexed status-bearing historical artifacts only; no semantic lesson or capability promotion is inferred.'
    })

indexed=[r['branch'] for r in records if r['classification']=='RAW_EVIDENCE_INDEXED']
deferred=[r['branch'] for r in records if r['classification']!='RAW_EVIDENCE_INDEXED']
artifact={
 'schema':'yado.experience_candidate_raw_index.v1',
 'status':'PASS_RAW_EVIDENCE_INDEX_COMPLETE' if len(records)==len(candidates) else 'WITHHOLD_INCOMPLETE',
 'source_inventory_digest':inv.get('artifact_digest'),'candidate_count':len(candidates),
 'indexed_count':len(indexed),'deferred_count':len(deferred),'indexed_candidates':indexed,'deferred_candidates':deferred,
 'records':records,
 'policy':{
   'semantic_promotion':'FORBIDDEN_BY_THIS_ARTIFACT',
   'code_activation':'FORBIDDEN_BY_THIS_ARTIFACT',
   'pass_and_withhold_preservation':'REQUIRED',
   'future_use':'RAW_PROVENANCE_FOR_SEPARATE_FRESH_ADMISSION_ONLY'
 },
 'claim_boundary':'This is a provenance index over historical branch evidence. It does not establish correctness of historical claims, active capability, AGI, or subjective consciousness.'
}
artifact['artifact_digest']=digest(artifact)
OUT.write_text(json.dumps(artifact,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps({'status':artifact['status'],'candidate_count':len(candidates),'indexed_count':len(indexed),'deferred_count':len(deferred),'artifact_digest':artifact['artifact_digest']},indent=2,sort_keys=True))
