from __future__ import annotations
from pathlib import Path
import copy,json

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_g2_unified_execution_fabric_v1 import CAP_LOGIC_V2,CAP_THINK_V2,CAP_INTEL_V3,CAP_API_V1
from yado_g2_unified_execution_fabric_v3 import G2UnifiedExecutionFabricV3
from yado_g2_typed_recurrent_capability_graph_runtime_v1 import G2TypedRecurrentCapabilityGraphRuntimeV1
from yado_g2_openapi_contract_capability_v1 import G2OpenAPIContractCapabilityV1
from yado_g2_openapi_readonly_executor_v1 import G2OpenAPIReadOnlyExecutorV1
from yado_g2_contextual_stream_capability_adapter_v1 import (
    ContextualStreamCapabilityAdapterV1,CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES
)
from yado_bounded_capability_set_coordinator_v1 import BoundedCapabilitySetCoordinatorV1
from yado_neutral_evidence_profile_selector_v1 import NeutralEvidenceProfileSelectorV1,EvidenceCandidate
from yado_g2_canonical_high_scale_binding_runtime_v5 import CanonicalHighScaleBindingRuntimeV5
from yado_evolutionary_genome_v1 import YADOEvolutionaryGenomeV1

CAP_ROUTER='ALG-BOUNDED-CAPABILITY-ROUTER-V1'
CAP_REPAIR='ALG-G2-AMBIGUITY-AWARE-PROGRAM-REPAIR-V11'
CAP_COORD='ALG-G2-BOUNDED-CAPABILITY-SET-COORDINATOR-V1'
CAP_SCI='ALG-G2-BOUNDED-SCIENTIFIC-DATA-REASONER-V1'
CAP_CONTEXT='ALG-G2-CONTEXTUAL-STREAM-CAPABILITY-ADAPTER-V1'
CAP_AUDIT='ALG-G2-DEEP-SELF-AUDIT-V1'
CAP_HS_MODEL='ALG-G2-HIGH-SCALE-TRIPLE-KNN-V4'
CAP_EXPERIENCE='ALG-G2-LEGACY-EXPERIENCE-RETRIEVER-V1'
CAP_RAW='ALG-G2-RAW-TASK-REPRESENTATION-V4'
CAP_SCALE_ROUTE='ALG-G2-SCALE-ROUTE-SEMANTICS-V5'
CAP_SEMANTIC='ALG-G2-SEMANTIC-EXPRESSION-SYNTHESIZER-V1'
CAP_SELECTOR='ALG-NEUTRAL-EVIDENCE-PROFILE-SELECTOR-V1'
CAP_COUNTERMEM='COUNTEREXAMPLE_LINEAGE_MEMORY_V1'
CAP_HS_RUNTIME='RUNTIME-G2-HIGH-SCALE-BINDING-V5'
CAP_BASE_RUNTIME='RUNTIME-G2-TYPED-RECURRENT-CAPABILITY-GRAPH-V1'
CAP_FABRIC='RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V3'
CAP_API=CAP_API_V1
CAP_API_EXEC='ALG-G2-OPENAPI-READONLY-EXECUTOR-V1'
CAP_GENOME='CTRL-G2-EVOLUTIONARY-GENOME-V1'
CAP_COGNITIVE='RUNTIME-G2-EXPERIENCE-CONDITIONED-COGNITIVE-LAYER-V3'

