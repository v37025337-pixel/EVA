from __future__ import annotations

import ast
import hashlib
import importlib.util
import inspect
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))

from yado_bounded_autonomous_learning_v1 import fetch_public_readonly, normalized_text, evidence_facts
from yado_unified_core_v1 import UnifiedYADOCoreV1

SCHEMA = "yado.python_study.v1"
OUT = REPO / "experience" / "python" / "yado-python-study-v1.json"

SOURCES = [
    {
        "id": "PYTHON_LANGUAGE_REFERENCE",
        "url": "https://docs.python.org/3/reference/index.html",
        "query": {"python", "syntax", "statement", "expression", "execution", "language"},
    },
    {
        "id": "PYTHON_EXPRESSIONS",
        "url": "https://docs.python.org/3/reference/expressions.html",
        "query": {"expression", "operator", "call", "attribute", "comprehension", "lambda"},
    },
    {
        "id": "PYTHON_AST",
        "url": "https://docs.python.org/3/library/ast.html",
        "query": {"ast", "parse", "compile", "node", "visitor", "syntax"},
    },
    {
        "id": "PYTHON_INSPECT",
        "url": "https://docs.python.org/3/library/inspect.html",
        "query": {"inspect", "signature", "function", "class", "source", "runtime"},
    },
    {
        "id": "PYTHON_IMPORTLIB",
        "url": "https://docs.python.org/3/library/importlib.html",
        "query": {"import", "module", "loader", "spec", "package", "runtime"},
    },
    {
        "id": "PYTHON_UNITTEST",
        "url": "https://docs.python.org/3/library/unittest.html",
        "query": {"test", "assert", "fixture", "case", "suite", "runner"},
    },
]


def canon(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def digest(obj):
    return hashlib.sha256(canon(obj).encode("utf-8")).hexdigest()


def interpreter_checks():
    checks = {}

    src = "def f(x):\n    return x * 2 + 1\n"
    tree = ast.parse(src)
    checks["ast_parse_function"] = isinstance(tree.body[0], ast.FunctionDef)
    code = compile(tree, "<yado-python-study>", "exec")
    ns = {}
    exec(code, {"__builtins__": {}}, ns)
    checks["compile_exec_local_generated_only"] = ns["f"](4) == 9

    def probe(a: int, b: int = 2) -> int:
        return a + b

    # The module uses postponed annotations, so inspect may otherwise expose strings.
    # Resolve them through inspect's documented eval_str path before checking identity.
    sig = inspect.signature(probe, eval_str=True)
    checks["inspect_signature"] = list(sig.parameters) == ["a", "b"] and sig.return_annotation is int
    checks["importlib_find_spec"] = importlib.util.find_spec("json") is not None

    pattern = ast.parse("match x:\n    case 1:\n        y = 'one'\n    case _:\n        y = 'other'\n")
    checks["modern_syntax_match_ast"] = any(isinstance(n, ast.Match) for n in ast.walk(pattern))

    return checks


def main():
    core = UnifiedYADOCoreV1(REPO)
    goal = core.represent_raw_task(
        "Study official Python language and standard-library documentation, verify selected concepts against the local Python interpreter, and preserve the result as experience without executing downloaded code."
    )

    source_results = []
    all_facts = []
    failures = []

    for spec in SOURCES:
        try:
            net = fetch_public_readonly(spec["url"])
            text = normalized_text(net["body"], net["content_type"])
            facts = evidence_facts(text, set(spec["query"]))[:12]
            all_facts.extend({"source_id": spec["id"], "text": x} for x in facts)
            source_results.append({
                "source_id": spec["id"],
                "url": spec["url"],
                "http_status": net["status"],
                "sha256": net["sha256"],
                "bytes": net["bytes"],
                "fact_count": len(facts),
                "network_executed": net["network_executed"],
                "read_only": net["read_only"],
                "credentials_used": net["credentials_used"],
            })
        except Exception as exc:
            failures.append({"source_id": spec["id"], "error": f"{type(exc).__name__}:{exc}"})

    checks = interpreter_checks()
    unique = []
    seen = set()
    for row in all_facts:
        h = hashlib.sha256(row["text"].encode("utf-8")).hexdigest()
        if h not in seen:
            seen.add(h)
            unique.append(row)

    pass_gate = (
        len(source_results) >= 5
        and len(unique) >= 12
        and all(checks.values())
        and all(x["read_only"] and not x["credentials_used"] for x in source_results)
    )

    report = {
        "schema": SCHEMA,
        "status": "PASS_SHADOW_BOUNDED_PYTHON_STUDY_V1" if pass_gate else "WITHHOLD_PYTHON_STUDY_V1",
        "goal_representation": goal,
        "python_runtime": {
            "version": sys.version,
            "implementation": sys.implementation.name,
        },
        "source_count": len(source_results),
        "source_failure_count": len(failures),
        "sources": source_results,
        "failures": failures,
        "fact_count": len(unique),
        "facts": unique[:48],
        "interpreter_checks": checks,
        "experience_digest": digest({"sources": source_results, "facts": unique, "checks": checks}),
        "safety": {
            "official_python_docs_only": True,
            "public_https_get_only": True,
            "credentials_used": False,
            "external_writes": False,
            "downloaded_code_executed": False,
            "local_interpreter_experiments_only": True,
        },
        "claim_boundary": "This is bounded study of official Python documentation plus local interpreter verification. It is not proof of open-ended autonomous programming or consciousness.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ["status", "source_count", "source_failure_count", "fact_count", "experience_digest"]}, sort_keys=True))
    if not pass_gate:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
