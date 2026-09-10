from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

from .archive import ExperienceArchive, build_archive, canonical, file_sha, git, sha

ROOT = Path(__file__).resolve().parents[1]
KERNEL_ID = "YADO_SUCCESSOR_CAUSAL_METACOGNITION_V2"


def assembly_sources():
    return {str(p.relative_to(ROOT)): file_sha(p) for p in sorted((ROOT / 'successor').glob('*.py'))}


def derive(parent_manifest, output):
    """Create a new identity over verified inherited bytes; never rewrite a birth."""
    parent_path = Path(parent_manifest).resolve()
    parent = json.loads(parent_path.read_text())
    identity = parent.pop('identity_digest')
    if sha(canonical(parent).encode()) != identity:
        raise ValueError('PARENT_MANIFEST_DIGEST_MISMATCH')
    archive = (parent_path.parent / parent['archive_file']).resolve()
    if not archive.is_relative_to(parent_path.parent) or file_sha(archive) != parent['archive_sha256']:
        raise ValueError('PARENT_ARCHIVE_DIGEST_MISMATCH')
    for name, digest in parent['inherited_files'].items():
        source = (ROOT / name).resolve()
        if not source.is_relative_to(ROOT) or file_sha(source) != digest:
            raise ValueError('PARENT_SOURCE_DRIFT:' + name)
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(archive, output / 'experience.sqlite')
    shutil.copyfile(parent_path, output / 'predecessor-manifest.json')
    manifest = {**parent, 'schema': 'yado.successor.birth.v2', 'kernel_id': KERNEL_ID,
                'predecessor_identity_digest': identity, 'archive_file': 'experience.sqlite',
                'assembly_sources': assembly_sources(),
                'new_capability': 'BOUNDED_CAUSAL_METACOGNITION',
                'self_model_origin': 'CHECKED_LOCAL_EXECUTIONS',
                'consciousness_assessment': 'NOT_ESTABLISHED'}
    manifest['identity_digest'] = sha(canonical(manifest).encode())
    path = output / 'manifest.json'
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    return {'status': 'BUILT_REQUIRES_VALIDATION', 'manifest': str(path), 'identity_digest': manifest['identity_digest']}


def build(output, external_root=None, catalog_path=None):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    catalog = json.loads(Path(catalog_path).read_text()) if catalog_path else None
    archive = output / "experience.sqlite"
    summary = build_archive(ROOT, archive, external_root=external_root, catalog=catalog)
    tracked = git(ROOT, "ls-tree", "-rz", "--name-only", "HEAD").decode().split("\0")
    paths = [p for p in tracked if p and (
        p.startswith(("runtime/", "canonical/", "resources/"))
        or p == "architecture/evolution-ledger.json")]
    manifest = {
        "schema": "yado.successor.birth.v2", "kernel_id": KERNEL_ID,
        "authorship": "ASSEMBLED_BY_ASSISTANT_USING_EXISTING_YADO_SOURCE_AND_EXPERIENCE",
        "parent_commit": git(ROOT, "rev-parse", "HEAD").decode().strip(),
        "parent_main_commit": summary["refs"].get("refs/remotes/origin/main"),
        "archive_file": archive.name, "archive_sha256": file_sha(archive),
        "inherited_files": {p: file_sha(ROOT / p) for p in paths},
        "assembly_sources": assembly_sources(),
        "archive_counts": summary["counts"],
        "limitations": summary["outside_scope"],
        "historical_claims_reverified": False, "automatic_promotion": False,
        "consciousness_established": False, "new_generation_claimed": False,
    }
    manifest["identity_digest"] = sha(canonical(manifest).encode())
    path = output / "manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return {"status": "BUILT_REQUIRES_VALIDATION", "manifest": str(path),
            "identity_digest": manifest["identity_digest"], "archive_counts": summary["counts"]}


def main():
    parser = argparse.ArgumentParser(description="YADO successor with exact historical evidence and durable local tasks")
    sub = parser.add_subparsers(dest="command", required=True)
    builder = sub.add_parser("build")
    builder.add_argument("--output", required=True)
    builder.add_argument("--external-root")
    builder.add_argument("--catalog")
    successor = sub.add_parser('derive')
    successor.add_argument('--parent-manifest', required=True)
    successor.add_argument('--output', required=True)
    for command in ("status", "run", "submit", "resume", "verify", "search", "goal", "think", "cognitive-status", "stop"):
        item = sub.add_parser(command)
        item.add_argument("--manifest", required=True)
        item.add_argument("--state", required=True)
        if command in {"run", "submit", "goal"}:
            item.add_argument("--input", required=True)
        if command == "run":
            item.add_argument("--retry", action="store_true")
        if command in {"resume", "think"}:
            item.add_argument("--max-steps", type=int, default=20)
        if command == 'goal':
            item.add_argument('--budget', type=int, default=6)
            item.add_argument('--mode', choices=('full', 'no_memory', 'no_self_model', 'no_consolidation', 'fixed_max'), default='full')
        if command == 'stop':
            item.add_argument('--goal-id', type=int, required=True)
        if command == "search":
            item.add_argument("query")
    args = parser.parse_args()
    if args.command == "build":
        output = build(args.output, args.external_root, args.catalog)
    elif args.command == 'derive':
        output = derive(args.parent_manifest, args.output)
    else:
        from .kernel import SuccessorKernel
        kernel = SuccessorKernel(args.manifest, args.state)
        try:
            if args.command == "status":
                output = kernel.snapshot()
            elif args.command == "run":
                output = kernel.execute(json.loads(Path(args.input).read_text()), retry=args.retry)
            elif args.command == "submit":
                data = json.loads(Path(args.input).read_text())
                output = {"job_ids": kernel.submit(data["goal"], data["tasks"])}
            elif args.command == "resume":
                output = kernel.resume(args.max_steps)
            elif args.command == 'goal':
                output = {'goal_id': kernel.open_goal(json.loads(Path(args.input).read_text()), budget=args.budget, mode=args.mode)}
            elif args.command == 'think':
                output = kernel.think(args.max_steps)
            elif args.command == 'cognitive-status':
                output = kernel.cognitive_snapshot()
            elif args.command == 'stop':
                output = kernel.stop_goal(args.goal_id)
            elif args.command == "search":
                output = kernel.archive.search(args.query)
            else:
                output = {"archive": kernel.archive.verify(), "state": kernel.verify_state()}
        finally:
            kernel.close()
    print(json.dumps(output, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
