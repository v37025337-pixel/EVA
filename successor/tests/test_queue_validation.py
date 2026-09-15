import os
from pathlib import Path
import tempfile
import unittest

from successor.kernel import SuccessorKernel


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = Path(os.environ.get('YADO_SUCCESSOR_TEST_MANIFEST', ROOT / 'successor/state/birth-v2/manifest.json'))


class QueueValidationTests(unittest.TestCase):
    def test_malformed_batch_is_atomic_and_does_not_block_later_work(self):
        if not MANIFEST.exists():
            self.skipTest('Build the pinned successor before integration tests')
        valid = {'kind': 'logic', 'payload': {'relation': [[1, 2], [2, 3]], 'start': 1},
                 'expect': {'path': ['result'], 'equals': [1, 2, 3]}}
        malformed = (None, [], {'kind': 'logic', 'payload': None},
                     {'kind': 'logic', 'payload': []})
        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary) / 'kernel.sqlite'
            kernel = SuccessorKernel(MANIFEST, state)
            try:
                for invalid in malformed:
                    with self.subTest(invalid=invalid):
                        before = kernel.verify_state()
                        with self.assertRaisesRegex(ValueError, 'TASK_AND_PAYLOAD_MUST_BE_OBJECTS'):
                            kernel.submit('invalid mixed batch', [valid, invalid, valid])
                        self.assertEqual(kernel.verify_state(), before)
                        self.assertEqual(kernel.snapshot()['jobs'], {})
                job_ids = kernel.submit('valid continuation', [valid])
            finally:
                kernel.close()
            kernel = SuccessorKernel(MANIFEST, state)
            try:
                results = kernel.resume(5)
                self.assertEqual([row['job_id'] for row in results], job_ids)
                self.assertEqual([row['status'] for row in results], ['VERIFIED'])
                self.assertEqual(kernel.snapshot()['jobs'], {'VERIFIED': 1})
            finally:
                kernel.close()


if __name__ == '__main__':
    unittest.main()
