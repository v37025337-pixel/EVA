import unittest

from yado_exa_mcp_web_research_v1 import ExaMCPClient, ExaMCPConfig, ExaMCPError


class FakeTransport:
    def __init__(self):
        self.calls = []

    def __call__(self, payload, endpoint, headers, timeout):
        self.calls.append((payload, endpoint, headers, timeout))
        method = payload["method"]
        if method == "initialize":
            return {"jsonrpc": "2.0", "id": payload["id"], "result": {"serverInfo": {"name": "fake-exa"}}}
        if method == "notifications/initialized":
            return {}
        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": payload["id"], "result": {"tools": [{"name": "web_search_exa"}, {"name": "web_fetch_exa"}]}}
        if method == "tools/call":
            args = payload["params"]["arguments"]
            return {"jsonrpc": "2.0", "id": payload["id"], "result": {"content": [{"type": "text", "text": str(args)}]}}
        raise AssertionError(method)


class ExaMCPBridgeTests(unittest.TestCase):
    def test_connect_list_search_fetch_are_read_only(self):
        transport = FakeTransport()
        client = ExaMCPClient(transport, config=ExaMCPConfig())
        connected = client.connect()
        self.assertEqual(connected["status"], "PASS_EXA_MCP_CONNECTED")
        listed = client.list_tools()
        self.assertEqual(listed["tools"], ["web_fetch_exa", "web_search_exa"])
        search = client.search("Ghidra information lineage", max_results=3)
        fetch = client.fetch(["https://example.com/"])
        self.assertEqual(search["tool"], "web_search_exa")
        self.assertEqual(fetch["tool"], "web_fetch_exa")
        self.assertTrue(search["read_only"])
        self.assertFalse(search["external_write"])
        self.assertFalse(fetch["downloaded_code_executed"])
        self.assertEqual(len(transport.calls), 5)

    def test_endpoint_and_tool_guards(self):
        transport = FakeTransport()
        with self.assertRaises(ExaMCPError):
            ExaMCPClient(transport, config=ExaMCPConfig(endpoint="http://mcp.exa.ai/mcp"))
        client = ExaMCPClient(transport)
        with self.assertRaises(ExaMCPError):
            client.call_tool("agent_run", {"query": "x"})
        with self.assertRaises(ExaMCPError):
            client.fetch(["http://example.com/"])

    def test_api_key_is_not_in_payload(self):
        transport = FakeTransport()
        client = ExaMCPClient(transport, api_key="secret")
        client.connect()
        payload, _, headers, _ = transport.calls[0]
        self.assertNotIn("secret", payload)
        self.assertEqual(headers["x-api-key"], "secret")
        self.assertEqual(client.snapshot()["credentials_from_environment_only"], True)


if __name__ == "__main__":
    unittest.main()
