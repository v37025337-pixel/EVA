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
from yado_stateful_frontier_repair_cycle6 import FrontierPortfolioV3

ROOT = Path(__file__).resolve().parent
DB = ROOT / 'yado_observe_stateful_frontier_cycle8.db'
REPORT = ROOT / 'yado_stateful_frontier_repair_cycle8_report.json'

SPECIAL = {'DEFER', 'INCONSISTENT'}


def cj(x: Any) -> str:
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def sha(x: Any) -> str:
    return hashlib.sha256(cj(x).encode('utf-8')).hexdigest()


def ev(probe: str, obs: Any) -> dict[str, Any]:
    return {'probe': probe, 'obs': obs}


@dataclass(frozen=True)
class BeliefDiagnosticSchema:
    family: str
    hypotheses: tuple[str, ...]
    probes: tuple[str, ...]
    observations: tuple[Any, ...]
    signatures: tuple[tuple[str, str, Any], ...]
    output_policy: str = 'SINGLETON_ELSE_DEFER_EMPTY_INCONSISTENT'
    origin: str = 'FAILURE_DERIVED_BELIEF_SET_DIAGNOSTIC_TRANSDUCER'

    @property
    def digest(self) -> str:
        return sha(asdict(self))

    @property
    def complexity(self) -> int:
        return len(self.signatures) + len(self.hypotheses)

    def signature_map(self) -> dict[tuple[str, str], Any]:
        return {(h, p): o for h, p, o in self.signatures}


class FailureDerivedBeliefSetInducer:
    FAMILY = 'BELIEF_SET_DIAGNOSTIC_TRANSDUCER'

    def __init__(self, complexity_penalty: float = 0.001):
        self.complexity_penalty = complexity_penalty

    @staticmethod
    def _validate(cases: Sequence[Case]) -> bool:
        if not cases:
            return False
        for c in cases:
            if not isinstance(c.input, list) or not isinstance(c.expected, list) or len(c.input) != len(c.expected):
                return False
            for e in c.input:
                if not isinstance(e, dict) or set(e) != {'probe', 'obs'} or not isinstance(e['probe'], str):
                    return False
        return True

    @staticmethod
    def infer_hypotheses(cases: Sequence[Case]) -> tuple[str, ...]:
        labels = sorted({
            str(out) for c in cases for out in c.expected
            if isinstance(out, str) and out not in SPECIAL
        })
        return tuple(labels)

    @staticmethod
    def infer_probes(cases: Sequence[Case]) -> tuple[str, ...]:
        return tuple(sorted({e['probe'] for c in cases for e in c.input}))

    @staticmethod
    def infer_observation_domains(cases: Sequence[Case], probes: Sequence[str]) -> dict[str, tuple[Any, ...]]:
        out = {}
        for p in probes:
            vals = {cj(e['obs']): e['obs'] for c in cases for e in c.input if e['probe'] == p}
            out[p] = tuple(vals[k] for k in sorted(vals))
        return out

    @staticmethod
    def execute_from_belief(schema: BeliefDiagnosticSchema, value: Any, initial_belief: Sequence[str]) -> tuple[list[Any], frozenset[str]]:
        if not isinstance(value, list):
            raise TypeError('diagnostic event sequence required')
        sig = schema.signature_map()
        belief = set(initial_belief)
        outputs = []
        for e in value:
            if not isinstance(e, dict) or 'probe' not in e or 'obs' not in e:
                raise TypeError('event must contain probe and obs')
            p, obs = e['probe'], e['obs']
            if any((h, p) not in sig for h in belief):
                raise KeyError(f'unseen probe {p}')
            belief = {h for h in belief if freeze(sig[(h, p)]) == freeze(obs)}
            if not belief:
                outputs.append('INCONSISTENT')
            elif len(belief) == 1:
                outputs.append(next(iter(belief)))
            else:
                outputs.append('DEFER')
        return outputs, frozenset(belief)

    @classmethod
    def execute(cls, schema: BeliefDiagnosticSchema, value: Any) -> Any:
        out, _ = cls.execute_from_belief(schema, value, schema.hypotheses)
        return out

    @classmethod
    def _fits(cls, schema: BeliefDiagnosticSchema, cases: Sequence[Case]) -> bool:
        for c in cases:
            try:
                if freeze(cls.execute(schema, c.input)) != freeze(c.expected):
                    return False
            except Exception:
                return False
        return True

    def search(self, cases: Sequence[Case]):
        if not self._validate(cases):
            return None, 0
        hypotheses = self.infer_hypotheses(cases)
        probes = self.infer_probes(cases)
        if len(hypotheses) < 2 or not probes:
            return None, 0
        domains = self.infer_observation_domains(cases, probes)
        if any(not domains[p] for p in probes):
            return None, 0
        keys = [(h, p) for h in hypotheses for p in probes]
        choice_domains = [domains[p] for _, p in keys]
        generated = 0
        best = None
        for choices in itertools.product(*choice_domains):
            generated += 1
            rows = tuple((h, p, o) for (h, p), o in zip(keys, choices))
            obs_union = {cj(o): o for vals in domains.values() for o in vals}
            schema = BeliefDiagnosticSchema(
                self.FAMILY, hypotheses, probes,
                tuple(obs_union[k] for k in sorted(obs_union)), rows,
            )
            if not self._fits(schema, cases):
                continue
            sc = self.score(schema, cases)
            key = (sc.exact, sc.mdl, -schema.complexity, schema.digest)
            if best is None or key > (best.exact, best.mdl, -best.schema.complexity, best.schema.digest):
                best = sc
        return best, generated

    def score(self, schema: BeliefDiagnosticSchema, cases: Sequence[Case]) -> Score:
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


