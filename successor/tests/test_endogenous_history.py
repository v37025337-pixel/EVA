from __future__ import annotations

import json
import unittest

from successor.endogenous_run import _pressure, _verified_endogenous_history


class _Archive:
    def __init__(self, documents):
        self._docs = documents

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
    def __init__(self, documents):
        self.archive = _Archive(documents)


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
        "regression": {"status": "PASS", "tests_run": 197},
        "kernel_audit": {"status": "PASS" if audit else "FAIL", "findings": [] if audit else ["x"]},
        "canonical_mutation": canonical_mutation,
    }


class VerifiedEndogenousHistoryTests(unittest.TestCase):
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
