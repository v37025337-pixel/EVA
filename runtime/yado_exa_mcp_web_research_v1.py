from __future__ import annotations

"""Read-only Exa MCP bridge for YADO.

This module binds Exa's hosted MCP contract to the existing YADO research
pipeline. It does not execute returned code, write to Exa, mutate canonical
state, or store credentials. A transport is injected so deployment controls
DNS/TLS, rate limits, and authentication outside the kernel.
"""

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any, Callable, Mapping

SCHEMA = "yado.exa_mcp_web_research.v1"
DEFAULT_ENDPOINT = "https://mcp.exa.ai/mcp"
ALLOWED_TOOLS = frozenset({"web_search_exa", "web_fetch_exa"})
PROTOCOL_VERSION = "2025-06-18"


class ExaMCPError(ValueError):
    pass


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")
    ).hexdigest()


def _validate_endpoint(endpoint: str) -> str:
    value = str(endpoint or "").strip()
    if not value.startswith("https://"):
        raise ExaMCPError("EXA_MCP_HTTPS_REQUIRED")
    if value.rstrip("/") != DEFAULT_ENDPOINT.rstrip("/") and not value.startswith(DEFAULT_ENDPOINT + "?"):
        raise ExaMCPError("EXA_MCP_ENDPOINT_NOT_ALLOWLISTED")
    return value


def _jsonrpc_request(request_id: int, method: str, params: Mapping[str, Any] | None = None) -> dict[str, Any]:
    body = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        body["params"] = dict(params)
    return body


def _decode_response(response: Any) -> dict[str, Any]:
    if isinstance(response, dict):
        payload = response
    elif isinstance(response, (bytes, bytearray)):
        payload = json.loads(bytes(response).decode("utf-8"))
    elif isinstance(response, str):
        lines = [line[5:].strip() for line in response.splitlines() if line.startswith("data:")]
        payload = json.loads(lines[-1] if lines else response)
    else:
        raise ExaMCPError("EXA_MCP_RESPONSE_FORMAT_UNSUPPORTED")
    if not isinstance(payload, dict):
        raise ExaMCPError("EXA_MCP_RESPONSE_OBJECT_REQUIRED")
    if "error" in payload:
        raise ExaMCPError("EXA_MCP_JSONRPC_ERROR:" + str(payload["error"])[:300])
    return payload


@dataclass(frozen=True)
class ExaMCPConfig:
    endpoint: str = DEFAULT_ENDPOINT
    api_key_env: str = "EXA_API_KEY"
    timeout: float = 20.0
    max_results: int = 8

    def validated(self) -> "ExaMCPConfig":
        endpoint = _validate_endpoint(self.endpoint)
        if not 1 <= int(self.max_results) <= 20:
            raise ExaMCPError("EXA_MCP_RESULT_BUDGET")
        if not 0 < float(self.timeout) <= 60:
            raise ExaMCPError("EXA_MCP_TIMEOUT")
        return ExaMCPConfig(endpoint, str(self.api_key_env), float(self.timeout), int(self.max_results))


class ExaMCPClient:
    """Minimal MCP initialize/tools/call client over an injected HTTPS transport.

    request(payload, endpoint, headers, timeout) must perform one HTTPS POST and
    return a JSON object or an MCP JSON/SSE response body. The kernel never
    persists the API key and never accepts arbitrary tool names.
    """

    def __init__(
        self,
        request: Callable[[dict[str, Any], str, dict[str, str], float], Any],
        *,
        config: ExaMCPConfig | None = None,
        api_key: str | None = None,
    ):
        self.config = (config or ExaMCPConfig()).validated()
        self._request = request
        self._api_key = api_key if api_key is not None else os.environ.get(self.config.api_key_env)
        self._session_id: str | None = None
        self._next_id = 1
        self._initialized = False

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }
        if self._api_key:
            headers["x-api-key"] = self._api_key
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        return headers

    def _call(self, method: str, params: Mapping[str, Any] | None = None) -> dict[str, Any]:
        request_id = self._next_id
        self._next_id += 1
        payload = _jsonrpc_request(request_id, method, params)
        response = self._request(payload, self.config.endpoint, self._headers(), self.config.timeout)
        if isinstance(response, dict) and response.get("session_id"):
            self._session_id = str(response["session_id"])
        return _decode_response(response)

    def _notify(self, method: str, params: Mapping[str, Any] | None = None) -> None:
        payload = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = dict(params)
        self._request(payload, self.config.endpoint, self._headers(), self.config.timeout)

    def connect(self) -> dict[str, Any]:
        if self._initialized:
            return {"status": "ALREADY_CONNECTED", "endpoint": self.config.endpoint}
        response = self._call(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "YADO-Exa-MCP-Bridge", "version": "1.0"},
            },
        )
        self._notify("notifications/initialized")
        self._initialized = True
        return {
            "status": "PASS_EXA_MCP_CONNECTED",
            "endpoint": self.config.endpoint,
            "server_result_digest": _digest(response.get("result", {})),
            "read_only": True,
            "credentials_used": bool(self._api_key),
            "external_write": False,
            "downloaded_code_executed": False,
        }

    def list_tools(self) -> dict[str, Any]:
        self.connect()
        response = self._call("tools/list")
        names = []
        for item in (response.get("result") or {}).get("tools") or []:
            if isinstance(item, dict) and isinstance(item.get("name"), str):
                names.append(item["name"])
        return {"status": "PASS_EXA_MCP_TOOLS_LISTED", "tools": sorted(names), "allowed_tools": sorted(ALLOWED_TOOLS)}

    def call_tool(self, name: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        if name not in ALLOWED_TOOLS:
            raise ExaMCPError("EXA_MCP_TOOL_NOT_ALLOWED")
        self.connect()
        response = self._call("tools/call", {"name": name, "arguments": dict(arguments)})
        result = response.get("result") or {}
        return {
            "schema": SCHEMA,
            "status": "PASS_EXA_MCP_TOOL_CALL",
            "tool": name,
            "result": result,
            "result_digest": _digest(result),
            "read_only": True,
            "credentials_used": bool(self._api_key),
            "external_write": False,
            "downloaded_code_executed": False,
            "automatic_canonical_mutation": False,
        }

    def search(self, query: str, *, max_results: int | None = None) -> dict[str, Any]:
        text = " ".join(str(query or "").split()).strip()
        if not text:
            raise ExaMCPError("EXA_MCP_QUERY_REQUIRED")
        limit = int(max_results or self.config.max_results)
        if not 1 <= limit <= 20:
            raise ExaMCPError("EXA_MCP_RESULT_BUDGET")
        return self.call_tool("web_search_exa", {"query": text, "numResults": limit})

    def fetch(self, urls: list[str]) -> dict[str, Any]:
        clean = [str(url).strip() for url in urls if str(url).strip()]
        if not clean or len(clean) > 20 or any(not url.startswith("https://") for url in clean):
            raise ExaMCPError("EXA_MCP_HTTPS_URLS_REQUIRED")
        return self.call_tool("web_fetch_exa", {"urls": clean})

    def snapshot(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "status": "SHADOW_READY_EXA_MCP_READ_ONLY",
            "endpoint": self.config.endpoint,
            "allowed_tools": sorted(ALLOWED_TOOLS),
            "transport_injected": True,
            "credentials_from_environment_only": True,
            "external_writes": False,
            "downloaded_code_executed": False,
            "automatic_canonical_mutation": False,
        }


__all__ = ["ALLOWED_TOOLS", "DEFAULT_ENDPOINT", "ExaMCPClient", "ExaMCPConfig", "ExaMCPError"]
