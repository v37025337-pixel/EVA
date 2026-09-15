import io
from email.message import Message
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request
import urllib.response

import yado_database_api_transfer_repair_v1 as database
import yado_endogenous_data_invariant_repair_v1 as endogenous
import yado_multi_resource_self_directed_data_task_loop_v1 as multi


class PublicDataTransportTests(unittest.TestCase):
    def test_redirect_is_rejected_before_contacting_another_host(self):
        for module in (database, endogenous, multi):
            source = "https://jsonplaceholder.typicode.com/todos"
            requests = []

            def respond(request, **kwargs):
                requests.append(request.full_url)
                headers = Message()
                redirect = request.full_url == source
                if redirect:
                    headers["Location"] = "https://example.invalid/private"
                response = urllib.response.addinfourl(io.BytesIO(b"[]"), headers, request.full_url, 302 if redirect else 200)
                response.msg = "Found" if redirect else "OK"
                return response

            with self.subTest(module=module.__name__), patch.object(urllib.request.HTTPSHandler, "https_open", side_effect=respond):
                with self.assertRaises(urllib.error.HTTPError):
                    module.fetch_json(source)
                self.assertEqual(requests, [source])

    def test_credential_urls_and_nonstandard_ports_are_rejected_before_transport(self):
        for module in (database, endogenous, multi):
            for url in ("https://user:dummy@jsonplaceholder.typicode.com/todos", "https://jsonplaceholder.typicode.com:8443/todos"):
                with self.subTest(module=module.__name__, url=url), patch.object(urllib.request.HTTPSHandler, "https_open") as transport:
                    with self.assertRaises(ValueError):
                        module.fetch_json(url)
                    transport.assert_not_called()


if __name__ == "__main__":
    unittest.main()
