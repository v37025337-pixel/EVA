from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import yado_core_v2_5_unified as unified_mod
from yado_core_v2_5_unified import CycleRequest, CycleTask
from yado_core_v3_0_rc6_r6_schema_adaptation import UnifiedYADOKernelV30RC6R6SchemaAdaptation
from yado_phase_a_shadow import Case
from yado_primitive_genesis_cycle1 import FailureDrivenSchemaInducer as SliceInducer, baseline_score, freeze

ROOT = Path(__file__).resolve().parent
OBS_DB = ROOT / 'yado_observe_run.db'
SHADOW_DB = ROOT / 'yado_observe_stateful_repair.db'
REPORT = ROOT / 'yado_stateful_frontier_repair_cycle1_report.json'
FAIL_CYCLE = 'CYCLE-60de9be43a4f'


def cj(x: Any) -> str:
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def sha(x: Any) -> str:
    return hashlib.sha256(cj(x).encode('utf-8')).hexdigest()


def expr_complexity(e: Any) -> int:
    if not isinstance(e, (list, tuple)) or not e:
        return 1
    return 1 + sum(expr_complexity(x) for x in e[1:])


def eval_expr(e: Any, item: Any, state: Any) -> Any:
    if not isinstance(e, (list, tuple)) or not e:
        return e
    op = e[0]
    if op == 'ITEM': return item
    if op == 'STATE': return state
    if op == 'CONST': return e[1]
    if op == 'TRUE': return True
    if op == 'ADD': return eval_expr(e[1], item, state) + eval_expr(e[2], item, state)
    if op == 'SUB': return eval_expr(e[1], item, state) - eval_expr(e[2], item, state)
    if op == 'MUL': return eval_expr(e[1], item, state) * eval_expr(e[2], item, state)
    raise ValueError(f'unsupported op: {op}')


@dataclass(frozen=True)
class StatefulRegisterSchema:
    family: str
    output_mode: str
    guard: Any
    emit_expr: Any
    state_update: Any
    initial_state: Any
    origin: str = 'FAILURE_DERIVED_STATEFUL_REGISTER'

    @property
    def digest(self) -> str:
        return sha(asdict(self))

    @property
    def complexity(self) -> int:
        return (
            expr_complexity(self.guard)
            + expr_complexity(self.emit_expr)
            + expr_complexity(self.state_update)
            + (0 if self.initial_state == 0 else 1)
        )


@dataclass
class Score:
    schema: Any
    exact: float
    mdl: float
    failures: list[str]


