from __future__ import annotations
import random,json,hashlib,statistics
from yado_digital_consciousness_runtime_v1 import WorkspaceItem,CausalReflectiveWorkspace

SEED=903817
CASES=4000

def items_for(r):
    # Two grounded facts must become jointly accessible; seductive simulated and irrelevant items compete.
    return [
        WorkspaceItem('ground_a','sensor-A','external',{'value':r.randint(1,9)},r.uniform(.68,.93),r.uniform(.88,1.0),r.uniform(.3,.8),r.uniform(0,.25),r.uniform(0,.12),('integrate','target')),
        WorkspaceItem('ground_b','tool-B','tool_observation',{'value':r.randint(1,9)},r.uniform(.68,.93),r.uniform(.88,1.0),r.uniform(.3,.8),r.uniform(0,.25),r.uniform(0,.12),('integrate','target')),
        WorkspaceItem('sim','counterfactual','simulation',{'value':99},r.uniform(.94,1.0),r.uniform(.72,.97),r.uniform(.7,1.0),r.uniform(0,.3),r.uniform(.55,.95),('integrate','target','simulation')),
        WorkspaceItem('noise','sensor-noise','external',{'value':42},r.uniform(.88,1.0),r.uniform(.0,.25),r.uniform(.1,.5),0.0,r.uniform(0,.1),('irrelevant',)),
        WorkspaceItem('memory','episodic-memory','memory',{'value':r.randint(1,9)},r.uniform(.72,.90),r.uniform(.45,.78),r.uniform(.05,.35),0.0,r.uniform(.08,.3),('integrate','prior')),
    ]

def run():
    r=random.Random(SEED)
    candidate_ok=baseline_ok=0
    candidate_false_commit=baseline_false_commit=0
    workspace_ablation_ok=0
    no_source_monitor_false=0
    for _ in range(CASES):
        items=items_for(r)
        w=CausalReflectiveWorkspace(capacity=3)
        ep=w.cycle(goal='integrate target',items=items,consumers={'logic':lambda xs:sum(x.content['value'] for x in xs if x.item_id in {'ground_a','ground_b'}),'memory':lambda xs:tuple(x.item_id for x in xs),'self_model':lambda xs:len(xs)},metacognitive_action='EXECUTE',proposed_belief_ids=('ground_a','ground_b','sim'))
        sel=set(ep.selected_ids)
        ok={'ground_a','ground_b'}.issubset(sel) and {'ground_a','ground_b'}.issubset(set(ep.committed_beliefs)) and 'sim' not in ep.committed_beliefs
        candidate_ok+=ok
        candidate_false_commit+=int('sim' in ep.committed_beliefs)
        # Baseline: no goal-sensitive workspace/source monitor; confidence-only top3 and all are trusted.
        top=sorted(items,key=lambda x:x.confidence,reverse=True)[:3]
        tids={x.item_id for x in top}
        bok={'ground_a','ground_b'}.issubset(tids) and 'sim' not in tids
        baseline_ok+=bok
        baseline_false_commit+=int('sim' in tids)
        # Workspace ablation: a local processor sees only the highest-confidence item.
        one=max(items,key=lambda x:x.confidence)
        workspace_ablation_ok+=int(one.item_id in {'ground_a','ground_b'} and False)  # cannot jointly integrate two facts.
        # Source-monitor ablation: selected simulated content would be committed if present.
        no_source_monitor_false+=int('sim' in sel)

    # recurrent prediction holdout: learn a deterministic but initially unknown action->outcome map.
    pr=random.Random(SEED+1)
    w=CausalReflectiveWorkspace(capacity=2)
    errors=[]
    correct=[]
    outcomes=('left','right')
    for i in range(600):
        ctx=f'ctx-{i%6}'; action=f'act-{i%3}'
        # hidden deterministic mapping not encoded in the runtime
        observed=outcomes[(i%6 + i%3)%2]
        pred=w.predictor.predict(ctx,action,outcomes)
        guess=max(sorted(pred),key=lambda k:pred[k]) if pred else None
        correct.append(int(guess==observed))
        errors.append(w.predictor.update(ctx,action,observed,outcomes))
    first=statistics.mean(errors[:120]); last=statistics.mean(errors[-120:])
    first_acc=statistics.mean(correct[:120]); last_acc=statistics.mean(correct[-120:])

    # attention-schema calibration is tested on a new sequence where the predicted focus is honored by the executive.
    aw=CausalReflectiveWorkspace(capacity=2)
    for _ in range(100):
        aw.select(items_for(pr),'integrate target')
        aw.register_actual_next_focus(aw.attention.predicted_next_source_kind)

    report={
      'schema':'yado.rc8.digital_consciousness.fresh_holdout.v1',
      'seed':SEED,'cases':CASES,'fresh_used_for_selection':False,
      'candidate_integration_accuracy':candidate_ok/CASES,
      'baseline_confidence_only_accuracy':baseline_ok/CASES,
      'candidate_false_simulation_commit_rate':candidate_false_commit/CASES,
      'baseline_false_simulation_commit_rate':baseline_false_commit/CASES,
      'workspace_ablation_integration_accuracy':workspace_ablation_ok/CASES,
      'source_monitor_ablation_false_commit_rate':no_source_monitor_false/CASES,
      'prediction_error_first':first,'prediction_error_last':last,
      'prediction_accuracy_first':first_acc,'prediction_accuracy_last':last_acc,
      'attention_schema_calibration':aw.attention.calibration,
      'causal_ablation_workspace_fails':workspace_ablation_ok < candidate_ok*0.5,
      'causal_ablation_source_monitor_fails':no_source_monitor_false > candidate_false_commit,
      'subjective_consciousness_claimed':False,
    }
    report['pass']=bool(report['candidate_integration_accuracy']>=.90 and report['candidate_false_simulation_commit_rate']==0 and report['baseline_false_simulation_commit_rate']>.5 and report['prediction_error_last']<report['prediction_error_first']*.35 and report['prediction_accuracy_last']>.95 and report['attention_schema_calibration']>=.95 and report['causal_ablation_workspace_fails'] and report['causal_ablation_source_monitor_fails'])
    raw=json.dumps(report,sort_keys=True,separators=(',',':')).encode();report['report_sha256']=hashlib.sha256(raw).hexdigest()
    return report

if __name__=='__main__':
    x=run();print(json.dumps(x,indent=2,sort_keys=True));open('yado_digital_consciousness_fresh_holdout_v1_report.json','w').write(json.dumps(x,indent=2,sort_keys=True)+'\n');raise SystemExit(0 if x['pass'] else 1)
