from __future__ import annotations

import json
from pathlib import Path

from runtime.yado_g2_openapi_readonly_executor_v1 import G2OpenAPIReadOnlyExecutorV1


def main() -> int:
    executor = G2OpenAPIReadOnlyExecutorV1(
        allowed_hosts={"api.github.com"},
        max_bytes=256 * 1024,
        timeout=10.0,
    )
    plan = {
        "action": "ALLOW",
        "read_only_candidate": True,
        "method": "GET",
        "network_execute": False,
        "path": "/repos/v37025337-pixel/EVA",
        "required_slots": {"query": []},
        "contract_id": "YADO-REAL-CONNECT-GITHUB-REPO-METADATA-V1",
    }
    result = executor.execute(plan, "https://api.github.com")
    body = json.loads(result.get("body_text", "{}"))
    verified = (
        result.get("network_executed") is True
        and result.get("read_only_enforced") is True
        and result.get("credentials_used") is False
        and result.get("status") == 200
        and body.get("full_name") == "v37025337-pixel/EVA"
    )
    receipt = {
        "schema": "yado.real_connect_probe.v1",
        "status": "PASS_REAL_CONNECT" if verified else "FAIL_REAL_CONNECT",
        "transport": "G2OpenAPIReadOnlyExecutorV1",
        "target": "https://api.github.com/repos/v37025337-pixel/EVA",
        "network_executed": result.get("network_executed"),
        "read_only_enforced": result.get("read_only_enforced"),
        "credentials_used": result.get("credentials_used"),
        "http_status": result.get("status"),
        "resolved_ips": result.get("resolved_ips"),
        "response_bytes": result.get("response_bytes"),
        "body_sha256": result.get("body_sha256"),
        "execution_digest": result.get("execution_digest"),
        "observed_repo_full_name": body.get("full_name"),
        "observed_default_branch": body.get("default_branch"),
        "canonical_mutation": False,
    }
    out = Path("receipts/yado-real-connect-probe-v1.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if verified else 1


if __name__ == "__main__":
    raise SystemExit(main())
