"""Observe a pinned predecessor, continuity upgrade and native composition.

The maintainer supplies the language implementation, acceptance tasks and this
finite harness. The kernel selects and emits each program from training only.
The predecessor is reproduced in CI; this does not claim that an unavailable
historical binary artifact has been restored.
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'runtime'), str(ROOT / 'runtime/yado_rc8_v36')]

from successor.archive import file_sha
from successor.cognitive import CognitiveLoop, replay
from successor.compositional_source import execute, synthesize
from successor.continuity import prepare_upgrade
from successor.generation import retained_memory
from successor.kernel import SuccessorKernel, decode
from successor.program_goals import SCHEMA as GOAL_SCHEMA, validate_goal as validate_program_goal
from yado_active_kernel_contract_v1 import active_kernel_identity
from yado_active_native_learning_v1 import validate_source_goal

PREDECESSOR_COMMIT = '2cc9c296137b1e9d7648ba341578725e9ae01123'


def save(out, name, value):
    (out / (name + '.json')).write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')
    print('YADO_EVIDENCE ' + json.dumps({'name': name, 'value': value}, sort_keys=True), flush=True)


def source(out, name, candidate):
    filename = name + '.py'
    (out / filename).write_text(candidate['source'])
    print('YADO_GENERATED_SOURCE ' + json.dumps({'name': filename, 'source': candidate['source']}), flush=True)


def journal(kernel):
    return [dict(row) for row in kernel.db.execute(
        'SELECT tick,previous_hash,body,event_hash FROM events ORDER BY tick')]


def all_goals(kernel):
    return replay(CognitiveLoop(kernel)._records())


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def serializer(message):
    return compact({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                    'params': {'name': 'hive_add_comment',
                               'arguments': {'id': 'YADO-1', 'message': message}}})


def original_tasks():
    path = ROOT / 'experiments/native-gap-repair-20260919/run.py'
    spec = importlib.util.spec_from_file_location('recorded_native_gap_tasks', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.fixtures()


def lineage_tasks():
    """Independent task data, including disjoint holdout and unseen queries."""
    tasks = []
    transforms = [
        ('serialized_message_length', lambda message: len(serializer(message)), False),
        ('structured_message_measurement', lambda message: {'serialized_size': len(serializer(message)), 'input': message}, True),
        ('serialized_measurement_record', lambda message: compact({'serialized_size': len(serializer(message)), 'input': message}), True),
    ]
    for index, (name, oracle, structured) in enumerate(transforms, start=2):
        values = [f'g{index}: plain', f'g{index}: "quoted"', f'g{index}: line\nnext',
                  f'g{index}: данные 😀', f'g{index}: back\\slash',
                  f'g{index}: tab\t雪', f'g{index}: final "ok"\n\\']
        inputs = [{'message': value} for value in values]
        spec = {'domain': 'native_source',
                'training': [{'input': row, 'expected': oracle(row['message'])} for row in inputs[:3]],
                'validation': [{'input': row, 'expected': oracle(row['message'])} for row in inputs[3:5]],
                'queries': [{'input': row} for row in inputs[5:]]}
        if structured:
            spec['schema'] = GOAL_SCHEMA
            validate_program_goal(spec)
        else:
            validate_source_goal(spec)
        tasks.append({'name': name, 'spec': spec,
                      'observer_query_expected': [oracle(row['message']) for row in inputs[5:]],
                      'acceptance_task_authorship': 'MAINTAINER',
                      'candidate_solution_source_supplied': False})
    return tasks


def preflight():
    tasks = original_tasks()
    parents = []
    for task in tasks:
        candidate = synthesize(task['spec']['training'])
        assert candidate.get('source'), (task['name'], candidate)
        assert execute(candidate, [row['input'] for row in task['spec']['queries']]) == task['observer_query_expected']
        if task['name'] == 'mcp_comment_serialization':
            parents.append(candidate)
    for task in lineage_tasks():
        candidate = synthesize(task['spec']['training'], memories=list(reversed(parents)))
        assert candidate.get('source'), (task['name'], candidate)
        assert candidate['parent_source_sha256'] == [parents[-1]['source_sha256']]
        assert execute(candidate, [row['input'] for row in task['spec']['queries']]) == task['observer_query_expected']
        parents.append(candidate)
    print(json.dumps({'status': 'FIXTURE_PREFLIGHT_PASS', 'program_lineage_length': len(parents),
                      'scope': 'DIRECT_GENERATOR_PREFLIGHT_NOT_KERNEL_UPGRADE_EVIDENCE'}))


def real_patch_check(out, candidate):
    """The learned diff program writes patch bytes; the harness applies/checks."""
    before = 'def add(x, y):\n    return x - y\n'
    after = 'def add(x, y):\n    return x + y\n'
    patch_text = execute(candidate, [{'before': before, 'after': after}])[0]
    (out / 'kernel-emitted-addition.patch').write_text(patch_text)
    check = 'import target; assert target.add(7, 2) == 9; assert target.add(-4, 5) == 1; assert target.add(0, 0) == 0'
    with tempfile.TemporaryDirectory(prefix='yado-emitted-patch-') as directory:
        cwd = Path(directory)
        subprocess.run(['git', 'init', '-q'], cwd=cwd, check=True, timeout=20)
        (cwd / 'target.py').write_text(before)
        failed = subprocess.run([sys.executable, '-B', '-c', check], cwd=cwd, text=True,
                                capture_output=True, timeout=20)
        assert failed.returncode != 0 and 'AssertionError' in failed.stderr
        checked = subprocess.run(['git', 'apply', '--check', '-'], cwd=cwd, input=patch_text,
                                 text=True, capture_output=True, timeout=20)
        assert checked.returncode == 0, checked.stderr
        applied = subprocess.run(['git', 'apply', '-'], cwd=cwd, input=patch_text,
                                 text=True, capture_output=True, timeout=20)
        assert applied.returncode == 0, applied.stderr
        assert (cwd / 'target.py').read_text() == after
        passed = subprocess.run([sys.executable, '-B', '-c', check], cwd=cwd, text=True,
                                capture_output=True, timeout=20)
        assert passed.returncode == 0, passed.stderr
    result = {'status': 'PASS', 'candidate_source_sha256': candidate['source_sha256'],
              'patch_sha256': file_sha(out / 'kernel-emitted-addition.patch'), 'patch': patch_text,
              'before_source': before, 'after_source': after, 'before_test_exit_code': failed.returncode,
              'git_apply_check_exit_code': checked.returncode, 'git_apply_exit_code': applied.returncode,
              'after_test_exit_code': passed.returncode, 'independent_assertion_count': 3,
              'scope': 'REAL_TEMPORARY_LOCAL_REPOSITORY',
              'patch_bytes_author': 'KERNEL_LEARNED_PROGRAM',
              'desired_change_and_acceptance_task_author': 'MAINTAINER',
              'bug_fix_algorithm_invented_by_kernel': False,
              'external_repository_written': False}
    save(out, 'real_patch_check', result)
    return result


def main(predecessor, out):
    out.mkdir(parents=True, exist_ok=False)
    save(out, 'summary', {'status': 'WITHHOLD_INCOMPLETE_RUN'})
    stage = 'PREDECESSOR_VALIDATION'
    try:
        parent_manifest = predecessor / 'birth/manifest.json'
        parent_state = predecessor / 'state.sqlite'
        parent = json.loads(parent_manifest.read_text())
        old_request = json.loads((predecessor / 'request.json').read_text())
        old_summary = json.loads((predecessor / 'summary.json').read_text())
        old_journal = json.loads((predecessor / 'kernel_journal.json').read_text())
        assert old_request['tested_commit'] == PREDECESSOR_COMMIT
        assert old_summary['component_probes_passed'] == 0 and old_summary['component_probes_total'] == 3
        assert len(old_journal['rows']) == 111
        with sqlite3.connect(parent_state.as_uri() + '?mode=ro', uri=True) as db:
            db.row_factory = sqlite3.Row
            actual_old_journal = [dict(row) for row in db.execute(
                'SELECT tick,previous_hash,body,event_hash FROM events ORDER BY tick')]
        assert actual_old_journal == old_journal['rows']
        original_files = {'manifest': file_sha(parent_manifest), 'state': file_sha(parent_state)}
        identity = active_kernel_identity(ROOT)
        save(out, 'provenance', {
            'tested_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            'tested_tree': subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}'], cwd=ROOT, text=True).strip(),
            'run_id': os.getenv('GITHUB_RUN_ID', 'LOCAL'), 'run_attempt': os.getenv('GITHUB_RUN_ATTEMPT', '1'),
            'predecessor_commit': PREDECESSOR_COMMIT,
            'predecessor_state_origin': 'FRESH_CI_REPRODUCTION_WITH_UNCHANGED_PINNED_PREDECESSOR_CODE',
            'historical_binary_artifact_restored': False, 'actual_reproduced_predecessor_events': 111,
            'predecessor_files': original_files, 'predecessor_identity': old_journal['identity'],
            'grammar_controller_and_harness_authorship': 'MAINTAINER_AUTHORIZED_BY_USER',
            'program_selection_authorship': 'KERNEL_USING_TRAINING_AND_VERIFIED_PRIOR_PROGRAMS',
            'external_llm_candidate_used': False, 'canonical_identity': identity})
        source_updates = {name: {'previous_sha256': digest, 'current_sha256': file_sha(ROOT / name)}
                          for name, digest in parent['inherited_files'].items() if digest != file_sha(ROOT / name)}
        save(out, 'exact_inherited_source_updates', source_updates)
        stage = 'CONTINUITY_UPGRADE'
        upgrade = prepare_upgrade(parent_manifest, parent_state, out / 'upgraded-birth', source_updates=source_updates)
        save(out, 'prepared_upgrade', upgrade)
        kernel = SuccessorKernel(upgrade['manifest'], upgrade['state'])
        try:
            assert kernel.identity == old_journal['identity']
            assert journal(kernel)[:111] == actual_old_journal
            assert kernel.implementation_identity != old_journal['implementation_identity']
            old_goals = copy.deepcopy(all_goals(kernel))
            save(out, 'continuity_before_development', {
                'state': kernel.verify_state(), 'identity': kernel.identity,
                'implementation_identity': kernel.implementation_identity,
                'inherited_event_prefix_equal': True, 'predecessor_goals': list(old_goals)})
            stage = 'KERNEL_SELECTED_GAP_REPAIR'
            continuation = kernel.develop_native_programs(rounds=3)
            save(out, 'gap_development', continuation)
            tasks = original_tasks()
            repaired = {}
            outcomes = []
            goals = all_goals(kernel)
            for task in tasks:
                solved = [g for g in goals.values() if g['spec'] == task['spec'] and g['status'] == 'VALIDATED_ON_HOLDOUT']
                assert len(solved) == 1, task['name']
                goal = solved[0]
                assert goal['result']['predictions'] == task['observer_query_expected'], task['name']
                assert goal['result']['schema'] == 'yado.compositional_source.v1'
                repaired[task['name']] = goal
                save(out, 'candidate_' + task['name'], goal['result'])
                source(out, 'candidate_' + task['name'], goal['result'])
                outcomes.append({'task': task['name'], 'goal_id': goal['id'],
                                 'status': goal['status'], 'fresh_query_count': len(task['observer_query_expected']),
                                 'fresh_queries_passed': True, 'source_sha256': goal['result']['source_sha256'],
                                 'scope': task['task_scope'], 'parent_deficit': task['parent_deficit']})
            for goal_id, old in old_goals.items():
                assert goals[goal_id] == old, 'HISTORICAL_GOAL_RELABELLED'
            save(out, 'resolved_component_probes', outcomes)
            stage = 'FOUR_PROGRAM_COMPOSITION_LINEAGE'
            seed = repaired['mcp_comment_serialization']
            lineage = [{'ordinal': 1, 'name': 'mcp_comment_serialization', 'goal_id': seed['id'],
                        'source_sha256': seed['result']['source_sha256'],
                        'parent_source_sha256': seed['result']['parent_source_sha256'],
                        'kind': 'TRAINING_SELECTED_SEED_PROGRAM'}]
            previous = seed['result']
            for ordinal, task in enumerate(lineage_tasks(), start=2):
                goal_id = kernel.open_goal(task['spec'], budget=20, mode='full')
                kernel.think(max_steps=100)
                goal = all_goals(kernel)[goal_id]
                assert goal['status'] == 'VALIDATED_ON_HOLDOUT', (task['name'], goal['status'])
                candidate = goal['result']
                assert candidate['parent_source_sha256'] == [previous['source_sha256']], task['name']
                assert candidate['source_sha256'] != previous['source_sha256']
                assert candidate['program'] != previous['program']
                assert candidate['predictions'] == task['observer_query_expected'], task['name']
                save(out, 'task_' + task['name'], task)
                save(out, 'candidate_' + task['name'], candidate)
                source(out, 'candidate_' + task['name'], candidate)
                lineage.append({'ordinal': ordinal, 'name': task['name'], 'goal_id': goal_id,
                                'source_sha256': candidate['source_sha256'],
                                'parent_source_sha256': candidate['parent_source_sha256'],
                                'fresh_queries_passed': True, 'kind': 'KERNEL_SELECTED_COMPOSITION_OF_VERIFIED_PARENT'})
                previous = candidate
            assert len({item['source_sha256'] for item in lineage}) == 4
            save(out, 'program_composition_lineage', {
                'status': 'PASS', 'programs': lineage, 'scope': 'FOUR_VERIFIED_COMPOSED_PROGRAMS',
                'new_kernel_architecture_generations': 0,
                'underlying_library_primitive_invention': False})
            stage = 'REAL_LOCAL_PATCH_APPLICATION'
            patch_result = real_patch_check(out, repaired['unified_patch_emission']['result'])
            stage = 'DEACTIVATION_REACTIVATION_AND_RETENTION'
            before_toggle = kernel.native_program_status()
            deactivation = kernel.set_compositional_synthesis(False)
            assert kernel.native_program_status()['synthesis_active'] is False
            reactivation = kernel.set_compositional_synthesis(True)
            assert kernel.native_program_status()['verified_programs'] == before_toggle['verified_programs']
            save(out, 'activation_roundtrip', {'deactivation': deactivation, 'reactivation': reactivation,
                                             'verified_program_memory_preserved': True})
            exhausted = kernel.develop_native_programs(rounds=3)
            assert exhausted['sessions'] and all(not s['selections'] for s in exhausted['sessions'])
            assert exhausted['unresolved_goal_ids'] == []
            save(out, 'finite_continuation', exhausted)
            retention = retained_memory(kernel)
            assert retention['passed']
            save(out, 'retained_memory', retention)
            final_goals = all_goals(kernel)
            for goal_id, old in old_goals.items():
                assert final_goals[goal_id] == old
            before = kernel.verify_state()
            before_journal = journal(kernel)
            assert before_journal[:111] == actual_old_journal
            save(out, 'selected_goals', {str(goal_id): {key: g[key] for key in
                 ('id', 'spec', 'status', 'attempted', 'budget', 'remaining', 'result')} for goal_id, g in final_goals.items()})
            save(out, 'kernel_journal', {'identity': kernel.identity,
                                        'implementation_identity': kernel.implementation_identity, 'rows': before_journal})
        finally:
            kernel.close()
        stage = 'RESTART_VERIFICATION'
        restored = SuccessorKernel(upgrade['manifest'], upgrade['state'])
        try:
            after = restored.verify_state()
            assert after == before and journal(restored) == before_journal
            assert all_goals(restored) == final_goals
            assert journal(restored)[:111] == actual_old_journal
            save(out, 'restart_verification', {'before': before, 'after': after,
                                              'all_event_bytes_equal': True,
                                              'predecessor_111_event_prefix_equal': True,
                                              'operational_identity_preserved': restored.identity == old_journal['identity']})
        finally:
            restored.close()
        assert original_files == {'manifest': file_sha(parent_manifest), 'state': file_sha(parent_state)}
        assert active_kernel_identity(ROOT) == identity
        assert not subprocess.check_output(['git', 'diff', '--name-only', '--',
                    'runtime', 'successor', 'canonical', 'architecture', 'resources'], cwd=ROOT).strip()
        save(out, 'summary', {'status': 'PASS_BOUNDED_NATIVE_PROGRAM_UPGRADE',
                              'component_probes_passed': 3, 'component_probes_total': 3,
                              'program_composition_lineage_length': 4,
                              'new_kernel_architecture_generations': 0,
                              'maintainer_implementation_upgrades': 1,
                              'predecessor_events_preserved': 111,
                              'predecessor_goals_relabelled': 0,
                              'operational_identity_preserved': True,
                              'implementation_identity_changed': True,
                              'restart_verified': True, 'retained_memory_passed': retention['passed'],
                              'real_local_patch_check': patch_result['status'],
                              'agent_conversation_performed': False,
                              'external_repository_written': False,
                              'credentials_or_permissions_expanded': False,
                              'background_process_running': False,
                              'general_intelligence_established': False,
                              'canonical_unchanged_during_experiment': True,
                              'unresolved_original_external_capabilities': ['LIVE_AGENT_COMMUNICATION', 'EXTERNAL_REPOSITORY_ACTION_ADAPTER'],
                              'canonical_identity': identity})
    except BaseException as error:
        save(out, 'summary', {'status': 'FAIL_OR_INCOMPLETE_UPGRADE', 'failed_stage': stage,
                              'error_type': type(error).__name__, 'error': str(error),
                              'background_process_running': False})
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--predecessor-output', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--preflight', action='store_true')
    args = parser.parse_args()
    if args.preflight:
        preflight()
    else:
        if args.predecessor_output is None or args.output is None:
            parser.error('--predecessor-output and --output are required for the experiment')
        main(args.predecessor_output.resolve(), args.output.resolve())
