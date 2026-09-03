import ast,json,pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parent
REC={'yado_trace_crystallization_cycle1','yado_cognitive_training_cycle1','yado_organ_autoevolution_cycle1','yado_meta_grammar_extension_genesis_cycle1','yado_algorithm_component_genesis_cycle1','yado_semantic_boundary_repair_probe','yado_evolution_of_evolution_cycle1','yado_core_v3_0_rc6_r2_real_external'}
class Cycle6(unittest.TestCase):
 def test_consumers_use_native(self):
  for n in ['yado_core_v3_0_rc4_meta_autoevolution.py','yado_core_v3_0_rc6_r1_real_external.py']:
   s=(ROOT/n).read_text(); self.assertIn('yado_evolution_runtime_native_v1',s); self.assertNotIn('from yado_evolution_of_evolution_cycle1 import',s)
 def test_old_shim_absent_active(self):
  self.assertFalse((ROOT/'yado_evolution_of_evolution_cycle1.py').exists())
 def test_active_recovery_le_two(self):
  seen=set();stack=['yado_core_v3_0_rc7_deep_integrity']
  while stack:
   m=stack.pop()
   if m in seen:continue
   seen.add(m);p=ROOT/(m+'.py')
   if not p.exists():continue
   t=ast.parse(p.read_text())
   for x in ast.walk(t):
    mods=[]
    if isinstance(x,ast.Import):mods=[a.name.split('.')[0] for a in x.names]
    elif isinstance(x,ast.ImportFrom) and x.module:mods=[x.module.split('.')[0]]
    stack.extend(a for a in mods if a.startswith('yado_') and a not in seen)
  active=REC&seen
  self.assertNotIn('yado_evolution_of_evolution_cycle1',active)
  self.assertLessEqual(len(active),2)
 def test_equivalence_and_failclosed(self):
  r=json.loads((ROOT/'yado_provenance_reduction_cycle6_equivalence.json').read_text())
  self.assertEqual(r['status'],'PASS_EQUIVALENCE_PLUS_FAIL_CLOSED_REPAIR')
  self.assertEqual(r['differences'],[])
  self.assertGreater(r['counts']['linear_old_crash_new_withhold'],0)
 def test_provenance_boundary(self):
  import yado_evolution_runtime_native_v1 as n
  self.assertFalse(n.NATIVE_PROVENANCE['lost_original_recovered'])
  self.assertFalse(n.NATIVE_PROVENANCE['external_code_copied_verbatim'])
if __name__=='__main__':unittest.main()
