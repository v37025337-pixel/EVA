from __future__ import annotations

from pathlib import Path
import ast
import copy
import hashlib
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
TARGET = ROOT / "yado_evolutionary_genome_v1.py"
ARMED = REPO / "candidates/g2-self-evolution/yado_evolutionary_genome_armed_v2.py"
SELF_CANDIDATE = REPO / "candidates/g2-self-evolution/yado_evolutionary_genome_self_candidate_v2.py"
RECEIPT = REPO / "candidates/g2-self-evolution/yado-native-controller-source-self-mutation-v2.json"

sys.path.insert(0, str(ROOT))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _method_node() -> ast.FunctionDef:
    src = '''
def native_self_mutation_source_candidate(self):
    source = open(__file__, encoding="utf-8").read()
    parent_sha256 = hashlib.sha256(source.encode("utf-8")).hexdigest()
    tree = ast.parse(source)
    changed = False
    semantic_change = None
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != "YADOEvolutionaryGenomeV1":
            continue
        for fn in node.body:
            if not isinstance(fn, ast.FunctionDef) or fn.name != "evolve_once":
                continue
            for stmt in fn.body:
                if not isinstance(stmt, ast.Assign):
                    continue
                if not any(isinstance(t, ast.Name) and t.id == "selected" for t in stmt.targets):
                    continue
                if not isinstance(stmt.value, ast.IfExp):
                    continue
                test_dump = ast.dump(stmt.value.test, include_attributes=False)
                key = None
                if "mutation_count" not in test_dump:
                    key = "mutation_count"
                elif "novel_gene_count" not in test_dump:
                    key = "novel_gene_count"
                if key is None:
                    return {
                        "source": None,
                        "candidate_source": None,
                        "reason": "SELF_MUTATION_GUARDS_EXHAUSTED",
                        "parent_sha256": parent_sha256,
                    }
                guard = ast.Compare(
                    left=ast.Call(
                        func=ast.Attribute(value=ast.Name(id="child", ctx=ast.Load()), attr="get", ctx=ast.Load()),
                        args=[ast.Constant(key), ast.Constant(0)],
                        keywords=[],
                    ),
                    ops=[ast.Gt()],
                    comparators=[ast.Constant(0)],
                )
                if isinstance(stmt.value.test, ast.BoolOp) and isinstance(stmt.value.test.op, ast.And):
                    stmt.value.test.values.append(guard)
                else:
                    stmt.value.test = ast.BoolOp(op=ast.And(), values=[stmt.value.test, guard])
                changed = True
                semantic_change = "REQUIRE_" + key.upper() + "_POSITIVE_FOR_CHILD_SELECTION"
                break
            if changed:
                break
        if changed:
            break
    if not changed:
        return {
            "source": None,
            "candidate_source": None,
            "reason": "EVOLVE_SELECTION_EXPRESSION_NOT_FOUND",
            "parent_sha256": parent_sha256,
        }
    ast.fix_missing_locations(tree)
    out = ast.unparse(tree) + "\\n"
    compile(out, "<yado-native-controller-self-candidate>", "exec")
    candidate_sha256 = hashlib.sha256(out.encode("utf-8")).hexdigest()
    return {
        "source": out,
        "candidate_source": out,
        "semantic_change": semantic_change,
        "parent_sha256": parent_sha256,
        "candidate_sha256": candidate_sha256,
        "canonical_mutation": False,
        "external_model_used": False,
        "downloaded_code_executed": False,
    }
'''
    node = ast.parse(src).body[0]
    assert isinstance(node, ast.FunctionDef)
    return node


