from __future__ import annotations
from pathlib import Path
import hashlib,json,random,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))

from yado_raw_task_representation_learner_v1 import RawTaskRepresentationLearnerV1
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

REAL=REPO/'receipts'/'yado-g2-real-world-transfer-benchmark-v1-run-33363995201.json'
CAND=REPO/'candidates'/'g2-self-repair'/'raw-task-representation-v1.json'
HEAD=REPO/'canonical'/'yado-main-head-g2.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
OUT=ROOT/'yado_raw_task_representation_fresh_admission_v1_receipt.json'

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

real=load(REAL);cand=load(CAND);head=load(HEAD);ledger=load(LEDGER)
validate_ledger_v2(ledger)
if cand.get('state')!='AUTHORIZED_FOR_SHADOW_REPAIR':raise RuntimeError('RAW_CANDIDATE_NOT_AUTHORIZED')
if ledger.get('open_deficits')!=['G2_RAW_TASK_REPRESENTATION_FRESH_ADMISSION_V1']:
    raise RuntimeError('UNEXPECTED_FRONTIER')
head_before=fsha(HEAD)

rows=[(x['raw_text'],x['expected']) for x in real['raw_unstructured']['rows']]
by={}
for text,label in rows:by.setdefault(label,[]).append(text)
train=[]
for label in sorted(by):
    train.extend((x,label) for x in by[label][:3])
spec=RawTaskRepresentationLearnerV1.fit(train,cand['learner_family'])

# New domains not present in the original 20-task raw benchmark.
blind=[
# CONJ: operations/governance/database/security
("A database migration may proceed only when backup verification, schema validation, and rollback readiness all succeed.",CAP_CONJ),
("Approve the governance proposal only if legality, quorum, and integrity checks are all satisfied.",CAP_CONJ),
("The security change is acceptable only when signature verification, policy compliance, and recovery readiness are simultaneously true.",CAP_CONJ),
("Keep the operational rollout blocked if any of the three mandatory readiness gates fails.",CAP_CONJ),
("A data export is permitted only after consent, integrity, and destination checks each pass.",CAP_CONJ),
("The incident can be closed only when containment, evidence preservation, and recovery verification all hold.",CAP_CONJ),
("Deploy the configuration only after validation, backup, and rollback tests have all passed.",CAP_CONJ),
("A record is trusted only if provenance, checksum, and validation conditions are jointly satisfied.",CAP_CONJ),
("This decision is a three-way mandatory gate: every prerequisite must be true.",CAP_CONJ),
("Release remains on hold unless all independent safeguards succeed together.",CAP_CONJ),
("The candidate must satisfy every required boolean condition before acceptance.",CAP_CONJ),
("Proceed iff all three required checks are true; one failure is sufficient to stop.",CAP_CONJ),

# REL
("Determine whether the database user owns the table, belongs to its authorized role group, or has a verified administrative relation.",CAP_REL),
("Permission depends on relationships between the requesting service, the resource owner, and their organizational groups.",CAP_REL),
("Resolve whether two account identifiers refer to the same principal or share the required tenancy relation.",CAP_REL),
("The policy decision depends on actor-to-owner identity, membership links, and verified role.",CAP_REL),
("Check the relationship between a certificate holder, the protected service, and the issuing trust group.",CAP_REL),
("Infer authorization from entity equality and group membership rather than from three independent flags.",CAP_REL),
("Determine whether the requester and resource are connected by the required ownership or team relation.",CAP_REL),
("Evaluate access using who owns the dataset, who belongs to its group, and which role the requester holds.",CAP_REL),
("This task is about matching identities and links between entities across two records.",CAP_REL),
("Decide from relational structure among principal, owner, tenant, and role.",CAP_REL),
("The result changes when two entity fields match or when their group relation matches.",CAP_REL),
("Reason over ownership and membership edges connecting the named entities.",CAP_REL),

# BUDGET
("With a fixed incident-response allowance, choose the cheapest investigation sequence that can reach the required confidence.",CAP_BUD),
("Select which database diagnostic to run next while respecting remaining credits and query quota.",CAP_BUD),
("Plan the next security scan under a hard compute ceiling and differing expected information gains.",CAP_BUD),
("Choose a staged verification path that cannot exceed the available resource allowance.",CAP_BUD),
("Allocate finite compute among several checks with different costs, latencies, and expected evidence gains.",CAP_BUD),
("Pick the next troubleshooting stage given remaining budget, quota, and stages already attempted.",CAP_BUD),
("Determine the least costly sequence of experiments that can reach the confidence target.",CAP_BUD),
("Schedule evidence-gathering stages under a strict cost cap.",CAP_BUD),
("Choose among cheap and deep diagnostics without spending more than the remaining allowance.",CAP_BUD),
("Optimize the order of tests subject to a finite resource ceiling.",CAP_BUD),
("Select the next validation action under cost and quota constraints.",CAP_BUD),
("The search plan must respect limited credits while maximizing expected evidence.",CAP_BUD),

# RESOURCE
("Internal records are insufficient; retrieve current public documentation before deciding.",CAP_RES),
("Find an external standards reference because the local evidence cannot resolve the question.",CAP_RES),
("Consult a public source outside the current repository to verify the unresolved behavior.",CAP_RES),
("Obtain external evidence from a trustworthy public resource because local support is incomplete.",CAP_RES),
("Search current vendor documentation rather than relying only on stored assumptions.",CAP_RES),
("Retrieve an outside technical reference to resolve disagreement between local claims.",CAP_RES),
("The next step is evidence acquisition from an external public source.",CAP_RES),
("Use an outside reference because the current internal state is underdetermined.",CAP_RES),
("Look up a current public specification before committing the decision.",CAP_RES),
("Seek external documentation to fill the missing evidence.",CAP_RES),
("Acquire evidence from a public resource beyond the local knowledge base.",CAP_RES),
("The unresolved issue requires an external source, not more local inference.",CAP_RES),
]
blind_acc=sum(spec.predict(t)==y for t,y in blind)/len(blind)

