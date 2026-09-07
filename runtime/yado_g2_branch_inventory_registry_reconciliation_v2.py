from __future__ import annotations

from pathlib import Path
import copy
import hashlib
import json
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))

from yado_evolution_ledger_v2 import validate_ledger_v2, event_hash

HEAD = REPO / "canonical/yado-main-head-g2.json"
CORE = REPO / "canonical/yado-unified-core-v1.json"
REG = REPO / "canonical/yado-unified-experience-registry-v1.json"
CTX = REPO / "canonical/yado-unified-context-kernel-v1.json"
LEDGER = REPO / "architecture/evolution-ledger.json"
REQ = REPO / "architecture/yado-g2-branch-inventory-registry-reconciliation-v2-request.json"
OUT = ROOT / "yado_g2_branch_inventory_registry_reconciliation_v2_receipt.json"
GUARD = ROOT / "yado_canonical_invariant_guard_v1.py"
ACTIVE = "yado-architecture-shadow-search"


def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def h(obj):
    return hashlib.sha256(canon(obj).encode()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, obj):
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def content_digest(obj, field):
    x = copy.deepcopy(obj)
    x.pop(field, None)
    return h(x)


def run_git(*args, check=True):
    p = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, timeout=120)
    if check and p.returncode != 0:
        raise RuntimeError("GIT_FAILED:" + repr(args) + ":" + p.stderr[-2000:])
    return p


head, core, reg, ctx, ledger, req = map(load, [HEAD, CORE, REG, CTX, LEDGER, REQ])
validate_ledger_v2(ledger)

generation = head["generation_id"]
frontier = (ledger.get("open_deficits") or [None])[0]
if generation != ledger.get("current_head"):
    raise RuntimeError("GENERATION_SPLIT_BRAIN")
if head.get("canonical_head_digest") != ledger.get("current_head_digest"):
    raise RuntimeError("HEAD_DIGEST_SPLIT_BRAIN")
if len(ledger.get("open_deficits", [])) != 1:
    raise RuntimeError("EXPECTED_ONE_FRONTIER")
if head.get("current_frontier") != frontier or core.get("current_frontier") != frontier:
    raise RuntimeError("FRONTIER_SPLIT_BRAIN")
if head.get("g3_genesis_performed") is not False:
    raise RuntimeError("G3_ALREADY_STARTED")
if req.get("generation") != generation or req.get("expected_frontier") != frontier:
    raise RuntimeError("REQUEST_BINDING_MISMATCH")

before_capabilities = copy.deepcopy(head.get("active_capabilities", []))
previous_head_digest = head["canonical_head_digest"]
previous_registry_digest = reg.get("registry_digest")
previous_registry_branches = {x.get("branch") for x in reg.get("branches", [])}

run_git("fetch", "--all", "--prune")
remote_lines = run_git("ls-remote", "--heads", "origin").stdout.splitlines()
remote = {}
for line in remote_lines:
    parts = line.split()
    if len(parts) == 2 and parts[1].startswith("refs/heads/"):
        remote[parts[1].removeprefix("refs/heads/")] = parts[0]

if ACTIVE not in remote:
    raise RuntimeError("ACTIVE_BRANCH_MISSING_FROM_REMOTE")

expected_remote_count = int(req.get("expected_remote_branch_count", 0))
if expected_remote_count and len(remote) != expected_remote_count:
    raise RuntimeError("UNEXPECTED_REMOTE_BRANCH_COUNT:" + json.dumps({"expected": expected_remote_count, "actual": len(remote)}))

missing = sorted(set(remote) - previous_registry_branches)
registry_only = sorted(previous_registry_branches - set(remote))
expected_missing = sorted(req.get("expected_missing_branches", []))
if registry_only:
    raise RuntimeError("REGISTRY_ONLY_BRANCHES:" + json.dumps(registry_only))
if missing != expected_missing:
    raise RuntimeError("UNEXPECTED_MISSING_BRANCH_SET:" + json.dumps({"expected": expected_missing, "actual": missing}))

