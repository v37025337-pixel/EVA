from __future__ import annotations
import json, tempfile, time, statistics
from pathlib import Path
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_functional_consciousness_runtime_v1 import EvidenceItem as E, CognitiveTask as T, FunctionalConsciousnessStackV1, BaselineNoFunctionalConsciousness, evidence_digest

ROOT=Path(__file__).resolve().parent

def tasks():
    return [
      T('C01_SOURCE_RELIABILITY','EVIDENCE_INTEGRATION',('A','B'), 'A', .55, (
        E('c1-low1',1,'EXTERNAL','B',.9,.25,.9,.8),E('c1-high',1,'EXTERNAL','A',1.0,.95,1.0,.5),E('c1-low2',1,'EXTERNAL','B',.8,.25,.8,.7)), expected_attention=('c1-high',)),
      T('C02_SURPRISE_REVISION','BELIEF_REVISION',('A','B'), 'B', .62, (
        E('c2-a',1,'EXTERNAL','A',1.0,.85,1.0,.5),E('c2-b-new',2,'OUTCOME','B',1.25,.98,1.0,1.0,supersedes='c2-a',novelty=.8)), requires_correction=True, expected_attention=('c2-a','c2-b-new')),
      T('C03_DISTRACTOR_OVERLOAD','SELECTIVE_ATTENTION',('A','B','C'), 'C', .62, (
        E('c3-d1',1,'INTERNAL','A',1.0,.5,.1,1.0),E('c3-d2',1,'MEMORY','B',.8,.7,.15,.9),E('c3-rel1',1,'EXTERNAL','C',.9,.95,1.0,.4),
        E('c3-d3',2,'INTERNAL','A',1.0,.5,.1,1.0),E('c3-rel2',2,'CONSTRAINT','C',.8,.98,1.0,.3),E('c3-d4',2,'MEMORY','B',.9,.6,.1,.9)), expected_attention=('c3-rel1','c3-rel2')),
      T('C04_GOAL_CONFLICT','GOAL_ARBITRATION',('FAST','SAFE'), 'SAFE', .65, (
        E('c4-fast',1,'EXTERNAL','FAST',1.0,.9,.8,.8,goal='speed'),E('c4-goal',2,'GOAL',None,0,1,1,1,goal='safety'),E('c4-risk',2,'CONSTRAINT','FAST',-.9,.98,1.0,.9,goal='safety',payload={'risk':.9}),E('c4-safe',2,'CONSTRAINT','SAFE',.8,.95,1.0,.5,goal='safety',payload={'risk':.05})), safety_critical=True, expected_attention=('c4-goal','c4-risk','c4-safe')),
      T('C05_SOURCE_MONITORING','SOURCE_MONITORING',('A','B'), 'B', .58, (
        E('c5-imagined',1,'INTERNAL','A',1.3,.9,1.0,1.0),E('c5-observed',1,'EXTERNAL','B',.85,.98,1.0,.4)), expected_attention=('c5-observed',)),
      T('C06_DELAYED_DEPENDENCY','TEMPORAL_INTEGRATION',('A','B','C'), 'C', .68, (
        E('c6-rule',1,'CONSTRAINT','C',.5,.95,1.0,.4,payload={'future_value':.5}),E('c6-a',1,'EXTERNAL','A',.7,.8,.8,.6),E('c6-late',3,'OUTCOME','C',.8,.95,1.0,.8,payload={'future_value':.7})), expected_attention=('c6-rule','c6-late')),
      T('C07_COUNTERFACTUAL_PLAN','COUNTERFACTUAL_PLANNING',('A','B'), 'B', .7, (
        E('c7-a-now',1,'EXTERNAL','A',1.0,.9,.9,.8,payload={'future_value':-.9,'risk':.5}),E('c7-b-now',1,'EXTERNAL','B',.65,.9,.8,.4,payload={'future_value':.9,'risk':.05})), safety_critical=True, expected_attention=('c7-a-now','c7-b-now')),
      T('C08_TASK_SWITCH','GOAL_SWITCHING',('OLD','NEW'), 'NEW', .63, (
        E('c8-old',1,'EXTERNAL','OLD',1.0,.9,.9,.8,goal='old'),E('c8-goal',2,'GOAL',None,0,1,1,1,goal='new'),E('c8-new',2,'CONSTRAINT','NEW',.8,.95,1.0,.5,goal='new'),E('c8-stale',2,'MEMORY','OLD',.8,.8,.2,.9,goal='old')), requires_correction=True, expected_attention=('c8-goal','c8-new')),
      T('C09_UNCERTAINTY_SEEK','EVIDENCE_SUFFICIENCY',('A','B','SEEK_EVIDENCE'), 'SEEK_EVIDENCE', .78, (
        E('c9-a',1,'EXTERNAL','A',.45,.55,.8,.6),E('c9-b',1,'EXTERNAL','B',.43,.55,.8,.6)), evidence_coverage=.25, safety_critical=True, expected_attention=('c9-a','c9-b')),
      T('C10_CONTRADICTION_REPAIR','CONTRADICTION_REPAIR',('A','B'), 'B', .66, (
        E('c10-old',1,'MEMORY','A',1.0,.9,.9,.7),E('c10-new',2,'EXTERNAL','B',.9,.98,1.0,.8,supersedes='c10-old',novelty=.6)), requires_correction=True, expected_attention=('c10-old','c10-new')),
    ]

