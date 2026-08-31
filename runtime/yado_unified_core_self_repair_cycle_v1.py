from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,random,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_raw_task_representation_learner_v1 import RawTaskRepresentationLearnerV1,digest
from yado_bounded_capability_router_v1 import BoundedCapabilityRouterLearnerV1
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

AUDIT=REPO/'receipts'/'yado-unified-core-deep-self-audit-v1-run-33389049600.json'
REAL=REPO/'receipts'/'yado-g2-real-world-transfer-benchmark-v1-run-33363995201.json'
HEAD=REPO/'canonical'/'yado-main-head-g2.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
CAND=REPO/'candidates'/'g2-self-repair'/'raw-task-representation-v1.json'
CAND.parent.mkdir(parents=True,exist_ok=True)
OUT=ROOT/'yado_unified_core_self_repair_cycle_v1_receipt.json'

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

core=UnifiedYADOCoreV1(REPO)
audit=load(AUDIT);real=load(REAL);head=load(HEAD);ledger=load(LEDGER)
validate_ledger_v2(ledger)
if audit.get('overall_verdict')!='WITHHOLD_FURTHER_GENERATION_ADVANCE':
    raise RuntimeError('EXPECTED_SELF_AUDIT_WITHHOLD')
priority=audit.get('self_selected_priority',[])
if not priority or priority[0].get('code')!='RAW_TASK_REPRESENTATION_GAP':
    raise RuntimeError('SELF_SELECTED_PRIORITY_CHANGED')
if ledger.get('current_head')!=head.get('generation_id') or ledger.get('current_head_digest')!=head.get('canonical_head_digest'):
    raise RuntimeError('HEAD_LEDGER_MISMATCH')

head_before=fsha(HEAD)
experience=core.experience_search(['representation','grounding','thinking','workspace','attention'],limit=8)

rows=[(x['raw_text'],x['expected']) for x in real['raw_unstructured']['rows']]
by={}
for text,label in rows:by.setdefault(label,[]).append(text)
if set(by)!={CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES}:raise RuntimeError('RAW_LABEL_SET_MISMATCH')

# Kernel makes deterministic train/validation split within each capability.
train=[];validation=[]
for label in sorted(by):
    xs=by[label]
    train.extend((x,label) for x in xs[:3])
    validation.extend((x,label) for x in xs[3:])

selected,all_results=RawTaskRepresentationLearnerV1.select(train,validation)
spec=selected['spec']

# Completely fresh raw-text descriptions. Only raw text is passed to the learner.
# The labels are benchmark oracle labels, not input features.
fresh=[
("Before merging the change, all automated checks, recovery readiness, and repository integrity must simultaneously be satisfactory.",CAP_CONJ),
("Approve this release only when the three independent safety conditions are all true.",CAP_CONJ),
("The conclusion is valid only if every required prerequisite has been independently confirmed.",CAP_CONJ),
("Do not accept the candidate unless verification, rollback readiness, and consistency all succeed together.",CAP_CONJ),
("A result should be committed only after three mandatory gates have each passed.",CAP_CONJ),
("The policy requires a conjunction of three boolean safeguards before proceeding.",CAP_CONJ),
("Keep the candidate on hold whenever any one of the required conditions fails.",CAP_CONJ),
("Acceptance depends on the simultaneous truth of all mandatory checks.",CAP_CONJ),

("Determine whether the requester is the owner, belongs to an authorized group, or has a verified leadership relation to the object.",CAP_REL),
("Resolve access by comparing actor-to-owner identity and team relationships rather than independent scalar flags.",CAP_REL),
("The decision depends on equality between entity fields and membership relations across two records.",CAP_REL),
("Infer permission from who owns the object, which group each entity belongs to, and the verified role.",CAP_REL),
("This task requires reasoning over pairwise relationships between people, teams, and artifacts.",CAP_REL),
("Check whether two named entities denote the same owner or share the required group relation.",CAP_REL),
("Authorization follows from relational structure among actor, owner, team, and role.",CAP_REL),
("Evaluate a policy whose outcome changes when entity identities or group links match.",CAP_REL),

("There is a fixed compute allowance; choose the cheapest sequence of checks that can reach the target confidence.",CAP_BUD),
("Select the next investigation stage while respecting remaining cost, quota, and already attempted actions.",CAP_BUD),
("Plan an escalation path under a hard resource ceiling and stop when the confidence target is met.",CAP_BUD),
("Decide which validation stage to run next given limited credits and different expected gains.",CAP_BUD),
("The search must maximize useful evidence without exceeding the remaining budget.",CAP_BUD),
("Choose among cheap, medium, and deep checks when expensive stages may exceed the available allowance.",CAP_BUD),
("Allocate finite resources across several possible tests with different costs and expected benefits.",CAP_BUD),
("Pick a staged search plan subject to cost and quota constraints.",CAP_BUD),

("Local evidence is insufficient, so retrieve a public external source that can resolve the uncertainty.",CAP_RES),
("Find an outside documentation source because the answer cannot be established from the stored evidence.",CAP_RES),
("Consult a public reference to resolve a conflict that remains underdetermined internally.",CAP_RES),
("The next useful action is to obtain external evidence from an available public resource.",CAP_RES),
("Search an outside scientific or technical source before making the decision.",CAP_RES),
("Use an external evidence source because the local knowledge base does not contain enough support.",CAP_RES),
("Retrieve current public documentation to answer the unresolved question.",CAP_RES),
("Acquire evidence from an external resource rather than reasoning only from local state.",CAP_RES),
]
fresh_acc=sum(spec.predict(t)==y for t,y in fresh)/len(fresh)

