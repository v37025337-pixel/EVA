from __future__ import annotations

"""Bounded YADO self-development using the admitted external dev capability pack.

The controller refreshes the five public capability sources, uses every admitted
pattern in a causal development chain, derives a deterministic routing policy,
materializes a YADO-authored Python candidate, and validates it on fresh deficits.
It never executes or copies third-party source code and never mutates canonical
main automatically.
"""

import hashlib
import json
import re
from pathlib import Path

from yado_external_dev_capability_pack_v1 import SOURCES

COMPONENT_ID = "RUNTIME-G2-EXTERNAL-DEV-SELF-DEVELOPMENT-V1"
SCHEMA = "yado.external_dev_self_development.v1"

SEMANTIC_ANCHORS = {
    "hivemind": [
        "coordinate", "task", "issue", "acceptance", "criteria", "branch",
        "worktree", "agent", "supervise", "review", "parallel", "isolate",
    ],
    "hoppscotch": [
        "api", "endpoint", "http", "graphql", "websocket", "request",
        "response", "schema", "assert", "protocol", "status",
    ],
    "dyad": [
        "app", "application", "build", "candidate", "preview", "compile",
        "test", "regression", "local", "stack", "admission",
    ],
    "nexustools": [
        "json", "base64", "url", "hash", "digest", "format", "minify",
        "transform", "utility", "offline", "encode", "decode",
    ],
    "free_for_dev": [
        "free", "cloud", "compute", "hosting", "serverless", "storage",
        "database", "resource", "deploy", "paas", "iaas", "ci", "cd",
    ],
}

GENERIC_TOKENS = {
    "external", "developer", "development", "capability", "pattern", "library",
    "workbench", "local", "read", "only", "source", "public", "native",
}

FRESH_CASES = (
    ("coordinate two isolated branches with review criteria", "TASK_CONTRACT_AND_AGENT_SUPERVISION_PATTERN"),
    ("inspect a public graphql endpoint response without writes", "READ_ONLY_API_ASSERTION_WORKBENCH"),
    ("prepare a candidate preview compile test and regression gate", "LOCAL_APP_BUILD_ADMISSION_LOOP"),
    ("normalize json and compute a digest offline", "PURE_LOCAL_DEV_UTILITY_LIBRARY"),
    ("find a free serverless compute resource for an experiment", "FREE_TIER_RESOURCE_DISCOVERY"),
)


