from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import yado_core_v2_5_unified as unified_mod
from yado_core_v2_5_unified import CycleRequest, CycleTask
from yado_core_v3_0_rc6_r6_schema_adaptation import UnifiedYADOKernelV30RC6R6SchemaAdaptation
from yado_phase_a_shadow import Case
from yado_primitive_genesis_cycle1 import freeze
from yado_stateful_frontier_repair_cycle1 import expr_complexity
from yado_stateful_frontier_repair_cycle2 import FrontierPortfolioInducer, Score

ROOT = Path(__file__).resolve().parent
DB = ROOT / 'yado_observe_stateful_frontier_cycle4.db'
REPORT = ROOT / 'yado_stateful_frontier_repair_cycle4_report.json'


def cj(x: Any) -> str:
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def sha(x: Any) -> str:
    return hashlib.sha256(cj(x).encode('utf-8')).hexdigest()


def vexpr_complexity(e: Any) -> int:
    if not isinstance(e, (list, tuple)) or not e:
        return 1
    return 1 + sum(vexpr_complexity(x) for x in e[1:])


def eval_vexpr(e: Any, item: Any, states: Sequence[Any]) -> Any:
    if not isinstance(e, (list, tuple)) or not e:
        return e
    op = e[0]
    if op == 'ITEM':
        return item
    if op == 'STATE':
        return states[int(e[1])]
    if op == 'CONST':
        return e[1]
    if op == 'ADD':
        return eval_vexpr(e[1], item, states) + eval_vexpr(e[2], item, states)
    if op == 'SUB':
        return eval_vexpr(e[1], item, states) - eval_vexpr(e[2], item, states)
    if op == 'MUL':
        return eval_vexpr(e[1], item, states) * eval_vexpr(e[2], item, states)
    raise ValueError(op)


@dataclass(frozen=True)
class CoupledRegisterSchema:
    family: str
    arity: int
    initial_states: tuple[Any, ...]
    state_updates: tuple[Any, ...]
    output_mode: str = 'POST_UPDATE_STATE_VECTOR'
    origin: str = 'FAILURE_DERIVED_COUPLED_REGISTER_BANK'

    @property
    def digest(self) -> str:
        return sha(asdict(self))

    @property
    def complexity(self) -> int:
        return sum(vexpr_complexity(x) for x in self.state_updates) + sum(0 if x == 0 else 1 for x in self.initial_states)


