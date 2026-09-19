from __future__ import annotations

"""Bounded self-directed public-web research for YADO G2.

This layer turns a knowledge objective into a read-only research cycle:
causal prepare -> public search/discovery -> independent source reads ->
cross-source comparison -> bounded deficit -> memory feedback -> next goal.
It never authorizes credentials, private-network access, external writes,
downloaded-code execution, canonical mutation, or G3 promotion.
"""

from copy import deepcopy
import hashlib
from html.parser import HTMLParser
import json
import re
from typing import Any, Callable, Iterable
from urllib.parse import parse_qs, quote_plus, unquote, urljoin, urlsplit


SCHEMA = "yado.self_directed_web_research.v1"
STATE_SCHEMA = "yado.self_directed_web_research.state.v1"
COMPONENT_ID = "RUNTIME-G2-SELF-DIRECTED-WEB-RESEARCH-V1"
MAX_EPISODES = 32
MAX_OBJECTIVE_CHARS = 600
MAX_SOURCES = 5
MAX_SEARCH_RESULTS = 24
MAX_GENERATIONS = 5

_STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "into", "about", "what", "when", "where", "which",
    "how", "does", "are", "was", "were", "can", "could", "should", "would", "using", "use", "find", "seek",
    "additional", "independent", "public", "source", "sources", "evidence", "corroboration", "contradiction",
    "для", "что", "как", "это", "или", "при", "про", "его", "ее", "они", "она", "оно", "найти", "источник",
    "источники", "данные", "доказательства", "независимые", "публичные",
}


def _canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _digest(obj: Any) -> str:
    return hashlib.sha256(_canon(obj).encode("utf-8")).hexdigest()


def _objective(value: str) -> str:
    text = " ".join(str(value or "").split()).strip()
    if not text or len(text) > MAX_OBJECTIVE_CHARS:
        raise ValueError("RESEARCH_OBJECTIVE_REQUIRED_OR_TOO_LONG")
    return text


def _tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-zА-Яа-яЁё0-9]{3,}", str(text).lower())


def _keywords(text: str, limit: int = 12) -> list[str]:
    out: list[str] = []
    seen = set()
    for token in _tokens(text):
        if token in _STOPWORDS or token in seen:
            continue
        seen.add(token)
        out.append(token)
        if len(out) >= limit:
            break
    return out


class _VisibleTextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() in {"script", "style", "noscript", "svg"}:
            self.depth += 1

    def handle_endtag(self, tag):
        if tag.lower() in {"script", "style", "noscript", "svg"} and self.depth:
            self.depth -= 1

    def handle_data(self, data):
        if not self.depth:
            text = " ".join(str(data).split())
            if text:
                self.parts.append(text)


class _AnchorParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return
        for key, value in attrs:
            if key.lower() == "href" and value:
                self.hrefs.append(str(value))


def _plain_text(content: str) -> str:
    if "<" not in content or ">" not in content:
        return " ".join(content.split())
    parser = _VisibleTextParser()
    parser.feed(content[:2_000_000])
    return " ".join(parser.parts)


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|[\r\n]+", text)
    out = []
    for part in parts:
        value = " ".join(part.split()).strip()
        if 40 <= len(value) <= 900:
            out.append(value)
        if len(out) >= 500:
            break
    return out


def _best_excerpts(text: str, keywords: Iterable[str], limit: int = 3) -> list[str]:
    wanted = set(keywords)
    ranked = []
    for i, sentence in enumerate(_sentences(text)):
        words = set(_tokens(sentence))
        score = len(words & wanted)
        ranked.append((-score, i, sentence[:600]))
    ranked.sort()
    chosen = [x[2] for x in ranked if -x[0] > 0][:limit]
    if not chosen:
        chosen = [x[2] for x in ranked[:limit]]
    return chosen


def _search_urls(objective: str) -> list[str]:
    q = quote_plus(objective)
    return [
        f"https://html.duckduckgo.com/html/?q={q}",
        f"https://www.google.com/search?q={q}&num=10&hl=en",
        f"https://search.brave.com/search?q={q}&source=web",
    ]


