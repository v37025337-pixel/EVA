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
class TestProvenanceReductionCycle2(unittest.TestCase):
 def test_semantic_consumer_uses_direct_durable_source(self):
  t=(ROOT/'yado_semantic_selective_v27.py').read_text(encoding='utf-8')
  self.assertIn('FRESH_DOCS as _FRESH_DOCS',t)
  self.assertNotIn('from yado_semantic_boundary_repair_probe import',t)
 def test_active_closure_drops_second_recovery_dependency(self):
  c=closure('yado_core_v3_0_rc7_deep_integrity')
  self.assertNotIn('yado_semantic_boundary_repair_probe',c)
  self.assertLessEqual(len(c&RECOVERY),6)
 def test_equivalence_receipt(self):
  d=json.loads((ROOT/'yado_provenance_reduction_cycle2_equivalence.json').read_text())
  self.assertEqual(d['status'],'PASS');self.assertTrue(d['canonical_identity']);self.assertEqual(d['cases'],220)
 def test_source_contract_is_direct(self):
  import yado_semantic_selective_v27 as s
  from yado_resource_intelligence_cycle8 import T1,T2,T3,FRESH_DOCS
  self.assertEqual(s.OLD1,list(T1)+list(T2));self.assertEqual(s.OLD2,list(T3));self.assertEqual(s.FRESH_DOCS,list(FRESH_DOCS))
if __name__=='__main__':unittest.main()