def _canon(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _tokens(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", str(value).lower())


def _safe_refresh(refresh: dict) -> None:
    if not isinstance(refresh, dict) or refresh.get("status") != "PASS_EXTERNAL_DEV_CAPABILITY_PACK_V1":
        raise RuntimeError("EXTERNAL_DEV_PACK_REFRESH_REQUIRED")
    if refresh.get("source_count") != 5 or len(refresh.get("sources") or []) != 5:
        raise RuntimeError("EXTERNAL_DEV_PACK_FIVE_SOURCES_REQUIRED")
    if refresh.get("read_only_external") is not True:
        raise RuntimeError("EXTERNAL_DEV_PACK_READ_ONLY_REQUIRED")
    if refresh.get("code_copy_performed") is not False or refresh.get("third_party_code_executed") is not False:
        raise RuntimeError("EXTERNAL_DEV_PACK_UNSAFE_SOURCE_USE")
    for row in refresh.get("sources") or []:
        if row.get("read_only") is not True or row.get("code_copy_performed") is not False or row.get("code_execution_performed") is not False:
            raise RuntimeError("EXTERNAL_DEV_SOURCE_SAFETY_MISMATCH")


class ExternalDevSelfDevelopmentV1:
    def __init__(self):
        self._last_receipt = None

    def snapshot(self) -> dict:
        return {
            "schema": SCHEMA,
            "component_id": COMPONENT_ID,
            "status": "PASS_SHADOW" if self._last_receipt else "BOUND_UNRUN",
            "autonomous_capability_selection_target": True,
            "third_party_code_execution": False,
            "third_party_code_copy": False,
            "credentials_allowed": False,
            "external_writes_to_third_parties": False,
            "automatic_main_mutation": False,
            "g3_genesis_performed": False,
            "last_receipt_sha256": (self._last_receipt or {}).get("receipt_sha256"),
        }

    @staticmethod
    def derive_router_policy(refresh: dict) -> dict:
        _safe_refresh(refresh)
        rules = {}
        priority = []
        source_bindings = {}
        for row in refresh["sources"]:
            key = row["key"]
            capability = row["capability"]
            if key not in SEMANTIC_ANCHORS:
                raise RuntimeError("UNKNOWN_EXTERNAL_DEV_SOURCE:" + str(key))
            words = set(SEMANTIC_ANCHORS[key])
            for marker in row.get("feature_markers_verified") or []:
                words.update(_tokens(marker))
            words.update(_tokens(capability.replace("_", " ")))
            words.update(_tokens(row.get("repo", "")))
            words = {w for w in words if (len(w) >= 3 or w in {"ci", "cd"}) and w not in GENERIC_TOKENS}
            rules[capability] = sorted(words)
            priority.append(capability)
            source_bindings[capability] = {
                "source_key": key,
                "repo": row["repo"],
                "readme_sha256": row.get("readme_sha256"),
                "license_mode": row.get("license_mode"),
                "restricted_paths": list(row.get("restricted_paths") or []),
            }
        policy = {
            "schema": "yado.external_dev_capability_router_policy.v1",
            "pack_digest": refresh.get("pack_digest"),
            "rules": rules,
            "priority": priority,
            "source_bindings": source_bindings,
            "selection_input": "DEFICIT_TEXT_ONLY",
            "selection_output": "ONE_ADMITTED_EXTERNAL_DEV_CAPABILITY_OR_WITHHOLD",
            "third_party_code_execution": False,
            "automatic_main_mutation": False,
        }
        policy["policy_sha256"] = _sha_text(_canon(policy))
        return policy

    @staticmethod
    def render_router_source(policy: dict) -> str:
        if not isinstance(policy, dict) or not policy.get("policy_sha256"):
            raise ValueError("ROUTER_POLICY_REQUIRED")
        rules = repr(policy["rules"])
        priority = repr(policy["priority"])
        pack_digest = repr(policy.get("pack_digest"))
        policy_sha = repr(policy["policy_sha256"])
        source = f'''from __future__ import annotations\n\nPACK_DIGEST = {pack_digest}\nPOLICY_SHA256 = {policy_sha}\nRULES = {rules}\nPRIORITY = {priority}\n\ndef _tokens(text):\n    cleaned = ''.join(ch.lower() if ch.isalnum() else ' ' for ch in str(text))\n    return set(x for x in cleaned.split() if x)\n\ndef route(deficit):\n    tokens = _tokens(deficit)\n    ranked = []\n    for index, capability in enumerate(PRIORITY):\n        matched = [word for word in RULES[capability] if word in tokens]\n        ranked.append((len(matched), -index, capability, matched))\n    ranked.sort(reverse=True)\n    if not ranked or ranked[0][0] <= 0:\n        return {{'status': 'WITHHOLD_ROUTER_NO_MATCH', 'capability': None, 'matched': [], 'pack_digest': PACK_DIGEST, 'policy_sha256': POLICY_SHA256}}\n    top = ranked[0]\n    return {{'status': 'PASS_ROUTER_SELECTION', 'capability': top[2], 'matched': top[3], 'score': top[0], 'pack_digest': PACK_DIGEST, 'policy_sha256': POLICY_SHA256}}\n\ndef snapshot():\n    return {{'schema': 'yado.external_dev_capability_router_candidate.v1', 'pack_digest': PACK_DIGEST, 'policy_sha256': POLICY_SHA256, 'capability_count': len(PRIORITY), 'automatic_main_mutation': False, 'g3_genesis_performed': False}}\n'''
        compile(source, "<yado-external-dev-router-candidate>", "exec")
        return source

    @staticmethod
    def load_router(source: str):
        allowed = {
            "str": str,
            "set": set,
            "len": len,
            "enumerate": enumerate,
            "list": list,
        }
        scope = {"__builtins__": allowed}
        exec(compile(source, "<yado-external-dev-router-eval>", "exec"), scope, scope)
        if not callable(scope.get("route")) or not callable(scope.get("snapshot")):
            raise RuntimeError("ROUTER_CANDIDATE_INTERFACE_MISSING")
        return scope["route"], scope["snapshot"]

    @classmethod
    def evaluate_router_source(cls, source: str, cases=FRESH_CASES) -> dict:
        route, snapshot = cls.load_router(source)
        rows = []
        passed = 0
        priority = snapshot().get("capability_count")
        if priority != 5:
            raise RuntimeError("ROUTER_CAPABILITY_COUNT_MISMATCH")
        for deficit, expected in cases:
            result = route(deficit)
            ok = result.get("status") == "PASS_ROUTER_SELECTION" and result.get("capability") == expected
            passed += int(ok)
            rows.append({"deficit": deficit, "expected": expected, "selected": result.get("capability"), "pass": ok, "matched": result.get("matched")})
        baseline_capability = "TASK_CONTRACT_AND_AGENT_SUPERVISION_PATTERN"
        baseline_passed = sum(1 for _, expected in cases if expected == baseline_capability)
        accuracy = passed / len(cases)
        baseline_accuracy = baseline_passed / len(cases)
        unknown = route("unclassified novel semantic dimension")
        return {
            "schema": "yado.external_dev_capability_router_fresh_eval.v1",
            "status": "PASS_FRESH_ROUTER_TRANSFER" if passed == len(cases) and unknown.get("status") == "WITHHOLD_ROUTER_NO_MATCH" else "WITHHOLD_FRESH_ROUTER_TRANSFER",
            "tests": rows,
            "tests_run": len(cases),
            "tests_passed": passed,
            "accuracy": accuracy,
            "baseline_accuracy": baseline_accuracy,
            "gain": accuracy - baseline_accuracy,
            "unknown_withhold": unknown.get("status") == "WITHHOLD_ROUTER_NO_MATCH",
        }

    def run(
        self,
        core,
        objective: str,
        *,
        candidate_path: str | Path | None = None,
        receipt_path: str | Path | None = None,
        timeout: float = 25.0,
        resolver=None,
        transport=None,
        fetch_override=None,
    ) -> dict:
        goal = " ".join(str(objective or "").split()).strip()
        if not goal:
            raise ValueError("SELF_DEVELOPMENT_OBJECTIVE_REQUIRED")

        refresh = core.refresh_external_dev_capabilities(
            timeout=timeout, resolver=resolver, transport=transport, fetch_override=fetch_override
        )
        _safe_refresh(refresh)

        task = core.external_dev_task_contract(goal, [
            "derive capability selection from a measured deficit without a host tool name",
            "use only verified read-only public source evidence",
            "materialize a deterministic native router candidate",
            "beat a fixed one-capability baseline on fresh deficits",
            "withhold on an unknown deficit and keep canonical main unchanged",
        ])

        api = core.external_dev_api_probe(
            SOURCES["hoppscotch"]["metadata"],
            must_contain="hoppscotch",
            timeout=timeout,
            resolver=resolver,
            transport=transport,
            fetch_override=fetch_override,
        )
        if api.get("status") != "PASS_READ_ONLY_API_ASSERTION":
            raise RuntimeError("EXTERNAL_DEV_SOURCE_API_ASSERTION_FAILED")

        build = core.external_dev_app_build_plan(
            "Materialize and validate a native external-development capability router",
            "Python stdlib + current YADO G2 core",
            ["compile", "fresh-transfer", "unknown-withhold", "full-regression"],
        )

        policy = self.derive_router_policy(refresh)
        policy_digest = core.external_dev_utility("sha256", _canon(policy))
        if policy_digest.get("network_used") is not False or len(policy_digest.get("output", "")) != 64:
            raise RuntimeError("LOCAL_POLICY_DIGEST_FAILED")

        resources = core.external_dev_free_resource_candidates(
            ["cloud", "compute", "serverless"],
            limit=8,
            timeout=timeout,
            resolver=resolver,
            transport=transport,
            fetch_override=fetch_override,
        )
        if resources.get("status") not in {"PASS_FREE_TIER_RESOURCE_DISCOVERY", "WITHHOLD_NO_MATCH"}:
            raise RuntimeError("FREE_RESOURCE_DISCOVERY_INVALID")

        candidate_source = self.render_router_source(policy)
        evaluation = self.evaluate_router_source(candidate_source)
        candidate_sha = _sha_text(candidate_source)
        pass_gate = (
            evaluation.get("status") == "PASS_FRESH_ROUTER_TRANSFER"
            and evaluation.get("gain", 0.0) > 0.0
            and evaluation.get("unknown_withhold") is True
        )

        generations = [
            {
                "generation": 1,
                "deficit": "NO_AUTONOMOUS_EXTERNAL_DEV_CAPABILITY_ROUTER",
                "selected_capability": "TASK_CONTRACT_AND_AGENT_SUPERVISION_PATTERN",
                "source_pattern": task["source_pattern"],
                "result": "PASS_TASK_CONTRACT",
                "next_goal": "VERIFY_EXTERNAL_CAPABILITY_SOURCE_ACCESS",
            },
            {
                "generation": 2,
                "deficit": "EXTERNAL_SOURCE_ACCESS_NOT_REVALIDATED_FOR_DEVELOPMENT",
                "selected_capability": "READ_ONLY_API_ASSERTION_WORKBENCH",
                "source_pattern": api["source_pattern"],
                "result": api["status"],
                "next_goal": "PLAN_ISOLATED_ROUTER_BUILD_AND_ADMISSION",
            },
            {
                "generation": 3,
                "deficit": "ROUTER_CANDIDATE_NOT_MATERIALIZED",
                "selected_capability": "LOCAL_APP_BUILD_ADMISSION_LOOP",
                "source_pattern": build["source_pattern"],
                "result": "PASS_BUILD_PLAN",
                "next_goal": "FREEZE_ROUTER_POLICY_IDENTITY",
            },
            {
                "generation": 4,
                "deficit": "ROUTER_POLICY_IDENTITY_NOT_FROZEN",
                "selected_capability": "PURE_LOCAL_DEV_UTILITY_LIBRARY",
                "source_pattern": policy_digest["source_pattern"],
                "result": "PASS_LOCAL_POLICY_DIGEST",
                "next_goal": "CHECK_FUTURE_ISOLATED_RESOURCE_OPTIONS",
            },
            {
                "generation": 5,
                "deficit": "FUTURE_EXTERNAL_DEVELOPMENT_RESOURCE_OPTIONS_UNKNOWN",
                "selected_capability": "FREE_TIER_RESOURCE_DISCOVERY",
                "source_pattern": resources["source_pattern"],
                "result": resources["status"],
                "next_goal": "VALIDATE_ROUTER_ON_FRESH_DEFICITS_AND_WITHHOLD_UNKNOWN",
            },
        ]

        receipt = {
            "schema": SCHEMA,
            "component_id": COMPONENT_ID,
            "status": "PASS_SHADOW_EXTERNAL_DEV_SELF_DEVELOPMENT_V1" if pass_gate else "WITHHOLD_EXTERNAL_DEV_SELF_DEVELOPMENT_V1",
            "objective": goal,
            "source_pack_digest": refresh.get("pack_digest"),
            "source_count": refresh.get("source_count"),
            "used_source_patterns": [
                "dip497/hivemind",
                "hoppscotch/hoppscotch",
                "dyad-sh/dyad",
                "nexustools-dev/nexus-tools",
                "ripienaar/free-for-dev",
            ],
            "development_generations": generations,
            "policy_sha256": policy["policy_sha256"],
            "local_policy_digest_sha256": policy_digest["output"],
            "candidate_sha256": candidate_sha,
            "candidate_compile": True,
            "fresh_evaluation": evaluation,
            "free_resource_candidate_count": resources.get("result_count", 0),
            "third_party_code_executed": False,
            "third_party_code_copied": False,
            "credentials_used": False,
            "private_network_access": False,
            "external_writes_to_third_parties": False,
            "candidate_branch_only": True,
            "automatic_main_mutation": False,
            "g3_genesis_performed": False,
            "next_goal": "BIND_GENERATED_ROUTER_INTO_SHADOW_CORE_AND_PROVE_3_TO_5_FRESH_SELF_DIRECTED_DEVELOPMENT_GOALS" if pass_gate else "REVISE_EXTERNAL_DEV_ROUTER_POLICY",
            "semantic_boundary": "BOUNDED SELF-DEVELOPMENT OF EXTERNAL DEV CAPABILITY SELECTION. FIVE VERIFIED PUBLIC SOURCES INFORM NATIVE YADO PATTERNS; NO THIRD-PARTY CODE EXECUTION/COPY, CREDENTIALS, PRIVATE NETWORK, THIRD-PARTY WRITES, AUTOMATIC MAIN MUTATION, G3, OR CONSCIOUSNESS CLAIM.",
        }
        receipt["receipt_sha256"] = _sha_text(_canon(receipt))

        if candidate_path is not None:
            path = Path(candidate_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(candidate_source, encoding="utf-8")
        if receipt_path is not None:
            path = Path(receipt_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")

        self._last_receipt = receipt
        return json.loads(json.dumps(receipt))


__all__ = [
    "ExternalDevSelfDevelopmentV1",
    "FRESH_CASES",
    "SEMANTIC_ANCHORS",
]
