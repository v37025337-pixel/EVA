from __future__ import annotations
import ast,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
RECOVERY={'yado_trace_crystallization_cycle1','yado_cognitive_training_cycle1','yado_organ_autoevolution_cycle1','yado_meta_grammar_extension_genesis_cycle1','yado_algorithm_component_genesis_cycle1','yado_semantic_boundary_repair_probe','yado_evolution_of_evolution_cycle1','yado_core_v3_0_rc6_r2_real_external'}
def closure(entry):
 seen=set();stack=[entry]
 while stack:
  m=stack.pop();p=ROOT/(m+'.py')
  if m in seen or not p.exists():continue
  seen.add(m);t=ast.parse(p.read_text(encoding='utf-8'))
  for n in ast.walk(t):
   if isinstance(n,ast.ImportFrom) and n.module and n.module.startswith('yado_'):stack.append(n.module)
   elif isinstance(n,ast.Import):
    for a in n.names:
     if a.name.startswith('yado_'):stack.append(a.name)
 return seen
class TestProvenanceReductionCycle5(unittest.TestCase):
 def test_meta_consumer_uses_native_runtime(self):
  t=(ROOT/'yado_core_v3_0_rc6_meta_grammar.py').read_text(encoding='utf-8')
  self.assertIn('import yado_meta_grammar_runtime_native_v1 as mg',t)
  self.assertNotIn('import yado_meta_grammar_extension_genesis_cycle1 as mg',t)
 def test_active_closure_drops_fifth_recovery_dependency(self):
  c=closure('yado_core_v3_0_rc7_deep_integrity')
  self.assertNotIn('yado_meta_grammar_extension_genesis_cycle1',c)
  self.assertIn('yado_meta_grammar_runtime_native_v1',c)
  self.assertLessEqual(len(c&RECOVERY),3)
 def test_equivalence_and_fail_closed_repair_receipt(self):
  d=json.loads((ROOT/'yado_provenance_reduction_cycle5_equivalence.json').read_text())
  self.assertEqual(d['status'],'PASS_EQUIVALENCE_PLUS_FAIL_CLOSED_REPAIR')
  self.assertEqual(d['dataset_comparisons'],492)
  self.assertGreater(d['by_family']['thinking_old_crash_new_withhold'],0)
  self.assertTrue(d['saved_crash_case_old_crashes'])
  self.assertEqual(d['saved_crash_case_new'],{'status':'WITHHOLD','reason':'REVEALED_PARTITION_COLLAPSE'})
 def test_native_provenance_boundary(self):
  from yado_meta_grammar_runtime_native_v1 import PROVENANCE
  self.assertFalse(PROVENANCE['lost_original_recovered'])
  self.assertFalse(PROVENANCE['external_code_copied_verbatim'])
if __name__=='__main__':unittest.main()
