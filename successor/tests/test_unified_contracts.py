import subprocess
import sys
import unittest

from successor.capabilities import materialize, source_expression, validate_input
from successor.graph import replay, validate_spec
from successor.kernel import fingerprint


class UnifiedContracts(unittest.TestCase):
    def test_codec_before_kernel_bootstrap(self):
        subprocess.run([sys.executable, '-c', 'from successor.kernel import fingerprint; from fractions import Fraction; assert len(fingerprint({"x":Fraction(1,3)}))==64'], check=True)

    def test_domain_cannot_override_adapter(self):
        with self.assertRaisesRegex(ValueError, 'OVERRIDE'):
            validate_input('relation', {'domain': 'events', 'events': []})

    def test_source_language_boundary_and_negative_constant(self):
        for source in ('def yado_generated_capability(x, y=1): return x',
                       'def yado_generated_capability(x, y): return abs(x)',
                       'def yado_generated_capability(x, y): return x ** y',
                       'def yado_generated_capability(x, y):\n z = x\n return z'):
            with self.assertRaises(ValueError):
                source_expression(source)
        self.assertEqual(source_expression(materialize(['+', 'x', -3])), ['+', 'x', -3])

    def test_cannot_finish_before_execution(self):
        spec = validate_spec({'goal': 'no premature success', 'nodes': [{'id': 'a', 'capability': 'relation', 'input': {'relation': [], 'start': 'x'}}]})
        with self.assertRaisesRegex(ValueError, 'PREMATURE'):
            replay([{'tick': 1, 'kind': 'GRAPH_OPEN', 'spec': spec, 'spec_digest': fingerprint(spec)},
                    {'tick': 2, 'kind': 'GRAPH_FINISH', 'graph_id': 1, 'status': 'VERIFIED'}])
