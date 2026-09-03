from __future__ import annotations
import random,tempfile,unittest
from yado_external_runtime_contract_v1 import HARD_REQUIREMENTS,assess_runtime,expected_boot_contract,verify_boot_receipt
from yado_core_v3_0_rc7_deep_integrity import UnifiedYADOKernelV30RC7DeepIntegrity
class ExternalRuntimeContract(unittest.TestCase):
 def test_current_connector_evidence_rejected_for_exact_reasons(self):
  github={'authorized_write_channel':False,'python_execution':True,'durable_state':True,'scheduled_or_event_invocation':True,'outbound_https':True,'independent_readback':True}
  self.assertEqual(assess_runtime(github).verdict,'BLOCKED_AUTHORIZED_WRITE_CHANNEL')
  vercel={'authorized_write_channel':True,'python_execution':True,'durable_state':False,'scheduled_or_event_invocation':True,'outbound_https':True,'independent_readback':False,'deployment_created':True,'provider_ready':True,'project_visible':False}
  a=assess_runtime(vercel);self.assertEqual(a.verdict,'CONTRADICTORY_UNVERIFIED');self.assertIn('DEPLOYMENT_CREATED_WITHOUT_READBACK',a.contradictions)
  supabase={'authorized_write_channel':True,'python_execution':False,'durable_state':True,'scheduled_or_event_invocation':True,'outbound_https':True,'independent_readback':True,'runtime_kind':'DENO_ONLY'}
  self.assertEqual(assess_runtime(supabase).verdict,'BLOCKED_PYTHON_RUNTIME')
 def test_all_hard_requirements_needed(self):
  good={k:True for k in HARD_REQUIREMENTS};self.assertTrue(assess_runtime(good).eligible)
  for k in HARD_REQUIREMENTS:
   x=dict(good);x[k]=False;self.assertFalse(assess_runtime(x).eligible,k)
 def test_fresh_random_holdout_matches_oracle_and_beats_naive(self):
  r=random.Random(26082955);new_false_accept=0;naive_false_accept=0;new_mismatch=0
  for _ in range(2000):
   e={k:bool(r.getrandbits(1)) for k in HARD_REQUIREMENTS}
   e['deployment_created']=bool(r.getrandbits(1));e['provider_ready']=bool(r.getrandbits(1));e['project_visible']=bool(r.getrandbits(1))
   contradictions=(e['deployment_created'] and not e['independent_readback']) or (e['provider_ready'] and not e['project_visible'])
   oracle=all(e[k] for k in HARD_REQUIREMENTS) and not contradictions
   got=assess_runtime(e).eligible
   if got!=oracle:new_mismatch+=1
   naive=e['deployment_created'] and e['outbound_https']
   if got and not oracle:new_false_accept+=1
   if naive and not oracle:naive_false_accept+=1
  self.assertEqual(new_mismatch,0);self.assertEqual(new_false_accept,0);self.assertGreater(naive_false_accept,100)
 def test_boot_receipt_requires_exact_identity_and_independent_readback(self):
  exp=expected_boot_contract(kernel_class='K',profile='P',state_sha256='s'*64,manifest_sha256='m'*64)
  receipt={**exp,'host':'external-python','independent_readback':True,'background_daemon':False,'canonical_state_mutated':False,'credential_bypass':False,'oauth_bypass':False,'payment_bypass':False}
  self.assertTrue(verify_boot_receipt(receipt,exp)['verified'])
  for key in ['canonical_state_sha256','manifest_sha256','kernel_profile']:
   bad=dict(receipt);bad[key]='tampered';self.assertFalse(verify_boot_receipt(bad,exp)['verified'])
  bad=dict(receipt);bad['independent_readback']=False;self.assertFalse(verify_boot_receipt(bad,exp)['verified'])
 def test_kernel_exposes_same_gate(self):
  k=UnifiedYADOKernelV30RC7DeepIntegrity(db_path=tempfile.gettempdir()+'/yado_ext_contract_test.sqlite')
  e={x:True for x in HARD_REQUIREMENTS};self.assertTrue(k.assess_external_runtime_candidate(e)['eligible'])
  try:k.close()
  except Exception:pass
if __name__=='__main__':unittest.main()
