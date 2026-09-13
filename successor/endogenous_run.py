"""Bounded endogenous continuation for the YADO Successor.

This module removes one narrow host dependency from the active acceptance loop:
the host supplies only a cycle budget.  Each concrete goal instance is selected
from the kernel's verified causal state and generated without labelled answers.

The goal grammar and controller remain assistant-authored and bounded.  This is
evidence for endogenous goal continuation inside that grammar, not evidence of
general intelligence, agency outside the process, or phenomenal consciousness.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .archive import canonical, sha
from .kernel import SuccessorKernel, fingerprint

DOMAINS = ("relation", "events")


def _pressure(snapshot, domain):
    """Prefer the domain with weaker or less certain verified experience."""
    stats = snapshot.get("all_observations", {})
    items = [value for key, value in stats.items() if key.startswith(domain + "/")]
    successes = sum(int(item.get("successes", 0)) for item in items)
    failures = sum(int(item.get("failures", 0)) for item in items)
    count = successes + failures
    squared_error = sum(float(item.get("squared_error", 0.0)) for item in items)
    failure_pressure = (failures + 1.0) / (count + 2.0)
    novelty_pressure = 1.0 / (count + 1.0)
    calibration_pressure = squared_error / max(1, count)
    return failure_pressure + novelty_pressure + 0.10 * calibration_pressure


def _relation_spec(seed):
    raw = bytes.fromhex(seed)
    base = int(seed[:8], 16) % 1_000_000
    count = 4 + raw[4] % 5
    nodes = [base + index for index in range(count)]
    edges = [[nodes[index], nodes[index + 1]] for index in range(count - 1)]
    for byte in raw[8:24]:
        left = nodes[byte % count]
        right = nodes[(byte // count) % count]
        edge = [left, right]
        if left != right and edge not in edges:
            edges.append(edge)
    return {"domain": "relation", "relation": edges, "start": nodes[0]}


def _events_spec(seed):
    raw = bytes.fromhex(seed)
    a = "e" + seed[8:14]
    b = "e" + seed[14:20]
    shape = raw[5] % 4
    if shape == 0:
        events = [["Q", a], ["Q", b], ["R", b], ["R", a]]
    elif shape == 1:
        events = [["Q", a], ["Q", b], ["R", a], ["R", b]]
    elif shape == 2:
        events = [["Q", a], ["Q", b], ["R", b]]
    else:
        events = [["R", a]]
    return {"domain": "events", "events": events}


def propose_endogenous_goal(kernel):
    """Derive one fresh bounded goal instance from current verified state."""
    verification = kernel.verify_state()
    snapshot = kernel.cognitive_snapshot()
    active = [goal for goal in snapshot["goals"].values() if goal["status"] == "ACTIVE"]
    if active:
        raise ValueError("ENDOGENOUS_PROPOSAL_REQUIRES_IDLE_COGNITIVE_LOOP")

    ordinal = len(snapshot["goals"])
    seed = sha(canonical({
        "identity": kernel.identity,
        "causal_event_hash": verification["event_hash"],
        "goal_ordinal": ordinal,
    }).encode())
    pressures = {domain: _pressure(snapshot, domain) for domain in DOMAINS}
    maximum = max(pressures.values())
    candidates = [domain for domain in DOMAINS if pressures[domain] == maximum]
    selected = candidates[int(seed[:8], 16) % len(candidates)]
    spec = _relation_spec(seed) if selected == "relation" else _events_spec(seed)

    return {
        "schema": "yado.endogenous_goal_proposal.v1",
        "status": "PROPOSED_BOUNDED_ENDOGENOUS_GOAL",
        "host_supplied_goal": False,
        "selected_from_fixed_goal_list": False,
        "selection_basis": "EMPIRICAL_DEFICIT_PRESSURE_PLUS_CAUSAL_STATE",
        "source_event_hash": verification["event_hash"],
        "goal_ordinal": ordinal,
        "pressures": pressures,
        "selected_domain": selected,
        "seed": seed,
        "spec": spec,
        "spec_digest": fingerprint(spec),
        "goal_grammar_authorship": "ASSISTANT_AUTHORED_BOUNDED_GRAMMAR",
        "goal_instance_authorship": "YADO_STATE_DERIVED",
        "consciousness_claimed": False,
    }


def _append_event(kernel, body, expected_event_hash=None):
    kernel._check_sources()
    kernel.db.execute("BEGIN IMMEDIATE")
    try:
        verification = kernel.verify_state()
        if expected_event_hash is not None and verification["event_hash"] != expected_event_hash:
            raise ValueError("STALE_ENDOGENOUS_PROPOSAL")
        event = kernel._append(body)
        kernel.db.execute("COMMIT")
        return event
    except BaseException:
        kernel.db.execute("ROLLBACK")
        raise


def run_endogenous_cycles(kernel, cycles=4, budget=3):
    """Generate, pursue, verify and remember a bounded sequence of own goals."""
    if type(cycles) is not int or not 1 <= cycles <= 32:
        raise ValueError("ENDOGENOUS_CYCLE_BUDGET")
    if type(budget) is not int or not 1 <= budget <= 30:
        raise ValueError("ENDOGENOUS_GOAL_BUDGET")

    # Resume any interrupted work before creating a new goal instance.
    kernel.think(200)
    snapshot = kernel.cognitive_snapshot()
    if any(goal["status"] == "ACTIVE" for goal in snapshot["goals"].values()):
        raise ValueError("ACTIVE_GOAL_DID_NOT_SETTLE")

    rows = []
    for _ in range(cycles):
        proposal = propose_endogenous_goal(kernel)
        proposal_event = _append_event(kernel, {
            "kind": "ENDOGENOUS_GOAL_PROPOSED",
            "proposal_schema": proposal["schema"],
            "host_supplied_goal": False,
            "selected_from_fixed_goal_list": False,
            "selection_basis": proposal["selection_basis"],
            "source_event_hash": proposal["source_event_hash"],
            "goal_ordinal": proposal["goal_ordinal"],
            "pressures": proposal["pressures"],
            "selected_domain": proposal["selected_domain"],
            "seed": proposal["seed"],
            "spec": proposal["spec"],
            "spec_digest": proposal["spec_digest"],
            "goal_grammar_authorship": proposal["goal_grammar_authorship"],
            "goal_instance_authorship": proposal["goal_instance_authorship"],
            "automatic_canonical_promotion": False,
        }, expected_event_hash=proposal["source_event_hash"])

        goal_id = kernel.open_goal(proposal["spec"], budget=budget)
        _append_event(kernel, {
            "kind": "ENDOGENOUS_GOAL_BOUND",
            "proposal_tick": proposal_event["tick"],
            "goal_id_cognitive": goal_id,
            "spec_digest": proposal["spec_digest"],
            "automatic_canonical_promotion": False,
        })
        kernel.think(100)
        goal = kernel.cognitive_snapshot()["goals"][str(goal_id)]
        rows.append({
            "proposal_tick": proposal_event["tick"],
            "goal_id": goal_id,
            "selected_domain": proposal["selected_domain"],
            "seed": proposal["seed"],
            "spec_digest": proposal["spec_digest"],
            "status": goal["status"],
            "attempted": goal["attempted"],
            "spent": goal["budget"] - goal["remaining"],
        })

    passed = all(row["status"] == "VERIFIED" for row in rows)
    return {
        "schema": "yado.bounded_endogenous_continuation.v1",
        "status": "PASS_BOUNDED_ENDOGENOUS_CONTINUATION_V1" if passed else "WITHHOLD_BOUNDED_ENDOGENOUS_CONTINUATION_V1",
        "cycles_requested": cycles,
        "cycles_completed": len(rows),
        "cycles_verified": sum(row["status"] == "VERIFIED" for row in rows),
        "host_goal_count": 0,
        "goal_instance_authorship": "YADO_STATE_DERIVED",
        "goal_grammar_authorship": "ASSISTANT_AUTHORED_BOUNDED_GRAMMAR",
        "selection_basis": "EMPIRICAL_DEFICIT_PRESSURE_PLUS_CAUSAL_STATE",
        "results": rows,
        "state_verification": kernel.verify_state(),
        "automatic_canonical_promotion": False,
        "general_intelligence_established": False,
        "consciousness_established": False,
        "g3_genesis_performed": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--cycles", type=int, default=4)
    parser.add_argument("--budget", type=int, default=3)
    args = parser.parse_args()

    kernel = SuccessorKernel(args.manifest, args.state)
    try:
        report = run_endogenous_cycles(kernel, cycles=args.cycles, budget=args.budget)
    finally:
        kernel.close()
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ("status", "cycles_completed", "cycles_verified", "host_goal_count")}))
    return 0 if report["status"].startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