MODULE_REGISTRY={
 CAP_ROUTER:('EXECUTOR','runtime/yado_bounded_capability_router_v1.py'),
 CAP_REL:('EXECUTOR','runtime/yado_bounded_dnf_relation_policy_inducer_v1.py'),
 CAP_BUD:('EXECUTOR','runtime/yado_budgeted_stage_policy_v1.py'),
 CAP_CONJ:('EXECUTOR','runtime/yado_conjunctive_rule_inducer_v1.py'),
 CAP_REPAIR:('EXECUTOR','runtime/yado_ambiguity_aware_program_repair_v11.py'),
 CAP_COORD:('COORDINATOR','runtime/yado_bounded_capability_set_coordinator_v1.py'),
 CAP_SCI:('EXECUTOR','runtime/yado_bounded_scientific_data_reasoner_v1.py'),
 CAP_LOGIC_V2:('EXECUTOR','runtime/yado_budget_adaptive_compositional_logic_v2.py'),
 CAP_CONTEXT:('MEMORY_ADAPTER','runtime/yado_g2_contextual_stream_capability_adapter_v1.py'),
 CAP_INTEL_V3:('EXECUTOR','runtime/yado_coverage_pruned_compositional_schema_router_v3.py'),
 CAP_AUDIT:('CONTROL','runtime/yado_unified_core_deep_self_audit_v1.py'),
 CAP_HS_MODEL:('EMBEDDED_EXECUTOR','runtime/yado_g2_canonical_high_scale_binding_runtime_v5.py'),
 CAP_EXPERIENCE:('MEMORY_RETRIEVER','runtime/yado_legacy_experience_retriever_v2.py'),
 CAP_RAW:('REPRESENTATION','runtime/yado_raw_task_representation_robustness_v4.py'),
 CAP_SCALE_ROUTE:('EMBEDDED_ROUTER','runtime/yado_g2_canonical_high_scale_binding_runtime_v5.py'),
 CAP_SEMANTIC:('EXECUTOR','runtime/yado_semantic_expression_synthesizer_v1.py'),
 CAP_THINK_V2:('EXECUTOR','runtime/yado_work_budget_adaptive_contingent_planner_v2.py'),
 CAP_SELECTOR:('META_SELECTOR','runtime/yado_neutral_evidence_profile_selector_v1.py'),
 CAP_COUNTERMEM:('PERSISTENT_STATE','architecture/evolution-ledger.json'),
 CAP_RES:('RESOURCE_STATE','resources/yado-unified-external-resource-portfolio-v1.json'),
 CAP_HS_RUNTIME:('RUNTIME','runtime/yado_g2_canonical_high_scale_binding_runtime_v5.py'),
 CAP_BASE_RUNTIME:('RUNTIME','runtime/yado_g2_typed_recurrent_capability_graph_runtime_v1.py'),
 CAP_FABRIC:('RUNTIME','runtime/yado_g2_unified_execution_fabric_v3.py'),
 CAP_API:('EXECUTOR','runtime/yado_g2_openapi_contract_capability_v1.py'),
 CAP_API_EXEC:('NETWORK_READONLY_EXECUTOR','runtime/yado_g2_openapi_readonly_executor_v1.py'),
 CAP_GENOME:('EVOLUTION_CONTROL','runtime/yado_evolutionary_genome_v1.py'),
 CAP_COGNITIVE:('COGNITIVE_COORDINATOR','runtime/yado_g2_experience_conditioned_cognitive_layer_v3.py'),
}

DIRECT_FABRIC={CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES,CAP_LOGIC_V2,CAP_THINK_V2,CAP_INTEL_V3}

class _ForcedRouter:
    def __init__(self,cap):self.cap=str(cap);self.fallback_output=self.cap
    def execute(self,descriptor):return self.cap

