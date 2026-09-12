"""Lossless historical store. Archived source and reported verdicts are data."""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import tempfile
import zipfile
import zlib

SCHEMA = "yado.successor.archive.v1"
INDEX_TEXT_LIMIT = 200_000


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def file_sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def git(repo, *args, **kwargs):
    return subprocess.check_output(["git", "-C", str(repo), *args], **kwargs)


def reported_outcome(data):
    # These are source assertions, never freshly verified results.
    if not isinstance(data, dict):
        return "", "UNKNOWN", ""
    status = next((data[k] for k in ("status", "verdict", "result")
                   if isinstance(data.get(k), str)), "")
    upper = status.upper()
    if upper.startswith(("FAIL", "ERROR")):
        outcome = "FAIL"
    elif upper.startswith("ROLLBACK"):
        outcome = "ROLLBACK"
    elif upper.startswith(("WITHHOLD", "BLOCK", "REJECT")):
        outcome = "WITHHOLD"
    elif upper.startswith(("PASS", "SUCCESS", "VERIFIED", "COMMIT")):
        outcome = "PASS"
    else:
        outcome = "UNKNOWN"
    nxt = data.get("next_required_capability")
    return status, outcome, nxt if isinstance(nxt, str) else ""


def _schema(db):
    db.executescript("""
    PRAGMA foreign_keys=ON;
    CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
    CREATE TABLE blobs(digest TEXT PRIMARY KEY, size INTEGER NOT NULL, payload BLOB NOT NULL);
    CREATE TABLE git_objects(oid TEXT PRIMARY KEY, kind TEXT NOT NULL,
        digest TEXT NOT NULL REFERENCES blobs(digest), path_hint TEXT NOT NULL);
    CREATE TABLE refs(name TEXT PRIMARY KEY, oid TEXT NOT NULL REFERENCES git_objects(oid));
    CREATE TABLE branch_files(ref TEXT NOT NULL REFERENCES refs(name), path TEXT NOT NULL,
        oid TEXT NOT NULL REFERENCES git_objects(oid), PRIMARY KEY(ref,path));
    CREATE TABLE external_sources(source TEXT PRIMARY KEY,
        digest TEXT NOT NULL REFERENCES blobs(digest), metadata TEXT NOT NULL);
    CREATE TABLE documents(id INTEGER PRIMARY KEY, digest TEXT NOT NULL UNIQUE REFERENCES blobs(digest),
        path TEXT NOT NULL, reported_status TEXT NOT NULL, reported_outcome TEXT NOT NULL,
        next_capability TEXT NOT NULL, indexed_chars INTEGER NOT NULL, full_chars INTEGER NOT NULL);
    CREATE VIRTUAL TABLE search_index USING fts5(path, body, content='');
    """)


def _put(db, raw):
    digest = sha(raw)
    if not db.execute("SELECT 1 FROM blobs WHERE digest=?", (digest,)).fetchone():
        db.execute("INSERT INTO blobs VALUES(?,?,?)", (digest, len(raw), zlib.compress(raw)))
    return digest


def _index(db, digest, raw, path):
    if db.execute("SELECT 1 FROM documents WHERE digest=?", (digest,)).fetchone():
        return
    if Path(path).suffix.lower() not in {".json", ".jsonl", ".py", ".md", ".txt", ".yml", ".yaml", ".sql"}:
        return
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return
    try:
        obj = json.loads(text)
    except (ValueError, RecursionError):
        obj = None
    status, outcome, nxt = reported_outcome(obj)
    indexed = text[:INDEX_TEXT_LIMIT]
    row = db.execute("INSERT INTO documents(digest,path,reported_status,reported_outcome,next_capability,indexed_chars,full_chars) VALUES(?,?,?,?,?,?,?)",
                     (digest, path, status, outcome, nxt, len(indexed), len(text)))
    db.execute("INSERT INTO search_index(rowid,path,body) VALUES(?,?,?)", (row.lastrowid, path, indexed))


