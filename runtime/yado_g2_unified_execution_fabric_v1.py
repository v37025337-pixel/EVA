from __future__ import annotations
from dataclasses import asdict
import copy,hashlib,json

from yado_bounded_capability_set_coordinator_v1 import BoundedCapabilitySetCoordinatorV1
from yado_budget_adaptive_compositional_logic_v2 import BudgetAdaptiveCompositionalLogicV2
from yado_work_budget_adaptive_contingent_planner_v2 import WorkBudgetAdaptiveContingentPlannerV2,ContingentStage
from yado_coverage_pruned_compositional_schema_router_v3 import CoveragePrunedCompositionalSchemaRouterV3
from yado_g2_openapi_contract_capability_v1 import G2OpenAPIContractCapabilityV1

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'
CAP_LOGIC_V2='ALG-G2-BUDGET-ADAPTIVE-COMPOSITIONAL-LOGIC-V2'
CAP_THINK_V2='ALG-G2-WORK-BUDGET-ADAPTIVE-CONTINGENT-PLANNER-V2'
CAP_INTEL_V3='ALG-G2-COVERAGE-PRUNED-COMPOSITIONAL-SCHEMA-ROUTER-V3'
CAP_API_V1='ALG-G2-OPENAPI-CONTRACT-CAPABILITY-V1'

def _canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def _digest(o):return hashlib.sha256(_canon(o).encode()).hexdigest()

class _ForcedRouter:
    def __init__(self,cap):self.capability=str(cap);self.fallback_output=self.capability
    def execute(self,descriptor):return self.capability

