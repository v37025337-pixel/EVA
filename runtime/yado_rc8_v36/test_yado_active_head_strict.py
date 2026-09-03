import hashlib,json,unittest
from pathlib import Path
import yado_bootstrap
from yado_core_current import UnifiedYADOKernelCurrent,ACTIVE_PROFILE,ACTIVE_STATE,ACTIVE_STATE_SHA256
ROOT=Path(__file__).resolve().parent
class TestActiveHeadStrict(unittest.TestCase):
    def test_preimport_lock_and_contract(self):
        b=yado_bootstrap.bootstrap_integrity();self.assertTrue(b['pass']);self.assertEqual(b['profile'],ACTIVE_PROFILE);self.assertEqual(b['state_sha256'],ACTIVE_STATE_SHA256)
        c=yado_bootstrap.active_contract();self.assertEqual(c['state'],ACTIVE_STATE);self.assertEqual(c['profile'],ACTIVE_PROFILE)
    def test_state_metadata_matches_contract(self):
        c=yado_bootstrap.active_contract();d=json.loads((ROOT/c['state']).read_text())
        self.assertEqual(d['version'],c['version']);self.assertEqual(d['profile'],c['profile']);self.assertEqual(d['active_profile'],c['profile']);self.assertEqual(d['schema'],c['schema'])
    def test_current_kernel_boots_locked_profile(self):
        k=UnifiedYADOKernelCurrent(db_path=':memory:')
        try:self.assertEqual(k.unified_snapshot()['profile'],ACTIVE_PROFILE)
        finally:k.close()
if __name__=='__main__':unittest.main()