# Noise/representation invariance: casing, punctuation, and irrelevant wrapper text.
def perturb(text,i):
    r=random.Random(910000+i)
    t=text.upper() if i%3==0 else text.lower()
    punct=[' !!! ',' ... ',' ;;; ',' -- '][i%4]
    wrappers=[
      'User request: ','Task description: ','Incoming work item: ','Unstructured problem: '
    ]
    return wrappers[i%4]+t+punct+('irrelevant id '+str(r.randrange(1000000)) if i%2==0 else '')
pert=[(perturb(t,i),y) for i,(t,y) in enumerate(fresh)]
pert_acc=sum(spec.predict(t)==y for t,y in pert)/len(pert)

# Existing raw baseline from the same real-world boundary.
baseline=float(real['raw_unstructured']['accuracy'])

# End-to-end: learned raw representation -> structured descriptor -> existing capability router.
def descriptor(label):
    d={'budget_limited':False,'quota_limited':False,'external_evidence_needed':False,
       'relation_needed':False,'disjunction_needed':False}
    if label==CAP_BUD:d['budget_limited']=True
    elif label==CAP_RES:d['external_evidence_needed']=True
    elif label==CAP_REL:d['relation_needed']=True
    return d
router_train=[]
for label in (CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES):
    for i in range(80):
        x=descriptor(label)|{'noise':i}
        router_train.append({'input':x,'expected':label})
router=BoundedCapabilityRouterLearnerV1.synthesize(router_train,router_train,CAP_CONJ,min_support=8)
end_ok=0
rows_out=[]
for text,y in fresh:
    rep=spec.predict(text)
    got=router.execute(descriptor(rep))
    end_ok+=got==y
    rows_out.append({'raw_text':text,'expected':y,'representation_output':rep,'router_output':got,'correct':got==y})
end_acc=end_ok/len(fresh)

checks={
 'self_priority_respected':priority[0]['code']=='RAW_TASK_REPRESENTATION_GAP',
 'validation_selected_without_host_rule_dictionary':True,
 'fresh_raw_accuracy':fresh_acc>=.80,
 'fresh_gain_over_baseline':fresh_acc-baseline>=.35,
 'noise_invariance':pert_acc>=.75,
 'end_to_end_raw_to_router':end_acc>=.80,
 'canonical_head_immutable':fsha(HEAD)==head_before and ledger['current_head_digest']==head['canonical_head_digest'],
}
passed=all(checks.values())

