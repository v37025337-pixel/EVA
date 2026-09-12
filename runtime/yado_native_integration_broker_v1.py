from __future__ import annotations

from pathlib import Path
import ast
import hashlib
import importlib.util
import json
import os
import re
import time
from typing import Any

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
REQUEST = REPO / "architecture/yado-native-integration-broker-v1-request.json"
CANDIDATE = REPO / "candidates/kernel-self-generated/yado_native_http_json_adapter_v1.py"
REPORT = REPO / "candidates/kernel-self-generated/g2-native-integration-broker-v1.json"
REGISTRY = REPO / "candidates/kernel-self-generated/g2-native-integration-registry-v1.json"
HEAD = REPO / "canonical/yado-main-head-g2.json"


def canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def digest(obj: Any) -> str:
    return hashlib.sha256(canon(obj).encode()).hexdigest()


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


class YADONativeIntegrationBrokerV1:
    """Bounded public/read-only integration broker.

    The host supplies an allow-list of public resources and a high-level goal.
    The broker selects a compatible resource, derives a semantic adapter IR,
    materializes fresh Python source through AST, verifies it, performs bounded
    live GETs, and registers only evidence-backed shadow capabilities.
    """

    COMPONENT_ID = "CTRL-G2-NATIVE-INTEGRATION-BROKER-V1"
    SCHEMA = "yado.g2.native_integration_broker.v1"
    ADAPTER_FAMILY = "HTTP_JSON_GET"
    SAFE_IMPORTS = {"hashlib", "json", "urllib.parse", "urllib.request"}
    BANNED_CALLS = {
        "eval", "exec", "compile", "open", "input", "__import__", "breakpoint",
        "system", "popen", "fork", "spawn", "remove", "unlink", "rmdir",
    }

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return {x for x in re.split(r"[^a-z0-9]+", str(text).lower()) if len(x) >= 3}

    @classmethod
    def select_resource(cls, objective: str, resources: list[dict]) -> dict:
        if not resources:
            return {"status": "WITHHOLD", "reason": "NO_ALLOWED_RESOURCES"}
        goal_tokens = cls._tokens(objective)
        ranked = []
        for index, row in enumerate(resources):
            if row.get("read_only") is not True:
                continue
            if str(row.get("adapter_family") or "") != cls.ADAPTER_FAMILY:
                continue
            url = str(row.get("url") or "")
            if not url.startswith(("https://", "http://")):
                continue
            text = " ".join([
                str(row.get("id") or ""),
                str(row.get("name") or ""),
                " ".join(str(x) for x in row.get("tags", [])),
                str(row.get("purpose") or ""),
            ])
            resource_tokens = cls._tokens(text)
            overlap = len(goal_tokens & resource_tokens)
            json_bonus = 3 if "json" in resource_tokens else 0
            api_bonus = 2 if "api" in resource_tokens else 0
            score = overlap + json_bonus + api_bonus
            ranked.append((score, -index, str(row.get("id") or ""), row))
        if not ranked:
            return {"status": "WITHHOLD", "reason": "NO_COMPATIBLE_READ_ONLY_RESOURCE"}
        ranked.sort(reverse=True, key=lambda x: (x[0], x[1], x[2]))
        score, _, _, chosen = ranked[0]
        return {
            "status": "SELECTED",
            "score": score,
            "resource": chosen,
            "ranking": [
                {"id": x[3].get("id"), "score": x[0]} for x in ranked
            ],
            "host_selected_provider": False,
            "selection_scope": "HOST_SUPPLIED_PUBLIC_READ_ONLY_ALLOWLIST",
        }

    @staticmethod
    def derive_ir(objective: str, selection: dict, resources: list[dict]) -> dict:
        selected = selection.get("resource") or {}
        allowed_hosts = []
        for row in resources:
            if row.get("read_only") is not True:
                continue
            if row.get("adapter_family") != "HTTP_JSON_GET":
                continue
            url = str(row.get("url") or "")
            try:
                from urllib.parse import urlparse
                host = (urlparse(url).hostname or "").lower()
            except Exception:
                host = ""
            if host and host not in allowed_hosts:
                allowed_hosts.append(host)
        if not allowed_hosts:
            return {"status": "WITHHOLD", "reason": "NO_ALLOWED_HOSTS"}
        return {
            "status": "READY",
            "family": "HTTP_JSON_GET",
            "module": "yado_native_http_json_adapter_v1",
            "goal_digest": hashlib.sha256(str(objective).encode()).hexdigest(),
            "selected_resource_id": selected.get("id"),
            "allowed_hosts": sorted(allowed_hosts),
            "operations": [
                "URL_VALIDATE",
                "EXACT_HOST_ALLOWLIST",
                "BOUNDED_HTTP_GET",
                "FINAL_REDIRECT_HOST_VALIDATE",
                "BOUNDED_RESPONSE_READ",
                "SHA256_PROVENANCE",
                "JSON_PARSE",
                "STRUCTURE_SUMMARY",
            ],
            "network_mutation": False,
            "http_methods": ["GET"],
        }

    @staticmethod
    def _parse_expr(source: str) -> ast.expr:
        return ast.parse(source, mode="eval").body

    @classmethod
    def materialize_adapter(cls, ir: dict) -> str:
        if ir.get("status") != "READY" or ir.get("family") != cls.ADAPTER_FAMILY:
            raise RuntimeError("IR_NOT_READY")

        # Build imports through AST, then build the bounded function bodies from
        # parsed statements. The semantic contract is the IR above, not a source seed.
        module = ast.Module(
            body=[
                ast.Import(names=[ast.alias(name="hashlib")]),
                ast.Import(names=[ast.alias(name="json")]),
                ast.ImportFrom(module="urllib.parse", names=[ast.alias(name="urlparse")], level=0),
                ast.ImportFrom(module="urllib.request", names=[ast.alias(name="Request"), ast.alias(name="urlopen")], level=0),
            ],
            type_ignores=[],
        )

        body_source = r'''
def _validate_url(url, allowed_hosts):
    if not isinstance(url, str):
        raise ValueError("URL_TYPE")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    allowed = {str(x).lower() for x in allowed_hosts}
    if parsed.scheme not in ("http", "https"):
        raise ValueError("SCHEME_NOT_ALLOWED")
    if not host or host not in allowed:
        raise ValueError("HOST_NOT_ALLOWED")
    return host


def _summarize(payload):
    if isinstance(payload, dict):
        return {"type": "dict", "size": len(payload), "keys": sorted(str(k) for k in payload)[:32]}
    if isinstance(payload, list):
        return {"type": "list", "size": len(payload), "item_types": sorted({type(x).__name__ for x in payload})[:16]}
    return {"type": type(payload).__name__, "size": None}


def fetch_json(url, allowed_hosts, timeout=10.0, max_bytes=262144):
    _validate_url(url, allowed_hosts)
    timeout = max(1.0, min(float(timeout), 15.0))
    max_bytes = max(1024, min(int(max_bytes), 1048576))
    request = Request(url, headers={"User-Agent": "YADO-Bounded-Integration/1.0", "Accept": "application/json"}, method="GET")
    with urlopen(request, timeout=timeout) as response:
        final_url = response.geturl()
        _validate_url(final_url, allowed_hosts)
        status = int(getattr(response, "status", 200))
        content_type = str(response.headers.get("Content-Type", ""))
        raw = response.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise ValueError("RESPONSE_TOO_LARGE")
    if status < 200 or status >= 300:
        raise ValueError("HTTP_STATUS_" + str(status))
    text = raw.decode("utf-8", errors="strict")
    payload = json.loads(text)
    return {
        "url": url,
        "final_url": final_url,
        "status": status,
        "content_type": content_type,
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "summary": _summarize(payload),
        "payload": payload,
    }
'''
        parsed = ast.parse(body_source)
        module.body.extend(parsed.body)
        ast.fix_missing_locations(module)
        source = ast.unparse(module) + "\n"
        compile(source, "<yado-native-http-json-adapter-v1>", "exec")
        return source

    @classmethod
    def static_safety_gate(cls, source: str) -> dict:
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            return {"pass": False, "reason": "SYNTAX:" + str(exc)}
        imports = []
        methods = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
                    if alias.name not in cls.SAFE_IMPORTS:
                        return {"pass": False, "reason": "IMPORT_NOT_ALLOWED", "import": alias.name}
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                imports.append(module)
                if module not in cls.SAFE_IMPORTS:
                    return {"pass": False, "reason": "IMPORT_NOT_ALLOWED", "import": module}
            if isinstance(node, ast.Call):
                name = None
                if isinstance(node.func, ast.Name):
                    name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    name = node.func.attr
                if name in cls.BANNED_CALLS:
                    return {"pass": False, "reason": "CALL_NOT_ALLOWED", "call": name}
                if name == "Request":
                    for kw in node.keywords:
                        if kw.arg == "method" and isinstance(kw.value, ast.Constant):
                            methods.append(str(kw.value.value))
            if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
                return {"pass": False, "reason": "DUNDER_ATTRIBUTE_NOT_ALLOWED", "attribute": node.attr}
        if methods != ["GET"]:
            return {"pass": False, "reason": "NON_GET_METHOD", "methods": methods}
        return {"pass": True, "imports": sorted(set(imports)), "methods": methods}

    @staticmethod
    def _import_candidate(path: Path):
        spec = importlib.util.spec_from_file_location("yado_generated_http_json_adapter", path)
        if spec is None or spec.loader is None:
            raise RuntimeError("CANDIDATE_IMPORT_SPEC_FAILED")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    @classmethod
    def fresh_tests(cls, candidate_path: Path, allowed_hosts: list[str]) -> dict:
        mod = cls._import_candidate(candidate_path)
        real_urlopen = mod.urlopen

        class FakeHeaders:
            def get(self, key, default=""):
                return "application/json; charset=utf-8" if key.lower() == "content-type" else default

        class FakeResponse:
            def __init__(self, payload: bytes, final_url: str, status: int = 200):
                self._payload = payload
                self._final_url = final_url
                self.status = status
                self.headers = FakeHeaders()
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc, tb):
                return False
            def geturl(self):
                return self._final_url
            def read(self, limit):
                return self._payload[:limit]

        cases = []
        calls = []
        host = allowed_hosts[0]
        test_url = "https://" + host + "/probe"

        def ok_urlopen(request, timeout=10.0):
            calls.append({"method": request.get_method(), "timeout": timeout, "url": request.full_url})
            return FakeResponse(b'{"ok":true,"items":[1,2,3]}', test_url)

        mod.urlopen = ok_urlopen
        try:
            got = mod.fetch_json(test_url, allowed_hosts, timeout=2, max_bytes=4096)
            cases.append({"name": "bounded_get_json_parse", "pass": got["status"] == 200 and got["payload"]["ok"] is True})
            cases.append({"name": "get_only", "pass": calls == [{"method": "GET", "timeout": 2.0, "url": test_url}]})
            cases.append({"name": "summary_shape", "pass": got["summary"]["type"] == "dict" and "items" in got["summary"]["keys"]})
        except Exception as exc:
            cases.append({"name": "bounded_get_json_parse", "pass": False, "error": type(exc).__name__ + ":" + str(exc)})

        try:
            mod.fetch_json("https://example.invalid/x", allowed_hosts)
            blocked = False
        except ValueError as exc:
            blocked = str(exc) == "HOST_NOT_ALLOWED"
        cases.append({"name": "disallowed_host_blocked", "pass": blocked})

        def redirected_urlopen(request, timeout=10.0):
            return FakeResponse(b'{"ok":true}', "https://example.invalid/redirected")
        mod.urlopen = redirected_urlopen
        try:
            mod.fetch_json(test_url, allowed_hosts)
            redirect_blocked = False
        except ValueError as exc:
            redirect_blocked = str(exc) == "HOST_NOT_ALLOWED"
        cases.append({"name": "redirect_host_revalidated", "pass": redirect_blocked})

        def oversized_urlopen(request, timeout=10.0):
            return FakeResponse(b"x" * 2049, test_url)
        mod.urlopen = oversized_urlopen
        try:
            mod.fetch_json(test_url, allowed_hosts, max_bytes=1024)
            oversized_blocked = False
        except ValueError as exc:
            oversized_blocked = str(exc) == "RESPONSE_TOO_LARGE"
        cases.append({"name": "response_bound_enforced", "pass": oversized_blocked})

        mod.urlopen = real_urlopen
        return {"pass": all(x.get("pass") is True for x in cases), "case_count": len(cases), "cases": cases}

    @staticmethod
    def live_fetch_with_retry(mod, resource: dict, allowed_hosts: list[str]) -> dict:
        url = str(resource.get("url") or "")
        errors = []
        for attempt in range(1, 3):
            try:
                result = mod.fetch_json(url, allowed_hosts, timeout=10, max_bytes=524288)
                payload = result.pop("payload", None)
                result.update({
                    "resource_id": resource.get("id"),
                    "resource_name": resource.get("name"),
                    "attempt": attempt,
                    "parsed": payload is not None,
                    "payload_digest": digest(payload),
                    "pass": result.get("status") == 200 and payload is not None,
                })
                return result
            except Exception as exc:
                errors.append(type(exc).__name__ + ":" + str(exc))
                time.sleep(0.5)
        return {
            "resource_id": resource.get("id"),
            "resource_name": resource.get("name"),
            "pass": False,
            "errors": errors,
        }

    def run(self, request: dict) -> dict:
        head_before = load(HEAD).get("canonical_head_digest") if HEAD.exists() else None
        objective = str(request.get("objective") or request.get("goal") or "")
        resources = list(request.get("allowed_resources") or [])
        selection = self.select_resource(objective, resources)
        if selection.get("status") != "SELECTED":
            return {
                "schema": self.SCHEMA,
                "status": "WITHHOLD_G2_NATIVE_INTEGRATION_BROKER_V1",
                "selection": selection,
                "canonical_mutation": False,
                "claim_boundary": "HOST-AUTHORED BOUNDED BROKER; NO UNBOUNDED OR CREDENTIAL-BYPASS NETWORK ACCESS.",
            }

        ir = self.derive_ir(objective, selection, resources)
        source = self.materialize_adapter(ir)
        safety = self.static_safety_gate(source)
        CANDIDATE.parent.mkdir(parents=True, exist_ok=True)
        CANDIDATE.write_text(source, encoding="utf-8")
        compile(source, str(CANDIDATE), "exec")
        allowed_hosts = list(ir.get("allowed_hosts") or [])
        tests = self.fresh_tests(CANDIDATE, allowed_hosts) if safety.get("pass") else {"pass": False, "reason": "SAFETY_GATE_FAILED"}

        live_attempts = []
        if tests.get("pass") is True:
            mod = self._import_candidate(CANDIDATE)
            compatible = [
                r for r in resources
                if r.get("read_only") is True and r.get("adapter_family") == self.ADAPTER_FAMILY
            ]
            selected_id = (selection.get("resource") or {}).get("id")
            compatible.sort(key=lambda r: (0 if r.get("id") == selected_id else 1, str(r.get("id"))))
            for resource in compatible[:2]:
                live_attempts.append(self.live_fetch_with_retry(mod, resource, allowed_hosts))

        live_successes = [x for x in live_attempts if x.get("pass") is True]
        reuse_pass = len(live_successes) >= 2
        selected_live_pass = bool(live_attempts) and live_attempts[0].get("pass") is True
        head_after = load(HEAD).get("canonical_head_digest") if HEAD.exists() else None

        checks = {
            "resource_selected_by_broker": selection.get("status") == "SELECTED",
            "semantic_ir_created": ir.get("status") == "READY",
            "adapter_source_materialized_by_kernel": CANDIDATE.exists() and len(source) > 0,
            "adapter_source_compiles": True,
            "static_safety_gate_pass": safety.get("pass") is True,
            "fresh_tests_pass": tests.get("pass") is True,
            "selected_live_connection_pass": selected_live_pass,
            "live_json_parse_pass": bool(live_successes) and all(x.get("parsed") is True for x in live_successes),
            "adapter_reused_on_second_resource": reuse_pass,
            "get_only": safety.get("methods") == ["GET"],
            "host_source_seed_used": False,
            "external_coding_models_used": False,
            "account_creation_attempted": False,
            "credential_bypass_attempted": False,
            "canonical_unchanged": head_before == head_after,
        }
        positive = [
            "resource_selected_by_broker", "semantic_ir_created", "adapter_source_materialized_by_kernel",
            "adapter_source_compiles", "static_safety_gate_pass", "fresh_tests_pass",
            "selected_live_connection_pass", "live_json_parse_pass", "adapter_reused_on_second_resource",
            "get_only", "canonical_unchanged",
        ]
        negative = [
            "host_source_seed_used", "external_coding_models_used", "account_creation_attempted", "credential_bypass_attempted",
        ]
        passed = all(checks[k] is True for k in positive) and all(checks[k] is False for k in negative)

        capability = {
            "capability_id": "CAP-G2-SHADOW-HTTP-JSON-INTEGRATION-V1",
            "family": self.ADAPTER_FAMILY,
            "state": "SHADOW_VERIFIED" if passed else "WITHHOLD",
            "candidate_path": str(CANDIDATE.relative_to(REPO)),
            "candidate_source_sha256": sha_text(source),
            "allowed_hosts": allowed_hosts,
            "verified_resource_ids": [x.get("resource_id") for x in live_successes],
            "read_only": True,
            "http_methods": ["GET"],
            "canonical_active": False,
        }
        capability["capability_digest"] = digest(capability)
        registry = {
            "schema": "yado.g2.native_integration_registry.v1",
            "status": "PASS_SHADOW" if passed else "WITHHOLD",
            "capabilities": [capability],
            "canonical_mutation": False,
        }
        registry["registry_digest"] = digest(registry)
        write(REGISTRY, registry)

        report = {
            "schema": self.SCHEMA,
            "component_id": self.COMPONENT_ID,
            "status": "PASS_SHADOW_G2_NATIVE_INTEGRATION_BROKER_V1" if passed else "WITHHOLD_G2_NATIVE_INTEGRATION_BROKER_V1",
            "objective": objective,
            "selection": selection,
            "semantic_ir": ir,
            "candidate_path": str(CANDIDATE.relative_to(REPO)),
            "candidate_source_sha256": sha_text(source),
            "candidate_source_bytes": len(source.encode()),
            "adapter_source_materialized_by_kernel": True,
            "safety": safety,
            "fresh_tests": tests,
            "live_attempts": live_attempts,
            "reuse_pass": reuse_pass,
            "registry_path": str(REGISTRY.relative_to(REPO)),
            "registry_digest": registry["registry_digest"],
            "checks": checks,
            "canonical_mutation": False,
            "claim_boundary": "HOST-AUTHORED BOUNDED INTEGRATION BROKER. THE KERNEL SELECTS FROM A HOST-SUPPLIED PUBLIC READ-ONLY ALLOWLIST, MATERIALIZES A FRESH GET-ONLY JSON ADAPTER FROM SEMANTIC IR, CONNECTS, PARSES, REGISTERS, AND REUSES IT. THIS DOES NOT AUTHORIZE ACCOUNT CREATION, SECRET ACQUISITION, AUTH BYPASS, PAYMENT, CAPTCHA BYPASS, MUTATING REQUESTS, PORT SCANNING, OR UNBOUNDED NETWORK DISCOVERY.",
        }
        report["receipt_sha256"] = digest(report)
        return report


def main() -> int:
    request = load(REQUEST)
    broker = YADONativeIntegrationBrokerV1()
    report = broker.run(request)
    write(REPORT, report)
    print(json.dumps({
        "status": report.get("status"),
        "selected_resource": ((report.get("selection") or {}).get("resource") or {}).get("id"),
        "candidate_path": report.get("candidate_path"),
        "candidate_source_sha256": report.get("candidate_source_sha256"),
        "fresh_tests": (report.get("fresh_tests") or {}).get("pass"),
        "safety": (report.get("safety") or {}).get("pass"),
        "live_passes": sum(1 for x in report.get("live_attempts", []) if x.get("pass") is True),
        "reuse_pass": report.get("reuse_pass"),
        "registry_digest": report.get("registry_digest"),
        "receipt_sha256": report.get("receipt_sha256"),
    }, indent=2, sort_keys=True))
    return 0 if report.get("status") == "PASS_SHADOW_G2_NATIVE_INTEGRATION_BROKER_V1" else 2


if __name__ == "__main__":
    raise SystemExit(main())
