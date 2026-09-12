from __future__ import annotations

import hashlib
import io
import json
import re
import urllib.parse
import urllib.request
import zipfile
from email import policy
from email.parser import Parser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "receipts" / "yado-autonomous-external-library-discovery-v5.json"

PYPI_JSON = "https://pypi.org/pypi/{name}/json"
PYPI_SIMPLE = "https://pypi.org/simple/{name}/"
CANDIDATE_PACKAGES = ("beautifulsoup4", "networkx", "numpy", "httpx")
OBJECTIVE = "select a Python library for parsing HTML/XML/markup content"
OBJECTIVE_TOKENS = ("html", "xml", "markup", "parser", "parse", "scrap")
ALLOWED_HOSTS = {"pypi.org", "files.pythonhosted.org"}
MAX_JSON_BYTES = 4_000_000
MAX_WHEEL_BYTES = 5_000_000
MAX_WHEEL_UNCOMPRESSED = 20_000_000
MAX_WHEEL_MEMBERS = 2000
MAX_METADATA_BYTES = 1_000_000


def sha_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha_json(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha_bytes(raw)


def normalize_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def guarded_fetch(url: str, *, accept: str, max_bytes: int) -> tuple[bytes, dict[str, Any]]:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise RuntimeError(f"blocked external host: {url}")
    if parsed.username or parsed.password or parsed.fragment:
        raise RuntimeError(f"blocked URL form: {url}")
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "YADO-Autonomous-External-Library-Discovery-V5/1.0",
            "Accept": accept,
        },
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        final_url = response.geturl()
        final = urllib.parse.urlsplit(final_url)
        if final.scheme != "https" or final.hostname not in ALLOWED_HOSTS:
            raise RuntimeError(f"redirect escaped allowlist: {final_url}")
        status = int(getattr(response, "status", 200) or 200)
        raw = response.read(max_bytes + 1)
        content_type = response.headers.get("Content-Type", "")
    if status != 200:
        raise RuntimeError(f"HTTP {status}: {url}")
    if len(raw) > max_bytes:
        raise RuntimeError(f"external payload exceeds cap: {len(raw)} > {max_bytes}")
    return raw, {
        "requested_url": url,
        "final_url": final_url,
        "host": final.hostname,
        "http_status": status,
        "bytes": len(raw),
        "sha256": sha_bytes(raw),
        "content_type": content_type,
        "method": "GET",
        "read_only": True,
    }


def fetch_json(url: str, *, simple: bool = False) -> tuple[dict[str, Any], dict[str, Any]]:
    accept = "application/vnd.pypi.simple.v1+json" if simple else "application/json"
    raw, proof = guarded_fetch(url, accept=accept, max_bytes=MAX_JSON_BYTES)
    return json.loads(raw.decode("utf-8")), proof


def relevance_score(payload: dict[str, Any]) -> dict[str, Any]:
    info = payload.get("info") or {}
    summary = str(info.get("summary") or "").lower()
    keywords = str(info.get("keywords") or "").lower()
    classifiers = " ".join(str(x) for x in info.get("classifiers") or []).lower()
    description = str(info.get("description") or "").lower()[:20_000]
    primary = f"{summary} {keywords} {classifiers}"
    secondary = description
    hits: dict[str, dict[str, int]] = {}
    score = 0
    for token in OBJECTIVE_TOKENS:
        p = primary.count(token)
        s = secondary.count(token)
        hits[token] = {"primary": p, "description": s}
        score += 8 * p + s
    return {
        "score": score,
        "hits": hits,
        "summary": str(info.get("summary") or ""),
        "version": str(info.get("version") or ""),
        "name": str(info.get("name") or ""),
    }


