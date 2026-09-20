"""Run the unchanged repository regression collection in isolated processes.

Every collected test runs exactly once. Workers get distinct temporary roots;
the coordinator verifies the complete source snapshot before and after all tests.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'runtime'), str(ROOT / 'runtime/yado_rc8_v36')]
spec = importlib.util.spec_from_file_location('full_regression', ROOT / 'runtime/yado_full_regression_v1.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def flatten(suite):
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from flatten(test)
        else:
            yield test


def artifact_hashes(manifest):
    data = json.loads(manifest.read_text())
    paths = {'manifest': manifest,
             'archive': manifest.parent / data['archive_file'],
             'harness': Path(__file__).resolve()}
    result = {}
    for name, path in paths.items():
        with path.open('rb') as stream:
            result[name] = hashlib.file_digest(stream, 'sha256').hexdigest()
    if result['archive'] != data['archive_sha256']:
        raise ValueError('REGRESSION_ARCHIVE_DIGEST_MISMATCH')
    return result


def worker(config, index):
    configuration = json.loads(config.read_text())
    selected = configuration['shards'][index]
    output = Path(configuration['directory']) / ('worker-' + str(index) + '.json')
    report = {'status': 'WITHHOLD', 'expected_ids': selected}
    runner.write_report(output, report)
    os.environ['YADO_SUCCESSOR_TEST_MANIFEST'] = configuration['manifest']
    suite, _ = runner.collect()
    tests = {test.id(): test for test in flatten(suite)}
    if any(identity not in tests for identity in selected):
        raise ValueError('SHARD_TEST_COLLECTION_DRIFT')
    with output.with_suffix('.log').open('w') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=runner.Result).run(
            unittest.TestSuite(tests[identity] for identity in selected))
    report.update(tests_run=result.testsRun, passed_ids=result.passed_ids,
                  failures=[{'test': t.id(), 'traceback': error} for t, error in result.failures],
                  errors=[{'test': t.id(), 'traceback': error} for t, error in result.errors],
                  skipped=[{'test': t.id(), 'reason': reason} for t, reason in result.skipped],
                  expected_failures=[t.id() for t, _ in result.expectedFailures],
                  unexpected_successes=[t.id() for t in result.unexpectedSuccesses])
    report['status'] = ('PASS' if result.wasSuccessful() and result.testsRun == len(selected)
                        and sorted(result.passed_ids) == sorted(selected) else 'FAIL_REGRESSION')
    runner.write_report(output, report)
    return 0 if report['status'] == 'PASS' else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest')
    parser.add_argument('--output')
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--worker', type=int)
    parser.add_argument('--config', type=Path)
    args = parser.parse_args()
    if args.worker is not None:
        return worker(args.config, args.worker)
    if not args.manifest or not args.output or not 1 <= args.workers <= 4:
        parser.error('--manifest, --output and 1..4 workers are required')
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {'schema': 'yado.full_regression.v1', 'status': 'WITHHOLD',
              'execution': 'ISOLATED_PROCESSES_COMPLETE_EXISTING_COLLECTION', 'python': sys.version}
    runner.write_report(output, report)
    started = time.monotonic()
    processes = []
    try:
        manifest = Path(args.manifest).resolve(strict=True)
        os.environ['YADO_SUCCESSOR_TEST_MANIFEST'] = str(manifest)
        subprocess.run(['git', 'diff', '--exit-code', '--quiet'], cwd=ROOT, check=True)
        tested_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        tested_tree = subprocess.check_output(['git', 'write-tree'], cwd=ROOT, text=True).strip()
        artifacts_before = artifact_hashes(manifest)
        before = runner.source_digests()
        suite, counts = runner.collect()
        tests = list(flatten(suite))
        identities = [test.id() for test in tests]
        if len(set(identities)) != len(identities) or sum(counts.values()) != len(tests):
            raise ValueError('REGRESSION_COLLECTION_NOT_UNIQUE_OR_COMPLETE')
        # Keep every module together, including its class/module fixtures.
        modules = {}
        for identity in identities:
            modules.setdefault(identity.split('.')[0], []).append(identity)
        shards = [[] for _ in range(args.workers)]
        weights = [0] * args.workers
        successor_modules = {path.stem for path in (ROOT / 'successor/tests').glob('test_*.py')}
        def weight(item):
            # The four full-archive migration tests measured 476 seconds in the
            # focused run. Keep that module together and reserve one worker's
            # capacity instead of treating it as four cheap unit tests.
            if item[0] == 'test_component_source_maintenance':
                return 960
            return len(item[1]) * (8 if item[0] in successor_modules else 1)
        for module, members in sorted(modules.items(), key=lambda item: (-weight(item), item[0])):
            index = min(range(args.workers), key=lambda i: weights[i])
            shards[index].extend(members)
            weights[index] += weight((module, members))
        directory = output.parent / (output.stem + '-workers')
        directory.mkdir(exist_ok=False)
        config = directory / 'config.json'
        config.write_text(json.dumps({'manifest': str(manifest), 'directory': str(directory), 'shards': shards}))
        streams = []
        for index in range(args.workers):
            temp = directory / ('tmp-' + str(index))
            temp.mkdir()
            env = {**os.environ, 'TMPDIR': str(temp), 'TMP': str(temp), 'TEMP': str(temp)}
            stream = (directory / ('worker-' + str(index) + '-stdout.log')).open('w')
            streams.append(stream)
            processes.append(subprocess.Popen([sys.executable, str(Path(__file__).resolve()),
                '--worker', str(index), '--config', str(config)], cwd=ROOT, env=env,
                stdout=stream, stderr=subprocess.STDOUT))
        codes = [process.wait() for process in processes]
        for stream in streams:
            stream.close()
        reports = [json.loads((directory / ('worker-' + str(i) + '.json')).read_text())
                   for i in range(args.workers)]
        after = runner.source_digests()
        artifacts_after = artifact_hashes(manifest)
        passed = [identity for child in reports for identity in child.get('passed_ids', [])]
        report.update(tested_commit=tested_commit, tested_tree=tested_tree,
                      manifest_sha256=artifacts_before['manifest'],
                      artifact_sha256=artifacts_before,
                      artifacts_unchanged=artifacts_before == artifacts_after,
                      identity_digest=json.loads(manifest.read_text())['identity_digest'],
                      suites=list(runner.SUITES), suite_counts=counts, expected_tests=len(identities),
                      tests_run=sum(child.get('tests_run', 0) for child in reports),
                      passed_ids=passed, source_sha256=before, source_unchanged=before == after,
                      worker_exit_codes=codes, worker_statuses=[child['status'] for child in reports],
                      temporary_roots_isolated=True)
        for key in ('failures', 'errors', 'skipped', 'expected_failures', 'unexpected_successes'):
            report[key] = [item for child in reports for item in child.get(key, [])]
        report['status'] = ('PASS' if not any(codes) and before == after
                            and artifacts_before == artifacts_after
                            and all(child['status'] == 'PASS' for child in reports)
                            and sorted(passed) == sorted(identities) else 'FAIL_REGRESSION')
    except Exception as exc:
        report['error'] = type(exc).__name__ + ':' + str(exc)
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
                process.wait()
    report['elapsed_seconds'] = time.monotonic() - started
    runner.write_report(output, report)
    print(json.dumps({key: value for key, value in report.items()
                      if key not in {'passed_ids', 'source_sha256'}}, indent=2))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
