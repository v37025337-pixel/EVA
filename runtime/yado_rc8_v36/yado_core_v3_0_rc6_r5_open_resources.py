from __future__ import annotations
from pathlib import Path
from yado_core_v3_0_rc6_r4_real_external import UnifiedYADOKernelV30RC6R4RealExternal
from yado_open_access_resource_runtime import OpenAccessSourceRouter

ROOT=Path(__file__).resolve().parent
DEFAULT_STATE=ROOT/'yado_canonical_state_v3_rc6_r5_open_resources.json'

class UnifiedYADOKernelV30RC6R5OpenResources(UnifiedYADOKernelV30RC6R4RealExternal):
    PROFILE='YADO_V3_0_RC6_R5_OPEN_RESOURCE_ECOSYSTEM_LOCAL'
    SCHEMA_VERSION=24
    def __init__(self,db_path='yado_v30_rc6_r5_open_resources.db',state_path=None):
        super().__init__(db_path=db_path,state_path=state_path or str(DEFAULT_STATE))
    def open_access_ecosystem(self):
        return dict(self.canonical_state.get('open_access_resource_ecosystem') or {})
    def open_access_sources(self):
        return dict(self.open_access_ecosystem().get('sources') or {})
    def route_open_resource(self,query:str,historical_ok:bool=False):
        eco=self.open_access_ecosystem(); src=self.open_access_sources()
        if not src:
            return {'action':'SEEK_MORE_EVIDENCE','reason':'NO_OPEN_ACCESS_SOURCE_REGISTRY'}
        features=tuple(eco.get('selected_features') or ('TOKEN_SOFT',))
        return OpenAccessSourceRouter(src).route(query,features,historical_ok=historical_ok)
    def resource_use_policy(self,source_id:str):
        p=self.open_access_sources().get(source_id)
        if not p:return {'action':'SEEK_MORE_EVIDENCE','reason':'UNKNOWN_SOURCE'}
        return {'action':'USE_POLICY','source_id':source_id,'status':p.get('status'),'role':p.get('role'),
                'use_policy':p.get('use_policy'),'authority':bool(p.get('authority',False)),
                'auto_execute':bool(p.get('auto_execute',False)),'access':p.get('access')}
    def unified_snapshot(self):
        s=super().unified_snapshot();s.update({'profile':self.PROFILE,'schema_version':self.SCHEMA_VERSION,
            'open_access_resource_ecosystem':self.open_access_ecosystem()});return s

__all__=['UnifiedYADOKernelV30RC6R5OpenResources']
