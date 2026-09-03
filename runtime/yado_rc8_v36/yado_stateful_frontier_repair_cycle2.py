from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import yado_core_v2_5_unified as unified_mod
from yado_core_v2_5_unified import CycleRequest, CycleTask
from yado_core_v3_0_rc6_r6_schema_adaptation import UnifiedYADOKernelV30RC6R6SchemaAdaptation
from yado_phase_a_shadow import Case
from yado_primitive_genesis_cycle1 import FailureDrivenSchemaInducer as SliceInducer, freeze
from yado_stateful_frontier_repair_cycle1 import (
    FailureDerivedStatefulRegisterInducer,
    StatefulRegisterSchema,
    eval_expr,
    expr_complexity,
)

ROOT = Path(__file__).resolve().parent
DB = ROOT / 'yado_observe_stateful_frontier_cycle2.db'
REPORT = ROOT / 'yado_stateful_frontier_repair_cycle2_report.json'


def cj(x: Any) -> str:
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def sha(x: Any) -> str:
    return hashlib.sha256(cj(x).encode('utf-8')).hexdigest()


@dataclass
class Score:
    schema: Any
    exact: float
    mdl: float
    failures: list[str]


@dataclass(frozen=True)
class FactoredRegisterSchema:
    family: str
    arity: int
    initial_states: tuple[Any, ...]
    state_updates: tuple[Any, ...]
    output_mode: str = 'POST_UPDATE_STATE_VECTOR'
    origin: str = 'FAILURE_DERIVED_FACTORED_REGISTER_BANK'

    @property
    def digest(self) -> str:
        return sha(asdict(self))

    @property
    def complexity(self) -> int:
        return sum(expr_complexity(x) for x in self.state_updates) + sum(0 if x == 0 else 1 for x in self.initial_states)


class FailureDerivedFactoredRegisterInducer:
    FAMILY = 'FACTORED_REGISTER_BANK_TRANSDUCER'

    def __init__(self, complexity_penalty: float = 0.001):
        self.complexity_penalty = complexity_penalty
        self.exprs = FailureDerivedStatefulRegisterInducer._expressions()

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
    def execute(schema: FactoredRegisterSchema, value: Any) -> Any:
        if not isinstance(value, list):
            raise TypeError('sequence input required')
        states = list(schema.initial_states)
        out = []
        for item in value:
            new_states = [eval_expr(expr, item, states[i]) for i, expr in enumerate(schema.state_updates)]
            states = new_states
            out.append(list(states))
        return out

    def _coord_exact(self, coord: int, initial: Any, expr: Any, cases: Sequence[Case]) -> bool:
        for c in cases:
            state = initial
            for item, expected in zip(c.input, c.expected):
                try:
                    state = eval_expr(expr, item, state)
                except Exception:
                    return False
                if freeze(state) != freeze(expected[coord]):
                    return False
        return True

    def search(self, cases: Sequence[Case]):
        arity = self.infer_arity(cases)
        if arity is None:
            return None, 0
        chosen_initials, chosen_updates = [], []
        generated = 0
        for coord in range(arity):
            winners = []
            for initial in (0, 1, -1):
                for expr in self.exprs:
                    generated += 1
                    if self._coord_exact(coord, initial, expr, cases):
                        winners.append((expr_complexity(expr) + (0 if initial == 0 else 1), cj(expr), initial, expr))
            if not winners:
                return None, generated
            winners.sort(key=lambda x: (x[0], x[1], cj(x[2])))
            _, _, initial, expr = winners[0]
            chosen_initials.append(initial); chosen_updates.append(expr)
        schema = FactoredRegisterSchema(self.FAMILY, arity, tuple(chosen_initials), tuple(chosen_updates))
        return self.score(schema, cases), generated

    def score(self, schema: FactoredRegisterSchema, cases: Sequence[Case]) -> Score:
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


