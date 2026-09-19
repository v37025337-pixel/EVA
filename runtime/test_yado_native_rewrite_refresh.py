import ast
import copy
from pathlib import Path
import unittest

from yado_native_experience_to_runtime_self_rewrite_v2 import synthesize_candidate as v2
from yado_native_experience_to_runtime_self_rewrite_v3 import synthesize_candidate as v3

ROOT = Path(__file__).resolve().parent


def binding(source):
    values = [ast.literal_eval(n.value) for n in ast.parse(source).body
              if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name)
              and t.id == 'LEARNED_EXTERNAL_EVIDENCE_V2' for t in n.targets)]
    return values


class NativeRewriteRefreshTests(unittest.TestCase):
    def setUp(self):
        self.parent = (ROOT / 'yado_bounded_autonomous_learning_v1.py').read_text()
        self.experience = {'experience_digest': 'a' * 64,
                           'sources': [{'source_id': 'MDN_HTTP', 'facts': ['Fresh protocol network learning evidence.'],
                                        'network': {'host': 'developer.mozilla.org'}}],
                           'failures': [{'source_id': 'PYTHON_AST'}]}

    def test_v2_refreshes_effective_binding_on_already_learned_parent(self):
        source, learned, safety = v2(self.parent, self.experience)
        self.assertEqual(binding(source), [learned])
        self.assertEqual(binding(source)[-1]['experience_digest'], 'a' * 64)
        self.assertEqual(learned['failed_source_ids'], ['PYTHON_AST'])
        self.assertEqual(safety['new_dangerous_calls'], {})

    def test_refresh_does_not_accumulate_score_bonuses(self):
        once, _, _ = v2(self.parent, self.experience)
        twice, _, _ = v2(once, self.experience)
        self.assertEqual(once, twice)

    def test_v3_removes_stale_duplicate_binding(self):
        # Reproduce a parent emitted by the old V2 generator: a stale later
        # assignment used to override the first, refreshed assignment.
        duplicate = self.parent + '\nLEARNED_EXTERNAL_EVIDENCE_V2 = ' + repr(binding(self.parent)[0]) + '\n'
        source, learned, _ = v3(duplicate, self.experience)
        self.assertEqual(binding(source), [learned])

    def test_repeated_v3_refresh_is_idempotent(self):
        source, _, _ = v3(self.parent, self.experience)
        self.assertEqual(v3(source, self.experience)[0], source)


if __name__ == '__main__':
    unittest.main()
