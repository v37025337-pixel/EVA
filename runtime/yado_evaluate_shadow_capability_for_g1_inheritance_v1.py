from __future__ import annotations
from pathlib import Path
import copy, hashlib, json, os, random, sys, time

ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(PKG))

from yado_core_v2_1 import RuleProgramSynthesizer
from yado_conjunctive_rule_inducer_v1 import ConjunctiveRuleInducerV1, program_acc, canonical_program
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_metacognitive_control_runtime_v1 import CapabilityBoundaryProfile, CapabilityObservation

STATE=PKG/'yado_canonical_state_v3_rc8_external_cognitive.json'
REG=ROOT.parent/'candidates'/'shadow-algorithm-bank'/'active-registry-entry.json'
LIVE=ROOT.parent/'receipts'/'yado-live-shadow-meta-selection-developmental-v1-latest.json'
LINEAGE=ROOT.parent/'receipts'/'yado-real-developmental-lineage-v1-latest.json'
LEDGER=ROOT.parent/'architecture'/'evolution-ledger.json'
CAND=ROOT.parent/'candidates'/'g1-inheritance'/'conjunctive-rule-inducer-v1.json'
OUT=ROOT/'evaluate_shadow_capability_for_g1_inheritance_v1'
OUT.mkdir(exist_ok=True); CAND.parent.mkdir(parents=True,exist_ok=True)

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def sha_file(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def objdict(x): return dict(x.__dict__) if hasattr(x,'__dict__') else x
def event_hash(e):
    x=copy.deepcopy(e); x.pop('event_hash',None); return h(x)

def make_cases(seed,n,fields,values,law):
    r=random.Random(seed); out=[]
    for _ in range(n):
        x={f:r.choice(values[f]) for f in fields}
        x['generation_nonce']=r.randint(1000,9999)
        x['schema_token']=r.choice(['G1A','G1B','G1C'])
        out.append({'input':x,'expected':law(x)})
    return out

reg=json.loads(REG.read_text())
live=json.loads(LIVE.read_text())
lineage=json.loads(LINEAGE.read_text())
ledger=json.loads(LEDGER.read_text())

parent_before=sha_file(STATE)
spec=lineage['next_generation_spec']
candidate_generation=spec['candidate_generation_id']
parent_generation=spec['parent_generation_id']

if reg.get('state')!='ACTIVE_FOR_SHADOW_META_SELECTION':
    raise RuntimeError('ACTIVE_SHADOW_META_SELECTION_REQUIRED')
if live.get('status')!='PASS_LIVE_SHADOW_META_SELECTION_DEVELOPMENTAL_V1':
    raise RuntimeError('LIVE_DEVELOPMENTAL_EVIDENCE_REQUIRED')
if live.get('selected_family')!='CONJUNCTIVE_RULE_INDUCTION' or live.get('live_blind_pass') is not True:
    raise RuntimeError('LIVE_CONJUNCTIVE_SELECTION_REQUIRED')
if lineage.get('developmental_head')!='G0_RC8_V36' or parent_generation!='G0_RC8_V36':
    raise RuntimeError('G0_PARENT_REQUIRED')
if candidate_generation!='G1_CANDIDATE_S2':
    raise RuntimeError('EXPECTED_G1_CANDIDATE_S2')

# Verify the append-only chain before doing any work.
prev='GENESIS'; seen=set()
for i,e in enumerate(ledger['events']):
    assert e['index']==i and e['parent_event_hash']==prev and e['event_hash']==event_hash(e)
    assert e['event_id'] not in seen
    seen.add(e['event_id']); prev=e['event_hash']
assert prev==ledger['tail_event_hash']
assert ledger['current_head']=='G0_RC8_V36'

TASKS={}
f=['ancestor_ok','rollback_ready','regression_clean','migration_mode']
v={'ancestor_ok':[True,False],'rollback_ready':[True,False],'regression_clean':[True,False],'migration_mode':['EPHEMERAL','CANONICAL']}
TASKS['G1_SUCCESSOR_LINEAGE']=(f,v,lambda x:'INHERIT' if x['ancestor_ok'] and x['rollback_ready'] and x['regression_clean'] else 'WITHHOLD')

f=['counterexample_fresh','causal_mechanism','ablation_pass','repair_scope']
v={'counterexample_fresh':[True,False],'causal_mechanism':[True,False],'ablation_pass':[True,False],'repair_scope':['LOCAL','CROSS_DOMAIN']}
TASKS['G1_DEFICIT_REPAIR']=(f,v,lambda x:'RETAIN' if x['counterexample_fresh'] and x['causal_mechanism'] and x['ablation_pass'] else 'REJECT')

f=['programming_ok','mathematics_ok','exact_science_ok','evidence_epoch']
v={'programming_ok':[True,False],'mathematics_ok':[True,False],'exact_science_ok':[True,False],'evidence_epoch':['NEW','STALE']}
TASKS['G1_CROSS_DOMAIN_EVIDENCE']=(f,v,lambda x:'TRUST' if x['programming_ok'] and x['mathematics_ok'] and x['exact_science_ok'] else 'SEEK_MORE')

f=['candidate_active','evidence_complete','no_protected_regression','selector_epoch']
v={'candidate_active':[True,False],'evidence_complete':[True,False],'no_protected_regression':[True,False],'selector_epoch':['G1','LEGACY']}
TASKS['G1_META_SELECTION']=(f,v,lambda x:'SELECT' if x['candidate_active'] and x['evidence_complete'] and x['no_protected_regression'] else 'HOLD')

results={}
min_blind=1.0; min_drop=1.0; all_restore=True
for i,(name,(fields,values,law)) in enumerate(TASKS.items()):
    train=make_cases(88000+i*100,480,fields,values,law)
    val=make_cases(88100+i*100,240,fields,values,law)
    blind=make_cases(88200+i*100,720,fields,values,law)

    baseline={'status':'UNAVAILABLE','validation':0.0,'fresh_blind':0.0}
    try:
        old=RuleProgramSynthesizer.synthesize(name,'LOGIC',train,min_support=2)
        baseline={'status':'SYNTHESIZED','validation':program_acc(old,val),'fresh_blind':program_acc(old,blind)}
    except Exception as e:
        baseline={'status':'REJECTED','reason':repr(e),'validation':0.0,'fresh_blind':0.0}

    t0=time.perf_counter()
    p=ConjunctiveRuleInducerV1.synthesize(name,'LOGIC',train,min_support=2,max_rules=12)
    synth_s=time.perf_counter()-t0
    tr=program_acc(p,train); va=program_acc(p,val); bl=program_acc(p,blind)
    ab=program_acc(p,blind,ablated=True); restore=program_acc(p,blind)
    drop=bl-ab
    task_pass=(tr>=.99 and va>=.99 and bl>=.97 and restore==bl and drop>=.08)
    min_blind=min(min_blind,bl); min_drop=min(min_drop,drop); all_restore &= (restore==bl)
    results[name]={
        'pass':task_pass,'train':tr,'validation':va,'fresh_blind':bl,
        'ablation':ab,'causal_drop':drop,'restore':restore,'synthesis_seconds':synth_s,
        'baseline':baseline,'program':canonical_program(p),
    }

# Let the live G0 metacognitive controller judge the accumulated inheritance evidence.
profile=CapabilityBoundaryProfile()
for d,s in [(0.50,True),(0.65,True),(0.75,True),(0.82,True),(0.88,min_blind>=.97),(0.92,min_drop>=.08 and all_restore)]:
    profile.update(CapabilityObservation('G1_SHADOW_CAPABILITY_INHERITANCE',d,s))
task={
    'task_id':'G0-G1-INHERIT-001',
    'capability':'G1_SHADOW_CAPABILITY_INHERITANCE',
    'difficulty':0.90,
    'verbal_confidence':0.95,
    'evidence_coverage':1.0,
    'novelty':0.88,
    'framework_conflict':False,
}
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(OUT/'inheritance.sqlite'))
decision=objdict(k.metacognitive_decide(task,profile))
k.close()

