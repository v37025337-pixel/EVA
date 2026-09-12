from __future__ import annotations
from pathlib import Path
from typing import Any
import hashlib, json, subprocess

REPO = Path(__file__).resolve().parent.parent
REGISTRY = REPO / 'canonical' / 'yado-unified-experience-registry-v1.json'
OUT = REPO / 'canonical' / 'yado-remote-branch-inventory-v1.json'


def canon(o: Any) -> str:
    return json.dumps(o, sort_keys=True, separators=(',', ':'), default=str)


def digest(o: Any) -> str:
    return hashlib.sha256(canon(o).encode()).hexdigest()


def load(p: Path) -> dict[str, Any]:
    return json.loads(p.read_text(encoding='utf-8'))


def run(args: list[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=REPO, capture_output=True, text=True, timeout=timeout)


def list_remote_heads() -> dict[str, str]:
    cp = run(['git', 'ls-remote', '--heads', 'origin'])
    if cp.returncode != 0:
        raise RuntimeError('REMOTE_HEAD_QUERY_FAILED:' + cp.stderr[-500:])
    out: dict[str, str] = {}
    for line in cp.stdout.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].startswith('refs/heads/'):
            out[parts[1][len('refs/heads/'):]] = parts[0]
    if not out:
        raise RuntimeError('REMOTE_HEAD_QUERY_EMPTY')
    return out


def is_ancestor(ancestor: str, descendant: str) -> bool:
    return run(['git', 'merge-base', '--is-ancestor', ancestor, descendant]).returncode == 0


def classify(name: str, head_sha: str, main_sha: str, registered: set[str]) -> tuple[str, str]:
    if name in registered:
        return 'REGISTERED_EXPERIENCE_REF', 'REGISTERED_IN_CANONICAL_EXPERIENCE'
    if name == 'main':
        return 'CANONICAL_MAIN_REF', 'CANONICAL_CONTROL_REF'
    if name.startswith('pre-'):
        return 'SAFETY_BACKUP_REF', 'BACKUP_ROLE'
    if name.startswith('tmp-'):
        return 'TEMPORARY_HISTORY_REF', 'TEMPORARY_ROLE'
    if name.startswith('deployment-'):
        return 'DEPLOYMENT_INFRASTRUCTURE_REF', 'DEPLOYMENT_ROLE'
    if any(token in name for token in ('integration', 'inventory', 'reconcile', 'resolution')):
        return 'INTEGRATION_VERIFICATION_REF', 'VERIFICATION_ROLE'
    if name.startswith('yado-'):
        if is_ancestor(head_sha, main_sha):
            return 'ABSORBED_CANONICAL_HISTORY_REF', 'TIP_IS_ANCESTOR_OF_CANONICAL_MAIN'
        if is_ancestor(main_sha, head_sha):
            return 'EXPERIENCE_CANDIDATE_REF', 'BRANCH_EXCLUSIVE_DESCENDANT_OF_MAIN'
        return 'EXPERIENCE_CANDIDATE_REF', 'DIVERGED_FROM_CANONICAL_MAIN'
    return 'UNCLASSIFIED_REF', 'NO_SAFE_CLASSIFICATION_RULE'


registry = load(REGISTRY)
registered = {str(x.get('branch')) for x in registry.get('branches', []) if x.get('branch')}
remote = list_remote_heads()
main_sha = remote.get('main')
if not main_sha:
    raise RuntimeError('REMOTE_MAIN_REF_REQUIRED')

# The workflow fetches all refs before execution. Verify that canonical main is locally addressable.
if run(['git', 'cat-file', '-e', main_sha + '^{commit}']).returncode != 0:
    raise RuntimeError('REMOTE_MAIN_COMMIT_NOT_FETCHED:' + main_sha)