class G2UnifiedExecutionFabricV1:
    COMPONENT_ID='RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V1'
    LEGACY={CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES}

    def __init__(self,base_runtime,api_state=None):
        self.base=base_runtime
        self.router=base_runtime.router
        self.logic=BudgetAdaptiveCompositionalLogicV2
        self.thinking=WorkBudgetAdaptiveContingentPlannerV2
        self.intelligence=CoveragePrunedCompositionalSchemaRouterV3
        self.api=G2OpenAPIContractCapabilityV1(api_state or {})

    @property
    def episodes(self):return self.base.episodes
    @property
    def stream_attempts(self):return self.base.stream_attempts

    def _remember(self,record,ablated_memory=False):
        self.base._remember(record,ablated_memory=ablated_memory)

    @staticmethod
    def _stages(rows):
        return [ContingentStage(
            str(x['stage_id']),float(x['cost']),float(x['expected_gain']),int(x.get('quota_remaining',1)),
            bool(x.get('available',True)),float(x.get('latency',1.0)),bool(x.get('attempted',False)),
            tuple(str(z) for z in x.get('requires',()))
        ) for x in rows]

    def _latest_stage_outcome(self,stream_id):
        sid=str(stream_id)
        for e in reversed(self.base.episodes):
            if e.get('kind')=='STAGE_OUTCOME' and str(e.get('stream_id',''))==sid:
                return copy.deepcopy(e)
        return None

    def record_outcome(self,stream_id,stage_id,observed_gain):
        self.base.observe_stage_outcome(stream_id,stage_id,observed_gain)
        return self._latest_stage_outcome(stream_id)

    def _legacy(self,cap,task,ablated_memory=False):
        old=self.base.router
        self.base.router=_ForcedRouter(cap)
        try:return self.base.run(task,ablated_memory=ablated_memory)
        finally:self.base.router=old

    def _logic(self,task):
        op=str(task.get('operation','predict_symmetric'))
        if op=='learn_symmetric':
            result=self.logic.learn_symmetric_boolean(task['rows'])
        elif op=='predict_symmetric':
            result=self.logic.predict_symmetric_boolean(task['model'],task.get('payload',{}))
        elif op=='fit_polynomial':
            result=self.logic.fit_polynomial(task['rows'],max_degree=int(task.get('max_degree',8)))
        elif op=='predict_polynomial':
            result=self.logic.predict_polynomial(task['model'],task['x'],task['y'])
        else:raise ValueError('UNKNOWN_LOGIC_V2_OPERATION:'+op)
        return result,{"operation":op}

    def _thinking(self,task):
        stages=self._stages(task['stages'])
        op=str(task.get('operation','plan'))
        feedback=None
        if op=='auto_feedback_plan':
            feedback=self._latest_stage_outcome(task.get('stream_id',''))
            if feedback:
                plan=self.thinking.next_after_observation(
                    task['current_confidence'],task['target_confidence'],task['remaining_budget'],stages,
                    feedback['stage_id'],feedback['observed_gain'],completed=tuple(task.get('completed',()))
                )
                return asdict(plan),{"operation":op,"memory_feedback_used":True,"feedback_episode_digest":feedback.get('episode_digest')}
            op='plan'
        if op=='plan':
            plan=self.thinking.plan(
                task['current_confidence'],task['target_confidence'],task['remaining_budget'],stages,
                completed=tuple(task.get('completed',()))
            )
            return asdict(plan),{"operation":op,"memory_feedback_used":False}
        if op=='next_after_observation':
            plan=self.thinking.next_after_observation(
                task['current_confidence'],task['target_confidence'],task['remaining_budget'],stages,
                str(task['completed_stage_id']),float(task['observed_gain']),completed=tuple(task.get('completed',()))
            )
            return asdict(plan),{"operation":op,"memory_feedback_used":False}
        raise ValueError('UNKNOWN_THINKING_V2_OPERATION:'+op)

    def _intelligence(self,task):
        op=str(task.get('operation','route'))
        if op=='route':
            result=self.intelligence.route(task['model'],task.get('payload',task.get('descriptor',{})))
            return result,{"operation":op}
        if op=='route_aligned':
            result=self.intelligence.route_aligned(task['model'],task['alignment'],task.get('payload',{}))
            return result,{"operation":op}
        if op=='route_execute':
            selected=tuple(self.intelligence.route(task['model'],task.get('payload',task.get('descriptor',{}))))
            cap_tasks=task['capability_tasks']
            ordered=BoundedCapabilitySetCoordinatorV1.order(selected,cap_tasks)
            if ordered.get('status')!='PASS':
                return ordered,{"operation":op,"selected":selected}
            results={}
            for cap in ordered['order']:
                sub=copy.deepcopy(cap_tasks[cap]);sub.pop('requires_capabilities',None)
                sub.setdefault('stream_id',task.get('stream_id','FABRIC'))
                results[cap]=self.execute_capability(cap,sub)
            return {"status":"PASS","selected":selected,"order":ordered['order'],"results":results},{"operation":op}
        raise ValueError('UNKNOWN_INTELLIGENCE_V3_OPERATION:'+op)

    def _api(self,task):
        op=str(task.get('operation','compile_plan'))
        if op=='classify':return self.api.classify(str(task['contract_id'])),{"operation":op}
        if op=='compile_plan':return self.api.compile_plan(str(task['contract_id'])),{"operation":op}
        raise ValueError('UNKNOWN_API_OPERATION:'+op)

    def execute_capability(self,selected,task,ablated_memory=False):
        cap=str(selected)
        if cap in self.LEGACY:
            out=self._legacy(cap,task,ablated_memory=ablated_memory)
            return {"selected_capability":cap,"result":out.get('result'),"parent_result":out}
        if cap==CAP_LOGIC_V2:result,meta=self._logic(task)
        elif cap==CAP_THINK_V2:result,meta=self._thinking(task)
        elif cap==CAP_INTEL_V3:result,meta=self._intelligence(task)
        elif cap==CAP_API_V1:result,meta=self._api(task)
        else:raise ValueError('UNKNOWN_FABRIC_CAPABILITY:'+cap)
        self._remember({
            'kind':'FABRIC_EPISODE','stream_id':str(task.get('stream_id','')),
            'selected_capability':cap,'result':result,'meta':meta,
        },ablated_memory=ablated_memory)
        return {"selected_capability":cap,"result":result,"meta":meta}

    def run(self,task,ablated_memory=False):
        selected=str(task.get('selected_capability') or self.router.execute(task.get('descriptor',{})))
        return self.execute_capability(selected,task,ablated_memory=ablated_memory)

    def run_capability_set(self,selected_capabilities,capability_tasks):
        ordered=BoundedCapabilitySetCoordinatorV1.order(selected_capabilities,capability_tasks)
        if ordered.get('status')!='PASS':return ordered|{"results":{}}
        results={}
        for cap in ordered['order']:
            task=copy.deepcopy(capability_tasks[cap]);task.pop('requires_capabilities',None)
            results[cap]=self.execute_capability(cap,task)
        return {"status":"PASS","reason":"UNIFIED_FABRIC_CAPABILITY_SET_EXECUTED","order":ordered['order'],"results":results}

    def memory_snapshot(self):
        x=self.base.memory_snapshot()
        x['fabric_episode_count']=sum(1 for e in self.base.episodes if e.get('kind')=='FABRIC_EPISODE')
        x['stage_outcome_count']=sum(1 for e in self.base.episodes if e.get('kind')=='STAGE_OUTCOME')
        return x

    @classmethod
    def component(cls):
        x={
          'schema':'yado.g2.unified_execution_fabric.v1',
          'component_id':cls.COMPONENT_ID,
          'architecture_family':'TYPED_RECURRENT_CAPABILITY_GRAPH',
          'dispatches':sorted(cls.LEGACY|{CAP_LOGIC_V2,CAP_THINK_V2,CAP_INTEL_V3,CAP_API_V1}),
          'memory_feedback':'STAGE_OUTCOME_TO_AUTO_FEEDBACK_PLAN',
          'bounded_capability_ordering':True,
          'legacy_parent_runtime_modified':False,
          'network_execution':False,
          'canonical_active':False,
        }
        x['component_digest']=_digest(x)
        return x

__all__=['G2UnifiedExecutionFabricV1']
