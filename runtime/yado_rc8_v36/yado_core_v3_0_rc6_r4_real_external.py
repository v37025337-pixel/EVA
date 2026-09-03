from __future__ import annotations
from pathlib import Path
from typing import Mapping, Sequence

from yado_core_v3_0_rc6_r3_real_external import UnifiedYADOKernelV30RC6R3RealExternal
from yado_job_condition_runtime import JobConditionRuntime, UnsupportedExpression, matrix_cardinality, eligible_job_instances

ROOT=Path(__file__).resolve().parent
DEFAULT_STATE=ROOT/'yado_canonical_state_v3_rc6_r4_real_external.json'

class UnifiedYADOKernelV30RC6R4RealExternal(UnifiedYADOKernelV30RC6R3RealExternal):
    PROFILE='YADO_V3_0_RC6_R4_REAL_JOB_CAUSALITY_LOCAL'
    SCHEMA_VERSION=23
    def __init__(self, db_path='yado_v30_rc6_r4_real_external.db', state_path=None):
        super().__init__(db_path=db_path,state_path=state_path or str(DEFAULT_STATE))

    def job_condition_registry(self):
        return dict((self.logic_registry().get('job_condition_semantics') or {}))

    def evaluate_job_condition(self, expr:str, context:Mapping[str,object]):
        reg=self.job_condition_registry(); ops=reg.get('expanded_operator_registry') or ()
        try:
            pred=bool(JobConditionRuntime(ops).evaluate(expr,context))
        except UnsupportedExpression as e:
            return {'action':'SEEK_MORE_EVIDENCE','reason':'UNSUPPORTED_JOB_CONDITION','detail':str(e),'operators':list(ops)}
        return {'action':'USE_MODEL','prediction':pred,'operators':list(ops),'mechanism':reg.get('mechanism')}

    def matrix_instances(self, dimensions:Sequence[int]):
        return {'action':'USE_MODEL','instances':matrix_cardinality(dimensions),'mechanism':'CARTESIAN_PRODUCT_CARDINALITY'}

    def eligible_instances(self, needs:Sequence[str], needs_status:Mapping[str,str], expr:str|None, context:Mapping[str,object], dimensions:Sequence[int]):
        ops=self.job_condition_registry().get('expanded_operator_registry') or ()
        v=eligible_job_instances(needs,needs_status,expr,context,dimensions,ops)
        if v is None:return {'action':'SEEK_MORE_EVIDENCE','reason':'UNSUPPORTED_JOB_CONDITION'}
        return {'action':'USE_MODEL','instances':v,'mechanism':'NEEDS_STATUS_PLUS_CONDITION_PLUS_MATRIX'}

    @staticmethod
    def extract_workflow_run_edge(target_workflow:str, source_workflow:str):
        # Generic semantic extraction: a workflow_run trigger creates a causal
        # predecessor edge from the named source workflow to this workflow.
        if not target_workflow or not source_workflow:
            return {'action':'SEEK_MORE_EVIDENCE','reason':'MISSING_WORKFLOW_RUN_ENDPOINT'}
        return {'action':'USE_MODEL','edge':[str(source_workflow),str(target_workflow)],'mechanism':'WORKFLOW_RUN_SOURCE_TO_TARGET_EDGE'}

    def unified_snapshot(self):
        s=super().unified_snapshot();s.update({'profile':self.PROFILE,'schema_version':self.SCHEMA_VERSION,
            'r4_job_condition_semantics':self.job_condition_registry(),
            'r4_thinking':dict((self.real_external_registry().get('THINKING') or {}))})
        return s

__all__=['UnifiedYADOKernelV30RC6R4RealExternal']