class FailureDerivedCoupledRegisterInducer:
    FAMILY = 'COUPLED_REGISTER_BANK_TRANSDUCER'

    def __init__(self, complexity_penalty: float = 0.001):
        self.complexity_penalty = complexity_penalty

    @staticmethod
    def infer_arity(cases: Sequence[Case]) -> int | None:
        arity = None
        for c in cases:
            if not isinstance(c.input, list) or not isinstance(c.expected, list) or len(c.input) != len(c.expected):
                return None
            for y in c.expected:
                if not isinstance(y, (list, tuple)) or len(y) < 2:
                    return None
                if arity is None:
                    arity = len(y)
                elif len(y) != arity:
                    return None
        return arity

    @staticmethod
    def expressions(arity: int) -> list[Any]:
        atoms = [['ITEM']] + [['STATE', i] for i in range(arity)] + [['CONST', 0], ['CONST', 1], ['CONST', -1]]
        exprs = list(atoms)
        for op in ('ADD', 'SUB', 'MUL'):
            for a in atoms:
                for b in atoms:
                    exprs.append([op, a, b])
        out, seen = [], set()
        for e in exprs:
            k = cj(e)
            if k not in seen:
                seen.add(k); out.append(e)
        return out

    @staticmethod
    def execute(schema: CoupledRegisterSchema, value: Any) -> Any:
        if not isinstance(value, list):
            raise TypeError('sequence input required')
        states = list(schema.initial_states)
        out = []
        for item in value:
            old = list(states)
            states = [eval_vexpr(expr, item, old) for expr in schema.state_updates]
            out.append(list(states))
        return out

    def _coord_exact(self, coord: int, initial_states: Sequence[Any], expr: Any, cases: Sequence[Case]) -> bool:
        for c in cases:
            states = list(initial_states)
            for item, expected in zip(c.input, c.expected):
                old = list(states)
                try:
                    # Candidate coordinate is evaluated against the actual old vector
                    # implied by the revealed expected trajectory. This makes the
                    # coordinate test valid without selecting on blind data.
                    got = eval_vexpr(expr, item, old)
                except Exception:
                    return False
                if freeze(got) != freeze(expected[coord]):
                    return False
                # Advance the full old-state vector with revealed previous output.
                states = list(expected)
        return True

    def search(self, cases: Sequence[Case]):
        arity = self.infer_arity(cases)
        if arity is None:
            return None, 0
        exprs = self.expressions(arity)
        best = None
        generated = 0
        for initials in itertools.product((0, 1, -1), repeat=arity):
            winners = []
            feasible = True
            for coord in range(arity):
                cw = []
                for expr in exprs:
                    generated += 1
                    if self._coord_exact(coord, initials, expr, cases):
                        cross_ref = any(isinstance(x, list) and x[:1] == ['STATE'] and int(x[1]) != coord for x in _walk(expr))
                        cw.append((vexpr_complexity(expr), 0 if cross_ref else 1, cj(expr), expr))
                if not cw:
                    feasible = False
                    break
                cw.sort(key=lambda x: (x[0], x[1], x[2]))
                winners.append(cw[0][3])
            if not feasible:
                continue
            schema = CoupledRegisterSchema(self.FAMILY, arity, tuple(initials), tuple(winners))
            sc = self.score(schema, cases)
            if sc.exact != 1.0:
                continue
            # Require at least one genuine cross-register dependency, otherwise
            # the older factored family should own the solution.
            if not any(_has_cross_ref(expr, i) for i, expr in enumerate(schema.state_updates)):
                continue
            key = (sc.exact, sc.mdl, -schema.complexity, schema.digest)
            if best is None or key > (best.exact, best.mdl, -best.schema.complexity, best.schema.digest):
                best = sc
        return best, generated

    def score(self, schema: CoupledRegisterSchema, cases: Sequence[Case]) -> Score:
        passed, failures = 0, []
        for c in cases:
            try:
                ok = freeze(self.execute(schema, c.input)) == freeze(c.expected)
            except Exception:
                ok = False
            if ok: passed += 1
            else: failures.append(c.case_id)
        exact = passed / max(1, len(cases))
        return Score(schema, exact, exact - self.complexity_penalty * schema.complexity, failures)


def _walk(e: Any):
    if isinstance(e, list):
        yield e
        for x in e[1:]:
            yield from _walk(x)


def _has_cross_ref(e: Any, coord: int) -> bool:
    for x in _walk(e):
        if x[:1] == ['STATE'] and int(x[1]) != coord:
            return True
    return False


@dataclass(frozen=True)
class FiniteTransitionSchema:
    family: str
    initial_state: Any
    transitions: tuple[tuple[str, str, Any], ...]
    output_mode: str = 'POST_UPDATE_STATE'
    origin: str = 'FAILURE_DERIVED_FINITE_TRANSITION_TABLE'

    @property
    def digest(self) -> str:
        return sha(asdict(self))

    @property
    def complexity(self) -> int:
        return len(self.transitions) + (0 if self.initial_state == 0 else 1)

    def transition_map(self) -> dict[tuple[str, str], Any]:
        return {(a, b): c for a, b, c in self.transitions}


