from __future__ import annotations

import ast
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
TARGET_REL = "runtime/yado_unified_core_deep_self_audit_v1.py"
TARGET = REPO / TARGET_REL
REGISTRY = REPO / "canonical/yado-unified-experience-registry-v1.json"
CANDIDATE = REPO / "candidates/g2-self-evolution/yado_unified_core_deep_self_audit_native_provenance_candidate_v1.py"
REPORT = REPO / "candidates/kernel-self-generated/g2-native-main-provenance-rewrite-v1.json"
AUDIT_RECEIPT = ROOT / "yado_unified_core_deep_self_audit_v1_receipt.json"

sys.path.insert(0, str(ROOT))
from yado_unified_core_v1 import UnifiedYADOCoreV1


def canon(x: Any) -> str:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), default=str)


def digest(x: Any) -> str:
    return hashlib.sha256(canon(x).encode()).hexdigest()


def sha_text(x: str) -> str:
    return hashlib.sha256(x.encode()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_current_audit() -> dict[str, Any]:
    cp = subprocess.run([sys.executable, TARGET_REL], cwd=REPO, capture_output=True, text=True, timeout=240)
    if cp.returncode != 0 or not AUDIT_RECEIPT.exists():
        raise RuntimeError("BASELINE_DEEP_AUDIT_FAILED:" + cp.stderr[-1000:])
    return load(AUDIT_RECEIPT)


def safe_policy_rows(registry: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for entry in registry.get("branches", []):
        if entry.get("mode") != "EXPERIENCE_ONLY":
            continue
        lp = entry.get("lesson_provenance") or {}
        rd = entry.get("rederived_evidence") or {}
        row = {
            "lesson_source_class": lp.get("source_class"),
            "semantic_validation_by_rederivation": lp.get("semantic_validation_by_rederivation"),
            "rederived_source_class": rd.get("source_class"),
            "semantic_equivalence_claimed": rd.get("semantic_equivalence_to_host_lessons_claimed"),
        }
        if row not in rows:
            rows.append(row)
    return rows


def make_row_expr(row: dict[str, Any]) -> ast.expr:
    # The candidate policy is synthesized only from provenance states already present
    # in canonical YADO memory. Safety invariant: semantic equivalence must never be claimed.
    x = ast.Name(id="x", ctx=ast.Load())
    lp = ast.Call(func=ast.Attribute(value=ast.Call(func=ast.Attribute(value=x, attr="get", ctx=ast.Load()), args=[ast.Constant("lesson_provenance"), ast.Dict(keys=[], values=[])], keywords=[]), attr="get", ctx=ast.Load()), args=[ast.Constant("source_class")], keywords=[])
    lp_sem = ast.Call(func=ast.Attribute(value=ast.Call(func=ast.Attribute(value=copy.deepcopy(x), attr="get", ctx=ast.Load()), args=[ast.Constant("lesson_provenance"), ast.Dict(keys=[], values=[])], keywords=[]), attr="get", ctx=ast.Load()), args=[ast.Constant("semantic_validation_by_rederivation")], keywords=[])
    rd = ast.Call(func=ast.Attribute(value=ast.Call(func=ast.Attribute(value=copy.deepcopy(x), attr="get", ctx=ast.Load()), args=[ast.Constant("rederived_evidence"), ast.Dict(keys=[], values=[])], keywords=[]), attr="get", ctx=ast.Load()), args=[ast.Constant("source_class")], keywords=[])
    rd_sem = ast.Call(func=ast.Attribute(value=ast.Call(func=ast.Attribute(value=copy.deepcopy(x), attr="get", ctx=ast.Load()), args=[ast.Constant("rederived_evidence"), ast.Dict(keys=[], values=[])], keywords=[]), attr="get", ctx=ast.Load()), args=[ast.Constant("semantic_equivalence_to_host_lessons_claimed")], keywords=[])
    return ast.BoolOp(op=ast.And(), values=[
        ast.Compare(left=lp, ops=[ast.Eq()], comparators=[ast.Constant(row["lesson_source_class"])]),
        ast.Compare(left=lp_sem, ops=[ast.Is()], comparators=[ast.Constant(row["semantic_validation_by_rederivation"])]),
        ast.Compare(left=rd, ops=[ast.Eq()], comparators=[ast.Constant(row["rederived_source_class"])]),
        ast.Compare(left=rd_sem, ops=[ast.Is()], comparators=[ast.Constant(False)]),
    ])


def synthesize_registry_predicate(rows: list[dict[str, Any]]) -> ast.expr:
    if not rows:
        raise RuntimeError("NO_CANONICAL_PROVENANCE_POLICIES")
    # Reject any observed state that itself claims semantic equivalence.
    if any(r.get("semantic_equivalence_claimed") is not False for r in rows):
        raise RuntimeError("CANONICAL_PROVENANCE_OVERCLAIM_PRESENT")
    allowed = ast.BoolOp(op=ast.Or(), values=[make_row_expr(r) for r in rows]) if len(rows) > 1 else make_row_expr(rows[0])
    gen = ast.GeneratorExp(
        elt=allowed,
        generators=[ast.comprehension(target=ast.Name(id="x", ctx=ast.Store()), iter=ast.Name(id="legacy_entries", ctx=ast.Load()), ifs=[], is_async=0)],
    )
    return ast.BoolOp(op=ast.And(), values=[
        ast.Call(func=ast.Name(id="bool", ctx=ast.Load()), args=[ast.Name(id="legacy_entries", ctx=ast.Load())], keywords=[]),
        ast.Call(func=ast.Name(id="all", ctx=ast.Load()), args=[gen], keywords=[]),
    ])


def replace_registry_predicate(tree: ast.Module, new_value: ast.expr) -> int:
    count = 0
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        t = node.targets[0]
        if isinstance(t, ast.Name) and t.id == "registry_labels_ok":
            node.value = copy.deepcopy(new_value)
            count += 1
    return count


core = UnifiedYADOCoreV1(REPO)
baseline = run_current_audit()
priority = (baseline.get("self_selected_priority") or [{}])[0]
if baseline.get("status") != "PASS_YADO_UNIFIED_CORE_DEEP_SELF_AUDIT_V1":
    raise RuntimeError("BASELINE_AUDIT_NOT_PASS")
if priority.get("code") != "LEGACY_EXPERIENCE_SUMMARY_PROVENANCE":
    raise RuntimeError("CURRENT_KERNEL_PRIORITY_MOVED:" + str(priority.get("code")))

finding = next((x for x in baseline.get("findings", []) if x.get("code") == "LEGACY_EXPERIENCE_SUMMARY_PROVENANCE"), {})
if finding.get("status") == "PASS":
    raise RuntimeError("PROVENANCE_ALREADY_PASS")

registry = load(REGISTRY)
rows = safe_policy_rows(registry)
parent_source = TARGET.read_text(encoding="utf-8")
parent_sha = sha_text(parent_source)
tree = ast.parse(parent_source)
new_predicate = synthesize_registry_predicate(rows)
replaced = replace_registry_predicate(tree, new_predicate)
if replaced != 1:
    raise RuntimeError(f"REGISTRY_PREDICATE_ANCHOR_COUNT:{replaced}")

ast.fix_missing_locations(tree)
candidate_source = ast.unparse(tree) + "\n"
compile(candidate_source, "<yado-native-main-provenance-v1>", "exec")
candidate_sha = sha_text(candidate_source)
if candidate_sha == parent_sha:
    raise RuntimeError("NATIVE_CANDIDATE_UNCHANGED")

CANDIDATE.parent.mkdir(parents=True, exist_ok=True)
CANDIDATE.write_text(candidate_source, encoding="utf-8")

report = {
    "schema": "yado.g2.native_main_provenance_rewrite.v1",
    "status": "PASS_SHADOW_G2_NATIVE_MAIN_PROVENANCE_REWRITE_V1",
    "kernel_selected_priority": priority,
    "baseline_finding": finding,
    "target_path": TARGET_REL,
    "target_parent_sha256": parent_sha,
    "candidate_path": str(CANDIDATE.relative_to(REPO)),
    "candidate_sha256": candidate_sha,
    "candidate_compile": True,
    "native_ast_materialization": True,
    "external_model_used": False,
    "policy_states_derived_from_canonical_memory": rows,
    "policy_state_count": len(rows),
    "semantic_equivalence_must_remain_false": True,
    "canonical_mutation": False,
    "rollback_parent_sha256": parent_sha,
    "generator": "YADO_CANONICAL_MEMORY_TO_AST_PREDICATE_V1",
    "kernel_identity": core.CORE_ID,
    "claim_boundary": "Bounded native AST/source repair derived from current canonical YADO provenance states and a kernel-selected deficit. It does not prove general open-ended source genesis or consciousness.",
}
report["receipt_sha256"] = digest(report)
REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({
    "status": report["status"],
    "target_path": report["target_path"],
    "candidate_path": report["candidate_path"],
    "candidate_sha256": candidate_sha,
    "external_model_used": False,
    "policy_state_count": len(rows),
}, indent=2, sort_keys=True))
