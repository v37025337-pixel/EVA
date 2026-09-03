from __future__ import annotations
import ast, json, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent
RECOVERY={
 'yado_trace_crystallization_cycle1','yado_cognitive_training_cycle1','yado_organ_autoevolution_cycle1',
 'yado_meta_grammar_extension_genesis_cycle1','yado_algorithm_component_genesis_cycle1',
 'yado_semantic_boundary_repair_probe','yado_evolution_of_evolution_cycle1','yado_core_v3_0_rc6_r2_real_external'
}

def closure(entry:str):
    seen=set(); stack=[entry]
    while stack:
        mod=stack.pop()
        if mod in seen: continue
        p=ROOT/(mod+'.py')
        if not p.exists(): continue
        seen.add(mod)
        tree=ast.parse(p.read_text(encoding='utf-8'))
        for n in ast.walk(tree):
            if isinstance(n,ast.ImportFrom) and n.module and n.module.startswith('yado_'):
                stack.append(n.module)
            elif isinstance(n,ast.Import):
                for a in n.names:
                    if a.name.startswith('yado_'): stack.append(a.name)
    return seen

class TestProvenanceReductionCycle1(unittest.TestCase):
    def test_v29_uses_native_runtime(self):
        text=(ROOT/'yado_core_v2_9_trace_crystallization.py').read_text(encoding='utf-8')
        self.assertIn('from yado_transition_runtime_native_v1 import',text)
        self.assertNotIn('from yado_trace_crystallization_cycle1 import',text)
    def test_active_closure_drops_one_recovery_dependency(self):
        c=closure('yado_core_v3_0_rc7_deep_integrity')
        self.assertIn('yado_transition_runtime_native_v1',c)
        self.assertNotIn('yado_trace_crystallization_cycle1',c)
        self.assertLessEqual(len(c & RECOVERY),7)
    def test_native_provenance_boundary(self):
        from yado_transition_runtime_native_v1 import PROVENANCE
        self.assertEqual(PROVENANCE['status'],'RC7_NATIVE_REDERIVATION_V1')
        self.assertFalse(PROVENANCE['lost_original_recovered'])
    def test_equivalence_receipt(self):
        d=json.loads((ROOT/'yado_provenance_reduction_cycle1_equivalence.json').read_text(encoding='utf-8'))
        self.assertEqual(d['status'],'PASS')
        self.assertEqual(d['total_cases'],960)

if __name__=='__main__': unittest.main()
