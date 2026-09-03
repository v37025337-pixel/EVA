from __future__ import annotations
import ast, json, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
RECOVERY={
 'yado_trace_crystallization_cycle1','yado_cognitive_training_cycle1','yado_organ_autoevolution_cycle1',
 'yado_meta_grammar_extension_genesis_cycle1','yado_algorithm_component_genesis_cycle1',
 'yado_semantic_boundary_repair_probe','yado_evolution_of_evolution_cycle1','yado_core_v3_0_rc6_r2_real_external'
}
def closure(entry):
    seen=set(); stack=[entry]
    while stack:
        m=stack.pop(); p=ROOT/(m+'.py')
        if m in seen or not p.exists(): continue
        seen.add(m); tree=ast.parse(p.read_text(encoding='utf-8'))
        for n in ast.walk(tree):
            if isinstance(n,ast.ImportFrom) and n.module and n.module.startswith('yado_'): stack.append(n.module)
            elif isinstance(n,ast.Import):
                for a in n.names:
                    if a.name.startswith('yado_'): stack.append(a.name)
    return seen
class TestProvenanceReductionCycle4(unittest.TestCase):
    def test_r3_uses_native_r2_bridge(self):
        t=(ROOT/'yado_core_v3_0_rc6_r3_real_external.py').read_text(encoding='utf-8')
        self.assertIn('from yado_external_bridge_native_v1 import UnifiedYADOKernelV30RC6R2NativeExternal',t)
        self.assertNotIn('from yado_core_v3_0_rc6_r2_real_external import',t)
    def test_active_closure_drops_fourth_recovery_dependency(self):
        c=closure('yado_core_v3_0_rc7_deep_integrity')
        self.assertNotIn('yado_core_v3_0_rc6_r2_real_external',c)
        self.assertIn('yado_external_bridge_native_v1',c)
        self.assertLessEqual(len(c&RECOVERY),4)
    def test_strong_equivalence_receipt(self):
        d=json.loads((ROOT/'yado_provenance_reduction_cycle4_equivalence.json').read_text())
        self.assertEqual(d['status'],'PASS_STRONG_SYNTHETIC_AND_DURABLE_EQUIVALENCE')
        self.assertEqual(d['logic_cases'],20000)
        self.assertEqual(d['route_cases'],5005)
    def test_native_provenance_boundary(self):
        from yado_external_bridge_native_v1 import PROVENANCE
        self.assertFalse(PROVENANCE['lost_original_recovered'])
        self.assertFalse(PROVENANCE['external_code_copied_verbatim'])
if __name__=='__main__': unittest.main()
