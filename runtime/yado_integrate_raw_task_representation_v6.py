from __future__ import annotations

from pathlib import Path
import copy
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
HEAD_P = ROOT / "canonical/yado-main-head-g2.json"
CORE_P = ROOT / "canonical/yado-unified-core-v1.json"
PROV_P = ROOT / "canonical/yado-algorithm-provenance-registry-v1.json"
LEDGER_P = ROOT / "architecture/evolution-ledger.json"
UNIFIED_P = ROOT / "runtime/yado_unified_core_v1.py"
V6_P = ROOT / "runtime/yado_raw_task_representation_canonical_v6.py"
RESIDUAL_P = ROOT / "runtime/yado_raw_task_representation_residual_repair_v3.py"
ARTIFACT_P = ROOT / "canonical/yado-raw-task-representation-v6.json"
RECEIPT_P = ROOT / "receipts/yado-g2-raw-representation-v6-integration-v1.json"

OLD_ID = "ALG-G2-RAW-TASK-REPRESENTATION-V4"
NEW_ID = "ALG-G2-RAW-TASK-REPRESENTATION-V6"
EXPECTED_FRONTIER = "KERNEL_G2_RAW_REPRESENTATION_V4_ROBUSTNESS_SELF_EVOLUTION_V2"
NEXT_FRONTIER = "KERNEL_G2_RAW_REPRESENTATION_V6_POST_ADMISSION_AUDIT_V1"
POLICY = "CLEAN_PLURALITY_TIE_CORE"
SELECTION_RECEIPT = "ab16a2e21bc2df656db0ba88f129fff239264b1971f869c32cd05482cab58320"
DEEP_RECEIPT = "3e5e78136072be7f93c194a12a569da762adfbe161b4be7bf1f25091c23c643b"
ADMISSION_RUN = "34715604111"


def canon(o):
    return json.dumps(o, sort_keys=True, separators=(",", ":"), default=str)


def digest(o):
    return hashlib.sha256(canon(o).encode()).hexdigest()


def cdig(o, field):
    x = copy.deepcopy(o)
    x.pop(field, None)
    return digest(x)


