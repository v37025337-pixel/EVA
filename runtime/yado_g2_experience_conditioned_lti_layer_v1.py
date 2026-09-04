from __future__ import annotations
from copy import deepcopy

from yado_organ_runtime_native_v1 import plan_with_edges, tree_predict
from yado_budget_adaptive_compositional_logic_v2 import BudgetAdaptiveCompositionalLogicV2
from yado_work_budget_adaptive_contingent_planner_v2 import WorkBudgetAdaptiveContingentPlannerV2
from yado_coverage_pruned_compositional_schema_router_v3 import CoveragePrunedCompositionalSchemaRouterV3

class ExperienceConditionedLTILayerV1:
    COMPONENT_ID='RUNTIME-G2-EXPERIENCE-CONDITIONED-LTI-LAYER-V1'

    def __init__(self,genes):
        self.genes=deepcopy(dict(genes))
        required={'LOGIC','THINKING','INTELLIGENCE'}
        if set(self.genes)!=required:
            raise ValueError('THREE_EXPERIENCE_GENES_REQUIRED')

    def logic_history_assessment(self,features):
        model=self.genes['LOGIC']['model']
        return bool(tree_predict(model,dict(features)))

    def thinking_history_order(self,actions):
        model=self.genes['THINKING']['model']
        return plan_with_edges(list(actions),model)

    def intelligence_history_action(self,features):
        model=self.genes['INTELLIGENCE']['model']
        return tree_predict(model,dict(features))

class ExperienceAugmentedLTICompositeV1(ExperienceConditionedLTILayerV1):
    COMPONENT_ID='RUNTIME-G2-EXPERIENCE-AUGMENTED-LTI-COMPOSITE-V1'
    logic_base=BudgetAdaptiveCompositionalLogicV2
    thinking_base=WorkBudgetAdaptiveContingentPlannerV2
    intelligence_base=CoveragePrunedCompositionalSchemaRouterV3

    @classmethod
    def legacy_logic_learn(cls,rows):
        return cls.logic_base.learn_symmetric_boolean(rows)

    @classmethod
    def legacy_logic_predict(cls,model,x):
        return cls.logic_base.predict_symmetric_boolean(model,x)

    @classmethod
    def legacy_thinking_plan(cls,current_confidence,target_confidence,remaining_budget,stages,completed=()):
        return cls.thinking_base.plan(current_confidence,target_confidence,remaining_budget,stages,completed=completed)

    @classmethod
    def legacy_intelligence_fit(cls,cases,fallback_output,max_trigger_width=None):
        return cls.intelligence_base.fit(cases,fallback_output,max_trigger_width=max_trigger_width)

    @classmethod
    def legacy_intelligence_route(cls,model,x):
        return cls.intelligence_base.route(model,x)

__all__=['ExperienceConditionedLTILayerV1','ExperienceAugmentedLTICompositeV1']