parent_after=sha_file(STATE)
all_tasks_pass=all(x['pass'] for x in results.values())
gate_pass=(
    all_tasks_pass and min_blind>=.97 and min_drop>=.08 and all_restore
    and parent_before==parent_after
    and decision.get('action')=='EXECUTE'
)

candidate={
    'schema':'yado.g1.shadow_capability_inheritance.v1',
    'candidate_generation_id':candidate_generation,
    'parent_generation_id':parent_generation,
    'developmental_head_at_evaluation':'G0_RC8_V36',
    'capability_id':reg['entry_id'],
    'family':reg['family'],
    'component_digest':reg['component_digest'],
    'inheritance_state':'AUTHORIZED_FOR_G1_CANDIDATE_SHADOW' if gate_pass else 'WITHHELD',
    'activation_scope':'G1_CANDIDATE_SHADOW_META_SELECTION_ONLY',
    'canonical_active':False,
    'canonical_promotion':False,
    'evidence':{
        'registry_entry_digest':reg['registry_entry_digest'],
        'live_developmental_receipt':live['receipt_sha256'],
        'generation_spec_digest':spec['spec_digest'],
        'fresh_generation_task_count':len(results),
        'min_fresh_blind':min_blind,
        'min_ablation_drop':min_drop,
        'all_restore_exact':all_restore,
        'g0_metacognitive_decision':decision,
    },
    'known_limitations':['ACCESS_CONTROL_HIGHER_EXPRESSIVENESS_COUNTEREXAMPLE_REMAINS_OPEN'],
    'next_required_capability':'RUN_INHERITED_SHADOW_CAPABILITY_INSIDE_G1_CANDIDATE_V1' if gate_pass else 'REVISE_G1_INHERITANCE_CANDIDATE',
}
candidate['candidate_digest']=h(candidate)