class FrontierPortfolioV4:
    def __init__(self):
        self.old = FrontierPortfolioV3()
        self.belief = FailureDerivedBeliefSetInducer()

    @staticmethod
    def is_belief_warrant(cases: Sequence[Case]) -> bool:
        return bool(cases) and all(
            isinstance(c.input, list) and all(isinstance(e, dict) and set(e) == {'probe', 'obs'} for e in c.input)
            for c in cases
        ) and any('DEFER' in c.expected for c in cases)

    def search(self, cases: Sequence[Case]):
        # Failure-derived routing warrant: the previous latent Mealy search is
        # bounded to <=4 latent states and explodes on this structured event
        # alphabet. Diagnostic evidence explicitly requires maintaining more
        # than four distinguishable posterior belief states (certified below).
        if self.is_belief_warrant(cases):
            b, n = self.belief.search(cases)
            if b is not None:
                return b, n
        return self.old.search(cases)

    def score(self, schema: Any, cases: Sequence[Case]):
        if isinstance(schema, BeliefDiagnosticSchema):
            return self.belief.score(schema, cases)
        return self.old.score(schema, cases)

    def execute(self, schema: Any, value: Any):
        if isinstance(schema, BeliefDiagnosticSchema):
            return self.belief.execute(schema, value)
        return self.old.execute(schema, value)


def request(name: str, train, blind, live, expected):
    return CycleRequest(
        resource_id='github:microsoft/prose:tutorial',
        resource_query='failure-driven belief-state reasoning: preserve multiple compatible latent hypotheses, defer while posterior is non-singleton, and detect inconsistent evidence',
        actions=[
            {'id':'b7','role':'COMMIT'}, {'id':'b4','role':'TEST'}, {'id':'b2','role':'DIAGNOSE'},
            {'id':'b6','role':'LEARN'}, {'id':'b1','role':'OBSERVE'}, {'id':'b5','role':'VERIFY'}, {'id':'b3','role':'HYPOTHESIZE'},
        ],
        features={'blind':0.0,'ablation_drop':0.0,'restore':0.0,'integration_gap':0.0},
        task=CycleTask(name=name, train=train, blind=blind, live_input=live, expected_live=expected),
    )


