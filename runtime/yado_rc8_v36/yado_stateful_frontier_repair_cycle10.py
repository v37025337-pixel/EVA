from __future__ import annotations

import hashlib
import itertools
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import yado_core_v2_5_unified as unified_mod
from yado_core_v2_5_unified import CycleRequest, CycleTask
from yado_core_v3_0_rc6_r6_schema_adaptation import UnifiedYADOKernelV30RC6R6SchemaAdaptation
from yado_phase_a_shadow import Case
from yado_primitive_genesis_cycle1 import freeze
from yado_stateful_frontier_repair_cycle2 import Score
from yado_stateful_frontier_repair_cycle8 import FrontierPortfolioV4, FailureDerivedBeliefSetInducer, SPECIAL, cj, ev

ROOT = Path(__file__).resolve().parent
DB = ROOT / 'yado_observe_stateful_frontier_cycle10.db'
REPORT = ROOT / 'yado_stateful_frontier_repair_cycle10_report.json'


def sha(x: Any) -> str:
    return hashlib.sha256(cj(x).encode('utf-8')).hexdigest()


@dataclass(frozen=True)
class ProbabilisticBeliefSchema:
    family: str
    hypotheses: tuple[str, ...]
    probes: tuple[str, ...]
    observations: tuple[Any, ...]
    priors: tuple[tuple[str, float], ...]
    likelihoods: tuple[tuple[str, str, Any, float], ...]
    confidence_threshold: float
    output_policy: str = 'MAP_IF_POSTERIOR_AT_OR_ABOVE_THRESHOLD_ELSE_DEFER'
    origin: str = 'FAILURE_DERIVED_BOUNDED_PROBABILISTIC_BELIEF'

    @property
    def digest(self) -> str:
        return sha(asdict(self))

    @property
    def complexity(self) -> int:
        return len(self.priors) + len(self.likelihoods) + 1

    def prior_map(self) -> dict[str, float]:
        return dict(self.priors)

    def likelihood_map(self) -> dict[tuple[str, str, str], float]:
        return {(h, p, cj(o)): float(v) for h, p, o, v in self.likelihoods}