def fsha(p: Path):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def write(p: Path, o):
    p.write_text(json.dumps(o, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def event_hash(e):
    x = copy.deepcopy(e)
    x.pop("event_hash", None)
    return digest(x)


head = load(HEAD_P)
core = load(CORE_P)
prov = load(PROV_P)
ledger = load(LEDGER_P)
old_head_digest = head["canonical_head_digest"]

fronts = {
    head.get("current_frontier"),
    core.get("current_frontier"),
    prov.get("current_g2_binding", {}).get("frontier"),
    (ledger.get("open_deficits") or [None])[0],
}
assert fronts == {EXPECTED_FRONTIER}, fronts
assert head.get("generation_id") == ledger.get("current_head") == "G2_CANDIDATE_TRCG_V1"
assert head.get("g3_genesis_performed") is False
assert core.get("g3_genesis_performed") is False
assert core.get("raw_task_representation", {}).get("component_id") == OLD_ID
assert OLD_ID in head.get("active_capabilities", [])
assert V6_P.exists() and RESIDUAL_P.exists()

# Behavior binding: exact V4 consumer is replaced by the behavior-equivalent V6 wrapper.
src = UNIFIED_P.read_text(encoding="utf-8")
old_import = "from yado_raw_task_representation_robustness_v4 import RobustRawTaskRepresentationRuntimeV4"
new_import = "from yado_raw_task_representation_canonical_v6 import CanonicalRawTaskRepresentationRuntimeV6"
old_init = "self.raw_representation=RobustRawTaskRepresentationRuntimeV4(self._load('canonical/yado-raw-task-representation-v3.json'), self._load('canonical/yado-raw-task-representation-v4.json')['selected_mode'])"
new_init = "self.raw_representation=CanonicalRawTaskRepresentationRuntimeV6(self._load('canonical/yado-raw-task-representation-v3.json'))"
assert src.count(old_import) == 1, src.count(old_import)
assert src.count(old_init) == 1, src.count(old_init)
src = src.replace(old_import, new_import).replace(old_init, new_init)
UNIFIED_P.write_text(src, encoding="utf-8")
unified_sha = fsha(UNIFIED_P)

parent_digest = core["raw_task_representation"]["component_digest"]
v6_runtime_sha = fsha(V6_P)
residual_runtime_sha = fsha(RESIDUAL_P)

artifact = {
    "schema": "yado.g2.raw_task_representation.canonical.v6",
    "component_id": NEW_ID,
    "parent_component_id": OLD_ID,
    "parent_component_digest": parent_digest,
    "supersedes": OLD_ID,
    "selected_policy": POLICY,
    "selection_receipt_sha256": SELECTION_RECEIPT,
    "deep_admission_receipt_sha256": DEEP_RECEIPT,
    "admission_completion_run_id": ADMISSION_RUN,
    "admission_metrics": {
        "residual_all_experience_gain": 0.04166666666666674,
        "validation_gain": 0.04878048780487798,
        "post_selection_holdout_gain": 0.05208333333333337,
        "post_freeze_holdout_gain": 0.078125,
        "post_freeze_improved_family_count": 3,
        "full_regression_tests": 170,
        "full_regression_failures": 0,
    },
    "runtime_source": "runtime/yado_raw_task_representation_canonical_v6.py",
    "runtime_sha256": v6_runtime_sha,
    "residual_runtime_source": "runtime/yado_raw_task_representation_residual_repair_v3.py",
    "residual_runtime_sha256": residual_runtime_sha,
    "canonical_active": True,
    "automatic_promotion": False,
    "g3_genesis_performed": False,
    "semantic_boundary": "SAME-G2 RAW TASK REPRESENTATION REPLACEMENT; BEHAVIOR EQUIVALENT TO FROZEN CLEAN_PLURALITY_TIE_CORE CANDIDATE; V4 REMAINS ROLLBACK.",
}
artifact["component_digest"] = digest(artifact)
write(ARTIFACT_P, artifact)

# Provenance first; core binds its digest.
binding = prov.setdefault("current_g2_binding", {})
binding["frontier"] = NEXT_FRONTIER
binding["current_execution_label"] = "G2_RAW_TASK_REPRESENTATION_V6_RESIDUAL_REPAIR_CANONICAL"
binding["raw_representation_active_component"] = NEW_ID
binding["raw_v6_parent_component"] = OLD_ID
binding["raw_v6_selected_policy"] = POLICY
binding["raw_v6_selection_receipt_sha256"] = SELECTION_RECEIPT
binding["raw_v6_deep_admission_receipt_sha256"] = DEEP_RECEIPT
binding["raw_v6_admission_completion_run_id"] = ADMISSION_RUN
prov["registry_digest"] = cdig(prov, "registry_digest")
write(PROV_P, prov)
prov_digest = prov["registry_digest"]

# Replace V4 only where it is currently active; retain all historical metadata/files.
replace_count = 0
for plane in core.get("planes", []):
    xs = plane.get("active_components", [])
    if OLD_ID in xs:
        plane["active_components"] = [NEW_ID if x == OLD_ID else x for x in xs]
        replace_count += 1
assert replace_count >= 1, replace_count

core["current_frontier"] = NEXT_FRONTIER
core["algorithm_provenance_registry_digest"] = prov_digest
core["raw_task_representation"] = {
    "component_id": NEW_ID,
    "component_digest": artifact["component_digest"],
    "parent_component_id": OLD_ID,
    "parent_component_digest": parent_digest,
    "selected_policy": POLICY,
    "runtime_source": artifact["runtime_source"],
    "runtime_sha256": v6_runtime_sha,
    "residual_runtime_source": artifact["residual_runtime_source"],
    "residual_runtime_sha256": residual_runtime_sha,
    "selection_receipt_sha256": SELECTION_RECEIPT,
    "deep_admission_receipt_sha256": DEEP_RECEIPT,
    "admission_completion_run_id": ADMISSION_RUN,
    "status": "CANONICAL_ACTIVE",
    "supersedes": OLD_ID,
}
core["raw_task_representation_v6"] = copy.deepcopy(core["raw_task_representation"])

active_sources = list(core.get("active_runtime_sources", []))
for rel in (
    "runtime/yado_raw_task_representation_residual_repair_v3.py",
    "runtime/yado_raw_task_representation_canonical_v6.py",
):
    if rel not in active_sources:
        active_sources.append(rel)
core["active_runtime_sources"] = sorted(active_sources)
sources = {}
for rel in core["active_runtime_sources"]:
    p = ROOT / rel
    assert p.exists(), rel
    sources[rel] = fsha(p)
core["runtime_integrity_manifest"] = {
    "schema": core.get("runtime_integrity_manifest", {}).get("schema", "yado.runtime_integrity_manifest.v1"),
    "sources": sources,
    "manifest_digest": digest(sources),
}
core["runtime_sha256"] = unified_sha
core["core_digest"] = cdig(core, "core_digest")
write(CORE_P, core)

# Head mirrors the exact staged canonical state.
head["current_frontier"] = NEXT_FRONTIER
head.setdefault("algorithm_provenance_registry", {})["registry_digest"] = prov_digest
head["algorithm_provenance_registry"]["current_execution_label"] = binding["current_execution_label"]
active = sorted({
    str(x)
    for plane in core.get("planes", [])
    for x in plane.get("active_components", [])
    if isinstance(x, str) and "/" not in x and not x.endswith(".json")
})
head["active_capabilities"] = active
head["raw_task_representation_v6"] = {
    "component_id": NEW_ID,
    "component_digest": artifact["component_digest"],
    "parent_component_id": OLD_ID,
    "parent_component_digest": parent_digest,
    "selected_policy": POLICY,
    "runtime_sha256": v6_runtime_sha,
    "admission_metrics": copy.deepcopy(artifact["admission_metrics"]),
    "status": "CANONICAL_ACTIVE",
    "supersedes": OLD_ID,
}
uc = head.setdefault("unified_core", {})
uc["core_digest"] = core["core_digest"]
uc["algorithm_provenance_registry_digest"] = prov_digest
uc["runtime_sha256"] = unified_sha
uc["runtime_integrity_manifest_digest"] = core["runtime_integrity_manifest"]["manifest_digest"]
uc["raw_task_representation_component_digest"] = artifact["component_digest"]
uc["raw_task_representation_runtime_sha256"] = v6_runtime_sha
head["canonical_head_digest"] = cdig(head, "canonical_head_digest")
write(HEAD_P, head)

# Evidence receipt is bound into the append-only ledger event.
receipt = {
    "schema": "yado.g2.raw_task_representation_v6.integration.receipt.v1",
    "status": "STAGED_CANONICAL_INTEGRATION_REQUIRES_REAUDIT",
    "generation": "G2_CANDIDATE_TRCG_V1",
    "component_id": NEW_ID,
    "parent_component_id": OLD_ID,
    "selected_policy": POLICY,
    "selection_receipt_sha256": SELECTION_RECEIPT,
    "deep_admission_receipt_sha256": DEEP_RECEIPT,
    "admission_completion_run_id": ADMISSION_RUN,
    "component_digest": artifact["component_digest"],
    "unified_core_digest": core["core_digest"],
    "provenance_registry_digest": prov_digest,
    "new_head_digest": head["canonical_head_digest"],
    "previous_head_digest": old_head_digest,
    "runtime_sha256": unified_sha,
    "runtime_integrity_manifest_digest": core["runtime_integrity_manifest"]["manifest_digest"],
    "canonical_mutation_staged_on_shadow": True,
    "automatic_main_mutation": False,
    "g3_genesis_performed": False,
    "next_action": "RUN_INTEGRATED_NATIVE_DEEP_FULL_SUCCESSOR_170_ABLATION_REAUDIT_BEFORE_MAIN",
}
receipt["receipt_sha256"] = digest(receipt)
write(RECEIPT_P, receipt)

idx = len(ledger.get("events", []))
event_id = f"E{idx+1:04d}_G2_RAW_REPRESENTATION_V6_INTEGRATION_V1"
event = {
    "architecture_mutation": False,
    "canonical_mechanism_mutation": True,
    "canonical_mutation": True,
    "deficit": EXPECTED_FRONTIER,
    "effect": (
        "SELECTED=RAW_TASK_REPRESENTATION_V6; POLICY=CLEAN_PLURALITY_TIE_CORE; "
        "FROZEN_FRESH_DELTA=0.078125; IMPROVED_FAMILIES=3; PREINTEGRATION_REGRESSION=170/170; "
        "G3=False; NEXT=" + NEXT_FRONTIER
    ),
    "event_id": event_id,
    "event_type": "G2_RAW_TASK_REPRESENTATION_V6_STAGED_CANONICAL_INTEGRATION",
    "generation": "G2_CANDIDATE_TRCG_V1",
    "generation_transition": False,
    "index": idx,
    "new_head_digest": head["canonical_head_digest"],
    "parent_event_hash": ledger.get("tail_event_hash"),
    "previous_head_digest": old_head_digest,
    "promotion_applied": False,
    "run_id": ADMISSION_RUN,
    "source_digest": fsha(RECEIPT_P),
    "source_path": RECEIPT_P.relative_to(ROOT).as_posix(),
    "status": "STAGED_REQUIRES_REAUDIT",
}
event["event_hash"] = event_hash(event)
ledger.setdefault("events", []).append(event)
ledger["event_count"] = len(ledger["events"])
ledger["tail_event_hash"] = event["event_hash"]
ledger["current_head_digest"] = head["canonical_head_digest"]
ledger["open_deficits"] = [NEXT_FRONTIER]
if EXPECTED_FRONTIER not in ledger.setdefault("resolved_deficits", []):
    ledger["resolved_deficits"].append(EXPECTED_FRONTIER)
ledger["ledger_digest"] = cdig(ledger, "ledger_digest")
write(LEDGER_P, ledger)

print(json.dumps({
    "status": "STAGED_CANONICAL_INTEGRATION_REQUIRES_REAUDIT",
    "component_id": NEW_ID,
    "component_digest": artifact["component_digest"],
    "head_digest": head["canonical_head_digest"],
    "core_digest": core["core_digest"],
    "provenance_digest": prov_digest,
    "ledger_digest": ledger["ledger_digest"],
    "event_id": event_id,
    "next_frontier": NEXT_FRONTIER,
    "g3_genesis_performed": False,
}, indent=2, sort_keys=True))