class FailureDerivedFiniteTransitionInducer:
    FAMILY = 'FINITE_DETERMINISTIC_TRANSITION_TABLE'

    def __init__(self, complexity_penalty: float = 0.001):
        self.complexity_penalty = complexity_penalty

    @staticmethod
    def _candidate_initials(cases: Sequence[Case]) -> list[Any]:
        vals = [0, 1, -1]
        for c in cases:
            if isinstance(c.expected, list):
                vals.extend(c.expected)
        out, seen = [], set()
        for v in vals:
            k = cj(v)
            if k not in seen:
                seen.add(k); out.append(v)
        return out

    @staticmethod
    def _derive(cases: Sequence[Case], initial: Any):
        table: dict[tuple[str, str], Any] = {}
        conflict = False
        observed_states = {cj(initial)}
        for c in cases:
            if not isinstance(c.input, list) or not isinstance(c.expected, list) or len(c.input) != len(c.expected):
                return None
            state = initial
            for item, nxt in zip(c.input, c.expected):
                key = (cj(state), cj(item))
                if key in table and freeze(table[key]) != freeze(nxt):
                    conflict = True; break
                table[key] = nxt
                observed_states.add(cj(nxt))
                state = nxt
            if conflict: break
        if conflict:
            return None
        # Require actual mode/state dependence: at least one input symbol has
        # different next states depending on the previous state.
        by_item: dict[str, set[str]] = {}
        for (s, item), nxt in table.items():
            by_item.setdefault(item, set()).add(cj(nxt))
        state_dependent = any(len(v) > 1 for v in by_item.values())
        if not state_dependent or len(observed_states) < 3:
            return None
        return table

    @staticmethod
    def execute(schema: FiniteTransitionSchema, value: Any) -> Any:
        if not isinstance(value, list):
            raise TypeError('sequence input required')
        table = schema.transition_map()
        state = schema.initial_state
        out = []
        for item in value:
            key = (cj(state), cj(item))
            if key not in table:
                raise KeyError(f'unseen transition {key}')
            state = table[key]
            out.append(state)
        return out

    def search(self, cases: Sequence[Case]):
        best = None; generated = 0
        for initial in self._candidate_initials(cases):
            generated += 1
            table = self._derive(cases, initial)
            if table is None:
                continue
            transitions = tuple(sorted(((s, i, nxt) for (s, i), nxt in table.items()), key=lambda x: (x[0], x[1], cj(x[2]))))
            schema = FiniteTransitionSchema(self.FAMILY, initial, transitions)
            sc = self.score(schema, cases)
            if sc.exact != 1.0:
                continue
            key = (sc.exact, sc.mdl, -schema.complexity, schema.digest)
            if best is None or key > (best.exact, best.mdl, -best.schema.complexity, best.schema.digest):
                best = sc
        return best, generated

    def score(self, schema: FiniteTransitionSchema, cases: Sequence[Case]) -> Score:
        passed, failures = 0, []
        for c in cases:
            try:
                ok = freeze(self.execute(schema, c.input)) == freeze(c.expected)
            except Exception:
                ok = False
            if ok: passed += 1
            else: failures.append(c.case_id)
        exact = passed / max(1, len(cases))
        return Score(schema, exact, exact - self.complexity_penalty * schema.complexity, failures)


class FrontierPortfolioV2:
    def __init__(self):
        self.old = FrontierPortfolioInducer()
        self.coupled = FailureDerivedCoupledRegisterInducer()
        self.fsm = FailureDerivedFiniteTransitionInducer()

    def search(self, cases: Sequence[Case]):
        old, n0 = self.old.search(cases)
        if old is not None and old.exact == 1.0:
            return old, n0
        c, n1 = self.coupled.search(cases)
        if c is not None and c.exact == 1.0:
            return c, n0 + n1
        f, n2 = self.fsm.search(cases)
        if f is not None and f.exact == 1.0:
            return f, n0 + n1 + n2
        candidates = [x for x in (old, c, f) if x is not None]
        if not candidates:
            return None, n0 + n1 + n2
        candidates.sort(key=lambda sc: (sc.exact, sc.mdl, -sc.schema.complexity, getattr(sc.schema, 'digest', '')), reverse=True)
        return candidates[0], n0 + n1 + n2

    def score(self, schema: Any, cases: Sequence[Case]):
        if isinstance(schema, CoupledRegisterSchema): return self.coupled.score(schema, cases)
        if isinstance(schema, FiniteTransitionSchema): return self.fsm.score(schema, cases)
        return self.old.score(schema, cases)

    def execute(self, schema: Any, value: Any):
        if isinstance(schema, CoupledRegisterSchema): return self.coupled.execute(schema, value)
        if isinstance(schema, FiniteTransitionSchema): return self.fsm.execute(schema, value)
        return self.old.execute(schema, value)


