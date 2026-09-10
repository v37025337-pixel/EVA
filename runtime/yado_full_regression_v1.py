"""Run every checked-in regression suite, including function-style tests.

A missing manifest, missing suite, skipped test, or incomplete run cannot pass.
The two inherited tmp_path tests use a fresh temporary directory per test.
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
SUITES = ("tests", "runtime/yado_rc8_v36", "successor/tests")


class FunctionTest(unittest.TestCase):
    def __init__(self, function):
        super().__init__("runTest")
        self.function = function

    def id(self):
        return self.function.__module__ + "." + self.function.__name__

    def shortDescription(self):
        return None

    def runTest(self):
        parameters = tuple(inspect.signature(self.function).parameters)
        if not parameters:
            self.function()
        elif parameters == ("tmp_path",):
            with tempfile.TemporaryDirectory(prefix="yado-function-test-") as directory:
                self.function(Path(directory))
        else:
            self.fail("Unsupported fixture contract: " + repr(parameters))


class Result(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.passed_ids = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.passed_ids.append(test.id())


def collect():
    combined = unittest.TestSuite()
    counts = {}
    for directory in SUITES:
        path = ROOT / directory
        if not path.is_dir():
            raise FileNotFoundError("MISSING_REGRESSION_SUITE:" + directory)
        loader = unittest.TestLoader()
        suite = loader.discover(str(path), pattern="test_*.py")
        if loader.errors:
            raise RuntimeError("REGRESSION_COLLECTION_FAILED:\n" + "\n".join(loader.errors))
        for source in sorted(path.glob("test_*.py")):
            module = sys.modules[source.stem]
            for name, function in inspect.getmembers(module, inspect.isfunction):
                if name.startswith("test_") and function.__module__ == module.__name__:
                    suite.addTest(FunctionTest(function))
        counts[directory] = suite.countTestCases()
        if not counts[directory]:
            raise ValueError("EMPTY_REGRESSION_SUITE:" + directory)
        combined.addTest(suite)
    return combined, counts


def source_digests():
    paths = set()
    for directory in ("runtime", "successor", "tests", "canonical", "resources", ".github"):
        paths.update(p for p in (ROOT / directory).rglob("*")
                     if p.is_file() and p.suffix in {".py", ".json", ".yml", ".yaml"}
                     and "state" not in p.relative_to(ROOT).parts)
    paths.add(ROOT / "architecture/evolution-ledger.json")
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(paths)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", default="audits/yado-full-regression-v1-report.json")
    args = parser.parse_args()
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    started = time.time()
    report = {"schema": "yado.full_regression.v1", "status": "WITHHOLD",
              "tested_commit": subprocess.check_output(
                  ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "python": sys.version, "suites": list(SUITES)}
    try:
        manifest = Path(args.manifest).resolve(strict=True)
        report["manifest_sha256"] = hashlib.sha256(manifest.read_bytes()).hexdigest()
        report["identity_digest"] = json.loads(manifest.read_text())["identity_digest"]
        os.environ["YADO_SUCCESSOR_TEST_MANIFEST"] = str(manifest)
        sys.path[:0] = [str(ROOT), str(ROOT / "runtime"), str(ROOT / "runtime/yado_rc8_v36")]
        before = source_digests()
        suite, counts = collect()
        expected = sum(counts.values())
        with output.with_suffix(".log").open("w", encoding="utf-8") as stream:
            result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Result).run(suite)
        after = source_digests()
        unchanged = before == after
        report.update(suite_counts=counts, expected_tests=expected, tests_run=result.testsRun,
                      passed_ids=result.passed_ids,
                      failures=[{"test": t.id(), "traceback": error} for t, error in result.failures],
                      errors=[{"test": t.id(), "traceback": error} for t, error in result.errors],
                      skipped=[{"test": t.id(), "reason": reason} for t, reason in result.skipped],
                      expected_failures=[t.id() for t, _ in result.expectedFailures],
                      unexpected_successes=[t.id() for t in result.unexpectedSuccesses],
                      source_sha256=before, source_unchanged=unchanged)
        complete = (result.wasSuccessful() and result.testsRun == expected
                    and len(result.passed_ids) == expected and unchanged)
        report["status"] = "PASS" if complete else "FAIL_REGRESSION"
    except Exception as exc:
        report["error"] = type(exc).__name__ + ": " + str(exc)
    report["elapsed_seconds"] = time.time() - started
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items()
                      if key not in {"passed_ids", "source_sha256"}}, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