# Lexical traps: include words associated with another class but make the required operation clear.
traps=[
("The owner mentions a budget in the description, but the decision is whether the requester and owner are the same principal.",CAP_REL),
("External documentation is already attached; the remaining task is to choose tests under a fixed compute limit.",CAP_BUD),
("The team discusses cost, but approval still requires integrity, rollback, and verification all to pass.",CAP_CONJ),
("Although ownership is described, local evidence is explicitly insufficient and a public source must be retrieved.",CAP_RES),
("A resource owner has a quota value, yet authorization depends only on identity and group membership relations.",CAP_REL),
("A public API is named, but no lookup is needed; choose the cheapest staged checks within the remaining allowance.",CAP_BUD),
("The word search appears in the ticket, but the actual acceptance rule requires three mandatory conditions together.",CAP_CONJ),
("The incident has a budget field, but the missing fact must be verified from an external standards document.",CAP_RES),
]
trap_acc=sum(spec.predict(t)==y for t,y in traps)/len(traps)

# Representation perturbation.
def perturb(t,i):
    wrappers=["Ticket: ","Problem: ","Incoming task: ","Operator note: "]
    noise=[" [id=8821]"," !!!","; unrelated metadata follows"," -- priority normal"]
    return wrappers[i%4]+(t.upper() if i%2==0 else t.lower())+noise[i%4]
pert=[(perturb(t,i),y) for i,(t,y) in enumerate(blind)]
pert_acc=sum(spec.predict(t)==y for t,y in pert)/len(pert)

baseline=float(real['raw_unstructured']['accuracy'])
checks={
 'fresh_cross_domain_raw_accuracy':blind_acc>=.82,
 'lexical_trap_accuracy':trap_acc>=.625,
 'perturbation_accuracy':pert_acc>=.78,
 'gain_over_original_baseline':blind_acc-baseline>=.45,
 'canonical_head_immutable':fsha(HEAD)==head_before and ledger['current_head_digest']==head['canonical_head_digest'],
}
passed=all(checks.values())
next_cap='G2_RAW_TASK_REPRESENTATION_CANONICAL_ADMISSION_GATE_V1' if passed else 'G2_RAW_TASK_REPRESENTATION_EXPRESSIVENESS_GAP_V1'

receipt={
 'schema':'yado.g2.raw_task_representation_fresh_admission.receipt.v1',
 'status':'PASS_G2_RAW_TASK_REPRESENTATION_FRESH_ADMISSION_V1' if passed else 'WITHHOLD_G2_RAW_TASK_REPRESENTATION_FRESH_ADMISSION_V1',
 'candidate_digest':cand['candidate_digest'],'learner_family':cand['learner_family'],
 'metrics':{'cross_domain_raw_accuracy':blind_acc,'lexical_trap_accuracy':trap_acc,'perturbation_accuracy':pert_acc,
            'original_baseline_raw_accuracy':baseline},
 'blind_task_count':len(blind),'trap_task_count':len(traps),'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'INDEPENDENT FRESH ADMISSION OF A BOUNDED RAW-TEXT CAPABILITY ROUTER ACROSS NEW DOMAINS. PASS DOES NOT ESTABLISH GENERAL LANGUAGE UNDERSTANDING OR ENTITY-LEVEL SEMANTIC GROUNDING.'
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_RAW_REPRESENTATION_FRESH_ADMISSION",
   'event_type':'KERNEL_NATIVE_SELF_REPAIR_ADMISSION_GATE','status':'PASS_SHADOW' if passed else 'WITHHOLD',
   'generation':ledger['current_head'],'deficit':'G2_RAW_TASK_REPRESENTATION_FRESH_ADMISSION_V1',
   'effect':'RAW_REPRESENTATION_FRESH_ADMISSION_PASS' if passed else 'RAW_REPRESENTATION_EXPRESSIVENESS_GAP_REMAINS',
   'source_path':f'receipts/yado-raw-task-representation-fresh-admission-v1-run-{run_id}.json',
   'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
   'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({'status':receipt['status'],'metrics':receipt['metrics'],'checks':checks,
 'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