def req(name: str, train, blind, live, expected):
    return CycleRequest(
        resource_id='github:microsoft/prose:tutorial',
        resource_query='failure-driven representation expansion beyond independent registers; infer cross-state dependencies or finite transition structure from revealed evidence',
        actions=[
            {'id':'z7','role':'COMMIT'},{'id':'z4','role':'TEST'},{'id':'z2','role':'DIAGNOSE'},
            {'id':'z6','role':'LEARN'},{'id':'z1','role':'OBSERVE'},{'id':'z5','role':'VERIFY'},{'id':'z3','role':'HYPOTHESIZE'},
        ],
        features={'blind':0.0,'ablation_drop':0.0,'restore':0.0,'integration_gap':0.0},
        task=CycleTask(name=name, train=train, blind=blind, live_input=live, expected_live=expected),
    )


def requests():
    linked = req('linked_register_running_sum_and_previous_sum', [
        Case('L-T1',[2,3,4],[[2,0],[5,2],[9,5]]),
        Case('L-T2',[1,5,2],[[1,0],[6,1],[8,6]]),
        Case('L-T3',[-1,2,3],[[-1,0],[1,-1],[4,1]]),
    ], [
        Case('L-B1',[3,2,5],[[3,0],[5,3],[10,5]]),
        Case('L-B2',[2,-2,4],[[2,0],[0,2],[4,0]]),
    ], [4,1,3], [[4,0],[5,4],[8,5]])

    linked2 = req('linked_register_running_product_and_previous_product', [
        Case('LP-T1',[2,3,4],[[2,1],[6,2],[24,6]]),
        Case('LP-T2',[1,5,2],[[1,1],[5,1],[10,5]]),
        Case('LP-T3',[-1,2,3],[[-1,1],[-2,-1],[-6,-2]]),
    ], [
        Case('LP-B1',[3,2,5],[[3,1],[6,3],[30,6]]),
        Case('LP-B2',[2,-2,4],[[2,1],[-4,2],[-16,-4]]),
    ], [4,2,3], [[4,1],[8,4],[24,8]])

    fsm = req('finite_mode_mod3_pulse_counter', [
        Case('F-T1',[1,1,1,0],[1,2,0,0]),
        Case('F-T2',[1,0,1,0,1],[1,1,2,2,0]),
        Case('F-T3',[0,1,0,1,1],[0,1,1,2,0]),
    ], [
        Case('F-B1',[1,0,0,1,1,0],[1,1,1,2,0,0]),
        Case('F-B2',[0,0,1,1,0,1],[0,0,1,2,2,0]),
    ], [1,1,0,1,0,1], [1,2,2,0,0,1])

    fsm2 = req('finite_mode_reverse_mod3_pulse_counter', [
        Case('R-T1',[1,1,1,0],[2,1,0,0]),
        Case('R-T2',[1,0,1,0,1],[2,2,1,1,0]),
        Case('R-T3',[0,1,0,1,1],[0,2,2,1,0]),
    ], [
        Case('R-B1',[1,0,0,1,1,0],[2,2,2,1,0,0]),
        Case('R-B2',[0,0,1,1,0,1],[0,0,2,1,1,0]),
    ], [1,1,0,1,0,1], [2,1,1,0,0,2])
    return linked, linked2, fsm, fsm2


def mechanism(r: Mapping[str, Any]) -> dict[str, Any]:
    for s in r.get('trace', []):
        if s.get('stage') == 'EXECUTION':
            return dict(s.get('action') or {})
    return {}


