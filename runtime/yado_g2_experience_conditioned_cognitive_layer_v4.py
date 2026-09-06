from __future__ import annotations

from copy import deepcopy
from typing import Any,Mapping

from yado_g2_experience_conditioned_cognitive_layer_v3 import G2ExperienceConditionedCognitiveLayerV3
from yado_budget_adaptive_compositional_logic_v2 import BudgetAdaptiveCompositionalLogicV2
from yado_organ_runtime_native_v1 import tree_predict
from yado_cognitive_growth_runtime_v1 import plan_multicontext,knn_predict,centroid_predict

class G2ExperienceConditionedCognitiveLayerV4:
    COMPONENT_ID='RUNTIME-G2-EXPERIENCE-CONDITIONED-COGNITIVE-LAYER-V4'

    def __init__(self,artifact:Mapping[str,Any]):
        self.artifact=deepcopy(dict(artifact))
        if self.artifact.get('component_id')!=self.COMPONENT_ID:
            raise ValueError('COGNITIVE_LAYER_V4_COMPONENT_ID_MISMATCH')
        parent=self.artifact.get('parent_v3')
        if not isinstance(parent,dict):
            raise ValueError('COGNITIVE_LAYER_V4_PARENT_V3_MISSING')
        self.parent=G2ExperienceConditionedCognitiveLayerV3(parent)
        self.multidomain=deepcopy(self.artifact.get('multidomain_genes') or {})
        self.real_data=deepcopy(self.artifact.get('real_data_genes') or {})
        self.cognitive=deepcopy(self.multidomain.get('COGNITIVE') or {})
        self._multi_tasks={}
        for organ in ('LOGIC','THINKING','INTELLIGENCE'):
            g=self.multidomain.get(organ) or {}
            self._multi_tasks[organ]={str(x.get('task_id')):deepcopy(x) for x in (g.get('task_models') or []) if x.get('task_id')}
        self._real_tasks={}
        for organ in ('LOGIC','THINKING','INTELLIGENCE'):
            g=self.real_data.get(organ) or {}
            task=str(g.get('task') or '')
            if task:self._real_tasks[(organ,task)]=deepcopy(g)
        self._validate()

    def _validate(self):
        if self.artifact.get('status') not in {'CANONICAL_ACTIVE','SHADOW_READY'}:
            raise ValueError('COGNITIVE_LAYER_V4_BAD_STATUS')
        if self.artifact.get('automatic_canonical_promotion') is not False:
            raise ValueError('COGNITIVE_LAYER_V4_AUTO_PROMOTION_FORBIDDEN')
        for organ in ('LOGIC','THINKING','INTELLIGENCE'):
            if organ not in self.multidomain or organ not in self.real_data:
                raise ValueError('COGNITIVE_LAYER_V4_MISSING_ORGAN:'+organ)
        if not self.cognitive.get('model') or not self.cognitive.get('strategy_family'):
            raise ValueError('COGNITIVE_LAYER_V4_COGNITIVE_MODEL_MISSING')

    @staticmethod
    def _logic_predict(task,payload):
        fam=str((task.get('selected') or {}).get('family') or '')
        model=task.get('model')
        if fam=='SYMMETRIC_COUNT_MAP_V2':
            return bool(BudgetAdaptiveCompositionalLogicV2.predict_symmetric_boolean(model,payload))
        return bool(tree_predict(model,payload))

    @staticmethod
    def _intel_predict(task,payload):
        return tree_predict(task.get('model'),payload)

    @staticmethod
    def _thinking_predict(task,payload):
        context=payload.get('context')
        actions=payload.get('actions')
        if not isinstance(context,Mapping) or not isinstance(actions,list) or not actions:
            return None
        try:return plan_multicontext(task.get('model'),context,actions)
        except Exception:return None

    @staticmethod
    def _result(decision,source,task_id,organ):
        if decision is None:
            return {
              'decision':'WITHHOLD','gate':'WITHHOLD','route_cardinality':'ZERO',
              'matched_outputs':[],'guard_features':{'organ':organ,'task_id':task_id,'state_known':False},
              'source':source,
            }
        return {
          'decision':deepcopy(decision),'gate':'SPECIALIST_PASS_THROUGH','route_cardinality':'ONE',
          'matched_outputs':[deepcopy(decision)],
          'guard_features':{'organ':organ,'task_id':task_id,'state_known':True},
          'source':source,
        }

    def decide(self,organ,payload):
        organ=str(organ).upper();p=deepcopy(dict(payload or {}));task_id=str(p.get('task_id') or '')
        if task_id:
            task=self._multi_tasks.get(organ,{}).get(task_id)
            if task is not None:
                if organ=='LOGIC':d=self._logic_predict(task,p)
                elif organ=='INTELLIGENCE':d=self._intel_predict(task,p)
                else:d=self._thinking_predict(task,p)
                return self._result(d,'MULTIDOMAIN_PORTFOLIO',task_id,organ)
            rg=self._real_tasks.get((organ,task_id))
            if rg is not None:
                if organ=='LOGIC':d=bool(tree_predict(rg.get('model'),p))
                elif organ=='INTELLIGENCE':d=tree_predict(rg.get('model'),p)
                else:d=self._thinking_predict(rg,p)
                return self._result(d,'REAL_DATA_PORTFOLIO',task_id,organ)
        out=self.parent.decide(organ,p)
        out=deepcopy(out);out['source']='V3_FAIL_CLOSED_FALLBACK'
        return out

    def compose(self,signals):
        s=deepcopy(dict(signals or {}))
        required=('logic_accept','thinking_cautious','intelligence_robust')
        if not all(k in s for k in required):
            return {'decision':'WITHHOLD','gate':'WITHHOLD','source':'MULTIDOMAIN_COGNITIVE_COMPOSER','missing':[k for k in required if k not in s]}
        fam=str(self.cognitive.get('strategy_family') or '')
        model=self.cognitive.get('model')
        x={k:float(bool(s.get(k))) for k in required}
        if fam=='KNN_STRATEGY':d=knn_predict(model,x)
        elif fam=='CENTROID_STRATEGY':d=centroid_predict(model,x)
        else:d=tree_predict(model,x)
        return {'decision':d,'gate':'SPECIALIST_PASS_THROUGH','source':'MULTIDOMAIN_COGNITIVE_COMPOSER','signals':x}

    def snapshot(self):
        return {
          'schema':'yado.g2.experience_conditioned_cognitive_layer.snapshot.v4',
          'component_id':self.COMPONENT_ID,
          'status':self.artifact.get('status'),
          'parent_component':self.artifact.get('parent_component'),
          'multidomain_genome_id':self.artifact.get('multidomain_genome_id'),
          'real_data_portfolio_id':self.artifact.get('real_data_portfolio_id'),
          'global_negative_evidence':deepcopy(self.artifact.get('global_negative_evidence')),
          'automatic_canonical_promotion':False,
          'specialist_task_counts':{
            organ:len(self._multi_tasks.get(organ,{}))+sum(1 for (o,_) in self._real_tasks if o==organ)
            for organ in ('LOGIC','THINKING','INTELLIGENCE')
          },
          'semantic_boundary':'V4 IS A SINGLE BOUNDED COGNITIVE LAYER WITH TASK-ID SPECIALISTS AND V3 FAIL-CLOSED FALLBACK. IT DOES NOT CLAIM SUBJECTIVE CONSCIOUSNESS OR GENERAL INTELLIGENCE.'
        }

    @classmethod
    def component(cls):
        return {
          'schema':'yado.g2.experience_conditioned_cognitive_layer.component.v4',
          'component_id':cls.COMPONENT_ID,
          'parent_component':'RUNTIME-G2-EXPERIENCE-CONDITIONED-COGNITIVE-LAYER-V3',
          'automatic_canonical_promotion':False,
          'specialist_domains':['MULTIDOMAIN','REAL_DATA'],
          'fallback':'V3_FAIL_CLOSED',
        }

__all__=['G2ExperienceConditionedCognitiveLayerV4']
