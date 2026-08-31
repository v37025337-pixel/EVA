from __future__ import annotations
from pathlib import Path
import json

from yado_raw_task_representation_learner_v1 import RawTaskRepresentationSpecV1

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'

class RawTaskRepresentationRuntimeV1:
    COMPONENT_ID='ALG-G2-RAW-TASK-REPRESENTATION-V1'

    def __init__(self,artifact:dict):
        if artifact.get('component_id')!=self.COMPONENT_ID:
            raise ValueError('RAW_REPRESENTATION_COMPONENT_ID_MISMATCH')
        m=artifact.get('model') or {}
        self.spec=RawTaskRepresentationSpecV1(
            family=m['family'],labels=list(m['labels']),payload=m['payload']
        )
        self.artifact=artifact

    @classmethod
    def from_path(cls,path):
        return cls(json.loads(Path(path).read_text(encoding='utf-8')))

    def predict_capability(self,raw_text:str)->str:
        return self.spec.predict(raw_text)

    def descriptor(self,raw_text:str)->dict:
        label=self.predict_capability(raw_text)
        d={'budget_limited':False,'quota_limited':False,'external_evidence_needed':False,
           'relation_needed':False,'disjunction_needed':False}
        if label==CAP_BUD:d['budget_limited']=True
        elif label==CAP_RES:d['external_evidence_needed']=True
        elif label==CAP_REL:d['relation_needed']=True
        return {'capability':label,'routing_descriptor':d,'raw_text':raw_text}

__all__=['RawTaskRepresentationRuntimeV1']
