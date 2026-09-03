from __future__ import annotations
import json, random
from yado_transfer_memory_runtime_v1 import TransferExperience,TransferMemoryRuntime,naive_trajectory_retrieve

SEED=202608292
R=random.Random(SEED)
patterns={
  f'P{i}': {'stable':(f'goal{i}',f'check{i}'),'procedure':(f'OBSERVE{i}',f'REASON{i}',f'VERIFY{i}')} for i in range(20)
}
experiences=[]
# Repeated successful cross-domain evidence. Surface tags intentionally vary.
for pid,p in patterns.items():
    for d in ('code','research','ops'):
        surface=f'surface{R.randrange(80)}'
        experiences.append(TransferExperience(f'{pid}-{d}',d,[*p['stable'],d,surface],p['procedure'],R.uniform(.88,1.0),True))
# One-off brittle trajectories with high lexical overlap but wrong procedures.
for j in range(600):
    pid=f'P{R.randrange(20)}';p=patterns[pid];surface=f'surface{R.randrange(80)}'
    experiences.append(TransferExperience(f'Z{j:04d}','single',[p['stable'][0],surface,'single'],(f'WRONG{j}',),R.uniform(.25,.65),True))

rt=TransferMemoryRuntime(min_support=3,min_domains=3,min_mean_score=.80,max_failure_rate=.2)
con=rt.consolidate(experiences)
memories=con['memories']
new_correct=naive_correct=0
cases=2000
for i in range(cases):
    pid=f'P{R.randrange(20)}';p=patterns[pid];surface=f'surface{R.randrange(80)}';newdomain=f'new{R.randrange(50)}'
    q=[*p['stable'],surface,newdomain]
    rr=rt.retrieve(memories,q,target_domain=newdomain,k=1)
    if rr['rows'] and tuple(rr['rows'][0]['procedure'])==tuple(p['procedure']): new_correct+=1
    n=naive_trajectory_retrieve(experiences,q)
    if n is not None and tuple(n.procedure)==tuple(p['procedure']): naive_correct+=1
out={
 'schema':'yado.transfer_memory.fresh_holdout.v1','seed':SEED,
 'train_experiences':len(experiences),'consolidated_memories':len(memories),'cases':cases,
 'procedural_transfer_correct':new_correct,'naive_trajectory_correct':naive_correct,
 'procedural_transfer_accuracy':new_correct/cases,'naive_trajectory_accuracy':naive_correct/cases,
 'gain':(new_correct-naive_correct)/cases,
 'pass':new_correct/cases>=.95 and new_correct>naive_correct,
}
print(json.dumps(out,indent=2))
open('yado_transfer_memory_fresh_holdout_v1_report.json','w').write(json.dumps(out,indent=2,sort_keys=True)+'\n')
if not out['pass']:raise SystemExit(1)
