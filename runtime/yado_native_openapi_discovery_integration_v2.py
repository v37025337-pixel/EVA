from __future__ import annotations

from pathlib import Path
import hashlib
import importlib.util
import ipaddress
import json
import re
import socket
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from yado_native_integration_broker_v1_1 import YADONativeIntegrationBrokerV11

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
REQUEST = REPO / "architecture/yado-native-openapi-discovery-integration-v2-request.json"
CANDIDATE = REPO / "candidates/kernel-self-generated/yado_native_discovered_http_json_adapter_v2.py"
REPORT = REPO / "candidates/kernel-self-generated/g2-native-openapi-discovery-integration-v2.json"
REGISTRY = REPO / "candidates/kernel-self-generated/g2-native-openapi-integration-registry-v2.json"
HEAD = REPO / "canonical/yado-main-head-g2.json"


def canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def digest(obj: Any) -> str:
    return hashlib.sha256(canon(obj).encode()).hexdigest()


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def fetch_bytes(url: str, max_bytes: int, timeout: float = 10.0) -> tuple[bytes, dict]:
    req = Request(url, headers={"User-Agent": "YADO-OpenAPI-Discovery/2.0", "Accept": "application/json, text/plain;q=0.8"}, method="GET")
    with urlopen(req, timeout=timeout) as response:
        final_url = response.geturl()
        status = int(getattr(response, "status", 200))
        raw = response.read(max_bytes + 1)
        content_type = str(response.headers.get("Content-Type", ""))
    if len(raw) > max_bytes:
        raise ValueError("RESPONSE_TOO_LARGE")
    if not (200 <= status < 300):
        raise ValueError("HTTP_STATUS_" + str(status))
    return raw, {"status": status, "final_url": final_url, "content_type": content_type, "bytes": len(raw), "sha256": sha_bytes(raw)}


def tokens(text: str) -> set[str]:
    return {x for x in re.split(r"[^a-z0-9]+", str(text).lower()) if len(x) >= 3}


def public_https_host(url: str) -> tuple[bool, str, list[str]]:
    p = urlparse(url)
    host = (p.hostname or "").lower().strip(".")
    if p.scheme != "https" or not host or host == "localhost" or host.endswith(".local"):
        return False, host, []
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False, host, []
    except ValueError:
        pass
    resolved: list[str] = []
    try:
        for row in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM):
            ip_s = row[4][0]
            if ip_s in resolved:
                continue
            ip = ipaddress.ip_address(ip_s)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                return False, host, resolved + [ip_s]
            resolved.append(ip_s)
    except Exception:
        return False, host, resolved
    return bool(resolved), host, resolved


