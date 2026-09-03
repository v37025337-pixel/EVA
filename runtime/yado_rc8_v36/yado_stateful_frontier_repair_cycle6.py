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
from yado_stateful_frontier_repair_cycle2 import Score
from yado_stateful_frontier_repair_cycle4 import FrontierPortfolioV2

ROOT = Path(__file__).resolve().parent
DB = ROOT / 'yado_observe_stateful_frontier_cycle6.db'
REPORT = ROOT / 'yado_stateful_frontier_repair_cycle6_report.json'


def cj(x: Any) -> str:
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def sha(x: Any) -> str:
    return hashlib.sha256(cj(x).encode('utf-8')).hexdigest()


@dataclass(frozen=True)
class LatentMealySchema:
    family: str
    state_count: int
    initial_state: int
    transitions: tuple[tuple[int, Any, int, Any], ...]
    output_mode: str = 'TRANSITION_EMISSION_ONLY'
    origin: str = 'FAILURE_DERIVED_LATENT_MEALY_TRANSDUCER'

    @property
    def digest(self) -> str:
        return sha(asdict(self))

    @property
    def complexity(self) -> int:
        # Prefer fewer latent states first, then fewer non-self transitions.
        return self.state_count * 10 + sum(1 for s, _, ns, _ in self.transitions if s != ns)

    def transition_map(self) -> dict[tuple[int, str], tuple[int, Any]]:
        return {(s, cj(item)): (ns, out) for s, item, ns, out in self.transitions}


class FailureDerivedLatentMealyInducer:
    FAMILY = 'LATENT_DETERMINISTIC_MEALY_TRANSDUCER'

    def __init__(self, max_states: int = 4, complexity_penalty: float = 0.001):
        self.max_states = max_states
        self.complexity_penalty = complexity_penalty

    @staticmethod
    def _validate_cases(cases: Sequence[Case]) -> bool:
        return bool(cases) and all(
            isinstance(c.input, list) and isinstance(c.expected, list) and len(c.input) == len(c.expected)
            for c in cases
        )

    @staticmethod
    def _alphabet(cases: Sequence[Case]) -> list[Any]:
        vals, seen = [], set()
        for c in cases:
            for item in c.input:
                k = cj(item)
                if k not in seen:
                    seen.add(k); vals.append(item)
        vals.sort(key=cj)
        return vals

    @staticmethod
    def _output_domains(cases: Sequence[Case], alphabet: Sequence[Any]) -> dict[str, list[Any]]:
        dom = {cj(a): [] for a in alphabet}
        seen = {cj(a): set() for a in alphabet}
        for c in cases:
            for item, out in zip(c.input, c.expected):
                ik, ok = cj(item), cj(out)
                if ok not in seen[ik]:
                    seen[ik].add(ok); dom[ik].append(out)
        for k in dom:
            dom[k].sort(key=cj)
        return dom

    @staticmethod
    def execute(schema: LatentMealySchema, value: Any) -> Any:
        if not isinstance(value, list):
            raise TypeError('sequence input required')
        table = schema.transition_map()
        state = schema.initial_state
        out = []
        for item in value:
            key = (state, cj(item))
            if key not in table:
                raise KeyError(f'unseen transition {key}')
            state, emitted = table[key]
            out.append(emitted)
        return out

    @staticmethod
    def _fits(schema: LatentMealySchema, cases: Sequence[Case]) -> bool:
        for c in cases:
            try:
                if freeze(FailureDerivedLatentMealyInducer.execute(schema, c.input)) != freeze(c.expected):
                    return False
            except Exception:
                return False
        return True

    def search(self, cases: Sequence[Case]):
        if not self._validate_cases(cases):
            return None, 0
        alphabet = self._alphabet(cases)
        output_domains = self._output_domains(cases, alphabet)
        generated = 0

        # One latent state is deliberately tested first. If it works, there is
        # no warrant for hidden state and the older portfolio should own it.
        for k in range(1, self.max_states + 1):
            variables = [(s, a) for s in range(k) for a in alphabet]
            choice_domains = []
            for _, a in variables:
                outs = output_domains[cj(a)]
                choice_domains.append([(ns, out) for ns in range(k) for out in outs])

            best = None
            for initial in range(k):
                for choices in itertools.product(*choice_domains):
                    generated += 1
                    rows = []
                    for (s, a), (ns, out) in zip(variables, choices):
                        rows.append((s, a, ns, out))
                    schema = LatentMealySchema(self.FAMILY, k, initial, tuple(rows))
                    if not self._fits(schema, cases):
                        continue
                    sc = self.score(schema, cases)
                    key = (sc.exact, sc.mdl, -schema.complexity, schema.digest)
                    if best is None or key > (best.exact, best.mdl, -best.schema.complexity, best.schema.digest):
                        best = sc
                if best is not None:
                    # Minimal latent-state count is the primary MDL constraint.
                    return best, generated
        return None, generated

    def score(self, schema: LatentMealySchema, cases: Sequence[Case]) -> Score:
        passed, failures = 0, []
        for c in cases:
            try:
                ok = freeze(self.execute(schema, c.input)) == freeze(c.expected)
            except Exception:
                ok = False
            if ok:
                passed += 1
            else:
                failures.append(c.case_id)
        exact = passed / max(1, len(cases))
        return Score(schema, exact, exact - self.complexity_penalty * schema.complexity, failures)


