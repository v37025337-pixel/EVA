"""Build a traceable birth from all frozen Git refs and historical snapshots."""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
import zlib

from . import archive as store
from .__main__ import build as predecessor_build, ROOT
from .cognitive import replay as replay_cognitive
from .graph import KERNEL_ID
from .kernel import decode, fingerprint


def import_snapshots(path):
    """Import verified bytes and derive replayable goals, never imported verdicts."""
    archive = store.ExperienceArchive(path)
    db = sqlite3.connect(path)
    db.execute('PRAGMA foreign_keys=ON')
    sources = archive.db.execute("SELECT source,digest FROM external_sources WHERE lower(source) LIKE '%.sqlite'").fetchall()
    seen, seeds, imported = set(), {}, []
    try:
        with db, tempfile.TemporaryDirectory(prefix='yado-history-') as tmp:
            for item in sources:
                digest = item['digest']
                if digest in seen:
                    continue
                seen.add(digest)
                target = Path(tmp) / (digest + '.sqlite')
                # Read through the importing connection: large transactions can
                # spill SQLite's cache and hold an exclusive rollback-journal
                # lock, so a second reader would wait on our own transaction.
                payload = db.execute('SELECT size,payload FROM blobs WHERE digest=?', (digest,)).fetchone()
                raw = zlib.decompress(payload[1])
                if len(raw) != payload[0] or store.sha(raw) != digest:
                    raise ValueError('HISTORICAL_CONTAINER_INTEGRITY')
                target.write_bytes(raw)
                old = sqlite3.connect(target.as_uri() + '?mode=ro', uri=True)
                old.row_factory = sqlite3.Row
                try:
                    old.execute('PRAGMA trusted_schema=OFF')
                    tables = {r[0] for r in old.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                    entry = {'source': item['source'], 'digest': digest, 'mode': 'OPAQUE_PRESERVED'}
                    if {'metadata', 'blobs', 'git_objects', 'refs', 'branch_files', 'documents'} <= tables:
                        summary = json.loads(old.execute("SELECT value FROM metadata WHERE key='summary'").fetchone()[0])
                        if summary['schema'] != store.SCHEMA:
                            raise ValueError('HISTORICAL_ARCHIVE_SCHEMA')
                        def old_raw(d):
                            row = old.execute('SELECT size,payload FROM blobs WHERE digest=?', (d,)).fetchone()
                            raw = zlib.decompress(row['payload'])
                            if len(raw) != row['size'] or store.sha(raw) != d:
                                raise ValueError('HISTORICAL_BLOB_INTEGRITY')
                            return raw
                        for row in old.execute('SELECT digest,size,payload FROM blobs'):
                            old_raw(row['digest'])
                            db.execute('INSERT OR IGNORE INTO blobs VALUES(?,?,?)', tuple(row))
                        for row in old.execute('SELECT oid,kind,digest,path_hint FROM git_objects'):
                            raw = old_raw(row['digest'])
                            oid = hashlib.new(summary['git_object_format'], f"{row['kind']} {len(raw)}\0".encode() + raw).hexdigest()
                            if oid != row['oid']:
                                raise ValueError('HISTORICAL_GIT_IDENTITY')
                            db.execute('INSERT OR IGNORE INTO git_objects VALUES(?,?,?,?)', tuple(row))
                        prefix = 'snapshots/' + digest + '/'
                        db.executemany('INSERT INTO refs VALUES(?,?)', ((prefix + r['name'], r['oid']) for r in old.execute('SELECT * FROM refs')))
                        db.executemany('INSERT INTO branch_files VALUES(?,?,?)', ((prefix + r['ref'], r['path'], r['oid']) for r in old.execute('SELECT * FROM branch_files')))
                        if 'external_sources' in tables:
                            db.executemany('INSERT INTO external_sources VALUES(?,?,?)', ((prefix + r['source'], r['digest'], r['metadata']) for r in old.execute('SELECT * FROM external_sources')))
                        for row in old.execute('SELECT digest,path FROM documents'):
                            store._index(db, row['digest'], old_raw(row['digest']), prefix + row['path'])
                        entry.update(mode='VERIFIED_ARCHIVE_IMPORTED', refs=old.execute('SELECT count(*) FROM refs').fetchone()[0])
                    elif 'events' in tables:
                        columns = {r[1] for r in old.execute('PRAGMA table_info(events)')}
                        if {'tick', 'previous_hash', 'body', 'event_hash'} <= columns:
                            if old.execute('SELECT count(*) FROM events').fetchone()[0] > 50000:
                                raise ValueError('HISTORICAL_EVENT_BUDGET')
                            previous, tick, records = '0' * 64, 0, []
                            for row in old.execute('SELECT * FROM events ORDER BY tick'):
                                tick += 1
                                expected = store.sha((previous + '\n' + str(tick) + '\n' + row['body']).encode())
                                if row['tick'] != tick or row['previous_hash'] != previous or row['event_hash'] != expected:
                                    raise ValueError('HISTORICAL_EVENT_CHAIN')
                                previous = expected
                                body = decode(row['body'])
                                if str(body.get('kind', '')).startswith('COG_'):
                                    records.append({**body, 'tick': tick, 'event_hash': expected})
                            goals = replay_cognitive(records)
                            for goal in goals.values():
                                value = {k: v for k, v in goal['spec'].items() if k != 'domain'}
                                seed = {'source_digest': digest, 'source_tick': goal['id'],
                                        'capability': goal['spec']['domain'], 'input': value,
                                        'previous_status_is_not_a_new_test': True}
                                seeds.setdefault(fingerprint({'capability': seed['capability'], 'input': value}), seed)
                            entry.update(mode='VERIFIED_SESSION_REHEARSAL_SOURCE', ticks=tick, goals=len(goals))
                    imported.append(entry)
                finally:
                    old.close()
                    target.unlink()
            if db.execute('PRAGMA foreign_key_check').fetchone() is not None:
                raise ValueError('IMPORTED_ARCHIVE_REFERENCE_FAILURE')
            summary = dict(archive.summary)
            counts = dict(summary['counts'])
            counts.update({kind: count for kind, count in db.execute('SELECT kind,count(*) FROM git_objects GROUP BY kind')})
            for key, table in [('unique_payloads', 'blobs'), ('indexed_documents', 'documents'), ('external_sources_and_members', 'external_sources')]:
                counts[key] = db.execute('SELECT count(*) FROM ' + table).fetchone()[0]
            counts['historical_snapshot_refs'] = db.execute("SELECT count(*) FROM refs WHERE name LIKE 'snapshots/%'").fetchone()[0]
            summary.update(counts=counts, historical_snapshot_imports=imported)
            db.execute("UPDATE metadata SET value=? WHERE key='summary'", (store.canonical(summary),))
        return summary, list(seeds.values())
    finally:
        db.close(); archive.close()


def source_catalog(path, manifest):
    archive = store.ExperienceArchive(path)
    versions = {}
    try:
        for row in archive.db.execute("SELECT f.ref,f.path,o.digest FROM branch_files f JOIN git_objects o ON f.oid=o.oid WHERE f.path LIKE '%.py'"):
            item = versions.setdefault(row['digest'], {'sha256': row['digest'], 'locations': [], 'working_paths': []})
            item['locations'].append({'ref': row['ref'], 'path': row['path']})
        for row in archive.db.execute("SELECT source,digest FROM external_sources WHERE lower(source) LIKE '%.py'"):
            item = versions.setdefault(row['digest'], {'sha256': row['digest'], 'locations': [], 'working_paths': []})
            item['locations'].append({'source': row['source']})
        pinned = manifest['inherited_files'] | manifest['assembly_sources']
        current = {}
        for name, digest in pinned.items():
            if not name.endswith('.py'):
                continue
            item = versions.setdefault(digest, {'sha256': digest, 'locations': [], 'working_paths': []})
            item['working_paths'].append(name)
            current[name] = digest
        for digest, item in versions.items():
            raw = (ROOT / item['working_paths'][0]).read_bytes() if item['working_paths'] else archive.read(digest)
            try:
                tree = ast.parse(raw)
                item.update(parse='PASS', symbols=sorted({n.name for n in ast.walk(tree) if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))}),
                            imports=[], component_ids=[])
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        item['imports'].extend({'module': a.name, 'level': 0} for a in node.names)
                    elif isinstance(node, ast.ImportFrom):
                        item['imports'].append({'module': node.module or '', 'level': node.level})
                    elif isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        if any(isinstance(t, ast.Name) and t.id in {'COMPONENT_ID', 'CORE_ID', 'KERNEL_ID', 'CONTROLLER_ID', 'ALGORITHM_ID'} for t in node.targets):
                            item['component_ids'].append(node.value.value)
            except (SyntaxError, UnicodeDecodeError, ValueError) as error:
                item.update(parse='HISTORICAL_SOURCE_NOT_ACTIVATED', parse_error=str(error))
        aliases = {}
        for name in current:
            module = name.removesuffix('.py').replace('/', '.')
            for alias in {module, Path(name).stem, module.removeprefix('runtime.'), module.removeprefix('runtime.yado_rc8_v36.')}:
                aliases.setdefault(alias, []).append(name)
        edges, unresolved = [], []
        for name, digest in current.items():
            package = name.removesuffix('.py').replace('/', '.').split('.')[:-1]
            for imp in versions[digest].get('imports', []):
                module = imp['module']
                if imp['level']:
                    module = '.'.join(package[:len(package) - imp['level'] + 1] + ([module] if module else []))
                targets = aliases.get(module, [])
                if targets:
                    edges.extend({'from': name, 'to': target, 'import': module} for target in targets if target != name)
                elif module.startswith(('yado_', 'successor.')):
                    unresolved.append({'from': name, 'import': module})
        edges = [dict(zip(('from', 'to', 'import'), edge)) for edge in sorted({(e['from'], e['to'], e['import']) for e in edges})]
        branches = []
        for ref, tip in archive.summary['refs'].items():
            if ref.startswith('refs/remotes/'):
                ahead = int(store.git(ROOT, 'rev-list', '--count', 'HEAD..' + tip))
                branches.append({'ref': ref, 'tip': tip, 'unintegrated_commits': ahead})
        canonical_planes = []
        for name in manifest['inherited_files']:
            if name.startswith('canonical/') and name.endswith('.json'):
                try:
                    data = json.loads((ROOT / name).read_text())
                    if isinstance(data, dict) and isinstance(data.get('planes'), (list, dict)):
                        canonical_planes.append({'path': name, 'planes': data['planes']})
                except (ValueError, UnicodeDecodeError):
                    pass
        summary = {'remote_branches': len(branches), 'all_frozen_branches_integrated': all(b['unintegrated_commits'] == 0 for b in branches),
                   'unique_python_versions': len(versions), 'current_python_files': len(current),
                   'local_import_edges': len(edges), 'unresolved_local_imports': len(unresolved),
                   'historical_parse_failures': sum(v['parse'] != 'PASS' for v in versions.values())}
        return {'schema': 'yado.unified.source_catalog.v1', 'summary': summary, 'branches': branches,
                'canonical_planes': canonical_planes, 'local_import_graph': edges, 'unresolved_local_imports': unresolved,
                'modules': [versions[k] for k in sorted(versions)], 'historical_source_is_not_automatically_executed': True}
    finally:
        archive.close()