def main() -> int:
    tasks = requests()
    old = FrontierPortfolioInducer()
    baselines = {}
    for r in tasks:
        b, n = old.search(r.task.train)
        baselines[r.task.name] = {
            'generated': n,
            'best_train_exact': None if b is None else b.exact,
            'best_family': None if b is None else getattr(b.schema, 'family', None),
        }

    if DB.exists(): DB.unlink()
    old_binding = unified_mod.FailureDrivenSchemaInducer
    unified_mod.FailureDrivenSchemaInducer = FrontierPortfolioV2
    try:
        k = UnifiedYADOKernelV30RC6R6SchemaAdaptation(str(DB))
        try:
            rows = []
            for r in tasks:
                good = k.run_causal_cycle(r)
                abl = k.run_causal_cycle(r, ablate={'MECHANISM'})
                rows.append((r, good, abl))
            snap = k.unified_snapshot()
        finally:
            k.close()
    finally:
        unified_mod.FailureDrivenSchemaInducer = old_binding

    detail = []; all_pass = True
    for r, g, a in rows:
        m = mechanism(g); schema = m.get('schema') or {}
        passed = (
            g.get('cycle_success') is True and g.get('blind_score') == 1.0 and
            g.get('ablation_score') == 0.0 and g.get('restore_score') == 1.0 and
            a.get('cycle_success') is False
        )
        all_pass = all_pass and passed
        detail.append({
            'task': r.task.name,
            'cycle_id': g.get('cycle_id'),
            'cycle_success': g.get('cycle_success'),
            'old_portfolio_baseline': baselines[r.task.name],
            'family': schema.get('family'),
            'schema': schema,
            'blind': g.get('blind_score'),
            'ablation': g.get('ablation_score'),
            'restore': g.get('restore_score'),
            'live_output': g.get('live_output'),
            'expected_live': g.get('expected_live'),
            'learning_closed': g.get('learning_closed'),
            'mechanism_ablation_cycle_success': a.get('cycle_success'),
        })

    report = {
        'schema': 'yado.stateful_frontier_repair.cycle4.v1',
        'status': 'SHADOW_SUPPORTED_COUPLED_STATE_AND_FINITE_MODE_EXPANSION' if all_pass else 'WITHHOLD',
        'old_portfolio_baseline': baselines,
        'failure_diagnosis': {
            'coupled_registers': 'INDEPENDENT_REGISTER_UPDATES_CANNOT_REFERENCE_OTHER_OLD_STATE_COMPONENTS',
            'finite_modes': 'ARITHMETIC_OR_SINGLE_GUARD_REGISTER_GRAMMAR_CANNOT_EXPRESS_REPEATED_MODE_DEPENDENT_WRAP_TRANSITIONS',
        },
        'derived_representation_warrants': {
            'coupled_register_bank': {
                'arity_inferred_from_revealed_output_structure': True,
                'cross_register_dependency_required_for_acceptance': True,
                'specific_dependency_graph_supplied': False,
                'specific_update_programs_synthesized_from_train': True,
            },
            'finite_transition_table': {
                'initial_state_selected_from_revealed_evidence': True,
                'transition_table_derived_from_revealed_pairs': True,
                'requires_state_dependent_same_input_behavior': True,
                'specific_modulo_rule_supplied': False,
            },
        },
        'cycles': detail,
        'observation_snapshot': snap,
        'claim_boundary': {
            'canonical_durable_head_modified': False,
            'shadow_runtime_binding_modified_only': True,
            'coupled_register_interpreter_host_supplied': True,
            'finite_transition_interpreter_host_supplied': True,
            'expression_atoms_and_search_controller_host_supplied': True,
            'specific_cross_state_updates_data_derived': True,
            'specific_transition_tables_data_derived': True,
            'blind_used_for_selection': False,
            'unrestricted_state_machine_invention_proven': False,
            'agi_or_subjective_consciousness_claim': False,
        },
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if all_pass else 2


if __name__ == '__main__':
    raise SystemExit(main())