class FailureDerivedProbabilisticBeliefInducer:
    FAMILY = 'BOUNDED_PROBABILISTIC_BELIEF_TRANSDUCER'
    PRIOR_GRID = (0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8)
    PROB_GRID = (0.1, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.7, 0.75, 0.8, 0.9)
    THRESHOLD_GRID = (0.7, 0.75, 0.8, 0.85, 0.9, 0.95)

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
        return tuple(sorted({str(x) for c in cases for x in c.expected if isinstance(x, str) and x not in SPECIAL}))

    @staticmethod
    def infer_probes(cases: Sequence[Case]) -> tuple[str, ...]:
        return tuple(sorted({e['probe'] for c in cases for e in c.input}))

    @staticmethod
    def infer_obs(cases: Sequence[Case], probe: str) -> tuple[Any, ...]:
        d = {cj(e['obs']): e['obs'] for c in cases for e in c.input if e['probe'] == probe}
        return tuple(d[k] for k in sorted(d))

    @classmethod
    def execute_with_trace(cls, schema: ProbabilisticBeliefSchema, value: Any):
        if not isinstance(value, list):
            raise TypeError('diagnostic event sequence required')
        pri = schema.prior_map()
        like = schema.likelihood_map()
        weights = {h: float(pri[h]) for h in schema.hypotheses}
        s0 = sum(weights.values())
        if s0 <= 0:
            raise ValueError('invalid prior mass')
        weights = {h: v / s0 for h, v in weights.items()}
        outs, trace = [], []
        for e in value:
            p, obs = e['probe'], e['obs']
            for h in schema.hypotheses:
                k = (h, p, cj(obs))
                if k not in like:
                    raise KeyError(f'unseen likelihood {k}')
                weights[h] *= like[k]
            z = sum(weights.values())
            if z <= 0:
                outs.append('INCONSISTENT')
                trace.append({'event': dict(e), 'posterior': {}, 'decision': 'INCONSISTENT', 'confidence': 0.0})
                continue
            weights = {h: v / z for h, v in weights.items()}
            ranked = sorted(weights.items(), key=lambda kv: (-kv[1], kv[0]))
            h, conf = ranked[0]
            decision = h if conf + 1e-12 >= schema.confidence_threshold else 'DEFER'
            outs.append(decision)
            trace.append({
                'event': dict(e),
                'posterior': {k: round(v, 12) for k, v in sorted(weights.items())},
                'decision': decision,
                'confidence': round(conf, 12),
            })
        return outs, trace

    @classmethod
    def execute(cls, schema: ProbabilisticBeliefSchema, value: Any):
        return cls.execute_with_trace(schema, value)[0]

    @classmethod
    def _fits(cls, schema: ProbabilisticBeliefSchema, cases: Sequence[Case]) -> bool:
        for c in cases:
            try:
                if freeze(cls.execute(schema, c.input)) != freeze(c.expected):
                    return False
            except Exception:
                return False
        return True

    @classmethod
    def calibration_margin(cls, schema: ProbabilisticBeliefSchema, cases: Sequence[Case]) -> float:
        margin = float('inf')
        for c in cases:
            _, tr = cls.execute_with_trace(schema, c.input)
            for expected, row in zip(c.expected, tr):
                conf = float(row['confidence'])
                if expected == 'DEFER':
                    margin = min(margin, schema.confidence_threshold - conf)
                elif expected == 'INCONSISTENT':
                    continue
                else:
                    margin = min(margin, conf - schema.confidence_threshold)
        return 0.0 if margin == float('inf') else margin

    def search(self, cases: Sequence[Case]):
        if not self._validate(cases):
            return None, 0
        hypotheses = self.infer_hypotheses(cases)
        probes = self.infer_probes(cases)
        # Current bounded genesis step deliberately supports 2 hypotheses and
        # one binary observation channel. This is a declared scope limit, not a
        # claim of general Bayesian/POMDP inference.
        if len(hypotheses) != 2 or len(probes) != 1:
            return None, 0
        probe = probes[0]
        obs = self.infer_obs(cases, probe)
        if len(obs) != 2:
            return None, 0
        h0, h1 = hypotheses
        o0, o1 = obs
        generated = 0
        best = None
        best_key = None
        for prior0, p0_o1, p1_o1, threshold in itertools.product(
            self.PRIOR_GRID, self.PROB_GRID, self.PROB_GRID, self.THRESHOLD_GRID
        ):
            generated += 1
            priors = ((h0, prior0), (h1, round(1.0-prior0, 12)))
            likes = (
                (h0, probe, o0, round(1.0-p0_o1, 12)), (h0, probe, o1, p0_o1),
                (h1, probe, o0, round(1.0-p1_o1, 12)), (h1, probe, o1, p1_o1),
            )
            schema = ProbabilisticBeliefSchema(self.FAMILY, hypotheses, probes, obs, priors, likes, threshold)
            if not self._fits(schema, cases):
                continue
            sc = self.score(schema, cases)
            margin = self.calibration_margin(schema, cases)
            separation = abs(p0_o1 - p1_o1)
            # Selection uses revealed train only: exact fit first, then robust
            # distance from the decision threshold, then more informative
            # likelihood separation, then deterministic digest.
            key = (sc.exact, round(margin, 12), round(separation, 12), -schema.complexity, schema.digest)
            if best is None or key > best_key:
                best, best_key = sc, key
        return best, generated

    def score(self, schema: ProbabilisticBeliefSchema, cases: Sequence[Case]) -> Score:
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


class FrontierPortfolioV5:
    def __init__(self):
        self.old = FrontierPortfolioV4()
        self.prob = FailureDerivedProbabilisticBeliefInducer()

    def search(self, cases: Sequence[Case]):
        # Give the already-proven set-valued belief mechanism a bounded direct
        # check. Do not fall through into the older latent-Mealy search here:
        # this benchmark intentionally contains repeated stochastic evidence and
        # the latent search is both structurally inappropriate and expensive.
        sb = FailureDerivedBeliefSetInducer()
        old_best, old_n = sb.search(cases)
        if old_best is not None and old_best.exact == 1.0:
            return old_best, old_n
        b, n = self.prob.search(cases)
        if b is not None:
            return b, old_n + n
        return old_best, old_n + n

    def score(self, schema: Any, cases: Sequence[Case]):
        if isinstance(schema, ProbabilisticBeliefSchema):
            return self.prob.score(schema, cases)
        return self.old.score(schema, cases)

    def execute(self, schema: Any, value: Any):
        if isinstance(schema, ProbabilisticBeliefSchema):
            return self.prob.execute(schema, value)
        return self.old.execute(schema, value)