rows = []
for name in sorted(remote):
    head_sha = remote[name]
    if run(['git', 'cat-file', '-e', head_sha + '^{commit}']).returncode != 0:
        raise RuntimeError('REMOTE_HEAD_COMMIT_NOT_FETCHED:' + name + ':' + head_sha)
    cls, reason = classify(name, head_sha, main_sha, registered)
    rows.append({
        'branch': name,
        'head_sha': head_sha,
        'classification': cls,
        'classification_reason': reason,
        'tip_is_ancestor_of_main': is_ancestor(head_sha, main_sha),
        'registered_in_experience_registry': name in registered,
        'runtime_active': False if name not in registered else next((bool(x.get('runtime_active')) for x in registry.get('branches', []) if x.get('branch') == name), False),
    })

classes: dict[str, int] = {}
for row in rows:
    classes[row['classification']] = classes.get(row['classification'], 0) + 1

unclassified = [x['branch'] for x in rows if x['classification'] == 'UNCLASSIFIED_REF']
experience_candidates = [x['branch'] for x in rows if x['classification'] == 'EXPERIENCE_CANDIDATE_REF']
absorbed = [x['branch'] for x in rows if x['classification'] == 'ABSORBED_CANONICAL_HISTORY_REF']
registered_remote = sorted(set(remote) & registered)
registry_only = sorted(registered - set(remote))

artifact = {
    'schema': 'yado.remote_branch_inventory.v2',
    'status': 'PASS_COMPLETE_REMOTE_REF_CLASSIFICATION' if not unclassified else 'WITHHOLD_UNCLASSIFIED_REMOTE_REFS',
    'canonical_main_sha': main_sha,
    'remote_branch_count': len(remote),
    'registered_branch_count': len(registered),
    'registered_remote_count': len(registered_remote),
    'classification_counts': dict(sorted(classes.items())),
    'absorbed_canonical_history_refs': absorbed,
    'experience_candidates': experience_candidates,
    'registry_only': registry_only,
    'unclassified_refs': unclassified,
    'coverage_complete': len(rows) == len(remote) and not unclassified,
    'policy': {
        'registered_experience_refs': 'PRESERVE_EXISTING_EXPERIENCE_SEMANTICS',
        'absorbed_canonical_history_refs': 'DO_NOT_DOUBLE_ADMIT; HISTORY_ALREADY_REACHABLE_FROM_CANONICAL_MAIN',
        'safety_backup_refs': 'DO_NOT_ADMIT_AS_COGNITIVE_EXPERIENCE_BY_NAME_ALONE',
        'temporary_history_refs': 'DO_NOT_ADMIT_AS_COGNITIVE_EXPERIENCE_BY_NAME_ALONE',
        'deployment_infrastructure_refs': 'INFRASTRUCTURE_NOT_COGNITIVE_EXPERIENCE',
        'integration_verification_refs': 'VERIFICATION_TRANSPORT_NOT_COGNITIVE_EXPERIENCE_BY_DEFAULT',
        'experience_candidate_refs': 'REQUIRE_FRESH_EVIDENCE_AND_PROVENANCE_REVALIDATION',
        'unknown_refs': 'FAIL_CLOSED',
        'branch_name_as_evidence': False,
        'semantic_promotion_by_ancestry': False,
    },
    'rows': rows,
    'claim_boundary': 'Git ancestry may prove that branch history is already physically absorbed into canonical main. It does not validate broad semantic claims, activate code, or prove intelligence/consciousness.',
}
artifact['artifact_digest'] = digest(artifact)
OUT.write_text(json.dumps(artifact, indent=2, sort_keys=True) + '\n', encoding='utf-8')
print(json.dumps({
    'status': artifact['status'],
    'main_sha': main_sha,
    'remote_branch_count': artifact['remote_branch_count'],
    'absorbed_count': len(absorbed),
    'experience_candidate_count': len(experience_candidates),
    'unclassified_count': len(unclassified),
    'artifact_digest': artifact['artifact_digest'],
}, indent=2, sort_keys=True))