def _unwrap_search_href(href: str, base_url: str) -> str | None:
    raw = str(href or "").strip()
    if not raw or raw.startswith(("javascript:", "mailto:", "data:")):
        return None
    url = urljoin(base_url, raw)
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    query = parse_qs(parsed.query)
    if host.endswith("duckduckgo.com") and parsed.path.startswith("/l/"):
        target = (query.get("uddg") or [None])[0]
        if target:
            url = unquote(target)
            parsed = urlsplit(url)
            host = (parsed.hostname or "").lower()
    elif host.endswith("google.com") and parsed.path == "/url":
        target = (query.get("q") or query.get("url") or [None])[0]
        if target:
            url = target
            parsed = urlsplit(url)
            host = (parsed.hostname or "").lower()
    if parsed.scheme.lower() != "https" or not host:
        return None
    search_host = (urlsplit(base_url).hostname or "").lower()
    if host == search_host or host.endswith("duckduckgo.com") or host.endswith("google.com") or host.endswith("brave.com"):
        return None
    return url


def _extract_search_candidates(content: str, base_url: str, limit: int) -> list[str]:
    parser = _AnchorParser()
    parser.feed(content[:2_000_000])
    out: list[str] = []
    seen = set()
    for href in parser.hrefs:
        candidate = _unwrap_search_href(href, base_url)
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        out.append(candidate)
        if len(out) >= limit:
            break
    return out