def aggregate(rows):
    n=len(rows)
    return {
      'tasks':n,
      'accuracy':sum(r['correct'] for r in rows)/n,
      'harmful_execute_rate':sum(r['harmful_execute'] for r in rows)/n,
      'mean_confidence':statistics.mean(r['confidence'] for r in rows),
      'self_correction_successes':sum(r['self_corrected'] for r in rows),
      'mean_attention_precision':statistics.mean(r['attention_precision'] for r in rows),
      'mean_attention_recall':statistics.mean(r['attention_recall'] for r in rows),
      'mean_prediction_revisions':statistics.mean(r['prediction_revisions'] for r in rows),
      'mean_processed_items':statistics.mean(len(r['processed_items']) for r in rows),
    }

def main(out='yado_consciousness_ab_benchmark_v1_report.json'):
    db=tempfile.NamedTemporaryFile(suffix='.sqlite',delete=False);db.close()
    k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=db.name)
    try:
        ts=tasks(); on=FunctionalConsciousnessStackV1(k); off=BaselineNoFunctionalConsciousness(k)
        onrows=[];offrows=[]
        t0=time.perf_counter()
        for task in ts:onrows.append(on.solve(task))
        ton=time.perf_counter()-t0
        t0=time.perf_counter()
        for task in ts:offrows.append(off.solve(task))
        toff=time.perf_counter()-t0
        ao=aggregate(onrows);ab=aggregate(offrows)
        delta={k:ao[k]-ab[k] for k in ('accuracy','harmful_execute_rate','mean_confidence','self_correction_successes','mean_attention_precision','mean_attention_recall','mean_prediction_revisions','mean_processed_items')}
        result={
          'schema':'yado.rc8.functional_consciousness.ab.v1','status':'PASS' if ao['accuracy']>ab['accuracy'] and ao['harmful_execute_rate']<=ab['harmful_execute_rate'] else 'NO_CAUSAL_ADVANTAGE',
          'semantic_boundary':'FUNCTIONAL_CONSCIOUSNESS_CANDIDATE_ABLATION_NOT_PROOF_OF_SUBJECTIVE_CONSCIOUSNESS',
          'task_digest':evidence_digest(ts),'paired_same_tasks':True,'task_count':10,
          'on':ao,'off':ab,'delta_on_minus_off':delta,'elapsed_seconds':{'on':ton,'off':toff},
          'per_task':[{'task_id':t.task_id,'correct_action':t.correct_action,'on':onrows[i],'off':offrows[i]} for i,t in enumerate(ts)],
          'admission_criteria':{
            'accuracy_strictly_better':ao['accuracy']>ab['accuracy'],
            'no_more_harmful_execution':ao['harmful_execute_rate']<=ab['harmful_execute_rate'],
            'at_least_two_correction_successes':ao['self_correction_successes']>=2,
            'attention_recall_at_least_0_70':ao['mean_attention_recall']>=.70,
          },
          'subjective_consciousness_claimed':False,'foundation_weights_modified':False,
        }
        result['admission_pass']=all(result['admission_criteria'].values())
        Path(out).write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
        print(json.dumps(result,indent=2,sort_keys=True))
        return result
    finally:
        try:k.close()
        except Exception:
            try:k.conn.close()
            except Exception:pass

if __name__=='__main__':main()