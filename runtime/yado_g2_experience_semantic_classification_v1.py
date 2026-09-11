#!/usr/bin/env python3
"""Evidence-driven semantic classification for recovered YADO branch history.

This stage classifies evidence character, not truth of broad semantic claims.
No branch name may determine class. No code activation or capability promotion.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'canonical/yado-historical-evidence-recovery-v1.json'
OUT=ROOT/'canonical/yado-experience-semantic-classification-v1.json'

PASS_TOKENS=('PASS',)
NEG_TOKENS=('WITHHOLD','FAIL','BLOCK','DEFER')

def classify(statuses):
    up=[str(s).upper() for s in statuses if isinstance(s,str)]
    p=sum(any(t in s for t in PASS_TOKENS) for s in up)
    n=sum(any(t in s for t in NEG_TOKENS) for s in up)
    if p and n: return 'MIXED_CAUSAL_EXPERIENCE',p,n
    if p: return 'POSITIVE_VERIFIED_EXPERIENCE_CANDIDATE',p,n
    if n: return 'NEGATIVE_VERIFIED_EXPERIENCE_CANDIDATE',p,n
    return 'HYPOTHESIS_OR_UNRESOLVED_EVIDENCE',p,n

def main():
    src=json.loads(SRC.read_text())
    rows=[]
    for r in src['records']:
        statuses=[e.get('status') for e in r.get('evidence',[])]
        cls,p,n=classify(statuses)
        paths=[e.get('path','') for e in r.get('evidence',[])]
        infra_only=bool(paths) and all(x.startswith('audits/') for x in paths)
        if infra_only and cls=='POSITIVE_VERIFIED_EXPERIENCE_CANDIDATE':
            cls='VERIFICATION_INFRASTRUCTURE_EVIDENCE'
        rows.append({
          'branch':r['branch'],'tip_sha':r['tip_sha'],'evidence_count':r['evidence_count'],
          'pass_like_count':p,'negative_like_count':n,'classification':cls,
          'evidence_paths':sorted(set(paths)),
          'claim_boundary':'CLASSIFIES RECORDED OUTCOME EVIDENCE ONLY; DOES NOT VALIDATE BROADER BRANCH CLAIMS OR ACTIVATE CODE.'
        })
    counts={}
    for r in rows: counts[r['classification']]=counts.get(r['classification'],0)+1
    out={
      'schema':'yado.g2.experience_semantic_classification.v1',
      'source_artifact_digest':src['artifact_digest'],
      'candidate_count':len(rows),'classification_counts':counts,'records':rows,
      'policy':{
        'branch_name_as_semantic_evidence':False,
        'broad_claim_validation':'NOT_PERFORMED',
        'code_activation':'FORBIDDEN_BY_THIS_ARTIFACT',
        'capability_promotion':'FORBIDDEN_BY_THIS_ARTIFACT',
        'next_step':'FRESH_REVALIDATION_REQUIRED_BEFORE_EXPERIENCE_ADMISSION'
      },
      'status':'PASS_EVIDENCE_CHARACTER_CLASSIFICATION_COMPLETE'
    }
    payload=json.dumps(out,sort_keys=True,separators=(',',':')).encode()
    out['artifact_digest']=hashlib.sha256(payload).hexdigest()
    OUT.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':out['status'],'counts':counts,'digest':out['artifact_digest']},sort_keys=True))
if __name__=='__main__': main()
