from __future__ import annotations
import copy,hashlib,json
from yado_g2_contextual_stream_capability_adapter_v1 import ContextualStreamCapabilityAdapterV1

def _canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def _digest(o):return hashlib.sha256(_canon(o).encode()).hexdigest()

class G2CompositeClonalSuccessorPrototypeV1:
    """
    Shadow CLONAL successor wrapper over the existing canonical G2 runtime.
    It does not rewrite the parent runtime. It binds three evidence-selected roles:
    local recurrent context, neuro-symbolic bounded execution (inside parent G2),
    and native evolutionary control.
    """
    FAMILY_ROLES={
      'OPEN_ENDED_EVOLUTION':'NATIVE_EVOLUTIONARY_PARENT_AND_OPERATION_CONTROL',
      'LOCAL_SELF_ORGANIZING':'BOUNDED_STREAM_LOCAL_RECURRENT_CONTEXT',
      'NEURO_SYMBOLIC':'PARENT_G2_BOUNDED_RULE_AND_RELATION_EXECUTION',
    }

    def __init__(self,parent_runtime,kernel,design):
        self.parent_runtime=parent_runtime
        self.kernel=kernel
        self.design=copy.deepcopy(design)
        fam=list(self.design.get('selected_families') or [])
        if fam!=['OPEN_ENDED_EVOLUTION','LOCAL_SELF_ORGANIZING','NEURO_SYMBOLIC']:
            raise ValueError('COMPOSITE_FAMILY_DRIFT')
        op=(self.design.get('kernel_selected_evolution_operation') or {}).get('operation')
        if op!='CLONAL':raise ValueError('PROTOTYPE_REQUIRES_CLONAL_DESIGN')
        self.adapter=ContextualStreamCapabilityAdapterV1(parent_runtime,'BOUNDED_STREAM_CONTEXT_MAP')

    def run(self,task,ablated_local_context=False):
        out=self.adapter.run(task,ablated_context=ablated_local_context)
        out['prototype']='G2_COMPOSITE_CLONAL_SUCCESSOR_PROTOTYPE_V1'
        out['family_roles']=copy.deepcopy(self.FAMILY_ROLES)
        return out

    def evolution_control(self,records,target_task):
        parent=self.kernel.select_evolution_parent(records,target_task)
        operation=self.kernel.propose_evolution_operation(records,parent['variant_id'],target_task)
        return {'parent':parent,'operation':operation}

    def snapshot(self):
        x={
          'schema':'yado.g2.composite_clonal_successor_prototype.v1',
          'parent_runtime_component':self.parent_runtime.component(self.parent_runtime.architecture.get('architecture_digest')),
          'design_digest':self.design.get('design_digest'),
          'family_roles':copy.deepcopy(self.FAMILY_ROLES),
          'context_strategy':'BOUNDED_STREAM_CONTEXT_MAP',
          'parent_runtime_modified':False,
          'architecture_mutation':False,
        }
        x['snapshot_digest']=_digest(x)
        return x