class FailureDerivedStatefulRegisterInducer:
    FAMILY = 'STATEFUL_REGISTER_TRANSDUCER'

    def __init__(self, complexity_penalty: float = 0.001):
        self.complexity_penalty = complexity_penalty

    @staticmethod
    def execute(schema: StatefulRegisterSchema, value: Any) -> Any:
        if not isinstance(value, list):
            raise TypeError('sequence input required')
        state = schema.initial_state
        out = []
        for item in value:
            if bool(eval_expr(schema.guard, item, state)):
                out.append(eval_expr(schema.emit_expr, item, state))
            state = eval_expr(schema.state_update, item, state)
        return out if schema.output_mode == 'LIST' else state

    @staticmethod
    def _state_requirement_witness(cases: Sequence[Case]) -> dict[str, Any]:
        # If the same current item maps to different outputs within the revealed
        # experience, a stateless item->output map cannot explain it.
        seen: dict[str, set[str]] = {}
        examples = []
        length_aligned = True
        for c in cases:
            if not isinstance(c.input, list) or not isinstance(c.expected, list) or len(c.input) != len(c.expected):
                length_aligned = False
                continue
            for i, (x, y) in enumerate(zip(c.input, c.expected)):
                k = cj(x)
                seen.setdefault(k, set()).add(cj(y))
                examples.append({'case_id': c.case_id, 'index': i, 'item': x, 'output': y})
        collisions = {k: sorted(v) for k, v in seen.items() if len(v) > 1}
        return {
            'length_aligned_emit_per_item': length_aligned,
            'same_item_different_output_collisions': collisions,
            'state_required_by_collision_witness': bool(length_aligned and collisions),
            'observations': len(examples),
        }

    @staticmethod
    def _expressions() -> list[Any]:
        atoms = [['ITEM'], ['STATE'], ['CONST', 0], ['CONST', 1], ['CONST', -1]]
        exprs = list(atoms)
        for op in ('ADD', 'SUB', 'MUL'):
            for a in atoms:
                for b in atoms:
                    exprs.append([op, a, b])
        # deterministic structural de-duplication
        out, seen = [], set()
        for e in exprs:
            k = cj(e)
            if k not in seen:
                seen.add(k); out.append(e)
        return out

    def generate_candidates(self, cases: Sequence[Case]) -> Iterable[StatefulRegisterSchema]:
        witness = self._state_requirement_witness(cases)
        if not witness['state_required_by_collision_witness']:
            return
        exprs = self._expressions()
        # Initial states are generic algebraic identities/small neutral seeds,
        # not inferred from blind data and not task-labelled.
        for initial in (0, 1, -1):
            for emit in exprs:
                for update in exprs:
                    # A stateful repair must actually use STATE somewhere;
                    # otherwise it is just a stateless remapping in disguise.
                    if 'STATE' not in cj(emit) and 'STATE' not in cj(update):
                        continue
                    yield StatefulRegisterSchema(
                        family=self.FAMILY,
                        output_mode='LIST',
                        guard=['TRUE'],
                        emit_expr=emit,
                        state_update=update,
                        initial_state=initial,
                    )

    def score(self, schema: StatefulRegisterSchema, cases: Sequence[Case]) -> Score:
        passed, failures = 0, []
        for c in cases:
            try:
                got = self.execute(schema, c.input)
                ok = freeze(got) == freeze(c.expected)
            except Exception:
                ok = False
            if ok: passed += 1
            else: failures.append(c.case_id)
        exact = passed / max(1, len(cases))
        return Score(schema, exact, exact - self.complexity_penalty * schema.complexity, failures)

    def search(self, cases: Sequence[Case]):
        best = None
        n = 0
        for cand in self.generate_candidates(cases) or []:
            n += 1
            sc = self.score(cand, cases)
            if best is None or (sc.exact, sc.mdl, -cand.complexity, cand.digest) > (
                best.exact, best.mdl, -best.schema.complexity, best.schema.digest
            ):
                best = sc
        return best, n


class PortfolioInducer:
    """Old slice inducer first; stateful register repair only after exact old-family failure."""
    def __init__(self):
        self.slice = SliceInducer()
        self.stateful = FailureDerivedStatefulRegisterInducer()

    def search(self, cases: Sequence[Case]):
        old, n_old = self.slice.search(cases)
        if old is not None and old.exact == 1.0:
            return old, n_old
        new, n_new = self.stateful.search(cases)
        if new is None:
            return old, n_old + n_new
        if old is None or (new.exact, new.mdl) > (old.exact, old.mdl):
            return new, n_old + n_new
        return old, n_old + n_new

    def score(self, schema: Any, cases: Sequence[Case]):
        if isinstance(schema, StatefulRegisterSchema):
            return self.stateful.score(schema, cases)
        return self.slice.score(schema, cases)

    def execute(self, schema: Any, value: Any):
        if isinstance(schema, StatefulRegisterSchema):
            return self.stateful.execute(schema, value)
        return self.slice.execute(schema, value)


