"""Public development entry points preserve the activated grammar and memory."""
import os
from pathlib import Path
import tempfile
import unittest

from successor.kernel import SuccessorKernel
from successor.cognitive import CognitiveLoop
from successor.compositional_binding import grammar_at
from successor.compositional_source import GRAMMAR, GRAMMAR_V2

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(os.environ.get('YADO_SUCCESSOR_TEST_MANIFEST',
                              ROOT / 'successor/state/birth-v2/manifest.json'))


class NativeProgramProfileTests(unittest.TestCase):
    def setUp(self):
        if not MANIFEST.exists():
            self.skipTest('Build the pinned successor before integration tests')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = Path(self.tmp.name) / 'kernel.sqlite'
        self.kernel = SuccessorKernel(MANIFEST, self.state)
        self.addCleanup(lambda: self.kernel.close())

    def test_default_enable_preserves_v2_and_explicit_switch_is_rejected(self):
        first = CognitiveLoop(self.kernel).set_compositional_synthesis(grammar=GRAMMAR_V2)
        before = self.kernel.verify_state()
        self.assertEqual(self.kernel.set_compositional_synthesis(), first)
        self.assertEqual(self.kernel.verify_state(), before)
        with self.assertRaisesRegex(ValueError, 'COMPOSITIONAL_PROFILE_REQUIRES_DEACTIVATION'):
            CognitiveLoop(self.kernel).set_compositional_synthesis(grammar=GRAMMAR)
        self.assertEqual(self.kernel.verify_state(), before)

    def test_public_status_reports_active_v2_programs(self):
        self.kernel.set_compositional_synthesis(grammar=GRAMMAR_V2)
        rows = [{'input': {'text': text}, 'expected': expected}
                for text, expected in [('ONE', 'one'), ('TWO', 'two'), ('THREE', 'three')]]
        goal = self.kernel.open_goal({'schema': 'yado.native_program_goal.v1',
            'domain': 'native_source', 'training': rows,
            'validation': [{'input': {'text': 'FOUR'}, 'expected': 'four'},
                           {'input': {'text': 'FIVE'}, 'expected': 'five'}],
            'queries': [{'input': {'text': 'SIX'}}]},
            budget=4, mode='no_memory')
        self.kernel.think(40)
        result = self.kernel.cognitive_snapshot()['goals'][str(goal)]
        self.assertEqual(result['status'], 'VALIDATED_ON_HOLDOUT')
        status = self.kernel.native_program_status()
        self.assertEqual(status['language']['grammar'], GRAMMAR_V2)
        self.assertIn(result['result']['source_sha256'],
                      [p['source_sha256'] for p in status['verified_programs']])

    def test_development_continues_v2_after_restart(self):
        CognitiveLoop(self.kernel).set_compositional_synthesis(grammar=GRAMMAR_V2)
        self.kernel.close()
        self.kernel = SuccessorKernel(MANIFEST, self.state)
        result = self.kernel.develop_native_programs(rounds=1)
        self.assertEqual(result['sessions'][0]['status'], 'COMPLETE')
        self.assertEqual(grammar_at(CognitiveLoop(self.kernel)._records()), GRAMMAR_V2)


if __name__ == '__main__':
    unittest.main()
