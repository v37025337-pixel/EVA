from __future__ import annotations
from pathlib import Path
from typing import Mapping
from yado_external_bridge_native_v1 import UnifiedYADOKernelV30RC6R2NativeExternal
from yado_organ_runtime_native_v1 import tree_predict

ROOT=Path(__file__).resolve().parent
DEFAULT_STATE=ROOT/'yado_canonical_state_v3_rc6_r3_real_external.json'

class UnifiedYADOKernelV30RC6R3RealExternal(UnifiedYADOKernelV30RC6R2NativeExternal):
    PROFILE='YADO_V3_0_RC6_R3_REAL_EXTERNAL_TRIGGER_GENERALIZATION_LOCAL'
    SCHEMA_VERSION=22
    def __init__(self, db_path='yado_v30_rc6_r3_real_external.db', state_path=None):
        super().__init__(db_path=db_path,state_path=state_path or str(DEFAULT_STATE))

    def dynamic_trigger_registry(self):
        return dict((self.logic_registry().get('dynamic_trigger') or {}))

    def predict_dynamic_trigger(self, features:Mapping[str,object]):
        reg=self.dynamic_trigger_registry(); model=reg.get('serialized_model')
        if not isinstance(model,dict):
            return {'action':'SEEK_MORE_EVIDENCE','reason':'NO_DYNAMIC_TRIGGER_MODEL'}
        return {'action':'USE_MODEL','prediction':bool(tree_predict(model,dict(features))),
                'representation_version':reg.get('representation_version'),
                'event_class_agnostic':bool(reg.get('event_class_agnostic'))}

    def workflow_event_support(self,event_type:str):
        legacy=set(self.logic_registry().get('supported_event_types') or ())
        dyn=self.dynamic_trigger_registry()
        if event_type in legacy:
            return {'action':'SUPPORTED','mode':'LEGACY_EVENT_GATED','event_type':event_type}
        if dyn.get('serialized_model'):
            # Dynamic representation does not key the model on a prelisted event name.
            return {'action':'SUPPORTED_DYNAMIC_REPRESENTATION','mode':'EVENT_CLASS_MATCH','event_type':event_type}
        return {'action':'SEEK_MORE_EVIDENCE','reason':'UNSUPPORTED_TRIGGER_CLASS','event_type':event_type}

    def unified_snapshot(self):
        s=super().unified_snapshot();s.update({'profile':self.PROFILE,'schema_version':self.SCHEMA_VERSION,
            'dynamic_trigger':self.dynamic_trigger_registry()});return s

__all__=['UnifiedYADOKernelV30RC6R3RealExternal']
