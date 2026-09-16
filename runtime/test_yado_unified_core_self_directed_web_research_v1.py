import socket
import unittest

from yado_unified_core_self_directed_web_research_v1 import UnifiedYADOCoreSelfDirectedWebResearchV1


PUBLIC_IPS = {
    "html.duckduckgo.com": "93.184.216.30",
    "alpha.example.com": "93.184.216.31",
    "beta.example.net": "93.184.216.32",
}


def resolver(host, port, **kwargs):
    ip = PUBLIC_IPS.get(host)
    if not ip:
        raise socket.gaierror(host)
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port))]


def transport(target, method, timeout, max_bytes):
    host = target["host"]
    if host == "html.duckduckgo.com":
        body = b"<html><a href='https://alpha.example.com/doc'>a</a><a href='https://beta.example.net/doc'>b</a></html>"
    else:
        body = ("<html><body>alpha protocol evidence explains alpha protocol evidence with independent verification and behavior. " * 4 + "</body></html>").encode()
    return {
        "status": 200,
        "headers": {"content-type": "text/html; charset=utf-8"},
        "body": body,
        "connected_ip": target["approved_ips"][0],
    }


class UnifiedCoreSelfDirectedResearchTests(unittest.TestCase):
    def setUp(self):
        self.core = UnifiedYADOCoreSelfDirectedWebResearchV1()

    def test_audit_binds_research_without_changing_generation(self):
        report = self.core.audit()
        self.assertTrue(report["pass"], report)
        self.assertTrue(report["checks"]["self_directed_web_research_v1_bound"])
        self.assertTrue(report["checks"]["self_directed_web_research_uses_causal_prepare"])
        self.assertEqual(self.core.snapshot()["generation"], "G2_CANDIDATE_TRCG_V1")

    def test_core_runs_causal_prepare_then_reads_two_independent_hosts(self):
        result = self.core.self_directed_web_research(
            "alpha protocol evidence",
            max_sources=2,
            closure_source_target=2,
            resolver=resolver,
            transport=transport,
        )
        self.assertEqual(result["status"], "PASS_SELF_DIRECTED_WEB_RESEARCH_V1")
        self.assertEqual(result["causal_prepare"]["status"], "PASS_CAUSAL_PREPARE")
        self.assertEqual(result["comparison"]["current_independent_source_count"], 2)
        self.assertEqual(result["core_route"], self.core.RESEARCH_LAYER_ID)
        self.assertFalse(result["external_write"])
        self.assertFalse(result["private_network_access"])

    def test_research_memory_survives_export_restore(self):
        self.core.self_directed_web_research(
            "alpha protocol evidence", max_sources=2, closure_source_target=2,
            resolver=resolver, transport=transport,
        )
        state = self.core.export_self_directed_research_state()
        other = UnifiedYADOCoreSelfDirectedWebResearchV1()
        snap = other.restore_self_directed_research_state(state)
        self.assertEqual(snap["episode_count"], 1)


if __name__ == "__main__":
    unittest.main()
