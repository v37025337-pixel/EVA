"""Persistence invariants with real SQLite connections and explicit oracles."""
import copy
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from successor.archive import sha
from successor.cognitive import replay, goal_context, split_examples
from successor.kernel import SuccessorKernel, encode, fingerprint
from yado_active_native_learning_v1 import source_sha


def kernel_connection(path):
    # Exercise the real journal/queue methods independently of archive assembly.
    kernel = SuccessorKernel.__new__(SuccessorKernel)
    kernel.manifest = {"inherited_files": {}, "assembly_sources": {}}
    kernel.repo = Path(__file__).resolve().parents[2]
    kernel.identity = kernel.implementation_identity = "test-state-identity"
    kernel.parent = SimpleNamespace(head={"generation_id": "G2", "active_capabilities": []})
    kernel.archive = SimpleNamespace(summary={"counts": {}})
    kernel.db = sqlite3.connect(path, isolation_level=None)
    kernel.db.row_factory = sqlite3.Row
    kernel.db.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS identity(id INTEGER PRIMARY KEY, digest TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events(tick INTEGER PRIMARY KEY, previous_hash TEXT NOT NULL,
            body TEXT NOT NULL, event_hash TEXT NOT NULL UNIQUE);
        CREATE TABLE IF NOT EXISTS jobs(id INTEGER PRIMARY KEY, goal TEXT NOT NULL, task TEXT NOT NULL,
            state TEXT NOT NULL DEFAULT 'PENDING', result_tick INTEGER REFERENCES events(tick));
    """)
    return kernel


def relation_records(answer=(1, 2), passed=True):
    spec = {"domain": "relation", "relation": [[1, 2]], "start": 1}
    choice = {"strategy": "native_logic", "cost": 1, "probability": .5}
    workspace = {"goal_digest": fingerprint(spec), "remaining_budget": 1, "proposals": [choice]}
    digest = fingerprint(workspace)
    result = {"status": "CANDIDATE", "answer": list(answer)}
    records = [
        {"kind": "COG_GOAL", "spec": spec, "spec_digest": fingerprint(spec), "budget": 1, "mode": "full"},
        {"kind": "COG_DECIDE", "goal_id": 1, "choice": choice, "workspace": workspace, "workspace_digest": digest},
        {"kind": "COG_EXECUTE", "goal_id": 1, "decision_tick": 2, "workspace_digest": digest, "result": result},
        {"kind": "COG_VERIFY", "goal_id": 1, "execution_tick": 3, "workspace_digest": digest,
         "passed": passed, "checks": 1, "scope": "INDEPENDENT_TRANSITIVE_CLOSURE", "evidence": {}},
        {"kind": "COG_REFLECT", "goal_id": 1, "verification_tick": 4, "success": passed,
         "domain": "relation", "strategy": "native_logic", "cost": 1, "brier_error": .25,
         "workspace_digest": digest},
        {"kind": "COG_FINISH", "goal_id": 1, "status": "VERIFIED" if passed else "WITHHOLD",
         "result": copy.deepcopy(result) if passed else None, "spent": 1},
    ]
    return [{**r, "tick": i, "event_hash": str(i) * 64} for i, r in enumerate(records, 1)]


def candidate_records(spec, strategy, cost, result, verification):
    records = relation_records()
    records[0].update(spec=spec, spec_digest=fingerprint(spec), budget=cost)
    choice = {"strategy": strategy, "cost": cost, "probability": .5}
    workspace = {"goal_digest": fingerprint(spec), "remaining_budget": cost, "proposals": [choice]}
    digest = fingerprint(workspace)
    records[1].update(choice=choice, workspace=workspace, workspace_digest=digest)
    records[2].update(result=result, workspace_digest=digest)
    records[3].update(**verification, workspace_digest=digest)
    passed = verification['passed']
    records[4].update(success=passed, domain=spec['domain'], strategy=strategy,
                      cost=cost, workspace_digest=digest, context=goal_context(spec))
    status = ('VALIDATED_ON_HOLDOUT' if spec['domain'] in {'numeric', 'native_source'} else 'VERIFIED') if passed else 'WITHHOLD'
    records[5].update(status=status, result=copy.deepcopy(result) if passed else None, spent=cost)
    return records


class StateSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "state.sqlite"
        self.reader = kernel_connection(self.path)
        self.writer = kernel_connection(self.path)

    def tearDown(self):
        self.reader.db.close()
        self.writer.db.close()
        self.tmp.cleanup()

    def test_concurrent_valid_submission_does_not_look_like_corruption(self):
        fired = []
        def commit_during_read(sql):
            if sql == "SELECT count(*) FROM jobs" and not fired:
                fired.append(True)
                self.writer.submit("concurrent goal", [{"kind": "audit"}])
        self.reader.db.set_trace_callback(commit_during_read)
        result = self.reader.verify_state()
        self.reader.db.set_trace_callback(None)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["tick"], 0)
        self.assertEqual(self.reader.verify_state()["tick"], 1)

    def test_snapshot_result_counts_and_integrity_share_one_version(self):
        fired = []
        def commit_before_integrity(sql):
            if sql == "SELECT * FROM events ORDER BY tick" and not fired:
                fired.append(True)
                self.writer.submit("later goal", [{"kind": "audit"}])
        self.reader.db.set_trace_callback(commit_before_integrity)
        result = self.reader.snapshot()
        self.reader.db.set_trace_callback(None)
        self.assertEqual(result["state_integrity"]["tick"], 0)
        self.assertEqual(result["jobs"], {})
        self.assertIsNone(result["last_result"])
        self.assertEqual(self.reader.snapshot()["jobs"], {"PENDING": 1})

    def test_validation_never_commits_or_rolls_back_callers_transaction(self):
        self.reader.db.execute("BEGIN IMMEDIATE")
        self.reader._append({"kind": "OBSERVATION"})
        self.assertEqual(self.reader.verify_state()["tick"], 1)
        self.assertTrue(self.reader.db.in_transaction)
        self.reader.db.execute("UPDATE events SET body='{}' WHERE tick=1")
        with self.assertRaisesRegex(ValueError, "CAUSAL_HISTORY_INTEGRITY_FAILURE"):
            self.reader.verify_state()
        self.assertTrue(self.reader.db.in_transaction)
        self.reader.db.execute("ROLLBACK")
        self.assertEqual(self.reader.verify_state()["tick"], 0)

    def test_stale_connection_cannot_poison_a_new_active_lineage(self):
        from successor.lineage import ConsecutiveLineage, REQUEST
        self.writer.verify_state()
        self.assertFalse(self.writer._lineage_present)
        ConsecutiveLineage(self.reader).start('test', 'YA-1', REQUEST)
        before = self.reader.verify_state()
        with self.assertRaisesRegex(ValueError, 'LINEAGE_UNRELATED_OR_OUT_OF_ORDER_EVENT'):
            self.writer.submit('unrelated concurrent goal', [{'kind': 'audit'}])
        self.assertEqual(self.reader.verify_state(), before)
        self.assertEqual(self.writer.verify_state(), before)
        self.assertEqual(self.writer.db.execute('SELECT count(*) FROM jobs').fetchone()[0], 0)

    def test_rehashed_wrong_answer_cannot_pass_journal_verification(self):
        previous = "0" * 64
        for record in relation_records(answer=[999]):
            body = {k: v for k, v in record.items() if k not in {"tick", "event_hash"}}
            raw = encode(body)
            digest = sha((previous + "\n" + str(record["tick"]) + "\n" + raw).encode())
            self.reader.db.execute("INSERT INTO events VALUES(?,?,?,?)", (record["tick"], previous, raw, digest))
            previous = digest
        with self.assertRaisesRegex(ValueError, "COGNITIVE_VERIFICATION_RESULT"):
            self.reader.verify_state()


class CognitiveSemanticReplayTests(unittest.TestCase):
    def test_wrong_answer_cannot_become_verified_by_a_true_flag(self):
        for records in (relation_records(answer=[999]), relation_records(answer=[1])):
            with self.subTest(records=records[2]["result"]):
                with self.assertRaisesRegex(ValueError, "COGNITIVE_VERIFICATION_RESULT"):
                    replay(records)

    def test_correct_and_honestly_failed_legacy_records_remain_valid(self):
        self.assertEqual(replay(relation_records())[1]["status"], "VERIFIED")
        self.assertEqual(replay(relation_records(answer=[999], passed=False))[1]["status"], "WITHHOLD")

    def test_successful_cache_entry_does_not_hide_changed_verification(self):
        records = relation_records()
        replay(records)
        for field, value in (("checks", 100), ("scope", "UNSUPPORTED_PROOF"), ("evidence", {"invented": True})):
            damaged = copy.deepcopy(records)
            damaged[3][field] = value
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, "COGNITIVE_VERIFICATION_RESULT"):
                    replay(damaged)

    def test_native_and_numeric_prediction_labels_are_rechecked(self):
        from yado_active_native_learning_v1 import synthesize_source
        spec = {'domain': 'native_source',
                'training': [{'input': {'text': x}, 'expected': x[::-1]} for x in ('abc', 'def', 'gh')],
                'validation': [{'input': {'text': x}, 'expected': x[::-1]} for x in ('ijk', 'lm')],
                'queries': [{'input': {'text': 'nop'}}]}
        source = synthesize_source(spec['training'], 'native_v3')['source']
        result = {'status': 'CANDIDATE', 'source': source, 'source_sha256': source_sha(source),
                  'source_context': goal_context(spec), 'training_predictions': ['cba', 'fed', 'hg'],
                  'validation_predictions': ['kji', 'ml'], 'predictions': ['pon']}
        verification = {'passed': True, 'checks': 2,
                        'scope': 'INDEPENDENT_VALIDATION_LABELS_AFTER_SOURCE_FREEZE',
                        'evidence': {'source_sha256': source_sha(source)}}
        records = candidate_records(spec, 'native_v3', 2, result, verification)
        self.assertEqual(replay(records)[1]['status'], 'VALIDATED_ON_HOLDOUT')
        damaged = copy.deepcopy(records)
        damaged[2]['result']['validation_predictions'][0] = 999
        damaged[5]['result'] = copy.deepcopy(damaged[2]['result'])
        with self.assertRaisesRegex(ValueError, 'COGNITIVE_VERIFICATION_RESULT'):
            replay(damaged)
        spec = {'domain': 'numeric', 'rows': [{'x': x, 'y': y, 'expected': x + y}
                                             for x in range(4) for y in range(4)],
                'queries': [{'x': 9, 'y': 9}]}
        holdout = split_examples(spec['rows'])[1]
        result = {'status': 'CANDIDATE', 'holdout_predictions': [r['expected'] for r in holdout], 'predictions': [18]}
        verification = {'passed': True, 'checks': len(holdout), 'scope': 'INDEPENDENT_HELD_OUT_LABELS', 'evidence': {}}
        records = candidate_records(spec, 'polynomial_1', 1, result, verification)
        self.assertEqual(replay(records)[1]['status'], 'VALIDATED_ON_HOLDOUT')
        records[2]['result']['holdout_predictions'][0] = 999
        records[5]['result'] = copy.deepcopy(records[2]['result'])
        with self.assertRaisesRegex(ValueError, 'COGNITIVE_VERIFICATION_RESULT'):
            replay(records)

    def test_error_result_cannot_be_declared_successful(self):
        records = relation_records()
        records[2]['result'] = {'status': 'ERROR', 'error_type': 'RuntimeError', 'error': 'execution failed'}
        records[5]['result'] = copy.deepcopy(records[2]['result'])
        with self.assertRaisesRegex(ValueError, 'COGNITIVE_VERIFICATION_RESULT'):
            replay(records)

    def test_library_receipts_are_bound_offline_and_failures_stay_valid(self):
        from yado_autonomous_external_library_discovery_v5 import sha_json
        spec = {'domain': 'library_discovery', 'objective': 'html_xml_parser'}
        bundle = {'package': 'example', 'filename': 'example.whl', 'artifact_sha256': 'a' * 64}
        result = {'status': 'CANDIDATE', 'bundle': bundle, 'bundle_sha256': sha_json(bundle),
                  'artifact': {'expected_sha256': bundle['artifact_sha256']}}
        proof = {'source': {'url': 'https://pypi.org/simple/example/'}, 'filename': bundle['filename'],
                 'sha256': bundle['artifact_sha256'], 'matched': True, 'selection_data_used': False}
        evidence = {'passed': True, 'scope': 'SEPARATE_PYPI_SIMPLE_AFTER_BUNDLE_FREEZE', 'checks': 1, 'proof': proof}
        verification = {'passed': True, 'checks': 1, 'scope': evidence['scope'], 'evidence': evidence}
        records = candidate_records(spec, 'catalog_v6', 4, result, verification)
        with patch('yado_autonomous_external_library_discovery_v5.fetch_json', side_effect=AssertionError('network replay forbidden')):
            self.assertEqual(replay(records)[1]['status'], 'VERIFIED')
            damaged = copy.deepcopy(records)
            damaged[3]['evidence']['proof']['filename'] = 'different.whl'
            with self.assertRaisesRegex(ValueError, 'COGNITIVE_VERIFICATION_RESULT'):
                replay(damaged)
            failure = {'passed': False, 'checks': 0, 'scope': 'LIBRARY_VALIDATION_ERROR',
                       'evidence': {'error_type': 'OSError', 'error': 'offline'}}
            failed = candidate_records(spec, 'catalog_v6', 4, result, failure)
            self.assertEqual(replay(failed)[1]['status'], 'WITHHOLD')

    def test_boolean_node_does_not_impersonate_numeric_node(self):
        with self.assertRaisesRegex(ValueError, 'COGNITIVE_VERIFICATION_RESULT'):
            replay(relation_records(answer=[True, 2]))


if __name__ == "__main__":
    unittest.main()
