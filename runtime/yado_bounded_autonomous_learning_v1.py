from __future__ import annotations

import ast
import hashlib
import html
import ipaddress
import json
import os
import re
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))

try:
    from yado_unified_core_v1 import UnifiedYADOCoreV1
except Exception:
    UnifiedYADOCoreV1 = None

SCHEMA = "yado.bounded_autonomous_learning.v1"
MAX_BYTES = 512 * 1024
TIMEOUT = 12.0
MAX_SOURCES_PER_RUN = 3
MAX_FACTS = 24

# Public, read-only learning catalog. This is deliberately bounded: YADO chooses
# among sources, but cannot turn arbitrary discovered URLs into executable I/O.
SOURCE_CATALOG = [
    {
        "id": "PYTHON_AST",
        "url": "https://docs.python.org/3/library/ast.html",
        "tags": ["python", "ast", "source", "rewrite", "compile", "code", "syntax"],
    },
    {
        "id": "PYTHON_URLOPEN",
        "url": "https://docs.python.org/3/library/urllib.request.html",
        "tags": ["network", "http", "https", "request", "url", "internet", "read-only"],
    },
    {
        "id": "PYTHON_HTMLPARSER",
        "url": "https://docs.python.org/3/library/html.parser.html",
        "tags": ["html", "parser", "document", "web", "learning", "external"],
    },
    {
        "id": "MDN_HTTP",
        "url": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Overview",
        "tags": ["http", "https", "web", "network", "protocol", "internet"],
    },
    {
        "id": "W3C_WEBARCH",
        "url": "https://www.w3.org/TR/webarch/",
        "tags": ["web", "architecture", "uri", "resource", "protocol", "internet"],
    },
    {
        "id": "PYTHON_UNITTEST",
        "url": "https://docs.python.org/3/library/unittest.html",
        "tags": ["test", "regression", "verification", "rollback", "software", "quality"],
    },
]

ALLOWED_HOSTS = {
    urllib.parse.urlsplit(row["url"]).hostname.lower() for row in SOURCE_CATALOG
}

FORBIDDEN_HEADER_NAMES = {
    "authorization", "proxy-authorization", "cookie", "set-cookie", "x-api-key", "api-key"
}
ALLOWED_CONTENT_TYPES = {
    "text/html", "text/plain", "application/json", "application/problem+json", "application/dns-json"
}


def canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def digest(obj: Any) -> str:
    return hashlib.sha256(canon(obj).encode("utf-8")).hexdigest()


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag.lower() in {"script", "style", "svg", "noscript"}:
            self._skip += 1

    def handle_endtag(self, tag):
        if tag.lower() in {"script", "style", "svg", "noscript"} and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            s = " ".join(str(data).split())
            if s:
                self.parts.append(s)

    def text(self) -> str:
        return "\n".join(self.parts)