def requests():
    three = request(
        'belief_three_hypothesis_diagnostic',
        [
            Case('B3-T1',[ev('p',0)],['DEFER']),
            Case('B3-T2',[ev('q',0)],['DEFER']),
            Case('B3-T3',[ev('r',0)],['DEFER']),
            Case('B3-T4',[ev('p',0),ev('q',0)],['DEFER','A']),
            Case('B3-T5',[ev('p',0),ev('r',0)],['DEFER','B']),
            Case('B3-T6',[ev('q',0),ev('r',0)],['DEFER','C']),
            Case('B3-T7',[ev('p',1)],['C']),
            Case('B3-T8',[ev('q',1)],['B']),
            Case('B3-T9',[ev('r',1)],['A']),
            Case('B3-T10',[ev('p',1),ev('q',0)],['C','C']),
            Case('B3-T11',[ev('q',1),ev('r',0)],['B','B']),
            Case('B3-T12',[ev('r',1),ev('p',0)],['A','A']),
            Case('B3-T13',[ev('p',1),ev('q',1)],['C','INCONSISTENT']),
        ],
        [
            Case('B3-B1',[ev('p',0),ev('q',1)],['DEFER','B']),
            Case('B3-B2',[ev('q',0),ev('p',1)],['DEFER','C']),
            Case('B3-B3',[ev('r',0),ev('p',0)],['DEFER','B']),
            Case('B3-B4',[ev('p',0),ev('q',0),ev('r',1)],['DEFER','A','A']),
            Case('B3-B5',[ev('q',0),ev('r',0),ev('p',0)],['DEFER','C','INCONSISTENT']),
        ],
        [ev('r',0),ev('q',1),ev('p',0)],
        ['DEFER','B','B'],
    )

    four = request(
        'belief_four_hypothesis_parity_diagnostic',
        [
            Case('B4-T1',[ev('p',0)],['DEFER']), Case('B4-T2',[ev('p',1)],['DEFER']),
            Case('B4-T3',[ev('q',0)],['DEFER']), Case('B4-T4',[ev('q',1)],['DEFER']),
            Case('B4-T5',[ev('r',0)],['DEFER']), Case('B4-T6',[ev('r',1)],['DEFER']),
            Case('B4-T7',[ev('p',0),ev('q',0)],['DEFER','W']),
            Case('B4-T8',[ev('p',0),ev('q',1)],['DEFER','X']),
            Case('B4-T9',[ev('p',1),ev('q',0)],['DEFER','Y']),
            Case('B4-T10',[ev('p',1),ev('q',1)],['DEFER','Z']),
            Case('B4-T11',[ev('q',0),ev('r',0)],['DEFER','W']),
            Case('B4-T12',[ev('q',1),ev('r',1)],['DEFER','X']),
            Case('B4-T13',[ev('q',0),ev('r',1)],['DEFER','Y']),
            Case('B4-T14',[ev('q',1),ev('r',0)],['DEFER','Z']),
            Case('B4-T15',[ev('p',0),ev('q',0),ev('r',1)],['DEFER','W','INCONSISTENT']),
        ],
        [
            Case('B4-B1',[ev('r',0),ev('p',0)],['DEFER','W']),
            Case('B4-B2',[ev('r',1),ev('p',0)],['DEFER','X']),
            Case('B4-B3',[ev('r',1),ev('p',1)],['DEFER','Y']),
            Case('B4-B4',[ev('r',0),ev('p',1)],['DEFER','Z']),
            Case('B4-B5',[ev('p',1),ev('q',1),ev('r',0)],['DEFER','Z','Z']),
        ],
        [ev('q',0),ev('r',1),ev('p',1)],
        ['DEFER','Y','Y'],
    )
    return three, four


def mechanism(r: Mapping[str, Any]) -> dict[str, Any]:
    for s in r.get('trace', []):
        if s.get('stage') == 'EXECUTION':
            return dict(s.get('action') or {})
    return {}


def residual_certificate(schema: BeliefDiagnosticSchema, train: Sequence[Case]) -> dict[str, Any]:
    inducer = FailureDerivedBeliefSetInducer()
    beliefs = {frozenset(schema.hypotheses)}
    for c in train:
        belief = frozenset(schema.hypotheses)
        beliefs.add(belief)
        for e in c.input:
            _, belief = inducer.execute_from_belief(schema, [e], belief)
            beliefs.add(belief)

    alphabet = []
    seen = set()
    for c in train:
        for e in c.input:
            k = cj(e)
            if k not in seen:
                seen.add(k); alphabet.append(e)
    suffixes = [[a] for a in alphabet]
    suffixes += [[a,b] for a in alphabet for b in alphabet]

    residual = {}
    for belief in sorted(beliefs, key=lambda x: (len(x), sorted(x))):
        sig = []
        for suf in suffixes:
            try:
                out, _ = inducer.execute_from_belief(schema, suf, belief)
                sig.append(tuple(out))
            except Exception as e:
                sig.append(('ERR', type(e).__name__))
        residual[tuple(sorted(belief))] = tuple(sig)
    distinguishable = len(set(residual.values()))
    return {
        'train_reachable_belief_states': len(beliefs),
        'train_residual_distinguishable_states': distinguishable,
        'current_latent_mealy_max_states': 4,
        'structurally_exceeds_current_latent_bound': distinguishable > 4,
        'belief_states': [list(x) for x in sorted(beliefs, key=lambda x: (len(x), sorted(x)))],
    }


