from __future__ import annotations
from pathlib import Path
from typing import Any
import copy, hashlib, json, subprocess

REPO = Path(__file__).resolve().parent.parent
REGISTRY = REPO / 'canonical' / 'yado-unified-experience-registry-v1.json'
OUT = REPO / 'canonical' / 'yado-remote-branch-inventory-v1.json'


def canon(o: Any) -> str:
    return json.dumps(o, sort_keys=True, separators=(',', ':'), default=str)


def digest(o: Any) -> str:
    return hashlib.sha256(canon(o).encode()).hexdigest()


def load(p: Path) -> dict[str, Any]:
    return json.loads(p.read_text(encoding='utf-8'))


def list_remote_heads() -> dict[str, str]:
    cp = subprocess.run(['git', 'ls-remote', '--heads', 'origin'], cwd=REPO, capture_output=True, text=True, timeout=30)
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


def classify(name: str, registered: set[str]) -> str:
    if name in registered:
        return 'REGISTERED_EXPERIENCE_REF'
    if name.startswith('pre-'):
        return 'SAFETY_BACKUP_REF'
    if name.startswith('tmp-'):
        return 'TEMPORARY_HISTORY_REF'
    if name.startswith('deployment-'):
        return 'DEPLOYMENT_INFRASTRUCTURE_REF'
    if 'integration' in name:
        return 'INTEGRATION_VERIFICATION_REF'
    if name.startswith('yado-'):
        return 'EXPERIENCE_CANDIDATE_REF'
    return 'UNCLASSIFIED_REF'


registry = load(REGISTRY)
registered = {str(x.get('branch')) for x in registry.get('branches', []) if x.get('branch')}
remote = list_remote_heads()
rows = []
for name in sorted(remote):
    cls = classify(name, registered)
    rows.append({
        'branch': name,
        'head_sha': remote[name],
        'classification': cls,
        'registered_in_experience_registry': name in registered,
        'runtime_active': False if name not in registered else next((bool(x.get('runtime_active')) for x in registry.get('branches', []) if x.get('branch') == name), False),
    })

classes: dict[str, int] = {}
for row in rows:
    classes[row['classification']] = classes.get(row['classification'], 0) + 1

unclassified = [x['branch'] for x in rows if x['classification'] == 'UNCLASSIFIED_REF']
experience_candidates = [x['branch'] for x in rows if x['classification'] == 'EXPERIENCE_CANDIDATE_REF']
registered_remote = sorted(set(remote) & registered)
registry_only = sorted(registered - set(remote))

artifact = {
    'schema': 'yado.remote_branch_inventory.v1',
    'status': 'PASS_COMPLETE_REMOTE_REF_CLASSIFICATION' if not unclassified else 'WITHHOLD_UNCLASSIFIED_REMOTE_REFS',
    'remote_branch_count': len(remote),
    'registered_branch_count': len(registered),
    'registered_remote_count': len(registered_remote),
    'classification_counts': dict(sorted(classes.items())),
    'experience_candidates': experience_candidates,
    'registry_only': registry_only,
    'unclassified_refs': unclassified,
    'coverage_complete': len(rows) == len(remote) and not unclassified,
    'policy': {
        'registered_experience_refs': 'PRESERVE_EXISTING_EXPERIENCE_SEMANTICS',
        'safety_backup_refs': 'DO_NOT_ADMIT_AS_COGNITIVE_EXPERIENCE_BY_NAME_ALONE',
        'temporary_history_refs': 'DO_NOT_ADMIT_AS_COGNITIVE_EXPERIENCE_BY_NAME_ALONE',
        'deployment_infrastructure_refs': 'INFRASTRUCTURE_NOT_COGNITIVE_EXPERIENCE',
        'integration_verification_refs': 'VERIFICATION_TRANSPORT_NOT_COGNITIVE_EXPERIENCE_BY_DEFAULT',
        'experience_candidate_refs': 'REQUIRE_SEPARATE_EVIDENCE_AND_PROVENANCE_ADMISSION',
        'unknown_refs': 'FAIL_CLOSED',
    },
    'rows': rows,
    'claim_boundary': 'This artifact classifies physical Git refs. It does not itself promote branch code, claims, or states into active YADO capabilities or validated cognitive experience.',
}
artifact['artifact_digest'] = digest(artifact)
OUT.write_text(json.dumps(artifact, indent=2, sort_keys=True) + '\n', encoding='utf-8')
print(json.dumps({
    'status': artifact['status'],
    'remote_branch_count': artifact['remote_branch_count'],
    'registered_remote_count': artifact['registered_remote_count'],
    'experience_candidate_count': len(experience_candidates),
    'unclassified_count': len(unclassified),
    'artifact_digest': artifact['artifact_digest'],
}, indent=2, sort_keys=True))
