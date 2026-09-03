from __future__ import annotations
import copy,hashlib,json

from yado_g2_unified_execution_fabric_v1 import G2UnifiedExecutionFabricV1,CAP_LOGIC_V2,CAP_THINK_V2,CAP_INTEL_V3,CAP_API_V1
from yado_g2_openapi_readonly_executor_v1 import G2OpenAPIReadOnlyExecutorV1

CAP_API_EXEC_V1='ALG-G2-OPENAPI-READONLY-EXECUTOR-V1'

def _canon_v2(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def _digest_v2(o):return hashlib.sha256(_canon_v2(o).encode()).hexdigest()

class G2UnifiedExecutionFabricV2(G2UnifiedExecutionFabricV1):
    COMPONENT_ID='RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V2'

    def __init__(self,base_runtime,api_state=None):
        super().__init__(base_runtime,api_state=api_state)

    @staticmethod
    def _bounded_external_evidence(result,stream_id):
        keep={
          'schema':result.get('schema'),
          'capability_id':result.get('capability_id'),
          'contract_id':result.get('contract_id'),
          'method':result.get('method'),
          'host':result.get('host'),
          'status':result.get('status'),
          'content_type':result.get('content_type'),
          'response_bytes':result.get('response_bytes'),
          'body_sha256':result.get('body_sha256'),
          'execution_digest':result.get('execution_digest'),
          'network_executed':result.get('network_executed'),
          'read_only_enforced':result.get('read_only_enforced'),
          'credentials_used':result.get('credentials_used'),
          'redirects_followed':result.get('redirects_followed'),
        }
        keep['kind']='EXTERNAL_EVIDENCE'
        keep['stream_id']=str(stream_id or '')
        keep['evidence_digest']=_digest_v2(keep)
        return keep

    def _api_execute(self,task):
        ex=G2OpenAPIReadOnlyExecutorV1(
            task['allowed_hosts'],
            max_bytes=int(task.get('max_bytes',1024*1024)),
            timeout=float(task.get('timeout',10.0)),
        )
        result=ex.execute(
            task['plan'],task['base_url'],
            query=task.get('query'),headers=task.get('headers')
        )
        evidence=self._bounded_external_evidence(result,task.get('stream_id',''))
        self._remember(evidence,ablated_memory=bool(task.get('ablated_memory',False)))
        return result,{"operation":"execute_readonly","workspace_memory_recorded":not bool(task.get('ablated_memory',False)),"evidence_digest":evidence['evidence_digest']}

    def execute_capability(self,selected,task,ablated_memory=False):
        cap=str(selected)
        if cap==CAP_API_EXEC_V1:
            t=copy.deepcopy(task)
            t['ablated_memory']=bool(ablated_memory)
            result,meta=self._api_execute(t)
            self._remember({
                'kind':'FABRIC_EPISODE','stream_id':str(task.get('stream_id','')),
                'selected_capability':cap,
                'result':{
                  'status':result.get('status'),'host':result.get('host'),
                  'response_bytes':result.get('response_bytes'),
                  'body_sha256':result.get('body_sha256'),
                  'execution_digest':result.get('execution_digest'),
                },
                'meta':meta,
            },ablated_memory=ablated_memory)
            return {"selected_capability":cap,"result":result,"meta":meta}
        return super().execute_capability(cap,task,ablated_memory=ablated_memory)

    def memory_snapshot(self):
        x=super().memory_snapshot()
        x['external_evidence_count']=sum(1 for e in self.base.episodes if e.get('kind')=='EXTERNAL_EVIDENCE')
        return x

    @classmethod
    def component(cls):
        x={
          'schema':'yado.g2.unified_execution_fabric.v2',
          'component_id':cls.COMPONENT_ID,
          'parent_component':'RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V1',
          'architecture_family':'TYPED_RECURRENT_CAPABILITY_GRAPH',
          'dispatches':sorted(G2UnifiedExecutionFabricV1.LEGACY|{CAP_LOGIC_V2,CAP_THINK_V2,CAP_INTEL_V3,CAP_API_V1,CAP_API_EXEC_V1}),
          'memory_feedback':'STAGE_OUTCOME_TO_AUTO_FEEDBACK_PLAN',
          'external_evidence_memory':'BOUNDED_METADATA_ONLY',
          'bounded_capability_ordering':True,
          'network_execution':{'enabled':True,'read_only_only':True,'methods':['GET','HEAD'],'credentials_allowed':False,'redirects_followed':False},
          'canonical_active':False,
          'architecture_mutation':False,
        }
        x['component_digest']=_digest_v2(x)
        return x

__all__=['G2UnifiedExecutionFabricV2','CAP_API_EXEC_V1']
