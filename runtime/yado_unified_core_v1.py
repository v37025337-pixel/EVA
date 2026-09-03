from __future__ import annotations
from pathlib import Path
from typing import Any, Iterable
import copy,hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(PKG))

from yado_evolution_ledger_v2 import validate_ledger_v2
from yado_g2_typed_recurrent_capability_graph_runtime_v1 import G2TypedRecurrentCapabilityGraphRuntimeV1
from yado_g2_contextual_stream_capability_adapter_v1 import ContextualStreamCapabilityAdapterV1
from yado_raw_task_representation_robustness_v4 import RobustRawTaskRepresentationRuntimeV4
from yado_legacy_experience_retriever_v2 import LegacyExperienceRetrieverV1
from yado_semantic_expression_synthesizer_v1 import SemanticExpressionSynthesizerV1
from yado_ambiguity_aware_program_repair_v11 import AmbiguityAwareProgramRepairV11
from yado_bounded_scientific_data_reasoner_v1 import BoundedScientificDataReasonerV1
from yado_work_budget_adaptive_contingent_planner_v2 import WorkBudgetAdaptiveContingentPlannerV2, ContingentStage
from yado_budget_adaptive_compositional_logic_v2 import BudgetAdaptiveCompositionalLogicV2
from yado_coverage_pruned_compositional_schema_router_v3 import CoveragePrunedCompositionalSchemaRouterV3
from yado_bounded_capability_set_coordinator_v1 import BoundedCapabilitySetCoordinatorV1
from yado_g2_unified_execution_fabric_v1 import G2UnifiedExecutionFabricV1
from yado_g2_unified_execution_fabric_v2 import G2UnifiedExecutionFabricV2
from yado_g2_unified_execution_fabric_v3 import G2UnifiedExecutionFabricV3
from yado_g2_openapi_contract_capability_v1 import G2OpenAPIContractCapabilityV1
from yado_g2_openapi_readonly_executor_v1 import G2OpenAPIReadOnlyExecutorV1
from yado_evolutionary_genome_v1 import YADOEvolutionaryGenomeV1

def canon(o:Any)->str:
    return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o:Any)->str:
    return hashlib.sha256(canon(o).encode()).hexdigest()

