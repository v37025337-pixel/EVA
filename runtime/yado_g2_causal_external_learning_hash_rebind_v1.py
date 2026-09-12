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
LEDGER = REPO / "architecture/evolution-ledger.json"
BINDING = REPO / "canonical/yado-g2-causal-external-learning-binding-v1.json"
UNIFIED_RUNTIME = ROOT / "yado_unified_core_v1.py"
BINDING_RUNTIME = ROOT / "yado_g2_causal_external_learning_binding_v1.py"
GUARD = ROOT / "yado_canonical_invariant_guard_v1.py"
COMPONENT = "RUNTIME-G2-CAUSAL-EXTERNAL-LEARNING-BINDING-V1"
BINDING_SOURCE = "runtime/yado_g2_causal_external_learning_binding_v1.py"


def canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def h(obj):
    return hashlib.sha256(canon(obj).encode()).hexdigest()


def fsha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, obj):
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def content_digest(obj, field):
    x = copy.deepcopy(obj)
    x.pop(field, None)
    return h(x)


head, core, ledger, binding = map(load, [HEAD, CORE, LEDGER, BINDING])
validate_ledger_v2(ledger)

if head.get("generation_id") != "G2_CANDIDATE_TRCG_V1" or ledger.get("current_head") != head.get("generation_id"):
    raise RuntimeError("GENERATION_BINDING_MISMATCH")
if head.get("g3_genesis_performed") is not False or binding.get("g3_genesis_performed") is not False:
    raise RuntimeError("G3_MUST_REMAIN_FALSE")
if head.get("canonical_head_digest") != ledger.get("current_head_digest"):
    raise RuntimeError("PRE_REBIND_HEAD_LEDGER_SPLIT_BRAIN")
if len(ledger.get("open_deficits", [])) != 1:
    raise RuntimeError("EXPECTED_SINGLE_FRONTIER")
frontier = ledger["open_deficits"][0]
if head.get("current_frontier") != frontier or core.get("current_frontier") != frontier:
    raise RuntimeError("FRONTIER_MISMATCH")
if binding.get("status") != "CANONICAL_ACTIVE" or binding.get("component_id") != COMPONENT:
    raise RuntimeError("BINDING_ARTIFACT_NOT_ACTIVE")

previous_head_digest = head["canonical_head_digest"]
previous_core_digest = core.get("core_digest")
previous_runtime_sha = core.get("runtime_sha256")
new_unified_sha = fsha(UNIFIED_RUNTIME)
binding_sha = fsha(BINDING_RUNTIME)

sources = list(core.get("active_runtime_sources", []))
if BINDING_SOURCE not in sources:
    sources.append(BINDING_SOURCE)
core["active_runtime_sources"] = sorted(set(sources))

bound_planes = []
for plane in core.get("planes", []):
    if plane.get("plane_id") in {"MEMORY_AND_EXPERIENCE", "RESOURCE_AND_EVIDENCE"}:
        active = list(plane.get("active_components", []))
        if COMPONENT not in active:
            active.append(COMPONENT)
        plane["active_components"] = sorted(set(active))
        responsibilities = list(plane.get("responsibilities", []))
        if plane.get("plane_id") == "MEMORY_AND_EXPERIENCE":
            for item in ("causal_external_result_to_episodic_memory", "restart_restored_external_learning_memory"):
                if item not in responsibilities:
                    responsibilities.append(item)
        else:
            for item in ("tri_organ_authorized_readonly_external_learning", "verified_external_result_feedback"):
                if item not in responsibilities:
                    responsibilities.append(item)
        plane["responsibilities"] = sorted(set(responsibilities))
        bound_planes.append(plane.get("plane_id"))

manifest_active = sorted({
    str(x)
    for plane in core.get("planes", [])
    for x in plane.get("active_components", [])
    if isinstance(x, str) and "/" not in x and not x.endswith(".json")
})
head["active_capabilities"] = manifest_active

rim = core.setdefault("runtime_integrity_manifest", {})
actual_sources = {}
for rel in core["active_runtime_sources"]:
    path = REPO / rel
    if not path.exists():
        raise RuntimeError("ACTIVE_RUNTIME_SOURCE_MISSING:" + rel)
    actual_sources[rel] = fsha(path)
rim["sources"] = actual_sources
rim["manifest_digest"] = h(actual_sources)

