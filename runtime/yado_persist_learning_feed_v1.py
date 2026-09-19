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


def copy_verified_outputs(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    from yado_active_kernel_contract_v1 import active_kernel_identity
    from yado_bounded_autonomous_learning_v1 import digest
    identity = active_kernel_identity(source)
    receipt = json.loads((source / RECEIPT).read_text())
    experience = json.loads((source / EXPERIENCE).read_text())
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
    paths = (RECEIPT, EXPERIENCE, name)
    for item in paths:
        src, dst = (source / item).resolve(), (destination / item).resolve()
        if not src.is_relative_to(source) or not dst.is_relative_to(destination) or not src.is_file():
            raise ValueError("FEED_PATH_ESCAPE")
        if item == name and hashlib.sha256(src.read_bytes()).hexdigest() != capability["sha256"]:
            raise ValueError("CAPABILITY_SOURCE_DRIFT")
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
