from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from yado_resource_intelligence_cycle8 import (
    BASE, T1, T2, T3, TRAIN, FRESH_DOCS as _FRESH_DOCS, grams_from_tokens, tokenize
)

# RC7 provenance reduction: these catalog segments are derived directly from the
# durable resource-intelligence source instead of a reconstructed compatibility shim.
OLD1 = list(T1) + list(T2)
OLD2 = list(T3)
FRESH_DOCS = list(_FRESH_DOCS)

# Source-derived catalog records accumulated across the revealed development cycles.
ACCUMULATED_NOVEL_DOCS: List[Tuple[str, str]] = list(OLD1) + list(OLD2) + list(FRESH_DOCS) + [
    ("FDH2/UxPlay", "Cross-platform AirPlay server"),
    ("builtree/handwrite", "Generate a custom font based on your handwriting sample"),
    ("noisetorch/NoiseTorch", "Real-time microphone noise suppression"),
    ("rhasspy/piper", "Local neural text to speech system"),
    ("osnr/TabFS", "Mount browser tabs as a filesystem"),
    ("alexkirsz/dispatch", "Combine internet connections"),
    ("timvisee/send", "Quick encrypted file sharing"),
    ("jtroo/kanata", "Cross-platform keyboard remapper"),
    ("kurolabs/stegcloak", "Create hidden messages"),
    ("QiuYannnn/Local-File-Organizer", "AI File Organizer"),
    ("winapps-org/winapps", "Run Windows apps like they are native"),
    ("mfat/systemd-pilot", "systemd service GUI manager"),
    ("flightlessmango/MangoHud", "Application overlay for monitoring resources"),
    ("wwmm/easyeffects", "PipeWire audio effect manager"),
    ("OptiKey/OptiKey", "Helps Motor Neuron Disease patients interact with their PC"),
    ("MaxAlyokhin/binary-synth", "Binary file interpreter for audio synthesis"),
    ("Flow-Launcher/Flow.Launcher", "App launcher for Windows"),
    ("project-gauntlet/gauntlet", "Cross-platform application launcher"),
    ("files-community/Files", "Modern file manager for Windows"),
    ("dail8859/NotepadNext", "Cross-platform reimplementation of Notepad++"),
    ("notepad-plus-plus/notepad-plus-plus", "Extensive text editor for Windows"),
    ("ShareX/ShareX", "Screen capture tool for Windows"),
    ("RsyncProject/rsync", "Incremental file transfer tool"),
    ("linuxmint/warpinator", "Send/receive files across local network"),
    ("linuxmint/timeshift", "System restore tool for Linux"),
]


