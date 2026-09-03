from __future__ import annotations
import copy,hashlib,json

from yado_g2_unified_execution_fabric_v2 import G2UnifiedExecutionFabricV2
from yado_g2_cognitive_clock_v1 import G2CognitiveClockV1

def _canon_v3(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def _digest_v3(o):return hashlib.sha256(_canon_v3(o).encode()).hexdigest()

class G2UnifiedExecutionFabricV3(G2UnifiedExecutionFabricV2):
    COMPONENT_ID='RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V3'

    def __init__(self,base_runtime,api_state=None,temporal_state=None):
        super().__init__(base_runtime,api_state=api_state)
        self.clock=G2CognitiveClockV1(temporal_state)
        self._tick_stack=[]

    @staticmethod
    def _entities(task):
        xs=[]
        for field,typ in [('goal_id','GOAL'),('hypothesis_id','HYPOTHESIS'),('memory_id','MEMORY'),('thought_id','THOUGHT')]:
            if task.get(field) is not None:xs.append({'entity_id':str(task[field]),'entity_type':typ})
        for x in task.get('temporal_entities',[]) or []:xs.append(copy.deepcopy(x))
        return xs

    @staticmethod
    def _state_projection(cap,task):
        keep={
          'selected_capability':str(cap),
          'kind':task.get('kind'),
          'operation':task.get('operation'),
          'stream_id':str(task.get('stream_id','')),
          'descriptor':task.get('descriptor'),
          'current_confidence':task.get('current_confidence'),
          'target_confidence':task.get('target_confidence'),
          'remaining_budget':task.get('remaining_budget'),
          'completed':task.get('completed'),
          'goal_id':task.get('goal_id'),
          'hypothesis_id':task.get('hypothesis_id'),
          'deficit_id':task.get('deficit_id'),
        }
        return {k:v for k,v in keep.items() if v is not None}

    def _parent_tick(self):
        return self._tick_stack[-1] if self._tick_stack else None

    def _write_temporal_transition(self,closed,cap,ablated_memory=False):
        record={
          'kind':'TEMPORAL_TRANSITION',
          'stream_id':closed['stream_id'],
          'tick_id':closed['tick_id'],
          'episode_tick':closed['episode_tick'],
          'predecessor_tick':closed.get('predecessor_tick'),
          'parent_tick':closed.get('parent_tick'),
          'selected_capability':str(cap),
          'state_digest':closed.get('state_digest'),
          'observed_result_digest':closed.get('observed_result_digest'),
          'next_state_digest':closed.get('next_state_digest'),
          'progress_digest':closed.get('progress_digest'),
          'no_progress_ticks':closed.get('no_progress_ticks'),
          'mechanism_change_required':closed.get('mechanism_change_required'),
          'tick_digest':closed.get('tick_digest'),
        }
        self._remember(record,ablated_memory=ablated_memory)
        if closed.get('no_progress_ticks')==self.clock.DEFAULT_STALL_THRESHOLD:
            self._remember({
              'kind':'TEMPORAL_STALL_SIGNAL',
              'stream_id':closed['stream_id'],
              'tick_id':closed['tick_id'],
              'no_progress_ticks':closed['no_progress_ticks'],
              'deficit_id':closed.get('state_projection',{}).get('deficit_id'),
              'mechanism_change_required':True,
              'cause_tick_digest':closed.get('tick_digest'),
            },ablated_memory=ablated_memory)

    def execute_capability(self,selected,task,ablated_memory=False):
        cap=str(selected)
        stream_id=str(task.get('stream_id','FABRIC'))
        state=self._state_projection(cap,task)
        begin=self.clock.begin_tick(
            stream_id=stream_id,
            action=cap,
            state=state,
            cause=task.get('cause'),
            prediction=task.get('prediction',task.get('expected_result')),
            entities=self._entities(task),
            parent_tick=self._parent_tick(),
        )
        self._tick_stack.append(begin['tick_id'])
        try:
            out=super().execute_capability(cap,task,ablated_memory=ablated_memory)
            progress_token=task.get('progress_token')
            if progress_token is None and task.get('deficit_state') is not None:
                progress_token={'deficit_state':task.get('deficit_state')}
            closed=self.clock.finish_tick(
                begin['tick_id'],
                observed_result=out,
                progress_token=progress_token,
                next_state=task.get('next_state'),
            )
            self._write_temporal_transition(closed,cap,ablated_memory=ablated_memory)
            out=copy.deepcopy(out)
            out['temporal']={
              'tick_id':closed['tick_id'],
              'episode_tick':closed['episode_tick'],
              'predecessor_tick':closed.get('predecessor_tick'),
              'parent_tick':closed.get('parent_tick'),
              'no_progress_ticks':closed['no_progress_ticks'],
              'mechanism_change_required':closed['mechanism_change_required'],
              'tick_digest':closed['tick_digest'],
            }
            return out
        except Exception as e:
            closed=self.clock.finish_tick(
                begin['tick_id'],
                observed_result={'status':'ERROR','error_type':type(e).__name__,'error':str(e)[:512]},
                progress_token=task.get('progress_token',{'error_type':type(e).__name__}),
            )
            self._write_temporal_transition(closed,cap,ablated_memory=ablated_memory)
            raise
        finally:
            if self._tick_stack and self._tick_stack[-1]==begin['tick_id']:
                self._tick_stack.pop()
            elif begin['tick_id'] in self._tick_stack:
                self._tick_stack.remove(begin['tick_id'])

    def record_outcome(self,stream_id,stage_id,observed_gain):
        begin=self.clock.begin_tick(
            stream_id=str(stream_id),action='OBSERVE_STAGE_OUTCOME',
            state={'stage_id':str(stage_id),'observed_gain':float(observed_gain)},
            cause='EXTERNAL_OR_INTERNAL_OBSERVATION',
            entities=[{'entity_id':'STAGE:'+str(stage_id),'entity_type':'STAGE'}],
            parent_tick=self._parent_tick(),
        )
        result=super().record_outcome(stream_id,stage_id,observed_gain)
        closed=self.clock.finish_tick(
            begin['tick_id'],observed_result=result,
            progress_token={'stage_id':str(stage_id),'observed_gain':float(observed_gain)}
        )
        self._write_temporal_transition(closed,'OBSERVE_STAGE_OUTCOME',ablated_memory=False)
        return result|{'temporal':{
          'tick_id':closed['tick_id'],'episode_tick':closed['episode_tick'],
          'predecessor_tick':closed.get('predecessor_tick'),'tick_digest':closed['tick_digest']
        }}

    def temporal_snapshot(self):
        return self.clock.snapshot()

    def temporal_stream_state(self,stream_id):
        return self.clock.stream_state(stream_id)

    def temporal_causal_chain(self,stream_id,limit=32):
        return self.clock.causal_chain(stream_id,limit=limit)

    def temporal_entity_age(self,entity_id):
        return self.clock.entity_age(entity_id)

    def temporal_evolution_signal(self,stream_id):
        state=self.clock.stream_state(stream_id)
        required=bool(state.get('mechanism_change_required'))
        out={
          'schema':'yado.g2.temporal_evolution_signal.v1',
          'stream_id':state['stream_id'],
          'last_tick':state.get('last_tick'),
          'no_progress_ticks':state.get('no_progress_ticks',0),
          'mechanism_change_required':required,
          'recommended_action':'EVOLVE_MECHANISM' if required else 'CONTINUE_CURRENT_MECHANISM',
        }
        out['signal_digest']=_digest_v3(out)
        return out

    def export_temporal_state(self):
        return self.clock.export_state()

    def memory_snapshot(self):
        x=super().memory_snapshot()
        x['temporal']=self.clock.snapshot()
        x['temporal_transition_count']=sum(1 for e in self.base.episodes if e.get('kind')=='TEMPORAL_TRANSITION')
        x['temporal_stall_signal_count']=sum(1 for e in self.base.episodes if e.get('kind')=='TEMPORAL_STALL_SIGNAL')
        return x

    @classmethod
    def component(cls):
        parent=G2UnifiedExecutionFabricV2.component()
        x={
          'schema':'yado.g2.unified_execution_fabric.v3',
          'component_id':cls.COMPONENT_ID,
          'parent_component':'RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V2',
          'architecture_family':'TYPED_RECURRENT_CAPABILITY_GRAPH',
          'dispatches':parent.get('dispatches',[]),
          'temporal_kernel':G2CognitiveClockV1.component(),
          'temporal_integration':{
             'all_capability_execution_ticks':True,
             'stage_outcome_ticks':True,
             'recurrent_temporal_transition_memory':True,
             'causal_predecessor_chain':True,
             'episode_time_per_stream':True,
             'entity_age':True,
             'no_progress_detection':True,
             'stall_signal_to_memory':True,
             'stall_signal_to_evolution_controller':True,
          },
          'network_execution':parent.get('network_execution'),
          'canonical_active':False,'architecture_mutation':False,
          'semantic_boundary':'SHADOW SUCCESSOR OF FABRIC V2 ADDING LOGICAL TEMPORAL CONTINUITY TO CAPABILITY EXECUTION WITHOUT CHANGING FORMAL G2 GENERATION.'
        }
        x['component_digest']=_digest_v3(x);return x

__all__=['G2UnifiedExecutionFabricV3']
