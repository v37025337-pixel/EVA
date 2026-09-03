from __future__ import annotations
import ast,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
RECOVERY={'yado_trace_crystallization_cycle1','yado_cognitive_training_cycle1','yado_organ_autoevolution_cycle1','yado_meta_grammar_extension_genesis_cycle1','yado_algorithm_component_genesis_cycle1','yado_semantic_boundary_repair_probe','yado_evolution_of_evolution_cycle1','yado_core_v3_0_rc6_r2_real_external'}
CONSUMERS=['yado_core_v3_0_rc6_r3_real_external.py','yado_core_v3_0_rc4_meta_autoevolution.py','yado_evolution_runtime_native_v1.py','yado_core_v3_0_rc3_autoevolution.py','yado_external_bridge_native_v1.py','yado_core_v3_0_rc3_trained.py','yado_algorithm_component_runtime_native_v1.py']
def closure(entry):
 seen=set();stack=[entry]
 while stack:
  m=stack.pop();p=ROOT/(m+'.py')
  if m in seen or not p.exists():continue
  seen.add(m);t=ast.parse(p.read_text())
  for n in ast.walk(t):
   if isinstance(n,ast.ImportFrom) and n.module and n.module.startswith('yado_'):stack.append(n.module.split('.')[0])
   elif isinstance(n,ast.Import):stack.extend(a.name.split('.')[0] for a in n.names if a.name.startswith('yado_'))
 return seen
class Cycle8(unittest.TestCase):
 def test_active_recovery_closure_is_zero(self):
  c=closure('yado_core_v3_0_rc7_deep_integrity')
  self.assertEqual(sorted(c&RECOVERY),[])
  self.assertIn('yado_organ_runtime_native_v1',c)
 def test_all_live_consumers_use_native_organ_runtime(self):
  for name in CONSUMERS:
   s=(ROOT/name).read_text();self.assertIn('yado_organ_runtime_native_v1',s);self.assertNotIn('from yado_organ_autoevolution_cycle1 import',s)
 def test_equivalence_receipt(self):
  d=json.loads((ROOT/'yado_provenance_reduction_cycle8_equivalence.json').read_text())
  self.assertEqual(d['status'],'PASS');self.assertEqual(d['difference_count'],0);self.assertGreaterEqual(d['total'],19000)
 def test_native_provenance_boundary(self):
  import yado_organ_runtime_native_v1 as n
  self.assertFalse(n.NATIVE_PROVENANCE['lost_original_recovered']);self.assertFalse(n.NATIVE_PROVENANCE['external_code_copied_verbatim'])
if __name__=='__main__':unittest.main()
