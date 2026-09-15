"""Restricted synchronous client for Hivemind's file-backed stdio MCP tools.

The caller supplies the executable and an initialized tracker. Pipe I/O uses
POSIX selectors so both writes and reads share a finite deadline. No MCP tool
can launch an agent through this client.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import selectors
import signal
import subprocess
import threading
import time


ISSUE_TOOLS = frozenset({
    "hive_create_issue", "hive_get_issue", "hive_list_issues",
    "hive_add_comment", "hive_mark_acceptance", "hive_set_state",
})
PROTOCOL_VERSION = "2024-11-05"


class HivemindError(RuntimeError):
    """The subprocess, MCP protocol, or requested issue operation failed."""


class HivemindClient:
    def __init__(self, argv, tracker_root, *, timeout=30.0, actor="yado",
                 env=None, max_response_bytes=1_048_576):
        if isinstance(argv, (str, bytes)):
            raise ValueError("argv must be an explicit argument sequence")
        self.argv = tuple(os.fspath(arg) for arg in argv)
        if not self.argv or any(not isinstance(arg, str) or not arg for arg in self.argv):
            raise ValueError("argv must contain nonempty strings")
        self.tracker_root = Path(tracker_root).resolve()
        if not (self.tracker_root / "config.yaml").is_file():
            raise ValueError("tracker_root must contain an initialized config.yaml")
        self.timeout = float(timeout)
        if not math.isfinite(self.timeout) or self.timeout <= 0:
            raise ValueError("timeout must be finite and positive")
        if type(max_response_bytes) is not int or max_response_bytes <= 0:
            raise ValueError("max_response_bytes must be a positive integer")
        if not isinstance(actor, str) or not actor or any(c.isspace() for c in actor):
            raise ValueError("actor must be a nonempty token without whitespace")
        self.max_response_bytes = max_response_bytes
        overrides = dict(env or {})
        self._env = os.environ.copy()
        self._env.update(overrides)
        # MCP issue calls register their workspace. Keep the default registry
        # local even when the parent process has a global XDG_CONFIG_HOME.
        self._env["XDG_CONFIG_HOME"] = overrides.get("XDG_CONFIG_HOME") or str(
            self.tracker_root / ".client-config")
        self._env["HIVE_ROOT"] = str(self.tracker_root)
        self._env["HIVE_AGENT_ID"] = actor
        for key in ("HIVE_HCP_SOCK", "HCP_TOKEN", "HIVEMIND_TILE"):
            self._env.pop(key, None)
        self._lock = threading.Lock()
        self._process = None
        self._buffer = bytearray()
        self._stderr = bytearray()
        self._next_id = 0
        self.server_info = None

    def __enter__(self):
        with self._lock:
            if self._process is not None:
                raise HivemindError("client is already open")
            self._buffer.clear()
            self._stderr.clear()
            self.server_info = None
            try:
                self._process = subprocess.Popen(
                    self.argv, cwd=self.tracker_root.parent, env=self._env,
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, bufsize=0, shell=False,
                    start_new_session=True,
                )
                for stream in (self._process.stdin, self._process.stdout,
                               self._process.stderr):
                    os.set_blocking(stream.fileno(), False)
                result = self._request("initialize", {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "yado-hivemind", "version": "1"},
                })
                if not isinstance(result, dict) or result.get("protocolVersion") != PROTOCOL_VERSION:
                    raise HivemindError("server did not negotiate the supported MCP version")
                info = result.get("serverInfo")
                capabilities = result.get("capabilities")
                if (not isinstance(info, dict) or info.get("name") != "hive"
                        or not isinstance(capabilities, dict) or "tools" not in capabilities):
                    raise HivemindError("server is not the expected Hivemind tool server")
                self.server_info = dict(info)
                self._exchange({"jsonrpc": "2.0", "method": "notifications/initialized"})
            except OSError as exc:
                self._shutdown()
                raise HivemindError(f"could not start Hivemind: {exc}") from exc
            except BaseException:
                self._shutdown()
                raise
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self):
        with self._lock:
            self._shutdown()

    def call(self, tool, arguments):
        if tool not in ISSUE_TOOLS:
            raise HivemindError(f"tool is not allowed: {tool}")
        if not isinstance(arguments, dict):
            raise ValueError("tool arguments must be an object")
        if not self._lock.acquire(timeout=self.timeout):
            raise HivemindError("timed out waiting for the active MCP call")
        try:
            if self._process is None or self.server_info is None:
                raise HivemindError("client is not open; use it as a context manager")
            result = self._request("tools/call", {"name": tool, "arguments": arguments})
            if not isinstance(result, dict):
                raise HivemindError("MCP tool result is not an object")
            content = result.get("content")
            if not isinstance(content, list):
                raise HivemindError("MCP tool result has no content array")
            blocks = [part["text"] for part in content
                      if isinstance(part, dict) and part.get("type") == "text"
                      and isinstance(part.get("text"), str)]
            if result.get("isError"):
                raise HivemindError("Hivemind tool error: " + "\n".join(blocks))
            if len(content) != 1 or len(blocks) != 1:
                raise HivemindError("expected one JSON text block from Hivemind")
            try:
                return json.loads(blocks[0])
            except (ValueError, RecursionError) as exc:
                raise HivemindError("Hivemind returned invalid tool JSON") from exc
        finally:
            self._lock.release()

    def _request(self, method, params):
        self._next_id += 1
        message = self._exchange({"jsonrpc": "2.0", "id": self._next_id,
                                  "method": method, "params": params}, self._next_id)
        if ("error" in message) == ("result" in message):
            raise HivemindError("invalid JSON-RPC result/error envelope")
        if "error" in message:
            error = message["error"]
            if isinstance(error, dict):
                raise HivemindError(f"MCP error {error.get('code')}: {error.get('message')}")
            raise HivemindError("invalid JSON-RPC error envelope")
        return message["result"]

    def _exchange(self, message, request_id=None):
        payload = json.dumps(message, ensure_ascii=False, separators=(",", ":"),
                             allow_nan=False).encode("utf-8") + b"\n"
        if len(payload) > self.max_response_bytes:
            raise HivemindError("MCP request exceeds the configured byte limit")
        process = self._process
        deadline = time.monotonic() + self.timeout
        received = len(self._buffer)
        sent = 0
        selector = selectors.DefaultSelector()
        try:
            selector.register(process.stdin, selectors.EVENT_WRITE, "stdin")
            selector.register(process.stdout, selectors.EVENT_READ, "stdout")
            selector.register(process.stderr, selectors.EVENT_READ, "stderr")
            while True:
                if sent == len(payload) and request_id is None:
                    return None
                while b"\n" in self._buffer:
                    line, _, remaining = self._buffer.partition(b"\n")
                    self._buffer = bytearray(remaining)
                    if not line.strip():
                        continue
                    try:
                        response = json.loads(line)
                    except (ValueError, UnicodeError, RecursionError) as exc:
                        raise HivemindError("invalid JSON on MCP stdout") from exc
                    if not isinstance(response, dict) or response.get("jsonrpc") != "2.0":
                        raise HivemindError("invalid JSON-RPC message on MCP stdout")
                    if "id" not in response and isinstance(response.get("method"), str):
                        continue  # Notifications do not complete a request.
                    if ("method" in response or type(response.get("id")) is not int
                            or response["id"] != request_id):
                        raise HivemindError("unexpected request or response id from MCP server")
                    return response
                remaining_time = deadline - time.monotonic()
                if remaining_time <= 0:
                    raise HivemindError("MCP exchange timed out")
                for key, _ in selector.select(remaining_time):
                    stream = key.fileobj
                    if key.data == "stdin":
                        try:
                            sent += os.write(stream.fileno(), payload[sent:sent + 65536])
                        except BlockingIOError:
                            continue
                        if sent == len(payload):
                            selector.unregister(stream)
                        continue
                    try:
                        chunk = os.read(stream.fileno(), 65536)
                    except BlockingIOError:
                        continue
                    if not chunk:
                        selector.unregister(stream)
                        if key.data == "stdout":
                            raise HivemindError("MCP subprocess closed stdout before responding")
                    elif key.data == "stderr":
                        self._stderr.extend(chunk)
                        del self._stderr[:-8192]
                    else:
                        received += len(chunk)
                        if received > self.max_response_bytes:
                            raise HivemindError("MCP response exceeds the configured byte limit")
                        self._buffer.extend(chunk)
        except BaseException as exc:
            # After an interrupted request, a late reply must never be treated
            # as the response to another call, and a mutation must not replay.
            self._shutdown()
            if isinstance(exc, OSError):
                raise HivemindError(f"MCP pipe failure: {exc}") from exc
            raise
        finally:
            selector.close()

    def _shutdown(self):
        process, self._process = self._process, None
        if process is None:
            return
        try:
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=min(self.timeout, 1.0))
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait(timeout=1.0)
        finally:
            for stream in (process.stdin, process.stdout, process.stderr):
                stream.close()