@dataclass(frozen=True)
class GuardedRegisterSchema:
    family: str
    predicate: Any
    update_if_true: Any
    update_if_false: Any
    initial_state: Any
    output_mode: str = 'POST_UPDATE_STATE'
    origin: str = 'FAILURE_DERIVED_PREDICATE_GATED_REGISTER'

    @property
    def digest(self) -> str:
        return sha(asdict(self))

    @property
    def complexity(self) -> int:
        return 1 + expr_complexity(self.predicate) + expr_complexity(self.update_if_true) + expr_complexity(self.update_if_false) + (0 if self.initial_state == 0 else 1)


def eval_pred(p: Any, item: Any, state: Any) -> bool:
    if not isinstance(p, (list, tuple)) or not p:
        return bool(p)
    op = p[0]
    if op in ('GT', 'LT', 'EQ'):
        a = eval_expr(p[1], item, state); b = eval_expr(p[2], item, state)
        if op == 'GT': return a > b
        if op == 'LT': return a < b
        return a == b
    raise ValueError(op)


class FailureDerivedGuardedRegisterInducer:
    FAMILY = 'PREDICATE_GATED_REGISTER_TRANSDUCER'

    def __init__(self, complexity_penalty: float = 0.001):
        self.complexity_penalty = complexity_penalty
        self.exprs = FailureDerivedStatefulRegisterInducer._expressions()

    @staticmethod
    def _stasis_witness(cases: Sequence[Case]) -> dict[str, Any]:
        transitions = 0; stasis = 0
        for c in cases:
            if not isinstance(c.expected, list): continue
            prev = None
            for y in c.expected:
                if prev is not None:
                    transitions += 1
                    if freeze(prev) == freeze(y): stasis += 1
                prev = y
        return {'transitions': transitions, 'stasis_transitions': stasis, 'predicate_gate_warranted': stasis > 0}

    @staticmethod
    def predicates() -> list[Any]:
        atoms = [['ITEM'], ['STATE']]
        consts = [['CONST', 0], ['CONST', 1], ['CONST', -1]]
        out=[]; seen=set()
        for op in ('GT','LT','EQ'):
            for a in atoms:
                for b in consts:
                    for p in ([op,a,b],[op,b,a]):
                        k=cj(p)
                        if k not in seen: seen.add(k); out.append(p)
        return out

    @staticmethod
    def execute(schema: GuardedRegisterSchema, value: Any) -> Any:
        if not isinstance(value, list): raise TypeError('sequence input required')
        state=schema.initial_state; out=[]
        for item in value:
            branch = schema.update_if_true if eval_pred(schema.predicate,item,state) else schema.update_if_false
            state = eval_expr(branch,item,state)
            out.append(state)
        return out

    def search(self, cases: Sequence[Case]):
        witness=self._stasis_witness(cases)
        if not witness['predicate_gate_warranted']:
            return None,0
        best=None; generated=0
        keep=['STATE']
        for initial in (0,1,-1):
            for pred in self.predicates():
                for expr in self.exprs:
                    for a,b in ((expr,keep),(keep,expr)):
                        generated += 1
                        schema=GuardedRegisterSchema(self.FAMILY,pred,a,b,initial)
                        sc=self.score(schema,cases)
                        if best is None or (sc.exact,sc.mdl,-schema.complexity,schema.digest) > (best.exact,best.mdl,-best.schema.complexity,best.schema.digest):
                            best=sc
        return best,generated

    def score(self, schema: GuardedRegisterSchema, cases: Sequence[Case]) -> Score:
        passed=0; failures=[]
        for c in cases:
            try: ok=freeze(self.execute(schema,c.input))==freeze(c.expected)
            except Exception: ok=False
            if ok: passed+=1
            else: failures.append(c.case_id)
        exact=passed/max(1,len(cases))
        return Score(schema,exact,exact-self.complexity_penalty*schema.complexity,failures)


