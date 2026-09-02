from __future__ import annotations
import copy,hashlib,json
from yado_g2_contextual_stream_capability_adapter_v1 import ContextualStreamCapabilityAdapterV1
from yado_bounded_capability_set_coordinator_v1 import BoundedCapabilitySetCoordinatorV1

def _canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def _digest(o):return hashlib.sha256(_canon(o).encode()).hexdigest()

class G2CompositeTransferRepairAdapterV1:
    """
    Shadow repair adapter selected from existing G2 substrates.
    Context selection is performed once by ContextualStreamCapabilityAdapterV1.
    Execution is then forced through BoundedCapabilitySetCoordinatorV1 so the
    parent router cannot reinterpret the already-selected capability.
    """
    COMPONENT_ID="ALG-G2-COMPOSITE-TRANSFER-REPAIR-ADAPTER-V1"

    def __init__(self,parent_runtime):
        self.parent_runtime=parent_runtime
        self.context=ContextualStreamCapabilityAdapterV1(parent_runtime,'BOUNDED_STREAM_CONTEXT_MAP')

    def run(self,task,ablated_context=False):
        desc=task.get('descriptor',{})
        selected=self.parent_runtime.router.execute(desc) if ablated_context else self.context.choose(task)
        cap_task=copy.deepcopy(task)
        cap_task.pop('descriptor',None)
        cap_task['descriptor']={}
        cap_task.setdefault('stream_id',str(task.get('stream_id','')))
        out=BoundedCapabilitySetCoordinatorV1.run(self.parent_runtime,[selected],{selected:cap_task})
        if out.get('status')!='PASS':
            raise RuntimeError('FORCED_CAPABILITY_EXECUTION_FAILED:'+json.dumps(out,sort_keys=True,default=str))
        result=out['results'][selected]
        if not ablated_context and not self.context._ambiguous(desc):
            self.context._map_put(task.get('stream_id',''),selected)
        return {
          'selected_capability':selected,
          'result':result.get('result'),
          'parent_result':result,
          'context_strategy':'BOUNDED_STREAM_CONTEXT_MAP',
          'execution_strategy':'BOUNDED_CAPABILITY_SET_FORCED_SINGLE_CAPABILITY',
          'repair_adapter':self.COMPONENT_ID,
        }

    def clear_context(self):
        self.context.clear_context()

    @classmethod
    def component(cls):
        x={
          'schema':'yado.g2.composite_transfer_repair_adapter.v1',
          'component_id':cls.COMPONENT_ID,
          'context_selector':'ALG-G2-CONTEXTUAL-STREAM-CAPABILITY-ADAPTER-V1',
          'execution_substrate':BoundedCapabilitySetCoordinatorV1.COMPONENT_ID,
          'selection_count_per_task':1,
          'parent_router_reinterpretation':False,
          'parent_runtime_modified':False,
          'canonical_active':False,
        }
        x['component_digest']=_digest(x)
        return x
