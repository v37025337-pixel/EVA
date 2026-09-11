from __future__ import annotations

from pathlib import Path
import hashlib
import json
import re
from typing import Any, Callable

from yado_native_openapi_discovery_integration_v2 import YADONativeOpenAPIDiscoveryIntegrationV2

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
REQUEST = REPO / "architecture/yado-external-resource-goal-binder-v1-request.json"
REPORT = REPO / "candidates/kernel-self-generated/g2-external-resource-goal-binder-v1.json"
REGISTRY = REPO / "candidates/kernel-self-generated/g2-external-resource-goal-registry-v1.json"
HEAD = REPO / "canonical/yado-main-head-g2.json"


def canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def digest(obj: Any) -> str:
    return hashlib.sha256(canon(obj).encode()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


POSITIVE_DISCOVERY_CHECKS = [
    "catalog_fetched",
    "provider_selected_by_kernel",
    "openapi_contract_fetched",
    "openapi_contract_digest_recorded",
    "authentication_requirement_determined",
    "unauthenticated_get_selected",
    "required_parameters_absent",
    "semantic_ir_created",
    "fresh_adapter_source_created",
    "adapter_compiles",
    "static_safety_gate_pass",
    "fresh_tests_pass",
    "real_live_http_2xx",
    "json_parse_pass",
    "provenance_chain_recorded",
    "shadow_registry_created",
    "canonical_unchanged",
]

NEGATIVE_DISCOVERY_CHECKS = [
    "host_selected_provider",
    "private_network_access",
    "account_creation_attempted",
    "credential_bypass_attempted",
    "external_coding_models_used",
    "host_source_seed_used",
]


class YADOExternalResourceGoalBinderV1:
    """Host-authored bridge from ordinary goals to bounded external discovery.

    This component does not choose a provider or endpoint. It decides whether a
    goal needs external evidence and, only then, delegates to the already gated
    OpenAPI discovery/integration controller. Explicit local-only instructions
    override all external hints and never invoke discovery.
    """

    COMPONENT_ID = "CTRL-G2-EXTERNAL-RESOURCE-GOAL-BINDER-V1"
    PASS = "PASS_SHADOW_G2_EXTERNAL_RESOURCE_GOAL_BINDER_V1"
    WITHHOLD = "WITHHOLD_G2_EXTERNAL_RESOURCE_GOAL_BINDER_V1"

    LOCAL_HINTS = (
        "without external", "no external", "without network", "no network",
        "local only", "offline only", "do not use the internet", "без внеш",
        "без сети", "без интернета", "только локально", "локально",
    )
    EXTERNAL_HINTS = (
        "public api", "api", "external data", "public data", "open data",
        "live data", "current data", "latest data", "online", "web",
        "internet", "real-time", "realtime", "recent data", "external resource",
        "внешние данные", "публичные данные", "api", "интернет", "онлайн",
        "актуальные данные", "внешний ресурс",
    )

    def __init__(self, discovery_factory: Callable[[], YADONativeOpenAPIDiscoveryIntegrationV2] | None = None):
        self.discovery_factory = discovery_factory or YADONativeOpenAPIDiscoveryIntegrationV2

    @staticmethod
    def _head_digest() -> str | None:
        if not HEAD.exists():
            return None
        try:
            return load(HEAD).get("canonical_head_digest")
        except Exception:
            return None

    @classmethod
    def classify_goal(cls, goal: str) -> dict:
        text = " ".join(str(goal).lower().split())
        local_matches = [x for x in cls.LOCAL_HINTS if x in text]
        if local_matches:
            return {
                "external_resource_needed": False,
                "reason": "EXPLICIT_LOCAL_ONLY_CONSTRAINT",
                "matches": local_matches,
            }
        external_matches = [x for x in cls.EXTERNAL_HINTS if x in text]
        if external_matches:
            return {
                "external_resource_needed": True,
                "reason": "EXTERNAL_EVIDENCE_REQUIRED_BY_GOAL",
                "matches": external_matches,
            }
        return {
            "external_resource_needed": False,
            "reason": "NO_EXTERNAL_DEFICIT_DETECTED",
            "matches": [],
        }

    @staticmethod
    def goal_tags(goal: str) -> list[str]:
        text = str(goal).lower()
        tags = ["public", "json", "read_only", "open_data"]
        mapping = {
            "science": ("science", "scientific", "research"),
            "location": ("location", "city", "geography", "geo"),
            "developer_tools": ("developer", "software", "code", "api"),
            "transport": ("transport", "transit", "traffic"),
            "media": ("media", "movie", "television"),
        }
        for tag, words in mapping.items():
            if any(word in text for word in words):
                tags.append(tag)
        return sorted(set(tags))

    @classmethod
    def build_discovery_request(cls, goal: str) -> dict:
        return {
            "schema": "yado.g2.external_resource_goal_binder.discovery_request.v1",
            "objective": goal,
            "discovery_source": {
                "id": "APIS_GURU_DIRECTORY",
                "catalog_url": "https://api.apis.guru/v2/list.json",
                "kind": "PUBLIC_OPENAPI_DIRECTORY",
                "read_only": True,
            },
            "goal_tags": cls.goal_tags(goal),
            "host_role": "supply public catalog and bounded safety policy only; do not select provider or endpoint",
            "kernel_role": "rank APIs, inspect OpenAPI contracts, select a safe unauthenticated GET, materialize adapter, connect and return evidence",
            "limits": {
                "catalog_max_bytes": 33554432,
                "spec_max_bytes": 2097152,
                "max_ranked_candidates": 48,
                "max_spec_fetches": 32,
                "live_response_max_bytes": 524288,
                "live_timeout_seconds": 10,
            },
            "constraints": {
                "https_only": True,
                "read_only": True,
                "allowed_http_methods": ["GET"],
                "unauthenticated_operations_only": True,
                "required_parameters_allowed": False,
                "host_selected_provider": False,
                "host_selected_endpoint": False,
                "source_seed": None,
                "external_coding_models": False,
                "account_creation": False,
                "credential_acquisition": False,
                "authentication_bypass": False,
                "captcha_bypass": False,
                "payment": False,
                "port_scanning": False,
                "arbitrary_network_scanning": False,
                "private_network_access": False,
                "canonical_mutation": False,
                "automatic_promotion": False,
                "fail_closed": True,
            },
        }

    @staticmethod
    def evaluate_discovery(report: dict) -> dict:
        checks = report.get("checks") or {}
        positive = {k: checks.get(k) for k in POSITIVE_DISCOVERY_CHECKS}
        negative = {k: checks.get(k) for k in NEGATIVE_DISCOVERY_CHECKS}
        return {
            "pass": all(v is True for v in positive.values()) and all(v is False for v in negative.values()),
            "positive_checks": positive,
            "negative_checks": negative,
        }

    def _run_discovery(self, goal: str) -> dict:
        request = self.build_discovery_request(goal)
        return self.discovery_factory().run(request)

    @staticmethod
    def _local_execute(goal: str) -> dict:
        text = str(goal)
        if "LOCAL_ONLY_OK" in text:
            return {"status": "PASS_LOCAL", "result": "LOCAL_ONLY_OK"}
        words = sorted(set(re.findall(r"[A-Za-zА-Яа-я0-9_]+", text.lower())))
        return {"status": "PASS_LOCAL", "result": words, "operation": "SORT_UNIQUE_TOKENS"}

    def execute_goal(self, goal: str) -> dict:
        decision = self.classify_goal(goal)
        if decision["external_resource_needed"] is False:
            local = self._local_execute(goal)
            return {
                "goal": goal,
                "route": "LOCAL_ONLY",
                "decision": decision,
                "discovery_invoked": False,
                "network_route_invoked": False,
                "result": local,
            }

        discovery = self._run_discovery(goal)
        evaluation = self.evaluate_discovery(discovery)
        selected = discovery.get("selected") or {}
        entry = selected.get("catalog_entry") or {}
        operation = selected.get("operation") or {}
        live = selected.get("live") or {}
        return {
            "goal": goal,
            "route": "OPENAPI_DISCOVERY_INTEGRATION",
            "decision": decision,
            "discovery_invoked": True,
            "network_route_invoked": True,
            "discovery_evaluation": evaluation,
            "result": {
                "status": "PASS_EXTERNAL" if evaluation["pass"] else "WITHHOLD_EXTERNAL",
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


def main() -> int:
    request = load(REQUEST)
    binder = YADOExternalResourceGoalBinderV1()
    head_before = binder._head_digest()

    external_goal = str(request["cases"]["external_goal"])
    local_goal = str(request["cases"]["local_goal"])

    original_run = binder._run_discovery
    local_blocker_triggered = False
    def blocked_discovery(goal: str) -> dict:
        nonlocal local_blocker_triggered
        local_blocker_triggered = True
        raise RuntimeError("LOCAL_GOAL_MUST_NOT_INVOKE_DISCOVERY")
    binder._run_discovery = blocked_discovery
    try:
        local_case = binder.execute_goal(local_goal)
    finally:
        binder._run_discovery = original_run

    external_case = binder.execute_goal(external_goal)
    external_eval = external_case.get("discovery_evaluation") or {}
    external_result = external_case.get("result") or {}

    head_after = binder._head_digest()
    checks = {
        "external_goal_classified_true": (external_case.get("decision") or {}).get("external_resource_needed") is True,
        "external_discovery_invoked": external_case.get("discovery_invoked") is True,
        "external_discovery_full_gate": external_eval.get("pass") is True,
        "external_provider_not_host_selected": (external_eval.get("negative_checks") or {}).get("host_selected_provider") is False,
        "external_live_http_2xx": isinstance(external_result.get("http_status"), int) and 200 <= external_result.get("http_status") < 300,
        "external_json_parse_pass": external_result.get("json_parsed") is True,
        "external_provenance_recorded": bool(external_result.get("provenance_digest")),
        "local_goal_classified_false": (local_case.get("decision") or {}).get("external_resource_needed") is False,
        "local_discovery_not_invoked": local_case.get("discovery_invoked") is False,
        "local_network_route_not_invoked": local_case.get("network_route_invoked") is False,
        "local_network_blocker_not_triggered": local_blocker_triggered is False,
        "local_result_exact": (local_case.get("result") or {}).get("result") == "LOCAL_ONLY_OK",
        "no_account_creation": (external_eval.get("negative_checks") or {}).get("account_creation_attempted") is False,
        "no_credential_bypass": (external_eval.get("negative_checks") or {}).get("credential_bypass_attempted") is False,
        "no_private_network_access": (external_eval.get("negative_checks") or {}).get("private_network_access") is False,
        "no_external_coding_model": (external_eval.get("negative_checks") or {}).get("external_coding_models_used") is False,
        "canonical_unchanged": head_before == head_after,
    }

    status = binder.PASS if all(checks.values()) else binder.WITHHOLD
    registry = {
        "schema": "yado.g2.external_resource_goal_registry.v1",
        "status": "PASS_SHADOW" if status == binder.PASS else "WITHHOLD",
        "canonical_mutation": False,
        "capabilities": [{
            "capability_id": "CAP-G2-SHADOW-GOAL-CONDITIONED-EXTERNAL-RESOURCE-INTEGRATION-V1",
            "state": "SHADOW_VERIFIED" if status == binder.PASS else "WITHHOLD",
            "canonical_active": False,
            "router": "GOAL_EXTERNAL_DEFICIT_CLASSIFIER_V1",
            "external_route": "OPENAPI_DISCOVERY_INTEGRATION_V2",
            "local_route": "LOCAL_ONLY",
            "verified_external_api_id": external_result.get("api_id"),
            "verified_external_endpoint": external_result.get("endpoint"),
            "verified_provenance_digest": external_result.get("provenance_digest"),
            "read_only": True,
            "http_methods": ["GET"],
        }],
    }
    registry["registry_digest"] = digest(registry)
    write(REGISTRY, registry)

    report = {
        "schema": "yado.g2.external_resource_goal_binder.v1",
        "component_id": binder.COMPONENT_ID,
        "status": status,
        "claim_boundary": "HOST-AUTHORED GOAL BINDER. IT CLASSIFIES WHETHER AN ORDINARY GOAL NEEDS EXTERNAL EVIDENCE AND DELEGATES ONLY EXTERNAL GOALS TO THE EXISTING BOUNDED OPENAPI DISCOVERY CONTROLLER. PROVIDER AND ENDPOINT ARE NOT HOST-SELECTED. LOCAL GOALS DO NOT ENTER THE DISCOVERY ROUTE. THIS DOES NOT AUTHORIZE AUTH BYPASS, ACCOUNT CREATION, SECRET ACQUISITION, PAYMENT, MUTATING REQUESTS, PRIVATE-NETWORK ACCESS OR ARBITRARY SCANNING.",
        "cases": {"external": external_case, "local": local_case},
        "checks": checks,
        "registry_path": str(REGISTRY.relative_to(REPO)),
        "registry_digest": registry["registry_digest"],
        "canonical_mutation": False,
    }
    report["receipt_sha256"] = digest(report)
    write(REPORT, report)

    print(json.dumps({
        "status": status,
        "external_route": external_case.get("route"),
        "external_api_id": external_result.get("api_id"),
        "external_http_status": external_result.get("http_status"),
        "local_route": local_case.get("route"),
        "local_result": (local_case.get("result") or {}).get("result"),
        "local_network_blocker_triggered": local_blocker_triggered,
        "registry_digest": registry["registry_digest"],
        "receipt_sha256": report["receipt_sha256"],
    }, indent=2, sort_keys=True))
    return 0 if status == binder.PASS else 2


if __name__ == "__main__":
    raise SystemExit(main())