def main() -> int:
    tasks = requests()
    if DB.exists():
        DB.unlink()
    old_binding = unified_mod.FailureDrivenSchemaInducer
    unified_mod.FailureDrivenSchemaInducer = FrontierPortfolioV4
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
        m = mechanism(g); s = m.get('schema') or {}
        schema_obj = None
        if s.get('family') == FailureDerivedBeliefSetInducer.FAMILY:
            schema_obj = BeliefDiagnosticSchema(
                s['family'], tuple(s['hypotheses']), tuple(s['probes']), tuple(s['observations']),
                tuple(tuple(x) for x in s['signatures']), s.get('output_policy','SINGLETON_ELSE_DEFER_EMPTY_INCONSISTENT'),
                s.get('origin','FAILURE_DERIVED_BELIEF_SET_DIAGNOSTIC_TRANSDUCER')
            )
        cert = residual_certificate(schema_obj, r.task.train) if schema_obj else None
        passed = (
            g.get('cycle_success') is True and s.get('family') == FailureDerivedBeliefSetInducer.FAMILY and
            g.get('blind_score') == 1.0 and g.get('ablation_score') == 0.0 and g.get('restore_score') == 1.0 and
            a.get('cycle_success') is False and cert is not None and cert['structurally_exceeds_current_latent_bound']
        )
        all_pass = all_pass and passed
        detail.append({
            'task': r.task.name,
            'cycle_id': g.get('cycle_id'),
            'cycle_success': g.get('cycle_success'),
            'family': s.get('family'),
            'hypotheses': s.get('hypotheses'),
            'signatures': s.get('signatures'),
            'blind': g.get('blind_score'),
            'ablation': g.get('ablation_score'),
            'restore': g.get('restore_score'),
            'live_output': g.get('live_output'),
            'expected_live': g.get('expected_live'),
            'learning_closed': g.get('learning_closed'),
            'mechanism_ablation_cycle_success': a.get('cycle_success'),
            'baseline_certificate': cert,
        })

    report = {
        'schema': 'yado.stateful_frontier_repair.cycle8.v1',
        'status': 'SHADOW_SUPPORTED_BELIEF_SET_REASONING' if all_pass else 'WITHHOLD',
        'failure_diagnosis': {
            'single_latent_state_hypothesis': 'INSUFFICIENT_WHEN_EVIDENCE_LEAVES_MULTIPLE_COMPATIBLE_INTERNAL_HYPOTHESES',
            'required_capability': 'MAINTAIN_AND_UPDATE_SET_VALUED_BELIEF_UNTIL_IDENTIFICATION_OR_INCONSISTENCY',
        },
        'derived_representation_warrant': {
            'family': FailureDerivedBeliefSetInducer.FAMILY,
            'specific_hypothesis_signatures_supplied': False,
            'hypothesis_labels_inferred_from_revealed_terminal_outputs': True,
            'posterior_update_rule_generic': 'FILTER_HYPOTHESES_BY_OBSERVATION_COMPATIBILITY',
            'defer_policy': 'NON_SINGLETON_POSTERIOR',
            'inconsistency_policy': 'EMPTY_POSTERIOR',
            'fresh_used_for_selection': False,
        },
        'cycles': detail,
        'observation_snapshot': snap,
        'claim_boundary': {
            'canonical_durable_head_modified': False,
            'shadow_runtime_binding_modified_only': True,
            'generic_belief_set_interpreter_host_supplied': True,
            'bounded_signature_enumeration_host_supplied': True,
            'specific_hypothesis_signatures_data_derived': True,
            'probabilistic_bayes_or_general_pomdp_inference_proven': False,
            'belief_is_set_valued_not_probabilistic': True,
            'agi_or_subjective_consciousness_claim': False,
        },
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if all_pass else 2


if __name__ == '__main__':
    raise SystemExit(main())
