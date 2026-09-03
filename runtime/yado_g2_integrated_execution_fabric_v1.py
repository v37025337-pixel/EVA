from __future__ import annotations
import copy,hashlib,json

from yado_g2_typed_recurrent_capability_graph_runtime_v1 import G2TypedRecurrentCapabilityGraphRuntimeV1
from yado_budget_adaptive_compositional_logic_v2 import BudgetAdaptiveCompositionalLogicV2
from yado_work_budget_adaptive_contingent_planner_v2 import WorkBudgetAdaptiveContingentPlannerV2,ContingentStage
from yado_coverage_pruned_compositional_schema_router_v3 import CoveragePrunedCompositionalSchemaRouterV3

CAP_LOGIC_V2=BudgetAdaptiveCompositionalLogicV2.COMPONENT_ID
CAP_THINK_V2=WorkBudgetAdaptiveContingentPlannerV2.COMPONENT_ID
CAP_INTEL_V3=CoveragePrunedCompositionalSchemaRouterV3.COMPONENT_ID

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()

class G2IntegratedExecutionFabricV1(G2TypedRecurrentCapabilityGraphRuntimeV1):
    COMPONENT_ID='RUNTIME-G2-INTEGRATED-EXECUTION-FABRIC-V1'
    MAX_FEEDBACK_RECORDS=128

    def __init__(self,architecture,router_program,scalar_program,relation_program,portfolio):
        super().__init__(architecture,router_program,scalar_program,relation_program,portfolio)
        self.feedback=[]

    @staticmethod
    def _stage(x):
        return ContingentStage(str(x['stage_id']),float(x['cost']),float(x['expected_gain']),int(x.get('quota_remaining',1)),bool(x.get('available',True)),float(x.get('latency',1.0)),bool(x.get('attempted',False)),tuple(str(z) for z in x.get('requires',())))

    def _remember_feedback(self,record,ablated_memory=False):
        if ablated_memory:return
        x=copy.deepcopy(record);x['feedback_digest']=digest(x)
        self.feedback.append(x)
        if len(self.feedback)>self.MAX_FEEDBACK_RECORDS:del self.feedback[:-self.MAX_FEEDBACK_RECORDS]
        self._remember({'kind':'SEMANTIC_FEEDBACK',**x},False)

    def _last_stage_gain(self,stream_id,stage_id):
        for x in reversed(self.feedback):
            if str(x.get('stream_id'))==str(stream_id) and str(x.get('stage_id'))==str(stage_id):
                return float(x.get('observed_gain',0.0))
        return None

    def run(self,task,ablated_router=False,ablated_memory=False):
        descriptor=task.get('descriptor',{})
        selected=self.router.fallback_output if ablated_router else self.router.execute(descriptor)
        if selected not in {CAP_LOGIC_V2,CAP_THINK_V2,CAP_INTEL_V3}:
            return super().run(task,ablated_router=ablated_router,ablated_memory=ablated_memory)

        result=None;meta={}
        if selected==CAP_LOGIC_V2:
            mode=str(task.get('logic_mode','symmetric_boolean'))
            if mode=='symmetric_boolean':
                model=task.get('model') or BudgetAdaptiveCompositionalLogicV2.learn_symmetric_boolean(task['train_rows'])
                result=BudgetAdaptiveCompositionalLogicV2.predict_symmetric_boolean(model,task['payload'])
                meta={'logic_mode':mode,'model_kind':model.get('kind')}
            elif mode=='polynomial':
                model=task.get('model') or BudgetAdaptiveCompositionalLogicV2.fit_polynomial(task['train_rows'],max_degree=int(task.get('max_degree',8)))
                result=BudgetAdaptiveCompositionalLogicV2.predict_polynomial(model,task['x'],task['y'])
                meta={'logic_mode':mode,'model_kind':model.get('kind')}
            else:raise ValueError('UNKNOWN_LOGIC_MODE:'+mode)

        elif selected==CAP_THINK_V2:
            stages=[self._stage(x) for x in task['stages']]
            completed=tuple(str(x) for x in task.get('completed',()))
            observation=task.get('observation')
            if observation is None and task.get('completed_stage_id'):
                gain=None if ablated_memory else self._last_stage_gain(task.get('stream_id',''),task['completed_stage_id'])
                if gain is not None:observation={'stage_id':task['completed_stage_id'],'observed_gain':gain}
            if observation is not None:
                plan=WorkBudgetAdaptiveContingentPlannerV2.next_after_observation(task['current_confidence'],task['target_confidence'],task['remaining_budget'],stages,str(observation['stage_id']),float(observation['observed_gain']),completed=completed)
                meta={'feedback_consumed':True,'observed_gain':float(observation['observed_gain'])}
            else:
                plan=WorkBudgetAdaptiveContingentPlannerV2.plan(task['current_confidence'],task['target_confidence'],task['remaining_budget'],stages,completed=completed)
                meta={'feedback_consumed':False}
            result=plan.action;meta.update({'sequence':plan.sequence,'expected_confidence':plan.expected_confidence,'feasible':plan.feasible,'reason':plan.reason})

        else:
            mode=str(task.get('intelligence_mode','route'))
            if mode=='route':
                model=task.get('model') or CoveragePrunedCompositionalSchemaRouterV3.fit(task['train_cases'],task['fallback_output'])
                result=CoveragePrunedCompositionalSchemaRouterV3.route(model,task['payload'])
                meta={'intelligence_mode':mode,'model_kind':model.get('kind')}
            elif mode=='route_aligned':
                result=CoveragePrunedCompositionalSchemaRouterV3.route_aligned(task['model'],task['alignment'],task['payload'])
                meta={'intelligence_mode':mode}
            else:raise ValueError('UNKNOWN_INTELLIGENCE_MODE:'+mode)

        self._remember({'kind':'TASK_EPISODE','task_kind':task.get('kind'),'stream_id':str(task.get('stream_id','')),'selected_capability':selected,'result':result,'meta':meta},ablated_memory)
        return {'selected_capability':selected,'result':result,'meta':meta}

    def observe_stage_outcome(self,stream_id,stage_id,observed_gain,ablated_memory=False):
        super().observe_stage_outcome(stream_id,stage_id,observed_gain,ablated_memory=ablated_memory)
        self._remember_feedback({'stream_id':str(stream_id),'stage_id':str(stage_id),'observed_gain':float(observed_gain)},ablated_memory=ablated_memory)

    def memory_snapshot(self):
        x=super().memory_snapshot();x['semantic_feedback_count']=len(self.feedback);x['last_feedback_digest']=self.feedback[-1]['feedback_digest'] if self.feedback else None;return x

    @classmethod
    def component(cls,architecture_digest):
        x={'schema':'yado.g2.integrated_execution_fabric.v1','component_id':cls.COMPONENT_ID,'architecture_digest':architecture_digest,'extends':'RUNTIME-G2-TYPED-RECURRENT-CAPABILITY-GRAPH-V1','direct_dispatch':[CAP_LOGIC_V2,CAP_THINK_V2,CAP_INTEL_V3],'semantic_feedback_memory':True,'bounded_feedback_records':cls.MAX_FEEDBACK_RECORDS,'architecture_mutation':False,'canonical_active':False}
        x['component_digest']=digest(x);return x

__all__=['G2IntegratedExecutionFabricV1','CAP_LOGIC_V2','CAP_THINK_V2','CAP_INTEL_V3']