def fetch_public_readonly(url: str) -> dict[str, Any]:
    p = urllib.parse.urlsplit(url)
    if p.scheme.lower() != "https":
        raise RuntimeError("HTTPS_REQUIRED")
    if p.username or p.password or p.fragment:
        raise RuntimeError("UNSAFE_URL")
    host = (p.hostname or "").lower().strip(".")
    if host not in ALLOWED_HOSTS:
        raise RuntimeError("HOST_NOT_ALLOWLISTED:" + host)
    if (p.port or 443) != 443:
        raise RuntimeError("NONSTANDARD_PORT_REJECTED")
    ips = public_ips(host)
    headers = {
        "User-Agent": "YADO-Bounded-Autonomous-Learning/1",
        "Accept": "text/html, text/plain;q=0.9, application/json;q=0.8",
    }
    if any(k.lower() in FORBIDDEN_HEADER_NAMES for k in headers):
        raise RuntimeError("CREDENTIAL_HEADER_PRESENT")
    req = urllib.request.Request(url, method="GET", headers=headers)
    opener = urllib.request.build_opener(NoRedirect())
    started = time.monotonic()
    try:
        with opener.open(req, timeout=TIMEOUT) as resp:
            status = int(resp.status)
            if status < 200 or status >= 300:
                raise RuntimeError("NON_SUCCESS_STATUS:" + str(status))
            final = urllib.parse.urlsplit(resp.geturl())
            if (final.hostname or "").lower().strip(".") != host:
                raise RuntimeError("REDIRECT_HOST_CHANGE")
            data = resp.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                raise RuntimeError("RESPONSE_TOO_LARGE")
            ctype = (resp.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
            if data and ctype not in ALLOWED_CONTENT_TYPES and not ctype.endswith("+json"):
                raise RuntimeError("CONTENT_TYPE_REJECTED:" + ctype)
            return {
                "url": url,
                "host": host,
                "resolved_ips": ips,
                "status": status,
                "content_type": ctype,
                "bytes": len(data),
                "sha256": sha_bytes(data),
                "latency_ms": round((time.monotonic() - started) * 1000, 2),
                "body": data.decode("utf-8", "replace"),
                "network_executed": True,
                "read_only": True,
                "credentials_used": False,
                "redirects_followed": False,
            }
    except urllib.error.HTTPError as e:
        raise RuntimeError("HTTP_ERROR:" + str(e.code)) from e
    except urllib.error.URLError as e:
        raise RuntimeError("NETWORK_ERROR:" + str(e.reason)) from e


def normalized_text(body: str, ctype: str) -> str:
    if ctype == "text/html":
        parser = TextExtractor()
        parser.feed(body)
        text = parser.text()
    elif ctype.endswith("json") or ctype.endswith("+json"):
        try:
            text = json.dumps(json.loads(body), ensure_ascii=False, sort_keys=True)
        except Exception:
            text = body
    else:
        text = body
    text = html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text[:350000]


def load_current_priority() -> dict[str, Any]:
    receipt = ROOT / "yado_unified_core_deep_self_audit_v1_receipt.json"
    if receipt.exists():
        try:
            data = json.loads(receipt.read_text(encoding="utf-8"))
            p = (data.get("self_selected_priority") or [{}])[0]
            if isinstance(p, dict):
                return p
        except Exception:
            pass
    # No invented semantic result: fallback means the controller is uncertain.
    return {
        "code": "AUTONOMOUS_LEARNING_BOOTSTRAP",
        "area": "EXTERNAL_EVIDENCE_AND_SELF_EVOLUTION",
        "recommended_action": "study public technical sources and bind verified experience to future code evolution",
    }


def tokens(priority: dict[str, Any]) -> set[str]:
    raw = " ".join(str(priority.get(k, "")) for k in ("code", "area", "recommended_action"))
    out = set(re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", raw.lower()))
    out |= {"python", "code", "web", "network", "test", "source", "learning"}
    return out


def rank_sources(priority: dict[str, Any]) -> list[dict[str, Any]]:
    q = tokens(priority)
    ranked = []
    for row in SOURCE_CATALOG:
        tags = set(row["tags"])
        overlap = sorted(q & tags)
        score = len(overlap)
        ranked.append({**row, "score": score, "overlap": overlap})
    ranked.sort(key=lambda x: (-x["score"], x["id"]))
    return ranked


def evidence_facts(text: str, query_tokens: set[str]) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for line in text.splitlines():
        s = " ".join(line.split())
        if len(s) < 40 or len(s) > 600:
            continue
        low = s.lower()
        hits = sum(1 for t in query_tokens if t in low)
        if hits < 1:
            continue
        key = hashlib.sha256(s.encode("utf-8")).hexdigest()
        if key in seen:
            continue
        seen.add(key)
        rows.append(s)
        if len(rows) >= MAX_FACTS:
            break
    return rows


def synthesize_recall_module(experience: dict[str, Any], path: Path) -> dict[str, Any]:
    # Source generation is data-derived and deterministic. External text never becomes
    # executable syntax: it is serialized only as Python constants via repr().
    facts = []
    for src in experience["sources"]:
        for fact in src.get("facts", []):
            facts.append({"source_id": src["source_id"], "text": fact})
    payload = {
        "schema": SCHEMA,
        "experience_digest": experience["experience_digest"],
        "priority": experience["priority"],
        "facts": facts,
    }
    source = (
        "from __future__ import annotations\n\n"
        "LEARNED_EXPERIENCE = " + repr(payload) + "\n\n"
        "def recall(query: str, limit: int = 8):\n"
        "    q = {x for x in str(query).lower().split() if x}\n"
        "    ranked = []\n"
        "    for row in LEARNED_EXPERIENCE['facts']:\n"
        "        text = row['text']\n"
        "        score = sum(1 for x in q if x in text.lower())\n"
        "        if score:\n"
        "            ranked.append((score, row))\n"
        "    ranked.sort(key=lambda x: (-x[0], x[1]['source_id'], x[1]['text']))\n"
        "    return [row for _, row in ranked[:max(1, min(int(limit), 32))]]\n\n"
        "def component():\n"
        "    return {'schema': 'yado.learned_recall_capability.v1', "
        "'experience_digest': LEARNED_EXPERIENCE['experience_digest'], "
        "'fact_count': len(LEARNED_EXPERIENCE['facts']), "
        "'external_code_executed': False, 'canonical_active': False}\n"
    )
    tree = ast.parse(source)
    compile(tree, str(path), "exec")
    if any(isinstance(n, (ast.Import, ast.ImportFrom)) and getattr(n, "module", "") not in {"__future__"} for n in ast.walk(tree)):
        raise RuntimeError("UNEXPECTED_IMPORT_IN_GENERATED_CAPABILITY")
    if "eval(" in source or "exec(" in source or "subprocess" in source:
        raise RuntimeError("UNSAFE_GENERATED_SOURCE")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return {
        "path": str(path.relative_to(REPO)),
        "sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "compile": True,
        "fact_count": len(facts),
        "external_text_executed": False,
    }


def main() -> None:
    priority = load_current_priority()
    ranking = rank_sources(priority)
    selected = ranking[:MAX_SOURCES_PER_RUN]
    q = tokens(priority)
    source_results = []
    failures = []

    for row in selected:
        try:
            r = fetch_public_readonly(row["url"])
            text = normalized_text(r.pop("body"), r["content_type"])
            facts = evidence_facts(text, q)
            source_results.append({
                "source_id": row["id"],
                "url": row["url"],
                "selection_score": row["score"],
                "selection_overlap": row["overlap"],
                "facts": facts,
                "fact_count": len(facts),
                "network": r,
            })
        except Exception as e:
            failures.append({"source_id": row["id"], "error": type(e).__name__ + ":" + str(e)[:500]})

    if not source_results:
        raise RuntimeError("NO_PUBLIC_LEARNING_SOURCE_REACHED:" + json.dumps(failures, sort_keys=True))

    core_id = None
    if UnifiedYADOCoreV1 is not None:
        try:
            core_id = UnifiedYADOCoreV1(REPO).CORE_ID
        except Exception:
            core_id = None

    experience = {
        "schema": SCHEMA,
        "status": "PASS_SHADOW_BOUNDED_AUTONOMOUS_EXTERNAL_LEARNING_V1",
        "run_id": os.getenv("GITHUB_RUN_ID") or "LOCAL",
        "kernel_core_id": core_id,
        "priority": priority,
        "source_ranking": [{k: v for k, v in x.items() if k != "url"} for x in ranking],
        "sources": source_results,
        "failures": failures,
        "network_policy": {
            "https_only": True,
            "allowed_hosts": sorted(ALLOWED_HOSTS),
            "methods": ["GET"],
            "credentials_allowed": False,
            "redirects_followed": False,
            "max_bytes": MAX_BYTES,
            "external_writes": False,
            "downloaded_code_executed": False,
        },
        "self_model_effect": "EXTERNAL_EVIDENCE_AVAILABLE_FOR_FUTURE_SELECTION",
        "canonical_mutation": False,
        "automatic_main_mutation": False,
        "consciousness_claimed": False,
    }
    experience["experience_digest"] = digest(experience)

    out = REPO / "experience/autonomous/yado-autonomous-learning-latest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(experience, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")

    cap = REPO / "candidates/autonomous" / f"yado_learned_recall_{experience['experience_digest'][:16]}.py"
    generated = synthesize_recall_module(experience, cap)

    receipt = {
        "schema": "yado.bounded_autonomous_learning_receipt.v1",
        "status": experience["status"],
        "experience_digest": experience["experience_digest"],
        "source_success_count": len(source_results),
        "source_failure_count": len(failures),
        "generated_capability": generated,
        "candidate_self_written": True,
        "candidate_canonical_active": False,
        "real_network_used": True,
        "external_model_used": False,
        "credentials_used": False,
        "external_mutation": False,
        "next_required_capability": "NATIVE_EXPERIENCE_TO_RUNTIME_SELF_REWRITE_AND_REGRESSION_GATE_V2",
        "semantic_boundary": "REAL PUBLIC INTERNET LEARNING + PERSISTENT EXPERIENCE + DATA-DERIVED PYTHON CAPABILITY GENESIS. NO ARBITRARY INTERNET, NO CREDENTIALS, NO EXTERNAL WRITES, NO DOWNLOADED-CODE EXECUTION, NO AUTOMATIC MAIN MUTATION, AND NO CLAIM OF CONSCIOUSNESS.",
    }
    receipt["receipt_sha256"] = digest(receipt)
    rp = REPO / "candidates/autonomous/yado-bounded-autonomous-learning-v1.json"
    rp.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