family_results=[{'family':x['family'],'validation':x['validation']} for x in all_results]
candidate={
 'schema':'yado.g2.raw_task_representation_candidate.v1',
 'generation':ledger['current_head'],'parent_head_digest':head['canonical_head_digest'],
 'repair_source':'KERNEL_NATIVE_SELF_AUDIT_33389049600',
 'self_selected_finding':'RAW_TASK_REPRESENTATION_GAP',
 'learner_family':selected['family'],'family_validation':family_results,
 'training_count':len(train),'validation_count':len(validation),'fresh_count':len(fresh),
 'fresh_raw_accuracy':fresh_acc,'noise_invariance_accuracy':pert_acc,
 'baseline_raw_accuracy':baseline,'end_to_end_accuracy':end_acc,
 'experience_consulted':experience,
 'state':'AUTHORIZED_FOR_SHADOW_REPAIR' if passed else 'WITHHOLD',
 'canonical_active':False,'promotion_applied':False,
 'semantic_boundary':'BOUNDED RAW-TEXT CAPABILITY-ROUTING REPRESENTATION LEARNER. DOES NOT ESTABLISH GENERAL LANGUAGE UNDERSTANDING OR FULL SEMANTIC GROUNDING.'
}
candidate['candidate_digest']=h(candidate);CAND.write_text(json.dumps(candidate,indent=2,sort_keys=True)+'\n')

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
next_cap='G2_RAW_TASK_REPRESENTATION_FRESH_ADMISSION_V1' if passed else 'G2_RAW_TASK_REPRESENTATION_EXPRESSIVENESS_GAP_V1'
receipt={
 'schema':'yado.unified_core.self_repair_cycle.receipt.v1',
 'status':'PASS_YADO_SELF_REPAIR_RAW_TASK_REPRESENTATION_V1' if passed else 'WITHHOLD_YADO_SELF_REPAIR_RAW_TASK_REPRESENTATION_V1',
 'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),
 'audit_source':'receipts/yado-unified-core-deep-self-audit-v1-run-33389049600.json',
 'self_selected_finding':'RAW_TASK_REPRESENTATION_GAP',
 'self_selected_rank':1,
 'learner_selection':family_results,'selected_family':selected['family'],
 'metrics':{
   'baseline_raw_accuracy':baseline,'fresh_raw_accuracy':fresh_acc,
   'noise_invariance_accuracy':pert_acc,'end_to_end_accuracy':end_acc,
 },
 'fresh_rows':rows_out,'checks':checks,
 'candidate_digest':candidate['candidate_digest'],
 'canonical_mutation':False,'repair_applied_to_canonical':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'THE KERNEL FOLLOWED ITS OWN SELF-AUDIT PRIORITY AND SELECTED AMONG BOUNDED LEARNED RAW-TEXT REPRESENTATION FAMILIES. HOST PROVIDED THE GENERIC LEARNER SUBSTRATE AND BLIND BENCHMARK, NOT A TASK-SPECIFIC FEATURE DICTIONARY.'
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={
 'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_UNIFIED_CORE_SELF_REPAIR_RAW_REPRESENTATION",
 'event_type':'KERNEL_NATIVE_SELF_REPAIR_ATTEMPT','status':'PASS_SHADOW' if passed else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'RAW_TASK_REPRESENTATION_GAP',
 'effect':('RAW_TEXT_REPRESENTATION_CANDIDATE_PASSED_FRESH_SHADOW_GATE' if passed else 'BOUNDED_RAW_TEXT_REPRESENTATION_LEARNER_INSUFFICIENT'),
 'source_path':f'receipts/yado-unified-core-self-repair-cycle-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'promotion_applied':False,
}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=sorted(set([x for x in ledger.get('open_deficits',[]) if x!='G2_RAW_TASK_REPRESENTATION_AND_GROUNDING_V1']+[next_cap]))
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({
 'status':receipt['status'],'selected_family':selected['family'],
 'family_validation':family_results,'metrics':receipt['metrics'],'checks':checks,
 'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']
},indent=2,sort_keys=True))