class FrontierPortfolioInducer:
    def __init__(self):
        self.slice=SliceInducer()
        self.scalar=FailureDerivedStatefulRegisterInducer()
        self.factored=FailureDerivedFactoredRegisterInducer()
        self.guarded=FailureDerivedGuardedRegisterInducer()

    def search(self,cases:Sequence[Case]):
        total=0
        for inducer in (self.slice,self.scalar,self.factored,self.guarded):
            best,n=inducer.search(cases); total+=n
            if best is not None and best.exact==1.0:
                return best,total
        return None,total

    def score(self,schema:Any,cases:Sequence[Case]):
        if isinstance(schema,FactoredRegisterSchema): return self.factored.score(schema,cases)
        if isinstance(schema,GuardedRegisterSchema): return self.guarded.score(schema,cases)
        if isinstance(schema,StatefulRegisterSchema): return self.scalar.score(schema,cases)
        return self.slice.score(schema,cases)

    def execute(self,schema:Any,value:Any):
        if isinstance(schema,FactoredRegisterSchema): return self.factored.execute(schema,value)
        if isinstance(schema,GuardedRegisterSchema): return self.guarded.execute(schema,value)
        if isinstance(schema,StatefulRegisterSchema): return self.scalar.execute(schema,value)
        return self.slice.execute(schema,value)


def req(name,train,blind,live,expected):
    return CycleRequest(
        resource_id='github:microsoft/prose:tutorial',
        resource_query='failure-driven program synthesis; infer the minimum state representation warranted by revealed examples',
        actions=[
            {'id':'a7','role':'COMMIT'},{'id':'a4','role':'TEST'},{'id':'a2','role':'DIAGNOSE'},
            {'id':'a6','role':'LEARN'},{'id':'a1','role':'OBSERVE'},{'id':'a5','role':'VERIFY'},{'id':'a3','role':'HYPOTHESIZE'},
        ],
        features={'blind':0.0,'ablation_drop':0.0,'restore':0.0,'integration_gap':0.0},
        task=CycleTask(name=name,train=train,blind=blind,live_input=live,expected_live=expected),
    )


def requests():
    multi=req('multi_register_sum_product',[
        Case('M-T1',[2,3,4],[[2,2],[5,6],[9,24]]),
        Case('M-T2',[1,5,2],[[1,1],[6,5],[8,10]]),
        Case('M-T3',[-1,2,3],[[-1,-1],[1,-2],[4,-6]]),
    ],[
        Case('M-B1',[3,2,5],[[3,3],[5,6],[10,30]]),
        Case('M-B2',[2,-2,4],[[2,2],[0,-4],[4,-16]]),
    ],[4,2,3],[[4,4],[6,8],[9,24]])

    multi2=req('multi_register_product_alternating_recurrence',[
        Case('X-T1',[2,3,4],[[2,2],[6,1],[24,3]]),
        Case('X-T2',[1,5,2],[[1,1],[5,4],[10,-2]]),
        Case('X-T3',[-1,2,3],[[-1,-1],[-2,3],[-6,0]]),
    ],[
        Case('X-B1',[3,2,5],[[3,3],[6,-1],[30,6]]),
        Case('X-B2',[2,-1,4],[[2,2],[-2,-3],[-8,7]]),
    ],[4,1,3],[[4,4],[4,-3],[12,6]])

    cond=req('conditional_running_sum_positive_items',[
        Case('C-T1',[2,-1,3],[2,2,5]),
        Case('C-T2',[-2,4,-3,1],[0,4,4,5]),
        Case('C-T3',[0,5,-1],[0,5,5]),
    ],[
        Case('C-B1',[3,-2,4],[3,3,7]),
        Case('C-B2',[-1,-2,6],[0,0,6]),
    ],[5,-2,1,-1],[5,5,6,6])

    cond2=req('conditional_running_product_skip_zero',[
        Case('Z-T1',[2,0,3],[2,2,6]),
        Case('Z-T2',[0,4,0,2],[1,4,4,8]),
        Case('Z-T3',[-1,0,-2],[-1,-1,2]),
    ],[
        Case('Z-B1',[3,0,2],[3,3,6]),
        Case('Z-B2',[0,-2,0,-3],[1,-2,-2,6]),
    ],[4,0,2],[4,4,8])
    return multi,multi2,cond,cond2


