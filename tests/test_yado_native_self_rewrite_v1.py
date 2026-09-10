"""Behavior, provenance and rejection tests for native-only proposal routing."""
from pathlib import Path
import copy, hashlib, json, socket, subprocess, sys, tempfile, unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO/'runtime'), str(REPO/'runtime/yado_rc8_v36')]
from yado_g2_goal_action_binding_v1 import YADOGoalActionBindingV1 as Binder
from yado_g2_native_semantic_ast_backend_v1 import load_bundle, materialize_source, propose
from yado_g2_autonomous_self_rewrite_v1 import run, latest_audit, canonical_snapshot, main


class NativeSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.request = json.loads((REPO/'architecture/yado-kernel-autonomous-self-improvement-v1-request.json').read_text())
        cls.audit = latest_audit(REPO)[1]
        cls.bundle = load_bundle(REPO)
        # Immutable spent historical source, not a target/template for the fresh goal.
        cls.parent = subprocess.check_output([
            'git','show','0565a6d46d35302d5db907878a6dbbb154452b02:runtime/yado_unified_core_deep_self_audit_v1.py'
        ],cwd=REPO).decode()

    def test_fresh_goal_reaches_priority(self):
        intake = Binder.resolve_goal(self.request, self.audit)
        self.assertEqual(intake['priority'][0]['code'], self.request['task']['task_id'])
        self.assertEqual(intake['priority'][0]['recommended_action'], self.request['task']['goal'])
        self.assertEqual(intake['deferred_self_audit'], self.audit['self_selected_priority'])

    def test_lexical_match_is_not_external_action_coverage(self):
        request = copy.deepcopy(self.request)
        request['task']['task_id'] = 'FRESH-UNSEEN-41'
        request['task']['goal'] = 'experience memory legacy provenance history evidence retrieval'
        priority = Binder.resolve_goal(request, self.audit)['priority'][0]
        selected = Binder.select_action(priority)
        self.assertEqual(selected['ranking'][0]['action_id'], 'EXPERIENCE_EVIDENCE_REVIEW')
        self.assertGreater(selected['ranking'][0]['score'], 0)
        self.assertIsNone(selected['selected_action'])
        self.assertEqual(selected['missing_capability'], request['task']['task_id'])

    def test_second_goal_is_bound_without_changing_intake_code(self):
        request = copy.deepcopy(self.request)
        request['task'].update(task_id='FRESH-UNSEEN-42',goal='Summarize a new local sensor dataset.')
        first = Binder.resolve_goal(self.request, self.audit)
        second = Binder.resolve_goal(request, self.audit)
        self.assertNotEqual(first['request_digest'], second['request_digest'])
        self.assertEqual(second['priority'][0]['code'], 'FRESH-UNSEEN-42')

    def test_audit_blocker_keeps_precedence_and_retains_goal(self):
        audit = copy.deepcopy(self.audit)
        audit['self_selected_priority'].append({'code':'INTEGRITY_FAILURE','blocking':True})
        got = Binder.resolve_goal(self.request,audit)
        self.assertEqual(got['priority'][0]['code'],'INTEGRITY_FAILURE')
        self.assertEqual(got['deferred_external_goal'],self.request['task'])

    def test_blocker_in_findings_is_not_lost(self):
        audit = copy.deepcopy(self.audit)
        audit['findings'].append({'code':'LEDGER_FAILURE','blocking':True})
        self.assertEqual(Binder.resolve_goal(self.request,audit)['priority'][0]['code'],'LEDGER_FAILURE')

    def test_no_external_task_preserves_legacy_behavior(self):
        got = Binder.resolve_goal({},self.audit)
        self.assertEqual(got['priority'],self.audit['self_selected_priority'])
        self.assertEqual(Binder.select_action(got['priority'][0])['selected_action'],'EXPERIENCE_EVIDENCE_REVIEW')

    def test_malformed_task_never_falls_back(self):
        for value in ({},None,'deploy',{'task_id':'x','goal':''}):
            request = copy.deepcopy(self.request)
            request['task'] = value
            got = Binder.resolve_goal(request,self.audit)
            self.assertEqual(got['status'],'WITHHOLD_INVALID_EXTERNAL_GOAL', value)
            self.assertEqual(got['priority'],[])

    def test_native_ast_replay_matches_historical_bytes(self):
        source = materialize_source(self.bundle,self.parent)
        compile(source,'<native-historical-replay>','exec')
        self.assertNotEqual(source,self.parent)
        self.assertEqual(hashlib.sha256(source.encode()).hexdigest(),self.bundle['historical_candidate_sha256'])

    def test_parent_drift_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'PARENT_SOURCE_DRIFT'):
            materialize_source(self.bundle,self.parent+'\n')

    def test_unbound_context_is_rejected(self):
        bundle = copy.deepcopy(self.bundle)
        bundle['context']['full_free_context_names'] = ['feat']
        with self.assertRaisesRegex(RuntimeError,'FREE_CONTEXT_MISMATCH'):
            materialize_source(bundle,self.parent)

    def test_gene_digest_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for relative in self.bundle['lineage_sha256']:
                dest = root/relative
                dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_bytes((REPO/relative).read_bytes())
            path = root/'candidates/kernel-self-generated/g2-native-contextual-ast-operand-materialization-gene-v12.json'
            obj = json.loads(path.read_text())
            obj['materialized_ifexp_source'] = "'PASS'"
            path.write_text(json.dumps(obj))
            with self.assertRaisesRegex(ValueError,'LINEAGE_DIGEST_MISMATCH'):
                load_bundle(root)

    def test_unknown_goal_does_not_receive_old_audit_patch(self):
        priority = Binder.resolve_goal(self.request,self.audit)['priority'][0]
        proposal = propose(REPO,priority)
        self.assertEqual(proposal['status'],'WITHHOLD_NO_NATIVE_SEMANTIC_OPERATOR_FOR_GOAL')
        self.assertIsNone(proposal['candidate_source'])
        self.assertIsNone(proposal['target_path'])

    def test_current_context_withhold_is_not_overridden_by_historical_pass(self):
        result = propose(REPO,{'code':self.bundle['anchor']['finding_code']})
        self.assertEqual(result['status'],'WITHHOLD_CURRENT_NATIVE_CONTEXT_NOT_VALIDATED')
        self.assertIsNone(result['candidate_source'])

    def test_native_run_with_network_disabled_preserves_canonical_bytes(self):
        before = canonical_snapshot(REPO)
        with patch.object(socket.socket,'connect',side_effect=AssertionError('NETWORK_FORBIDDEN')) as network:
            report = run(REPO,'offline-provenance-test')
        network.assert_not_called()
        self.assertEqual(report['kernel_selected_priority']['code'],self.request['task']['task_id'])
        self.assertEqual(report['native_goal']['objective'],self.request['task']['goal'])
        self.assertEqual(report['kernel_selection']['selected_count'],0)
        self.assertFalse(report['external_models_used'])
        self.assertIsNone(report['candidate_path'])
        self.assertTrue(report['inputs_unchanged'])
        self.assertTrue(report['canonical_head_unchanged'])
        self.assertEqual(before,canonical_snapshot(REPO))

    def test_failed_run_replaces_stale_pass_with_current_withhold(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)/'result.json'
            out.write_text('{"status":"PASS","candidate_path":"old.py"}')
            code = main(['--repo',td,'--output',str(out),'--run-id','fresh-failure'])
            result = json.loads(out.read_text())
            self.assertEqual(code,2)
            self.assertEqual(result['run_id'],'fresh-failure')
            self.assertTrue(result['status'].startswith('WITHHOLD_'))
            self.assertIsNone(result['candidate_path'])


if __name__ == '__main__':
    unittest.main()
