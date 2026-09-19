"""Verify the executing learner against the single canonical implementation."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEARNER = "runtime/yado_bounded_autonomous_learning_v1.py"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _load(root, name, field=None):
    value = json.loads((root / name).read_text(encoding="utf-8"))
    if field and value.get(field) != digest({k: v for k, v in value.items() if k != field}):
        raise ValueError("CANONICAL_CONTENT_DIGEST_MISMATCH:" + name)
    return value


def active_kernel_identity(root=ROOT):
    root = Path(root).resolve()
    core = _load(root, "canonical/yado-unified-core-v1.json", "core_digest")
    head = _load(root, "canonical/yado-main-head-g2.json", "canonical_head_digest")
    ledger = _load(root, "architecture/evolution-ledger.json", "ledger_digest")
    contract = _load(root, "architecture/yado-unified-architecture-v2.json")
    manifest = core["runtime_integrity_manifest"]
    expected = manifest["sources"].get(LEARNER)
    actual = hashlib.sha256((root / LEARNER).read_bytes()).hexdigest()
    checks = (
        expected == actual == contract["runtime_lineage"].get("active_sha256"),
        manifest["manifest_digest"] == digest(manifest["sources"]),
        head["unified_core"]["core_digest"] == core["core_digest"],
        head["unified_core"]["runtime_integrity_manifest_digest"] == manifest["manifest_digest"],
        head["canonical_head_digest"] == ledger["current_head_digest"],
        contract.get("implementation_id") == core.get("implementation_id") == head.get("implementation_id"),
        contract.get("execution_branch") == "main",
    )
    if not all(checks):
        raise ValueError("ACTIVE_KERNEL_IMPLEMENTATION_MISMATCH")
    for relative, sha in manifest["sources"].items():
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            raise ValueError("ACTIVE_KERNEL_SOURCE_DRIFT:" + relative)
    return {"implementation_id": contract["implementation_id"], "execution_branch": "main",
            "controller_sha256": actual, "canonical_head_digest": head["canonical_head_digest"],
            "runtime_manifest_digest": manifest["manifest_digest"]}


if __name__ == "__main__":
    print(json.dumps(active_kernel_identity(), sort_keys=True))
