from __future__ import annotations

import ast
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
TARGET_REL = "runtime/yado_g2_openapi_readonly_executor_v1.py"
TARGET = REPO / TARGET_REL
PRIOR = REPO / "candidates/network/yado-network-self-directed-repair-v2.json"
CANDIDATE = REPO / "candidates/network/yado_g2_openapi_readonly_executor_content_type_candidate_v1.py"
REPORT = REPO / "candidates/network/yado-readonly-executor-content-type-policy-evolution-v1.json"


def canon(x: Any) -> str:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), default=str)


def digest(x: Any) -> str:
    return hashlib.sha256(canon(x).encode()).hexdigest()


def sha_text(x: str) -> str:
    return hashlib.sha256(x.encode()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


class ContentTypePolicyRepair(ast.NodeTransformer):
    def __init__(self, media_type: str):
        self.media_type = media_type
        self.replacements = 0

    def visit_Compare(self, node: ast.Compare):
        self.generic_visit(node)
        # Anchor exactly on: ctype not in {json types...}
        if not (isinstance(node.left, ast.Name) and node.left.id == "ctype"):
            return node
        if len(node.ops) != 1 or not isinstance(node.ops[0], ast.NotIn):
            return node
        if len(node.comparators) != 1 or not isinstance(node.comparators[0], ast.Set):
            return node
        vals = node.comparators[0].elts
        strings = [x.value for x in vals if isinstance(x, ast.Constant) and isinstance(x.value, str)]
        required = {"application/json", "text/plain", "application/problem+json"}
        if not required.issubset(set(strings)):
            return node
        if self.media_type not in strings:
            vals.append(ast.Constant(self.media_type))
            self.replacements += 1
        return node


prior = load(PRIOR)
if prior.get("status") != "WITHHOLD_EXPLICIT_NETWORK_CAPABILITY_DEFICIT_V2":
    raise RuntimeError("PRIOR_DEFICIT_NOT_ACTIVE")
if prior.get("diagnosis") != "LOCAL_EXECUTOR_POLICY_BLOCKS_VALID_DNS_MEDIA_TYPE":
    raise RuntimeError("PRIOR_DIAGNOSIS_MOVED")
if prior.get("next_required_capability") != "READONLY_EXECUTOR_CONTENT_TYPE_POLICY_EVOLUTION_V1":
    raise RuntimeError("PRIOR_NEXT_CAPABILITY_MOVED")

# The required media type is derived from actual observed failure evidence, not supplied as a target patch.
errors = [str(x.get("error", "")) for x in prior.get("observations", [])]
observed = sorted({e.split("CONTENT_TYPE_REJECTED:",1)[1] for e in errors if "CONTENT_TYPE_REJECTED:" in e})
if observed != ["application/dns-json"]:
    raise RuntimeError("UNEXPECTED_OR_AMBIGUOUS_MEDIA_TYPE_EVIDENCE:" + repr(observed))
media_type = observed[0]

parent_source = TARGET.read_text(encoding="utf-8")
parent_sha = sha_text(parent_source)
tree = ast.parse(parent_source)
repair = ContentTypePolicyRepair(media_type)
tree = repair.visit(tree)
if repair.replacements != 1:
    raise RuntimeError(f"CONTENT_TYPE_POLICY_ANCHOR_COUNT:{repair.replacements}")
ast.fix_missing_locations(tree)
candidate_source = ast.unparse(tree) + "\n"
compile(candidate_source, "<yado-readonly-executor-content-type-policy-v1>", "exec")
candidate_sha = sha_text(candidate_source)
if candidate_sha == parent_sha:
    raise RuntimeError("CANDIDATE_UNCHANGED")

# Static safety invariants: the candidate may only expand response media parsing; all network guards remain.
for invariant in [
    "FORBIDDEN_HEADERS",
    "ALLOWED_METHODS={'GET','HEAD'}",
    "HTTPS_REQUIRED",
    "NON_PUBLIC_ADDRESS_REJECTED",
    "NONSTANDARD_PORT_REJECTED",
    "REDIRECT_REJECTED",
    "CREDENTIAL_HEADER_REJECTED",
    "RESPONSE_TOO_LARGE",
]:
    compact = candidate_source.replace(" ", "") if " " not in invariant else candidate_source
    if invariant == "ALLOWED_METHODS={'GET','HEAD'}":
        if "ALLOWED_METHODS = {'GET', 'HEAD'}" not in candidate_source and "ALLOWED_METHODS={'GET','HEAD'}" not in candidate_source.replace(" ", ""):
            raise RuntimeError("SAFETY_INVARIANT_LOST:ALLOWED_METHODS")
    elif invariant not in candidate_source:
        raise RuntimeError("SAFETY_INVARIANT_LOST:" + invariant)

CANDIDATE.parent.mkdir(parents=True, exist_ok=True)
CANDIDATE.write_text(candidate_source, encoding="utf-8")
report = {
    "schema": "yado.readonly_executor_content_type_policy_evolution.v1",
    "status": "PASS_SHADOW_NATIVE_POLICY_REPAIR_CANDIDATE_V1",
    "source_deficit_status": prior.get("status"),
    "source_goal_id": prior.get("goal_id"),
    "source_diagnosis": prior.get("diagnosis"),
    "derived_media_type": media_type,
    "target_path": TARGET_REL,
    "target_parent_sha256": parent_sha,
    "candidate_path": str(CANDIDATE.relative_to(REPO)),
    "candidate_sha256": candidate_sha,
    "candidate_compile": True,
    "native_ast_materialization": True,
    "external_model_used": False,
    "canonical_mutation": False,
    "safety_guards_preserved": True,
    "rollback_parent_sha256": parent_sha,
    "claim_boundary": "Bounded AST repair driven by YADO's observed network deficit. It expands only an observed response media type and does not authorize credentials, redirects, writes, private-network access, account creation, or deployment.",
}
report["receipt_sha256"] = digest(report)
REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({
    "status": report["status"],
    "derived_media_type": media_type,
    "candidate_sha256": candidate_sha,
    "external_model_used": False,
    "canonical_mutation": False,
}, indent=2, sort_keys=True))
