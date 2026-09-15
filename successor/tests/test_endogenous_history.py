from __future__ import annotations

import json
import unittest

from successor.endogenous_run import _pressure, _verified_endogenous_history


class _Archive:
    def __init__(self, documents, admitted_digests=None):
        self._docs = documents
        self.admitted_digests = {row[0] for row in documents} if admitted_digests is None else admitted_digests
        self.summary = {"refs": {"refs/remotes/origin/main": "f" * 40}}

    def files_at_ref(self, ref, prefix, limit=40):
        assert ref == "refs/remotes/origin/main"
        return [row for row in self.search("", limit) if row["digest"] in self.admitted_digests and row["path"].startswith(prefix)]

    def search(self, query, limit=40):
        return [
            {"digest": digest, "path": path, "reported_outcome": "PASS"}
            for digest, path, _ in self._docs[:limit]
        ]

    def read(self, digest):
        for candidate, _, data in self._docs:
            if candidate == digest:
                return json.dumps(data).encode()
        raise KeyError(digest)


class _Kernel:
    def __init__(self, documents, admitted_digests=None):
        self.archive = _Archive(documents, admitted_digests)
        self.manifest = {"parent_main_commit": "f" * 40}


def _receipt(*, cycles=20, events=10, relation=10, audit=True, canonical_mutation=False):
    return {
        "schema": "yado.active_native_loop.applied_experience.v1",
        "status": "PASS_APPLIED_VERIFIED_ENDOGENOUS_EXPERIENCE_V1",
        "source_run_id": 123,
        "endogenous": {
            "status": "PASS_BOUNDED_ENDOGENOUS_CONTINUATION_V1",
            "cycles_completed": cycles,
            "cycles_verified": cycles,
            "host_goal_count": 0,
            "domain_counts": {"events": events, "relation": relation},
        },
        "regression": {"status": "PASS", "tests_run": 197, "expected_tests": 197,
                       "failures": 0, "errors": 0, "skipped": 0, "source_unchanged": True},
        "kernel_audit": {"status": "PASS" if audit else "FAIL", "findings": [] if audit else ["x"]},
        "canonical_mutation": canonical_mutation,
    }


class VerifiedEndogenousHistoryTests(unittest.TestCase):
    def test_candidate_branch_receipt_is_not_admitted_history(self):
        kernel = _Kernel([("a" * 64, "receipts/yado-active-native-loop-candidate.json", _receipt())], admitted_digests=set())
        self.assertEqual(_verified_endogenous_history(kernel)["verified_cycles"], 0)

    def test_missing_or_mismatched_pinned_main_cannot_admit_history(self):
        for commit in (None, "e" * 40):
            kernel = _Kernel([("a" * 64, "receipts/yado-active-native-loop-test.json", _receipt())])
            kernel.manifest["parent_main_commit"] = commit
            with self.subTest(commit=commit):
                self.assertEqual(_verified_endogenous_history(kernel)["verified_cycles"], 0)

    def test_malformed_or_contradictory_receipts_are_ignored(self):
        mutations = [
            ("endogenous", "cycles_verified", "invalid"),
            ("endogenous", "domain_counts", []),
            ("endogenous", "domain_counts", {"events": True, "relation": 19}),
            ("regression", "tests_run", "197"),
            ("regression", "failures", 1),
            ("regression", "errors", 1),
            ("regression", "skipped", 1),
            ("regression", "expected_tests", 198),
            ("regression", "source_unchanged", False),
        ]
        for section, field, value in mutations:
            data = _receipt()
            data[section][field] = value
            kernel = _Kernel([("a" * 64, "receipts/yado-active-native-loop-test.json", data)])
            with self.subTest(section=section, field=field, value=value):
                self.assertEqual(_verified_endogenous_history(kernel)["verified_cycles"], 0)

    def test_one_source_run_is_counted_once(self):
        kernel = _Kernel([
            ("a" * 64, "receipts/yado-active-native-loop-one.json", _receipt()),
            ("b" * 64, "receipts/yado-active-native-loop-copy.json", _receipt()),
        ])
        self.assertEqual(_verified_endogenous_history(kernel)["verified_cycles"], 20)

    def test_accepts_only_fully_gated_receipt(self):
        good = _receipt()
        bad_audit = _receipt(audit=False)
        bad_path = _receipt()
        kernel = _Kernel([
            ("a" * 64, "receipts/yado-active-native-loop-good-applied.json", good),
            ("b" * 64, "receipts/yado-active-native-loop-bad-applied.json", bad_audit),
            ("c" * 64, "architecture/not-an-admitted-receipt.json", bad_path),
        ])
        history = _verified_endogenous_history(kernel)
        self.assertEqual(history["accepted_receipt_count"], 1)
        self.assertEqual(history["verified_cycles"], 20)
        self.assertEqual(history["domain_counts"], {"relation": 10, "events": 10})
        self.assertEqual(history["receipt_digests"], ["a" * 64])

    def test_rejects_inconsistent_domain_counts_and_canonical_mutation(self):
        inconsistent = _receipt(cycles=20, events=9, relation=10)
        mutated = _receipt(canonical_mutation=True)
        kernel = _Kernel([
            ("d" * 64, "receipts/yado-active-native-loop-inconsistent-applied.json", inconsistent),
            ("e" * 64, "receipts/yado-active-native-loop-mutated-applied.json", mutated),
        ])
        history = _verified_endogenous_history(kernel)
        self.assertEqual(history["accepted_receipt_count"], 0)
        self.assertEqual(history["verified_cycles"], 0)

    def test_historical_success_reduces_redundant_domain_pressure(self):
        snapshot = {"all_observations": {}}
        fresh = _pressure(snapshot, "events", historical_successes=0)
        experienced = _pressure(snapshot, "events", historical_successes=20)
        self.assertLess(experienced, fresh)


if __name__ == "__main__":
    unittest.main()
