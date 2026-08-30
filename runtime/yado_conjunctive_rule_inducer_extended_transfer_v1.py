from __future__ import annotations
from pathlib import Path
import hashlib,json,os,random,sys,time

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))

# Import the already-evidenced algorithm candidate. Its module also runs its original
# regression corpus; that is acceptable and acts as an internal non-regression check.
from yado_conjunctive_rule_inducer_v1 import (
    ConjunctiveRuleInducerV1, program_acc, canonical_program
)

OUT=ROOT/'conjunctive_rule_inducer_extended_transfer_v1'
OUT.mkdir(exist_ok=True)

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)

def cases(seed,n,fields,law,values):
    r=random.Random(seed);out=[]
    for _ in range(n):
        x={f:r.choice(values[f]) for f in fields}
        x['unseen_noise_a']=r.randint(-9,9)
        x['unseen_noise_b']=r.choice(['N0','N1','N2','N3'])
        out.append({'input':x,'expected':law(x)})
    return out

TASKS={}

# 1. Access-control / security policy: ternary allow override + deny by default.
fields=['identity_verified','resource_class','session_risk','mfa']
vals={
 'identity_verified':[True,False],
 'resource_class':['PUBLIC','INTERNAL','RESTRICTED'],
 'session_risk':['LOW','MEDIUM','HIGH'],
 'mfa':[True,False],
}
def law_access(x):
    if x['identity_verified'] and x['mfa'] and x['resource_class']=='RESTRICTED' and x['session_risk']=='LOW':
        return 'ALLOW'
    if x['identity_verified'] and x['resource_class']=='INTERNAL' and x['session_risk']!='HIGH':
        return 'ALLOW'
    return 'DENY'
TASKS['ACCESS_CONTROL_TRANSFER']=(fields,law_access,vals)

# 2. Compiler optimization gate.
fields=['alias_free','loop_invariant','overflow_safe','vector_width']
vals={
 'alias_free':[True,False],
 'loop_invariant':[True,False],
 'overflow_safe':[True,False],
 'vector_width':['SCALAR','SIMD128','SIMD256'],
}
def law_compiler(x):
    if x['alias_free'] and x['loop_invariant'] and x['vector_width']=='SIMD256':
        return 'VECTORIZE'
    if x['loop_invariant'] and x['overflow_safe']:
        return 'HOIST'
    return 'KEEP_BASELINE'
TASKS['COMPILER_OPTIMIZATION_TRANSFER']=(fields,law_compiler,vals)

# 3. Scientific evidence acceptance.
fields=['replicated','blinded','effect_direction','preregistered']
vals={
 'replicated':[True,False],
 'blinded':[True,False],
 'effect_direction':['POSITIVE','NEGATIVE','NULL'],
 'preregistered':[True,False],
}
def law_science(x):
    if x['replicated'] and x['blinded'] and x['preregistered']:
        return 'STRONG_EVIDENCE'
    if x['replicated'] and x['effect_direction']!='NULL':
        return 'MODERATE_EVIDENCE'
    return 'INSUFFICIENT'
TASKS['SCIENTIFIC_EVIDENCE_TRANSFER']=(fields,law_science,vals)

# 4. Fault isolation / hardware control.
fields=['sensor_agrees','thermal_alarm','voltage_alarm','redundancy_ok']
vals={
 'sensor_agrees':[True,False],
 'thermal_alarm':[True,False],
 'voltage_alarm':[True,False],
 'redundancy_ok':[True,False],
}
def law_fault(x):
    if x['thermal_alarm'] and x['voltage_alarm'] and not x['redundancy_ok']:
        return 'EMERGENCY_SHUTDOWN'
    if (x['thermal_alarm'] or x['voltage_alarm']) and not x['sensor_agrees']:
        return 'ISOLATE_AND_RECHECK'
    return 'CONTINUE'
TASKS['FAULT_ISOLATION_TRANSFER']=(fields,law_fault,vals)

