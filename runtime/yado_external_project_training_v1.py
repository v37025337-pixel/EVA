from __future__ import annotations

"""Bounded training from verified public repository observations.

Only normalized facts are admitted. The trainer does not fetch, import, clone,
or execute repository code and does not mutate canonical runtime state.
"""

import hashlib
import json
import re
from typing import Any


SCHEMA = "yado.external_project_training.v1"
STATUS_PASS = "PASS_SHADOW_EXTERNAL_PROJECT_TRAINING_V1"
STATUS_WITHHOLD = "WITHHOLD_EXTERNAL_PROJECT_TRAINING_UNKNOWN"
ALLOWED_REPOSITORIES = {
    "ripienaar/free-for-dev": "master",
    "dip497/hivemind": "main",
}


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", str(value).lower()))


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


# These are paraphrased observations, not copied source code. Every row keeps
# provenance so a later auditor can reproduce the read-only observation.
SOURCE_ROWS = (
    {
        "repository": "ripienaar/free-for-dev",
        "ref": "master",
        "source_url": "https://github.com/ripienaar/free-for-dev/blob/master/README.md",
        "lines": "3-11",
        "observation": "curated catalog of developer services with free tiers for infrastructure work",
        "labels": ("LOGIC", "INTELLIGENCE"),
    },
    {
        "repository": "ripienaar/free-for-dev",
        "ref": "master",
        "source_url": "https://github.com/ripienaar/free-for-dev/blob/master/README.md",
        "lines": "11-12",
        "observation": "admission requires a real free tier rather than a short trial and considers security constraints",
        "labels": ("LOGIC",),
    },
    {
        "repository": "ripienaar/free-for-dev",
        "ref": "master",
        "source_url": "https://github.com/ripienaar/free-for-dev/blob/master/README.md",
        "lines": "8-11",
        "observation": "community pull requests reviews and removals keep stale resource claims corrigible",
        "labels": ("THINKING", "INTELLIGENCE"),
    },
    {
        "repository": "dip497/hivemind",
        "ref": "main",
        "source_url": "https://github.com/dip497/hivemind/blob/main/README.md",
        "lines": "5-15",
        "observation": "local-first markdown-backed project workspace coordinates multiple coding agents without telemetry",
        "labels": ("THINKING", "INTELLIGENCE"),
    },
    {
        "repository": "dip497/hivemind",
        "ref": "main",
        "source_url": "https://github.com/dip497/hivemind/blob/main/README.md",
        "lines": "170-215",
        "observation": "MCP stdio maps agent work to issue state acceptance criteria comments and filesystem events",
        "labels": ("LOGIC", "THINKING"),
    },
    {
        "repository": "dip497/hivemind",
        "ref": "main",
        "source_url": "https://github.com/dip497/hivemind/blob/main/README.md",
        "lines": "202-225",
        "observation": "local control plane supervises sibling agents through a protected unix socket and explicit review",
        "labels": ("LOGIC", "INTELLIGENCE"),
    },
    {
        "repository": "dip497/hivemind",
        "ref": "main",
        "source_url": "https://github.com/dip497/hivemind/blob/main/README.md",
        "lines": "265-315",
        "observation": "architecture separates issue storage MCP server desktop canvas worktrees remote frames and persistence",
        "labels": ("THINKING", "INTELLIGENCE"),
    },
    {
        "repository": "dip497/hivemind",
        "ref": "main",
        "source_url": "https://github.com/dip497/hivemind/blob/main/README.md",
        "lines": "120-150",
        "observation": "Windows support is explicitly experimental and unvalidated on physical hardware",
        "labels": ("LOGIC",),
    },
)


CAPABILITY_TOKENS = {
    "LOGIC": ("admission", "criteria", "security", "review", "state", "validated", "explicit"),
    "THINKING": ("context", "workspace", "sequence", "architecture", "persistence", "event", "workflow"),
    "INTELLIGENCE": ("coordinate", "agent", "resource", "adapt", "supervise", "catalog", "separate"),
}


def validate_rows(rows: tuple[dict[str, Any], ...] | list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("TRAINING_ROWS_EMPTY")
    for row in rows:
        repository = row.get("repository")
        if repository not in ALLOWED_REPOSITORIES:
            raise ValueError("TRAINING_REPOSITORY_NOT_ADMITTED")
        if row.get("ref") != ALLOWED_REPOSITORIES[repository]:
            raise ValueError("TRAINING_REF_DRIFT")
        if not str(row.get("source_url", "")).startswith("https://github.com/"):
            raise ValueError("TRAINING_PROVENANCE_REQUIRED")
        if not row.get("lines") or not row.get("observation"):
            raise ValueError("TRAINING_OBSERVATION_INCOMPLETE")
        if not set(row.get("labels", ())) <= set(CAPABILITY_TOKENS):
            raise ValueError("TRAINING_LABEL_NOT_ADMITTED")


def train(rows: tuple[dict[str, Any], ...] | list[dict[str, Any]] = SOURCE_ROWS) -> dict[str, Any]:
    validate_rows(rows)
    profiles: dict[str, dict[str, int]] = {}
    for capability, vocabulary in CAPABILITY_TOKENS.items():
        profile: dict[str, int] = {}
        for row in rows:
            if capability not in row["labels"]:
                continue
            tokens = _tokens(row["observation"])
            for token in vocabulary:
                if token in tokens:
                    profile[token] = profile.get(token, 0) + 1
        if not profile:
            raise ValueError("TRAINING_CAPABILITY_PROFILE_EMPTY:" + capability)
        profiles[capability] = profile
    return {
        "schema": SCHEMA,
        "status": STATUS_PASS,
        "row_count": len(rows),
        "source_repositories": sorted({row["repository"] for row in rows}),
        "profiles": profiles,
        "training_digest": _digest(rows),
        "third_party_code_copied": False,
        "third_party_code_executed": False,
        "external_writes": False,
        "automatic_main_mutation": False,
    }


def route(task: str, trained: dict[str, Any]) -> dict[str, Any]:
    tokens = _tokens(task)
    ranked = []
    for index, capability in enumerate(("LOGIC", "THINKING", "INTELLIGENCE")):
        profile = trained["profiles"][capability]
        matched = sorted(token for token in profile if token in tokens)
        raw = sum(profile[token] for token in matched)
        total = sum(profile.values())
        ranked.append(((raw / total) if total else 0.0, -index, capability, matched))
    ranked.sort(reverse=True)
    if not ranked or ranked[0][0] == 0.0:
        return {"status": STATUS_WITHHOLD, "capability": None, "matched": []}
    score, _, capability, matched = ranked[0]
    return {
        "status": STATUS_PASS,
        "capability": capability,
        "matched": matched,
        "score": score,
        "training_digest": trained["training_digest"],
    }


def snapshot() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": STATUS_PASS,
        "source_count": len(ALLOWED_REPOSITORIES),
        "training_mode": "NORMALIZED_PROVENANCE_WEIGHTED_CAPABILITY_PROFILES",
        "network_fetch": False,
        "third_party_code_executed": False,
        "external_writes": False,
        "automatic_main_mutation": False,
    }
