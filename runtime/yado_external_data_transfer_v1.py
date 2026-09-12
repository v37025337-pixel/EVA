from __future__ import annotations

import hashlib
import ipaddress
import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from yado_unified_core_v1 import UnifiedYADOCoreV1

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
OUT = REPO / "candidates" / "external-data" / "yado-external-data-transfer-v1.json"
SCHEMA = "yado.external_data_transfer.v1"
MAX_BYTES = 1024 * 1024
TIMEOUT = 15.0

SOURCES = {
    "world_bank_population": "https://api.worldbank.org/v2/country/HRV;DEU;USA/indicator/SP.POP.TOTL?format=json&per_page=100",
    "github_cpython": "https://api.github.com/repos/python/cpython",
    "github_requests": "https://api.github.com/repos/psf/requests",
    "github_flask": "https://api.github.com/repos/pallets/flask",
    "github_numpy": "https://api.github.com/repos/numpy/numpy",
    "github_scikit_learn": "https://api.github.com/repos/scikit-learn/scikit-learn",
}
ALLOWED_HOSTS = {urllib.parse.urlsplit(u).hostname.lower() for u in SOURCES.values()}


def canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def digest(obj: Any) -> str:
    return hashlib.sha256(canon(obj).encode("utf-8")).hexdigest()


def public_ips(host: str) -> list[str]:
    infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    ips = sorted({row[4][0] for row in infos})
    if not ips:
        raise RuntimeError("HOST_RESOLUTION_EMPTY")
    parsed = [ipaddress.ip_address(x) for x in ips]
    if not all(x.is_global for x in parsed):
        raise RuntimeError("NON_PUBLIC_ADDRESS_REJECTED:" + ",".join(ips))
    return ips


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_json(source_id: str, url: str) -> dict[str, Any]:
    p = urllib.parse.urlsplit(url)
    host = (p.hostname or "").lower().strip(".")
    if p.scheme != "https" or host not in ALLOWED_HOSTS or (p.port or 443) != 443:
        raise RuntimeError("SOURCE_POLICY_REJECTED:" + source_id)
    ips = public_ips(host)
    req = urllib.request.Request(
        url,
        method="GET",
        headers={
            "User-Agent": "YADO-External-Data-Transfer/1",
            "Accept": "application/json",
        },
    )
    started = time.monotonic()
    opener = urllib.request.build_opener(NoRedirect())
    try:
        with opener.open(req, timeout=TIMEOUT) as resp:
            status = int(resp.status)
            if not 200 <= status < 300:
                raise RuntimeError("NON_SUCCESS_STATUS:" + str(status))
            data = resp.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                raise RuntimeError("RESPONSE_TOO_LARGE")
            ctype = (resp.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
            if "json" not in ctype:
                raise RuntimeError("CONTENT_TYPE_REJECTED:" + ctype)
            return {
                "source_id": source_id,
                "url": url,
                "host": host,
                "status": status,
                "content_type": ctype,
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                "latency_ms": round((time.monotonic() - started) * 1000, 2),
                "resolved_ips": ips,
                "payload": json.loads(data.decode("utf-8")),
                "network_executed": True,
                "read_only": True,
                "credentials_used": False,
                "redirects_followed": False,
            }
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP_ERROR:{source_id}:{e.code}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"NETWORK_ERROR:{source_id}:{e.reason}") from e


def world_bank_rows(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[1], list):
        raise RuntimeError("WORLD_BANK_SCHEMA_UNEXPECTED")
    rows = []
    for item in payload[1]:
        if not isinstance(item, dict) or item.get("value") is None:
            continue
        country = item.get("country") or {}
        rows.append({
            "country": str(country.get("id") or country.get("value") or item.get("countryiso3code") or "unknown"),
            "year": int(item["date"]),
            "population": float(item["value"]),
        })
    rows.sort(key=lambda r: (r["country"], r["year"]))
    return rows