class FrontierPortfolioV3:
    def __init__(self):
        self.old = FrontierPortfolioV2()
        self.latent = FailureDerivedLatentMealyInducer(max_states=4)

    def search(self, cases: Sequence[Case]):
        old, n0 = self.old.search(cases)
        if old is not None and old.exact == 1.0:
            return old, n0
        latent, n1 = self.latent.search(cases)
        if latent is not None and latent.exact == 1.0:
            return latent, n0 + n1
        candidates = [x for x in (old, latent) if x is not None]
        if not candidates:
            return None, n0 + n1
        candidates.sort(key=lambda sc: (sc.exact, sc.mdl, -sc.schema.complexity, getattr(sc.schema, 'digest', '')), reverse=True)
        return candidates[0], n0 + n1

    def score(self, schema: Any, cases: Sequence[Case]):
        if isinstance(schema, LatentMealySchema):
            return self.latent.score(schema, cases)
        return self.old.score(schema, cases)

    def execute(self, schema: Any, value: Any):
        if isinstance(schema, LatentMealySchema):
            return self.latent.execute(schema, value)
        return self.old.execute(schema, value)


def req(name: str, train, blind, live, expected):
    return CycleRequest(
        resource_id='github:microsoft/prose:tutorial',
        resource_query='failure-driven latent-state inference: current visible output is insufficient state; infer minimal deterministic hidden-state transducer from revealed input-output history only',
        actions=[
            {'id':'h7','role':'COMMIT'},{'id':'h4','role':'TEST'},{'id':'h2','role':'DIAGNOSE'},
            {'id':'h6','role':'LEARN'},{'id':'h1','role':'OBSERVE'},{'id':'h5','role':'VERIFY'},{'id':'h3','role':'HYPOTHESIZE'},
        ],
        features={'blind':0.0,'ablation_drop':0.0,'restore':0.0,'integration_gap':0.0},
        task=CycleTask(name=name, train=train, blind=blind, live_input=live, expected_live=expected),
    )


