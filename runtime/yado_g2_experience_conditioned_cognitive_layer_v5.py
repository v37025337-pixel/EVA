from __future__ import annotations

from copy import deepcopy
from typing import Any,Mapping

from yado_g2_experience_conditioned_cognitive_layer_v4 import G2ExperienceConditionedCognitiveLayerV4
from yado_organ_runtime_native_v1 import tree_predict


class G2ExperienceConditionedCognitiveLayerV5:
    COMPONENT_ID='RUNTIME-G2-EXPERIENCE-CONDITIONED-COGNITIVE-LAYER-V5'

    def __init__(self,artifact:Mapping[str,Any]):
        self.artifact=deepcopy(dict(artifact))
        if self.artifact.get('component_id')!=self.COMPONENT_ID:
            raise ValueError('COGNITIVE_LAYER_V5_COMPONENT_ID_MISMATCH')
        parent=self.artifact.get('parent_v4')
        if not isinstance(parent,dict):
            raise ValueError('COGNITIVE_LAYER_V5_PARENT_V4_MISSING')
        self.parent=G2ExperienceConditionedCognitiveLayerV4(parent)
        self.portable=deepcopy(self.artifact.get('portable_real_data_specialists') or {})
        self._portable_routes={}
        for organ,g in self.portable.items():
            task=str(g.get('task') or '')
            parent_task=str(g.get('parent_task') or '')
            for t in (task,parent_task):
                if t:self._portable_routes[(str(organ).upper(),t)]=g

    @staticmethod
    def _result(decision,source,task_id,organ):
        return G2ExperienceConditionedCognitiveLayerV4._result(decision,source,task_id,organ)

    @staticmethod
    def _raw_feature_transform(spec,payload):
        if str(spec.get('schema') or '')!='yado.real_data.feature_transform.usgs.v1':
            raise ValueError('UNSUPPORTED_PORTABLE_FEATURE_TRANSFORM')
        required=('mag','depth','tsunami','felt_any','reviewed')
        if not all(k in payload for k in required):
            return None
        return {
          'mag_ge_q75':float(payload['mag'])>=float(spec['mag_q75']),
          'shallow':float(payload['depth'])<float(spec['depth_shallow_lt']),
          'very_shallow':float(payload['depth'])<float(spec['depth_very_shallow_lt']),
          'tsunami':bool(payload['tsunami']),
          'felt_any':bool(payload['felt_any']),
          'reviewed':bool(payload['reviewed']),
        }

    def decide(self,organ,payload):
        organ=str(organ).upper()
        p=deepcopy(dict(payload or {}))
        task_id=str(p.get('task_id') or '')
        spec=self._portable_routes.get((organ,task_id))
        if spec is not None and organ=='LOGIC':
            try:
                x=self._raw_feature_transform(spec.get('feature_transform') or {},p)
            except Exception:
                x=None
            if x is not None:
                try:d=bool(tree_predict(spec.get('model'),x))
                except Exception:d=None
                out=self._result(d,'PORTABLE_REAL_DATA_V5',task_id,organ)
                out['portable_feature_contract']='yado.real_data.feature_transform.usgs.v1'
                out['portable_candidate_digest']=spec.get('candidate_digest')
                return out
            # Preserve backward compatibility for the legacy pre-transformed task.
            if task_id==str(spec.get('parent_task') or ''):
                return self.parent.decide(organ,p)
            return self._result(None,'PORTABLE_REAL_DATA_V5',task_id,organ)
        return self.parent.decide(organ,p)

    def compose(self,signals):
        return self.parent.compose(signals)

    def snapshot(self):
        base=self.parent.snapshot()
        return {
          'schema':'yado.g2.experience_conditioned_cognitive_layer.snapshot.v5',
          'component_id':self.COMPONENT_ID,
          'status':self.artifact.get('status'),
          'parent_component':self.artifact.get('parent_component'),
          'rollback_parent_component':self.artifact.get('rollback_parent_component'),
          'portable_specialist_count':sum(1 for _ in self.portable.values()),
          'portable_tasks':sorted({str(g.get('task')) for g in self.portable.values() if g.get('task')}),
          'parent_v4_snapshot':base,
          'automatic_canonical_promotion':False,
          'semantic_boundary':'V5 ADDS DECLARATIVE RAW-DATA PREPROCESSING FOR FRESH-READMITTED PORTABLE REAL-DATA SPECIALISTS AND DELEGATES ALL OTHER BEHAVIOR TO CANONICAL V4.'
        }

    @classmethod
    def component(cls):
        return {
          'schema':'yado.g2.experience_conditioned_cognitive_layer.component.v5',
          'component_id':cls.COMPONENT_ID,
          'parent_component':'RUNTIME-G2-EXPERIENCE-CONDITIONED-COGNITIVE-LAYER-V4',
          'automatic_canonical_promotion':False,
          'specialist_domains':['PORTABLE_REAL_DATA'],
          'fallback':'V4_CANONICAL_PARENT',
        }


__all__=['G2ExperienceConditionedCognitiveLayerV5']