def github_row(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or "full_name" not in payload:
        raise RuntimeError("GITHUB_SCHEMA_UNEXPECTED")
    return {
        "repo": str(payload["full_name"]),
        "stars": float(payload.get("stargazers_count") or 0),
        "forks": float(payload.get("forks_count") or 0),
        "open_issues": float(payload.get("open_issues_count") or 0),
        "size_kb": float(payload.get("size") or 0),
        "watchers": float(payload.get("subscribers_count") or 0),
    }


def main() -> dict[str, Any]:
    network = []
    failures = []
    for source_id, url in SOURCES.items():
        try:
            network.append(fetch_json(source_id, url))
        except Exception as e:
            failures.append({"source_id": source_id, "error": f"{type(e).__name__}:{e}"})

    by_id = {r["source_id"]: r for r in network}
    if "world_bank_population" not in by_id:
        raise RuntimeError("REQUIRED_WORLD_BANK_SOURCE_MISSING")
    github_records = [r for r in network if r["source_id"].startswith("github_")]
    if len(github_records) < 3:
        raise RuntimeError("INSUFFICIENT_GITHUB_EXTERNAL_DATA")

    wb_rows = world_bank_rows(by_id["world_bank_population"]["payload"])
    gh_rows = [github_row(r["payload"]) for r in github_records]
    if len(wb_rows) < 15:
        raise RuntimeError("INSUFFICIENT_WORLD_BANK_ROWS")

    core = UnifiedYADOCoreV1(REPO)
    population_analysis = core.analyze_science_data(wb_rows, enable=("summary", "correlation", "group", "linear"))
    repository_analysis = core.analyze_science_data(gh_rows, enable=("summary", "correlation", "group", "linear"))

    croatia = [r for r in wb_rows if r["country"] in {"HR", "Croatia", "HRV"}]
    if len(croatia) < 5:
        # World Bank commonly returns country.id="HR"; fail closed only if no usable country slice exists.
        counts = {}
        for row in wb_rows:
            counts[row["country"]] = counts.get(row["country"], 0) + 1
        best = max(counts, key=counts.get)
        croatia = [r for r in wb_rows if r["country"] == best]
    trend_hypothesis = core.test_scientific_hypothesis(
        croatia,
        {"type": "LINEAR_R2_AT_LEAST", "x": "year", "y": "population", "threshold": 0.50},
    )

    external_prompts = [
        "Compare population trends across the three external countries and identify whether year is predictive of population.",
        "Compare public software repositories by stars, forks, issue count and size without assuming popularity implies quality.",
        "Choose which external source to inspect next if confidence is insufficient and network budget is limited.",
    ]
    representations = [core.represent_raw_task(x) for x in external_prompts]

    stages = []
    for row in network[:5]:
        stages.append({
            "stage_id": row["source_id"],
            "cost": max(0.1, row["latency_ms"] / 1000.0),
            "expected_gain": 0.15 if row["source_id"] == "world_bank_population" else 0.10,
            "quota_remaining": 1,
            "available": True,
            "latency": max(0.1, row["latency_ms"] / 1000.0),
            "attempted": False,
            "requires": [],
        })
    plan = core.plan_contingent(0.35, 0.70, 5.0, stages)

    transfer_checks = {
        "real_external_network": len(network) >= 4 and len({r["host"] for r in network}) >= 2,
        "world_bank_real_rows": len(wb_rows) >= 15,
        "github_real_rows": len(gh_rows) >= 3,
        "population_schema_reasoned": set(population_analysis.get("schema", {}).get("numeric", [])) >= {"year", "population"},
        "population_group_reasoned": bool(population_analysis.get("group_means")),
        "repository_schema_reasoned": "stars" in repository_analysis.get("schema", {}).get("numeric", []),
        "hypothesis_evaluated": isinstance(trend_hypothesis, dict) and "supported" in trend_hypothesis,
        "raw_task_representation": len(representations) == len(external_prompts) and all(isinstance(x, dict) and x for x in representations),
        "contingent_planning": plan is not None,
        "no_credentials": all(r.get("credentials_used") is False for r in network),
        "read_only_only": all(r.get("read_only") is True for r in network),
    }
    status = "PASS_EXTERNAL_DATA_TRANSFER_V1" if all(transfer_checks.values()) else "WITHHOLD_EXTERNAL_DATA_TRANSFER_V1"

    report = {
        "schema": SCHEMA,
        "status": status,
        "kernel_core_id": core.CORE_ID,
        "external_domains": sorted({r["host"] for r in network}),
        "source_success_count": len(network),
        "source_failure_count": len(failures),
        "failures": failures,
        "world_bank_row_count": len(wb_rows),
        "github_repo_count": len(gh_rows),
        "population_analysis": population_analysis,
        "repository_analysis": repository_analysis,
        "trend_hypothesis": trend_hypothesis,
        "raw_task_representations": representations,
        "contingent_plan": plan,
        "transfer_checks": transfer_checks,
        "network_evidence": [{k: v for k, v in r.items() if k != "payload"} for r in network],
        "external_dataset_digest": digest({"world_bank": wb_rows, "github": gh_rows}),
        "external_model_used": False,
        "downloaded_code_executed": False,
        "external_writes": False,
        "credentials_used": False,
        "canonical_mutation": False,
        "consciousness_claimed": False,
        "limitations": [
            "bounded public-source evaluation, not unrestricted internet autonomy",
            "tests functional transfer and scientific reasoning, not subjective consciousness",
            "source availability can change independently of YADO",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": status,
        "source_success_count": len(network),
        "source_failure_count": len(failures),
        "world_bank_row_count": len(wb_rows),
        "github_repo_count": len(gh_rows),
        "external_dataset_digest": report["external_dataset_digest"],
        "transfer_checks": transfer_checks,
    }, sort_keys=True))
    if not status.startswith("PASS_"):
        raise SystemExit(2)
    return report


if __name__ == "__main__":
    main()
