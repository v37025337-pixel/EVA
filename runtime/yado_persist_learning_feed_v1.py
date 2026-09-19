"""Copy only verified learning outputs; executable code stays on main."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = "candidates/autonomous/yado-bounded-autonomous-learning-v1.json"
EXPERIENCE = "experience/autonomous/yado-autonomous-learning-latest.json"


def _data_path(root, relative):
    path = root
    for part in Path(relative).parts:
        path = path / part
        if path.is_symlink():
            raise ValueError("FEED_PATH_SYMLINK")
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("FEED_PATH_ESCAPE")
    return resolved


def verified_learning_outputs(source, identity):
    """Validate data and its provenance without executing generated recall code."""
    source = Path(source).resolve()
    from yado_bounded_autonomous_learning_v1 import digest
    receipt = json.loads(_data_path(source, RECEIPT).read_text())
    experience = json.loads(_data_path(source, EXPERIENCE).read_text())
    expected = digest({k: v for k, v in experience.items() if k != "experience_digest"})
    capability = receipt["generated_capability"]
    name = capability["path"]
    relative = Path(name)
    if relative.parent.as_posix() != "candidates/autonomous" or not relative.name.startswith("yado_learned_recall_") or relative.suffix != ".py":
        raise ValueError("FEED_OUTPUT_PATH_NOT_ALLOWED")
    if (receipt.get("status") != "PASS_SHADOW_BOUNDED_AUTONOMOUS_EXTERNAL_LEARNING_V1"
        or experience.get("status") != receipt["status"]
        or experience.get("execution_identity") != identity
        or expected != experience.get("experience_digest")
        or expected != receipt.get("experience_digest")
        or capability.get("fact_count", 0) <= 0
        or receipt.get("receipt_sha256") != digest({k: v for k, v in receipt.items() if k != "receipt_sha256"})):
        raise ValueError("UNVERIFIED_LEARNING_OUTPUT")
    sources = experience.get("sources") or []
    failures = experience.get("failures", [])
    policy = experience.get("network_policy") or {}
    facts = sum(len(row.get("facts", [])) for row in sources)
    if (not sources or facts != capability.get("fact_count")
        or len({row.get("source_id") for row in sources}) != len(sources)
        or any(not row.get("source_id") or row.get("fact_count") != len(row.get("facts", []))
               or any(not isinstance(fact, str) or not fact.strip() for fact in row.get("facts", []))
               for row in sources)
        or receipt.get("source_success_count") != len(sources)
        or receipt.get("source_failure_count") != len(failures)
        or receipt.get("real_network_used") is not True
        or any(receipt.get(key) is not False for key in ("credentials_used", "external_mutation", "external_model_used", "candidate_canonical_active"))
        or any(experience.get(key) is not False for key in ("canonical_mutation", "automatic_main_mutation"))
        or policy.get("https_only") is not True or policy.get("methods") != ["GET"]
        or any(policy.get(key) is not False for key in ("credentials_allowed", "external_writes", "downloaded_code_executed"))
        or any((row.get("network") or {}).get("network_executed") is not True
               or row["network"].get("status") != 200
               or row["network"].get("credentials_used") is not False
               or row["network"].get("read_only") is not True for row in sources)):
        raise ValueError("INCONSISTENT_LEARNING_EVIDENCE")
    paths = (RECEIPT, EXPERIENCE, name)
    for item in paths:
        src = _data_path(source, item)
        if not src.is_file():
            raise ValueError("FEED_PATH_ESCAPE")
        if item == name and hashlib.sha256(src.read_bytes()).hexdigest() != capability["sha256"]:
            raise ValueError("CAPABILITY_SOURCE_DRIFT")
    return experience, receipt, paths


def copy_verified_outputs(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    from yado_active_kernel_contract_v1 import active_kernel_identity
    _, _, paths = verified_learning_outputs(source, active_kernel_identity(source))
    for item in paths:
        _data_path(destination, item)
    for item in paths:
        dst = destination / item
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / item, dst)
    return list(paths)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", required=True)
    args = parser.parse_args()
    print(json.dumps({"copied": copy_verified_outputs(ROOT, args.destination)}))
