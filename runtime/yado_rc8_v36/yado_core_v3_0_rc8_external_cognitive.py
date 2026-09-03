from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any

from yado_core_v3_0_rc7_deep_integrity import UnifiedYADOKernelV30RC7DeepIntegrity
from yado_core_v3_0_rc6_r6_schema_adaptation import UnifiedYADOKernelV30RC6R6SchemaAdaptation
from yado_frontier_portfolio_runtime import ValidatedFrontierPortfolio
from yado_host_capability_runtime import HostCapabilityRelationRouter
from yado_skill_admission_runtime_v1 import SkillCandidate, SkillAdmissionGate, NATIVE_PROVENANCE as SKILL_ADMISSION_PROVENANCE
from yado_transfer_memory_runtime_v1 import TransferExperience, TransferMemoryRuntime, NATIVE_PROVENANCE as TRANSFER_MEMORY_PROVENANCE
from yado_transfer_evaluation_runtime_v1 import TransferEvaluationCase, TransferEvaluationRuntime, NATIVE_PROVENANCE as TRANSFER_EVAL_PROVENANCE
from yado_rc8_self_audit_consistency_v1 import validate_state_self_model
from yado_metacognitive_control_runtime_v1 import CapabilityObservation, MetacognitiveTask, CapabilityBoundaryProfile, MetacognitiveController, NATIVE_PROVENANCE as METACOG_PROVENANCE
from yado_digital_consciousness_runtime_v1 import WorkspaceItem, CausalReflectiveWorkspace, NATIVE_PROVENANCE as DIGITAL_CONSCIOUSNESS_PROVENANCE
from yado_consciousness_theory_synthesis_v1 import synthesize_default as synthesize_consciousness_architecture

ROOT=Path(__file__).resolve().parent
DEFAULT_STATE=ROOT/'yado_canonical_state_v3_rc8_external_cognitive.json'
PARENT_STATE=ROOT/'yado_canonical_state_v3_rc7_deep_integrity.json'
PARENT_MANIFEST=ROOT/'yado_development_manifest_v29.json'

