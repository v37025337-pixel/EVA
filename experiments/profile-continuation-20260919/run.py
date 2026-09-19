"""Continue an intact repaired checkpoint through the public V2 entry points."""
import argparse
from contextlib import ExitStack
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
from successor.kernel import SuccessorKernel, encode, equivalent
from successor.cognitive import CognitiveLoop, replay
from successor.compositional_source import GRAMMAR_V2
from successor.endogenous_run import run_endogenous_cycles
from successor.generation import GenerationKernel, retained_memory
from yado_unified_core_v1 import UnifiedYADOCoreV1


def save(path, value):
    path.write_text(encode(value) + '\n')


def save_json(path, value):
    # Checkpoint consumers read these public metadata files with json.loads.
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def rows(path):
    with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as db:
        return list(db.execute('SELECT * FROM events ORDER BY tick'))


def run(predecessor, output):
    predecessor, output = predecessor.resolve(), output.resolve()
    if output.exists():
        raise ValueError('NEW_OUTPUT_REQUIRED')
    receipt = json.loads((predecessor / 'continuation-receipt.json').read_text())
    for name, digest in receipt['checkpoint_files_sha256'].items():
        path = (predecessor / name).resolve()
        assert path.is_relative_to(predecessor) and file_sha(path) == digest, name
    native_before = rows(predecessor / 'kernel.sqlite')
    component_before = rows(predecessor / 'component-evolution/state.sqlite')
    shutil.copytree(predecessor, output)
    evidence = output / 'profile-continuation'
    evidence.mkdir()
    save(evidence / 'predecessor-receipt.json', receipt)
    (output / 'birth').rename(output / 'preprofile-birth')
    parent = json.loads((output / 'preprofile-birth/manifest.json').read_text())
    changes = {p: {'previous_sha256': old, 'current_sha256': file_sha(ROOT / p)}
               for p, old in parent['inherited_files'].items() if file_sha(ROOT / p) != old}
    assert set(changes) <= {'successor/cognitive.py', 'successor/kernel.py',
        'architecture/evolution-ledger.json', 'canonical/yado-main-head-g2.json',
        'canonical/yado-unified-core-v1.json'}, changes
    transition = prepare_upgrade(output / 'preprofile-birth/manifest.json',
                                 output / 'kernel.sqlite', output / 'birth', source_updates=changes)
    shutil.copyfile(output / 'birth/kernel.sqlite', output / 'kernel.sqlite')
    save(evidence / 'implementation-transition.json', transition)
    print('CHECKPOINT_MIGRATED_WITH_HISTORY_PRESERVED', flush=True)
    with ExitStack() as stack:
        network = [stack.enter_context(patch.object(UnifiedYADOCoreV1, name,
                   side_effect=AssertionError('HISTORICAL_REPLAY_MUST_BE_OFFLINE')))
                   for name in ('native_library_candidate', 'verify_native_library')]
        kernel = SuccessorKernel(output / 'birth/manifest.json', output / 'kernel.sqlite')
        try:
            kernel.db.execute('PRAGMA journal_mode=DELETE')
            assert kernel.identity == receipt['identity_digest']
            before = kernel.native_program_status()
            assert before['language']['grammar'] == GRAMMAR_V2
            assert len(before['verified_programs']) == 6
            old_goals = replay(CognitiveLoop(kernel)._records())
            development = kernel.develop_native_programs(rounds=1)
            save(evidence / 'native-development.json', development)
            assert all(s['status'] == 'COMPLETE' for s in development['sessions'])
            assert development['language']['grammar'] == GRAMMAR_V2
            print('PUBLIC_V2_DEVELOPMENT_COMPLETED', flush=True)
            endogenous = run_endogenous_cycles(kernel, cycles=10, budget=3)
            save(evidence / 'endogenous.json', endogenous)
            assert endogenous['cycles_completed'] == endogenous['cycles_verified'] == 10
            print('ENDOGENOUS_CYCLES_10_OF_10', flush=True)
            memory = retained_memory(kernel)
            save(evidence / 'retained-memory.json', memory)
            assert memory['passed']
            current_goals = replay(CognitiveLoop(kernel)._records())
            assert all(current_goals[g] == old_goals[g] for g in old_goals)
            after = kernel.native_program_status()
            previous_hashes = {p['source_sha256'] for p in before['verified_programs']}
            current_hashes = {p['source_sha256'] for p in after['verified_programs']}
            assert previous_hashes <= current_hashes
            state = kernel.verify_state()
            canonical = kernel.parent.audit()
            assert canonical['pass']
        finally:
            kernel.close()
        print('MEMORY_RETAINED_REOPENING_IN_NEW_INSTANCE', flush=True)
        kernel = SuccessorKernel(output / 'birth/manifest.json', output / 'kernel.sqlite')
        try:
            kernel.db.execute('PRAGMA journal_mode=DELETE')
            assert kernel.verify_state() == state
            assert kernel.native_program_status() == after
            component = GenerationKernel(kernel, output / 'component-evolution/experience.sqlite',
                                         output / 'component-evolution/state.sqlite')
            try:
                from successor.generation_tasks import challenge
                application = []
                for _ in range(3):
                    seed = secrets.token_hex(24)
                    for task, expected in challenge(seed):
                        observed = component.execute(task)
                        application.append({'seed': seed, 'task': task, 'expected': expected,
                            'observed': observed, 'passed': equivalent(observed['result']['answer'], expected)})
                assert len(application) == 12 and all(r['passed'] for r in application)
                component_state = component.snapshot()
                assert component_state['execution_admitted']
                save(evidence / 'component-application.json', application)
            finally:
                component.close()
        finally:
            kernel.close()
        assert all(access.call_count == 0 for access in network)
    assert rows(output / 'kernel.sqlite')[:len(native_before)] == native_before
    assert rows(output / 'component-evolution/state.sqlite')[:len(component_before)] == component_before
    summary = {'status': 'PASS_PROFILE_REPAIR_AND_STATEFUL_CONTINUATION',
        'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'identity_digest': receipt['identity_digest'], 'state_before': receipt['state_after'],
        'state_after': state, 'inherited_native_events': len(native_before),
        'inherited_component_events': len(component_before), 'prior_event_prefixes_preserved': True,
        'active_grammar': after['language']['grammar'], 'native_programs_before': len(previous_hashes),
        'native_programs_after': len(current_hashes), 'new_program_hashes': sorted(current_hashes - previous_hashes),
        'development_sessions': len(development['sessions']),
        'development_selections': sum(len(s['selections']) for s in development['sessions']),
        'endogenous_cycles_verified': endogenous['cycles_verified'], 'host_goals_in_cycles': 0,
        'retained_goals': memory['goals'], 'retained_memory_passed': memory['passed'],
        'component_tasks_passed': len(application), 'component_state': component_state,
        'historical_pypi_calls': 0, 'canonical_audit_passed': canonical['pass'],
        'repair_authorship': 'ASSISTANT', 'goal_selection': 'EXISTING_YADO_ALGORITHMS',
        'new_internet_data_collected': False, 'background_process_running': False,
        'formal_g3_transition': False, 'consciousness_established': False}
    save_json(evidence / 'summary.json', summary)
    save_json(output / 'summary.json', summary)
    manifest = json.loads((output / 'birth/manifest.json').read_text())
    exported = set(manifest['assembly_sources']) | set(changes)
    exported.add('experiments/profile-continuation-20260919/profile-tests.json')
    for name in exported:
        target = output / 'source-overlay' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    new_receipt = {'status': summary['status'], 'identity_digest': summary['identity_digest'],
        'state_after': state, 'source_run_id': 0,
        'checkpoint_files_sha256': {str(p.relative_to(output)): file_sha(p)
            for p in sorted(output.rglob('*')) if p.is_file()
            and p.name != 'continuation-receipt.json' and not p.name.endswith(('-wal', '-shm'))}}
    save_json(output / 'continuation-receipt.json', new_receipt)
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--predecessor', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.predecessor, args.output)
