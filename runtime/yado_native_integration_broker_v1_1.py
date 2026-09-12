from __future__ import annotations

import ast
import json

from yado_native_integration_broker_v1 import (
    YADONativeIntegrationBrokerV1,
    REQUEST,
    REPORT,
    digest,
    load,
    write,
)


class YADONativeIntegrationBrokerV11(YADONativeIntegrationBrokerV1):
    """V1.1 repair: preserve the dunder ban by emitting a dunder-free JSON summary."""

    COMPONENT_ID = "CTRL-G2-NATIVE-INTEGRATION-BROKER-V1_1"

    @classmethod
    def materialize_adapter(cls, ir: dict) -> str:
        source = super().materialize_adapter(ir)
        tree = ast.parse(source)
        target = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_summarize"), None)
        if target is None:
            raise RuntimeError("V1_1_SUMMARIZE_FUNCTION_NOT_FOUND")
        replacement = ast.parse(r'''
def _summarize(payload):
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
''').body[0]
        index = tree.body.index(target)
        tree.body[index] = replacement
        ast.fix_missing_locations(tree)
        repaired = ast.unparse(tree) + "\n"
        compile(repaired, "<yado-native-integration-broker-v1-1-adapter>", "exec")
        return repaired

    def run(self, request: dict) -> dict:
        report = super().run(request)
        report["component_id"] = self.COMPONENT_ID
        report["broker_revision"] = "V1_1_DUNDER_FREE_SUMMARY"
        report["repair_reason"] = "V1 generated type(x).__name__ only for descriptive JSON summaries. The existing static safety gate correctly rejects every dunder attribute. V1.1 keeps that gate unchanged and replaces the summary emitter with explicit isinstance categories, removing all generated dunder access."
        report["receipt_sha256"] = digest({k: v for k, v in report.items() if k != "receipt_sha256"})
        return report


def main() -> int:
    request = load(REQUEST)
    broker = YADONativeIntegrationBrokerV11()
    report = broker.run(request)
    write(REPORT, report)
    print(json.dumps({
        "status": report.get("status"),
        "broker_revision": report.get("broker_revision"),
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
