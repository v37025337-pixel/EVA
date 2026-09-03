import copy, json, tempfile, unittest
from pathlib import Path

from yado_core_v3_0_rc7_deep_integrity import UnifiedYADOKernelV30RC7DeepIntegrity
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive

ROOT=Path(__file__).resolve().parent
RC7_STATE=ROOT/'yado_canonical_state_v3_rc7_deep_integrity.json'
RC8_STATE=ROOT/'yado_canonical_state_v3_rc8_external_cognitive.json'

class TestRC8Migration(unittest.TestCase):
    def test_rc8_identity_and_schema(self):
        k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=':memory:')
        try:
            s=k.unified_snapshot()
        finally:
            k.close()
        self.assertEqual(s['profile'],'YADO_V3_0_RC8_VERIFIED_EXTERNAL_COGNITIVE_RUNTIME')
        self.assertEqual(s['canonical_state_version'],'3.0-rc8')
        self.assertEqual(s['schema_version'],27)
        self.assertEqual(s['kernel_identity']['release_candidate'],8)

    def test_parent_payload_preserved_outside_migration_allowlist(self):
        p=json.loads(RC7_STATE.read_text())
        c=json.loads(RC8_STATE.read_text())
        allowed=set(c['rc8_migration']['allowed_changed_keys'])
        self.assertEqual({k:v for k,v in p.items() if k not in allowed},{k:v for k,v in c.items() if k not in allowed})

    def test_stale_rc7_findings_closed_and_new_boundaries_explicit(self):
        k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=':memory:')
        try:
            a=k.self_audit_registry()
        finally:
            k.close()
        self.assertNotIn('F-R7-PROV-015',a['remaining_findings'])
        self.assertNotIn('F-R7-BOUND-016',a['remaining_findings'])
        self.assertEqual(a['remaining_findings'],['F-R8-XFER-001','F-R8-DAEMON-002'])

    def test_external_runtime_and_cognitive_lineage_are_identity_level(self):
        k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=':memory:')
        try:
            e=k.external_runtime_identity(); c=k.cognitive_capability_lineage()
        finally:
            k.close()
        self.assertTrue(e['verified']); self.assertTrue(e['python_execution']); self.assertTrue(e['event_driven'])
        self.assertFalse(e['background_daemon']); self.assertTrue(e['independent_readback'])
        self.assertEqual(set(c['active_layers']),{'LOGIC','THINKING','INTELLIGENCE'})
        self.assertTrue(c['fallback_preserved'])

    def test_tampered_migration_parent_hash_fails_closed(self):
        c=json.loads(RC8_STATE.read_text())
        c['rc8_migration']['parent_state_sha256']='0'*64
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'bad.json'; p.write_text(json.dumps(c))
            with self.assertRaisesRegex(RuntimeError,'R8_PARENT_STATE_HASH_MISMATCH'):
                UnifiedYADOKernelV30RC8ExternalCognitive(db_path=':memory:',state_path=p)

    def test_rc7_rollback_image_still_boots(self):
        k=UnifiedYADOKernelV30RC7DeepIntegrity(db_path=':memory:',state_path=RC7_STATE)
        try:
            s=k.unified_snapshot()
        finally:
            k.close()
        self.assertEqual(s['profile'],'YADO_V3_0_RC7_DEEP_INTEGRITY_AND_FRONTIER_CONSOLIDATION_LOCAL')
        self.assertEqual(s['canonical_state_version'],'3.0-rc7')

if __name__=='__main__': unittest.main()
