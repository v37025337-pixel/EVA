from __future__ import annotations
from pathlib import Path
from yado_core_v3_0_rc6_r5_open_resources import UnifiedYADOKernelV30RC6R5OpenResources
from yado_openapi_adapter_runtime import OpenAPIContractRuntime

ROOT=Path(__file__).resolve().parent
DEFAULT_STATE=ROOT/'yado_canonical_state_v3_rc6_r6_schema_adaptation.json'

class UnifiedYADOKernelV30RC6R6SchemaAdaptation(UnifiedYADOKernelV30RC6R5OpenResources):
    PROFILE='YADO_V3_0_RC6_R6_BOUNDED_SCHEMA_ADAPTATION_LOCAL'
    SCHEMA_VERSION=25
    def __init__(self,db_path='yado_v30_rc6_r6_schema_adaptation.db',state_path=None):
        super().__init__(db_path=db_path,state_path=state_path or str(DEFAULT_STATE))
        self._openapi_runtime=OpenAPIContractRuntime(self.canonical_state.get('openapi_contract_learning') or {})
    def openapi_learning(self):return dict(self.canonical_state.get('openapi_contract_learning') or {})
    def classify_openapi_contract(self,contract_id:str):return self._openapi_runtime.classify(contract_id)
    def compile_openapi_adapter(self,contract_id:str):return self._openapi_runtime.compile_plan(contract_id)
    def openapi_self_model(self):return dict(self.openapi_learning().get('self_model') or {})
    def unified_snapshot(self):
        s=super().unified_snapshot(); sec=self.openapi_learning()
        s.update({'profile':self.PROFILE,'schema_version':self.SCHEMA_VERSION,
                  'openapi_contract_learning':{k:sec.get(k) for k in ('status','train_exact','fresh_exact','ablation','restore','memory','developmental_layers','self_model')}})
        return s

__all__=['UnifiedYADOKernelV30RC6R6SchemaAdaptation']
