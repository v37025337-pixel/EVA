#!/usr/bin/env python3
"""Bounded real-internet, cross-disciplinary experience acquisition for YADO.

Reads only public HTTPS pages, stores provenance/derived features rather than raw
page text, and produces evidence for later gated cognitive mutation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

SCHEMA = "yado.cross_disciplinary_internet_learning.v1"
USER_AGENT = "YADO-Public-Research/1.0"
STOPWORDS = {
    "about", "after", "again", "against", "also", "another", "because", "been", "before",
    "being", "between", "both", "could", "does", "each", "from", "have", "having", "into",
    "more", "most", "other", "over", "same", "some", "such", "than", "that", "their", "there",
    "these", "they", "this", "those", "through", "under", "using", "very", "what", "when", "where",
    "which", "while", "with", "would", "your", "page", "site", "http", "https", "www"
}


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: List[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, str | None]]) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "noscript", "svg"} and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.parts.append(data)

    def text(self) -> str:
        return re.sub(r"\s+", " ", " ".join(self.parts)).strip()


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def tokens(text: str) -> List[str]:
    out = []
    for token in re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", text.lower()):
        if token not in STOPWORDS and not token.isdigit():
            out.append(token)
    return out


def top_terms(items: Iterable[str], n: int = 30) -> List[Tuple[str, int]]:
    return Counter(items).most_common(n)


def fetch_public_https(url: str, max_bytes: int, timeout: int) -> Dict[str, Any]:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        return {"status": "BLOCKED_NON_HTTPS", "url": url}
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,text/plain;q=0.9,*/*;q=0.1",
        },
        method="GET",
    )
    try:
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            final_url = resp.geturl()
            final = urllib.parse.urlparse(final_url)
            if final.scheme != "https":
                return {"status": "BLOCKED_REDIRECT_NON_HTTPS", "url": url, "final_url": final_url}
            content_type = (resp.headers.get("Content-Type") or "").lower()
            if not ("text/html" in content_type or "text/plain" in content_type or not content_type):
                return {"status": "BLOCKED_CONTENT_TYPE", "url": url, "final_url": final_url, "content_type": content_type}
            data = resp.read(max_bytes + 1)
            truncated = len(data) > max_bytes
            data = data[:max_bytes]
            charset = resp.headers.get_content_charset() or "utf-8"
            text_raw = data.decode(charset, errors="replace")
            if "html" in content_type or "<html" in text_raw[:500].lower():
                parser = TextExtractor()
                parser.feed(text_raw)
                text = parser.text()
            else:
                text = re.sub(r"\s+", " ", text_raw).strip()
            ts = tokens(text)
            return {
                "status": "FETCHED",
                "url": url,
                "final_url": final_url,
                "http_status": getattr(resp, "status", 200),
                "content_type": content_type,
                "sha256": digest_bytes(data),
                "bytes": len(data),
                "truncated": truncated,
                "word_count": len(text.split()),
                "token_count": len(ts),
                "top_terms": top_terms(ts, 35),
                "_tokens": ts,
            }
    except urllib.error.HTTPError as exc:
        return {"status": "HTTP_ERROR", "url": url, "http_status": exc.code, "error": str(exc)}
    except Exception as exc:  # network/SSL/DNS are evidence, not fatal to whole corpus
        return {"status": "FETCH_ERROR", "url": url, "error": f"{type(exc).__name__}: {exc}"}


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def jaccard(a: set[str], b: set[str]) -> float:
    union = a | b
    return 0.0 if not union else len(a & b) / len(union)


def derive_cross_domain(domain_terms: Dict[str, Counter[str]]) -> Dict[str, Any]:
    profiles: Dict[str, set[str]] = {}
    for domain, counter in domain_terms.items():
        profiles[domain] = {term for term, _ in counter.most_common(80)}

    edges = []
    domains = sorted(profiles)
    for i, left in enumerate(domains):
        for right in domains[i + 1 :]:
            shared = sorted(profiles[left] & profiles[right])
            score = round(jaccard(profiles[left], profiles[right]), 6)
            if shared:
                edges.append({
                    "left": left,
                    "right": right,
                    "similarity": score,
                    "shared_terms": shared[:12],
                })
    edges.sort(key=lambda x: (-x["similarity"], x["left"], x["right"]))

    term_domains: Dict[str, set[str]] = defaultdict(set)
    for domain, terms_set in profiles.items():
        for term in terms_set:
            term_domains[term].add(domain)
    bridges = [
        {"term": term, "disciplines": sorted(ds), "discipline_count": len(ds)}
        for term, ds in term_domains.items()
        if len(ds) >= 3
    ]
    bridges.sort(key=lambda x: (-x["discipline_count"], x["term"]))
    return {"edges": edges[:30], "bridge_terms": bridges[:30]}


def choose_self_development_target(self_model: Dict[str, Any]) -> Dict[str, Any]:
    deficits = [d for d in self_model.get("generation_deficits", []) if isinstance(d, dict) and d.get("deficit_id")]
    deficits.sort(key=lambda d: (d.get("priority", 9999), d.get("deficit_id", "")))
    if deficits:
        return deficits[0]
    return {"deficit_id": "CROSS_DOMAIN_TRANSFER", "priority": 1, "observed": None, "target_min": 0.9}


def run(config: Dict[str, Any], self_model: Dict[str, Any]) -> Dict[str, Any]:
    limits = config.get("limits", {})
    max_pages = int(limits.get("max_total_pages", 18))
    max_bytes = int(limits.get("max_bytes_per_page", 700000))
    timeout = int(limits.get("timeout_seconds", 15))
    sources = list(config.get("sources", []))[:max_pages]

    records: List[Dict[str, Any]] = []
    domain_terms: Dict[str, Counter[str]] = defaultdict(Counter)
    for source in sources:
        discipline = str(source.get("discipline", "unknown"))
        result = fetch_public_https(str(source.get("url", "")), max_bytes=max_bytes, timeout=timeout)
        private_tokens = result.pop("_tokens", [])
        result["discipline"] = discipline
        records.append(result)
        if result.get("status") == "FETCHED":
            domain_terms[discipline].update(private_tokens)

    fetched = [r for r in records if r.get("status") == "FETCHED"]
    disciplines = sorted({r["discipline"] for r in fetched})
    total_words = sum(int(r.get("word_count", 0)) for r in fetched)
    cross = derive_cross_domain(domain_terms)
    target = choose_self_development_target(self_model)

    acquisition_pass = len(fetched) >= 5 and len(disciplines) >= 5 and total_words >= 3000
    synthesis_pass = bool(cross["edges"]) and len(domain_terms) >= 5
    status = "PASS_REAL_INTERNET_CROSS_DISCIPLINARY_EXPERIENCE" if acquisition_pass and synthesis_pass else "WITHHOLD_INSUFFICIENT_REAL_INTERNET_EVIDENCE"

    domain_profiles = {
        domain: [{"term": term, "count": count} for term, count in counter.most_common(25)]
        for domain, counter in sorted(domain_terms.items())
    }
    result: Dict[str, Any] = {
        "schema": SCHEMA,
        "status": status,
        "internet_access_verified": bool(fetched),
        "acquisition": {
            "configured_sources": len(sources),
            "fetched_sources": len(fetched),
            "disciplines_covered": disciplines,
            "discipline_count": len(disciplines),
            "total_words_observed": total_words,
            "raw_page_text_persisted": False,
            "records": records,
        },
        "derived_experience": {
            "domain_profiles": domain_profiles,
            "cross_domain": cross,
        },
        "self_development_binding": {
            "self_model_status": self_model.get("status", "MISSING"),
            "target_deficit": target,
            "action": "USE_REAL_CROSS_DISCIPLINARY_EVIDENCE_TO_FORM_AND_TEST_REPAIR_HYPOTHESES",
            "claimed_cognitive_improvement": False,
            "next_gate": "EXPERIENCE_CONDITIONED_MUTATION_THEN_FRESH_TRANSFER_AND_REGRESSION",
            "canonical_direct_write": False,
        },
        "safety_boundary": {
            "public_https_only": True,
            "authenticated_access": False,
            "remote_code_execution": False,
            "remote_content_treated_as_untrusted_data": True,
        },
    }
    encoded = json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    result["evidence_digest"] = hashlib.sha256(encoded).hexdigest()
    return result


def self_test() -> None:
    sample = "Causal systems use evidence, models, feedback and uncertainty across science and engineering."
    assert "causal" in tokens(sample)
    a = {"model", "evidence", "risk"}
    b = {"model", "evidence", "system"}
    assert 0 < jaccard(a, b) < 1
    target = choose_self_development_target({"generation_deficits": [{"deficit_id": "THINKING_BOUNDARY_REASONING", "priority": 1}]})
    assert target["deficit_id"] == "THINKING_BOUNDARY_REASONING"
    print("PASS_CROSS_DISCIPLINARY_INTERNET_LEARNING_SELF_TEST")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="architecture/yado-cross-disciplinary-internet-learning-v1.json")
    parser.add_argument("--self-model", default="architecture/developmental-self-model-overlay.json")
    parser.add_argument("--out", default="artifacts/yado-cross-disciplinary-internet-learning-v1.json")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        return 0

    result = run(load_json(Path(args.config)), load_json(Path(args.self_model)))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "internet_access_verified": result["internet_access_verified"],
        "fetched_sources": result["acquisition"]["fetched_sources"],
        "discipline_count": result["acquisition"]["discipline_count"],
        "disciplines": result["acquisition"]["disciplines_covered"],
        "cross_domain_edges": len(result["derived_experience"]["cross_domain"]["edges"]),
        "bridge_terms": len(result["derived_experience"]["cross_domain"]["bridge_terms"]),
        "target_deficit": result["self_development_binding"]["target_deficit"].get("deficit_id"),
        "evidence_digest": result["evidence_digest"],
    }, indent=2, sort_keys=True))
    return 0 if result["status"].startswith("PASS_") else 2


if __name__ == "__main__":
    raise SystemExit(main())