def _external(db, source, raw, metadata, *, expand_zip=True,
              max_expanded_bytes=128 * 1024 * 1024, max_member_bytes=32 * 1024 * 1024):
    digest = _put(db, raw)
    db.execute("INSERT INTO external_sources VALUES(?,?,?)", (source, digest, canonical(metadata)))
    _index(db, digest, raw, source)
    if expand_zip and source.lower().endswith(".zip"):
        # Read members as bytes; never extract paths or run reconstruction scripts.
        with zipfile.ZipFile(io.BytesIO(raw)) as bundle:
            infos = [x for x in bundle.infolist() if not x.is_dir()]
            if sum(x.file_size for x in infos) > max_expanded_bytes:
                raise ValueError("EXTERNAL_ARCHIVE_EXPANSION_LIMIT:" + source)
            for index, member in enumerate(infos):
                if member.file_size > max_member_bytes:
                    raise ValueError("EXTERNAL_MEMBER_SIZE_LIMIT:" + member.filename)
                _external(db, source + "!/" + str(index) + "/" + member.filename,
                          bundle.read(member), {"container_digest": digest,
                                                "member": member.filename}, expand_zip=False)


def build_archive(repo, target, *, external_root=None, catalog=None):
    """Capture all objects reachable from frozen local refs, including deleted history."""
    repo, target = Path(repo).resolve(), Path(target).resolve()
    if target.exists():
        raise FileExistsError("ARCHIVE_EXISTS; choose a new snapshot path")
    if git(repo, "rev-parse", "--is-shallow-repository").strip() != b"false":
        raise ValueError("SHALLOW_HISTORY_NOT_COMPLETE")
    fmt = git(repo, "rev-parse", "--show-object-format").decode().strip()
    refs = {}
    rawrefs = git(repo, "for-each-ref", "--format=%(refname) %(objectname) %(symref)").decode()
    for row in rawrefs.splitlines():
        fields = row.split()
        if len(fields) == 2:
            refs[fields[0]] = fields[1]
    if not refs:
        raise ValueError("NO_SOURCE_REFS")
    tips = sorted(set(refs.values()))
    lines = git(repo, "rev-list", "--objects", *tips).decode().splitlines()
    objects = dict(line.split(" ", 1) if " " in line else (line, "") for line in lines)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix="archive-", suffix=".sqlite", dir=target.parent)
    os.close(fd)
    db = sqlite3.connect(temp_name)
    try:
        _schema(db)
        with db, tempfile.TemporaryFile() as source:
            source.write(("\n".join(objects) + "\n").encode())
            source.seek(0)
            with subprocess.Popen(["git", "-C", str(repo), "cat-file", "--batch"],
                                  stdin=source, stdout=subprocess.PIPE) as process:
                for expected_oid, hint in objects.items():
                    header = process.stdout.readline().decode().strip().split()
                    if len(header) != 3 or header[0] != expected_oid:
                        raise ValueError("MISSING_GIT_OBJECT:" + expected_oid)
                    oid, kind, size = header
                    raw = process.stdout.read(int(size))
                    if len(raw) != int(size) or process.stdout.read(1) != b"\n":
                        raise ValueError("TRUNCATED_GIT_OBJECT:" + oid)
                    hashed = hashlib.new(fmt, f"{kind} {size}\0".encode() + raw).hexdigest()
                    if hashed != oid:
                        raise ValueError("GIT_OBJECT_HASH_MISMATCH:" + oid)
                    digest = _put(db, raw)
                    db.execute("INSERT INTO git_objects VALUES(?,?,?,?)", (oid, kind, digest, hint))
                    if kind == "blob":
                        _index(db, digest, raw, hint)
                if process.wait() != 0:
                    raise RuntimeError("GIT_OBJECT_READ_FAILED")
            db.executemany("INSERT INTO refs VALUES(?,?)", sorted(refs.items()))
            for ref, tip in sorted(refs.items()):
                if not ref.startswith(("refs/heads/", "refs/remotes/")):
                    continue
                for entry in git(repo, "ls-tree", "-r", "-z", tip).split(b"\0"):
                    if not entry:
                        continue
                    attrs, name = entry.split(b"\t", 1)
                    _, kind, oid = attrs.decode().split()
                    if kind == "blob":
                        db.execute("INSERT INTO branch_files VALUES(?,?,?)",
                                   (ref, name.decode(), oid))
            if catalog:
                if external_root is None:
                    raise ValueError("EXTERNAL_SOURCE_ROOT_REQUIRED")
                external_root = Path(external_root).resolve()
                for item in catalog["items"]:
                    local = (external_root / item["path"].lstrip("/")).resolve()
                    if not local.is_relative_to(external_root):
                        raise ValueError("EXTERNAL_PATH_OUTSIDE_ROOT")
                    raw = local.read_bytes()
                    if item.get("size_bytes") is not None and len(raw) != item["size_bytes"]:
                        raise ValueError("EXTERNAL_SOURCE_SIZE_MISMATCH:" + item["path"])
                    limits = {key: item.get(key, default) for key, default in (
                        ("max_expanded_bytes", 128 * 1024 * 1024), ("max_member_bytes", 32 * 1024 * 1024))}
                    if any(type(v) is not int or not 1 <= v <= 512 * 1024 * 1024 for v in limits.values()):
                        raise ValueError("INVALID_EXTERNAL_SIZE_LIMIT")
                    _external(db, item["library_file_id"] + ":" + item["path"], raw, item, **limits)
            counts = {kind: count for kind, count in db.execute("SELECT kind,count(*) FROM git_objects GROUP BY kind")}
            counts.update({"unique_payloads": db.execute("SELECT count(*) FROM blobs").fetchone()[0],
                           "indexed_documents": db.execute("SELECT count(*) FROM documents").fetchone()[0],
                           "external_sources_and_members": db.execute("SELECT count(*) FROM external_sources").fetchone()[0],
                           "external_files": len(catalog["items"]) if catalog else 0,
                           "remote_branches": sum(k.startswith("refs/remotes/") for k in refs)})
            summary = {"schema": SCHEMA, "git_object_format": fmt, "refs": refs, "counts": counts,
                       "all_reachable_git_objects_archived": True,
                       "index_prefix_limit_chars": INDEX_TEXT_LIMIT,
                       "raw_payloads_complete": True,
                       "historical_statuses_are_reported_not_reverified": True,
                       "outside_scope": ["unreachable/deleted remote refs absent from this clone",
                                         "expired or uncommitted workflow artifacts", "unresolved conversation attachments"]}
            db.execute("INSERT INTO metadata VALUES('summary',?)", (canonical(summary),))
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("ARCHIVE_SQLITE_INTEGRITY_FAILURE")
        db.close()
        os.replace(temp_name, target)
        return summary
    except BaseException:
        db.close()
        Path(temp_name).unlink(missing_ok=True)
        raise