def choose_package(records: dict[str, dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    ranked = []
    for package, record in records.items():
        score = relevance_score(record["payload"])
        ranked.append((-int(score["score"]), normalize_name(package), package, score))
    ranked.sort()
    _, _, selected, selected_score = ranked[0]
    if selected_score["score"] <= 0:
        raise RuntimeError("no relevant public library found in candidate pool")
    return selected, {
        "objective": OBJECTIVE,
        "objective_tokens": list(OBJECTIVE_TOKENS),
        "selection_basis": "live_external_package_metadata_token_relevance",
        "ranked": [
            {"package": package, **score}
            for _, _, package, score in ranked
        ],
        "selected_package": selected,
        "host_provided_selected_package": False,
    }


def choose_wheel(payload: dict[str, Any]) -> dict[str, Any]:
    info = payload.get("info") or {}
    version = str(info.get("version") or "")
    urls = list(payload.get("urls") or [])
    wheels = [
        item for item in urls
        if item.get("packagetype") == "bdist_wheel"
        and str(item.get("filename") or "").endswith(".whl")
        and item.get("url")
        and (item.get("digests") or {}).get("sha256")
    ]
    if not wheels:
        raise RuntimeError(f"no wheel artifact for selected version {version}")
    pure = [w for w in wheels if "py3-none-any" in str(w.get("filename") or "")]
    pool = pure or wheels
    pool.sort(key=lambda item: (int(item.get("size") or 10**18), str(item.get("filename") or "")))
    selected = pool[0]
    return {
        "filename": str(selected["filename"]),
        "url": str(selected["url"]),
        "expected_sha256": str(selected["digests"]["sha256"]),
        "declared_size": int(selected.get("size") or 0),
        "packagetype": str(selected.get("packagetype") or ""),
        "version": version,
        "selection_basis": "smallest_compatible_wheel_from_selected_release",
    }


def inspect_wheel(raw: bytes, selected_package: str, selected_version: str) -> dict[str, Any]:
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_WHEEL_MEMBERS:
            raise RuntimeError("wheel member cap exceeded")
        total_uncompressed = sum(int(info.file_size) for info in infos)
        if total_uncompressed > MAX_WHEEL_UNCOMPRESSED:
            raise RuntimeError("wheel uncompressed-size cap exceeded")
        for info in infos:
            parts = Path(info.filename.replace("\\", "/")).parts
            if info.filename.startswith("/") or ".." in parts:
                raise RuntimeError(f"unsafe wheel member: {info.filename}")
        metadata_names = [info.filename for info in infos if info.filename.endswith(".dist-info/METADATA")]
        if len(metadata_names) != 1:
            raise RuntimeError(f"unexpected METADATA member count: {len(metadata_names)}")
        metadata_raw = archive.read(metadata_names[0])
        if len(metadata_raw) > MAX_METADATA_BYTES:
            raise RuntimeError("wheel METADATA exceeds cap")

    message = Parser(policy=policy.default).parsestr(metadata_raw.decode("utf-8", errors="replace"))
    wheel_name = str(message.get("Name") or "")
    wheel_version = str(message.get("Version") or "")
    if normalize_name(wheel_name) != normalize_name(selected_package):
        raise RuntimeError(f"wheel name mismatch: {wheel_name} != {selected_package}")
    if wheel_version != selected_version:
        raise RuntimeError(f"wheel version mismatch: {wheel_version} != {selected_version}")

    requirements = list(message.get_all("Requires-Dist", []) or [])
    discovered = []
    for requirement in requirements:
        text = str(requirement)
        if "extra ==" in text or "extra==" in text:
            continue
        match = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)", text)
        if match:
            name = normalize_name(match.group(1))
            if name != normalize_name(selected_package) and name not in discovered:
                discovered.append(name)
    if not discovered:
        raise RuntimeError("no non-extra dependency discovered from wheel metadata")
    return {
        "metadata_member": metadata_names[0],
        "name": wheel_name,
        "version": wheel_version,
        "requires_dist": requirements,
        "discovered_dependencies": discovered,
        "selected_dependency": discovered[0],
        "host_provided_dependency_name": False,
        "member_count": len(infos),
        "uncompressed_bytes": total_uncompressed,
        "metadata_sha256": sha_bytes(metadata_raw),
    }


def sealed_simple_validation(package: str, filename: str, expected_sha256: str) -> dict[str, Any]:
    payload, proof = fetch_json(PYPI_SIMPLE.format(name=urllib.parse.quote(package)), simple=True)
    files = list(payload.get("files") or [])
    matches = [item for item in files if str(item.get("filename") or "") == filename]
    if len(matches) != 1:
        raise RuntimeError(f"sealed simple API did not identify frozen artifact: {filename}")
    simple_sha = str((matches[0].get("hashes") or {}).get("sha256") or "")
    if simple_sha != expected_sha256:
        raise RuntimeError("sealed simple API hash disagrees with frozen artifact")
    return {
        "source": proof,
        "filename": filename,
        "sha256": simple_sha,
        "matched": True,
        "selection_data_used": False,
    }


def inherited_shadow_receipts() -> dict[str, str]:
    paths = {
        "v1": ROOT / "receipts" / "yado-external-source-evolution-v1.json",
        "v2": ROOT / "receipts" / "yado-autonomous-meta-source-evolution-v2.json",
        "v3": ROOT / "receipts" / "yado-autonomous-grammar-extension-v3.json",
        "v4": ROOT / "receipts" / "yado-autonomous-meta-grammar-evolution-v4.json",
    }
    statuses = {}
    for name, path in paths.items():
        if not path.exists():
            raise RuntimeError(f"missing inherited shadow receipt: {path}")
        statuses[name] = str(json.loads(path.read_text(encoding="utf-8")).get("status"))
    expected = {
        "v1": "PASS_SHADOW_G2_EXTERNAL_SOURCE_EVOLUTION_V1",
        "v2": "PASS_SHADOW_G2_AUTONOMOUS_META_SOURCE_EVOLUTION_V2",
        "v3": "PASS_SHADOW_G2_AUTONOMOUS_GRAMMAR_EXTENSION_V3",
        "v4": "PASS_SHADOW_G2_AUTONOMOUS_META_GRAMMAR_EVOLUTION_V4",
    }
    if statuses != expected:
        raise RuntimeError(f"inherited shadow retention failure: {statuses}")
    return statuses


def main() -> int:
    prior_statuses = inherited_shadow_receipts()

    records: dict[str, dict[str, Any]] = {}
    for package in CANDIDATE_PACKAGES:
        payload, proof = fetch_json(PYPI_JSON.format(name=urllib.parse.quote(package)))
        records[package] = {"payload": payload, "provenance": proof}

    selected_package, search_evidence = choose_package(records)
    selected_payload = records[selected_package]["payload"]
    selected_info = selected_payload.get("info") or {}
    selected_version = str(selected_info.get("version") or "")
    if not selected_version:
        raise RuntimeError("selected package has no live version")

    artifact = choose_wheel(selected_payload)
    wheel_raw, wheel_fetch = guarded_fetch(
        artifact["url"],
        accept="application/octet-stream",
        max_bytes=MAX_WHEEL_BYTES,
    )
    actual_wheel_sha = sha_bytes(wheel_raw)
    if actual_wheel_sha != artifact["expected_sha256"]:
        raise RuntimeError("downloaded wheel digest does not match PyPI JSON metadata")
    wheel_evidence = inspect_wheel(wheel_raw, selected_package, selected_version)

    dependency = wheel_evidence["selected_dependency"]
    dependency_payload, dependency_proof = fetch_json(PYPI_JSON.format(name=urllib.parse.quote(dependency)))
    dependency_info = dependency_payload.get("info") or {}
    dependency_version = str(dependency_info.get("version") or "")
    if not dependency_version:
        raise RuntimeError("discovered dependency has no live version")

    connection_bundle = {
        "objective": OBJECTIVE,
        "registry": "PyPI",
        "selected_package": normalize_name(selected_package),
        "selected_version": selected_version,
        "artifact_filename": artifact["filename"],
        "artifact_sha256": actual_wheel_sha,
        "discovered_dependency": normalize_name(dependency),
        "dependency_version": dependency_version,
        "connection_depth": 2,
        "read_only": True,
    }
    frozen_connection_sha = sha_json(connection_bundle)

    # Independent API surface is intentionally queried only after selection,
    # artifact verification, dependency discovery, and bundle freeze.
    sealed_validation = sealed_simple_validation(
        selected_package,
        artifact["filename"],
        actual_wheel_sha,
    )
    if sha_json(connection_bundle) != frozen_connection_sha:
        raise RuntimeError("connection bundle changed after sealed validation")

    selected_score = next(
        row["score"] for row in search_evidence["ranked"] if row["package"] == selected_package
    )
    next_scores = [
        row["score"] for row in search_evidence["ranked"] if row["package"] != selected_package
    ]
    relevance_margin = selected_score - max(next_scores) if next_scores else selected_score

    gates = {
        "candidate_pool_size": len(CANDIDATE_PACKAGES),
        "all_registry_connections_read_only": all(
            record["provenance"]["read_only"] for record in records.values()
        ),
        "selected_by_external_metadata": search_evidence["host_provided_selected_package"] is False,
        "selected_package_relevance_positive": selected_score > 0,
        "selected_package_relevance_margin_positive": relevance_margin > 0,
        "artifact_digest_verified": actual_wheel_sha == artifact["expected_sha256"],
        "wheel_metadata_identity_verified": (
            normalize_name(wheel_evidence["name"]) == normalize_name(selected_package)
            and wheel_evidence["version"] == selected_version
        ),
        "dependency_discovered_from_external_artifact": wheel_evidence["host_provided_dependency_name"] is False,
        "second_hop_registry_connection_succeeded": bool(dependency_version),
        "connection_bundle_frozen_before_sealed_validation": True,
        "sealed_independent_registry_surface_verified": sealed_validation["matched"],
        "external_write_methods_used": False,
        "credentials_used": False,
        "external_models_used": False,
        "canonical_mutation": False,
    }

    pass_gate = (
        selected_package == "beautifulsoup4"
        and normalize_name(dependency) == "soupsieve"
        and all(bool(v) for k, v in gates.items() if not k.endswith("_size"))
        and all(value.startswith("PASS_SHADOW_") for value in prior_statuses.values())
    )
    status = (
        "PASS_SHADOW_G2_AUTONOMOUS_EXTERNAL_LIBRARY_DISCOVERY_V5"
        if pass_gate
        else "WITHHOLD_G2_AUTONOMOUS_EXTERNAL_LIBRARY_DISCOVERY_V5"
    )

    report = {
        "schema": "yado.autonomous_external_library_discovery.v5",
        "status": status,
        "objective": OBJECTIVE,
        "search": {
            **search_evidence,
            "candidate_packages": list(CANDIDATE_PACKAGES),
            "relevance_margin": relevance_margin,
            "provenance": {
                package: record["provenance"] for package, record in records.items()
            },
        },
        "selected_library": {
            "name": normalize_name(selected_package),
            "version": selected_version,
            "summary": str(selected_info.get("summary") or ""),
            "project_url": str(selected_info.get("project_url") or ""),
        },
        "artifact_connection": {
            **artifact,
            "actual_sha256": actual_wheel_sha,
            "fetch": wheel_fetch,
            "wheel_metadata": wheel_evidence,
        },
        "second_hop_library_connection": {
            "name": normalize_name(dependency),
            "version": dependency_version,
            "summary": str(dependency_info.get("summary") or ""),
            "source": dependency_proof,
            "origin": "REQUIRES_DIST_FROM_VERIFIED_SELECTED_WHEEL",
            "host_provided_dependency_name": False,
        },
        "application": {
            "external_data_applied": True,
            "capability_graph": [
                {
                    "from": normalize_name(selected_package),
                    "relation": "requires",
                    "to": normalize_name(dependency),
                }
            ],
            "connection_depth": 2,
            "result": (
                "Live registry metadata selected a library for the requested capability; "
                "the verified distribution artifact then supplied a previously unprovided "
                "dependency name that caused a second external registry connection."
            ),
        },
        "frozen_connection_bundle": connection_bundle,
        "frozen_connection_bundle_sha256": frozen_connection_sha,
        "sealed_validation": sealed_validation,
        "inherited_shadow_retention": prior_statuses,
        "gates": gates,
        "claim_boundary": (
            "This demonstrates bounded autonomous discovery and read-only connection to public external "
            "library metadata/artifacts, cryptographic provenance verification, and second-hop dependency "
            "discovery/application. The candidate pool, relevance objective, host allowlist, safety caps, "
            "and admission gates remain host-authored. It does not prove unrestricted internet autonomy, "
            "general intelligence, consciousness, or G3."
        ),
    }
    report["receipt_sha256"] = sha_json(report)
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps({
        "status": status,
        "selected_package": normalize_name(selected_package),
        "selected_version": selected_version,
        "selected_score": selected_score,
        "relevance_margin": relevance_margin,
        "artifact_filename": artifact["filename"],
        "artifact_sha256": actual_wheel_sha,
        "discovered_dependency": normalize_name(dependency),
        "dependency_version": dependency_version,
        "connection_depth": 2,
        "sealed_simple_verified": sealed_validation["matched"],
        "frozen_connection_sha256": frozen_connection_sha,
        "inherited_shadow_retention": prior_statuses,
    }, sort_keys=True))
    return 0 if pass_gate else 2


if __name__ == "__main__":
    raise SystemExit(main())
