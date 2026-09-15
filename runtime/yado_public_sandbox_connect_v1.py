#!/usr/bin/env python3
"""YADO public sandbox execution adapter v1.

Connects to explicitly allow-listed public code-execution sandboxes and performs
small deterministic probes. No credentials are embedded or discovered.
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any

JUDGE0 = "https://ce.judge0.com"
RUNLET = "https://runlet.codealong.live"
ALLOWED_ENDPOINTS = {JUDGE0, RUNLET}
USER_AGENT = "YADO-Public-Sandbox-Connect/1.0"


@dataclass
class ProbeResult:
    provider: str
    endpoint: str
    connected: bool
    executed: bool
    status: str
    stdout: str = ""
    stderr: str = ""
    detail: str = ""


def _request(url: str, *, method: str = "GET", payload: dict[str, Any] | None = None,
             timeout: float = 12.0) -> Any:
    parsed = urllib.parse.urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    if base not in ALLOWED_ENDPOINTS or parsed.scheme != "https":
        raise ValueError(f"endpoint_not_allowed:{base}")
    data = None
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read(1_000_000)
    return json.loads(raw.decode("utf-8"))


def probe_runlet() -> ProbeResult:
    try:
        health = _request(f"{RUNLET}/health")
        if str(health.get("status", "")).lower() != "healthy":
            return ProbeResult("runlet", RUNLET, True, False, "DEGRADED", detail=str(health))
        runtimes = _request(f"{RUNLET}/runtimes")
        names = " ".join(str(r.get("language_name", "")).lower() for r in runtimes)
        if "python" not in names:
            return ProbeResult("runlet", RUNLET, True, False, "NO_PYTHON_RUNTIME")
        code = "value=sum(i*i for i in range(1,8)); print('YADO_SANDBOX_OK', value)"
        result = _request(
            f"{RUNLET}/execute",
            method="POST",
            payload={"language": "python", "code": code, "stdin": ""},
        )
        stdout = str(result.get("stdout") or "")
        stderr = str(result.get("stderr") or "")
        ok = result.get("status") == "OK" and "YADO_SANDBOX_OK 140" in stdout
        return ProbeResult(
            "runlet", RUNLET, True, ok,
            "PASS_PUBLIC_SANDBOX_EXECUTION" if ok else f"EXECUTION_{result.get('status', 'UNKNOWN')}",
            stdout=stdout, stderr=stderr,
        )
    except Exception as exc:  # evidence path: provider failure should not crash fallback
        return ProbeResult("runlet", RUNLET, False, False, "UNAVAILABLE", detail=f"{type(exc).__name__}:{exc}")


def _judge0_python_language_id() -> int:
    languages = _request(f"{JUDGE0}/languages")
    candidates: list[tuple[int, str]] = []
    for item in languages:
        name = str(item.get("name", ""))
        if "python" in name.lower() and "python 2" not in name.lower():
            candidates.append((int(item["id"]), name))
    if not candidates:
        raise RuntimeError("judge0_python_runtime_not_found")
    return max(candidates, key=lambda x: x[0])[0]


def probe_judge0(*, polls: int = 12, poll_delay: float = 0.8) -> ProbeResult:
    try:
        language_id = _judge0_python_language_id()
        source = "value=sum(i*i for i in range(1,8))\nprint('YADO_SANDBOX_OK', value)\n"
        created = _request(
            f"{JUDGE0}/submissions/?base64_encoded=false&wait=false",
            method="POST",
            payload={"source_code": source, "language_id": language_id},
        )
        token = created.get("token")
        if not token:
            return ProbeResult("judge0", JUDGE0, True, False, "SUBMISSION_REJECTED", detail=str(created))
        for _ in range(polls):
            result = _request(
                f"{JUDGE0}/submissions/{urllib.parse.quote(str(token))}?base64_encoded=false&fields=stdout,stderr,status"
            )
            status = result.get("status") or {}
            status_id = int(status.get("id", 0) or 0)
            if status_id in (1, 2):
                time.sleep(poll_delay)
                continue
            stdout = str(result.get("stdout") or "")
            stderr = str(result.get("stderr") or "")
            ok = status_id == 3 and "YADO_SANDBOX_OK 140" in stdout
            return ProbeResult(
                "judge0", JUDGE0, True, ok,
                "PASS_PUBLIC_SANDBOX_EXECUTION" if ok else f"EXECUTION_{status.get('description', status_id)}",
                stdout=stdout, stderr=stderr,
            )
        return ProbeResult("judge0", JUDGE0, True, False, "TIMEOUT_WAITING_FOR_RESULT")
    except Exception as exc:
        return ProbeResult("judge0", JUDGE0, False, False, "UNAVAILABLE", detail=f"{type(exc).__name__}:{exc}")


def run_fallback_order() -> dict[str, Any]:
    results = [probe_judge0()]
    if not results[-1].executed:
        results.append(probe_runlet())
    success = next((r for r in results if r.executed), None)
    return {
        "schema": "yado.public_sandbox_connect.v1",
        "status": "PASS_REAL_EXTERNAL_CODE_EXECUTION" if success else "BLOCKED_NO_PUBLIC_SANDBOX_AVAILABLE",
        "selected_provider": success.provider if success else None,
        "credentials_used": False,
        "provider_fallback_used": len(results) > 1,
        "canonical_mutation": False,
        "results": [asdict(r) for r in results],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=("auto", "judge0", "runlet"), default="auto")
    args = parser.parse_args()
    if args.provider == "judge0":
        report = {"schema": "yado.public_sandbox_connect.v1", "results": [asdict(probe_judge0())]}
    elif args.provider == "runlet":
        report = {"schema": "yado.public_sandbox_connect.v1", "results": [asdict(probe_runlet())]}
    else:
        report = run_fallback_order()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if args.provider == "auto":
        return 0 if report["status"] == "PASS_REAL_EXTERNAL_CODE_EXECUTION" else 2
    return 0 if report["results"][0]["executed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