trigger_sha = str(os.getenv("GITHUB_SHA") or run_git("rev-parse", "HEAD").stdout.strip())
ancestry = {}
for name, sha in sorted(remote.items()):
    if name == ACTIVE:
        continue
    p = run_git("merge-base", "--is-ancestor", sha, trigger_sha, check=False)
    ancestry[name] = p.returncode == 0
if not all(ancestry.values()):
    raise RuntimeError("NON_ACTIVE_TIP_OUTSIDE_ACTIVE_ANCESTRY:" + json.dumps(sorted(k for k, v in ancestry.items() if not v)))

for name in missing:
    reg.setdefault("branches", []).append({
        "branch": name,
        "head_sha": remote[name],
        "branch_tip_at_closure": remote[name],
        "mode": "EXPERIENCE_ONLY",
        "role": "POST_CLOSURE_HISTORY_SOURCE",
        "tags": ["history", "post_closure", "branch_registry_sync"],
        "lessons": [],
        "evidence": [],
        "history_only": True,
        "runtime_active": False,
        "legacy_auto_execution": False,
        "reuse_requires_fresh_admission": True,
        "closed_into_generation": generation,
        "closure_target": "YADO_UNIFIED_CONTEXT_KERNEL_V1",
        "physical_ref_ancestry_contained": True,
        "lesson_provenance": {
            "source_class": "UNSUMMARIZED_GIT_HISTORY",
            "allowed_use": "RAW_HISTORY_RETRIEVAL_ONLY",
            "semantic_validation_by_rederivation": False,
        },
    })

for entry in reg.get("branches", []):
    name = entry["branch"]
    if name == ACTIVE:
        entry["mode"] = "ACTIVE_LINEAGE"
        entry["runtime_active"] = True
        entry["history_only"] = False
        entry["generation"] = generation
        entry["head_sha"] = trigger_sha
        entry["head_sha_semantics"] = "REGISTRY_RECONCILIATION_INPUT_CHECKPOINT_NOT_SELF_REFERENTIAL_LIVE_TIP"
        entry.pop("closed_into_generation", None)
        entry.pop("closure_target", None)
        entry.pop("branch_tip_at_closure", None)
    else:
        entry["mode"] = "EXPERIENCE_ONLY"
        entry["runtime_active"] = False
        entry["history_only"] = True
        entry["head_sha"] = remote[name]
        entry["branch_tip_at_closure"] = remote[name]
        entry["closed_into_generation"] = generation
        entry["closure_target"] = "YADO_UNIFIED_CONTEXT_KERNEL_V1"
        entry["legacy_auto_execution"] = False
        entry["reuse_requires_fresh_admission"] = True
        entry["physical_ref_ancestry_contained"] = ancestry[name]

reg["branches"] = sorted(reg.get("branches", []), key=lambda x: (x.get("branch") != ACTIVE, x.get("branch", "")))
legacy = [x for x in reg["branches"] if x["branch"] != ACTIVE]
closure = reg.setdefault("closure", {})
closure.update({
    "schema": "yado.branch_history_closure.v2",
    "active_branch": ACTIVE,
    "active_generation": generation,
    "remote_branch_count": len(remote),
    "active_lineage_count": 1,
    "historical_branch_count": len(legacy),
    "all_remote_branches_registered": True,
    "all_non_active_branches_history_only": all(x.get("history_only") is True for x in legacy),
    "all_current_remote_tips_contained_in_active_ancestry": all(ancestry.values()),
    "current_remote_ancestry_containment": "VERIFIED",
    "physical_branches_preserved": True,
    "physical_merge_or_deletion_required": False,
    "post_closure_registry_reconciliation": "V2_DYNAMIC_REMOTE_INVENTORY",
    "semantic_rule": "NON_ACTIVE BRANCH TIPS ARE READ-ONLY HISTORY; NEWLY DISCOVERED POST-CLOSURE BRANCHES ENTER MEMORY WITHOUT CAPABILITY ADMISSION.",
})
if closure.get("physical_branch_closure_merge_commit"):
    closure["physical_ref_convergence_scope"] = "BASELINE_CLOSURE_COMMIT_PLUS_CURRENT_ANCESTRY_CONTAINMENT"

