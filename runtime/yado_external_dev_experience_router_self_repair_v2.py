from __future__ import annotations

"""Experience-derived repair of the admitted external-development router.

The admitted V1 router uses raw matched-token counts. The seven-goal residual
campaign retained enough evidence to expose a concrete weakness: unrelated
resource-description words can outweigh the actual continuation intent.

This layer does not accept a hand-written replacement policy. It reuses the
admitted V1 rule vocabulary and priority, learns positive weights from the
retained campaign events plus the admitted bootstrap transfer cases, reproduces
the contamination failure from retained resource evidence, and materializes a
new restricted Python router candidate. The candidate must preserve all retained
routes, repair the reproduced case, transfer to a second held-out contaminated
historical goal, and WITHHOLD on unknown semantics.

The result is shadow-only. Canonical/main mutation remains externally gated.
"""

import hashlib
import json
import re
from pathlib import Path

from yado_external_dev_multigoal_campaign_v1 import digest
from yado_external_dev_self_development_v1 import FRESH_CASES

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_ROUTER = ROOT / "candidates/autonomous/yado_external_dev_capability_router_candidate_v1.py"
DEFAULT_HISTORY_RECEIPT = ROOT / "candidates/autonomous/yado-external-dev-residual-continuation-v2.json"

COMPONENT_ID = "RUNTIME-G2-EXPERIENCE-ROUTER-SELF-REPAIR-V2"
SCHEMA = "yado.external_dev_experience_router_self_repair.v2"
POSITIVE_MULTIPLIER = 3
EXPECTED_HISTORY_STATUS = "PASS_SHADOW_EXTERNAL_DEV_RESIDUAL_CONTINUATION_V2"


