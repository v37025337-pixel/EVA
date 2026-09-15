import copy
import os
from pathlib import Path
import tempfile
import unittest

from successor.kernel import SuccessorKernel
from successor.runtime_evolution import verify_implementations


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(os.environ.get('YADO_SUCCESSOR_TEST_MANIFEST', ROOT / 'successor/state/birth-v2/manifest.json'))


class ImplementationProvenanceTests(unittest.TestCase):
    def test_verify_and_reopen_check_upgrade_without_runtime_events(self):
        if not MANIFEST.exists():
            self.skipTest('Build the pinned successor before integration tests')
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary) / 'kernel.sqlite'
            kernel = SuccessorKernel(MANIFEST, state)
            try:
                self.assertEqual(kernel.verify_state()['tick'], 0)
                kernel._append({'kind': 'IMPLEMENTATION_UPGRADE',
                    'predecessor_implementation_digest': kernel.implementation_identity,
                    'implementation_digest': '0' * 64})
                with self.assertRaisesRegex(ValueError, 'IMPLEMENTATION_PROVENANCE'):
                    kernel.verify_state()
            finally:
                kernel.close()
            with self.assertRaisesRegex(ValueError, 'IMPLEMENTATION_PROVENANCE'):
                SuccessorKernel(MANIFEST, state)

    def test_journal_tail_must_match_current_manifest_implementation(self):
        records = [{'kind': 'COG_RUNTIME_PROPOSE', 'implementation_identity': 'current'},
                   {'kind': 'IMPLEMENTATION_UPGRADE',
                    'predecessor_implementation_digest': 'current',
                    'implementation_digest': 'different-manifest'}]
        with self.assertRaisesRegex(ValueError, 'IMPLEMENTATION_PROVENANCE'):
            verify_implementations(records, 'current')

    def test_every_upgrade_must_follow_the_preceding_implementation(self):
        records = [{'kind': 'IMPLEMENTATION_UPGRADE',
                    'predecessor_implementation_digest': 'first', 'implementation_digest': 'second'},
                   {'kind': 'IMPLEMENTATION_UPGRADE',
                    'predecessor_implementation_digest': 'unrelated', 'implementation_digest': 'current'}]
        with self.assertRaisesRegex(ValueError, 'IMPLEMENTATION_PROVENANCE'):
            verify_implementations(records, 'current')

    def test_valid_upgrade_chain_preserves_legacy_and_runtime_history(self):
        records = [{'task': {'kind': 'logic'}, 'status': 'VERIFIED'},
                   {'kind': 'COG_RUNTIME_PROPOSE', 'implementation_identity': 'first'},
                   {'kind': 'IMPLEMENTATION_UPGRADE',
                    'predecessor_implementation_digest': 'first', 'implementation_digest': 'second'},
                   {'kind': 'COG_RUNTIME_EVALUATE', 'implementation_identity': 'second'},
                   {'kind': 'IMPLEMENTATION_UPGRADE',
                    'predecessor_implementation_digest': 'second', 'implementation_digest': 'current'},
                   {'kind': 'COG_RUNTIME_ADMIT', 'implementation_identity': 'current'}]
        before = copy.deepcopy(records)
        verify_implementations(records, 'current')
        self.assertEqual(records, before)


if __name__ == '__main__':
    unittest.main()
