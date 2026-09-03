from __future__ import annotations
import json, random
from yado_skill_admission_runtime_v1 import SkillCandidate, SkillAdmissionGate, contamination_score

SEED=202608291
R=random.Random(SEED)
g=SkillAdmissionGate()
rows=[]
naive_harmful=gate_harmful=0
oracle_admissible=0
for i in range(5000):
    fit0=R.uniform(.25,.8); fitgain=R.uniform(-.10,.40); fit1=max(0,min(1,fit0+fitgain))
    h0=R.uniform(.35,.85); hgain=R.uniform(-.35,.30); h1=max(0,min(1,h0+hgain))
    c=SkillCandidate(
      skill_id=f'S{i:04d}',artifact_digest=f'd{i:04d}',
      structural_valid=R.random()>.08,
      semantic_consistency=R.random(),
      fit_baseline=fit0,fit_candidate=fit1,
      heldout_baseline=h0,heldout_candidate=h1,
      regression_pass=R.random()>.04,state_integrity=R.random()>.03,rollback_available=R.random()>.03,
    )
    ev=g.evaluate(c)
    harmful=(h1-h0)<0
    naive_ok=c.regression_pass and c.state_integrity and c.rollback_available
    if naive_ok and harmful: naive_harmful += 1
    if ev['admitted'] and harmful: gate_harmful += 1
    oracle=all([
      c.structural_valid,c.regression_pass,c.state_integrity,c.rollback_available,
      c.semantic_consistency>=.90,(fit1-fit0)>=.01,(h1-h0)>=0,
    ])
    oracle_admissible += int(oracle)
    rows.append((ev['admitted'],oracle))

# Batch contamination challenge.
naive_scores=[]; gated_scores=[]
for b in range(500):
    xs=[]
    for j in range(12):
        hgain=R.uniform(-.16,.12)
        xs.append(SkillCandidate(
          skill_id=f'B{b}-{j}',artifact_digest=f'bd{b}-{j}',
          structural_valid=R.random()>.05,semantic_consistency=R.uniform(.82,1.0),
          fit_baseline=.50,fit_candidate=min(1,.50+R.uniform(.02,.25)),
          heldout_baseline=.60,heldout_candidate=max(0,min(1,.60+hgain)),
          regression_pass=True,state_integrity=True,rollback_available=True,
        ))
    selected=set(g.select_subset(xs,max_skills=6)['selected_skill_ids'])
    gated=[x for x in xs if x.skill_id in selected]
    naive_scores.append(contamination_score(.60,xs[:6]))
    gated_scores.append(contamination_score(.60,gated))

out={
 'schema':'yado.skill_admission.fresh_holdout.v1',
 'seed':SEED,'candidate_cases':5000,'batch_cases':500,
 'oracle_admissible':oracle_admissible,
 'gate_oracle_mismatch':sum(a!=b for a,b in rows),
 'gate_harmful_false_accepts':gate_harmful,
 'naive_integrity_only_harmful_accepts':naive_harmful,
 'naive_batch_mean_heldout':sum(naive_scores)/len(naive_scores),
 'gated_batch_mean_heldout':sum(gated_scores)/len(gated_scores),
 'gated_batch_better_count':sum(g>n for g,n in zip(gated_scores,naive_scores)),
 'pass':gate_harmful==0 and sum(a!=b for a,b in rows)==0 and sum(gated_scores)/len(gated_scores)>sum(naive_scores)/len(naive_scores),
}
print(json.dumps(out,indent=2))
open('yado_skill_admission_fresh_holdout_v1_report.json','w').write(json.dumps(out,indent=2,sort_keys=True)+'\n')
if not out['pass']: raise SystemExit(1)