class UnifiedYADOModuleKernelV1:
    KERNEL_ID='UNIFIED_YADO_MODULE_KERNEL_V1'
    ASSEMBLY_RUNTIME=CAP_FABRIC

    def __init__(self,router_program,scalar_program,relation_program,repo_root:Path|str|None=None):
        self.repo=Path(repo_root) if repo_root else REPO
        self.core=UnifiedYADOCoreV1(self.repo)
        self.base_runtime=G2TypedRecurrentCapabilityGraphRuntimeV1(
            self.core.architecture,router_program,scalar_program,relation_program,self.core.portfolio
        )
        self.fabric=G2UnifiedExecutionFabricV3(self.base_runtime)
        self.context=ContextualStreamCapabilityAdapterV1(self.fabric,'BOUNDED_STREAM_CONTEXT_MAP')
        self.high_scale=CanonicalHighScaleBindingRuntimeV5(repo_root=self.repo)
        self.active=set(self.core.head.get('active_capabilities',[]))

    def registry(self):
        return {
          k:{'kind':v[0],'source':v[1],'canonical_active':k in self.active}
          for k,v in MODULE_REGISTRY.items()
        }

    def _record(self,module_id,result,stream_id=''):
        self.fabric._remember({
          'kind':'MODULE_EPISODE','module_id':str(module_id),
          'stream_id':str(stream_id),'result':copy.deepcopy(result)
        },False)

    def _normalize_fabric_task(self,module_id,task):
        t=copy.deepcopy(task)
        t.setdefault('descriptor',{})
        if module_id==CAP_LOGIC_V2:
            if 'operation' not in t:
                if 'model' not in t and 'train_rows' in t:
                    t['model']=self.core.learn_symmetric_logic(t['train_rows'])
                t['operation']='predict_symmetric'
        elif module_id==CAP_THINK_V2:
            t.setdefault('operation','plan')
        elif module_id==CAP_INTEL_V3:
            if 'model' not in t and 'train_cases' in t:
                t['model']=self.core.fit_compositional_capability_router(t['train_cases'],t.get('fallback_output',CAP_LOGIC_V2))
            t.setdefault('operation','route')
        return t

    def _force_fabric(self,module_id,task):
        old=self.fabric.router
        try:
            self.fabric.router=_ForcedRouter(module_id)
            return self.fabric.run(self._normalize_fabric_task(module_id,task))
        finally:
            self.fabric.router=old

    def execute(self,module_id,task):
        mid=str(module_id);task=copy.deepcopy(task)
        if mid not in MODULE_REGISTRY:raise KeyError('MODULE_NOT_REGISTERED:'+mid)

        if mid in DIRECT_FABRIC:
            return self._force_fabric(mid,task)

        if mid==CAP_ROUTER:
            out={'selected_capability':self.fabric.router.execute(task.get('descriptor',{}))}
        elif mid==CAP_REPAIR:
            action=task.get('action','repair')
            if action=='repair':
                out=self.core.repair_program(task['source'],task['function_name'],task['train_examples'],max_candidates=int(task.get('max_candidates',10000)))
            elif action=='execute':
                out={'result':self.core.execute_program_task(task['source'],task['function_name'],tuple(task.get('args',())))}
            else:raise ValueError('UNKNOWN_REPAIR_ACTION:'+str(action))
        elif mid==CAP_COORD:
            normalized={cap:self._normalize_fabric_task(cap,t) for cap,t in task['capability_tasks'].items()}
            out=self.fabric.run_capability_set(task['selected_capabilities'],normalized)
        elif mid==CAP_SCI:
            action=task.get('action','analyze')
            if action=='analyze':out=self.core.analyze_science_data(task['rows'],enable=tuple(task.get('enable',('summary','correlation','group','linear'))))
            elif action=='hypothesis':out=self.core.test_scientific_hypothesis(task['rows'],task['spec'])
            else:raise ValueError('UNKNOWN_SCIENCE_ACTION:'+str(action))
        elif mid==CAP_CONTEXT:
            return self.context.run(task,ablated_context=bool(task.pop('ablated_context',False)))
        elif mid==CAP_AUDIT:
            out={'control_runtime':'runtime/yado_unified_core_deep_self_audit_v1.py','core_audit':self.core.audit()}
        elif mid==CAP_HS_MODEL:
            out={'route':self.high_scale.route(task['case']),'prediction':self.high_scale.predict(task['case'])}
        elif mid==CAP_EXPERIENCE:
            action=task.get('action','search_registry')
            if action=='search_registry':out={'matches':self.core.experience_search(task.get('tags',[]),limit=int(task.get('limit',8)))}
            elif action=='search_verified':out={'matches':self.core.experience_search_verified(task['query'],limit=int(task.get('limit',8)))}
            elif action=='read_exact':out=self.core.experience_read_exact(task['branch'],task['path'])
            else:raise ValueError('UNKNOWN_EXPERIENCE_ACTION:'+str(action))
        elif mid==CAP_RAW:
            out=self.core.represent_raw_task(task['raw_text'])
        elif mid==CAP_SCALE_ROUTE:
            out={'route':self.high_scale.route(task['case']),'cardinality':self.high_scale.cardinality(task['case'])}
        elif mid==CAP_SEMANTIC:
            action=task.get('action','synthesize')
            if action=='synthesize':out=self.core.synthesize_mathematical_expression(task['train_rows'],max_ops=int(task.get('max_ops',3)),max_states_per_level=int(task.get('max_states_per_level',30000)))
            elif action=='predict':out={'result':self.core.predict_mathematical_expression(task['model'],task['x'],task['y'])}
            else:raise ValueError('UNKNOWN_SEMANTIC_ACTION:'+str(action))
        elif mid==CAP_SELECTOR:
            candidates=[EvidenceCandidate(
                token=str(x['token']),evidence=float(x['evidence']),complexity=float(x.get('complexity',0)),
                risk=float(x.get('risk',0)),novelty=float(x.get('novelty',0))
            ) for x in task['candidates']]
            out=NeutralEvidenceProfileSelectorV1.select(candidates)
        elif mid==CAP_COUNTERMEM:
            limit=max(1,min(64,int(task.get('limit',12))))
            xs=self.core.ledger.get('events',[])
            if task.get('nonpass_only',True):
                xs=[x for x in xs if str(x.get('status','')).upper() not in {'PASS','PASS_CANONICAL'}]
            out={'event_count':len(xs),'events':copy.deepcopy(xs[-limit:])}
        elif mid==CAP_HS_RUNTIME:
            out=self.high_scale.snapshot()
        elif mid==CAP_BASE_RUNTIME:
            out=self.fabric.memory_snapshot()
        elif mid==CAP_FABRIC:
            out={'component_id':CAP_FABRIC,'memory':self.fabric.memory_snapshot(),'canonical_active':CAP_FABRIC in self.active}
        elif mid==CAP_API:
            api=G2OpenAPIContractCapabilityV1(task.get('state_section',{}))
            action=task.get('action','compile_plan')
            if action=='compile_plan':out=api.compile_plan(str(task['contract_id']))
            elif action=='classify':out=api.classify(str(task['contract_id']))
            else:raise ValueError('UNKNOWN_API_ACTION:'+str(action))
        elif mid==CAP_API_EXEC:
            action=task.get('action','component')
            if action=='component':
                out=G2OpenAPIReadOnlyExecutorV1.component()
            elif action=='execute':
                ex=G2OpenAPIReadOnlyExecutorV1(task['allowed_hosts'],max_bytes=int(task.get('max_bytes',1024*1024)),timeout=float(task.get('timeout',10)))
                out=ex.execute(task['plan'],task['base_url'],query=task.get('query'),headers=task.get('headers'))
            else:raise ValueError('UNKNOWN_API_EXEC_ACTION:'+str(action))
        elif mid==CAP_COGNITIVE:
            action=task.get('action','decide')
            if action=='decide':
                out=self.core.cognitive_experience_decide(task['organ'],task.get('payload',{}))
            elif action=='snapshot':
                out=self.core.cognitive_experience_snapshot()
            else:
                raise ValueError('UNKNOWN_COGNITIVE_ACTION:'+str(action))
        elif mid==CAP_GENOME:
            action=task.get('action','component')
            if action=='component':
                out=YADOEvolutionaryGenomeV1.component()
            elif action=='evolve_once':
                if not hasattr(self.core,'evolve_cognitive_code_genome'):
                    raise RuntimeError('EVOLUTIONARY_GENOME_NOT_BOUND_TO_CORE')
                out=self.core.evolve_cognitive_code_genome()
            else:raise ValueError('UNKNOWN_GENOME_ACTION:'+str(action))
        else:
            raise KeyError('NO_EXECUTION_PATH:'+mid)

        self._record(mid,out,task.get('stream_id',''))
        return out

    def snapshot(self):
        reg=self.registry();active=set(self.active);registered=set(reg)
        return {
          'schema':'yado.g2.unified_module_kernel.snapshot.v1',
          'kernel_id':self.KERNEL_ID,
          'generation':self.core.head.get('generation_id'),
          'frontier':self.core.head.get('current_frontier'),
          'assembly_runtime':self.ASSEMBLY_RUNTIME,
          'assembly_runtime_canonical_active':self.ASSEMBLY_RUNTIME in active,
          'active_module_count':len(active),
          'registered_module_count':len(registered),
          'missing_active_modules':sorted(active-registered),
          'extra_registry_modules':sorted(registered-active),
          'registry':reg,
          'memory':self.fabric.memory_snapshot(),
          'semantic_boundary':'SHADOW MODULE-ASSEMBLY AUDIT OVER THE CANONICAL G2 UNIFIED EXECUTION FABRIC. THE ASSEMBLY KERNEL ITSELF IS NOT A NEW GENERATION OR CONSCIOUSNESS CLAIM.'
        }

__all__=['UnifiedYADOModuleKernelV1','MODULE_REGISTRY']+[k for k in globals() if k.startswith('CAP_')]