def requests():
    # Hidden two-mode machine. 't' changes hidden mode but always emits 0;
    # 'q' reveals mode without changing it. Therefore visible output is not a
    # sufficient Markov state and the prior output-as-state FSM conflicts.
    hidden2 = req('partially_observed_toggle_probe_machine', [
        Case('H2-T1',['t','q','t','q'],[0,1,0,0]),
        Case('H2-T2',['q','t','t','q','t','q'],[0,0,0,0,0,1]),
        Case('H2-T3',['t','t','t','q','q'],[0,0,0,1,1]),
        Case('H2-T4',['q','q','t','q','t'],[0,0,0,1,0]),
    ], [
        Case('H2-B1',['t','q','q','t','q'],[0,1,1,0,0]),
        Case('H2-B2',['q','t','q','t','t','q'],[0,0,1,0,0,1]),
    ], ['t','t','q','t','q','q'], [0,0,0,0,1,1])

    # Hidden three-mode cycle. 'x' advances hidden state and emits the same
    # symbol every time; 'p' emits an aliased observation (A and C both 0).
    hidden3 = req('partially_observed_three_mode_alias_machine', [
        Case('H3-T1',['x','p','x','p','x','p'],['u',1,'u',0,'u',0]),
        Case('H3-T2',['p','x','x','p','x','p'],[0,'u','u',0,'u',0]),
        Case('H3-T3',['x','x','x','p','x','p'],['u','u','u',0,'u',1]),
        Case('H3-T4',['p','x','p','x','p'],[0,'u',1,'u',0]),
    ], [
        Case('H3-B1',['x','p','p','x','x','p'],['u',1,1,'u','u',0]),
        Case('H3-B2',['x','x','p','x','p','p'],['u','u',0,'u',0,0]),
    ], ['x','x','x','x','p','x','p'], ['u','u','u','u',1,'u',0])
    return hidden2, hidden3


def mechanism(r: Mapping[str, Any]) -> dict[str, Any]:
    for s in r.get('trace', []):
        if s.get('stage') == 'EXECUTION':
            return dict(s.get('action') or {})
    return {}


def main() -> int:
    tasks = requests()
    old = FrontierPortfolioV2()
    baselines = {}
    for r in tasks:
        b, n = old.search(r.task.train)
        baselines[r.task.name] = {
            'generated': n,
            'best_train_exact': None if b is None else b.exact,
            'best_family': None if b is None else getattr(b.schema, 'family', None),
        }

    if DB.exists():
        DB.unlink()
    old_binding = unified_mod.FailureDrivenSchemaInducer
    unified_mod.FailureDrivenSchemaInducer = FrontierPortfolioV3
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

    detail = []
    all_pass = True
    for r, g, a in rows:
        m = mechanism(g); schema = m.get('schema') or {}
        passed = (
            g.get('cycle_success') is True and g.get('blind_score') == 1.0 and
            g.get('ablation_score') == 0.0 and g.get('restore_score') == 1.0 and
            a.get('cycle_success') is False and schema.get('family') == FailureDerivedLatentMealyInducer.FAMILY
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
        'schema': 'yado.stateful_frontier_repair.cycle6.v1',
        'status': 'SHADOW_SUPPORTED_LATENT_STATE_INFERENCE' if all_pass else 'WITHHOLD',
        'old_portfolio_baseline': baselines,
        'failure_diagnosis': {
            'visible_output_as_state': 'OUTPUT_ALIASING_MAKES_VISIBLE_OUTPUT_NON_MARKOV',
            'required_capability': 'INFER_MINIMAL_LATENT_STATE_FROM_INPUT_OUTPUT_HISTORY',
        },
        'derived_representation_warrant': {
            'family': FailureDerivedLatentMealyInducer.FAMILY,
            'state_count_selected_by_minimal_exact_search': True,
            'specific_transition_table_supplied': False,
            'specific_emission_table_supplied': False,
            'train_only_selection': True,
        },
        'cycles': detail,
        'observation_snapshot': snap,
        'claim_boundary': {
            'canonical_durable_head_modified': False,
            'shadow_runtime_binding_modified_only': True,
            'generic_latent_mealy_interpreter_host_supplied': True,
            'bounded_state_count_search_host_supplied': True,
            'specific_hidden_states_transition_and_emission_tables_data_derived': True,
            'blind_used_for_selection': False,
            'general_pomdp_or_world_model_inference_proven': False,
            'agi_or_subjective_consciousness_claim': False,
        },
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if all_pass else 2


if __name__ == '__main__':
    raise SystemExit(main())
