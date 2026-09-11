from __future__ import annotations

from pathlib import Path
import hashlib
import ipaddress
import json
import socket
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from yado_external_resource_goal_binder_v1 import YADOExternalResourceGoalBinderV1

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
REQUEST = REPO / "architecture/yado-goal-external-resource-execution-fabric-v1-request.json"
REPORT = REPO / "candidates/kernel-self-generated/g2-goal-external-resource-execution-fabric-v1.json"
REGISTRY = REPO / "candidates/kernel-self-generated/g2-goal-external-resource-execution-fabric-registry-v1.json"
EXISTING_REGISTRY = REPO / "candidates/kernel-self-generated/g2-external-resource-goal-registry-v1.json"
HEAD = REPO / "canonical/yado-main-head-g2.json"

GENERIC_TAGS = {"public", "json", "read_only", "open_data", "developer_tools"}


def canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def digest(obj: Any) -> str:
    return hashlib.sha256(canon(obj).encode()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def head_digest() -> str | None:
    if not HEAD.exists():
        return None
    try:
        return load(HEAD).get("canonical_head_digest")
    except Exception:
        return None


def public_https_endpoint(url: str) -> tuple[bool, str, list[str]]:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().strip(".")
    if parsed.scheme != "https" or not host or host == "localhost" or host.endswith(".local"):
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


def summarize(payload: Any) -> dict:
    if isinstance(payload, dict):
        return {"type": "dict", "size": len(payload), "keys": sorted(str(k) for k in payload)[:32]}
    if isinstance(payload, list):
        return {"type": "list", "size": len(payload)}
    if isinstance(payload, str):
        return {"type": "str", "size": len(payload)}
    if isinstance(payload, bool):
        return {"type": "bool", "size": None}
    if isinstance(payload, (int, float)):
        return {"type": "number", "size": None}
    if payload is None:
        return {"type": "null", "size": None}
    return {"type": "other", "size": None}


def fetch_registered_json(endpoint: str, max_bytes: int = 524288, timeout: float = 10.0) -> dict:
    ok, host, resolved = public_https_endpoint(endpoint)
    if not ok:
        return {"pass": False, "reason": "REGISTERED_ENDPOINT_NOT_PUBLIC_HTTPS", "host": host, "resolved": resolved}
    request = Request(endpoint, headers={"User-Agent": "YADO-Execution-Fabric/1.0", "Accept": "application/json"}, method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            final_url = response.geturl()
            final_ok, final_host, final_resolved = public_https_endpoint(final_url)
            if not final_ok or final_host != host:
                return {"pass": False, "reason": "REDIRECT_HOST_NOT_ALLOWED", "final_url": final_url, "final_host": final_host, "resolved": final_resolved}
            status = int(getattr(response, "status", 200))
            raw = response.read(max_bytes + 1)
            content_type = str(response.headers.get("Content-Type", ""))
        if len(raw) > max_bytes:
            return {"pass": False, "reason": "RESPONSE_TOO_LARGE", "bytes": len(raw)}
        if not 200 <= status < 300:
            return {"pass": False, "reason": "HTTP_STATUS", "http_status": status}
        payload = json.loads(raw.decode("utf-8", errors="strict"))
        return {
            "pass": True,
            "http_status": status,
            "json_parsed": True,
            "bytes": len(raw),
            "content_type": content_type,
            "response_sha256": hashlib.sha256(raw).hexdigest(),
            "summary": summarize(payload),
            "endpoint": endpoint,
            "final_url": final_url,
            "host": host,
            "resolved_public_ips": resolved,
        }
    except Exception as exc:
        return {"pass": False, "reason": type(exc).__name__ + ":" + str(exc), "endpoint": endpoint}


class YADOGoalExternalResourceExecutionFabricV1:
    """Shadow execution fabric over the existing goal binder.

    This is host-authored routing/integration plumbing, not evidence that YADO
    natively invented the fabric. Provider selection for new discovery remains
    delegated to the bounded discovery controller and is not host-selected.
    """

    COMPONENT_ID = "CTRL-G2-GOAL-EXTERNAL-RESOURCE-EXECUTION-FABRIC-V1"
    PASS = "PASS_SHADOW_G2_GOAL_EXTERNAL_RESOURCE_EXECUTION_FABRIC_V1"
    WITHHOLD = "WITHHOLD_G2_GOAL_EXTERNAL_RESOURCE_EXECUTION_FABRIC_V1"

    def __init__(self) -> None:
        self.binder = YADOExternalResourceGoalBinderV1()
        self.existing_registry = load(EXISTING_REGISTRY) if EXISTING_REGISTRY.exists() else {"capabilities": []}

    def verified_existing(self) -> list[dict]:
        rows = []
        for row in self.existing_registry.get("capabilities", []):
            if row.get("state") != "SHADOW_VERIFIED" or row.get("canonical_active") is not False:
                continue
            endpoint = str(row.get("verified_external_endpoint") or "")
            if not endpoint.startswith("https://"):
                continue
            rows.append(row)
        return rows

    def route_goal(self, goal: str) -> dict:
        decision = self.binder.classify_goal(goal)
        if decision.get("external_resource_needed") is False:
            return {"route": "LOCAL_ONLY", "decision": decision, "required_domain_tags": []}
        tags = set(self.binder.goal_tags(goal))
        domain = sorted(tags - GENERIC_TAGS)
        existing = self.verified_existing()
        if existing and not domain:
            return {"route": "USE_EXISTING_INTEGRATION", "decision": decision, "goal_tags": sorted(tags), "required_domain_tags": domain}
        return {"route": "DISCOVER_NEW_API", "decision": decision, "goal_tags": sorted(tags), "required_domain_tags": domain}

    def execute_local(self, goal: str) -> dict:
        return {
            "goal": goal,
            "route": "LOCAL_ONLY",
            "discovery_invoked": False,
            "network_route_invoked": False,
            "registry_reused": False,
            "result": self.binder._local_execute(goal),
        }

    def execute_existing(self, goal: str) -> dict:
        existing = self.verified_existing()
        if not existing:
            return {"goal": goal, "route": "USE_EXISTING_INTEGRATION", "discovery_invoked": False, "network_route_invoked": False, "registry_reused": False, "result": {"pass": False, "reason": "NO_VERIFIED_EXISTING_INTEGRATION"}}
        selected = existing[0]
        endpoint = str(selected.get("verified_external_endpoint"))
        live = fetch_registered_json(endpoint)
        return {
            "goal": goal,
            "route": "USE_EXISTING_INTEGRATION",
            "discovery_invoked": False,
            "network_route_invoked": True,
            "registry_reused": True,
            "selected_api_id": selected.get("verified_external_api_id"),
            "selected_endpoint": endpoint,
            "result": live,
        }

    def execute_discovery(self, goal: str) -> dict:
        discovery = self.binder._run_discovery(goal)
        evaluation = self.binder.evaluate_discovery(discovery)
        selected = discovery.get("selected") or {}
        entry = selected.get("catalog_entry") or {}
        operation = selected.get("operation") or {}
        live = selected.get("live") or {}
        return {
            "goal": goal,
            "route": "DISCOVER_NEW_API",
            "discovery_invoked": True,
            "network_route_invoked": True,
            "registry_reused": False,
            "discovery_evaluation": evaluation,
            "result": {
                "pass": evaluation.get("pass") is True,
                "api_id": entry.get("api_id"),
                "api_title": entry.get("title"),
                "endpoint": operation.get("url"),
                "http_status": live.get("status"),
                "json_parsed": live.get("parsed"),
                "summary": live.get("summary"),
                "response_sha256": live.get("sha256"),
                "provenance_digest": (discovery.get("provenance") or {}).get("digest"),
                "candidate_source_sha256": discovery.get("candidate_source_sha256"),
            },
        }

    def execute(self, goal: str) -> dict:
        route = self.route_goal(goal)
        if route["route"] == "LOCAL_ONLY":
            out = self.execute_local(goal)
        elif route["route"] == "USE_EXISTING_INTEGRATION":
            out = self.execute_existing(goal)
        else:
            out = self.execute_discovery(goal)
        out["routing"] = route
        return out


def main() -> int:
    request = load(REQUEST)
    fabric = YADOGoalExternalResourceExecutionFabricV1()
    head_before = head_digest()

    local_goal = str(request["cases"]["local_goal"])
    existing_goal = str(request["cases"]["existing_integration_goal"])
    discovery_goal = str(request["cases"]["new_api_goal"])

    local_case = fabric.execute(local_goal)
    existing_case = fabric.execute(existing_goal)
    discovery_case = fabric.execute(discovery_goal)

    old_ids = {str(x.get("verified_external_api_id")) for x in fabric.verified_existing() if x.get("verified_external_api_id")}
    discovered_id = str((discovery_case.get("result") or {}).get("api_id") or "")
    discovery_eval = discovery_case.get("discovery_evaluation") or {}
    discovery_negative = discovery_eval.get("negative_checks") or {}
    head_after = head_digest()

    checks = {
        "local_routed_local_only": local_case.get("route") == "LOCAL_ONLY",
        "local_no_discovery": local_case.get("discovery_invoked") is False,
        "local_no_network": local_case.get("network_route_invoked") is False,
        "local_result_ok": ((local_case.get("result") or {}).get("result") == "LOCAL_ONLY_OK"),
        "existing_routed_to_reuse": existing_case.get("route") == "USE_EXISTING_INTEGRATION",
        "existing_registry_reused": existing_case.get("registry_reused") is True,
        "existing_no_discovery": existing_case.get("discovery_invoked") is False,
        "existing_live_2xx": isinstance((existing_case.get("result") or {}).get("http_status"), int) and 200 <= (existing_case.get("result") or {}).get("http_status") < 300,
        "existing_json_parsed": (existing_case.get("result") or {}).get("json_parsed") is True,
        "new_goal_routed_to_discovery": discovery_case.get("route") == "DISCOVER_NEW_API",
        "new_goal_discovery_invoked": discovery_case.get("discovery_invoked") is True,
        "new_goal_not_registry_reuse": discovery_case.get("registry_reused") is False,
        "new_goal_full_discovery_gate": discovery_eval.get("pass") is True,
        "new_goal_provider_not_host_selected": discovery_negative.get("host_selected_provider") is False,
        "new_goal_live_2xx": isinstance((discovery_case.get("result") or {}).get("http_status"), int) and 200 <= (discovery_case.get("result") or {}).get("http_status") < 300,
        "new_goal_json_parsed": (discovery_case.get("result") or {}).get("json_parsed") is True,
        "new_api_differs_from_existing": bool(discovered_id) and discovered_id not in old_ids,
        "new_goal_provenance_recorded": bool((discovery_case.get("result") or {}).get("provenance_digest")),
        "canonical_unchanged": head_before == head_after,
    }
    status = fabric.PASS if all(checks.values()) else fabric.WITHHOLD

    capabilities = []
    for row in fabric.verified_existing():
        capabilities.append({
            "route": "USE_EXISTING_INTEGRATION",
            "api_id": row.get("verified_external_api_id"),
            "endpoint": row.get("verified_external_endpoint"),
            "state": "SHADOW_VERIFIED",
            "canonical_active": False,
        })
    if discovered_id:
        capabilities.append({
            "route": "DISCOVER_NEW_API",
            "api_id": discovered_id,
            "endpoint": (discovery_case.get("result") or {}).get("endpoint"),
            "state": "SHADOW_VERIFIED" if (discovery_case.get("result") or {}).get("pass") is True else "WITHHOLD",
            "canonical_active": False,
        })
    registry = {
        "schema": "yado.g2.goal_external_resource_execution_fabric.registry.v1",
        "status": "PASS_SHADOW" if status == fabric.PASS else "WITHHOLD",
        "canonical_mutation": False,
        "routes": ["LOCAL_ONLY", "USE_EXISTING_INTEGRATION", "DISCOVER_NEW_API"],
        "capabilities": capabilities,
    }
    registry["registry_digest"] = digest(registry)
    write(REGISTRY, registry)

    report = {
        "schema": "yado.g2.goal_external_resource_execution_fabric.v1",
        "component_id": fabric.COMPONENT_ID,
        "status": status,
        "claim_boundary": "HOST-AUTHORED SHADOW EXECUTION FABRIC OVER EXISTING YADO GOAL BINDING AND DISCOVERY COMPONENTS. IT TESTS ROUTE SELECTION AND REAL READ-ONLY EXECUTION; IT IS NOT EVIDENCE THAT YADO NATIVELY INVENTED THIS FABRIC. NEW PROVIDER/ENDPOINT SELECTION IS DELEGATED TO THE BOUNDED DISCOVERY CONTROLLER AND IS NOT HOST-SELECTED.",
        "cases": {"local": local_case, "existing": existing_case, "discovery": discovery_case},
        "checks": checks,
        "existing_api_ids_before": sorted(old_ids),
        "discovered_api_id": discovered_id or None,
        "canonical_mutation": False,
        "canonical_head_before": head_before,
        "canonical_head_after": head_after,
        "registry_path": str(REGISTRY.relative_to(REPO)),
        "registry_digest": registry["registry_digest"],
    }
    report["receipt_sha256"] = digest(report)
    write(REPORT, report)

    print(json.dumps({
        "status": status,
        "local_route": local_case.get("route"),
        "existing_route": existing_case.get("route"),
        "existing_api_id": existing_case.get("selected_api_id"),
        "existing_http_status": (existing_case.get("result") or {}).get("http_status"),
        "discovery_route": discovery_case.get("route"),
        "discovered_api_id": discovered_id or None,
        "discovery_http_status": (discovery_case.get("result") or {}).get("http_status"),
        "canonical_unchanged": checks["canonical_unchanged"],
        "receipt_sha256": report["receipt_sha256"],
    }, indent=2, sort_keys=True))
    return 0 if status == fabric.PASS else 2


if __name__ == "__main__":
    raise SystemExit(main())