def load_failure_request() -> tuple[CycleRequest, dict[str, Any], dict[str, Any]]:
    con = sqlite3.connect(OBS_DB)
    try:
        row = con.execute('select request_json,result_json,trace_json from unified_cycles where cycle_id=?', (FAIL_CYCLE,)).fetchone()
    finally:
        con.close()
    if not row:
        raise RuntimeError(f'failure cycle not found: {FAIL_CYCLE}')
    reqj, resj, tracej = map(json.loads, row)
    t = reqj['task']
    req = CycleRequest(
        resource_id=reqj['resource_id'], resource_query=reqj['resource_query'], actions=reqj['actions'], features=reqj['features'],
        task=CycleTask(
            name=t['name'],
            train=[Case(x['case_id'], x['input'], x['expected']) for x in t['train']],
            blind=[Case(x['case_id'], x['input'], x['expected']) for x in t['blind']],
            live_input=t['live_input'], expected_live=t['expected_live'],
        )
    )
    return req, resj, {'request': reqj, 'trace': tracej}


def product_transfer_request() -> CycleRequest:
    return CycleRequest(
        resource_id='github:microsoft/prose:tutorial',
        resource_query='program synthesis from examples after a stateful representation has been recovered; test transfer to another recurrence',
        actions=[
            {'id':'c7','role':'COMMIT'}, {'id':'c4','role':'TEST'}, {'id':'c2','role':'DIAGNOSE'},
            {'id':'c6','role':'LEARN'}, {'id':'c1','role':'OBSERVE'}, {'id':'c5','role':'VERIFY'}, {'id':'c3','role':'HYPOTHESIZE'},
        ],
        features={'blind':0.0,'ablation_drop':0.0,'restore':0.0,'integration_gap':0.0},
        task=CycleTask(
            name='fresh_stateful_running_product_transfer',
            train=[
                Case('P-T1',[2,3,4],[2,6,24]),
                Case('P-T2',[2,2,2],[2,4,8]),
                Case('P-T3',[-1,2,3],[-1,-2,-6]),
            ],
            blind=[
                Case('P-B1',[3,2,5],[3,6,30]),
                Case('P-B2',[-1,-2,-3],[-1,2,-6]),
            ],
            live_input=[4,2,3], expected_live=[4,8,24],
        )
    )


def extract_mechanism(result: Mapping[str, Any]) -> dict[str, Any]:
    for step in result.get('trace', []):
        if step.get('stage') == 'EXECUTION':
            return dict(step.get('action') or {})
    return {}


