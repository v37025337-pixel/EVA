"""Repair admission on a copied checkpoint; preserve every historical event.

No network is required. Historical PyPI accessors are blocked and counted.
The old WITHHOLD remains; an explicit V2 contract is a new learning goal.
"""
import argparse
from contextlib import ExitStack
import copy
import json
from pathlib import Path
import secrets
import shutil
import sqlite3
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'runtime'), str(ROOT / 'runtime/yado_rc8_v36')]
from successor.archive import file_sha
from successor.continuity import prepare_upgrade
from successor.kernel import SuccessorKernel, equivalent
from successor.cognitive import CognitiveLoop, replay
from successor.compositional_binding import memories
from successor.compositional_source import execute, GRAMMAR_V2
from successor.generation import GenerationKernel, upgrade_component_state
from successor.generation_tasks import challenge
from yado_unified_core_v1 import UnifiedYADOCoreV1


def save(folder, name, value):
    (folder / (name + '.json')).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def row(before, after, expected):
    return {'input': {'before': before, 'after': after}, 'expected': expected}


def contract():
    # Authored contract labels. No historical holdout enters the training set.
    training = [row('{"a":1,"b":2}', '{ "a": 1, "b": 2 }', True),
        row('{"a":3,"b":4}', '{"a":3,"b":5}', False),
        row('[1,2]', '[1, 2]', True),
        row('{"k":[true,null]}', '{"k": [false,null]}', False),
        row('{"c":3,"d":4}', '{"d":4,"c":3}', True),
        row('{"flag":true}', '{"flag":1}', False)]
    validation = [row('{"outer":{"x":41,"y":[false,null]},"end":7}',
                      '{"end":7,"outer":{"y":[false,null],"x":41}}', True),
                  row('[7,8,9]', '[9,8,7]', False),
                  row('{"optional":null}', '{}', False),
                  row('"Case"', '"case"', False)]
    return {'schema': 'yado.native_program_goal.v1', 'domain': 'native_source',
            'training': training, 'validation': validation,
            'queries': [{'input': {'before': '{"p":91,"q":92}', 'after': '{"q":92,"p":91}'}}]}


def fresh_matrix():
    # Called only after candidate admission/source freeze. Expectations are
    # authored independently of the engine's equality or freeze functions.
    cases = []
    dump = lambda value: json.dumps(value, ensure_ascii=False, separators=(',', ':'))
    for _ in range(2):
        key, other, number = secrets.token_hex(4), secrets.token_hex(4), secrets.randbelow(10000) + 100
        pairs = [({key: {other: number, 'list': [True, None]}, 'tail': 9},
                  {'tail': 9, key: {'list': [True, None], other: number}}, True),
                 ([{key: number, other: number + 1}], [{other: number + 1, key: number}], True),
                 ([number, number + 1], [number + 1, number], False),
                 ({key: True}, {key: 1}, False), ({key: False}, {key: 0}, False),
                 ({key: None}, {}, False), ({key: 'Case'}, {key: 'case'}, False),
                 ({'Case': number}, {'case': number}, False),
                 ([], [], True), ({}, {}, True), ([], {}, False),
                 (None, None, True), (str(number), number, False)]
        cases.extend(row(dump(a), dump(b), expected) for a, b, expected in pairs)
        cases.extend([row('"\\u00e9\\ud83d\\ude42"', '"é🙂"', True),
                      row('"line\\nend"', '"line\\u000aend"', True),
                      row('"line\\nend"', '"line\\\\nend"', False)])
    return cases


def events(path, table='events'):
    with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as db:
        return list(db.execute('SELECT * FROM ' + table + ' ORDER BY 1'))


def canonical_source_updates(manifest_path):
    """Only the three explicit maintenance-binding files may also transition."""
    manifest = json.loads(Path(manifest_path).read_text())
    allowed = {'canonical/yado-unified-core-v1.json', 'canonical/yado-main-head-g2.json',
               'architecture/evolution-ledger.json'}
    changes = {p: {'previous_sha256': old, 'current_sha256': file_sha(ROOT / p)}
               for p, old in manifest['inherited_files'].items() if file_sha(ROOT / p) != old}
    if not set(changes) <= allowed:
        raise ValueError('UNREVIEWED_INHERITED_SOURCE_CHANGE')
    subprocess.run([sys.executable, str(ROOT / 'runtime/yado_canonical_invariant_guard_v1.py')],
                   check=True, capture_output=True)
    return changes or None


