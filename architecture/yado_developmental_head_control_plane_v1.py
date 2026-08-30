from __future__ import annotations
from dataclasses import dataclass,asdict
from pathlib import Path
from typing import Any,Dict,Mapping,Optional
import hashlib,json,os,sys

ROOT=Path(__file__).resolve().parents[1]
RUNTIME=ROOT/'runtime'
sys.path.insert(0,str(RUNTIME))

from yado_unified_causal_evolution_architecture_v1 import digest_obj

HEAD_ID='G0_RC8_V36'
HEAD_SHA='7ecfd384d48bfd5c39312fa4c54a8feb49f4473b171902c8190a6b276beda9d1'

@dataclass(frozen=True)
class CandidateState:
    candidate_id:str
    parent_id:str
    artifact_digest:str
    evidence_status:str
    promotion_decision:str='WITHHOLD_CANDIDATE'
    promotion_decision_digest:Optional[str]=None
    reason:str='NO_PROMOTION_EVIDENCE'

    def canonical(self):
        return asdict(self)

class DevelopmentalHeadControlPlane:
    """Single-head control plane. Experiments are evidence; only explicit verified promotion changes head."""
    def __init__(self,head_id:str,head_digest:str):
        self.head_id=head_id
        self.head_digest=head_digest
        self.candidates:Dict[str,CandidateState]={}
        self.evidence:Dict[str,Dict[str,Any]]={}
        self.rejected:Dict[str,Dict[str,Any]]={}
        self.history=[{'head_id':head_id,'head_digest':head_digest,'event':'ROOT_HEAD'}]

    def register_evidence(self,evidence_id:str,*,kind:str,digest:str,status:str,metadata:Optional[Mapping[str,Any]]=None):
        self.evidence[evidence_id]={
            'evidence_id':evidence_id,'kind':kind,'digest':digest,'status':status,
            'metadata':dict(metadata or {}),
        }

    def register_candidate(self,c:CandidateState):
        if c.candidate_id==self.head_id:
            raise ValueError('CANDIDATE_ID_EQUALS_HEAD')
        self.candidates[c.candidate_id]=c

    def evaluate(self,candidate_id:str)->Dict[str,Any]:
        c=self.candidates[candidate_id]
        reasons=[]
        if c.parent_id!=self.head_id:
            reasons.append('PARENT_IS_NOT_CURRENT_HEAD')
        if c.promotion_decision!='PROMOTE_GENERATION':
            reasons.append('NO_EXPLICIT_PROMOTION_DECISION')
        if not c.promotion_decision_digest:
            reasons.append('NO_PROMOTION_DECISION_DIGEST')
        if c.evidence_status not in {'FULL_CAUSAL_GATE_PASS','FULL_EXTERNAL_REGRESSION_PASS'}:
            reasons.append('INSUFFICIENT_EVIDENCE_STATUS')
        action='PROMOTE_GENERATION' if not reasons else 'WITHHOLD_CANDIDATE'
        out={
            'candidate_id':candidate_id,'parent_id':c.parent_id,'current_head':self.head_id,
            'action':action,'reasons':reasons,'artifact_digest':c.artifact_digest,
        }
        out['decision_digest']=digest_obj(out)
        return out

    def promote(self,candidate_id:str,decision:Mapping[str,Any]):
        if decision.get('action')!='PROMOTE_GENERATION':
            raise ValueError('PROMOTION_NOT_AUTHORIZED')
        if decision.get('candidate_id')!=candidate_id:
            raise ValueError('DECISION_CANDIDATE_MISMATCH')
        c=self.candidates[candidate_id]
        if c.parent_id!=self.head_id:
            raise ValueError('HEAD_CHANGED')
        old=self.head_id
        self.head_id=candidate_id
        self.head_digest=c.artifact_digest
        self.history.append({
            'event':'PROMOTION','from':old,'to':self.head_id,
            'decision_digest':decision['decision_digest'],
        })

    def reject(self,candidate_id:str,reason:str):
        c=self.candidates.pop(candidate_id)
        self.rejected[candidate_id]={
            **c.canonical(),'rejection_reason':reason,
            'preserve_as_evidence':True,
        }

    def snapshot(self):
        out={
            'schema':'yado.developmental_head_control_plane.v1',
            'invariant':'EXACTLY_ONE_DEVELOPMENTAL_HEAD',
            'head_id':self.head_id,'head_digest':self.head_digest,
            'candidate_count':len(self.candidates),'rejected_count':len(self.rejected),
            'evidence_count':len(self.evidence),
            'candidates':[self.candidates[k].canonical() for k in sorted(self.candidates)],
            'rejected':[self.rejected[k] for k in sorted(self.rejected)],
            'evidence':[self.evidence[k] for k in sorted(self.evidence)],
            'history':self.history,
        }
        out['snapshot_digest']=digest_obj(out)
        return out

def read_json(path:Path):
    return json.loads(path.read_text())

