"""Run YADO against fresh public GitHub data without supplying answers.

The runner clones public repositories at execution time, records exact commit/source
provenance, derives bounded relation and event tasks from that live data, lets the
existing cognitive loop solve them, and independently checks the returned answers.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import tokenize

from .kernel import SuccessorKernel

TARGETS = (
    ("opentrashmail", "https://github.com/HaschekSolutions/opentrashmail.git"),
    ("requests", "https://github.com/psf/requests.git"),
    ("click", "https://github.com/pallets/click.git"),
)
BRACKETS = {"(": (")", "paren"), "[": ("]", "square"), "{": ("}", "curly")}
CLOSERS = {close: key for _, (close, key) in BRACKETS.items()}


def run_git(cwd: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def clone_target(root: Path, name: str, url: str) -> Path:
    target = root / name
    subprocess.run(
        ["git", "clone", "--depth", "48", "--no-tags", "--quiet", url, str(target)],
        check=True,
        timeout=180,
    )
    return target


def commit_relation(repo: Path) -> dict:
    head = run_git(repo, "rev-parse", "HEAD")
    lines = run_git(repo, "log", "--format=%H%x09%P", "-n", "48").splitlines()
    edges = []
    commits = set()
    for line in lines:
        parts = line.split("\t", 1)
        child = parts[0]
        commits.add(child)
        parents = parts[1].split() if len(parts) > 1 and parts[1] else []
        for parent in parents:
            commits.add(parent)
            edges.append([child, parent])
    if len(commits) > 128 or len(edges) > 1024 or not edges:
        raise ValueError("REAL_RELATION_BUDGET")
    return {"domain": "relation", "relation": edges, "start": head}


def closure(spec: dict) -> set:
    reachable = {spec["start"]}
    changed = True
    while changed:
        changed = False
        for left, right in spec["relation"]:
            if left in reachable and right not in reachable:
                reachable.add(right)
                changed = True
    return reachable


def bracket_events(data: bytes) -> list[list[str]]:
    events = []
    try:
        tokens = tokenize.tokenize(io.BytesIO(data).readline)
        for token in tokens:
            if token.type != tokenize.OP:
                continue
            text = token.string
            if text in BRACKETS:
                events.append(["Q", BRACKETS[text][1]])
            elif text in CLOSERS:
                events.append(["R", CLOSERS[text]])
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return []
    return events


def event_truth(events: list[list[str]]) -> bool:
    opened = []
    valid = True
    for code, key in events:
        if code == "Q":
            opened.append(key)
        elif code == "R" and opened and opened[-1] == key:
            opened.pop()
        else:
            valid = False
    return valid and not opened


def choose_python_source(repo: Path) -> tuple[Path, bytes, list[list[str]]]:
    candidates = []
    for path in repo.rglob("*.py"):
        if ".git" in path.parts or not path.is_file():
            continue
        data = path.read_bytes()
        if len(data) > 300_000:
            continue
        events = bracket_events(data)
        if 24 <= len(events) <= 900 and event_truth(events):
            candidates.append((len(events), path.as_posix(), path, data, events))
    if not candidates:
        raise ValueError("NO_SUITABLE_REAL_PYTHON_SOURCE")
    candidates.sort(key=lambda row: (-row[0], row[1]))
    _, _, path, data, events = candidates[0]
    return path, data, events


def truncated_real_prefix(events: list[list[str]]) -> list[list[str]]:
    upper = min(len(events) - 1, 300)
    for end in range(upper, 15, -1):
        prefix = events[:end]
        if not event_truth(prefix):
            opened = []
            malformed = False
            for code, key in prefix:
                if code == "Q":
                    opened.append(key)
                elif opened and opened[-1] == key:
                    opened.pop()
                else:
                    malformed = True
                    break
            if not malformed and opened:
                return prefix
    raise ValueError("NO_UNCLOSED_REAL_PREFIX")


def run_goal(kernel: SuccessorKernel, name: str, spec: dict, provenance: dict) -> dict:
    goal_id = kernel.open_goal(spec, budget=3)
    kernel.think(120)
    goal = kernel.cognitive_snapshot()["goals"][str(goal_id)]
    result = goal.get("result") or {}
    if spec["domain"] == "relation":
        expected = closure(spec)
        answer = result.get("answer")
        independent = isinstance(answer, (list, tuple, set)) and set(answer) == expected
        expected_summary = {"reachable_nodes": len(expected)}
    else:
        expected = event_truth(spec["events"])
        independent = result.get("answer") is expected
        expected_summary = {"expected_boolean": expected}
    return {
        "name": name,
        "domain": spec["domain"],
        "goal_id": goal_id,
        "status": goal["status"],
        "attempted": goal["attempted"],
        "spent": goal["budget"] - goal["remaining"],
        "independent_check": bool(independent),
        "expected_not_supplied_to_kernel": True,
        "expected_summary_after_freeze": expected_summary,
        "provenance": provenance,
    }


def run(manifest: Path, output: Path) -> int:
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    state = output / "kernel.sqlite"
    kernel = SuccessorKernel(manifest, state)
    rows = []
    sources = []
    started = time.time()
    with tempfile.TemporaryDirectory(prefix="yado-real-world-") as temp:
        temp_root = Path(temp)
        try:
            for index, (name, url) in enumerate(TARGETS):
                repo = clone_target(temp_root, name, url)
                head = run_git(repo, "rev-parse", "HEAD")
                branch = run_git(repo, "rev-parse", "--abbrev-ref", "HEAD")
                relation = commit_relation(repo)
                relation_provenance = {
                    "repository": url,
                    "head_sha": head,
                    "checked_out_branch": branch,
                    "commit_edge_count": len(relation["relation"]),
                    "collector": "git log --parents shallow depth 48",
                }
                rows.append(run_goal(kernel, f"{name}:commit-ancestry", relation, relation_provenance))

                path, data, events = choose_python_source(repo)
                rel_path = path.relative_to(repo).as_posix()
                source_provenance = {
                    "repository": url,
                    "head_sha": head,
                    "path": rel_path,
                    "source_sha256": sha256(data),
                    "source_bytes": len(data),
                    "full_event_count": len(events),
                    "collector": "python tokenize OP brackets",
                }
                rows.append(run_goal(kernel, f"{name}:source-nesting-full",
                                     {"domain": "events", "events": events},
                                     {**source_provenance, "derived_view": "complete real source token stream"}))
                prefix = truncated_real_prefix(events)
                rows.append(run_goal(kernel, f"{name}:source-nesting-prefix",
                                     {"domain": "events", "events": prefix},
                                     {**source_provenance, "derived_view": "real token-stream prefix",
                                      "prefix_event_count": len(prefix)}))
                sources.append(source_provenance)

                if index < len(TARGETS) - 1:
                    kernel.close()
                    kernel = SuccessorKernel(manifest, state)

            verification = kernel.verify_state()
            snapshot = kernel.cognitive_snapshot()
        finally:
            kernel.close()

    passed = all(row["status"] == "VERIFIED" and row["independent_check"] for row in rows)
    report = {
        "schema": "yado.real_world_public_github_benchmark.v1",
        "status": "PASS_REAL_WORLD_PUBLIC_DATA_V1" if passed else "WITHHOLD_REAL_WORLD_PUBLIC_DATA_V1",
        "source_policy": "FRESH_PUBLIC_GITHUB_CLONES_AT_RUN_TIME",
        "repositories": [url for _, url in TARGETS],
        "goals_run": len(rows),
        "goals_verified": sum(row["status"] == "VERIFIED" for row in rows),
        "independent_checks_passed": sum(row["independent_check"] for row in rows),
        "results": rows,
        "source_receipts": sources,
        "state_verification": verification,
        "cognitive_snapshot": snapshot,
        "elapsed_seconds": time.time() - started,
        "answers_supplied_to_kernel": False,
        "general_intelligence_established": False,
        "consciousness_established": False,
    }
    (output / "receipt.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({
        "status": report["status"],
        "goals_run": report["goals_run"],
        "goals_verified": report["goals_verified"],
        "independent_checks_passed": report["independent_checks_passed"],
        "repositories": report["repositories"],
    }), flush=True)
    return 0 if passed and verification["status"] == "PASS" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    return run(args.manifest, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