def mechanism(r:Mapping[str,Any])->dict[str,Any]:
    for s in r.get('trace',[]):
        if s.get('stage')=='EXECUTION': return dict(s.get('action') or {})
    return {}


def main()->int:
    multi,multi2,cond,cond2=requests()
    scalar=FailureDerivedStatefulRegisterInducer()
    scalar_baseline={}
    for r in (multi,cond):
        b,n=scalar.search(r.task.train)
        scalar_baseline[r.task.name]={'generated':n,'best_train_exact':None if b is None else b.exact}

    if DB.exists(): DB.unlink()
    old=unified_mod.FailureDrivenSchemaInducer
    unified_mod.FailureDrivenSchemaInducer=FrontierPortfolioInducer
    try:
        k=UnifiedYADOKernelV30RC6R6SchemaAdaptation(str(DB))
        try:
            results=[]
            for r in (multi,multi2,cond,cond2):
                good=k.run_causal_cycle(r)
                abl=k.run_causal_cycle(r,ablate={'MECHANISM'})
                results.append((r,good,abl))
            snap=k.unified_snapshot()
        finally: k.close()
    finally: unified_mod.FailureDrivenSchemaInducer=old

    detail=[]; all_pass=True
    for r,g,a in results:
        m=mechanism(g); fam=(m.get('schema') or {}).get('family')
        passed=(g.get('cycle_success') is True and g.get('blind_score')==1.0 and g.get('ablation_score')==0.0 and g.get('restore_score')==1.0 and a.get('cycle_success') is False)
        all_pass=all_pass and passed
        detail.append({
            'task':r.task.name,'cycle_id':g.get('cycle_id'),'cycle_success':g.get('cycle_success'),
            'old_substrate_train_exact':g.get('old_substrate_train_exact'),'blind':g.get('blind_score'),
            'ablation':g.get('ablation_score'),'restore':g.get('restore_score'),'live_output':g.get('live_output'),
            'expected_live':g.get('expected_live'),'learning_closed':g.get('learning_closed'),'family':fam,
            'mechanism':m,'mechanism_ablation_cycle_success':a.get('cycle_success')
        })

    report={
        'schema':'yado.stateful_frontier_repair.cycle2.v1',
        'status':'SHADOW_SUPPORTED_STATE_REPRESENTATION_EXPANSION' if all_pass else 'WITHHOLD',
        'prior_scalar_baseline':scalar_baseline,
        'failure_diagnosis':{
            'multi_state':'EXPECTED_ELEMENT_STRUCTURE_HAS_ARITY_GT_1_WHILE_SCALAR_FAMILY_EMITS_SCALAR',
            'conditional_state':'REVEALED_OUTPUT_CONTAINS_STATE_STASIS_TRANSITIONS_NOT_EXPLAINED_BY_UNCONDITIONAL_REGISTER_GRAMMAR',
        },
        'derived_representation_warrants':{
            'factored_register_bank':{
                'arity_is_inferred_from_revealed_output_structure':True,
                'specific_register_programs_supplied':False,
                'coordinate_programs_synthesized_from_train':True,
            },
            'predicate_gated_register':{
                'warranted_only_after_stasis_witness':True,
                'predicate_selected_from_train':True,
                'specific_positive_or_zero_rule_supplied':False,
            },
        },
        'cycles':detail,
        'observation_snapshot':snap,
        'claim_boundary':{
            'canonical_durable_head_modified':False,
            'shadow_runtime_binding_modified_only':True,
            'factored_register_interpreter_host_supplied':True,
            'predicate_interpreter_host_supplied':True,
            'candidate_expression_and_comparison_grammar_host_supplied':True,
            'register_arity_and_specific_programs_data_derived':True,
            'blind_used_for_selection':False,
            'general_multi_register_or_conditional_synthesis_proven':False,
            'agi_or_subjective_consciousness_claim':False,
        }
    }
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if all_pass else 2

if __name__=='__main__':
    raise SystemExit(main())