class SelfDirectedWebResearchV1:
    def __init__(self, prepare_causal: Callable[[str], dict[str, Any]], meta_decide: Callable[[dict[str, Any]], dict[str, Any]]):
        self.prepare_causal = prepare_causal
        self.meta_decide = meta_decide
        self._episodes: list[dict[str, Any]] = []

    def _prior_hosts(self, root_objective: str) -> set[str]:
        hosts = set()
        for row in self._episodes:
            if row.get("root_objective") == root_objective:
                hosts.update(row.get("source_hosts") or [])
        return hosts

    def _record(self, event: dict[str, Any]) -> dict[str, Any]:
        if len(self._episodes) >= MAX_EPISODES:
            raise ValueError("RESEARCH_MEMORY_CAPACITY_REACHED")
        body = deepcopy(event)
        body["sequence"] = len(self._episodes) + 1
        body["prior_event_digest"] = self._episodes[-1]["event_digest"] if self._episodes else None
        body["event_digest"] = _digest({k: v for k, v in body.items() if k != "event_digest"})
        self._episodes.append(deepcopy(body))
        return body

    def research(
        self,
        objective: str,
        *,
        fetch: Callable[[str], dict[str, Any]],
        discover: Callable[[str, str, int], list[dict[str, Any]]] | None = None,
        seed_urls: Iterable[str] | None = None,
        root_objective: str | None = None,
        max_sources: int = 3,
        max_search_results: int = 16,
        closure_source_target: int = 4,
        use_search: bool = True,
    ) -> dict[str, Any]:
        goal = _objective(objective)
        root = _objective(root_objective or goal)
        if not 1 <= int(max_sources) <= MAX_SOURCES:
            raise ValueError("RESEARCH_SOURCE_BUDGET")
        if not 1 <= int(max_search_results) <= MAX_SEARCH_RESULTS:
            raise ValueError("RESEARCH_SEARCH_RESULT_BUDGET")
        if not 2 <= int(closure_source_target) <= 8:
            raise ValueError("RESEARCH_CLOSURE_SOURCE_TARGET")

        prepared = self.prepare_causal(goal)
        prepared_summary = {
            "status": prepared.get("status"),
            "thinking_status": (prepared.get("thinking") or {}).get("status"),
            "logic_status": (prepared.get("logic") or {}).get("status"),
            "intelligence_status": (prepared.get("intelligence") or {}).get("status"),
            "plan_digest": (prepared.get("action_plan") or {}).get("plan_digest"),
        }
        if prepared_summary["status"] != "PASS_CAUSAL_PREPARE":
            event = self._record({
                "root_objective": root,
                "objective": goal,
                "status": "WITHHOLD_CAUSAL_PREPARE",
                "source_hosts": [],
                "deficits": ["CAUSAL_PREPARE_WITHHOLD"],
                "next_goal": None,
                "causal_prepare": prepared_summary,
            })
            return {"schema": SCHEMA, "status": "WITHHOLD_SELF_DIRECTED_WEB_RESEARCH_V1", "event": event}

        keywords = _keywords(root)
        candidates = [str(x) for x in (seed_urls or []) if str(x).strip()]
        search_receipts = []
        search_errors = []
        if use_search:
            for search_url in _search_urls(goal):
                try:
                    page = fetch(search_url)
                    receipt = deepcopy(page.get("receipt") or {})
                    search_receipts.append({
                        "url": receipt.get("final_url", search_url),
                        "host": receipt.get("final_host"),
                        "sha256": receipt.get("sha256"),
                        "read_only": receipt.get("read_only"),
                    })
                    candidates.extend(_extract_search_candidates(page.get("content", ""), receipt.get("final_url", search_url), int(max_search_results)))
                    if len(candidates) >= max_search_results:
                        break
                except Exception as exc:
                    search_errors.append({"url": search_url, "error_type": type(exc).__name__, "reason": str(exc)[:240]})

        if discover is not None and candidates:
            # A seed can expose direct public links before evidence selection.
            try:
                seed = fetch(candidates[0])
                candidates.extend(x.get("url") for x in discover(seed.get("content", ""), (seed.get("receipt") or {}).get("final_url", candidates[0]), min(8, max_search_results)) if x.get("url"))
            except Exception:
                pass

        deduped = []
        seen_urls = set()
        for candidate in candidates:
            if candidate and candidate not in seen_urls:
                seen_urls.add(candidate)
                deduped.append(candidate)
            if len(deduped) >= max_search_results:
                break

        prior_hosts = self._prior_hosts(root)
        # Prefer new hosts for diversity, but retain known public sources as
        # revalidation candidates. History must not permanently ban a domain.
        sources = []
        revisits = []
        source_errors = []
        current_hosts = set()
        for url in deduped:
            try:
                page = fetch(url)
                receipt = deepcopy(page.get("receipt") or {})
                host = str(receipt.get("final_host") or (urlsplit(str(receipt.get("final_url") or url)).hostname or "")).lower()
                if not host or host in current_hosts:
                    continue
                text = _plain_text(str(page.get("content") or ""))
                if len(text) < 80:
                    source_errors.append({"url": url, "reason": "SOURCE_TEXT_TOO_SHORT"})
                    continue
                words = set(_tokens(text))
                covered = [k for k in keywords if k in words]
                excerpts = _best_excerpts(text, keywords)
                source = {
                    "url": receipt.get("final_url", url),
                    "host": host,
                    "sha256": receipt.get("sha256"),
                    "bytes": receipt.get("bytes"),
                    "covered_keywords": covered,
                    "excerpts": excerpts,
                    "read_only": receipt.get("read_only") is True,
                    "credentials_used": receipt.get("credentials_used") is True,
                    "external_write": receipt.get("external_write") is True,
                    "private_network_access": receipt.get("private_network_access") is True,
                    "previously_observed_host": host in prior_hosts,
                }
                if host in prior_hosts:
                    revisits.append(source)
                    continue
                sources.append(source)
                current_hosts.add(host)
                if len(sources) >= max_sources:
                    break
            except Exception as exc:
                source_errors.append({"url": url, "error_type": type(exc).__name__, "reason": str(exc)[:240]})

        for source in revisits:
            if len(sources) >= max_sources:
                break
            if source["host"] not in current_hosts:
                sources.append(source)
                current_hosts.add(source["host"])

        counts = {key: sum(key in set(src["covered_keywords"]) for src in sources) for key in keywords}
        covered = [key for key in keywords if counts.get(key, 0) >= 1]
        corroborated = [key for key in keywords if counts.get(key, 0) >= 2]
        uncovered = [key for key in keywords if counts.get(key, 0) == 0]
        coverage_ratio = 1.0 if not keywords else len(covered) / len(keywords)
        corroboration_ratio = 1.0 if not keywords else len(corroborated) / len(keywords)
        combined_hosts = prior_hosts | current_hosts

        safety_ok = all(
            src["read_only"] and not src["credentials_used"] and not src["external_write"] and not src["private_network_access"]
            for src in sources
        )
        evidence_verified = len(sources) >= 2 and coverage_ratio >= 0.40 and safety_ok
        deficits = []
        if len(sources) < 2:
            deficits.append("INSUFFICIENT_CURRENT_INDEPENDENT_SOURCES")
        if coverage_ratio < 0.60:
            deficits.append("OBJECTIVE_TERM_COVERAGE_DEFICIT")
        if keywords and corroboration_ratio < 0.40:
            deficits.append("CROSS_SOURCE_CORROBORATION_DEFICIT")
        if len(combined_hosts) < closure_source_target:
            deficits.append("SOURCE_DIVERSITY_DEFICIT")

        next_goal = None
        if deficits:
            if uncovered:
                next_goal = f"Find independent public evidence covering {', '.join(uncovered[:5])} for: {root}"
            elif "CROSS_SOURCE_CORROBORATION_DEFICIT" in deficits:
                next_goal = f"Find independent corroboration or contradiction for: {root}"
            elif "SOURCE_DIVERSITY_DEFICIT" in deficits:
                next_goal = f"Find additional independent corroborating or challenging sources for: {root}"
            elif len(sources) < 2:
                next_goal = f"Find two independent accessible public sources for: {root}"

        comparison = {
            "objective_keywords": keywords,
            "covered_keywords": covered,
            "corroborated_keywords": corroborated,
            "uncovered_keywords": uncovered,
            "coverage_ratio": round(coverage_ratio, 6),
            "corroboration_ratio": round(corroboration_ratio, 6),
            "current_independent_source_count": len(current_hosts),
            "new_independent_host_count": len(current_hosts - prior_hosts),
            "revisited_hosts": sorted(current_hosts & prior_hosts),
            "prior_independent_hosts": sorted(prior_hosts),
            "combined_independent_hosts": sorted(combined_hosts),
            "closure_source_target": closure_source_target,
        }
        artifact = {
            "fresh_source_diversity": len(current_hosts) >= 2,
            "fresh_objective_coverage": coverage_ratio >= 0.40,
            "safety_public_read_only": safety_ok,
            "canonical_mutation": False,
            "automatic_canonical_promotion": False,
            "g3_genesis_performed": False,
        }
        meta_evidence = {
            "outcome": "PASS" if evidence_verified else "WITHHOLD",
            "domain": "MEMORY",
            "next_required_capability": "BOUNDED_EVIDENCE_REFINEMENT" if next_goal else None,
            "next_domain": "MEMORY" if next_goal else None,
            "source_class": "RECEIPT",
            "artifact": artifact,
        }
        meta = self.meta_decide(meta_evidence)
        event = self._record({
            "root_objective": root,
            "objective": goal,
            "status": "PASS_SELF_DIRECTED_WEB_RESEARCH_V1" if evidence_verified else "WITHHOLD_SELF_DIRECTED_WEB_RESEARCH_V1",
            "source_hosts": sorted(current_hosts),
            "source_receipt_digests": [src.get("sha256") for src in sources],
            "comparison": comparison,
            "deficits": deficits,
            "next_goal": next_goal,
            "causal_prepare": prepared_summary,
            "meta_decision": meta,
        })
        return {
            "schema": SCHEMA,
            "status": event["status"],
            "root_objective": root,
            "objective": goal,
            "causal_prepare": prepared_summary,
            "search": {"receipts": search_receipts, "errors": search_errors, "candidate_count": len(deduped)},
            "sources": sources,
            "comparison": comparison,
            "deficits": deficits,
            "next_goal": next_goal,
            "meta_decision": meta,
            "memory_feedback": {"event_digest": event["event_digest"], "episode_count": len(self._episodes)},
            "read_only": True,
            "credentials_used": False,
            "private_network_access": False,
            "external_write": False,
            "downloaded_code_executed": False,
            "automatic_canonical_mutation": False,
            "g3_genesis_performed": False,
            "source_errors": source_errors,
        }

    def run_generations(
        self,
        initial_objective: str,
        *,
        fetch: Callable[[str], dict[str, Any]],
        discover: Callable[[str, str, int], list[dict[str, Any]]] | None = None,
        seed_urls: Iterable[str] | None = None,
        max_generations: int = 3,
        max_sources_per_generation: int = 2,
        closure_source_target: int = 4,
        max_search_results: int = 20,
    ) -> dict[str, Any]:
        root = _objective(initial_objective)
        if not 1 <= int(max_generations) <= MAX_GENERATIONS:
            raise ValueError("RESEARCH_GENERATION_BUDGET")
        goal = root
        generations = []
        seen_goals = set()
        first_seeds = list(seed_urls or [])
        for index in range(max_generations):
            if goal in seen_goals:
                break
            seen_goals.add(goal)
            result = self.research(
                goal,
                root_objective=root,
                fetch=fetch,
                discover=discover,
                seed_urls=first_seeds if index == 0 else None,
                max_sources=max_sources_per_generation,
                max_search_results=max_search_results,
                closure_source_target=closure_source_target,
                use_search=True,
            )
            generations.append(result)
            goal = result.get("next_goal")
            if not goal:
                break
        goal_closed = bool(generations and not generations[-1].get("next_goal") and generations[-1].get("status") == "PASS_SELF_DIRECTED_WEB_RESEARCH_V1")
        all_hosts = sorted({host for row in self._episodes if row.get("root_objective") == root for host in row.get("source_hosts", [])})
        return {
            "schema": "yado.self_directed_web_research.generations.v1",
            "status": "PASS_BOUNDED_SELF_DIRECTED_WEB_RESEARCH_GENERATIONS_V1" if generations and any(x.get("status") == "PASS_SELF_DIRECTED_WEB_RESEARCH_V1" for x in generations) else "WITHHOLD_BOUNDED_SELF_DIRECTED_WEB_RESEARCH_GENERATIONS_V1",
            "root_objective": root,
            "generation_count": len(generations),
            "goal_closed": goal_closed,
            "independent_hosts_accumulated": all_hosts,
            "generations": generations,
            "remaining_goal": generations[-1].get("next_goal") if generations else root,
            "automatic_canonical_mutation": False,
            "g3_genesis_performed": False,
        }

    def export_state(self) -> dict[str, Any]:
        state = {
            "schema": STATE_SCHEMA,
            "component_id": COMPONENT_ID,
            "episodes": deepcopy(self._episodes),
            "executable_objects": False,
            "automatic_canonical_mutation": False,
            "g3_genesis_performed": False,
        }
        state["state_digest"] = _digest(state)
        return state

    def import_state(self, state: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(state, dict):
            raise ValueError("RESEARCH_STATE_INVALID")
        body = deepcopy(state)
        supplied = body.pop("state_digest", None)
        if supplied != _digest(body) or body.get("schema") != STATE_SCHEMA or body.get("component_id") != COMPONENT_ID:
            raise ValueError("RESEARCH_STATE_INVALID")
        episodes = body.get("episodes")
        if not isinstance(episodes, list) or len(episodes) > MAX_EPISODES or body.get("executable_objects") is not False:
            raise ValueError("RESEARCH_STATE_INVALID")
        previous = None
        for sequence, row in enumerate(episodes, start=1):
            if not isinstance(row, dict) or row.get("sequence") != sequence or row.get("prior_event_digest") != previous:
                raise ValueError("RESEARCH_EVENT_CHAIN_INVALID")
            check = deepcopy(row)
            digest = check.pop("event_digest", None)
            if digest != _digest(check):
                raise ValueError("RESEARCH_EVENT_CHAIN_INVALID")
            previous = digest
        self._episodes = deepcopy(episodes)
        return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        return {
            "schema": "yado.self_directed_web_research.snapshot.v1",
            "component_id": COMPONENT_ID,
            "status": "SHADOW_READY",
            "episode_count": len(self._episodes),
            "durable_state_supported": True,
            "uses_causal_prepare": True,
            "multi_source_comparison": True,
            "deficit_to_next_goal": True,
            "read_only_external": True,
            "automatic_canonical_promotion": False,
            "g3_genesis_performed": False,
        }


__all__ = ["SelfDirectedWebResearchV1", "COMPONENT_ID"]