def expected_from_hidden(seq, labels, prior0, p0_1, p1_1, threshold):
    weights = [prior0, 1.0-prior0]
    out = []
    for bit in seq:
        likes = [p0_1 if bit == 1 else 1-p0_1, p1_1 if bit == 1 else 1-p1_1]
        weights = [weights[i]*likes[i] for i in range(2)]
        z = sum(weights); weights = [x/z for x in weights]
        j = 0 if weights[0] >= weights[1] else 1
        out.append(labels[j] if weights[j] + 1e-12 >= threshold else 'DEFER')
    return out


def seq_case(prefix, idx, seq, labels, prior0, p0, p1, threshold):
    return Case(f'{prefix}-{idx}', [ev('signal', x) for x in seq], expected_from_hidden(seq, labels, prior0, p0, p1, threshold))


def all_binary(max_len):
    rows=[]
    for n in range(1,max_len+1):
        rows.extend(list(x) for x in itertools.product((0,1), repeat=n))
    return rows


def request(name, train, blind, live, expected):
    return CycleRequest(
        resource_id='github:microsoft/prose:tutorial',
        resource_query='failure-driven probabilistic belief reasoning: maintain weighted hypotheses under overlapping evidence and defer until posterior confidence is calibrated',
        actions=[
            {'id':'p7','role':'COMMIT'}, {'id':'p4','role':'TEST'}, {'id':'p2','role':'DIAGNOSE'},
            {'id':'p6','role':'LEARN'}, {'id':'p1','role':'OBSERVE'}, {'id':'p5','role':'VERIFY'}, {'id':'p3','role':'HYPOTHESIZE'},
        ],
        features={'blind':0.0,'ablation_drop':0.0,'restore':0.0,'integration_gap':0.0},
        task=CycleTask(name=name, train=train, blind=blind, live_input=live, expected_live=expected),
    )


def requests():
    # Hidden benchmark parameters generate the ground truth only. They are not
    # supplied to the inducer; the inducer sees event sequences + decisions.
    labels1=('A','B'); truth1=(0.5,0.8,0.2,0.85)
    train1=[seq_case('PB1-T',i,s,labels1,*truth1) for i,s in enumerate(all_binary(4),1)]
    fresh1_seqs=[[1,0,1,1,1],[0,1,0,0,0],[1,1,0,1,0],[0,0,1,0,1],[1,0,0,1,1],[0,1,1,0,0],[1,1,1,0,1],[0,0,0,1,0]]
    blind1=[seq_case('PB1-B',i,s,labels1,*truth1) for i,s in enumerate(fresh1_seqs,1)]
    live1=[1,1,0,1,1]
    r1=request('probabilistic_belief_symmetric_overlap',train1,blind1,[ev('signal',x) for x in live1],expected_from_hidden(live1,labels1,*truth1))

    labels2=('X','Y'); truth2=(0.6,0.75,0.25,0.9)
    train2=[seq_case('PB2-T',i,s,labels2,*truth2) for i,s in enumerate(all_binary(5),1)]
    fresh2_seqs=[[1,0,1,1,1,0],[0,1,0,0,0,1],[1,1,0,1,0,1],[0,0,1,0,1,0],[1,0,0,1,1,1],[0,1,1,0,0,0],[1,1,1,0,1,0],[0,0,0,1,0,1]]
    blind2=[seq_case('PB2-B',i,s,labels2,*truth2) for i,s in enumerate(fresh2_seqs,1)]
    live2=[0,0,1,0,0,0]
    r2=request('probabilistic_belief_unequal_prior_overlap',train2,blind2,[ev('signal',x) for x in live2],expected_from_hidden(live2,labels2,*truth2))
    return [(r1, {'prior0':truth1[0],'p_h0_obs1':truth1[1],'p_h1_obs1':truth1[2],'threshold':truth1[3]}),
            (r2, {'prior0':truth2[0],'p_h0_obs1':truth2[1],'p_h1_obs1':truth2[2],'threshold':truth2[3]})]


def mechanism(r: Mapping[str,Any]):
    for s in r.get('trace',[]):
        if s.get('stage')=='EXECUTION':
            return dict(s.get('action') or {})
    return {}


def schema_obj(s):
    if s.get('family') != FailureDerivedProbabilisticBeliefInducer.FAMILY:
        return None
    return ProbabilisticBeliefSchema(
        s['family'], tuple(s['hypotheses']), tuple(s['probes']), tuple(s['observations']),
        tuple((x[0],float(x[1])) for x in s['priors']),
        tuple((x[0],x[1],x[2],float(x[3])) for x in s['likelihoods']),
        float(s['confidence_threshold']), s.get('output_policy','MAP_IF_POSTERIOR_AT_OR_ABOVE_THRESHOLD_ELSE_DEFER'),
        s.get('origin','FAILURE_DERIVED_BOUNDED_PROBABILISTIC_BELIEF')
    )


