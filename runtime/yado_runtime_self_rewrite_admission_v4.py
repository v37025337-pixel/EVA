from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
V4_RECEIPT = Path("candidates/autonomous/yado-native-self-rewrite-v4-fresh-experience.json")
CANDIDATE = Path("candidates/autonomous/yado_bounded_autonomous_learning_runtime_candidate_v4.py")
TARGET = Path("runtime/yado_bounded_autonomous_learning_v1.py")
OUT = Path("candidates/autonomous/yado-runtime-self-rewrite-admission-v4.json")


def load_json(path: Path) -> dict[str, Any]:
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict):
        raise RuntimeError("JSON_OBJECT_REQUIRED:"+str(path))
    return value


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def binding(path: Path) -> dict[str, Any]:
    tree=ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node,ast.Assign) and any(
            isinstance(t,ast.Name) and t.id=="LEARNED_EXTERNAL_EVIDENCE_V2"
            for t in node.targets
        ):
            value=ast.literal_eval(node.value)
            if isinstance(value,dict):
                return value
    raise RuntimeError("LEARNED_BINDING_MISSING:"+str(path))


def load_module(path: Path):
    spec=importlib.util.spec_from_file_location("yado_v4_admission_candidate",path)
    if spec is None or spec.loader is None:
        raise RuntimeError("MODULE_SPEC_FAILED")
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def analyze(root: Path = ROOT) -> dict[str, Any]:
    root=Path(root).resolve()
    receipt=load_json(root/V4_RECEIPT)
    candidate=root/CANDIDATE
    target=root/TARGET

    if receipt.get("status")!="PASS_SHADOW_NATIVE_SELF_REWRITE_V4_FRESH_EXPERIENCE":
        raise RuntimeError("V4_GENERATION_NOT_VERIFIED")

    candidate_sha=sha(candidate)
    target_sha=sha(target)
    parent_sha=str(receipt.get("parent_runtime_sha256") or "")
    expected_candidate=str(receipt.get("candidate_sha256") or "")

    if target_sha==parent_sha:
        state="PARENT_RUNTIME_PENDING_SHADOW_APPLY"
    elif target_sha==expected_candidate:
        state="V4_CANDIDATE_APPLIED_IN_ISOLATED_WORKTREE"
    else:
        state="UNEXPECTED_RUNTIME_STATE"

    compile(candidate.read_text(encoding="utf-8"),str(candidate),"exec")
    compile(target.read_text(encoding="utf-8"),str(target),"exec")
    candidate_binding=binding(candidate)
    target_binding=binding(target)

    module=load_module(candidate)
    priority={
        "code":"AUTONOMOUS_LEARNING_BOOTSTRAP",
        "area":"MEMORY_AND_EXPERIENCE",
        "recommended_action":"For each candidate branch, rederive evidence and provenance; admit only validated developmental experience, never branch names alone.",
    }
    observed={str(row["id"]):float(row["score"]) for row in module.rank_sources(priority)}
    expected={str(k):float(v) for k,v in (receipt.get("ranking_after") or {}).items()}

    source=candidate.read_text(encoding="utf-8")
    tree=ast.parse(source)
    calls={
        node.func.id for node in ast.walk(tree)
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name)
    }
    imported=set()
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node,ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])

    checks={
        "candidate_sha_matches_v4_receipt":candidate_sha==expected_candidate,
        "candidate_differs_from_parent":candidate_sha!=parent_sha,
        "runtime_state_recognized":state in {"PARENT_RUNTIME_PENDING_SHADOW_APPLY","V4_CANDIDATE_APPLIED_IN_ISOLATED_WORKTREE"},
        "candidate_binding_matches_v4_receipt":candidate_binding==dict(receipt.get("candidate_learned_binding") or {}),
        "candidate_binds_latest_experience":candidate_binding.get("experience_digest")==receipt.get("latest_experience_digest"),
        "candidate_ranking_matches_v4_receipt":observed==expected,
        "target_matches_candidate_when_shadow_applied":True if state!="V4_CANDIDATE_APPLIED_IN_ISOLATED_WORKTREE" else target_binding==candidate_binding,
        "no_eval_exec_subprocess":"eval" not in calls and "exec" not in calls and "subprocess" not in imported,
        "probe_mutated_runtime":False,
        "automatic_main_mutation":False,
        "canonical_mutation":False,
    }
    passed=all(v is True for k,v in checks.items() if k not in {"probe_mutated_runtime","automatic_main_mutation","canonical_mutation"}) and all(
        checks[k] is False for k in {"probe_mutated_runtime","automatic_main_mutation","canonical_mutation"}
    )

    return {
        "schema":"yado.runtime_self_rewrite_admission.v4.probe.v1",
        "status":"PASS_SHADOW_RUNTIME_SELF_REWRITE_ADMISSION_V4_PROBE" if passed else "WITHHOLD_RUNTIME_SELF_REWRITE_ADMISSION_V4_PROBE",
        "runtime_state":state,
        "parent_runtime_sha256":parent_sha,
        "candidate_sha256":candidate_sha,
        "target_sha256":target_sha,
        "latest_experience_digest":receipt.get("latest_experience_digest"),
        "checks":checks,
        "next_required_capability":"ISOLATED_FULL_REGRESSION_V4" if state=="PARENT_RUNTIME_PENDING_SHADOW_APPLY" else "PHYSICAL_RUNTIME_PROMOTION_V4_REQUIRES_SEPARATE_GATE",
    }


def analyze_committed(root: Path = ROOT) -> dict[str, Any]:
    """Analyze committed Git HEAD, insulated from transient shadow mutations."""
    root=Path(root).resolve()
    if not (root/".git").exists():
        result=analyze(root)
        result["repository_view"]="WORKTREE_FALLBACK_NO_GIT"
        return result

    required=(V4_RECEIPT,CANDIDATE,TARGET)
    with tempfile.TemporaryDirectory(prefix="yado-v4-admission-head-") as directory:
        shadow=Path(directory)
        for relative in required:
            cp=subprocess.run(
                ["git","show","HEAD:"+relative.as_posix()],
                cwd=root,
                capture_output=True,
                timeout=30,
            )
            if cp.returncode != 0:
                raise RuntimeError(
                    "COMMITTED_ARTIFACT_READ_FAILED:"
                    +relative.as_posix()
                    +":"
                    +cp.stderr.decode("utf-8","replace")[-500:]
                )
            out=shadow/relative
            out.parent.mkdir(parents=True,exist_ok=True)
            out.write_bytes(cp.stdout)
        result=analyze(shadow)
        result["repository_view"]="COMMITTED_HEAD"
        return result


def run(root: Path = ROOT) -> dict[str, Any]:
    root=Path(root).resolve()
    result=analyze(root)
    out=root/OUT
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(result,sort_keys=True))
    return result


if __name__=="__main__":
    raise SystemExit(0 if run()["status"].startswith("PASS_") else 2)
