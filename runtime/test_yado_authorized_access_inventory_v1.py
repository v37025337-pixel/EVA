import os
import tempfile
import unittest
from pathlib import Path

import yado_authorized_access_inventory_v1 as inv


class AuthorizedAccessInventoryTests(unittest.TestCase):
    def test_extracts_secret_names_without_values(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / '.github/workflows').mkdir(parents=True)
            (root / '.github/workflows/test.yml').write_text(
                "env:\n  TOKEN: ${{ secrets.TEST_API_TOKEN }}\n",
                encoding='utf-8',
            )
            old_roots = inv.SCAN_ROOTS
            inv.SCAN_ROOTS = ('.github/workflows',)
            try:
                os.environ['TEST_API_TOKEN'] = 'DO_NOT_EXPOSE_VALUE'
                refs = inv.find_credential_references(root)
            finally:
                inv.SCAN_ROOTS = old_roots
                os.environ.pop('TEST_API_TOKEN', None)
            self.assertEqual(refs[0]['name'], 'TEST_API_TOKEN')
            self.assertTrue(refs[0]['configured_in_current_process'])
            self.assertFalse(refs[0]['value_exposed'])
            self.assertNotIn('DO_NOT_EXPOSE_VALUE', repr(refs))

    def test_report_never_enables_bypass(self):
        report = inv.build_report(inv.ROOT)
        self.assertFalse(report['policy']['credential_value_capture'])
        self.assertFalse(report['policy']['credential_guessing'])
        self.assertFalse(report['policy']['credential_bypass'])
        self.assertFalse(report['policy']['secret_values_exposed'])

    def test_public_execution_resources_registered(self):
        ids = {x['id'] for x in inv.PUBLIC_ACCESS}
        self.assertIn('judge0_ce', ids)
        self.assertIn('runlet', ids)

    def test_mailru_profile_uses_names_only(self):
        profile = next(x for x in inv.KNOWN_PROTECTED_ACCESS if x['id'] == 'mailru_webdav')
        self.assertEqual(profile['required_env'], ['YADO_MAILRU_USER', 'YADO_MAILRU_APP_PASSWORD'])
        self.assertNotIn('password_value', profile)


if __name__ == '__main__':
    unittest.main()