def build(output, external_root=None, catalog_path=None):
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError('BIRTH_EXISTS; select a fresh output directory')
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='unified-birth-', dir=output.parent))
    try:
        predecessor_build(staging, external_root, catalog_path)
        manifest = json.loads((staging / 'manifest.json').read_text())
        previous = manifest.pop('identity_digest')
        archive_summary, seeds = import_snapshots(staging / 'experience.sqlite')
        catalog = source_catalog(staging / 'experience.sqlite', manifest)
        if not catalog['summary']['all_frozen_branches_integrated']:
            raise ValueError('UNINTEGRATED_FROZEN_BRANCHES')
        for key, filename, data in [('source_catalog', 'source-catalog.json', catalog), ('rehearsal_goals', 'rehearsal-goals.json', seeds)]:
            path = staging / filename
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
            manifest[key] = {'file': filename, 'sha256': store.file_sha(path)}
        manifest.update(schema='yado.unified.birth.v1', kernel_id=KERNEL_ID,
                        predecessor_identity_digest=previous, archive_sha256=store.file_sha(staging / 'experience.sqlite'),
                        archive_counts=archive_summary['counts'],
                        architecture='PERSISTENT_VERIFIED_CAUSAL_DATAFLOW_WITH_EMPIRICAL_ROUTING',
                        self_model_origin='DEDUPLICATED_CHECKED_LOCAL_EXECUTIONS', historical_rehearsal_goal_count=len(seeds))
        manifest['identity_digest'] = store.sha(store.canonical(manifest).encode())
        (staging / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
        staging.rename(output)
        return {'status': 'BUILT_REQUIRES_VALIDATION', 'manifest': str(output / 'manifest.json'),
                'identity_digest': manifest['identity_digest'], 'archive_counts': manifest['archive_counts'],
                'catalog_summary': catalog['summary'], 'historical_rehearsal_goals': len(seeds)}
    except BaseException:
        shutil.rmtree(staging)
        raise


def rehearse(graph, limit=12):
    if type(limit) is not int or not 1 <= limit <= 64:
        raise ValueError('REHEARSAL_BUDGET')
    kernel = graph.kernel
    binding = kernel.manifest.get('rehearsal_goals')
    if binding is None:
        return []
    path = (kernel.manifest_path.parent / binding['file']).resolve()
    if not path.is_relative_to(kernel.manifest_path.parent) or store.file_sha(path) != binding['sha256']:
        raise ValueError('REHEARSAL_ARTIFACT_INTEGRITY')
    seeds = json.loads(path.read_text())
    already = {g['spec']['provenance'].get('rehearsal_id') for g in graph.snapshot()['goals'].values()}
    submitted = []
    for seed in seeds:
        oid = fingerprint({'capability': seed['capability'], 'input': seed['input']})
        if oid in already:
            continue
        submitted.append(graph.submit({'goal': 'Recheck historical goal ' + oid[:12], 'origin': 'experience',
            'provenance': {'source_digest': seed['source_digest'], 'source_tick': seed['source_tick'],
                           'rehearsal_id': oid, 'fresh_external_test': False},
            'nodes': [{'id': 'rehearsal', 'capability': seed['capability'], 'input': seed['input'], 'budget': 6}]}))
        already.add(oid)
        if len(submitted) == limit:
            break
    return submitted
