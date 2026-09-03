import hashlib,json,os,tempfile,unittest
from pathlib import Path
from yado_core_v3_0_rc7_deep_integrity import UnifiedYADOKernelV30RC7DeepIntegrity,DEFAULT_STATE
from yado_stateful_frontier_repair_cycle1 import product_transfer_request
from yado_stateful_frontier_repair_cycle13 import request as active_information_gain_request
ROOT=Path(__file__).resolve().parent
PARENT=ROOT/'yado_canonical_state_v3_rc6_r6_schema_adaptation.json'
class TestRC7DeepIntegrity(unittest.TestCase):
    def setUp(self):self.k=UnifiedYADOKernelV30RC7DeepIntegrity(db_path=':memory:')
    def tearDown(self):self.k.close()
    def test_profile_metadata_and_audit(self):
        s=self.k.unified_snapshot();self.assertEqual(s['profile'],'YADO_V3_0_RC7_DEEP_INTEGRITY_AND_FRONTIER_CONSOLIDATION_LOCAL');self.assertEqual(s['canonical_state_version'],'3.0-rc7');self.assertEqual(s['deep_self_audit']['remaining_findings'],['F-R7-PROV-015','F-R7-BOUND-016'])
    def test_parent_r6_unchanged(self):
        self.assertEqual(hashlib.sha256(PARENT.read_bytes()).hexdigest(),'b910356f172069e97437802955decee262608fab4330b675148b167acfe523b3')
    def test_direct_fetch_is_default_deny(self):
        with self.assertRaisesRegex(ValueError,'explicit YADO_ALLOWED_DOMAINS'):
            self.k._validate_evidence_url('https://example.com',set())
    def test_private_address_rejected_even_if_allowlisted(self):
        with self.assertRaisesRegex(ValueError,'non-public'):
            self.k._validate_evidence_url('https://127.0.0.1',{'127.0.0.1'})
    def test_historical_state_commit_guard(self):
        fd,p=tempfile.mkstemp(suffix='.json',dir=str(ROOT));os.close(fd)
        try:
            Path(p).write_bytes(DEFAULT_STATE.read_bytes()); k=UnifiedYADOKernelV30RC7DeepIntegrity(db_path=':memory:',state_path=p)
            try:r=k.durable_commit_evolution_bundle({}, {'passed':True});self.assertFalse(r['committed']);self.assertEqual(r['reason'],'HISTORICAL_OR_NONACTIVE_STATE_IMMUTABLE_IN_R7')
            finally:k.close()
        finally:Path(p).unlink(missing_ok=True)
    def test_durable_host_model_replays_fresh(self):
        d=json.loads((ROOT/'yado_chatgpt_study_cycle2_report.json').read_text())
        for row in d['fresh_results']:
            got=self.k.route_host_capability(row['query']);self.assertEqual(got['action'],row['expected'],row['id'])
    def test_instance_local_stateful_frontier(self):
        r=product_transfer_request();g=self.k.run_frontier_causal_cycle(r);a=self.k.run_frontier_causal_cycle(r,ablate={'MECHANISM'})
        self.assertTrue(g['cycle_success']);self.assertEqual((g['blind_score'],g['ablation_score'],g['restore_score']),(1.0,0.0,1.0));self.assertFalse(a['cycle_success'])
    def test_active_information_gain_frontier(self):
        r=active_information_gain_request();g=self.k.run_frontier_causal_cycle(r)
        self.assertTrue(g['cycle_success']);self.assertEqual((g['blind_score'],g['ablation_score'],g['restore_score']),(1.0,0.0,1.0))
if __name__=='__main__':unittest.main()
