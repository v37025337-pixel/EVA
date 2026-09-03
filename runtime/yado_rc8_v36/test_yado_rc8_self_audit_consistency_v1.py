import copy,json,tempfile,unittest
from pathlib import Path
from yado_rc8_self_audit_consistency_v1 import validate_state_self_model,validate_package_coherence
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
ROOT=Path(__file__).resolve().parent
class TestRC8SelfAuditConsistency(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state=json.loads((ROOT/'yado_canonical_state_v3_rc8_external_cognitive.json').read_text())
        cls.manifest=json.loads((ROOT/'yado_development_manifest_v33.json').read_text())
        cls.head=json.loads((ROOT/'yado_active_developmental_head.json').read_text())
    def test_repaired_state_is_coherent(self):
        self.assertEqual(validate_state_self_model(self.state),[])
    def test_stale_pending_is_detected(self):
        s=copy.deepcopy(self.state)
        s['deep_self_audit']['transfer_progress']['direct_research_external_verification_pending']=True
        self.assertIn('DIRECT_RESEARCH_STILL_MARKED_PENDING',validate_state_self_model(s))
    def test_missing_new_capability_is_detected(self):
        s=copy.deepcopy(self.state)
        s['r8_self_model']['known_capabilities'].remove('PROCEDURAL_TRANSFER_MEMORY')
        self.assertTrue(any(x.startswith('SELF_MODEL_CAPABILITIES_STALE:') for x in validate_state_self_model(s)))
    def test_core_fails_closed_on_stale_state(self):
        s=copy.deepcopy(self.state)
        s['cognitive_capability_lineage']['internet_research_cycle']['status']='BOUNDED_DIRECT_FETCH_SCRIPT_READY_EXTERNAL_VERIFICATION_PENDING'
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'state.json'; p.write_text(json.dumps(s))
            with self.assertRaisesRegex(RuntimeError,'R8_SELF_MODEL_COHERENCE_FAILURE'):
                UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(Path(td)/'x.db'),state_path=str(p))
    def test_current_package_semantics_are_coherent(self):
        import yado_bootstrap
        manifest=json.loads((ROOT/yado_bootstrap.MANIFEST_NAME).read_text())
        head=json.loads((ROOT/'yado_active_developmental_head.json').read_text())
        self.assertEqual(validate_package_coherence(manifest,head,self.state),[])
