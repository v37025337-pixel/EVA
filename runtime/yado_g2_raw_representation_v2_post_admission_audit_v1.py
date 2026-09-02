from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,subprocess,sys

ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]
from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_raw_task_representation_runtime_v1 import RawTaskRepresentationRuntimeV1
from yado_bounded_capability_router_v1 import BoundedCapabilityRouterLearnerV1
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json';CORE=REPO/'canonical/yado-unified-core-v1.json';LEDGER=REPO/'architecture/evolution-ledger.json'
PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json';V2ART=REPO/'canonical/yado-raw-task-representation-v2.json'
V1ART=REPO/'canonical/yado-raw-task-representation-v1.json';BASE=REPO/'receipts/yado-g2-real-world-transfer-benchmark-v1-run-33363995201.json'
OUT=ROOT/'yado_g2_raw_representation_v2_post_admission_audit_v1_receipt.json';GUARD=ROOT/'yado_canonical_invariant_guard_v1.py'
UNIFIED=ROOT/'yado_unified_core_v1.py';V2SRC=ROOT/'yado_raw_task_representation_candidate_v2.py'
V1='ALG-G2-RAW-TASK-REPRESENTATION-V1';V2='ALG-G2-RAW-TASK-REPRESENTATION-V2'
CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1';CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1';CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1';CAP_RES='RESOURCE-PORTFOLIO-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):
    x=copy.deepcopy(o);x.pop(field,None);return h(x)

head,core,ledger,prov,v2,v1,base=map(load,[HEAD,CORE,LEDGER,PROV,V2ART,V1ART,BASE]);validate_ledger_v2(ledger)
front='KERNEL_G2_RAW_REPRESENTATION_V2_POST_ADMISSION_AUDIT_V1'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER')
if head.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')

plane=next((p for p in core.get('planes',[]) if p.get('plane_id')=='REPRESENTATION_AND_GROUNDING'),{})
rim=core.get('runtime_integrity_manifest',{})
sup=next((x for x in core.get('superseded_components',[]) if x.get('component_id')==V1),None)

# Restarted unified core must consume V2 through the real entry point.
ucore=UnifiedYADOCoreV1(REPO)
rows=[]
for i,label in enumerate([CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES]*140):
    rows.append({'input':{'budget_limited':label==CAP_BUD,'quota_limited':False,'external_evidence_needed':label==CAP_RES,'relation_needed':label==CAP_REL,'disjunction_needed':False,'noise':i},'expected':label})
router=BoundedCapabilityRouterLearnerV1.synthesize(rows,rows,CAP_CONJ,min_support=8)

canary=[
("A cybersecurity rollout is allowed only if signature, recovery, and policy checks all succeed.",CAP_CONJ),
("An education dataset is publishable only when consent, integrity, and validation are jointly true.",CAP_CONJ),
("Do not plan stages; every mandatory readiness gate must pass before the bank change is committed.",CAP_CONJ),
("External docs are present, but the ocean-sensor deployment still requires all independent safety prerequisites.",CAP_CONJ),
("One failed required invariant is sufficient to keep the operation blocked.",CAP_CONJ),
("This is an all-of acceptance rule rather than an ownership decision.",CAP_CONJ),
("Proceed iff all required checks are true, regardless of remaining credits.",CAP_CONJ),
("The release depends on simultaneous satisfaction of provenance, validation, and rollback readiness.",CAP_CONJ),

("Determine whether the security principal owns the key or belongs to its authorized rotation group.",CAP_REL),
("Student-record access depends on requester-owner identity and approved-role membership.",CAP_REL),
("Budget is not relevant; infer permission from identity equality and organizational links.",CAP_REL),
("All readiness gates pass, but bank access still depends on owner and group relations.",CAP_REL),
("Resolve whether two marine sensors belong to the same authorized fleet group.",CAP_REL),
("The task concerns relational structure among principal, owner, tenant, and role.",CAP_REL),
("A public manual exists, yet authorization follows from entity links.",CAP_REL),
("Determine access from ownership and membership edges rather than independent booleans.",CAP_REL),

("Choose the next penetration test under a finite security-compute allowance.",CAP_BUD),
("Allocate limited lab credits among educational-data validation stages with different evidence gains.",CAP_BUD),
("Ownership is known; select an affordable diagnostic sequence for the bank service.",CAP_BUD),
("Plan ocean-sensor investigations without exceeding the remaining observation budget.",CAP_BUD),
("External references are already available; optimize the next test under cost and quota.",CAP_BUD),
("Pick the least costly sequence capable of reaching the target confidence.",CAP_BUD),
("Schedule deeper checks according to expected gain and remaining resources.",CAP_BUD),
("This is resource-constrained staged search, not an all-gates decision.",CAP_BUD),

("Local security logs lack the decisive protocol fact; retrieve current public documentation.",CAP_RES),
("The education repository does not contain the applicable standard, so consult an authoritative external source.",CAP_RES),
("All bank ownership relations are known; the missing rule must be obtained from outside documentation.",CAP_RES),
("Do not schedule another sensor experiment; fetch the absent specification from a public technical reference.",CAP_RES),
("Remaining budget cannot resolve a fact missing from local state; retrieve it externally.",CAP_RES),
("Use a trustworthy outside source because internal evidence is insufficient.",CAP_RES),
("The next action is public evidence acquisition rather than local inference.",CAP_RES),
("Obtain the unresolved requirement from current external documentation.",CAP_RES),
]
canary_rows=[]
for text,expected in canary:
    out=ucore.route_raw_task(text,router);canary_rows.append({'text':text,'expected':expected,'got':out['selected_capability'],'correct':out['selected_capability']==expected})