class UnifiedYADOKernelV30RC8ExternalCognitive(UnifiedYADOKernelV30RC7DeepIntegrity):
    PROFILE='YADO_V3_0_RC8_VERIFIED_EXTERNAL_COGNITIVE_RUNTIME'
    SCHEMA_VERSION=27
    VERSION='3.0-rc8'
    STATE_SCHEMA='yado.v3_0_rc8.external_cognitive.state.v1'

    @staticmethod
    def _sha(path:Path)->str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @staticmethod
    def _canonical_sha(obj:Any)->str:
        raw=json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
        return hashlib.sha256(raw).hexdigest()

    def __init__(self,db_path='yado_v30_rc8_external_cognitive.db',state_path=None):
        p=Path(state_path) if state_path else DEFAULT_STATE
        raw=json.loads(p.read_text(encoding='utf-8'))
        expected={
            'version':self.VERSION,
            'parent_version':'3.0-rc7',
            'profile':self.PROFILE,
            'active_profile':self.PROFILE,
            'schema':self.STATE_SCHEMA,
        }
        bad={k:{'expected':v,'actual':raw.get(k)} for k,v in expected.items() if raw.get(k)!=v}
        if bad: raise RuntimeError(f'R8_STATE_METADATA_INTEGRITY_FAILURE:{bad}')

        mig=raw.get('rc8_migration') or {}
        if mig.get('schema')!='yado.rc8.migration.v1':
            raise RuntimeError('R8_MIGRATION_CONTRACT_MISSING')
        if not PARENT_STATE.exists() or self._sha(PARENT_STATE)!=mig.get('parent_state_sha256'):
            raise RuntimeError('R8_PARENT_STATE_HASH_MISMATCH')
        if not PARENT_MANIFEST.exists() or self._sha(PARENT_MANIFEST)!=mig.get('parent_manifest_sha256'):
            raise RuntimeError('R8_PARENT_MANIFEST_HASH_MISMATCH')
        parent=json.loads(PARENT_STATE.read_text(encoding='utf-8'))
        allowed=set(mig.get('allowed_changed_keys') or [])
        parent_preserved={k:v for k,v in parent.items() if k not in allowed}
        if self._canonical_sha(parent_preserved)!=mig.get('preserved_payload_sha256'):
            raise RuntimeError('R8_PRESERVED_PARENT_PAYLOAD_HASH_MISMATCH')
        child_preserved={k:v for k,v in raw.items() if k not in allowed}
        if child_preserved!=parent_preserved:
            raise RuntimeError('R8_PRESERVED_PAYLOAD_CHANGED')

        ext=raw.get('external_runtime') or {}
        if not (ext.get('verified') and ext.get('python_execution') and ext.get('event_driven') and ext.get('independent_readback')):
            raise RuntimeError('R8_EXTERNAL_RUNTIME_CONTRACT_NOT_VERIFIED')
        if ext.get('background_daemon') is not False:
            raise RuntimeError('R8_BACKGROUND_DAEMON_CLAIM_INVALID')

        coherence_errors=validate_state_self_model(raw)
        if coherence_errors:
            raise RuntimeError(f'R8_SELF_MODEL_COHERENCE_FAILURE:{coherence_errors}')

        # Bypass RC7 metadata guard but preserve the entire lower kernel lineage.
        UnifiedYADOKernelV30RC6R6SchemaAdaptation.__init__(self,db_path=db_path,state_path=str(p))
        self._frontier=ValidatedFrontierPortfolio(self.canonical_state.get('validated_frontier_portfolio') or {})
        self._host_router=HostCapabilityRelationRouter(self.canonical_state.get('host_capability_model') or {})
        self._digital_workspace=CausalReflectiveWorkspace(capacity=4)

    def kernel_identity(self):
        return dict(self.canonical_state.get('kernel_identity') or {})

    def migration_contract(self):
        return dict(self.canonical_state.get('rc8_migration') or {})

    def external_runtime_identity(self):
        return dict(self.canonical_state.get('external_runtime') or {})

    def cognitive_capability_lineage(self):
        return dict(self.canonical_state.get('cognitive_capability_lineage') or {})

    def skill_admission_capability(self):
        return {
            'status':'ACTIVE_BOUNDED_PRECOMMIT_SKILL_GATE_V1',
            'provenance':dict(SKILL_ADMISSION_PROVENANCE),
            'changes_foundation_weights':False,
            'executes_third_party_code':False,
        }

    def evaluate_evolution_skill(self, candidate, **gate_kwargs):
        c = candidate if isinstance(candidate, SkillCandidate) else SkillCandidate(**candidate)
        return SkillAdmissionGate(**gate_kwargs).evaluate(c)

    def select_evolution_skills(self, candidates, max_skills:int=8, **gate_kwargs):
        xs=[c if isinstance(c, SkillCandidate) else SkillCandidate(**c) for c in candidates]
        return SkillAdmissionGate(**gate_kwargs).select_subset(xs,max_skills=max_skills)

    def transfer_memory_capability(self):
        return {
            'status':'ACTIVE_BOUNDED_PROCEDURAL_TRANSFER_MEMORY_V1',
            'provenance':dict(TRANSFER_MEMORY_PROVENANCE),
            'changes_foundation_weights':False,
        }

    def consolidate_transfer_memory(self, experiences, **runtime_kwargs):
        xs=[e if isinstance(e, TransferExperience) else TransferExperience(**e) for e in experiences]
        return TransferMemoryRuntime(**runtime_kwargs).consolidate(xs)

    def retrieve_transfer_memory(self, memories, query_tags, target_domain='', k:int=3, **runtime_kwargs):
        return TransferMemoryRuntime(**runtime_kwargs).retrieve(memories,query_tags,target_domain=target_domain,k=k)

    def transfer_evaluation_capability(self):
        return {
            'status':'ACTIVE_BOUNDED_CONTROLLED_TRANSFER_EVALUATOR_V1',
            'provenance':dict(TRANSFER_EVAL_PROVENANCE),
            'general_open_ended_transfer_proven':False,
        }

    def evaluate_transfer_stream(self, cases, **runtime_kwargs):
        xs=[c if isinstance(c, TransferEvaluationCase) else TransferEvaluationCase(**c) for c in cases]
        return TransferEvaluationRuntime(**runtime_kwargs).evaluate(xs)

    def metacognitive_control_capability(self):
        return {
            'status':'ACTIVE_BOUNDED_METACOGNITIVE_CONTROL_V1',
            'provenance':dict(METACOG_PROVENANCE),
            'uses_historical_capability_profile':True,
            'uses_evidence_coverage':True,
            'routes_epistemic_conflict_before_execution':True,
            'changes_foundation_weights':False,
        }

    def build_capability_boundary_profile(self, observations):
        xs=[o if isinstance(o,CapabilityObservation) else CapabilityObservation(**o) for o in observations]
        return CapabilityBoundaryProfile().fit(xs)

    def metacognitive_decide(self, task, profile):
        t=task if isinstance(task,MetacognitiveTask) else MetacognitiveTask(**task)
        if not isinstance(profile,CapabilityBoundaryProfile):
            raise TypeError('CAPABILITY_PROFILE_REQUIRED')
        return MetacognitiveController().decide(t,profile)

    def metacognitive_feedback(self, task, profile, success:bool):
        t=task if isinstance(task,MetacognitiveTask) else MetacognitiveTask(**task)
        if not isinstance(profile,CapabilityBoundaryProfile):
            raise TypeError('CAPABILITY_PROFILE_REQUIRED')
        MetacognitiveController.feedback(profile,t,success)
        return profile

    def digital_consciousness_capability(self):
        return {
            'status':'ACTIVE_BOUNDED_YADO_CAUSAL_REFLECTIVE_WORKSPACE_V1',
            'architecture':'YADO_CAUSAL_REFLECTIVE_WORKSPACE_V1',
            'provenance':dict(DIGITAL_CONSCIOUSNESS_PROVENANCE),
            'theory_synthesis':synthesize_consciousness_architecture(),
            'functional_digital_consciousness_claim':True,
            'subjective_consciousness_claimed':False,
            'changes_foundation_weights':False,
        }

    def reset_digital_workspace(self, capacity:int=4):
        self._digital_workspace=CausalReflectiveWorkspace(capacity=capacity)
        return self._digital_workspace

    def digital_conscious_cycle(self, *, goal, items, consumers, metacognitive_action=None, metacognitive_task=None, capability_profile=None, context='default', action=None, possible_outcomes=(), observed_outcome=None, proposed_belief_ids=()):
        if metacognitive_action is None:
            if metacognitive_task is None or capability_profile is None:
                raise TypeError('METACOGNITIVE_ACTION_OR_TASK_PROFILE_REQUIRED')
            decision=self.metacognitive_decide(metacognitive_task,capability_profile)
            metacognitive_action=decision.action
        xs=[x if isinstance(x,WorkspaceItem) else WorkspaceItem(**x) for x in items]
        return self._digital_workspace.cycle(
            goal=goal,items=xs,consumers=consumers,metacognitive_action=metacognitive_action,
            context=context,action=action,possible_outcomes=possible_outcomes,observed_outcome=observed_outcome,
            proposed_belief_ids=proposed_belief_ids,
        )

    def digital_consciousness_snapshot(self):
        out=self._digital_workspace.functional_indicator_snapshot()
        out.update({
            'episode_count':len(self._digital_workspace.episodes),
            'attention_calibration':self._digital_workspace.attention.calibration,
            'mean_prediction_error':self._digital_workspace.predictor.mean_prediction_error,
            'continuity_verified':self._digital_workspace.verify_continuity() if self._digital_workspace.episodes else False,
            'semantic_boundary':'FUNCTIONAL_DIGITAL_CONSCIOUSNESS_ARCHITECTURE_NOT_PROOF_OF_SUBJECTIVE_EXPERIENCE',
        })
        return out

    def rc8_boundaries(self):
        audit=self.canonical_state.get('deep_self_audit') or {}
        return {
            'remaining_findings':list(audit.get('remaining_findings') or []),
            'continuous_daemon_enabled':False,
            'general_open_ended_transfer_proven':False,
            'subjective_consciousness_claimed':False,
            'foundation_weights_modified':False,
        }

    def unified_snapshot(self):
        s=super().unified_snapshot()
        s.update({
            'profile':self.PROFILE,
            'schema_version':self.SCHEMA_VERSION,
            'canonical_state_version':self.VERSION,
            'kernel_identity':self.kernel_identity(),
            'migration_contract':self.migration_contract(),
            'external_runtime':self.external_runtime_identity(),
            'cognitive_capability_lineage':self.cognitive_capability_lineage(),
            'skill_admission':self.skill_admission_capability(),
            'transfer_memory':self.transfer_memory_capability(),
            'transfer_evaluation':self.transfer_evaluation_capability(),
            'metacognitive_control':self.metacognitive_control_capability(),
            'digital_consciousness':self.digital_consciousness_capability(),
            'digital_consciousness_runtime':self.digital_consciousness_snapshot(),
            'rc8_boundaries':self.rc8_boundaries(),
        })
        return s

__all__=['UnifiedYADOKernelV30RC8ExternalCognitive']
