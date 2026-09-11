#!/usr/bin/env python3
"""YADO G2 historical evidence recovery V1.

Recovers machine-readable evidence for deferred experience-candidate refs by
walking each ref's Git history rather than trusting branch names or tip files.
This stage never promotes semantics or activates code.
"""
from __future__ import annotations
import hashlib, json, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'canonical/yado-experience-candidate-raw-index-v1.json'
OUT=ROOT/'canonical/yado-historical-evidence-recovery-v1.json'
ALLOWED_PREFIXES=('receipts/','candidates/','audits/')
STATUS_KEYS=('status','verdict','result')

def git(*args:str)->str:
    return subprocess.check_output(['git',*args],cwd=ROOT,text=True,stderr=subprocess.DEVNULL).strip()

def json_at(commit:str,path:str):
    try: text=git('show',f'{commit}:{path}')
    except subprocess.CalledProcessError: return None
    try: return json.loads(text)
    except Exception: return None

def status_of(x):
    if not isinstance(x,dict): return None
    for k in STATUS_KEYS:
        v=x.get(k)
        if isinstance(v,str) and any(t in v.upper() for t in ('PASS','WITHHOLD','FAIL','BLOCK','DEFER')): return v
    return None

def main():
    raw=json.loads(RAW.read_text())
    records=[]
    for r in raw['records']:
        branch=r['branch']; tip=r['tip_sha']
        commits=git('rev-list',tip).splitlines()
        evidence=[]
        seen=set()
        for c in commits:
            try: paths=git('diff-tree','--no-commit-id','--name-only','-r',c).splitlines()
            except subprocess.CalledProcessError: continue
            for p in paths:
                if not p.endswith('.json') or not p.startswith(ALLOWED_PREFIXES): continue
                key=(c,p)
                if key in seen: continue
                seen.add(key)
                obj=json_at(c,p); st=status_of(obj)
                if st:
                    evidence.append({'commit':c,'path':p,'status':st,'sha256':hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':')).encode()).hexdigest()})
        records.append({'branch':branch,'tip_sha':tip,'commits_scanned':len(commits),'evidence_count':len(evidence),'evidence':evidence[:64], 'classification':'HISTORICAL_EVIDENCE_RECOVERED' if evidence else 'DEFER_NO_HISTORICAL_MACHINE_READABLE_EVIDENCE'})
    recovered=sum(x['classification']=='HISTORICAL_EVIDENCE_RECOVERED' for x in records)
    out={'schema':'yado.g2.historical_evidence_recovery.v1','source_index_digest':raw.get('artifact_digest'),'candidate_count':len(records),'recovered_count':recovered,'deferred_count':len(records)-recovered,'policy':{'semantic_promotion':'FORBIDDEN_BY_THIS_ARTIFACT','code_activation':'FORBIDDEN_BY_THIS_ARTIFACT','branch_name_as_evidence':False},'records':records,'status':'PASS_HISTORICAL_EVIDENCE_RECOVERY_COMPLETE'}
    payload=json.dumps(out,sort_keys=True,separators=(',',':')).encode(); out['artifact_digest']=hashlib.sha256(payload).hexdigest()
    OUT.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':out['status'],'recovered':recovered,'deferred':out['deferred_count'],'digest':out['artifact_digest']},sort_keys=True))
if __name__=='__main__': main()
