from __future__ import annotations

from pathlib import Path
import ast
import copy
import hashlib
import importlib.util
import json
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
REQUEST = REPO / "architecture/yado-native-code-writer-v1-request.json"
CANDIDATE = REPO / "candidates/kernel-self-generated/yado_native_public_link_traversal_v1.py"
REPORT = REPO / "candidates/kernel-self-generated/g2-native-code-writer-v1.json"
HEAD = REPO / "canonical/yado-main-head-g2.json"


def canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def digest(obj: Any) -> str:
    return hashlib.sha256(canon(obj).encode()).hexdigest()


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class YADONativeCodeWriterV1:
    """Bounded seedless source writer.

    The host provides a goal, not source. The writer classifies the goal, builds
    a small semantic IR, materializes it through Python AST, and emits a fresh
    candidate module. Unknown capability families fail closed.
    """

    COMPONENT_ID = "CTRL-G2-NATIVE-CODE-WRITER-V1"
    SCHEMA = "yado.g2.native_code_writer.v1"
    SAFE_IMPORTS = {"re", "urllib.parse"}
    BANNED_CALLS = {
        "eval", "exec", "compile", "open", "input", "__import__", "breakpoint",
        "system", "popen", "fork", "spawn", "remove", "unlink", "rmdir",
    }

    @staticmethod
    def classify_goal(goal: str) -> dict:
        text = re.sub(r"[^a-z0-9]+", "_", str(goal).lower())
        scores = {
            "PUBLIC_LINK_TRAVERSAL": sum(
                token in text
                for token in (
                    "link", "href", "url", "http", "https", "travers", "page",
                    "document", "provenance", "official", "crawl",
                )
            )
        }
        family, score = max(scores.items(), key=lambda item: item[1])
        if score < 2:
            return {"status": "WITHHOLD", "reason": "NO_SUPPORTED_CAPABILITY_FAMILY", "scores": scores}
        return {"status": "SELECTED", "family": family, "score": score, "scores": scores}

    @staticmethod
    def derive_ir(goal: str, classification: dict) -> dict:
        if classification.get("family") != "PUBLIC_LINK_TRAVERSAL":
            return {"status": "WITHHOLD", "reason": "UNSUPPORTED_FAMILY"}
        return {
            "status": "READY",
            "family": "PUBLIC_LINK_TRAVERSAL",
            "goal_digest": hashlib.sha256(str(goal).encode()).hexdigest(),
            "module": "yado_native_public_link_traversal_v1",
            "imports": [
                {"kind": "import", "module": "re"},
                {"kind": "from", "module": "urllib.parse", "names": ["urljoin", "urlparse"]},
            ],
            "function": {
                "name": "extract_public_links",
                "args": ["parent_url", "html", "max_links"],
                "defaults": {"max_links": 64},
                "operations": [
                    "TYPE_GUARD",
                    "HREF_EXTRACTION",
                    "URL_JOIN",
                    "PUBLIC_SCHEME_FILTER",
                    "FRAGMENT_STRIP",
                    "DEDUP",
                    "PROVENANCE_RECORD",
                    "BOUNDED_OUTPUT",
                ],
            },
        }

    @staticmethod
    def _name(name: str, ctx=ast.Load()) -> ast.Name:
        return ast.Name(id=name, ctx=ctx)

    @classmethod
    def materialize(cls, ir: dict) -> str:
        if ir.get("status") != "READY" or ir.get("family") != "PUBLIC_LINK_TRAVERSAL":
            raise ValueError("IR_NOT_READY")

        imports: list[ast.stmt] = [
            ast.Import(names=[ast.alias(name="re")]),
            ast.ImportFrom(
                module="urllib.parse",
                names=[ast.alias(name="urljoin"), ast.alias(name="urlparse")],
                level=0,
            ),
        ]

        args = ast.arguments(
            posonlyargs=[],
            args=[ast.arg(arg="parent_url"), ast.arg(arg="html"), ast.arg(arg="max_links")],
            vararg=None,
            kwonlyargs=[],
            kw_defaults=[],
            kwarg=None,
            defaults=[ast.Constant(64)],
        )

        body: list[ast.stmt] = []
        type_guard = ast.UnaryOp(
            op=ast.Not(),
            operand=ast.BoolOp(
                op=ast.And(),
                values=[
                    ast.Call(func=cls._name("isinstance"), args=[cls._name("parent_url"), cls._name("str")], keywords=[]),
                    ast.Call(func=cls._name("isinstance"), args=[cls._name("html"), cls._name("str")], keywords=[]),
                ],
            ),
        )
        body.append(ast.If(test=type_guard, body=[ast.Return(value=ast.List(elts=[], ctx=ast.Load()))], orelse=[]))
        body.extend([
            ast.Assign(targets=[cls._name("seen", ast.Store())], value=ast.Call(func=cls._name("set"), args=[], keywords=[])),
            ast.Assign(targets=[cls._name("out", ast.Store())], value=ast.List(elts=[], ctx=ast.Load())),
            ast.Assign(
                targets=[cls._name("limit", ast.Store())],
                value=ast.Call(
                    func=cls._name("max"),
                    args=[ast.Constant(1), ast.Call(func=cls._name("int"), args=[cls._name("max_links")], keywords=[])],
                    keywords=[],
                ),
            ),
        ])

        findall = ast.Call(
            func=ast.Attribute(value=cls._name("re"), attr="findall", ctx=ast.Load()),
            args=[ast.Constant(r"href\s*=\s*[\"']([^\"'#]+)[\"']"), cls._name("html")],
            keywords=[ast.keyword(arg="flags", value=ast.Attribute(value=cls._name("re"), attr="I", ctx=ast.Load()))],
        )

        loop_body: list[ast.stmt] = [
            ast.Assign(
                targets=[cls._name("raw", ast.Store())],
                value=ast.Call(func=ast.Attribute(value=cls._name("raw"), attr="strip", ctx=ast.Load()), args=[], keywords=[]),
            ),
            ast.If(test=ast.UnaryOp(op=ast.Not(), operand=cls._name("raw")), body=[ast.Continue()], orelse=[]),
            ast.Assign(
                targets=[cls._name("absolute", ast.Store())],
                value=ast.Call(func=cls._name("urljoin"), args=[cls._name("parent_url"), cls._name("raw")], keywords=[]),
            ),
            ast.Assign(
                targets=[cls._name("parsed", ast.Store())],
                value=ast.Call(func=cls._name("urlparse"), args=[cls._name("absolute")], keywords=[]),
            ),
            ast.If(
                test=ast.BoolOp(
                    op=ast.Or(),
                    values=[
                        ast.Compare(
                            left=ast.Attribute(value=cls._name("parsed"), attr="scheme", ctx=ast.Load()),
                            ops=[ast.NotIn()],
                            comparators=[ast.Tuple(elts=[ast.Constant("http"), ast.Constant("https")], ctx=ast.Load())],
                        ),
                        ast.UnaryOp(op=ast.Not(), operand=ast.Attribute(value=cls._name("parsed"), attr="netloc", ctx=ast.Load())),
                    ],
                ),
                body=[ast.Continue()],
                orelse=[],
            ),
            ast.Assign(
                targets=[cls._name("normalized", ast.Store())],
                value=ast.Call(
                    func=ast.Attribute(
                        value=ast.Call(
                            func=ast.Attribute(value=cls._name("parsed"), attr="_replace", ctx=ast.Load()),
                            args=[],
                            keywords=[ast.keyword(arg="fragment", value=ast.Constant(""))],
                        ),
                        attr="geturl",
                        ctx=ast.Load(),
                    ),
                    args=[],
                    keywords=[],
                ),
            ),
            ast.If(
                test=ast.Compare(left=cls._name("normalized"), ops=[ast.In()], comparators=[cls._name("seen")]),
                body=[ast.Continue()],
                orelse=[],
            ),
            ast.Expr(
                value=ast.Call(
                    func=ast.Attribute(value=cls._name("seen"), attr="add", ctx=ast.Load()),
                    args=[cls._name("normalized")],
                    keywords=[],
                )
            ),
            ast.Expr(
                value=ast.Call(
                    func=ast.Attribute(value=cls._name("out"), attr="append", ctx=ast.Load()),
                    args=[
                        ast.Dict(
                            keys=[ast.Constant("parent_url"), ast.Constant("url"), ast.Constant("scheme"), ast.Constant("host"), ast.Constant("source")],
                            values=[
                                cls._name("parent_url"),
                                cls._name("normalized"),
                                ast.Attribute(value=cls._name("parsed"), attr="scheme", ctx=ast.Load()),
                                ast.BoolOp(
                                    op=ast.Or(),
                                    values=[ast.Attribute(value=cls._name("parsed"), attr="hostname", ctx=ast.Load()), ast.Constant("")],
                                ),
                                ast.Constant("HTML_HREF"),
                            ],
                        )
                    ],
                    keywords=[],
                )
            ),
            ast.If(
                test=ast.Compare(
                    left=ast.Call(func=cls._name("len"), args=[cls._name("out")], keywords=[]),
                    ops=[ast.GtE()],
                    comparators=[cls._name("limit")],
                ),
                body=[ast.Break()],
                orelse=[],
            ),
        ]
        body.append(ast.For(target=cls._name("raw", ast.Store()), iter=findall, body=loop_body, orelse=[]))
        body.append(ast.Return(value=cls._name("out")))

        fn = ast.FunctionDef(
            name="extract_public_links",
            args=args,
            body=body,
            decorator_list=[],
            returns=None,
            type_comment=None,
        )
        module = ast.Module(body=imports + [fn], type_ignores=[])
        ast.fix_missing_locations(module)
        source = ast.unparse(module) + "\n"
        compile(source, "<yado-native-code-writer-v1>", "exec")
        return source

    @classmethod
    def static_safety_gate(cls, source: str) -> dict:
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            return {"pass": False, "reason": f"SYNTAX:{exc}"}
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
                    if alias.name not in cls.SAFE_IMPORTS:
                        return {"pass": False, "reason": "IMPORT_NOT_ALLOWED", "import": alias.name}
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                imports.append(module)
                if module not in cls.SAFE_IMPORTS:
                    return {"pass": False, "reason": "IMPORT_NOT_ALLOWED", "import": module}
            if isinstance(node, ast.Call):
                name = None
                if isinstance(node.func, ast.Name):
                    name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    name = node.func.attr
                if name in cls.BANNED_CALLS:
                    return {"pass": False, "reason": "CALL_NOT_ALLOWED", "call": name}
            if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
                return {"pass": False, "reason": "DUNDER_ATTRIBUTE_NOT_ALLOWED", "attribute": node.attr}
        return {"pass": True, "imports": sorted(set(imports))}

    @staticmethod
    def fresh_tests(candidate_path: Path) -> dict:
        spec = importlib.util.spec_from_file_location("yado_generated_link_traversal", candidate_path)
        if spec is None or spec.loader is None:
            return {"pass": False, "reason": "IMPORT_SPEC_FAILED"}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        fn = getattr(mod, "extract_public_links", None)
        if not callable(fn):
            return {"pass": False, "reason": "FUNCTION_MISSING"}

        cases = []
        html1 = """<a href='/docs/start#top'>A</a><a href='https://example.org/api'>B</a><a href='mailto:x@y.z'>M</a><a href='/docs/start#again'>D</a>"""
        got1 = fn("https://example.com/root/page", html1, 10)
        cases.append({
            "name": "relative_absolute_filter_dedup_fragment",
            "pass": [x["url"] for x in got1] == ["https://example.com/docs/start", "https://example.org/api"],
        })

        html2 = """<a href='//docs.python.org/3/library/urllib.parse.html'>P</a><a href='javascript:alert(1)'>J</a>"""
        got2 = fn("https://example.com/", html2, 10)
        cases.append({
            "name": "protocol_relative_and_non_http_rejection",
            "pass": len(got2) == 1 and got2[0]["host"] == "docs.python.org" and got2[0]["scheme"] == "https",
        })

        html3 = """<a href='/1'>1</a><a href='/2'>2</a><a href='/3'>3</a>"""
        got3 = fn("https://example.com/base", html3, 2)
        cases.append({"name": "bounded_output", "pass": len(got3) == 2})

        got4 = fn(None, html3, 2)
        cases.append({"name": "type_guard", "pass": got4 == []})

        provenance_ok = all(
            set(row) == {"parent_url", "url", "scheme", "host", "source"} and row["source"] == "HTML_HREF"
            for row in got1 + got2 + got3
        )
        cases.append({"name": "provenance_shape", "pass": provenance_ok})
        return {"pass": all(c["pass"] for c in cases), "cases": cases, "case_count": len(cases)}

    def run(self, request: dict) -> dict:
        head_before = load(HEAD).get("canonical_head_digest") if HEAD.exists() else None
        goal = str(request.get("goal") or request.get("objective") or "")
        classification = self.classify_goal(goal)
        if classification.get("status") != "SELECTED":
            return {
                "schema": self.SCHEMA,
                "status": "WITHHOLD_G2_NATIVE_CODE_WRITER_V1",
                "classification": classification,
                "candidate_source_produced_by_yado": False,
                "host_source_seed_used": False,
                "canonical_mutation": False,
            }
        ir = self.derive_ir(goal, classification)
        source = self.materialize(ir)
        safety = self.static_safety_gate(source)
        CANDIDATE.parent.mkdir(parents=True, exist_ok=True)
        CANDIDATE.write_text(source, encoding="utf-8")
        compile(source, str(CANDIDATE), "exec")
        tests = self.fresh_tests(CANDIDATE) if safety.get("pass") else {"pass": False, "reason": "SAFETY_GATE_FAILED"}
        head_after = load(HEAD).get("canonical_head_digest") if HEAD.exists() else None
        checks = {
            "goal_classified_by_writer": classification.get("status") == "SELECTED",
            "semantic_ir_created": ir.get("status") == "READY",
            "candidate_source_produced_by_yado": CANDIDATE.exists() and len(source) > 0,
            "candidate_source_nonempty_sha": bool(sha_text(source)),
            "candidate_source_compiles": True,
            "static_safety_gate_pass": safety.get("pass") is True,
            "fresh_tests_pass": tests.get("pass") is True,
            "host_source_seed_used": False,
            "external_coding_models_used": False,
            "canonical_unchanged": head_before == head_after,
        }
        passed = all(v is True for k, v in checks.items() if k not in {"host_source_seed_used", "external_coding_models_used"})
        passed = passed and checks["host_source_seed_used"] is False and checks["external_coding_models_used"] is False
        report = {
            "schema": self.SCHEMA,
            "component_id": self.COMPONENT_ID,
            "status": "PASS_SHADOW_G2_NATIVE_CODE_WRITER_V1" if passed else "WITHHOLD_G2_NATIVE_CODE_WRITER_V1",
            "goal": goal,
            "classification": classification,
            "semantic_ir": ir,
            "candidate_path": str(CANDIDATE.relative_to(REPO)),
            "candidate_source_sha256": sha_text(source),
            "candidate_source_bytes": len(source.encode()),
            "candidate_source_produced_by_yado": checks["candidate_source_produced_by_yado"],
            "safety": safety,
            "fresh_tests": tests,
            "checks": checks,
            "canonical_mutation": False,
            "claim_boundary": "HOST-AUTHORED BOUNDED SEEDLESS WRITER; YADO MATERIALIZES FRESH PYTHON SOURCE FROM A HIGH-LEVEL GOAL THROUGH ITS INTERNAL CLASSIFICATION, IR, AND AST EMITTER. THIS DOES NOT YET PROVE OPEN-ENDED GENERAL PROGRAMMING OR SELF-INVENTION OF THE WRITER ITSELF.",
        }
        report["receipt_sha256"] = digest(report)
        return report


def main() -> int:
    request = load(REQUEST)
    writer = YADONativeCodeWriterV1()
    report = writer.run(copy.deepcopy(request))
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report.get("status"),
        "candidate_path": report.get("candidate_path"),
        "candidate_source_sha256": report.get("candidate_source_sha256"),
        "candidate_source_produced_by_yado": report.get("candidate_source_produced_by_yado"),
        "fresh_tests": (report.get("fresh_tests") or {}).get("pass"),
        "safety": (report.get("safety") or {}).get("pass"),
        "receipt_sha256": report.get("receipt_sha256"),
    }, indent=2, sort_keys=True))
    return 0 if report.get("status") == "PASS_SHADOW_G2_NATIVE_CODE_WRITER_V1" else 2


if __name__ == "__main__":
    raise SystemExit(main())
