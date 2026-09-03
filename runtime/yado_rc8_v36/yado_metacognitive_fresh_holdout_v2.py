from __future__ import annotations
import json
from pathlib import Path
from yado_metacognitive_training_benchmark_v1 import make_observations,make_tasks,eval_decider
from yado_metacognitive_control_runtime_v1 import CapabilityBoundaryProfile,MetacognitiveController,VerbalOnlyBaseline

def main():
    profile=CapabilityBoundaryProfile().fit(make_observations(seed=8819,n=2400))
    tasks=make_tasks(8808293701,7000)
    cand=eval_decider(tasks,MetacognitiveController(),profile)
    base=eval_decider(tasks,VerbalOnlyBaseline(),profile,True)
    empty=eval_decider(tasks,MetacognitiveController(),CapabilityBoundaryProfile())
    result={'seed':8808293701,'fresh_used_for_selection':False,'cases':7000,'candidate':cand,'verbal_only':base,'empty_profile_ablation':empty}
    result['status']='PASS' if (cand['accuracy']>=.89 and cand['accuracy']>base['accuracy']+.15 and cand['harmful_execute_rate']<.02 and empty['accuracy']<cand['accuracy']-.10) else 'FAIL'
    Path('yado_metacognitive_fresh_holdout_v2_report.json').write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0 if result['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
