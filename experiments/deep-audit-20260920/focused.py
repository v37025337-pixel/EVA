"""Reproduce focused defect regressions before current-manifest rebinding."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'runtime'), str(ROOT / 'runtime/yado_rc8_v36'),
                str(ROOT / 'successor/tests')]
from yado_full_regression_v1 import Result, write_report

MODULES = ('test_yado_deep_audit_regressions_v1', 'test_yado_genome_fitness_binding_v1',
           'test_yado_legacy_boundary_v1', 'test_yado_branch_inventory_integrity_v1',
           'test_yado_current_manifest_source_audit_v1', 'test_yado_repository_file_audit_v1',
           'test_execution_replay_integrity', 'test_generation_upgrade_repair',
           'test_component_source_maintenance')


def source_hashes():
    return {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for directory in ('runtime', 'successor')
            for path in sorted((ROOT / directory).rglob('*.py'))
            if not path.name.startswith('test_') and 'state' not in path.relative_to(ROOT).parts}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', required=True)
    args = parser.parse_args()
    os.environ['YADO_SUCCESSOR_TEST_MANIFEST'] = str(Path(args.manifest).resolve(strict=True))
    output = Path(__file__).with_name('focused-validation.json')
    before = source_hashes()
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromNames(MODULES)
    if loader.errors:
        raise RuntimeError('FOCUSED_COLLECTION_FAILED:' + str(loader.errors))
    expected = suite.countTestCases()
    with output.with_suffix('.log').open('w') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Result).run(suite)
    unchanged = before == source_hashes()
    report = {'status': 'PASS' if result.wasSuccessful() and not result.skipped
              and result.testsRun == expected and len(result.passed_ids) == expected
              and unchanged else 'FAIL_FOCUSED_REGRESSIONS',
              'modules': list(MODULES), 'expected_tests': expected, 'tests_run': result.testsRun,
              'passed_ids': result.passed_ids, 'source_sha256': before, 'source_unchanged': unchanged,
              'failures': [{'test': t.id(), 'traceback': e} for t, e in result.failures],
              'errors': [{'test': t.id(), 'traceback': e} for t, e in result.errors],
              'skipped': [{'test': t.id(), 'reason': e} for t, e in result.skipped],
              'scope': 'DEFECT_REGRESSIONS_BEFORE_CANONICAL_REBINDING; FULL_INTEGRATION_REQUIRED'}
    write_report(output, report)
    print(json.dumps({k: v for k, v in report.items() if k not in {'source_sha256', 'passed_ids'}}))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