def build_real_manifest():
    lineage_path=ROOT/'receipts'/'yado-real-developmental-lineage-v1-latest.json'
    meta_path=ROOT/'receipts'/'yado-live-g0-autonomous-metacognitive-v1-latest.json'
    rapid_path=ROOT/'receipts'/'yado-rapid-stem-holdout-v1-latest.json'

    lineage=read_json(lineage_path)
    meta=read_json(meta_path)
    rapid=read_json(rapid_path)

    cp=DevelopmentalHeadControlPlane(HEAD_ID,HEAD_SHA)

    cp.register_evidence(
        'REAL_LINEAGE_V1',kind='LINEAGE',
        digest=lineage['report_digest'],status=lineage['status'],
        metadata={'s1_action':lineage['s1_decision']['action']}
    )
    cp.register_evidence(
        'G0_AUTONOMOUS_META',kind='LIVE_KERNEL',
        digest=meta['receipt_sha256'],status=meta['status'],
        metadata={'decisions':[{x['id']:x['decision']['action']} for x in meta['results']]}
    )
    cp.register_evidence(
        'RAPID_STEM_V1',kind='DOMAIN_EXPERIENCE',
        digest=rapid['receipt_sha256'],status=rapid['status'],
        metadata={'overall_mean':rapid['summary']['overall_mean'],'task_count':rapid['summary']['task_count']}
    )

    # S1 is a rejected stepping stone. It remains causal evidence, never a head.
    s1=CandidateState(
        candidate_id='CANDIDATE_S1',
        parent_id=HEAD_ID,
        artifact_digest='e5e1ada993db0e48ac36f57ecb1981e77ddf287c565c9dd5b7bea89bb21a1d70',
        evidence_status='BURNIN_WITHHOLD',
        promotion_decision='WITHHOLD_CANDIDATE',
        reason='THINKING_REGRESSION_AND_FRESH_BLIND_FAIL',
    )
    cp.register_candidate(s1)
    s1_eval=cp.evaluate('CANDIDATE_S1')
    cp.reject('CANDIDATE_S1',';'.join(s1_eval['reasons']))

    # S2 exists only as an experiment until its receipts prove a full gate pass.
    s2=CandidateState(
        candidate_id='G1_CANDIDATE_S2',
        parent_id=HEAD_ID,
        artifact_digest='PENDING_EXPERIMENT_RESULT',
        evidence_status='EXPERIMENT_IN_PROGRESS_OR_UNADMITTED',
        promotion_decision='WITHHOLD_CANDIDATE',
        reason='G0_METACOGNITIVE_WITHHOLD',
    )
    cp.register_candidate(s2)
    s2_eval=cp.evaluate('G1_CANDIDATE_S2')

    snap=cp.snapshot()
    manifest={
        'schema':'yado.real_developmental_head_manifest.v1',
        'status':'PASS_ONE_HEAD_CONTROL_PLANE',
        'current_head':snap['head_id'],
        'current_head_digest':snap['head_digest'],
        'one_head_invariant':True,
        's1_evaluation':s1_eval,
        's2_evaluation':s2_eval,
        'domain_experiments_are_evidence_only':True,
        'autonomous_g0_lineage_decision':'EXECUTE',
        'autonomous_g0_s1_promotion_decision':'WITHHOLD',
        'autonomous_g0_s2_repair_decision':'WITHHOLD',
        'control_plane_snapshot':snap,
        'canonical_rc8_mutation':False,
        'promotion_applied':False,
    }
    manifest['manifest_digest']=digest_obj(manifest)
    return manifest

def self_test():
    cp=DevelopmentalHeadControlPlane('T0','root')
    cp.register_candidate(CandidateState(
        'BAD_SPECIALIST','T0','a','FULL_CAUSAL_GATE_PASS','WITHHOLD_CANDIDATE',None
    ))
    d1=cp.evaluate('BAD_SPECIALIST')
    assert d1['action']=='WITHHOLD_CANDIDATE'

    cp.register_candidate(CandidateState(
        'WRONG_PARENT','OTHER','b','FULL_CAUSAL_GATE_PASS','PROMOTE_GENERATION','decision-x'
    ))
    d2=cp.evaluate('WRONG_PARENT')
    assert d2['action']=='WITHHOLD_CANDIDATE' and 'PARENT_IS_NOT_CURRENT_HEAD' in d2['reasons']

    cp.register_candidate(CandidateState(
        'GOOD','T0','c','FULL_CAUSAL_GATE_PASS','PROMOTE_GENERATION','decision-good'
    ))
    d3=cp.evaluate('GOOD')
    assert d3['action']=='PROMOTE_GENERATION'
    cp.promote('GOOD',d3)
    assert cp.head_id=='GOOD'
    return {'bad':d1,'wrong_parent':d2,'good':d3,'snapshot':cp.snapshot()}

if __name__=='__main__':
    test=self_test()
    manifest=build_real_manifest()
    out=ROOT/'architecture'/'developmental-head-manifest.json'
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(manifest,indent=2,sort_keys=True,default=str)+'\n')
    report={
        'status':'PASS_DEVELOPMENTAL_HEAD_CONTROL_PLANE_V1',
        'self_test':test,
        'real_manifest':manifest,
    }
    report['report_digest']=digest_obj(report)
    p=ROOT/'runtime'/'yado_developmental_head_control_plane_v1_report.json'
    p.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
    print(json.dumps({
        'status':report['status'],
        'current_head':manifest['current_head'],
        's1_action':manifest['s1_evaluation']['action'],
        's2_action':manifest['s2_evaluation']['action'],
        'manifest_digest':manifest['manifest_digest'],
    },indent=2,sort_keys=True))