def main() -> int:
    fail_req, prior_result, prior = load_failure_request()
    if prior_result.get('strategy') != 'EXPAND_REPRESENTATION' or prior_result.get('live_output') is not None:
        raise RuntimeError('expected a clean representation failure receipt')
    prior_exec = next(x for x in prior['trace'] if x.get('stage') == 'EXECUTION')
    if (prior_exec.get('action') or {}).get('verdict') != 'NO_SCHEMA':
        raise RuntimeError('expected NO_SCHEMA failure receipt')

    witness = FailureDerivedStatefulRegisterInducer._state_requirement_witness(fail_req.task.train)

    if SHADOW_DB.exists(): SHADOW_DB.unlink()
    # Shadow-only meta-routing repair: replace the active inducer binding for this
    # observation process. The canonical/durable head is not modified.
    old_binding = unified_mod.FailureDrivenSchemaInducer
    unified_mod.FailureDrivenSchemaInducer = PortfolioInducer
    try:
        system = UnifiedYADOKernelV30RC6R6SchemaAdaptation(str(SHADOW_DB))
        try:
            repaired = system.run_causal_cycle(fail_req)
            repaired_ablation = system.run_causal_cycle(fail_req, ablate={'MECHANISM'})
            transfer_req = product_transfer_request()
            transfer = system.run_causal_cycle(transfer_req)
            transfer_ablation = system.run_causal_cycle(transfer_req, ablate={'MECHANISM'})
            snapshot = system.unified_snapshot()
        finally:
            system.close()
    finally:
        unified_mod.FailureDrivenSchemaInducer = old_binding

    rep_action = extract_mechanism(repaired)
    tr_action = extract_mechanism(transfer)
    pass_repair = (
        repaired.get('cycle_success') is True
        and repaired.get('blind_score') == 1.0
        and repaired.get('ablation_score') == 0.0
        and repaired.get('restore_score') == 1.0
        and (rep_action.get('schema') or {}).get('family') == 'STATEFUL_REGISTER_TRANSDUCER'
    )
    pass_transfer = (
        transfer.get('cycle_success') is True
        and transfer.get('blind_score') == 1.0
        and transfer.get('ablation_score') == 0.0
        and transfer.get('restore_score') == 1.0
        and (tr_action.get('schema') or {}).get('family') == 'STATEFUL_REGISTER_TRANSDUCER'
    )
    report = {
        'schema':'yado.stateful_frontier_repair.cycle1.v1',
        'status':'SHADOW_SUPPORTED_ACTIVE_STATEFUL_ROUTING_REPAIR' if pass_repair and pass_transfer else 'WITHHOLD',
        'prior_failure':{
            'cycle_id':FAIL_CYCLE,
            'strategy':prior_result.get('strategy'),
            'verdict':(prior_exec.get('action') or {}).get('verdict'),
            'old_substrate_train_exact':prior_result.get('old_substrate_train_exact'),
            'live_output':prior_result.get('live_output'),
        },
        'self_audit':{
            'corrected_deficit':'ACTIVE_MECHANISM_ROUTING_GAP_TO_STATEFUL_SUBSTRATE',
            'historical_stateful_substrate_present':True,
            'active_v25_mechanism_was_slice_only':True,
            'failure_witness':witness,
            'decision':'RECOVER_AND_ROUTE_GENERIC_STATEFUL_REGISTER_REPRESENTATION_NOT_INVENT_DUPLICATE',
        },
        'repair_cycle':{
            'cycle_id':repaired.get('cycle_id'),
            'cycle_success':repaired.get('cycle_success'),
            'train_old':repaired.get('old_substrate_train_exact'),
            'blind':repaired.get('blind_score'),
            'ablation':repaired.get('ablation_score'),
            'restore':repaired.get('restore_score'),
            'live_output':repaired.get('live_output'),
            'expected_live':repaired.get('expected_live'),
            'learning_closed':repaired.get('learning_closed'),
            'mechanism':rep_action,
            'mechanism_ablation_cycle_success':repaired_ablation.get('cycle_success'),
        },
        'independent_stateful_transfer':{
            'task':transfer_req.task.name,
            'cycle_id':transfer.get('cycle_id'),
            'cycle_success':transfer.get('cycle_success'),
            'train_old':transfer.get('old_substrate_train_exact'),
            'blind':transfer.get('blind_score'),
            'ablation':transfer.get('ablation_score'),
            'restore':transfer.get('restore_score'),
            'live_output':transfer.get('live_output'),
            'expected_live':transfer.get('expected_live'),
            'learning_closed':transfer.get('learning_closed'),
            'mechanism':tr_action,
            'mechanism_ablation_cycle_success':transfer_ablation.get('cycle_success'),
        },
        'observation_snapshot':snapshot,
        'claim_boundary':{
            'canonical_durable_head_modified':False,
            'shadow_runtime_binding_modified_only':True,
            'specific_cumsum_operator_supplied':False,
            'specific_product_operator_supplied':False,
            'generic_register_interpreter_host_supplied':True,
            'generic_expression_grammar_host_supplied':True,
            'representation_need_derived_from_failure_evidence':True,
            'task_specific_programs_synthesized_from_train_only':True,
            'blind_used_for_selection':False,
            'general_stateful_program_synthesis_proven':False,
            'agi_or_consciousness_claim':False,
        }
    }
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if report['status'].startswith('SHADOW_SUPPORTED') else 2

if __name__=='__main__':
    raise SystemExit(main())
