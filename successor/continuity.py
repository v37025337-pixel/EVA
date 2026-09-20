"""Version the implementation while preserving a verified journal identity.

An upgrade creates a new manifest and state copy. It never edits the predecessor,
relabels historical results, or removes source pinning.
"""
from contextlib import closing
import json
from pathlib import Path
import shutil
import sqlite3
import sys
from types import SimpleNamespace

from .archive import canonical, file_sha, sha

SCHEMA = 'yado.successor.implementation-upgrade.v1'


def _inside(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError('CONTINUITY_FILE_OUTSIDE_MANIFEST')
    return path


def _manifest(path):
    value = json.loads(path.read_text())
    body = {k: v for k, v in value.items() if k != 'identity_digest'}
    if sha(canonical(body).encode()) != value.get('identity_digest'):
        raise ValueError('CONTINUITY_MANIFEST_DIGEST')
    return value


def verify_source_transition(manifest, parent):
    before, after = parent['inherited_files'], manifest['inherited_files']
    if set(before) != set(after):
        raise ValueError('CONTINUITY_INHERITED_SOURCE_SET_CHANGED')
    expected = {name: {'previous_sha256': digest, 'current_sha256': after[name]}
                for name, digest in before.items() if digest != after[name]}
    if manifest.get('inherited_source_updates', {}) != expected:
        raise ValueError('CONTINUITY_SOURCE_UPDATE_BINDING')


def operational_identity(manifest, directory):
    continuity = manifest.get('continuity')
    if continuity is None:
        return manifest['identity_digest']
    required = {'schema', 'identity_digest', 'predecessor_implementation_digest',
                'predecessor_manifest_file', 'predecessor_manifest_sha256',
                'predecessor_state_file', 'predecessor_state_sha256',
                'predecessor_tick', 'predecessor_event_hash'}
    if (set(continuity) != required or continuity['schema'] != SCHEMA
            or type(continuity['predecessor_tick']) is not int or continuity['predecessor_tick'] < 0):
        raise ValueError('CONTINUITY_MANIFEST_CONTRACT')
    path = _inside(directory, continuity['predecessor_manifest_file'])
    if file_sha(path) != continuity['predecessor_manifest_sha256']:
        raise ValueError('CONTINUITY_PREDECESSOR_MANIFEST_CHANGED')
    parent = _manifest(path)
    verify_source_transition(manifest, parent)
    expected = parent.get('continuity', {}).get('identity_digest', parent['identity_digest'])
    if (continuity['identity_digest'] != expected
            or continuity['predecessor_implementation_digest'] != parent['identity_digest']
            or manifest.get('predecessor_identity_digest') != parent['identity_digest']):
        raise ValueError('CONTINUITY_IDENTITY_LINEAGE')
    return expected


def upgrade_event(manifest):
    c = manifest['continuity']
    event = {'kind': 'IMPLEMENTATION_UPGRADE', 'identity_digest': c['identity_digest'],
            'predecessor_implementation_digest': c['predecessor_implementation_digest'],
            'implementation_digest': manifest['identity_digest'],
            'predecessor_tick': c['predecessor_tick'],
            'predecessor_event_hash': c['predecessor_event_hash']}
    if manifest.get('inherited_source_updates'):
        event['source_updates_digest'] = sha(canonical(manifest['inherited_source_updates']).encode())
    return event


def verify_prefix(kernel):
    c = kernel.manifest.get('continuity')
    if c is None:
        return
    from .kernel import decode
    path = _inside(kernel.manifest_path.parent, c['predecessor_state_file'])
    if file_sha(path) != c['predecessor_state_sha256']:
        raise ValueError('CONTINUITY_PREDECESSOR_STATE_CHANGED')
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as old:
        if old.execute('SELECT digest FROM identity WHERE id=1').fetchone()[0] != kernel.identity:
            raise ValueError('CONTINUITY_PREDECESSOR_IDENTITY')
        inherited = list(old.execute('SELECT tick,previous_hash,body,event_hash FROM events ORDER BY tick'))
        old_jobs = list(old.execute('SELECT id,goal,task FROM jobs ORDER BY id'))
    current = [tuple(r) for r in kernel.db.execute(
        'SELECT tick,previous_hash,body,event_hash FROM events WHERE tick<=? ORDER BY tick',
        (c['predecessor_tick'],))]
    tail = inherited[-1][3] if inherited else '0' * 64
    if (len(inherited) != c['predecessor_tick'] or tail != c['predecessor_event_hash']
            or current != inherited):
        raise ValueError('CONTINUITY_INHERITED_EVENT_PREFIX_CHANGED')
    for job in old_jobs:
        row = kernel.db.execute('SELECT id,goal,task FROM jobs WHERE id=?', (job[0],)).fetchone()
        if row is None or tuple(row) != job:
            raise ValueError('CONTINUITY_INHERITED_JOB_CHANGED')
    event = kernel.db.execute('SELECT body FROM events WHERE tick=?', (c['predecessor_tick'] + 1,)).fetchone()
    if event is None or decode(event[0]) != upgrade_event(kernel.manifest):
        raise ValueError('CONTINUITY_UPGRADE_EVENT_MISSING_OR_CHANGED')


def prepare_upgrade(parent_manifest, parent_state, output, *, source_updates=None):
    from .__main__ import derive
    from .kernel import ROOT, decode, encode
    # The CLI can decode a checkpoint before any UnifiedYADOCore is constructed.
    sys.path.insert(0, str(ROOT / 'runtime/yado_rc8_v36'))
    from .cognitive import replay as replay_cognitive
    from .development import replay as replay_development
    from .autonomy import replay as replay_autonomy
    from .lineage import replay as replay_lineage
    parent_path, state_path, output = map(lambda p: Path(p).resolve(), (parent_manifest, parent_state, output))
    parent = _manifest(parent_path)
    identity = operational_identity(parent, parent_path.parent)
    if not state_path.is_file():
        raise ValueError('CONTINUITY_PREDECESSOR_STATE_MISSING')
    derive(parent_path, output, source_updates=source_updates)
    snapshot = output / 'predecessor-state.sqlite'
    with closing(sqlite3.connect(state_path.as_uri() + '?mode=ro', uri=True)) as old:
        with closing(sqlite3.connect(snapshot)) as destination:
            old.backup(destination)
    with closing(sqlite3.connect(snapshot)) as old:
        old.execute('PRAGMA journal_mode=DELETE')
        if (old.execute('PRAGMA integrity_check').fetchone()[0] != 'ok'
                or old.execute('PRAGMA foreign_key_check').fetchone() is not None
                or old.execute('SELECT digest FROM identity WHERE id=1').fetchone()[0] != identity):
            raise ValueError('CONTINUITY_PREDECESSOR_STATE_INVALID')
        verify_prefix(SimpleNamespace(manifest=parent, manifest_path=parent_path,
                                      identity=identity, db=old))
        previous, records = '0' * 64, []
        for tick, previous_hash, raw, digest in old.execute(
                'SELECT tick,previous_hash,body,event_hash FROM events ORDER BY tick'):
            if (tick != len(records) + 1 or previous_hash != previous
                    or sha((previous + '\n' + str(tick) + '\n' + raw).encode()) != digest):
                raise ValueError('CONTINUITY_PREDECESSOR_CHAIN_INVALID')
            records.append({**decode(raw), 'tick': tick, 'event_hash': digest})
            previous = digest
    cognitive = [r for r in records if str(r.get('kind', '')).startswith('COG_')]
    development = [r for r in records if str(r.get('kind', '')).startswith(('COG_', 'DEV_'))]
    goals = replay_cognitive(cognitive)
    sessions = list(replay_development(development).values()) + list(replay_autonomy(records, identity).values())
    sessions += list(replay_lineage(records, identity, parent['identity_digest']).values())
    if any(v['status'] == 'ACTIVE' for v in list(goals.values()) + sessions):
        raise ValueError('CONTINUITY_REQUIRES_IDLE_PREDECESSOR')
    manifest_path = output / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest.pop('identity_digest')
    manifest['continuity'] = {
        'schema': SCHEMA, 'identity_digest': identity,
        'predecessor_implementation_digest': parent['identity_digest'],
        'predecessor_manifest_file': 'predecessor-manifest.json',
        'predecessor_manifest_sha256': file_sha(output / 'predecessor-manifest.json'),
        'predecessor_state_file': snapshot.name, 'predecessor_state_sha256': file_sha(snapshot),
        'predecessor_tick': len(records), 'predecessor_event_hash': previous,
    }
    manifest['identity_digest'] = sha(canonical(manifest).encode())
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    state = output / 'kernel.sqlite'
    shutil.copyfile(snapshot, state)
    raw, tick = encode(upgrade_event(manifest)), len(records) + 1
    digest = sha((previous + '\n' + str(tick) + '\n' + raw).encode())
    from .component_binding import implementation_upgrade_event
    component_upgrade = implementation_upgrade_event(records, {
        **upgrade_event(manifest), 'tick': tick, 'event_hash': digest})
    with closing(sqlite3.connect(state)) as db:
        db.execute('INSERT INTO events VALUES(?,?,?,?)', (tick, previous, raw, digest))
        if component_upgrade is not None:
            component_raw = encode(component_upgrade)
            component_digest = sha((digest + '\n' + str(tick + 1) + '\n' + component_raw).encode())
            db.execute('INSERT INTO events VALUES(?,?,?,?)',
                       (tick + 1, digest, component_raw, component_digest))
        db.commit()
    return {'status': 'PREPARED_REQUIRES_RUNTIME_VALIDATION', 'manifest': str(manifest_path),
            'state': str(state), 'identity_digest': identity,
            'implementation_digest': manifest['identity_digest'], 'inherited_events': len(records),
            'component_readmission_required': component_upgrade is not None}


def main():
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--parent-manifest', required=True)
    p.add_argument('--parent-state', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--source-updates', help='Exact predecessor/current SHA-256 map for an audited runtime repair')
    a = p.parse_args()
    updates = json.loads(Path(a.source_updates).read_text()) if a.source_updates else None
    print(json.dumps(prepare_upgrade(a.parent_manifest, a.parent_state, a.output,
                                    source_updates=updates), indent=2))


if __name__ == '__main__':
    main()