reg["activation_mode"] = "SINGLE_ACTIVE_G2_WITH_READ_ONLY_HISTORY"
reg.setdefault("policy", {}).update({
    "active_branch": ACTIVE,
    "single_active_lineage": True,
    "legacy_branches_are_runtime_inactive": True,
    "g3_genesis_blocked": True,
    "receipts_preferred_over_code_claims": True,
})
reg["registry_digest"] = content_digest(reg, "registry_digest")

core["experience_registry"] = "canonical/yado-unified-experience-registry-v1.json"
core["experience_registry_digest"] = reg["registry_digest"]
core["legacy_branch_count"] = len(legacy)
for plane in core.get("planes", []):
    if plane.get("plane_id") == "MEMORY_AND_EXPERIENCE":
        plane["historical_branch_count"] = len(legacy)
        plane["remote_branch_count"] = len(remote)
        plane["branch_closure_mode"] = "READ_ONLY_HISTORY_INTO_G2_DYNAMIC_INVENTORY_V2"
        plane["experience_components"] = ["canonical/yado-unified-experience-registry-v1.json"]
core["core_digest"] = content_digest(core, "core_digest")

bp = ctx.setdefault("branch_policy", {})
bp.update({
    "active_branch": ACTIVE,
    "active_lineage_count": 1,
    "historical_branch_count": len(legacy),
    "remote_branch_count": len(remote),
    "all_non_active_branches_closed_into_generation": generation,
    "non_active_branch_role": "MEMORY_HISTORY_ONLY",
    "all_historical_heads_preserved_in_g2_ancestry": True,
    "current_remote_ancestry_containment": "VERIFIED",
    "branch_registry_reconciliation": "V2_DYNAMIC_REMOTE_INVENTORY",
    "physical_branches_preserved": True,
    "physical_merge_or_deletion_required": False,
})
ctx["generation"] = generation

head["current_frontier"] = frontier
head["frontier_source"] = "architecture/evolution-ledger.json:open_deficits"
head.setdefault("unified_core", {})["experience_registry_digest"] = reg["registry_digest"]
head["unified_core"]["legacy_branch_count"] = len(legacy)
head["unified_core"]["core_digest"] = core["core_digest"]
bh = head.setdefault("branch_history_closure", {})
bh.update({
    "active_branch": ACTIVE,
    "historical_branch_count": len(legacy),
    "remote_branch_count": len(remote),
    "closed_into_generation": generation,
    "all_current_remote_tips_contained_in_active_ancestry": True,
    "registry_reconciliation": "V2_DYNAMIC_REMOTE_INVENTORY",
})
head["canonical_head_digest"] = content_digest(head, "canonical_head_digest")

evidence_digest = h({
    "generation": generation,
    "frontier": frontier,
    "previous_head_digest": previous_head_digest,
    "new_head_digest": head["canonical_head_digest"],
    "previous_registry_digest": previous_registry_digest,
    "new_registry_digest": reg["registry_digest"],
    "added_branches": missing,
    "historical_branch_tips": {x["branch"]: x["head_sha"] for x in legacy},
    "ancestry": ancestry,
})

