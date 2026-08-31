from __future__ import annotations
from dataclasses import dataclass
import hashlib,json

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()

@dataclass(frozen=True)
class EvidenceCandidate:
    token:str
    evidence:float
    complexity:float=0.0
    risk:float=0.0
    novelty:float=0.0

class NeutralEvidenceProfileSelectorV1:
    MAX_CANDIDATES=64

    @classmethod
    def select(cls,candidates,complexity_penalty=0.05,risk_penalty=0.25,novelty_bonus=0.03):
        xs=list(candidates)[:cls.MAX_CANDIDATES]
        if not xs:raise ValueError('EMPTY_CANDIDATE_SET')
        scored=[]
        for x in xs:
            score=float(x.evidence)-complexity_penalty*float(x.complexity)-risk_penalty*float(x.risk)+novelty_bonus*float(x.novelty)
            scored.append((score,str(x.token),x))
        scored.sort(key=lambda z:(-z[0],z[1]))
        best=scored[0]
        return {
          'selected_token':best[2].token,
          'selected_score':best[0],
          'candidate_count':len(xs),
          'ranking':[{'token':z[2].token,'score':z[0]} for z in scored],
        }

    @classmethod
    def component(cls):
        x={
          'schema':'yado.neutral_evidence_profile_selector.v1',
          'component_id':'ALG-NEUTRAL-EVIDENCE-PROFILE-SELECTOR-V1',
          'family':'NEUTRAL_EVIDENCE_ARGMAX_WITH_COST_RISK',
          'organ':'INTELLIGENCE',
          'max_candidates':cls.MAX_CANDIDATES,
          'architecture_names_hardcoded':False,
          'candidate_tokens_semantically_opaque':True,
        }
        x['component_digest']=digest(x)
        return x