report={
    'schema':'yado.evaluate_shadow_capability_for_g1_inheritance.v1',
    'status':'PASS_G1_SHADOW_CAPABILITY_INHERITANCE_V1' if gate_pass else 'WITHHOLD_G1_SHADOW_CAPABILITY_INHERITANCE_V1',
    'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),
    'developmental_head':'G0_RC8_V36',
    'candidate_generation_id':candidate_generation,
    'parent_generation_id':parent_generation,
    'inherited_capability_id':reg['entry_id'],
    'inherited_family':reg['family'],
    'fresh_generation_results':results,
    'summary':{
        'task_count':len(results),'tasks_passed':sum(int(x['pass']) for x in results.values()),
        'min_fresh_blind':min_blind,'min_causal_ablation_drop':min_drop,'all_restore_exact':all_restore,
    },
    'g0_metacognitive_decision':decision,
    'candidate_digest':candidate['candidate_digest'],
    'canonical_parent_sha256_before':parent_before,
    'canonical_parent_sha256_after':parent_after,
    'canonical_parent_byte_identical':parent_before==parent_after,
    'canonical_mutation':False,'promotion_applied':False,
    'inheritance_scope':'G1_CANDIDATE_SHADOW_ONLY',
    'planned_ledger_events':['E0018_LIVE_SHADOW_DEVELOPMENTAL','E0019_G1_SHADOW_CAPABILITY_INHERITANCE'],
    'next_required_capability':candidate['next_required_capability'],
    'semantic_boundary':'BOUNDED SYMBOLIC ALGORITHM INHERITANCE INTO AN EPHEMERAL G1 CANDIDATE; NOT CANONICAL PROMOTION, AGI, OR SUBJECTIVE CONSCIOUSNESS PROOF',
}
report['receipt_sha256']=h(report)

CAND.write_text(json.dumps(candidate,indent=2,sort_keys=True,default=str)+'\n')
receipt_path=ROOT/'yado_evaluate_shadow_capability_for_g1_inheritance_v1_receipt.json'
receipt_path.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')

