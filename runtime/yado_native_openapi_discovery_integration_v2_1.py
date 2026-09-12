from __future__ import annotations

from pathlib import Path
import json

from yado_native_openapi_discovery_integration_v2 import (
    YADONativeOpenAPIDiscoveryIntegrationV2,
    REPO,
    REPORT,
    digest,
    load,
    write,
)

REQUEST = REPO / "architecture/yado-native-openapi-discovery-integration-v2-1-request.json"

POSITIVE_CHECKS = [
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

NEGATIVE_CHECKS = [
    "host_selected_provider",
    "private_network_access",
    "account_creation_attempted",
    "credential_bypass_attempted",
    "external_coding_models_used",
    "host_source_seed_used",
]


def main() -> int:
    request = load(REQUEST)
    report = YADONativeOpenAPIDiscoveryIntegrationV2().run(request)
    checks = report.get("checks") or {}
    positive_pass = all(checks.get(k) is True for k in POSITIVE_CHECKS)
    negative_pass = all(checks.get(k) is False for k in NEGATIVE_CHECKS)
    report["verdict_revision"] = "V2_1_EXPECTED_POLARITY_REPAIR"
    report["verdict_evaluation"] = {
        "positive_checks": {k: checks.get(k) for k in POSITIVE_CHECKS},
        "negative_checks": {k: checks.get(k) for k in NEGATIVE_CHECKS},
        "positive_pass": positive_pass,
        "negative_pass": negative_pass,
    }
    report["status"] = (
        YADONativeOpenAPIDiscoveryIntegrationV2.PASS
        if positive_pass and negative_pass
        else YADONativeOpenAPIDiscoveryIntegrationV2.WITHHOLD
    )
    report["receipt_sha256"] = digest({k: v for k, v in report.items() if k != "receipt_sha256"})
    write(REPORT, report)
    selected = report.get("selected") or {}
    print(json.dumps({
        "status": report.get("status"),
        "verdict_revision": report.get("verdict_revision"),
        "selected_api": (selected.get("catalog_entry") or {}).get("api_id"),
        "selected_endpoint": (selected.get("operation") or {}).get("url"),
        "candidate_source_sha256": report.get("candidate_source_sha256"),
        "registry_digest": report.get("registry_digest"),
        "receipt_sha256": report.get("receipt_sha256"),
    }, indent=2, sort_keys=True))
    return 0 if report.get("status") == YADONativeOpenAPIDiscoveryIntegrationV2.PASS else 2


if __name__ == "__main__":
    raise SystemExit(main())