class YADONativeOpenAPIDiscoveryIntegrationV2:
    COMPONENT_ID = "CTRL-G2-NATIVE-OPENAPI-DISCOVERY-INTEGRATION-V2"
    PASS = "PASS_SHADOW_G2_NATIVE_OPENAPI_DISCOVERY_INTEGRATION_V2"
    WITHHOLD = "WITHHOLD_G2_NATIVE_OPENAPI_DISCOVERY_INTEGRATION_V2"
    BANNED_TEXT = {
        "payment", "banking", "trading", "gambling", "casino", "weapon", "surveillance",
        "identity", "password", "admin", "management", "billing", "crypto exchange",
    }

    @staticmethod
    def _head_digest() -> str | None:
        if not HEAD.exists():
            return None
        try:
            return load(HEAD).get("canonical_head_digest")
        except Exception:
            return None

    @classmethod
    def rank_catalog(cls, catalog: dict, goal_tags: list[str], limit: int) -> list[dict]:
        goal = tokens(" ".join(goal_tags))
        ranked: list[dict] = []
        for api_id, meta in catalog.items():
            if api_id == "apis.guru":
                continue
            preferred = str(meta.get("preferred") or "")
            ver = (meta.get("versions") or {}).get(preferred) or {}
            info = ver.get("info") or {}
            categories = [str(x).lower() for x in info.get("x-apisguru-categories", [])]
            text = " ".join([
                api_id,
                str(info.get("title") or ""),
                str(info.get("description") or ""),
                " ".join(categories),
                " ".join(str(x) for x in info.get("x-tags", [])),
            ]).lower()
            if any(b in text for b in cls.BANNED_TEXT):
                continue
            swagger_url = str(ver.get("swaggerUrl") or "")
            if not swagger_url.startswith("https://api.apis.guru/"):
                continue
            score = len(tokens(text) & goal)
            if "open_data" in categories:
                score += 10
            if "developer_tools" in categories:
                score += 7
            if "location" in categories or "science" in categories:
                score += 5
            if "json" in text:
                score += 2
            if info.get("x-apiClientRegistration"):
                score -= 4
            ranked.append({
                "api_id": api_id,
                "preferred": preferred,
                "title": info.get("title"),
                "categories": categories,
                "swagger_url": swagger_url,
                "external_docs": (ver.get("externalDocs") or {}).get("url") or (info.get("externalDocs") or {}).get("url"),
                "score": score,
            })
        ranked.sort(key=lambda x: (-x["score"], x["api_id"]))
        return ranked[:limit]

    @staticmethod
    def base_url(spec: dict, path_item: dict, operation: dict) -> str | None:
        for servers in (operation.get("servers"), path_item.get("servers"), spec.get("servers")):
            if isinstance(servers, list):
                for s in servers:
                    url = str((s or {}).get("url") or "")
                    if url.startswith("https://") and "{" not in url:
                        return url.rstrip("/")
        if spec.get("swagger"):
            schemes = [str(x).lower() for x in spec.get("schemes", [])]
            host = str(spec.get("host") or "")
            base_path = str(spec.get("basePath") or "")
            if "https" in schemes and host and "{" not in host:
                return ("https://" + host + "/" + base_path.strip("/")).rstrip("/")
        return None

    @classmethod
    def operation_candidates(cls, spec: dict) -> list[dict]:
        out: list[dict] = []
        global_security = spec.get("security", [])
        for path, item in (spec.get("paths") or {}).items():
            if not isinstance(item, dict) or "{" in path:
                continue
            op = item.get("get")
            if not isinstance(op, dict):
                continue
            effective_security = op["security"] if "security" in op else global_security
            if effective_security:
                continue
            params = []
            for source in (item.get("parameters", []), op.get("parameters", [])):
                if isinstance(source, list):
                    params.extend(x for x in source if isinstance(x, dict))
            if any(x.get("required") is True for x in params):
                continue
            request_body = op.get("requestBody")
            if isinstance(request_body, dict) and request_body.get("required") is True:
                continue
            base = cls.base_url(spec, item, op)
            if not base:
                continue
            url = urljoin(base + "/", path.lstrip("/"))
            ok, host, resolved = public_https_host(url)
            if not ok:
                continue
            responses = op.get("responses") or {}
            response_keys = {str(k) for k in responses}
            out.append({
                "method": "GET",
                "path": path,
                "url": url,
                "host": host,
                "resolved_public_ips": resolved,
                "operation_id": op.get("operationId"),
                "summary": op.get("summary") or op.get("description"),
                "auth_required": False,
                "required_parameter_count": 0,
                "response_codes": sorted(response_keys),
            })
        out.sort(key=lambda x: (0 if "200" in x["response_codes"] else 1, len(x["path"]), x["path"]))
        return out

    @staticmethod
    def import_candidate(path: Path):
        spec = importlib.util.spec_from_file_location("yado_discovered_adapter_v2", path)
        if spec is None or spec.loader is None:
            raise RuntimeError("CANDIDATE_IMPORT_FAILED")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def run(self, request: dict) -> dict:
        head_before = self._head_digest()
        source = request["discovery_source"]
        limits = request.get("limits") or {}
        attempts: list[dict] = []
        report: dict = {
            "schema": "yado.g2.native_openapi_discovery_integration.v2",
            "component_id": self.COMPONENT_ID,
            "objective": request.get("objective"),
            "status": self.WITHHOLD,
            "host_selected_provider": False,
            "host_selected_endpoint": False,
            "external_coding_models_used": False,
            "host_source_seed_used": False,
            "canonical_mutation": False,
            "claim_boundary": "HOST-AUTHORED BOUNDED DISCOVERY BROKER. THE KERNEL/BROKER SELECTS A PROVIDER AND READ-ONLY ENDPOINT FROM A PUBLIC OPENAPI DIRECTORY, MATERIALIZES A FRESH ADAPTER, AND EXECUTES ONLY UNAUNTHENTICATED HTTPS GET OPERATIONS WITH NO REQUIRED PARAMETERS. NO ACCOUNT CREATION, SECRET ACQUISITION, AUTH BYPASS, MUTATION, PORT SCANNING OR PRIVATE-NETWORK ACCESS IS AUTHORIZED.",
        }
        try:
            raw, cat_meta = fetch_bytes(
                str(source["catalog_url"]),
                int(limits.get("catalog_max_bytes", 8388608)),
                timeout=float(limits.get("live_timeout_seconds", 10)),
            )
            catalog = json.loads(raw.decode("utf-8"))
            report["catalog"] = {**cat_meta, "url": source["catalog_url"], "entry_count": len(catalog)}
        except Exception as exc:
            report["failure"] = "CATALOG_FETCH:" + type(exc).__name__ + ":" + str(exc)
            write(REPORT, report)
            return report

        ranked = self.rank_catalog(catalog, request.get("goal_tags") or [], int(limits.get("max_ranked_candidates", 48)))
        report["ranked_candidate_count"] = len(ranked)
        report["ranking_preview"] = ranked[:12]
        max_specs = int(limits.get("max_spec_fetches", 32))
        selected: dict | None = None

        for row in ranked[:max_specs]:
            attempt: dict = {"api_id": row["api_id"], "score": row["score"], "swagger_url": row["swagger_url"]}
            try:
                spec_raw, spec_meta = fetch_bytes(row["swagger_url"], int(limits.get("spec_max_bytes", 2097152)))
                spec = json.loads(spec_raw.decode("utf-8"))
                attempt["openapi_contract"] = {**spec_meta, "openapi": spec.get("openapi"), "swagger": spec.get("swagger")}
                ops = self.operation_candidates(spec)
                attempt["eligible_get_count"] = len(ops)
                if not ops:
                    attempt["result"] = "NO_UNAUTHENTICATED_PARAMETERLESS_HTTPS_GET"
                    attempts.append(attempt)
                    continue

                for operation in ops[:4]:
                    ir = {
                        "status": "READY",
                        "family": "HTTP_JSON_GET",
                        "module": "yado_native_discovered_http_json_adapter_v2",
                        "goal_digest": hashlib.sha256(str(request.get("objective") or "").encode()).hexdigest(),
                        "selected_resource_id": row["api_id"],
                        "allowed_hosts": [operation["host"]],
                        "operations": [
                            "URL_VALIDATE", "EXACT_HOST_ALLOWLIST", "BOUNDED_HTTP_GET",
                            "FINAL_REDIRECT_HOST_VALIDATE", "BOUNDED_RESPONSE_READ",
                            "SHA256_PROVENANCE", "JSON_PARSE", "STRUCTURE_SUMMARY",
                        ],
                        "network_mutation": False,
                        "http_methods": ["GET"],
                    }
                    adapter_source = YADONativeIntegrationBrokerV11.materialize_adapter(ir)
                    CANDIDATE.parent.mkdir(parents=True, exist_ok=True)
                    CANDIDATE.write_text(adapter_source, encoding="utf-8")
                    compile(adapter_source, str(CANDIDATE), "exec")
                    safety = YADONativeIntegrationBrokerV11.static_safety_gate(adapter_source)
                    if not safety.get("pass"):
                        attempt.setdefault("operation_failures", []).append({"path": operation["path"], "reason": "SAFETY_GATE", "detail": safety})
                        continue
                    fresh = YADONativeIntegrationBrokerV11.fresh_tests(CANDIDATE, [operation["host"]])
                    if not fresh.get("pass"):
                        attempt.setdefault("operation_failures", []).append({"path": operation["path"], "reason": "FRESH_TESTS", "detail": fresh})
                        continue
                    mod = self.import_candidate(CANDIDATE)
                    live = YADONativeIntegrationBrokerV11.live_fetch_with_retry(
                        mod,
                        {"id": row["api_id"], "name": row.get("title") or row["api_id"], "url": operation["url"]},
                        [operation["host"]],
                    )
                    if live.get("pass") is not True:
                        attempt.setdefault("operation_failures", []).append({"path": operation["path"], "reason": "LIVE_FETCH", "detail": live})
                        continue
                    selected = {
                        "catalog_entry": row,
                        "openapi_contract": {**spec_meta, "openapi": spec.get("openapi"), "swagger": spec.get("swagger")},
                        "operation": operation,
                        "semantic_ir": ir,
                        "candidate_source_sha256": hashlib.sha256(adapter_source.encode()).hexdigest(),
                        "candidate_source_bytes": len(adapter_source.encode()),
                        "safety": safety,
                        "fresh_tests": fresh,
                        "live": live,
                    }
                    attempt["result"] = "PASS_SELECTED"
                    attempt["selected_path"] = operation["path"]
                    attempts.append(attempt)
                    break
                if selected:
                    break
                if "result" not in attempt:
                    attempt["result"] = "NO_LIVE_OPERATION_PASSED"
                attempts.append(attempt)
            except Exception as exc:
                attempt["result"] = "SPEC_OR_CONTRACT_ERROR"
                attempt["error"] = type(exc).__name__ + ":" + str(exc)
                attempts.append(attempt)

        report["attempts"] = attempts
        if not selected:
            report["failure"] = "NO_DISCOVERED_API_PASSED_FULL_GATE"
            report["canonical_unchanged"] = self._head_digest() == head_before
            write(REPORT, report)
            return report

        provenance = {
            "catalog_url": source["catalog_url"],
            "catalog_sha256": report["catalog"]["sha256"],
            "api_id": selected["catalog_entry"]["api_id"],
            "spec_url": selected["catalog_entry"]["swagger_url"],
            "spec_sha256": selected["openapi_contract"]["sha256"],
            "endpoint_url": selected["operation"]["url"],
            "response_sha256": selected["live"].get("sha256"),
        }
        provenance["digest"] = digest(provenance)
        registry = {
            "schema": "yado.g2.native_openapi_integration_registry.v2",
            "status": "PASS_SHADOW",
            "canonical_mutation": False,
            "capabilities": [{
                "capability_id": "CAP-G2-SHADOW-DISCOVERED-OPENAPI-JSON-INTEGRATION-V2",
                "state": "SHADOW_VERIFIED",
                "canonical_active": False,
                "api_id": selected["catalog_entry"]["api_id"],
                "title": selected["catalog_entry"].get("title"),
                "family": "HTTP_JSON_GET",
                "endpoint": selected["operation"]["url"],
                "host": selected["operation"]["host"],
                "operation_id": selected["operation"].get("operation_id"),
                "auth_required": False,
                "read_only": True,
                "http_methods": ["GET"],
                "candidate_path": str(CANDIDATE.relative_to(REPO)),
                "candidate_source_sha256": selected["candidate_source_sha256"],
                "provenance_digest": provenance["digest"],
            }],
        }
        registry["registry_digest"] = digest(registry)
        write(REGISTRY, registry)

        head_after = self._head_digest()
        checks = {
            "catalog_fetched": True,
            "provider_selected_by_kernel": True,
            "host_selected_provider": False,
            "openapi_contract_fetched": True,
            "openapi_contract_digest_recorded": bool(selected["openapi_contract"].get("sha256")),
            "authentication_requirement_determined": True,
            "unauthenticated_get_selected": selected["operation"].get("auth_required") is False,
            "required_parameters_absent": selected["operation"].get("required_parameter_count") == 0,
            "semantic_ir_created": selected["semantic_ir"].get("status") == "READY",
            "fresh_adapter_source_created": bool(selected["candidate_source_sha256"]),
            "adapter_compiles": True,
            "static_safety_gate_pass": selected["safety"].get("pass") is True,
            "fresh_tests_pass": selected["fresh_tests"].get("pass") is True,
            "real_live_http_2xx": selected["live"].get("pass") is True and 200 <= int(selected["live"].get("status", 0)) < 300,
            "json_parse_pass": selected["live"].get("parsed") is True,
            "provenance_chain_recorded": bool(provenance["digest"]),
            "shadow_registry_created": REGISTRY.exists(),
            "private_network_access": False,
            "account_creation_attempted": False,
            "credential_bypass_attempted": False,
            "external_coding_models_used": False,
            "host_source_seed_used": False,
            "canonical_unchanged": head_after == head_before,
        }
        report.update({
            "selected": selected,
            "provenance": provenance,
            "registry_path": str(REGISTRY.relative_to(REPO)),
            "registry_digest": registry["registry_digest"],
            "candidate_path": str(CANDIDATE.relative_to(REPO)),
            "candidate_source_sha256": selected["candidate_source_sha256"],
            "checks": checks,
        })
        report["status"] = self.PASS if all(checks.values()) else self.WITHHOLD
        report["receipt_sha256"] = digest({k: v for k, v in report.items() if k != "receipt_sha256"})
        write(REPORT, report)
        return report


def main() -> int:
    request = load(REQUEST)
    report = YADONativeOpenAPIDiscoveryIntegrationV2().run(request)
    print(json.dumps({
        "status": report.get("status"),
        "selected_api": ((report.get("selected") or {}).get("catalog_entry") or {}).get("api_id"),
        "selected_endpoint": ((report.get("selected") or {}).get("operation") or {}).get("url"),
        "candidate_source_sha256": report.get("candidate_source_sha256"),
        "registry_digest": report.get("registry_digest"),
        "attempt_count": len(report.get("attempts") or []),
        "receipt_sha256": report.get("receipt_sha256"),
    }, indent=2, sort_keys=True))
    return 0 if report.get("status") == YADONativeOpenAPIDiscoveryIntegrationV2.PASS else 2


if __name__ == "__main__":
    raise SystemExit(main())
