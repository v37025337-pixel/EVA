import socket
import unittest

from yado_unified_core_personal_web_v2 import UnifiedYADOCorePersonalWebV2


def resolver(host, port, **kwargs):
    table = {
        "seed.example.com": ["93.184.216.34"],
        "next.example.com": ["93.184.216.35"],
    }
    if host not in table:
        raise socket.gaierror(host)
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port)) for ip in table[host]]


def transport(target, method, timeout, max_bytes):
    if target["host"] == "seed.example.com":
        body = b"<html><a href='https://next.example.com/page'>next</a><a href='https://127.0.0.1/private'>bad</a></html>"
    else:
        body = b"<html><body>second public page</body></html>"
    return {
        "status": 200,
        "headers": {"content-type": "text/html; charset=utf-8"},
        "body": body,
        "connected_ip": target["approved_ips"][0],
    }


class UnifiedCorePersonalWebV2Tests(unittest.TestCase):
    def setUp(self):
        self.core = UnifiedYADOCorePersonalWebV2()

    def test_core_audit_binds_broad_readonly_channel(self):
        report = self.core.audit()
        self.assertTrue(report["pass"], report)
        self.assertTrue(report["checks"]["personal_public_web_access_v2_bound"])
        self.assertTrue(report["checks"]["personal_public_web_public_only"])
        self.assertTrue(report["checks"]["personal_public_web_read_only"])
        self.assertTrue(report["checks"]["personal_public_web_dns_pinned"])

    def test_core_fetch_routes_through_new_transport_without_allowlist(self):
        result = self.core.public_web_fetch(
            "https://seed.example.com/",
            resolver=resolver,
            transport=transport,
        )
        self.assertEqual(result["core_route"], self.core.ACCESS_LAYER_ID)
        self.assertEqual(result["receipt"]["status"], "PASS_PERSONAL_PUBLIC_WEB_ACCESS_V2")
        self.assertFalse(result["receipt"]["credentials_used"])
        self.assertFalse(result["receipt"]["external_write"])

    def test_core_bounded_explore_follows_public_discovery_only(self):
        result = self.core.public_web_explore(
            "https://seed.example.com/",
            max_pages=2,
            resolver=resolver,
            transport=transport,
        )
        self.assertEqual(result["status"], "PASS_BOUNDED_PUBLIC_WEB_EXPLORATION_V2")
        self.assertEqual(result["page_count"], 2)
        self.assertEqual(result["hosts"], ["next.example.com", "seed.example.com"])
        self.assertFalse(result["credentials_used"])
        self.assertFalse(result["private_network_access"])
        self.assertFalse(result["external_write"])

    def test_snapshot_preserves_g2_and_exposes_access_layer(self):
        snap = self.core.snapshot()
        self.assertEqual(snap["generation"], "G2_CANDIDATE_TRCG_V1")
        self.assertEqual(snap["access_layer_id"], self.core.ACCESS_LAYER_ID)
        self.assertFalse(snap["personal_public_web"]["automatic_canonical_mutation"])


if __name__ == "__main__":
    unittest.main()