def main():
    tasks=requests()
    # Explicit precheck: the previous set-valued belief layer cannot fit these
    # stochastic-overlap decision sequences exactly.
    baseline=[]
    oldp=FailureDerivedBeliefSetInducer()
    for r,_ in tasks:
        b,n=oldp.search(r.task.train)
        baseline.append({'task':r.task.name,'set_belief_exact_schema_found': bool(b is not None and b.exact==1.0),'generated':n,'best_exact': None if b is None else b.exact})

    if DB.exists(): DB.unlink()
    old=unified_mod.FailureDrivenSchemaInducer
    unified_mod.FailureDrivenSchemaInducer=FrontierPortfolioV5
    try:
        k=UnifiedYADOKernelV30RC6R6SchemaAdaptation(str(DB))
        try:
            rows=[]
            for r,truth in tasks:
                good=k.run_causal_cycle(r)
                abl=k.run_causal_cycle(r,ablate={'MECHANISM'})
                rows.append((r,truth,good,abl))
            snap=k.unified_snapshot()
        finally:k.close()
    finally:unified_mod.FailureDrivenSchemaInducer=old

    detail=[]; all_pass=True
    inducer=FailureDerivedProbabilisticBeliefInducer()
    for r,truth,g,a in rows:
        m=mechanism(g); s=m.get('schema') or {}; obj=schema_obj(s)
        tr=[]
        if obj is not None:
            _,tr=inducer.execute_with_trace(obj,r.task.live_input)
        passed=(g.get('cycle_success') is True and obj is not None and g.get('blind_score')==1.0 and g.get('ablation_score')==0.0 and g.get('restore_score')==1.0 and a.get('cycle_success') is False)
        all_pass=all_pass and passed
        detail.append({
            'task':r.task.name,'cycle_id':g.get('cycle_id'),'cycle_success':g.get('cycle_success'),'family':s.get('family'),
            'selected_priors':s.get('priors'),'selected_likelihoods':s.get('likelihoods'),'selected_threshold':s.get('confidence_threshold'),
            'hidden_benchmark_parameters_not_supplied_to_learner':truth,
            'train_exact':m.get('train_exact'),'blind':g.get('blind_score'),'ablation':g.get('ablation_score'),'restore':g.get('restore_score'),
            'live_output':g.get('live_output'),'expected_live':g.get('expected_live'),'posterior_live_trace':tr,
            'learning_closed':g.get('learning_closed'),'mechanism_ablation_cycle_success':a.get('cycle_success'),
        })
    report={
        'schema':'yado.stateful_frontier_repair.cycle10.v1',
        'status':'SHADOW_SUPPORTED_BOUNDED_PROBABILISTIC_BELIEF' if all_pass and all(not x['set_belief_exact_schema_found'] for x in baseline) else 'WITHHOLD',
        'baseline_set_valued_belief':baseline,
        'failure_diagnosis':{
            'set_valued_compatibility_filter':'INSUFFICIENT_WHEN_ALL_HYPOTHESES_REMAIN_POSSIBLE_BUT_EVIDENCE_CHANGES_RELATIVE_WEIGHT',
            'required_capability':'WEIGHTED_POSTERIOR_UPDATE_WITH_CALIBRATED_DEFER',
        },
        'derived_representation_warrant':{
            'family':FailureDerivedProbabilisticBeliefInducer.FAMILY,
            'selection':'REVEALED_TRAIN_ONLY_EXACT_THEN_CALIBRATION_MARGIN',
            'fresh_used_for_selection':False,
            'posterior_policy':'MAP_IF_CONFIDENCE_THRESHOLD_ELSE_DEFER',
        },
        'cycles':detail,'observation_snapshot':snap,
        'claim_boundary':{
            'canonical_durable_head_modified':False,'shadow_runtime_binding_modified_only':True,
            'generic_bayes_updater_host_supplied':True,'parameter_grid_search_host_supplied':True,
            'specific_selected_priors_likelihoods_thresholds_data_derived_from_revealed_decision_examples':True,
            'selected_parameters_need_not_equal_hidden_ground_truth_if_behaviorally_equivalent_on_tested_distribution':True,
            'general_bayesian_inference_proven':False,'general_pomdp_inference_proven':False,
            'continuous_distributions_or_model_uncertainty_proven':False,
        }
    }
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if report['status'].startswith('SHADOW_SUPPORTED') else 2

if __name__=='__main__': raise SystemExit(main())
