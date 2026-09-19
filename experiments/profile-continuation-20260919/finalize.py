"""Verify the completed checkpoint in a fresh process and seal public JSON metadata."""
import argparse
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'runtime'), str(ROOT / 'runtime/yado_rc8_v36')]
from successor.archive import file_sha
from successor.kernel import SuccessorKernel, decode
from successor.generation import GenerationKernel


def read(path):
    text = path.read_text()
    value = json.loads(text)
    return decode(text) if set(value) == {'t', 'v'} else value


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def finalize(output, regression, audit):
    output = output.resolve()
    receipt = read(output / 'continuation-receipt.json')
    for name, expected in receipt['checkpoint_files_sha256'].items():
        path = (output / name).resolve()
        assert path.is_relative_to(output) and file_sha(path) == expected, name
    summary = read(output / 'summary.json')
    assert summary['status'] == 'PASS_PROFILE_REPAIR_AND_STATEFUL_CONTINUATION'
    suite = read(regression)
    assert read(audit)['status'] == 'PASS'
    assert suite['status'] == 'PASS' and suite['tests_run'] == suite['expected_tests']
    assert not suite['failures'] and not suite['errors'] and not suite['skipped']
    assert suite['source_unchanged']
    for name, expected in suite['source_sha256'].items():
        assert file_sha(ROOT / name) == expected, name
    kernel = SuccessorKernel(output / 'birth/manifest.json', output / 'kernel.sqlite')
    try:
        kernel.db.execute('PRAGMA journal_mode=DELETE')
        assert kernel.identity == summary['identity_digest']
        assert kernel.verify_state() == summary['state_after']
        status = kernel.native_program_status()
        assert status['language']['grammar'] == summary['active_grammar']
        assert len(status['verified_programs']) == summary['native_programs_after']
        component = GenerationKernel(kernel, output / 'component-evolution/experience.sqlite',
                                     output / 'component-evolution/state.sqlite')
        try:
            assert component.snapshot() == summary['component_state']
        finally:
            component.close()
    finally:
        kernel.close()
    evidence = output / 'profile-continuation'
    fresh = {'status': 'PASS_FRESH_PROCESS_REOPEN', 'state': summary['state_after'],
             'verified_checkpoint_files': len(receipt['checkpoint_files_sha256']),
             'full_regression_tests': suite['tests_run'], 'active_grammar': summary['active_grammar']}
    write(evidence / 'fresh-process.json', fresh)
    write(evidence / 'summary.json', summary)
    write(output / 'summary.json', summary)
    shutil.copyfile(regression, evidence / 'full-regression.json')
    shutil.copyfile(regression.with_suffix('.log'), evidence / 'full-regression.log')
    shutil.copyfile(audit, evidence / 'kernel-audit.json')
    report_name = 'experiments/profile-continuation-20260919/profile-tests.json'
    target = output / 'source-overlay' / report_name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / report_name, target)
    receipt['checkpoint_files_sha256'] = {str(p.relative_to(output)): file_sha(p)
        for p in sorted(output.rglob('*')) if p.is_file()
        and p.name != 'continuation-receipt.json' and not p.name.endswith(('-wal', '-shm'))}
    write(output / 'continuation-receipt.json', receipt)
    assert json.loads((output / 'continuation-receipt.json').read_text())['state_after'] == summary['state_after']
    print(json.dumps(fresh), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--regression', type=Path, required=True)
    parser.add_argument('--audit', type=Path, required=True)
    args = parser.parse_args()
    finalize(args.output, args.regression, args.audit)
