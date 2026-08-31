from __future__ import annotations
from collections import deque
from dataclasses import dataclass
import copy,hashlib,json

from yado_budgeted_stage_policy_v1 import BudgetedStagePolicyV1,SearchStage
from yado_neutral_evidence_profile_selector_v1 import NeutralEvidenceProfileSelectorV1,EvidenceCandidate

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()

class G2TypedRecurrentCapabilityGraphRuntimeV1:
    MAX_EPISODES=128
    MAX_ATTEMPTED_PER_STREAM=32

    def __init__(self,architecture,router_program,scalar_program,relation_program,portfolio):
        if architecture.get('architecture_family')!='TYPED_RECURRENT_CAPABILITY_GRAPH':
            raise ValueError('UNSUPPORTED_ARCHITECTURE')
        self.architecture=copy.deepcopy(architecture)
        self.router=router_program
        self.scalar=scalar_program
        self.relation=relation_program
        self.portfolio=copy.deepcopy(portfolio)
        self.episodes=deque(maxlen=self.MAX_EPISODES)
        self.stream_attempts={}
        self.sequence=0

    def _remember(self,record,ablated_memory=False):
        if ablated_memory:return
        self.sequence+=1
        x=copy.deepcopy(record)
        x['sequence']=self.sequence
        x['episode_digest']=digest(x)
        self.episodes.append(x)

    def observe_stage_outcome(self,stream_id,stage_id,observed_gain,ablated_memory=False):
        if ablated_memory:return
        xs=self.stream_attempts.setdefault(str(stream_id),[])
        if stage_id not in xs:
            xs.append(stage_id)
            if len(xs)>self.MAX_ATTEMPTED_PER_STREAM:
                del xs[:-self.MAX_ATTEMPTED_PER_STREAM]
        self._remember({
          'kind':'STAGE_OUTCOME','stream_id':str(stream_id),'stage_id':stage_id,
          'observed_gain':float(observed_gain)
        },False)

    def _budget_stages(self,task,ablated_memory=False):
        attempted=set() if ablated_memory else set(self.stream_attempts.get(str(task['stream_id']),[]))
        out=[]
        for s in task['stages']:
            out.append(SearchStage(
              stage_id=s['stage_id'],cost=float(s['cost']),expected_gain=float(s['expected_gain']),
              quota_remaining=int(s['quota_remaining']),available=bool(s.get('available',True)),
              latency=float(s.get('latency',1.0)),attempted=s['stage_id'] in attempted or bool(s.get('attempted',False))
            ))
        return out

    def run(self,task,ablated_router=False,ablated_memory=False):
        descriptor=task['descriptor']
        selected=self.router.fallback_output if ablated_router else self.router.execute(descriptor)
        result=None
        if selected==CAP_CONJ:
            result=self.scalar.execute(task['payload'])
        elif selected==CAP_REL:
            result=self.relation.execute(task['payload'])
        elif selected==CAP_BUD:
            stages=self._budget_stages(task,ablated_memory=ablated_memory)
            plan=BudgetedStagePolicyV1.plan(
              task['current_confidence'],task['target_confidence'],task['remaining_budget'],stages
            )
            result=plan.action
        elif selected==CAP_RES:
            key=task.get('route_key')
            routes=self.portfolio.get('routes_for_current_open_deficits',{})
            arr=routes.get(key,[])
            result=arr[0]['resource_id'] if arr else None
        else:
            raise ValueError('UNKNOWN_SELECTED_CAPABILITY:'+str(selected))
        self._remember({
          'kind':'TASK_EPISODE','task_kind':task.get('kind'),'stream_id':str(task.get('stream_id','')),
          'selected_capability':selected,'result':result,
        },ablated_memory)
        return {'selected_capability':selected,'result':result}

    def select_architecture_candidate(self,candidates):
        xs=[EvidenceCandidate(
          token=str(x['token']),evidence=float(x['evidence']),complexity=float(x.get('complexity',0)),
          risk=float(x.get('risk',0)),novelty=float(x.get('novelty',0))
        ) for x in candidates]
        return NeutralEvidenceProfileSelectorV1.select(xs)

    def memory_snapshot(self):
        return {
          'episode_count':len(self.episodes),
          'stream_attempts':copy.deepcopy(self.stream_attempts),
          'last_episode_digest':self.episodes[-1]['episode_digest'] if self.episodes else None,
        }

    @classmethod
    def component(cls,architecture_digest):
        x={
          'schema':'yado.g2.typed_recurrent_capability_graph_runtime.v1',
          'component_id':'RUNTIME-G2-TYPED-RECURRENT-CAPABILITY-GRAPH-V1',
          'architecture_digest':architecture_digest,
          'max_episodes':cls.MAX_EPISODES,
          'max_attempted_per_stream':cls.MAX_ATTEMPTED_PER_STREAM,
          'recurrent_memory':True,
          'typed_capability_dispatch':True,
          'resource_cost_aware':True,
        }
        x['component_digest']=digest(x)
        return x