def run(predecessor, output):
    predecessor, output = predecessor.resolve(), output.resolve()
    if output.exists():
        raise ValueError('CHOOSE_NEW_OUTPUT; earlier evidence must remain intact')
    shutil.copytree(predecessor, output, ignore=shutil.ignore_patterns('*-wal', '*-shm'))
    (output / 'birth').rename(output / 'inherited-birth')
    evidence = output / 'admission-repair'; evidence.mkdir()
    for name in ('summary.json', 'continuation-receipt.json'):
        (output / name).rename(evidence / ('predecessor-' + name))
    print('PREPARING_NATIVE_IMPLEMENTATION_UPGRADE', flush=True)
    transition = prepare_upgrade(predecessor / 'birth/manifest.json', predecessor / 'kernel.sqlite', output / 'birth',
                                 source_updates=canonical_source_updates(predecessor / 'birth/manifest.json'))
    shutil.copyfile(output / 'birth/kernel.sqlite', output / 'kernel.sqlite')
    save(evidence, 'native-transition', transition)
    report = {'status': 'RUNNING', 'identity_digest': transition['identity_digest'],
              'implementation_digest': transition['implementation_digest'],
              'authorship': 'ASSISTANT_AUTHORED_REPAIR_AND_CONTRACT_KERNEL_SELECTED_PROGRAM',
              'background_process_running': False, 'formal_g3_transition': False}
    save(evidence, 'summary', report)
    with ExitStack() as guards:
        network = [guards.enter_context(patch.object(UnifiedYADOCoreV1, name,
                   side_effect=AssertionError('HISTORICAL_REPLAY_MUST_NOT_ACCESS_NETWORK')))
                   for name in ('native_library_candidate', 'verify_native_library')]
        kernel = SuccessorKernel(output / 'birth/manifest.json', output / 'kernel.sqlite')
        try:
            kernel.db.execute('PRAGMA journal_mode=DELETE')
            loop = CognitiveLoop(kernel)
            old_goals = replay(loop._records())
            old_failed = copy.deepcopy(old_goals[1796])
            assert old_failed['status'] == 'WITHHOLD'
            prior_memories = {m['source_sha256'] for m in memories(loop._records(), grammar=GRAMMAR_V2)}
            loop.set_compositional_synthesis(False)
            loop.set_compositional_synthesis(True, grammar=GRAMMAR_V2)
            definition = contract(); save(evidence, 'json-contract', definition)
            goal_id = kernel.open_goal(definition, budget=10, mode='no_memory')
            kernel.think(40)
            goal = replay(loop._records())[goal_id]
            save(evidence, 'json-goal', goal)
            assert goal['status'] == 'VALIDATED_ON_HOLDOUT', goal['status']
            candidate = goal['result']
            assert candidate['grammar'] == GRAMMAR_V2 and 'json_equal_v2' in candidate['source']
            matrix = fresh_matrix()
            predictions = execute(candidate, [r['input'] for r in matrix])
            fresh = [{**r, 'observed': value, 'passed': type(value) is bool and value == r['expected']}
                     for r, value in zip(matrix, predictions)]
            assert len(fresh) == 32 and all(r['passed'] for r in fresh)
            save(evidence, 'json-fresh-after-freeze', fresh)
            previous_cases = old_failed['spec']['validation']
            regression = execute(candidate, [r['input'] for r in previous_cases])
            assert regression == [r['expected'] for r in previous_cases]
            assert replay(loop._records())[1796] == old_failed
            after_memories = {m['source_sha256'] for m in memories(loop._records(), grammar=GRAMMAR_V2)}
            assert prior_memories < after_memories
            print('JSON_NEW_GOAL_PASS_FRESH_32_OF_32', flush=True)
            directory = output / 'component-evolution'
            (directory / 'state.sqlite').rename(directory / 'predecessor-state.sqlite')
            migration = upgrade_component_state(kernel, directory / 'experience.sqlite',
                                                directory / 'predecessor-state.sqlite', directory / 'state.sqlite')
            save(evidence, 'component-transition', migration)
            component = GenerationKernel(kernel, directory / 'experience.sqlite', directory / 'state.sqlite')
            try:
                assert component.snapshot()['execution_admitted'] is False
                try:
                    component.execute(challenge('must-be-blocked')[0][0])
                except ValueError as exc:
                    assert str(exc) == 'GENERATION_REQUIRES_READMISSION'
                else:
                    raise AssertionError('Execution was not gated')
                admission = component.readmit(); save(evidence, 'readmission', admission)
                assert admission['passed'], admission['inherited_memory']
                component_before_restart = component.snapshot()
            finally:
                component.close()
            state = kernel.verify_state()
        finally:
            kernel.close()
        print('FRESH_READMISSION_PASS_RESTARTING', flush=True)
        kernel = SuccessorKernel(output / 'birth/manifest.json', output / 'kernel.sqlite')
        try:
            kernel.db.execute('PRAGMA journal_mode=DELETE')
            assert kernel.verify_state() == state
            assert replay(CognitiveLoop(kernel)._records())[1796] == old_failed
            component = GenerationKernel(kernel, output / 'component-evolution/experience.sqlite',
                                         output / 'component-evolution/state.sqlite')
            try:
                assert component.snapshot() == component_before_restart
                seed = secrets.token_hex(16)
                checks = []
                for task, expected in challenge(seed):
                    measured = component.execute(task)
                    checks.append({'task': task, 'expected': expected, 'result': measured,
                                   'passed': equivalent(measured['result']['answer'], expected)})
                assert checks and all(c['passed'] for c in checks)
                save(evidence, 'component-fresh-after-restart', {'seed': seed, 'checks': checks})
                component_state = component.snapshot()
            finally:
                component.close()
            canonical = kernel.parent.audit()
            assert canonical['pass']
            save(evidence, 'canonical-audit', canonical)
        finally:
            kernel.close()
        assert all(n.call_count == 0 for n in network)
    old_native = events(predecessor / 'kernel.sqlite')
    old_component = events(predecessor / 'component-evolution/state.sqlite')
    assert events(output / 'kernel.sqlite')[:len(old_native)] == old_native
    assert events(output / 'component-evolution/state.sqlite')[:len(old_component)] == old_component
    assert file_sha(output / 'component-evolution/predecessor-state.sqlite') == file_sha(predecessor / 'component-evolution/state.sqlite')
    report.update(status='PASS_REPAIRED_REPLAY_JSON_AND_READMISSION', state_after=state,
        inherited_native_events=len(old_native), inherited_component_events=len(old_component),
        inherited_event_prefixes_unchanged=True, old_json_goal_status='WITHHOLD',
        new_json_goal_id=goal_id, new_json_goal_status=goal['status'],
        json_source_sha256=candidate['source_sha256'], json_fresh_checks=len(fresh),
        json_fresh_passed=sum(c['passed'] for c in fresh), old_json_regression=regression,
        native_programs_before=len(prior_memories), native_programs_after=len(after_memories),
        historical_pypi_network_calls=0, readmission_passed=admission['passed'],
        retained_goals=admission['inherited_memory']['goals'],
        component_fresh_after_restart=len(checks), component_fresh_passed=sum(c['passed'] for c in checks),
        component_state=component_state, canonical_audit_passed=True,
        json_domain='BOUNDED_INTEGER_JSON; floats and surrogate code points remain unsupported',
        json_training_origin='NEW_EXPLICIT_CONTRACT; old validation is regression only',
        autonomous_architecture_evolution_proven=False)
    save(evidence, 'summary', report); save(output, 'summary', report)
    # All required source bytes, including the prior runtime overlay, are pinned.
    manifest = json.loads((output / 'birth/manifest.json').read_text())
    for relative in manifest['assembly_sources']:
        target = output / 'source-overlay' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    save(output, 'continuation-receipt', {'status': report['status'],
        'checkpoint_id': 'yado-admission-repair-20260919', 'source_run_id': 0,
        'identity_digest': kernel.identity, 'state_after': state,
        'checkpoint_files_sha256': {str(p.relative_to(output)): file_sha(p) for p in sorted(output.rglob('*'))
            if p.is_file() and p.name != 'continuation-receipt.json' and not p.name.endswith(('-wal', '-shm'))}})
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--predecessor', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.predecessor, args.output)