@dataclass(frozen=True)
class SelectiveConfig:
    semantic_coverage_min: float = 0.67
    semantic_margin_min: float = 0.0
    generic_top_min: float = 0.0
    generic_margin_min: float = 0.15
    deep_pool_k: int = 12
    deep_feature: str = "TOKEN_SOFT"

    @property
    def digest(self) -> str:
        payload = json.dumps(self.__dict__, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class SelectiveEvidenceRouter:
    """Bounded resource router with calibrated abstention and deep evidence fallback.

    The router does not contain repository-specific selection rules. It combines:
      1) learned semantic translation inside the evidence-supported domain,
      2) generic character-trigram transfer across all catalog entries,
      3) a calibrated reject option,
      4) wider deep-evidence retrieval and token-soft matching after rejection.

    Deep evidence is host-mediated source text supplied in the request. Missing deep
    text falls back to the catalog description; it is never treated as authority.
    """

    def __init__(self, extra_docs: Sequence[Sequence[str]], deep_evidence: Mapping[str, str], config: SelectiveConfig | None = None):
        self.config = config or SelectiveConfig()
        supported = list(BASE + T1 + T2 + T3)
        merged: Dict[str, str] = {str(r): str(d) for r, d in supported}
        for r, d in ACCUMULATED_NOVEL_DOCS:
            merged.setdefault(str(r), str(d))
        for r, d in extra_docs:
            merged[str(r)] = str(d)

        self.supported = supported
        self.supported_set = {r for r, _ in supported}
        self.all_docs = list(merged.items())
        self.raw_desc = dict(self.all_docs)
        self.deep_evidence = {str(k): str(v) for k, v in deep_evidence.items()}
        self.camel = False
        self.desc = {r: tokenize(d, self.camel) for r, d in self.all_docs}
        self.grams = {r: grams_from_tokens(self.desc[r]) for r, _ in self.all_docs}
        self.pos = defaultdict(float)
        self.neg = defaultdict(float)
        for q, tgt in TRAIN:
            qs = set(tokenize(q, self.camel))
            td = set(self.desc[tgt])
            for x in qs:
                for d in td:
                    self.pos[(x, d)] += 1.0
                for r in self.supported_set:
                    if r == tgt:
                        continue
                    for d in set(self.desc[r]):
                        self.neg[(x, d)] += 1.0 / (len(self.supported_set) - 1)

    @staticmethod
    def _word_grams(x: str) -> set[str]:
        return {x[i:i+3] for i in range(max(0, len(x) - 2))}

    def token_only_rows(self, q: str) -> List[Tuple[float, str]]:
        qs = set(tokenize(q, self.camel))
        rows = []
        for r, _ in self.all_docs:
            ds = set(self.desc[r])
            rows.append((len(qs & ds) / (len(qs) or 1), r))
        return sorted(rows, key=lambda z: (z[0], z[1]), reverse=True)

    def generic_rows(self, q: str) -> List[Tuple[float, str]]:
        qg = grams_from_tokens(tokenize(q, self.camel))
        rows = []
        for r, _ in self.all_docs:
            dg = self.grams[r]
            rows.append((len(qg & dg) / (len(qg | dg) or 1), r))
        return sorted(rows, key=lambda z: (z[0], z[1]), reverse=True)

    def semantic_rows(self, q: str) -> List[Tuple[float, float, str]]:
        qs = set(tokenize(q, self.camel))
        rows = []
        for r in self.supported_set:
            vals = []
            covered = 0
            for x in qs:
                best = 0.0
                for d in set(self.desc[r]):
                    p = self.pos[(x, d)]
                    n = self.neg[(x, d)]
                    if p:
                        best = max(best, max(0.0, math.log((p + 0.5) / (n + 0.5))))
                covered += int(best > 0.0)
                vals.append(best)
            rows.append((sum(vals) / (len(vals) or 1), covered / (len(qs) or 1), r))
        return sorted(rows, key=lambda z: (z[0], z[2]), reverse=True)

    def _token_soft(self, q: str, text: str) -> float:
        doc_tokens = tokenize(text, self.camel)
        vals = []
        for x in tokenize(q, self.camel):
            xg = self._word_grams(x)
            best = 0.0
            for d in doc_tokens:
                dg = self._word_grams(d)
                best = max(best, len(xg & dg) / (len(xg | dg) or 1))
            vals.append(best)
        return sum(vals) / (len(vals) or 1)

    def deep_rows(self, q: str, candidate_ids: Sequence[str]) -> List[Tuple[float, str]]:
        rows = []
        for r in candidate_ids:
            text = self.deep_evidence.get(r, self.raw_desc.get(r, ""))
            rows.append((self._token_soft(q, text), r))
        return sorted(rows, key=lambda z: (z[0], z[1]), reverse=True)

    def decide(self, q: str) -> Dict[str, Any]:
        cfg = self.config
        sr = self.semantic_rows(q)
        gr = self.generic_rows(q)
        sem_score, sem_cov, sem_winner = sr[0]
        sem_margin = sem_score - sr[1][0] if len(sr) > 1 else sem_score
        gen_score, gen_winner = gr[0]
        gen_margin = gen_score - gr[1][0] if len(gr) > 1 else gen_score
        features = {
            "semantic_coverage": sem_cov,
            "semantic_margin": sem_margin,
            "generic_top": gen_score,
            "generic_margin": gen_margin,
        }

        if sem_cov >= cfg.semantic_coverage_min and sem_margin >= cfg.semantic_margin_min:
            ordered = [sem_winner] + [r for _, r in gr if r != sem_winner]
            return {"action": "USE_LEARNED_SEMANTICS", "winner": sem_winner, "ordered": ordered, "features": features, "deep_pool": []}

        if gen_score >= cfg.generic_top_min and gen_margin >= cfg.generic_margin_min:
            return {"action": "USE_GENERIC_TRANSFER", "winner": gen_winner, "ordered": [r for _, r in gr], "features": features, "deep_pool": []}

        pool = [r for _, r in gr[: cfg.deep_pool_k]]
        dr = self.deep_rows(q, pool)
        winner = dr[0][1] if dr else None
        ordered = [r for _, r in dr] + [r for _, r in gr if r not in {x for _, x in dr}]
        return {
            "action": "SEEK_MORE_EVIDENCE_THEN_RERANK",
            "winner": winner,
            "ordered": ordered,
            "features": features,
            "deep_pool": pool,
            "deep_top": [{"repo": r, "score": float(s)} for s, r in dr[:5]],
        }

    def evaluate(self, cases: Sequence[Sequence[str]]) -> Dict[str, Any]:
        hit = 0
        rr = 0.0
        actions: Dict[str, int] = defaultdict(int)
        details = []
        for q, expected in cases:
            result = self.decide(str(q))
            ids = result["ordered"]
            rank = ids.index(str(expected)) + 1 if str(expected) in ids else len(ids) + 1
            hit += int(rank == 1)
            rr += 1.0 / rank
            actions[result["action"]] += 1
            details.append({
                "query": str(q), "expected": str(expected), "rank": rank,
                "winner": result["winner"], "action": result["action"],
                "features": result["features"], "deep_pool_size": len(result.get("deep_pool", [])),
                "deep_top": result.get("deep_top", []),
            })
        n = max(1, len(cases))
        return {"top1": hit / n, "mrr": rr / n, "actions": dict(actions), "details": details}


__all__ = ["SelectiveConfig", "SelectiveEvidenceRouter", "ACCUMULATED_NOVEL_DOCS"]