class UnifiedYADOCoreV1:
    """Single entry point over the current G2 runtime plus read-only legacy experience.

    Important: legacy branches are knowledge/evidence sources only. This class never
    imports code from legacy Git branches. Re-admission requires a separate fresh gate.
    """
    CORE_ID='UNIFIED_YADO_CORE_V1'

    def __init__(self,repo_root:Path|str|None=None):
        self.repo=Path(repo_root) if repo_root else REPO
        self.head=self._load('canonical/yado-main-head-g2.json')
        self.architecture=self._load('canonical/yado-g2-architecture-v1.json')
        self.ledger=self._load('architecture/evolution-ledger.json')
        self.portfolio=self._load('resources/yado-unified-external-resource-portfolio-v1.json')
        self.manifest=self._load('canonical/yado-unified-core-v1.json')
        self.experience=self._load('canonical/yado-unified-experience-registry-v1.json')
        self.shadow_context=self._load('candidates/g2-development/contextual-stream-capability-adapter-v1.json')
        self.raw_representation=RobustRawTaskRepresentationRuntimeV4(self._load('canonical/yado-raw-task-representation-v3.json'), self._load('canonical/yado-raw-task-representation-v4.json')['selected_mode'])
        self.legacy_experience_retriever=LegacyExperienceRetrieverV1(self.repo,self.experience)
        self.semantic_expression_synthesizer=SemanticExpressionSynthesizerV1
        self.bounded_program_repair=AmbiguityAwareProgramRepairV11
        self.scientific_data_reasoner=BoundedScientificDataReasonerV1
        self.adaptive_contingent_planner=WorkBudgetAdaptiveContingentPlannerV2
        self.compositional_logic=BudgetAdaptiveCompositionalLogicV2
        self.compositional_schema_router=CoveragePrunedCompositionalSchemaRouterV3
        self.capability_set_coordinator=BoundedCapabilitySetCoordinatorV1
        self.execution_fabric_cls=G2UnifiedExecutionFabricV3
        self.openapi_contract_capability_cls=G2OpenAPIContractCapabilityV1
        self.openapi_readonly_executor_cls=G2OpenAPIReadOnlyExecutorV1
        self.evolutionary_genome_cls=YADOEvolutionaryGenomeV1
        validate_ledger_v2(self.ledger)

    def _load(self,rel:str)->dict[str,Any]:
        return json.loads((self.repo/rel).read_text(encoding='utf-8'))

    def audit(self)->dict[str,Any]:
        branches=self.experience.get('branches',[])
        open_deficits=self.ledger.get('open_deficits',[])
        ledger_frontier=open_deficits[0] if len(open_deficits)==1 else None
        active=[x for x in branches if x.get('mode')=='ACTIVE_LINEAGE']
        legacy=[x for x in branches if x.get('mode')=='EXPERIENCE_ONLY']
        active_components=set()
        for p in self.manifest.get('planes',[]):
            active_components.update(p.get('active_components',[]))
        checks={
            'core_id':self.manifest.get('core_id')==self.CORE_ID,
            'generation_is_g2':self.head.get('generation_id')=='G2_CANDIDATE_TRCG_V1',
            'one_active_experience_lineage':len(active)==1 and active[0].get('branch')=='yado-architecture-shadow-search',
            'all_other_branches_experience_only':len(legacy)==13 and all(x.get('mode')=='EXPERIENCE_ONLY' for x in legacy),
            'branch_inventory_complete':len(branches)==14,
            'legacy_auto_execution_forbidden':self.experience.get('policy',{}).get('legacy_code_import_forbidden_without_fresh_admission_gate') is True,
            'ledger_head_matches_generation':self.ledger.get('current_head')==self.head.get('generation_id'),
            'ledger_head_digest_matches':self.ledger.get('current_head_digest')==self.head.get('canonical_head_digest'),
            'g2_architecture_canonical':self.architecture.get('canonical_active') is True and self.architecture.get('promotion_applied') is True,
            'experience_registry_bound':self.manifest.get('experience_registry')=='canonical/yado-unified-experience-registry-v1.json',
            'developmental_frontier_coherent':bool(ledger_frontier) and self.manifest.get('current_frontier')==ledger_frontier and self.head.get('current_frontier')==ledger_frontier,
            'g3_blocked':self.manifest.get('g3_genesis_performed') is False and self.experience.get('policy',{}).get('g3_genesis_blocked') is True,
            'context_adapter_binding_coherent':(('ALG-G2-CONTEXTUAL-STREAM-CAPABILITY-ADAPTER-V1' in active_components)==(self.shadow_context.get('canonical_active') is True)),
            'required_active_families_present':all(x in active_components for x in [
                'ALG-CONJUNCTIVE-RULE-INDUCER-V1',
                'ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1',
                'ALG-BUDGETED-STAGE-POLICY-V1',
                'ALG-BOUNDED-CAPABILITY-ROUTER-V1',
                'ALG-NEUTRAL-EVIDENCE-PROFILE-SELECTOR-V1',
                'RESOURCE-PORTFOLIO-V1',
                'RUNTIME-G2-TYPED-RECURRENT-CAPABILITY-GRAPH-V1',
            ]),
        }
        return {
            'core_id':self.CORE_ID,
            'generation':self.head.get('generation_id'),
            'branch_count':len(branches),
            'legacy_experience_count':len(legacy),
            'checks':checks,
            'pass':all(checks.values()),
            'current_frontier':ledger_frontier,
            'frontier_source':'architecture/evolution-ledger.json:open_deficits',
            'manifest_frontier_snapshot':self.manifest.get('current_frontier'),
            'head_frontier_snapshot':self.head.get('current_frontier'),
            'open_deficits':copy.deepcopy(open_deficits),
        }

    def experience_search(self,tags:Iterable[str],limit:int=8)->list[dict[str,Any]]:
        wanted={str(x).strip().lower() for x in tags if str(x).strip()}
        rows=[]
        for entry in self.experience.get('branches',[]):
            if entry.get('mode')!='EXPERIENCE_ONLY':
                continue
            hay={str(x).lower() for x in entry.get('tags',[])}
            lessons=' '.join(entry.get('lessons',[])).lower()
            score=len(wanted & hay)
            score+=sum(1 for w in wanted if w and w in lessons)
            if score:
                rows.append({
                    'branch':entry.get('branch'),
                    'role':entry.get('role'),
                    'score':score,
                    'tags':entry.get('tags',[]),
                    'lessons':entry.get('lessons',[]),
                    'lesson_provenance':entry.get('lesson_provenance'),
                    'rederived_evidence':entry.get('rederived_evidence'),
                    'evidence':entry.get('evidence',[]),
                    'claim_boundary':entry.get('claim_boundary'),
                })
        rows.sort(key=lambda x:(-x['score'],x['branch']))
        return rows[:max(1,int(limit))]

    def developmental_frontier(self)->dict[str,Any]:
        open_deficits=copy.deepcopy(self.ledger.get('open_deficits',[]))
        return {
            'generation':self.head.get('generation_id'),
            'current_frontier':open_deficits[0] if len(open_deficits)==1 else None,
            'frontier_source':'architecture/evolution-ledger.json:open_deficits',
            'open_deficits':open_deficits,
            'manifest_frontier_snapshot':self.manifest.get('current_frontier'),
            'recommended_experience':self.experience_search(
                ['representation','grounding','workspace','attention','thinking','self_audit'],limit=6
            ),
        }

    def experience_read_exact(self,branch:str,path:str)->dict[str,Any]:
        return self.legacy_experience_retriever.read_registered(branch,path)

    def experience_search_verified(self,query:str,limit:int=8)->list[dict[str,Any]]:
        return self.legacy_experience_retriever.search_content(query,limit=limit)

    def analyze_science_data(self,rows:list[dict[str,Any]],enable:tuple[str,...]=('summary','correlation','group','linear'))->dict[str,Any]:
        return self.scientific_data_reasoner.analyze(rows,enable=enable)

    def test_scientific_hypothesis(self,rows:list[dict[str,Any]],spec:dict[str,Any])->dict[str,Any]:
        return self.scientific_data_reasoner.evaluate_hypothesis(rows,spec)

    @staticmethod
    def _contingent_stage_from_dict(x:dict[str,Any])->ContingentStage:
        return ContingentStage(
            str(x["stage_id"]),float(x["cost"]),float(x["expected_gain"]),int(x.get("quota_remaining",1)),
            bool(x.get("available",True)),float(x.get("latency",1.0)),bool(x.get("attempted",False)),
            tuple(str(z) for z in x.get("requires",()))
        )

    def execute_capability_set(self,runtime,selected_capabilities,capability_tasks):
        if isinstance(runtime,G2UnifiedExecutionFabricV1):
            return runtime.run_capability_set(selected_capabilities,capability_tasks)
        fabric=self.execution_fabric_cls(runtime)
        return fabric.run_capability_set(selected_capabilities,capability_tasks)

    def fit_compositional_capability_router(self,cases:list[dict[str,Any]],fallback_output:str)->dict[str,Any]:
        return self.compositional_schema_router.fit(cases,fallback_output)

    def route_capability_set(self,model:dict[str,Any],descriptor:dict[str,Any]):
        return self.compositional_schema_router.route(model,descriptor)

    def fit_capability_schema_alignment(self,reference_rows:list[dict[str,Any]],alias_rows:list[dict[str,Any]])->dict[str,Any]:
        return self.compositional_schema_router.fit_schema_alignment(reference_rows,alias_rows)

    def route_aligned_capability_set(self,model:dict[str,Any],alignment:dict[str,Any],descriptor:dict[str,Any]):
        return self.compositional_schema_router.route_aligned(model,alignment,descriptor)

    def learn_symmetric_logic(self,rows:list[dict[str,Any]])->dict[str,Any]:
        return self.compositional_logic.learn_symmetric_boolean(rows)

    def predict_symmetric_logic(self,model:dict[str,Any],x:dict[str,Any])->Any:
        return self.compositional_logic.predict_symmetric_boolean(model,x)

    def fit_polynomial_logic(self,rows:list[dict[str,Any]],max_degree:int=8)->dict[str,Any]:
        return self.compositional_logic.fit_polynomial(rows,max_degree=max_degree)

    def predict_polynomial_logic(self,model:dict[str,Any],x:float,y:float)->Any:
        return self.compositional_logic.predict_polynomial(model,x,y)

    def plan_contingent(self,current_confidence:float,target_confidence:float,remaining_budget:float,stages:list[dict[str,Any]],completed=()):
        xs=[self._contingent_stage_from_dict(x) for x in stages]
        return self.adaptive_contingent_planner.plan(current_confidence,target_confidence,remaining_budget,xs,completed=completed)

    def update_contingent_plan(self,current_confidence:float,target_confidence:float,remaining_budget:float,stages:list[dict[str,Any]],completed_stage_id:str,observed_gain:float,completed=()):
        xs=[self._contingent_stage_from_dict(x) for x in stages]
        return self.adaptive_contingent_planner.next_after_observation(
            current_confidence,target_confidence,remaining_budget,xs,completed_stage_id,observed_gain,completed=completed
        )

    def repair_program(self,source:str,function_name:str,train_examples:list[tuple[tuple[Any,...],Any]],max_candidates:int=10000)->dict[str,Any]:
        return self.bounded_program_repair.repair(source,function_name,train_examples,max_candidates=max_candidates)

    def execute_program_task(self,source:str,function_name:str,args:tuple[Any,...])->Any:
        return self.bounded_program_repair.execute(source,function_name,args)

    def synthesize_mathematical_expression(self,train_rows:list[dict[str,Any]],max_ops:int=3,max_states_per_level:int=30000)->dict[str,Any]:
        return self.semantic_expression_synthesizer.synthesize(train_rows,max_ops=max_ops,max_states_per_level=max_states_per_level)

    def predict_mathematical_expression(self,result:dict[str,Any],x:float,y:float)->Any:
        return self.semantic_expression_synthesizer.predict(result,x,y)

    def represent_raw_task(self,raw_text:str)->dict[str,Any]:
        return self.raw_representation.descriptor(raw_text)

    def route_raw_task(self,raw_text:str,router_program)->dict[str,Any]:
        rep=self.represent_raw_task(raw_text)
        selected=router_program.execute(rep['routing_descriptor'])
        return {'representation':rep,'selected_capability':selected}

    def instantiate_runtime(self,router_program,scalar_program,relation_program,enable_shadow_context:bool=True):
        runtime=G2TypedRecurrentCapabilityGraphRuntimeV1(
            self.architecture,router_program,scalar_program,relation_program,self.portfolio
        )
        if enable_shadow_context:
            return ContextualStreamCapabilityAdapterV1(runtime,'BOUNDED_STREAM_CONTEXT_MAP')
        return runtime

    def instantiate_execution_fabric(self,router_program,scalar_program,relation_program,api_state=None,temporal_state=None):
        base=G2TypedRecurrentCapabilityGraphRuntimeV1(
            self.architecture,router_program,scalar_program,relation_program,self.portfolio
        )
        return self.execution_fabric_cls(base,api_state=api_state,temporal_state=temporal_state)

    def compile_openapi_contract_plan(self,state_section:dict[str,Any],contract_id:str)->dict[str,Any]:
        return self.openapi_contract_capability_cls(state_section).compile_plan(contract_id)

    def execute_openapi_readonly_plan(self,plan:dict[str,Any],base_url:str,allowed_hosts:list[str],query=None,headers=None,max_bytes:int=1048576,timeout:float=10.0)->dict[str,Any]:
        executor=self.openapi_readonly_executor_cls(allowed_hosts,max_bytes=max_bytes,timeout=timeout)
        return executor.execute(plan,base_url,query=query,headers=headers)

    def execute_openapi_readonly_via_fabric(self,execution_fabric,plan:dict[str,Any],base_url:str,allowed_hosts:list[str],query=None,headers=None,max_bytes:int=1048576,timeout:float=10.0,stream_id:str='OPENAPI')->dict[str,Any]:
        if not hasattr(execution_fabric,'execute_capability'):
            raise TypeError('EXECUTION_FABRIC_REQUIRED')
        return execution_fabric.execute_capability(
            'ALG-G2-OPENAPI-READONLY-EXECUTOR-V1',
            {
              'plan':plan,'base_url':base_url,'allowed_hosts':allowed_hosts,
              'query':query,'headers':headers,'max_bytes':max_bytes,'timeout':timeout,
              'stream_id':stream_id,
            }
        )

    def evolutionary_parent_genome(self)->dict[str,Any]:
        component_sources={
          'LOGIC':'runtime/yado_budget_adaptive_compositional_logic_v2.py',
          'THINKING':'runtime/yado_work_budget_adaptive_contingent_planner_v2.py',
          'INTELLIGENCE':'runtime/yado_coverage_pruned_compositional_schema_router_v3.py',
          'CODE':'runtime/yado_ambiguity_aware_program_repair_v11.py',
        }
        component_digests={k:hashlib.sha256((self.repo/v).read_bytes()).hexdigest() for k,v in component_sources.items()}
        experience=self.experience_search(['logic','thinking','intelligence','repair','counterexample'],limit=8)
        parent=self.evolutionary_genome_cls.parent_genome(
            self.head['canonical_head_digest'],component_digests,experience_digest=digest(experience)
        )
        return {'parent':parent,'experience':experience}

    def evolve_cognitive_code_genome(self)->dict[str,Any]:
        state=self.evolutionary_parent_genome()
        controller=self.evolutionary_genome_cls(state['parent'],experience_sources=state['experience'])
        return controller.evolve_once()

    def export_cognitive_temporal_state(self,execution_fabric)->dict[str,Any]:
        if not hasattr(execution_fabric,'export_temporal_state'):
            raise TypeError('TEMPORAL_EXECUTION_FABRIC_REQUIRED')
        return execution_fabric.export_temporal_state()

    def temporal_evolution_on_stall(self,execution_fabric,stream_id:str)->dict[str,Any]:
        if not hasattr(execution_fabric,'temporal_evolution_signal'):
            raise TypeError('TEMPORAL_EXECUTION_FABRIC_REQUIRED')
        signal=execution_fabric.temporal_evolution_signal(stream_id)
        if not signal.get('mechanism_change_required'):
            return {'status':'CONTINUE_CURRENT_MECHANISM','temporal_signal':signal,'promotion_authorized':False}
        evolution=self.evolve_cognitive_code_genome()
        return {
          'status':'SHADOW_EVOLUTION_TRIGGERED',
          'temporal_signal':signal,
          'evolution':evolution,
          'promotion_authorized':False,
          'semantic_boundary':'TEMPORAL STALL MAY TRIGGER SHADOW GENOME EVOLUTION BUT CANNOT PROMOTE THE CHILD.'
        }

    def snapshot(self)->dict[str,Any]:
        audit=self.audit()
        return {
            'schema':'yado.unified_core.snapshot.v1',
            'core_id':self.CORE_ID,
            'generation':self.head.get('generation_id'),
            'head_digest':self.head.get('canonical_head_digest'),
            'architecture_id':self.head.get('architecture_id'),
            'experience_registry_digest':digest(self.experience),
            'manifest_digest':digest(self.manifest),
            'audit':audit,
            'frontier':self.developmental_frontier(),
            'semantic_boundary':'ONE ACTIVE YADO SOFTWARE KERNEL WITH LEGACY BRANCHES AS READ-ONLY EXPERIENCE; NOT AGI OR SUBJECTIVE CONSCIOUSNESS.'
        }

__all__=['UnifiedYADOCoreV1','digest']