class ExperienceArchive:
    def __init__(self, path):
        self.path = Path(path).resolve()
        self.db = sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True)
        self.db.row_factory = sqlite3.Row
        self.summary = json.loads(self.db.execute("SELECT value FROM metadata WHERE key='summary'").fetchone()[0])
        if self.summary.get("schema") != SCHEMA:
            raise ValueError("ARCHIVE_SCHEMA_MISMATCH")

    def close(self):
        self.db.close()

    def read(self, digest):
        row = self.db.execute("SELECT size,payload FROM blobs WHERE digest=?", (digest,)).fetchone()
        if row is None:
            raise KeyError(digest)
        raw = zlib.decompress(row["payload"])
        if len(raw) != row["size"] or sha(raw) != digest:
            raise ValueError("ARCHIVE_PAYLOAD_INTEGRITY_FAILURE:" + digest)
        return raw

    def git_blob(self, oid):
        row = self.db.execute("SELECT digest FROM git_objects WHERE oid=? AND kind='blob'", (oid,)).fetchone()
        if row is None:
            raise KeyError(oid)
        return self.read(row[0])

    def search(self, query, limit=6):
        words = re.findall(r"[^\W_]+", str(query), re.UNICODE)[:12]
        if not words:
            return []
        match = " OR ".join('"' + word + '"' for word in words)
        rows = self.db.execute("""SELECT d.*,bm25(search_index) AS rank FROM search_index
            JOIN documents d ON d.id=search_index.rowid WHERE search_index MATCH ?
            ORDER BY rank,d.digest LIMIT ?""", (match, max(1, min(int(limit), 40))))
        return [{**dict(row), "evidence_level": "ARCHIVED_SOURCE_ASSERTION"} for row in rows]

    def verify(self):
        checked = 0
        for row in self.db.execute("SELECT digest FROM blobs ORDER BY digest"):
            self.read(row[0])
            checked += 1
        for row in self.db.execute("SELECT oid,kind,digest FROM git_objects"):
            raw = self.read(row["digest"])
            value = hashlib.new(self.summary["git_object_format"],
                                f"{row['kind']} {len(raw)}\0".encode() + raw).hexdigest()
            if value != row["oid"]:
                raise ValueError("ARCHIVE_GIT_IDENTITY_FAILURE")
        if self.db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("ARCHIVE_SQLITE_INTEGRITY_FAILURE")
        return {"status": "PASS", "payloads_verified": checked,
                "git_objects_verified": self.db.execute("SELECT count(*) FROM git_objects").fetchone()[0]}
