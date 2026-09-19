"""Fresh-process replay, source binding and checkpoint integrity verification."""
import argparse
from contextlib import ExitStack
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'runtime'), str(ROOT / 'runtime/yado_rc8_v36')]
from successor.archive import file_sha
from successor.kernel import SuccessorKernel
from successor.cognitive import CognitiveLoop, replay
from successor.compositional_source import execute
from successor.generation import GenerationKernel
from yado_unified_core_v1 import UnifiedYADOCoreV1


def verify(output):
    output = output.resolve()
    receipt = json.loads((output / 'continuation-receipt.json').read_text())
    for relative, digest in receipt['checkpoint_files_sha256'].items():
        path = (output / relative).resolve()
        assert path.is_relative_to(output) and file_sha(path) == digest, relative
    report = json.loads((output / 'summary.json').read_text())
    assert report['status'] == 'PASS_REPAIRED_REPLAY_JSON_AND_READMISSION'
    with ExitStack() as stack:
        network = [stack.enter_context(patch.object(UnifiedYADOCoreV1, name,
            side_effect=AssertionError('OFFLINE_REPLAY_ONLY'))) for name in
            ('native_library_candidate', 'verify_native_library')]
        kernel = SuccessorKernel(output / 'birth/manifest.json', output / 'kernel.sqlite')
        try:
            kernel.db.execute('PRAGMA journal_mode=DELETE')
            assert kernel.identity == report['identity_digest']
            assert kernel.verify_state() == report['state_after']
            goals = replay(CognitiveLoop(kernel)._records())
            assert goals[1796]['status'] == 'WITHHOLD'
            goal = goals[report['new_json_goal_id']]
            assert goal['status'] == 'VALIDATED_ON_HOLDOUT'
            assert goal['result']['source_sha256'] == report['json_source_sha256']
            cases = json.loads((output / 'admission-repair/json-fresh-after-freeze.json').read_text())
            observed = execute(goal['result'], [r['input'] for r in cases])
            assert len(observed) == 32
            assert all(type(a) is bool and a == r['expected'] == r['observed']
                       for a, r in zip(observed, cases))
            component = GenerationKernel(kernel, output / 'component-evolution/experience.sqlite',
                                         output / 'component-evolution/state.sqlite')
            try:
                assert component.snapshot() == report['component_state']
                assert component.snapshot()['readmission_passed'] is True
            finally:
                component.close()
        finally:
            kernel.close()
        assert all(n.call_count == 0 for n in network)
    result = {'status': 'PASS_FRESH_PROCESS_OFFLINE_REPLAY',
        'verified_checkpoint_files': len(receipt['checkpoint_files_sha256']),
        'state': report['state_after'], 'component_events': report['component_state']['events'],
        'historical_pypi_network_calls': 0, 'json_fresh_cases_reexecuted': len(cases)}
    target = output / 'admission-repair/fresh-process-verification.json'
    target.write_text(json.dumps(result, indent=2) + '\n')
    receipt['checkpoint_files_sha256'][str(target.relative_to(output))] = file_sha(target)
    # SQLite may update its physical header when entering/leaving WAL mode;
    # the logical event chain was checked above against the frozen state.
    receipt['checkpoint_files_sha256']['kernel.sqlite'] = file_sha(output / 'kernel.sqlite')
    (output / 'continuation-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    verify(parser.parse_args().output)