# 5. Scheduler/resource policy.
fields=['deadline_tight','memory_pressure','io_bound','checkpoint_ready']
vals={
 'deadline_tight':[True,False],
 'memory_pressure':['LOW','HIGH'],
 'io_bound':[True,False],
 'checkpoint_ready':[True,False],
}
def law_sched(x):
    if x['deadline_tight'] and x['checkpoint_ready'] and x['memory_pressure']=='HIGH':
        return 'PREEMPT_AND_CHECKPOINT'
    if x['io_bound'] and x['memory_pressure']=='LOW':
        return 'DEPRIORITIZE_CPU'
    return 'RUN'
TASKS['RESOURCE_SCHEDULING_TRANSFER']=(fields,law_sched,vals)

results={}
all_pass=True
for i,(name,(fields,law,vals)) in enumerate(TASKS.items()):
    train=cases(61000+i*100,480,fields,law,vals)
    val=cases(62000+i*100,240,fields,law,vals)
    blind=cases(63000+i*100,600,fields,law,vals)

    t0=time.perf_counter()
    try:
        p=ConjunctiveRuleInducerV1.synthesize(name,'LOGIC',train,min_support=3,max_rules=12)
        synth=time.perf_counter()-t0
        tr=program_acc(p,train);va=program_acc(p,val);bl=program_acc(p,blind)
        ab=program_acc(p,blind,ablated=True);restore=program_acc(p,blind)
        passed=(tr>=.98 and va>=.97 and bl>=.97 and restore==bl and bl>ab+.02)
        results[name]={
          'pass':passed,'train':tr,'validation':va,'fresh_blind':bl,
          'ablation':ab,'restore':restore,'synthesis_seconds':synth,
          'program':canonical_program(p),
          'train_count':len(train),'validation_count':len(val),'blind_count':len(blind),
        }
    except Exception as e:
        results[name]={
          'pass':False,'train':0.0,'validation':0.0,'fresh_blind':0.0,
          'ablation':0.0,'restore':0.0,'error':repr(e),
          'train_count':len(train),'validation_count':len(val),'blind_count':len(blind),
        }
    all_pass &= bool(results[name]['pass'])

fresh=[v['fresh_blind'] for v in results.values()]
summary={
 'task_count':len(results),
 'tasks_passed':sum(v['pass'] for v in results.values()),
 'mean_fresh_blind':sum(fresh)/len(fresh),
 'min_fresh_blind':min(fresh),
 'all_pass':all_pass,
}
report={
 'schema':'yado.conjunctive_rule_inducer.extended_transfer.v1',
 'status':'PASS_CONJUNCTIVE_RULE_INDUCER_EXTENDED_TRANSFER_V1' if all_pass else 'WITHHOLD_CONJUNCTIVE_RULE_INDUCER_EXTENDED_TRANSFER_V1',
 'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),
 'candidate_component_digest':'3b31c7d26e4e51db3a5135a58ac4fe764f45ce96bf4e80e016172bd212e43150',
 'domains':['ACCESS_CONTROL','COMPILER_OPTIMIZATION','SCIENTIFIC_EVIDENCE','FAULT_ISOLATION','RESOURCE_SCHEDULING'],
 'results':results,'summary':summary,
 'canonical_mutation':False,'promotion_applied':False,
 'semantic_boundary':'FIVE NEW HOST-DEFINED BOUNDED RULE-INDUCTION DOMAINS; TESTS ALGORITHM TRANSFER, NOT GENERAL REASONING',
}
report['receipt_sha256']=hashlib.sha256(canon(report).encode()).hexdigest()
(ROOT/'yado_conjunctive_rule_inducer_extended_transfer_v1_receipt.json').write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps({
 'status':report['status'],'summary':summary,
 'per_task':{k:{q:v.get(q) for q in ('pass','validation','fresh_blind','ablation','synthesis_seconds','error')} for k,v in results.items()},
 'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True,default=str))
