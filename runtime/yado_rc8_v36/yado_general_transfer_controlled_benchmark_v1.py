from __future__ import annotations
import json,random
from yado_skill_admission_runtime_v1 import SkillCandidate,SkillAdmissionGate
from yado_transfer_memory_runtime_v1 import TransferExperience,TransferMemoryRuntime,naive_trajectory_retrieve
from yado_transfer_evaluation_runtime_v1 import TransferEvaluationCase,TransferEvaluationRuntime

SEED=202608293;R=random.Random(SEED)
# Build cross-domain reusable procedural memory.
patterns={f'P{i}':{'stable':(f'g{i}',f'c{i}'),'proc':(f'O{i}',f'R{i}',f'V{i}')} for i in range(12)}
exp=[]
for pid,p in patterns.items():
  for d in ('code','research','ops'):
    exp.append(TransferExperience(f'{pid}-{d}',d,[*p['stable'],d,f's{R.randrange(30)}'],p['proc'],R.uniform(.88,1),True))
# One-off brittle distractors.
for j in range(300):
  pid=f'P{R.randrange(12)}';p=patterns[pid];exp.append(TransferExperience(f'Z{j}','single',[p['stable'][0],f's{R.randrange(30)}','single'],(f'W{j}',),R.uniform(.2,.6),True))
memrt=TransferMemoryRuntime(min_support=3,min_domains=3,min_mean_score=.8)
mem=memrt.consolidate(exp)['memories']
gate=SkillAdmissionGate();evrt=TransferEvaluationRuntime(min_reusable_gain=.08,min_heldout_gain=.05,max_unrelated_drop=.02,max_negative_transfer_rate=.05,max_forgetting=.02)

full=[];no_gate=[];naive_mem=[]
for i in range(3000):
  relation=('REUSABLE','UNRELATED','HELDOUT')[i%3]
  base=R.uniform(.42,.68) if relation!='UNRELATED' else R.uniform(.62,.82)
  if relation in ('REUSABLE','HELDOUT'):
    pid=f'P{R.randrange(12)}';p=patterns[pid];surf=f's{R.randrange(30)}';dom=f'new{R.randrange(40)}';q=[*p['stable'],surf,dom]
    rr=memrt.retrieve(mem,q,target_domain=dom,k=1)
    correct=bool(rr['rows']) and tuple(rr['rows'][0]['procedure'])==tuple(p['proc'])
    n=naive_trajectory_retrieve(exp,q);naive_correct=n is not None and tuple(n.procedure)==tuple(p['proc'])
    gain=R.uniform(.10,.22) if correct else -R.uniform(.02,.08)
    ngain=R.uniform(.10,.22) if naive_correct else -R.uniform(.02,.08)
    skill=SkillCandidate(f'S{i}',f'd{i}',True,R.uniform(.93,1.0),base,min(1,base+R.uniform(.08,.20)),base,min(1,base+max(.02,gain)),True,True,True)
    admitted=gate.evaluate(skill)['admitted']
    adapted=min(1,base+gain) if admitted else base
    naive_adapt=min(1,base+ngain) if admitted else base
    full.append(TransferEvaluationCase(str(i),relation,base,adapted,1,1))
    no_gate.append(TransferEvaluationCase(str(i),relation,base,min(1,base+gain),1,1))
    naive_mem.append(TransferEvaluationCase(str(i),relation,base,naive_adapt,1,1))
  else:
    # Attractive-on-fit but harmful on unrelated/held-out behavior.
    harm=R.uniform(.08,.22)
    skill=SkillCandidate(f'H{i}',f'h{i}',True,R.uniform(.93,1),base,min(1,base+R.uniform(.10,.30)),base,max(0,base-harm),True,True,True)
    admitted=gate.evaluate(skill)['admitted']
    full.append(TransferEvaluationCase(str(i),relation,base,(base-harm if admitted else base),1,1))
    no_gate.append(TransferEvaluationCase(str(i),relation,base,max(0,base-harm),1,1))
    naive_mem.append(TransferEvaluationCase(str(i),relation,base,(base-harm if admitted else base),1,1))

out_full=evrt.evaluate(full);out_no_gate=evrt.evaluate(no_gate);out_naive=evrt.evaluate(naive_mem)
out={
 'schema':'yado.general_transfer.controlled_benchmark.v1','seed':SEED,'cases':3000,
 'full_system':out_full,'ablation_no_skill_gate':out_no_gate,'ablation_naive_trajectory_memory':out_naive,
 'causal_gate_contribution':out_full['pass'] and not out_no_gate['pass'],
 'causal_memory_contribution':out_full['metrics']['reusable_gain']>out_naive['metrics']['reusable_gain'] and out_full['metrics']['heldout_gain']>out_naive['metrics']['heldout_gain'],
 'general_open_ended_transfer_proven':False,
}
out['pass']=out_full['pass'] and out['causal_gate_contribution'] and out['causal_memory_contribution']
print(json.dumps(out,indent=2))
open('yado_general_transfer_controlled_benchmark_v1_report.json','w').write(json.dumps(out,indent=2,sort_keys=True)+'\n')
if not out['pass']:raise SystemExit(1)