ledger["current_head_digest"] = head["canonical_head_digest"]
run_id = str(os.getenv("GITHUB_RUN_ID") or "LOCAL")
event = {
    "index": len(ledger["events"]),
    "event_id": f"E{len(ledger['events']) + 1:04d}_G2_BRANCH_INVENTORY_REGISTRY_RECONCILIATION_V2",
    "event_type": "G2_MEMORY_AND_EXPERIENCE_BRANCH_REGISTRY_RECONCILIATION",
    "status": "PASS",
    "generation": generation,
    "deficit": "REMOTE_BRANCH_INVENTORY_MATCH",
    "effect": f"REGISTERED_REMOTE_BRANCHES={len(remote)}; HISTORICAL={len(legacy)}; ADDED={len(missing)}; FRONTIER_UNCHANGED={frontier}",
    "source_path": f"receipts/yado-g2-branch-inventory-registry-reconciliation-v2-run-{run_id}.json",
    "source_digest": evidence_digest,
    "run_id": run_id,
    "parent_event_hash": ledger["tail_event_hash"],
    "canonical_mutation": True,
    "promotion_applied": False,
    "generation_transition": False,
    "previous_head_digest": previous_head_digest,
    "new_head_digest": head["canonical_head_digest"],
}
event["event_hash"] = event_hash(event)
ledger["events"].append(event)
ledger["event_count"] = len(ledger["events"])
ledger["tail_event_hash"] = event["event_hash"]
ledger["ledger_digest"] = h({k: v for k, v in ledger.items() if k != "ledger_digest"})
validate_ledger_v2(ledger)

write(REG, reg)
write(CORE, core)
write(CTX, ctx)
write(HEAD, head)
write(LEDGER, ledger)

guard = subprocess.run([sys.executable, str(GUARD)], cwd=REPO, capture_output=True, text=True, timeout=120)
if guard.returncode != 0:
    raise RuntimeError("POST_RECONCILIATION_CANONICAL_GUARD_FAILED:" + guard.stdout[-3000:] + guard.stderr[-1000:])
guard_payload = json.loads(guard.stdout)

checks = {
    "remote_registry_exact_match": set(remote) == {x["branch"] for x in reg["branches"]},
    "expected_missing_branches_added": set(missing).issubset({x["branch"] for x in reg["branches"]}),
    "one_active_lineage": sum(x.get("mode") == "ACTIVE_LINEAGE" for x in reg["branches"]) == 1,
    "dynamic_historical_count": len(legacy) == len(remote) - 1,
    "all_history_runtime_inactive": all(x.get("runtime_active") is False and x.get("history_only") is True for x in legacy),
    "all_non_active_tips_in_active_ancestry": all(ancestry.values()),
    "frontier_unchanged": head["current_frontier"] == core["current_frontier"] == frontier,
    "head_ledger_digest_equal": head["canonical_head_digest"] == ledger["current_head_digest"],
    "active_capabilities_unchanged": head.get("active_capabilities", []) == before_capabilities,
    "g3_not_started": head.get("g3_genesis_performed") is False,
    "canonical_guard": guard_payload.get("status") == "PASS_CANONICAL_INVARIANT_GUARD_V1",
}
if not all(checks.values()):
    raise RuntimeError("RECONCILIATION_CHECK_FAILED:" + json.dumps(checks, sort_keys=True))

receipt = {
    "schema": "yado.g2.branch_inventory_registry_reconciliation.receipt.v2",
    "status": "PASS_G2_BRANCH_INVENTORY_REGISTRY_RECONCILIATION_V2",
    "generation": generation,
    "frontier": frontier,
    "active_branch": ACTIVE,
    "remote_branch_count": len(remote),
    "historical_branch_count": len(legacy),
    "added_branch_count": len(missing),
    "added_branches": missing,
    "previous_registry_digest": previous_registry_digest,
    "new_registry_digest": reg["registry_digest"],
    "previous_head_digest": previous_head_digest,
    "new_head_digest": head["canonical_head_digest"],
    "evidence_digest": evidence_digest,
    "checks": checks,
    "canonical_mutation": True,
    "capability_mutation": False,
    "promotion_applied": False,
    "generation_transition": False,
    "g3_genesis_performed": False,
    "semantic_boundary": "CANONICAL MEMORY/PROVENANCE METADATA RECONCILIATION ONLY. NEW BRANCHES ARE REGISTERED AS READ-ONLY HISTORY WITHOUT SEMANTIC LESSON CLAIMS OR CAPABILITY ADMISSION.",
}
receipt["receipt_sha256"] = h(receipt)
write(OUT, receipt)
print(json.dumps(receipt, indent=2, sort_keys=True))