def arm_controller_source(source: str) -> str:
    tree = ast.parse(source)
    target_class = None
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "YADOEvolutionaryGenomeV1":
            target_class = node
            break
    if target_class is None:
        raise RuntimeError("CONTROLLER_CLASS_NOT_FOUND")
    if any(isinstance(n, ast.FunctionDef) and n.name == "native_self_mutation_source_candidate" for n in target_class.body):
        return source
    target_class.body.append(_method_node())
    ast.fix_missing_locations(tree)
    out = ast.unparse(tree) + "\n"
    compile(out, "<yado-armed-controller>", "exec")
    return out


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("MODULE_SPEC_FAILURE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_parent(cls):
    component_digests = {
        "LOGIC": "logic-v2",
        "THINKING": "thinking-v2",
        "INTELLIGENCE": "intelligence-v3",
        "CODE": "code-v11",
    }
    return cls.parent_genome(
        head_digest="0" * 64,
        component_digests=component_digests,
        experience_digest="internet-evolution-cycle-v1",
    )


def semantic_noop_probe(cls):
    parent = make_parent(cls)
    controller = cls(parent, experience_sources=[{"role": "VERIFIED_INTERNET_EVOLUTION_CYCLE_V1"}])
    fake_child = copy.deepcopy(parent)
    fake_child["genome_id"] = "G2-NOOP-CHILD-PROBE"
    fake_child["mutation_count"] = 0
    fake_child["novel_gene_count"] = 0
    fake_child["genome_digest"] = "1" * 64
    controller.observe_parent_deficits = lambda: {}
    controller.mutate = lambda deficits: copy.deepcopy(fake_child)
    controller.evaluate = lambda p, c: {
        "parent": {"LOGIC": 0.0, "THINKING": 0.0, "INTELLIGENCE": 0.0, "CODE": 0.0},
        "child": {"LOGIC": 1.0, "THINKING": 1.0, "INTELLIGENCE": 1.0, "CODE": 1.0},
        "regression": {"LOGIC": True, "THINKING": True, "INTELLIGENCE": True, "CODE": True},
        "parent_mean": 0.0,
        "child_mean": 1.0,
        "fitness_gain": 1.0,
        "all_regressions_pass": True,
    }
    return controller.evolve_once()["selection"]


def normal_probe(cls):
    parent = make_parent(cls)
    controller = cls(parent, experience_sources=[{"role": "VERIFIED_INTERNET_EVOLUTION_CYCLE_V1"}])
    result = controller.evolve_once()
    return {
        "selection": result.get("selection"),
        "fitness_gain": (result.get("fitness") or {}).get("fitness_gain"),
        "all_regressions_pass": (result.get("fitness") or {}).get("all_regressions_pass"),
        "mutation_count": (result.get("child") or {}).get("mutation_count"),
        "novel_gene_count": (result.get("child") or {}).get("novel_gene_count"),
    }


def main() -> int:
    source = TARGET.read_text(encoding="utf-8")
    parent_sha = sha256_text(source)
    armed = arm_controller_source(source)
    armed_sha = sha256_text(armed)
    ARMED.parent.mkdir(parents=True, exist_ok=True)
    ARMED.write_text(armed, encoding="utf-8")

    armed_mod = load_module(ARMED, "yado_evolutionary_genome_armed_v2")
    armed_parent = make_parent(armed_mod.YADOEvolutionaryGenomeV1)
    armed_controller = armed_mod.YADOEvolutionaryGenomeV1(
        armed_parent,
        experience_sources=[
            {"role": "VERIFIED_INTERNET_EVOLUTION_CYCLE_V1"},
            {"role": "PRIOR_CONTROLLER_WITHHOLD", "next_required_capability": "NATIVE_SEMANTIC_SELF_MUTATION_OF_EVOLUTIONARY_CONTROLLER"},
        ],
    )
    emitted = armed_controller.native_self_mutation_source_candidate()
    self_source = emitted.get("candidate_source")
    if not isinstance(self_source, str) or not self_source.strip():
        raise RuntimeError("CONTROLLER_DID_NOT_EMIT_SOURCE")
    compile(self_source, str(SELF_CANDIDATE), "exec")
    SELF_CANDIDATE.write_text(self_source, encoding="utf-8")
    self_sha = sha256_text(self_source)

    parent_mod = load_module(TARGET, "yado_evolutionary_genome_parent_probe_v2")
    self_mod = load_module(SELF_CANDIDATE, "yado_evolutionary_genome_self_probe_v2")
    parent_noop = semantic_noop_probe(parent_mod.YADOEvolutionaryGenomeV1)
    self_noop = semantic_noop_probe(self_mod.YADOEvolutionaryGenomeV1)
    parent_normal = normal_probe(parent_mod.YADOEvolutionaryGenomeV1)
    self_normal = normal_probe(self_mod.YADOEvolutionaryGenomeV1)

    checks = {
        "host_bootstrap_arm_compiles": True,
        "host_bootstrap_arm_changed_source": armed_sha != parent_sha,
        "controller_self_emitted_candidate_source": True,
        "self_emitted_source_changed": self_sha not in {parent_sha, armed_sha},
        "self_emitted_source_compiles": True,
        "semantic_behavior_changed_on_noop_child": parent_noop == "CHILD" and self_noop == "PARENT",
        "normal_evolution_still_selects_child": self_normal.get("selection") == "CHILD",
        "normal_evolution_regressions_pass": self_normal.get("all_regressions_pass") is True,
        "canonical_mutation": False,
        "external_model_used": False,
        "downloaded_code_executed": False,
    }
    passed = all(v is True for k, v in checks.items() if k not in {"canonical_mutation", "external_model_used", "downloaded_code_executed"})
    passed = passed and not checks["canonical_mutation"] and not checks["external_model_used"] and not checks["downloaded_code_executed"]
    report = {
        "schema": "yado.native_controller_source_self_mutation.v2",
        "status": "PASS_SHADOW_NATIVE_CONTROLLER_SOURCE_SELF_MUTATION_V2" if passed else "WITHHOLD_NATIVE_CONTROLLER_SOURCE_SELF_MUTATION_V2",
        "target": str(TARGET.relative_to(REPO)),
        "armed_candidate": str(ARMED.relative_to(REPO)),
        "self_emitted_candidate": str(SELF_CANDIDATE.relative_to(REPO)),
        "parent_sha256": parent_sha,
        "armed_sha256": armed_sha,
        "self_emitted_sha256": self_sha,
        "self_emitted_semantic_change": emitted.get("semantic_change"),
        "parent_noop_selection": parent_noop,
        "self_candidate_noop_selection": self_noop,
        "parent_normal": parent_normal,
        "self_candidate_normal": self_normal,
        "checks": checks,
        "host_role": "BOOTSTRAP_ONLY: INSTALL A ZERO-ARG NATIVE SELF-MUTATION SOURCE-EMISSION ARM. THE SECOND-GENERATION SEMANTIC SOURCE MUTATION IS EMITTED BY THE ARMED CONTROLLER ITSELF.",
        "semantic_boundary": "DEVELOPMENT-BRANCH SOURCE SELF-MUTATION ONLY. NO CANONICAL MAIN WRITE, NO EXTERNAL MODEL, NO DOWNLOADED CODE EXECUTION. THIS CLOSES SOURCE EMISSION, NOT NEW-DIMENSION GENESIS.",
        "next_required_capability": "NATIVE_CONTROLLER_NEW_DIMENSION_GENESIS" if passed else "NATIVE_CONTROLLER_SOURCE_SELF_MUTATION_V2_REPAIR",
    }
    report["receipt_sha256"] = hashlib.sha256(json.dumps(report, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "semantic_change": report["self_emitted_semantic_change"],
        "parent_noop_selection": parent_noop,
        "self_candidate_noop_selection": self_noop,
        "normal_selection": self_normal.get("selection"),
        "self_emitted_sha256": self_sha,
        "next_required_capability": report["next_required_capability"],
        "receipt_sha256": report["receipt_sha256"],
    }, indent=2, sort_keys=True))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
