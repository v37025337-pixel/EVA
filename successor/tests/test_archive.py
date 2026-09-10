import json
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest
import zlib

from successor.archive import ExperienceArchive, build_archive, git, sha


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.repo)], check=True)
        git(self.repo, "config", "user.name", "Archive test")
        git(self.repo, "config", "user.email", "archive-test@example.invalid")
        (self.repo / "experience").mkdir()
        self.raw = b'{"status":"FAIL_PRIOR_ATTEMPT","lesson":"retain causal error"}\n'
        (self.repo / "experience/run.json").write_bytes(self.raw)
        self.oid = git(self.repo, "hash-object", "experience/run.json").decode().strip()
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "original failure")
        git(self.repo, "checkout", "-qb", "repair")
        (self.repo / "experience/run.json").write_text('{"status":"PASS_SHADOW","lesson":"repair"}\n')
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "later repair")
        git(self.repo, "checkout", "-q", "main")
        (self.repo / "experience/run.json").unlink()
        (self.repo / "current.txt").write_text("current state")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "file removed from current tree")
        self.target = self.root / "archive.sqlite"

    def tearDown(self):
        self.tmp.cleanup()

    def test_deleted_history_and_all_branches_have_exact_bytes(self):
        report = build_archive(self.repo, self.target)
        self.assertEqual(report["counts"]["commit"], 3)
        archive = ExperienceArchive(self.target)
        self.addCleanup(archive.close)
        self.assertEqual(archive.git_blob(self.oid), self.raw)
        self.assertEqual(set(archive.summary["refs"]), {"refs/heads/main", "refs/heads/repair"})
        results = archive.search("causal error")
        self.assertTrue(any(r["reported_outcome"] == "FAIL" for r in results))
        self.assertTrue(all(r["evidence_level"] == "ARCHIVED_SOURCE_ASSERTION" for r in results))
        self.assertEqual(archive.verify()["status"], "PASS")

    def test_missing_external_source_aborts_without_partial_snapshot(self):
        catalog = {"items": [{"path": "/missing.json", "library_file_id": "test-source"}]}
        with self.assertRaises(FileNotFoundError):
            build_archive(self.repo, self.target, external_root=self.root, catalog=catalog)
        self.assertFalse(self.target.exists())

    def test_tampered_bytes_are_detected(self):
        build_archive(self.repo, self.target)
        with sqlite3.connect(self.target) as db:
            db.execute("UPDATE blobs SET payload=? WHERE digest=?", (zlib.compress(b"forged"), sha(self.raw)))
        archive = ExperienceArchive(self.target)
        self.addCleanup(archive.close)
        with self.assertRaisesRegex(ValueError, "INTEGRITY_FAILURE"):
            archive.git_blob(self.oid)

    def test_large_document_index_limit_does_not_truncate_source(self):
        raw = ("large body " * 22000).encode()
        (self.repo / "large.txt").write_bytes(raw)
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "large source")
        oid = git(self.repo, "hash-object", "large.txt").decode().strip()
        build_archive(self.repo, self.target)
        archive = ExperienceArchive(self.target)
        self.addCleanup(archive.close)
        self.assertEqual(archive.git_blob(oid), raw)
        self.assertLess(archive.search("large body", 1)[0]["indexed_chars"], len(raw))

    def test_existing_snapshot_cannot_be_replaced_accidentally(self):
        build_archive(self.repo, self.target)
        with self.assertRaises(FileExistsError):
            build_archive(self.repo, self.target)

    def test_shallow_clone_is_not_claimed_as_complete(self):
        shallow = self.root / "shallow"
        subprocess.run(["git", "clone", "-q", "--depth=1", self.repo.as_uri(), str(shallow)], check=True)
        with self.assertRaisesRegex(ValueError, "SHALLOW_HISTORY"):
            build_archive(shallow, self.target)


if __name__ == "__main__":
    unittest.main()