canary_acc=sum(x['correct'] for x in canary_rows)/len(canary_rows)

# Rollback substrate remains constructible and historically usable.
rollback=RawTaskRepresentationRuntimeV1(v1)
base_rows=[(r['raw_text'],r['expected']) for r in base['raw_unstructured']['rows']]
rollback_acc=sum(rollback.predict_capability(x)==y for x,y in base_rows)/len(base_rows)

checks={
 'v2_component_digest_exact':v2.get('component_digest')==cdig(v2,'component_digest'),
 'v2_model_digest_exact':v2.get('model_digest')==h(v2.get('model')),
 'v2_canonical_active':v2.get('canonical_active') is True,
 'head_active_v2_only':V2 in head.get('active_capabilities',[]) and V1 not in head.get('active_capabilities',[]),
 'plane_active_v2_only':V2 in plane.get('active_components',[]) and V1 not in plane.get('active_components',[]),
 'core_raw_binding_v2':core.get('raw_task_representation',{}).get('component_id')==V2,
 'runtime_source_hash_bound':rim.get('sources',{}).get('runtime/yado_raw_task_representation_candidate_v2.py')==fsha(V2SRC),
 'unified_runtime_hash_bound':core.get('runtime_sha256')==head.get('unified_core',{}).get('runtime_sha256')==fsha(UNIFIED),
 'runtime_manifest_digest_bound':rim.get('manifest_digest')==h(rim.get('sources',{}))==head.get('unified_core',{}).get('runtime_integrity_manifest_digest'),
 'v1_superseded_with_history':bool(sup and sup.get('superseded_by')==V2 and sup.get('historical_evidence_retained') is True),
 'restart_unified_canary':canary_acc>=.90,
 'rollback_v1_constructible':rollback_acc>=.80,
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
passed=all(checks.values())
next_cap='KERNEL_G2_RAW_REPRESENTATION_V2_CANONICAL_BURNIN_V1' if passed else 'KERNEL_G2_RAW_REPRESENTATION_V2_POST_ADMISSION_REPAIR_V1'

prev=head['canonical_head_digest']
prov['current_g2_binding'].update({'current_execution_label':'G2_RAW_REPRESENTATION_V2_CANONICAL_BURNIN_PENDING' if passed else 'G2_RAW_REPRESENTATION_V2_POST_ADMISSION_REPAIR_PENDING',
 'frontier':next_cap,'frontier_native_method':'UnifiedYADOCoreV1.route_raw_task','frontier_native_owner':'UnifiedYADOCoreV1',
 'raw_representation_active_component':V2})
prov['registry_digest']=cdig(prov,'registry_digest');write(PROV,prov)
core['algorithm_provenance_registry_digest']=prov['registry_digest'];core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits'
core['raw_representation_v2_post_admission_audit_v1']={'status':'PASS' if passed else 'WITHHOLD','canary_accuracy':canary_acc,'rollback_v1_accuracy':rollback_acc,'checks':checks}
core['core_digest']=cdig(core,'core_digest');write(CORE,core)
head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest'];head['algorithm_provenance_registry']['current_execution_label']=prov['current_g2_binding']['current_execution_label']
head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest'];head['unified_core']['core_digest']=core['core_digest']
head['raw_representation_v2_post_admission_audit_v1']={'status':'PASS' if passed else 'WITHHOLD','canary_accuracy':canary_acc,'rollback_v1_accuracy':rollback_acc}
head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits';head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)
ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap]

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.raw_representation_v2_post_admission_audit.receipt.v1',
 'status':'PASS_G2_RAW_REPRESENTATION_V2_POST_ADMISSION_AUDIT_V1' if passed else 'WITHHOLD_G2_RAW_REPRESENTATION_V2_POST_ADMISSION_AUDIT_V1',
 'canary_accuracy':canary_acc,'rollback_v1_accuracy':rollback_acc,'canary_rows':canary_rows,'checks':checks,
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest'],
 'canonical_mutation':True,'canonical_mechanism_mutation':False,'architecture_mutation':False,'g3_genesis_performed':False,'next_required_capability':next_cap,
 'semantic_boundary':'POST-ADMISSION RESTART AUDIT OF CANONICAL RAW REPRESENTATION V2 AND ITS V1 ROLLBACK SUBSTRATE. NOT GENERAL LANGUAGE UNDERSTANDING.'}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_RAW_REPRESENTATION_V2_POST_ADMISSION_AUDIT_V1",
 'event_type':'G2_RAW_REPRESENTATION_POST_ADMISSION_AUDIT','status':'PASS' if passed else 'WITHHOLD','generation':ledger['current_head'],'deficit':front,
 'effect':f"AUDIT={'PASS' if passed else 'WITHHOLD'}; CANARY={canary_acc:.6f}; ROLLBACK_V1={rollback_acc:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-g2-raw-representation-v2-post-admission-audit-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':True,'canonical_mechanism_mutation':False,'architecture_mutation':False,'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);write(LEDGER,ledger)
ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_RAW_V2_AUDIT_CONTEXT_INCONSISTENT')
post=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=60)
if post.returncode!=0:raise RuntimeError('POST_RAW_V2_AUDIT_GUARD_FAILED:'+post.stdout[-5000:]+post.stderr[-1000:])
print(json.dumps({'status':receipt['status'],'canary_accuracy':canary_acc,'rollback_v1_accuracy':rollback_acc,'checks':checks,'next_required_capability':next_cap},indent=2,sort_keys=True))
