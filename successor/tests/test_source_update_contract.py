"""Explicit runtime upgrades preserve exact pins and reject unrelated drift."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from successor import __main__ as cli
from successor.archive import canonical, file_sha, sha
from successor.continuity import verify_source_transition


class SourceUpdateContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root/'runtime').mkdir()
        (self.root/'successor').mkdir()
        self.source = self.root/'runtime/example.py'
        self.source.write_text('VALUE = 1\n')
        archive = self.root/'experience.sqlite'
        archive.write_bytes(b'fixture for the byte-pinning boundary; not a runtime database')
        self.parent = {'archive_file': archive.name, 'archive_sha256': file_sha(archive),
                       'inherited_files': {'runtime/example.py': file_sha(self.source)}}
        self.parent['identity_digest'] = sha(canonical(self.parent).encode())
        self.manifest = self.root/'parent.json'
        self.manifest.write_text(json.dumps(self.parent))
        self.source.write_text('VALUE = 2\n')
        self.updates = {'runtime/example.py': {
            'previous_sha256': self.parent['inherited_files']['runtime/example.py'],
            'current_sha256': file_sha(self.source)}}
        self.root_patch = patch.object(cli, 'ROOT', self.root)
        self.root_patch.start()

    def tearDown(self):
        self.root_patch.stop()
        self.tmp.cleanup()

    def test_unlisted_source_drift_still_fails_without_creating_an_output(self):
        out = self.root/'rejected'
        with self.assertRaisesRegex(ValueError, 'PARENT_SOURCE_DRIFT'):
            cli.derive(self.manifest, out)
        self.assertFalse(out.exists())

    def test_exact_transition_changes_only_declared_pins_and_preserves_predecessor(self):
        before = self.manifest.read_bytes()
        out = self.root/'upgrade'
        cli.derive(self.manifest, out, source_updates=self.updates)
        current = json.loads((out/'manifest.json').read_text())
        self.assertEqual(current['inherited_source_updates'], self.updates)
        self.assertEqual(current['inherited_files']['runtime/example.py'], file_sha(self.source))
        self.assertEqual((out/'predecessor-manifest.json').read_bytes(), before)
        self.assertEqual(self.manifest.read_bytes(), before)
        self.assertEqual((out/'experience.sqlite').read_bytes(), (self.root/'experience.sqlite').read_bytes())
        verify_source_transition(current, self.parent)
        changed = copy.deepcopy(current)
        changed['inherited_source_updates']['runtime/example.py']['previous_sha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'SOURCE_UPDATE_BINDING'):
            verify_source_transition(changed, self.parent)

    def test_missing_extra_wrong_predecessor_or_wrong_current_pin_is_rejected(self):
        wrong_old, wrong_new = copy.deepcopy(self.updates), copy.deepcopy(self.updates)
        wrong_old['runtime/example.py']['previous_sha256'] = '0'*64
        wrong_new['runtime/example.py']['current_sha256'] = '0'*64
        values = [{}, wrong_old, wrong_new, {**self.updates, '../outside.py': self.updates['runtime/example.py']}]
        for index, update in enumerate(values):
            with self.subTest(update=index):
                out = self.root/f'rejected-{index}'
                with self.assertRaisesRegex(ValueError, 'SOURCE_UPDATE_SET_MISMATCH'):
                    cli.derive(self.manifest, out, source_updates=update)
                self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