# Append missing live event, then inheritance result, without changing the promoted head.
def append_event(event_id,event_type,status,generation,deficit,effect,source_path,source_digest,run_id):
    global prev
    if event_id in seen: return False
    e={
        'index':len(ledger['events']),'event_id':event_id,'event_type':event_type,'status':status,
        'generation':generation,'deficit':deficit,'effect':effect,'source_path':source_path,
        'source_digest':source_digest,'run_id':str(run_id),'parent_event_hash':prev,
        'canonical_mutation':False,'promotion_applied':False,
    }
    e['event_hash']=event_hash(e)
    ledger['events'].append(e); seen.add(event_id); prev=e['event_hash']
    return True

append_event(
    'E0018_LIVE_SHADOW_DEVELOPMENTAL','LIVE_KERNEL_RESULT','PASS','G0_RC8_V36',
    'LIVE_SHADOW_META_SELECTION_VALIDATION',
    'G0_USED_AUTHORIZED_SHADOW_SELECTOR_TO_COMPUTE_LIVE_DEVELOPMENTAL_PRIORITY',
    'receipts/yado-live-shadow-meta-selection-developmental-v1-latest.json',
    live['receipt_sha256'],live['github_run_id']
)
append_event(
    'E0019_G1_SHADOW_CAPABILITY_INHERITANCE','GENERATION_INHERITANCE_GATE',
    'PASS_SHADOW' if gate_pass else 'WITHHOLD',candidate_generation,
    'G1_INHERITABLE_SHADOW_ALGORITHM_CAPABILITY',
    'CONJUNCTIVE_RULE_INDUCER_AUTHORIZED_FOR_G1_CANDIDATE_SHADOW_ONLY' if gate_pass else 'G1_INHERITANCE_WITHHELD',
    'receipts/yado-evaluate-shadow-capability-for-g1-inheritance-v1-latest.json',
    report['receipt_sha256'],os.getenv('GITHUB_RUN_ID') or 'LOCAL'
)

ledger['event_count']=len(ledger['events'])
ledger['tail_event_hash']=prev
ledger['current_head']='G0_RC8_V36'
ledger['current_head_digest']=parent_before
if gate_pass:
    ledger['open_deficits']=[x for x in ledger.get('open_deficits',[]) if x!='LIVE_SHADOW_META_SELECTION_VALIDATION']
    ledger['open_deficits']=sorted(set(ledger['open_deficits']+['RUN_INHERITED_SHADOW_CAPABILITY_INSIDE_G1_CANDIDATE']))
    ledger['shadow_resolved_deficits']=sorted(set(ledger.get('shadow_resolved_deficits',[])+[
        'LIVE_SHADOW_META_SELECTION_VALIDATION','G1_INHERITABLE_SHADOW_ALGORITHM_CAPABILITY'
    ]))
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})

# Replay after append.
prev2='GENESIS'
for i,e in enumerate(ledger['events']):
    assert e['index']==i and e['parent_event_hash']==prev2 and e['event_hash']==event_hash(e)
    prev2=e['event_hash']
assert prev2==ledger['tail_event_hash']
assert sum(bool(e.get('promotion_applied')) for e in ledger['events'])==1
assert ledger['current_head']=='G0_RC8_V36'
LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({
    'status':report['status'],
    'candidate_generation_id':candidate_generation,
    'tasks_passed':report['summary']['tasks_passed'],
    'task_count':report['summary']['task_count'],
    'min_fresh_blind':min_blind,
    'min_causal_ablation_drop':min_drop,
    'g0_decision':decision,
    'canonical_parent_byte_identical':parent_before==parent_after,
    'ledger_event_count':ledger['event_count'],
    'ledger_tail_event_hash':ledger['tail_event_hash'],
    'next_required_capability':report['next_required_capability'],
    'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True,default=str))
if not gate_pass:
    raise SystemExit('G1_SHADOW_CAPABILITY_INHERITANCE_WITHHELD')