def _canon(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", str(value).lower()))


def _clone(value):
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _load_base_router(source: str):
    allowed = {"str": str, "set": set, "len": len, "enumerate": enumerate, "list": list}
    scope = {"__builtins__": allowed}
    exec(compile(source, "<yado-base-router-v1>", "exec"), scope, scope)
    required = {"PACK_DIGEST", "POLICY_SHA256", "RULES", "PRIORITY", "route", "snapshot"}
    if not required <= set(scope):
        raise RuntimeError("BASE_ROUTER_INTERFACE_MISSING")
    rules = scope["RULES"]
    priority = scope["PRIORITY"]
    if not isinstance(rules, dict) or not isinstance(priority, list) or set(rules) != set(priority):
        raise RuntimeError("BASE_ROUTER_POLICY_INVALID")
    if scope["snapshot"]().get("capability_count") != len(priority):
        raise RuntimeError("BASE_ROUTER_CAPABILITY_COUNT_MISMATCH")
    return {
        "pack_digest": scope["PACK_DIGEST"],
        "policy_sha256": scope["POLICY_SHA256"],
        "rules": {key: list(value) for key, value in rules.items()},
        "priority": list(priority),
        "route": scope["route"],
    }


def _validate_history(receipt: dict, base_source_sha256: str, base_policy_sha256: str) -> None:
    if not isinstance(receipt, dict) or receipt.get("status") != EXPECTED_HISTORY_STATUS:
        raise RuntimeError("EXPERIENCE_ROUTER_VERIFIED_HISTORY_REQUIRED")
    if receipt.get("goal_count") != 7 or receipt.get("chain_verification", {}).get("status") != "PASS":
        raise RuntimeError("EXPERIENCE_ROUTER_SEVEN_GOAL_HISTORY_REQUIRED")
    if receipt.get("unknown_withhold") is not True:
        raise RuntimeError("EXPERIENCE_ROUTER_HISTORY_UNKNOWN_WITHHOLD_REQUIRED")
    if receipt.get("automatic_main_mutation") is not False or receipt.get("g3_genesis_performed") is not False:
        raise RuntimeError("EXPERIENCE_ROUTER_HISTORY_BOUNDARY_MISMATCH")
    if receipt.get("router_source_sha256") != base_source_sha256:
        raise RuntimeError("EXPERIENCE_ROUTER_BASE_SOURCE_DRIFT")
    if receipt.get("router_policy_sha256") != base_policy_sha256:
        raise RuntimeError("EXPERIENCE_ROUTER_BASE_POLICY_DRIFT")

    events = receipt.get("events") or []
    if len(events) != 7:
        raise RuntimeError("EXPERIENCE_ROUTER_EVENT_COUNT_MISMATCH")
    previous = None
    for index, event in enumerate(events, start=1):
        if event.get("cycle") != index or event.get("previous_event_sha256") != previous:
            raise RuntimeError("EXPERIENCE_ROUTER_EVENT_CHAIN_BROKEN")
        base = dict(event)
        recorded = base.pop("event_sha256", None)
        if recorded != digest(base):
            raise RuntimeError("EXPERIENCE_ROUTER_EVENT_DIGEST_MISMATCH")
        previous = recorded
    if previous != receipt.get("chain_verification", {}).get("head_event_sha256"):
        raise RuntimeError("EXPERIENCE_ROUTER_CHAIN_HEAD_MISMATCH")


def _derive_training(receipt: dict, priority: list[str], base_route):
    rows = [
        {"text": text, "expected": expected, "origin": "ADMITTED_V1_BOOTSTRAP"}
        for text, expected in FRESH_CASES
    ]
    events = receipt["events"]
    for event in events:
        expected = event.get("selected_capability")
        if expected not in priority:
            raise RuntimeError("EXPERIENCE_ROUTER_UNKNOWN_HISTORY_CAPABILITY")
        rows.append({
            "text": event["goal"],
            "expected": expected,
            "origin": "RETAINED_CAMPAIGN_EVENT_" + str(event["cycle"]),
        })

    description = str((receipt.get("resource_candidate") or {}).get("description") or "").strip()
    if not description:
        raise RuntimeError("EXPERIENCE_ROUTER_RESOURCE_DESCRIPTION_REQUIRED")
    utility_events = [
        event for event in events
        if event.get("selected_capability") == "PURE_LOCAL_DEV_UTILITY_LIBRARY"
    ]
    if len(utility_events) < 2:
        raise RuntimeError("EXPERIENCE_ROUTER_TWO_UTILITY_EVENTS_REQUIRED")

    repair_event = utility_events[-1]
    repair_text = repair_event["goal"] + " " + description
    base_repair = base_route(repair_text)
    if base_repair.get("capability") == repair_event["selected_capability"]:
        raise RuntimeError("EXPERIENCE_ROUTER_REPRODUCED_DEFECT_REQUIRED")
    rows.append({
        "text": repair_text,
        "expected": repair_event["selected_capability"],
        "origin": "RETAINED_RESOURCE_DESCRIPTION_CONTAMINATION_REPAIR",
    })

    holdout_event = utility_events[0]
    holdout_text = holdout_event["goal"] + " " + description
    if holdout_text == repair_text:
        raise RuntimeError("EXPERIENCE_ROUTER_FRESH_HOLDOUT_REQUIRED")

    return rows, {
        "repair_text": repair_text,
        "repair_expected": repair_event["selected_capability"],
        "repair_base": _clone(base_repair),
        "holdout_text": holdout_text,
        "holdout_expected": holdout_event["selected_capability"],
        "holdout_base": _clone(base_route(holdout_text)),
        "resource_description_sha256": _sha_text(description),
    }


def derive_weights(base_rules: dict, priority: list[str], training_rows: list[dict]) -> dict:
    weights = {}
    for capability in priority:
        capability_weights = {}
        for token in base_rules[capability]:
            positive = sum(
                1 for row in training_rows
                if row["expected"] == capability and token in _tokens(row["text"])
            )
            negative = sum(
                1 for row in training_rows
                if row["expected"] != capability and token in _tokens(row["text"])
            )
            score = POSITIVE_MULTIPLIER * positive - negative
            if score > 0:
                capability_weights[token] = score
        if not capability_weights:
            raise RuntimeError("EXPERIENCE_ROUTER_EMPTY_CAPABILITY_PROFILE:" + capability)
        weights[capability] = capability_weights
    return weights


def render_candidate_source(base: dict, weights: dict, training_digest: str) -> str:
    source = f'''BASE_ROUTER_SOURCE_SHA256 = {base["source_sha256"]!r}\nBASE_POLICY_SHA256 = {base["policy_sha256"]!r}\nPACK_DIGEST = {base["pack_digest"]!r}\nTRAINING_DIGEST = {training_digest!r}\nWEIGHTS = {weights!r}\nPRIORITY = {base["priority"]!r}\n\ndef _tokens(text):\n    cleaned = ''.join(ch.lower() if ch.isalnum() else ' ' for ch in str(text))\n    return set(x for x in cleaned.split() if x)\n\ndef route(deficit):\n    tokens = _tokens(deficit)\n    ranked = []\n    for index, capability in enumerate(PRIORITY):\n        profile = WEIGHTS[capability]\n        matched = [word for word in profile if word in tokens]\n        raw = sum(profile[word] for word in matched)\n        total = sum(profile.values())\n        score = (raw / total) if total else 0.0\n        ranked.append((score, -index, capability, matched, raw, total))\n    ranked.sort(reverse=True)\n    if not ranked or ranked[0][0] <= 0.0:\n        return {{'status': 'WITHHOLD_ROUTER_NO_MATCH', 'capability': None, 'matched': [], 'score': 0.0, 'pack_digest': PACK_DIGEST, 'training_digest': TRAINING_DIGEST}}\n    top = ranked[0]\n    return {{'status': 'PASS_ROUTER_SELECTION', 'capability': top[2], 'matched': top[3], 'score': top[0], 'raw_score': top[4], 'profile_total': top[5], 'pack_digest': PACK_DIGEST, 'training_digest': TRAINING_DIGEST}}\n\ndef snapshot():\n    return {{'schema': 'yado.external_dev_experience_router_candidate.v2', 'base_policy_sha256': BASE_POLICY_SHA256, 'training_digest': TRAINING_DIGEST, 'capability_count': len(PRIORITY), 'scoring': 'NORMALIZED_EXPERIENCE_WEIGHTED_COVERAGE', 'automatic_main_mutation': False, 'g3_genesis_performed': False}}\n'''
    compile(source, "<yado-experience-router-candidate-v2>", "exec")
    return source


def load_candidate(source: str):
    allowed = {
        "str": str,
        "set": set,
        "len": len,
        "enumerate": enumerate,
        "list": list,
        "sum": sum,
    }
    scope = {"__builtins__": allowed}
    exec(compile(source, "<yado-experience-router-candidate-v2-eval>", "exec"), scope, scope)
    if not callable(scope.get("route")) or not callable(scope.get("snapshot")):
        raise RuntimeError("EXPERIENCE_ROUTER_CANDIDATE_INTERFACE_MISSING")
    return scope["route"], scope["snapshot"]


class ExternalDevExperienceRouterSelfRepairV2:
    def __init__(self, base_router_path=None, history_receipt_path=None):
        self.base_router_path = Path(base_router_path or DEFAULT_BASE_ROUTER)
        self.history_receipt_path = Path(history_receipt_path or DEFAULT_HISTORY_RECEIPT)

    def run(self, *, candidate_path=None, receipt_path=None) -> dict:
        base_source = self.base_router_path.read_text(encoding="utf-8")
        base = _load_base_router(base_source)
        base["source_sha256"] = _sha_text(base_source)
        history = json.loads(self.history_receipt_path.read_text(encoding="utf-8"))
        _validate_history(history, base["source_sha256"], base["policy_sha256"])

        training_rows, probes = _derive_training(history, base["priority"], base["route"])
        training_digest = _sha_text(_canon(training_rows))
        weights = derive_weights(base["rules"], base["priority"], training_rows)
        candidate_source = render_candidate_source(base, weights, training_digest)
        candidate_sha256 = _sha_text(candidate_source)
        route, snapshot = load_candidate(candidate_source)

        history_results = []
        for event in history["events"]:
            result = route(event["goal"])
            passed = (
                result.get("status") == "PASS_ROUTER_SELECTION"
                and result.get("capability") == event["selected_capability"]
            )
            history_results.append({
                "cycle": event["cycle"],
                "expected": event["selected_capability"],
                "selected": result.get("capability"),
                "pass": passed,
            })

        bootstrap_results = []
        for text, expected in FRESH_CASES:
            result = route(text)
            bootstrap_results.append({
                "expected": expected,
                "selected": result.get("capability"),
                "pass": result.get("capability") == expected,
            })

        repair_after = route(probes["repair_text"])
        holdout_after = route(probes["holdout_text"])
        unknown = route("evaluate an unclassified quantum biology hypothesis")
        candidate_snapshot = snapshot()

        base_repair_failed = probes["repair_base"].get("capability") != probes["repair_expected"]
        base_holdout_failed = probes["holdout_base"].get("capability") != probes["holdout_expected"]
        repair_passed = repair_after.get("capability") == probes["repair_expected"]
        holdout_passed = holdout_after.get("capability") == probes["holdout_expected"]
        retained_passed = all(row["pass"] for row in history_results)
        bootstrap_passed = all(row["pass"] for row in bootstrap_results)
        unknown_withhold = unknown.get("status") == "WITHHOLD_ROUTER_NO_MATCH"
        source_changed = candidate_sha256 != base["source_sha256"]
        pass_gate = all((
            base_repair_failed,
            base_holdout_failed,
            repair_passed,
            holdout_passed,
            retained_passed,
            bootstrap_passed,
            unknown_withhold,
            source_changed,
            candidate_snapshot.get("automatic_main_mutation") is False,
            candidate_snapshot.get("g3_genesis_performed") is False,
        ))

        out = {
            "schema": SCHEMA,
            "component_id": COMPONENT_ID,
            "status": (
                "PASS_SHADOW_EXPERIENCE_ROUTER_SELF_REPAIR_V2"
                if pass_gate else "WITHHOLD_EXPERIENCE_ROUTER_SELF_REPAIR_V2"
            ),
            "mutation_origin": "RETAINED_CAMPAIGN_ROUTING_DEFECT",
            "base_router_source_sha256": base["source_sha256"],
            "base_policy_sha256": base["policy_sha256"],
            "source_pack_digest": base["pack_digest"],
            "history_receipt_sha256": history.get("receipt_sha256"),
            "history_event_count": len(history["events"]),
            "training_row_count": len(training_rows),
            "training_digest": training_digest,
            "candidate_source_sha256": candidate_sha256,
            "candidate_compile": True,
            "candidate_snapshot": candidate_snapshot,
            "weights_sha256": _sha_text(_canon(weights)),
            "retained_history_replay": history_results,
            "bootstrap_retention": bootstrap_results,
            "reproduced_defect": {
                "expected": probes["repair_expected"],
                "base_selected": probes["repair_base"].get("capability"),
                "candidate_selected": repair_after.get("capability"),
                "base_failed": base_repair_failed,
                "candidate_passed": repair_passed,
            },
            "fresh_contamination_holdout": {
                "expected": probes["holdout_expected"],
                "base_selected": probes["holdout_base"].get("capability"),
                "candidate_selected": holdout_after.get("capability"),
                "base_failed": base_holdout_failed,
                "candidate_passed": holdout_passed,
                "gain_over_base": int(holdout_passed) - int(not base_holdout_failed),
            },
            "resource_description_sha256": probes["resource_description_sha256"],
            "unknown_withhold": unknown_withhold,
            "third_party_code_executed": False,
            "third_party_code_copied": False,
            "credentials_used": False,
            "private_network_access": False,
            "external_writes_to_third_parties": False,
            "candidate_branch_only": True,
            "automatic_main_mutation": False,
            "g3_genesis_performed": False,
            "next_goal": (
                "BIND_EXPERIENCE_WEIGHTED_ROUTER_TO_SHADOW_CAMPAIGN_AND_PROVE_THREE_STATE_DERIVED_GENERATIONS"
                if pass_gate else "REVISE_EXPERIENCE_ROUTER_SELF_REPAIR"
            ),
            "semantic_boundary": (
                "BOUNDED EXPERIENCE-DERIVED ROUTER SCORING REPAIR USING THE ADMITTED V1 VOCABULARY, "
                "RETAINED SEVEN-GOAL HISTORY, AND RETAINED RESOURCE DESCRIPTION. NO THIRD-PARTY CODE "
                "EXECUTION OR COPY, NO CREDENTIALS, NO EXTERNAL WRITES, NO AUTOMATIC MAIN MUTATION, "
                "NO G3 CLAIM, AND NO CONSCIOUSNESS CLAIM."
            ),
        }
        out["receipt_sha256"] = _sha_text(_canon(out))

        if candidate_path is not None:
            path = Path(candidate_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(candidate_source, encoding="utf-8")
        if receipt_path is not None:
            path = Path(receipt_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return out


__all__ = [
    "COMPONENT_ID",
    "SCHEMA",
    "ExternalDevExperienceRouterSelfRepairV2",
    "derive_weights",
    "render_candidate_source",
    "load_candidate",
]