core["runtime_sha256"] = new_unified_sha
core.setdefault("causal_external_learning_binding_v1", {}).update({
    "artifact": "canonical/yado-g2-causal-external-learning-binding-v1.json",
    "component_id": COMPONENT,
    "runtime_source": BINDING_SOURCE,
    "runtime_sha256": binding_sha,
    "status": "CANONICAL_ACTIVE",
    "bound_planes": bound_planes,
    "read_only_external": True,
    "durable_restart_memory": True,
    "automatic_canonical_promotion": False,
    "g3_genesis_performed": False,
})
core["core_digest"] = content_digest(core, "core_digest")

uc = head.setdefault("unified_core", {})
uc["runtime_sha256"] = new_unified_sha
uc["runtime_integrity_manifest_digest"] = rim["manifest_digest"]
uc["core_digest"] = core["core_digest"]
uc["causal_external_learning_binding"] = {
    "component_id": COMPONENT,
    "runtime_sha256": binding_sha,
    "status": "CANONICAL_ACTIVE",
    "read_only_external": True,
    "durable_restart_memory": True,
    "g3_genesis_performed": False,
}
head["canonical_head_digest"] = content_digest(head, "canonical_head_digest")

ledger["current_head_digest"] = head["canonical_head_digest"]
run_id = str(os.getenv("GITHUB_RUN_ID") or "LOCAL")
source_digest = h(binding)
event = {
    "index": len(ledger["events"]),
    "event_id": f"E{len(ledger['events']) + 1:04d}_G2_CAUSAL_EXTERNAL_LEARNING_HASH_REBIND_V1",
    "event_type": "G2_CANONICAL_RUNTIME_HASH_REBIND",
    "status": "PASS",
    "generation": head["generation_id"],
    "deficit": "UNIFIED_RUNTIME_HASH_BINDING",
    "effect": f"UNIFIED_RUNTIME_REBOUND={new_unified_sha}; BINDING_ACTIVE={COMPONENT}; FRONTIER_UNCHANGED={frontier}",
    "source_path": "canonical/yado-g2-causal-external-learning-binding-v1.json",
    "source_digest": source_digest,
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

write(CORE, core)
write(HEAD, head)
write(LEDGER, ledger)

guard = subprocess.run([sys.executable, str(GUARD)], cwd=REPO, capture_output=True, text=True, timeout=180)
if guard.returncode != 0:
    raise RuntimeError("POST_REBIND_CANONICAL_GUARD_FAILED:" + guard.stdout[-6000:] + guard.stderr[-2000:])
guard_payload = json.loads(guard.stdout)
if guard_payload.get("status") != "PASS_CANONICAL_INVARIANT_GUARD_V1":
    raise RuntimeError("POST_REBIND_GUARD_WITHHOLD")

checks = {
    "runtime_sha_rebound": core["runtime_sha256"] == new_unified_sha == head["unified_core"]["runtime_sha256"],
    "binding_source_active": BINDING_SOURCE in core["active_runtime_sources"],
    "binding_hash_manifest_bound": rim["sources"].get(BINDING_SOURCE) == binding_sha,
    "binding_component_explicit": COMPONENT in head["active_capabilities"],
    "binding_planes_bound": set(bound_planes) == {"MEMORY_AND_EXPERIENCE", "RESOURCE_AND_EVIDENCE"},
    "head_ledger_bound": head["canonical_head_digest"] == ledger["current_head_digest"],
    "frontier_preserved": frontier == core.get("current_frontier") == head.get("current_frontier"),
    "g3_not_started": head.get("g3_genesis_performed") is False,
    "guard_pass": guard_payload.get("status") == "PASS_CANONICAL_INVARIANT_GUARD_V1",
}
if not all(checks.values()):
    raise RuntimeError("CAUSAL_BINDING_REBIND_CHECK_FAILED:" + json.dumps(checks, sort_keys=True))

print(json.dumps({
    "status": "PASS_G2_CAUSAL_EXTERNAL_LEARNING_HASH_REBIND_V1",
    "previous_runtime_sha256": previous_runtime_sha,
    "new_runtime_sha256": new_unified_sha,
    "binding_runtime_sha256": binding_sha,
    "previous_core_digest": previous_core_digest,
    "new_core_digest": core["core_digest"],
    "previous_head_digest": previous_head_digest,
    "new_head_digest": head["canonical_head_digest"],
    "active_runtime_source_count": len(core["active_runtime_sources"]),
    "active_capability_count": len(head["active_capabilities"]),
    "ledger_event_count": ledger["event_count"],
    "frontier": frontier,
    "checks": checks,
}, indent=2, sort_keys=True))
