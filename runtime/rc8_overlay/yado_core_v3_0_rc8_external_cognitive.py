from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any

from yado_core_v3_0_rc7_deep_integrity import UnifiedYADOKernelV30RC7DeepIntegrity
from yado_core_v3_0_rc6_r6_schema_adaptation import UnifiedYADOKernelV30RC6R6SchemaAdaptation
from yado_frontier_portfolio_runtime import ValidatedFrontierPortfolio
from yado_host_capability_runtime import HostCapabilityRelationRouter

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

        # Bypass RC7 metadata guard but preserve the entire lower kernel lineage.
        UnifiedYADOKernelV30RC6R6SchemaAdaptation.__init__(self,db_path=db_path,state_path=str(p))
        self._frontier=ValidatedFrontierPortfolio(self.canonical_state.get('validated_frontier_portfolio') or {})
        self._host_router=HostCapabilityRelationRouter(self.canonical_state.get('host_capability_model') or {})

    def kernel_identity(self):
        return dict(self.canonical_state.get('kernel_identity') or {})

    def migration_contract(self):
        return dict(self.canonical_state.get('rc8_migration') or {})

    def external_runtime_identity(self):
        return dict(self.canonical_state.get('external_runtime') or {})

    def cognitive_capability_lineage(self):
        return dict(self.canonical_state.get('cognitive_capability_lineage') or {})

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
            'rc8_boundaries':self.rc8_boundaries(),
        })
        return s

__all__=['UnifiedYADOKernelV30RC8ExternalCognitive']