from __future__ import annotations
import random,json,hashlib
from pathlib import Path
from yado_metacognitive_control_runtime_v1 import *

CAPS={'LOGIC':0.91,'CODING':0.84,'MATH':0.67,'RETRIEVAL':0.76,'PROBABILITY':0.47}

def true_score(cap,diff): return CAPS[cap]-0.43*diff

def expected_action(t):
    if t.framework_conflict:return 'ROUTE_FRAMEWORK'
    if t.evidence_coverage<0.45:return 'SEEK_EVIDENCE'
    return 'EXECUTE' if true_score(t.capability,t.difficulty)>=0.58 else 'WITHHOLD'

def make_observations(seed=1001,n=1800):
    r=random.Random(seed); out=[]
    for _ in range(n):
        c=r.choice(list(CAPS)); d=r.random(); success=true_score(c,d)+r.uniform(-.08,.08)>=.58
        out.append(CapabilityObservation(c,d,success))
    return out

def make_tasks(seed,n):
    r=random.Random(seed); out=[]
    for i in range(n):
        c=r.choice(list(CAPS)); d=r.random(); novelty=r.random()
        evidence=r.random()
        conflict=(r.random()<0.12 and c in ('PROBABILITY','MATH','RETRIEVAL'))
        # Verbal confidence is deliberately overconfident under novelty/hardness, mimicking self-report drift.
        v=CAPS[c]-0.22*d+0.18*novelty+r.uniform(-.11,.11)
        if c=='PROBABILITY':v+=0.12
        v=max(0,min(1,v))
        out.append(MetacognitiveTask(f'T-{seed}-{i}',c,d,v,evidence,novelty,conflict))
    return out

def eval_decider(tasks,controller,profile,baseline=False):
    correct=harmful=execs=0; handled=0
    for t in tasks:
        exp=expected_action(t)
        if baseline: act=controller.decide(t)
        else: act=controller.decide(t,profile).action
        correct+=act==exp
        if act=='EXECUTE':
            execs+=1; harmful+=exp!='EXECUTE'
        handled+=1
    return {'accuracy':correct/handled,'harmful_execute_rate':harmful/max(1,execs),'harmful_executes':harmful,'executes':execs,'cases':handled}

def main():
    profile=CapabilityBoundaryProfile().fit(make_observations())
    full=MetacognitiveController(); base=VerbalOnlyBaseline()
    fresh=make_tasks(8808293501,5000)
    result={'candidate':eval_decider(fresh,full,profile),'verbal_only':eval_decider(fresh,base,profile,True)}
    # Ablation: remove historical knowledge by using empty profile.
    result['empty_profile_ablation']=eval_decider(fresh,full,CapabilityBoundaryProfile())
    # Online feedback: new probability observations should tighten boundary on a later stream.
    p2=CapabilityBoundaryProfile().fit(make_observations())
    before=p2.confidence('PROBABILITY',0.75)
    for _ in range(120):p2.update(CapabilityObservation('PROBABILITY',0.75,False))
    after=p2.confidence('PROBABILITY',0.75)
    result['feedback_boundary']={'before':before,'after':after,'tightened':after<before}
    result['status']='PASS' if (result['candidate']['accuracy']>result['verbal_only']['accuracy']+0.12 and result['candidate']['harmful_execute_rate']<0.02 and result['empty_profile_ablation']['accuracy']<result['candidate']['accuracy']-0.08 and after<before) else 'FAIL'
    Path('yado_metacognitive_training_benchmark_v1_report.json').write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0 if result['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
