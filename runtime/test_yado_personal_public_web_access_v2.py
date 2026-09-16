import socket
import unittest

import yado_personal_public_web_access_v2 as m


def public_resolver(host, port, **kwargs):
    table = {
        "example.com": ["93.184.216.34"],
        "docs.example.com": ["93.184.216.35"],
        "mixed.example.com": ["93.184.216.34", "10.0.0.7"],
        "private.example.com": ["192.168.1.4"],
    }
    if host not in table:
        raise socket.gaierror(host)
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port)) for ip in table[host]]


class PersonalPublicWebAccessTests(unittest.TestCase):
    def test_public_https_is_accepted_without_domain_allowlist(self):
        target = m.validate_public_https_url("https://example.com/path?q=1", resolver=public_resolver)
        self.assertEqual(target["host"], "example.com")
        self.assertEqual(target["approved_ips"], ["93.184.216.34"])
        self.assertEqual(target["url"], "https://example.com/path?q=1")

    def test_non_https_credentials_ports_and_local_names_fail_closed(self):
        bad = (
            "http://example.com/",
            "https://user:dummy@example.com/",
            "https://example.com:8443/",
            "https://localhost/",
            "https://service.local/",
            "https://metadata.google.internal/computeMetadata/v1/",
        )
        for url in bad:
            with self.subTest(url=url), self.assertRaises(m.PublicWebAccessError):
                m.validate_public_https_url(url, resolver=public_resolver)

    def test_private_literal_and_private_dns_are_rejected(self):
        for url in ("https://127.0.0.1/", "https://10.0.0.1/", "https://[::1]/", "https://private.example.com/"):
            with self.subTest(url=url), self.assertRaises(m.PublicWebAccessError):
                m.validate_public_https_url(url, resolver=public_resolver)

    def test_mixed_public_private_dns_is_rejected_entirely(self):
        with self.assertRaises(m.PublicWebAccessError):
            m.validate_public_https_url("https://mixed.example.com/", resolver=public_resolver)

    def test_read_only_methods_only(self):
        with self.assertRaises(m.PublicWebAccessError):
            m.fetch_public("https://example.com/", method="POST", resolver=public_resolver,
                           transport=lambda *args: None)

    def test_success_receipt_proves_bounded_read_only_transport(self):
        calls = []
        def transport(target, method, timeout, max_bytes):
            calls.append((target, method))
            return {
                "status": 200,
                "headers": {"content-type": "text/html; charset=utf-8"},
                "body": b"<html><a href='https://docs.example.com/x'>x</a></html>",
                "connected_ip": target["approved_ips"][0],
            }
        result = m.fetch_public("https://example.com/", resolver=public_resolver, transport=transport)
        receipt = result["receipt"]
        self.assertEqual(receipt["status"], "PASS_PERSONAL_PUBLIC_WEB_ACCESS_V2")
        self.assertTrue(receipt["read_only"])
        self.assertFalse(receipt["credentials_used"])
        self.assertFalse(receipt["external_write"])
        self.assertFalse(receipt["downloaded_code_executed"])
        self.assertFalse(receipt["private_network_access"])
        self.assertEqual(calls[0][0]["approved_ips"], ["93.184.216.34"])
        self.assertEqual(receipt["sha256"], m._sha256(b"<html><a href='https://docs.example.com/x'>x</a></html>"))

    def test_redirect_to_private_target_is_rejected_before_second_transport_call(self):
        calls = []
        def transport(target, method, timeout, max_bytes):
            calls.append(target["url"])
            return {
                "status": 302,
                "headers": {"location": "https://127.0.0.1/private"},
                "body": b"",
                "connected_ip": target["approved_ips"][0],
            }
        with self.assertRaises(m.PublicWebAccessError):
            m.fetch_public("https://example.com/start", resolver=public_resolver, transport=transport)
        self.assertEqual(calls, ["https://example.com/start"])

    def test_public_redirect_is_revalidated_and_followed(self):
        calls = []
        def transport(target, method, timeout, max_bytes):
            calls.append((target["host"], tuple(target["approved_ips"])))
            if target["host"] == "example.com":
                return {"status": 302, "headers": {"location": "https://docs.example.com/final"},
                        "body": b"", "connected_ip": target["approved_ips"][0]}
            return {"status": 200, "headers": {"content-type": "text/plain"},
                    "body": b"ok", "connected_ip": target["approved_ips"][0]}
        result = m.fetch_public("https://example.com/start", resolver=public_resolver, transport=transport)
        self.assertEqual(result["content"], "ok")
        self.assertEqual(len(result["receipt"]["redirects"]), 1)
        self.assertEqual(calls, [("example.com", ("93.184.216.34",)),
                                 ("docs.example.com", ("93.184.216.35",))])

    def test_non_text_response_and_oversized_body_fail_closed(self):
        def binary(target, method, timeout, max_bytes):
            return {"status": 200, "headers": {"content-type": "application/octet-stream"},
                    "body": b"abc", "connected_ip": target["approved_ips"][0]}
        with self.assertRaises(m.PublicWebAccessError):
            m.fetch_public("https://example.com/file", resolver=public_resolver, transport=binary)

        def huge(target, method, timeout, max_bytes):
            return {"status": 200, "headers": {"content-type": "text/plain"},
                    "body": b"x" * 101, "connected_ip": target["approved_ips"][0]}
        with self.assertRaises(m.PublicWebAccessError):
            m.fetch_public("https://example.com/", max_bytes=100, resolver=public_resolver, transport=huge)

    def test_discovery_filters_unsafe_links_and_is_bounded(self):
        html = """
        <a href='/relative'>relative</a>
        <a href='https://docs.example.com/doc'>doc</a>
        <a href='http://example.com/plain'>http</a>
        <a href='https://127.0.0.1/private'>private</a>
        <a href='https://docs.example.com/doc#fragment'>duplicate</a>
        """
        links = m.discover_links(html, "https://example.com/base", limit=2, resolver=public_resolver)
        self.assertEqual([x["url"] for x in links],
                         ["https://example.com/relative", "https://docs.example.com/doc"])
        self.assertTrue(all(x["policy"] == m.POLICY for x in links))

    def test_channel_snapshot_does_not_claim_write_or_private_authority(self):
        snap = m.channel_snapshot()
        self.assertFalse(snap["domain_allowlist_required"])
        self.assertTrue(snap["dns_pinned_transport"])
        self.assertFalse(snap["credentials"])
        self.assertFalse(snap["external_writes"])
        self.assertFalse(snap["private_networks"])
        self.assertFalse(snap["downloaded_code_execution"])


if __name__ == "__main__":
    unittest.main()
