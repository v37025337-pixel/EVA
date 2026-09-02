from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,subprocess,sys

ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_raw_task_representation_candidate_v2 import RawTaskRepresentationRuntimeV2
from yado_raw_task_representation_candidate_v3 import RawTaskRepresentationRuntimeV3
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json';CORE=REPO/'canonical/yado-unified-core-v1.json';LEDGER=REPO/'architecture/evolution-ledger.json';PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
V2ART=REPO/'canonical/yado-raw-task-representation-v2.json';CAND=REPO/'candidates/kernel-self-generated/raw-task-representation-v3-structural.json'
PREV=REPO/'resources/yado-raw-task-representation-v3-structural-fresh-holdout-v1.json';BASE=REPO/'receipts/yado-g2-real-world-transfer-benchmark-v1-run-33363995201.json'
CANON=REPO/'canonical/yado-raw-task-representation-v3.json';OUT=ROOT/'yado_kernel_g2_raw_representation_v3_canonical_admission_v1_receipt.json'
GUARD=ROOT/'yado_canonical_invariant_guard_v1.py';UNIFIED=ROOT/'yado_unified_core_v1.py';V3SRC=ROOT/'yado_raw_task_representation_candidate_v3.py'

V2='ALG-G2-RAW-TASK-REPRESENTATION-V2';V3='ALG-G2-RAW-TASK-REPRESENTATION-V3'
C1='ALG-CONJUNCTIVE-RULE-INDUCER-V1';CR='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1';CB='ALG-BUDGETED-STAGE-POLICY-V1';CE='RESOURCE-PORTFOLIO-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):x=copy.deepcopy(o);x.pop(field,None);return h(x)
def acc(rows,pred):return sum(pred(x)==y for x,y in rows)/max(1,len(rows))
def log(stage,**kw):print(json.dumps({'stage':stage,**kw},sort_keys=True,default=str),flush=True)

head,core,ledger,prov,v2,cand,prev,base=map(load,[HEAD,CORE,LEDGER,PROV,V2ART,CAND,PREV,BASE]);validate_ledger_v2(ledger)
front='KERNEL_G2_RAW_REPRESENTATION_V3_CANONICAL_ADMISSION_V1'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if cand.get('state')!='SHADOW_STRUCTURAL_V3_SUPPORTED':raise RuntimeError('V3_NOT_SHADOW_SUPPORTED')
if cand.get('candidate_digest')!='42e8762202434018f949ee0fd48af72db94a56f49dfc7b14d4198ddb77591894':raise RuntimeError('V3_CANDIDATE_DRIFT')
if cand.get('selected_mode')!='PIVOT_CLAUSE':raise RuntimeError('V3_MODE_DRIFT')
if head.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')
if V2 not in head.get('active_capabilities',[]):raise RuntimeError('V2_NOT_ACTIVE_PARENT')

parent=RawTaskRepresentationRuntimeV2(v2);child=RawTaskRepresentationRuntimeV3(cand)

fresh=[
# CONJ -- deliberately many without the discovered pivot token.
("A railway control update is authorized only when signal validation, operator authentication, and rollback readiness all succeed together.",C1),
("The loan model may be deployed iff fairness review, data integrity, and recovery verification are simultaneously true.",C1),
("Do not choose another diagnostic; decide whether every mandatory bridge-inspection prerequisite has passed.",C1),
("Ownership details are included, yet approval depends only on the complete set of independent readiness gates.",C1),
("No outside fact is missing; the decision is whether all required launch conditions hold at once.",C1),
("A warehouse robot can start only after calibration, identity, and fail-safe checks each pass.",C1),
("The specification has already been read; commit when every mandatory invariant is true.",C1),
("This is a conjunction of required safeguards, not an authorization-link problem.",C1),
("One failed mandatory check blocks the surgical procedure even with remaining compute.",C1),
("Proceed exactly when all independent acceptance predicates evaluate true.",C1),
("The candidate is withheld unless each prerequisite is satisfied.",C1),
("Search and ownership terms are incidental; evaluate all required conditions together.",C1),

# REL
("Determine whether the railway service account owns the signal asset or belongs to its authorized operations group.",CR),
("Loan-record access depends on requester-owner identity and approved institution-role membership.",CR),
("Ignore the compute allowance; decide whether the two principals are identical or linked by the required organization relation.",CR),
("Every scalar safety gate passes, yet bridge-control permission depends on ownership and team edges.",CR),
("The manual is known; infer authorization from account, tenant, owner, and role relationships.",CR),
("Resolve whether the surgeon belongs to the patient's authorized care cohort.",CR),
("The outcome changes with entity equality and group membership rather than resource credits.",CR),
("This task concerns relational structure among actor, owner, organization, and verified role.",CR),
("No public lookup is needed; compare ownership and membership links.",CR),
("Infer whether requester and protected resource share the required owner or cohort relation.",CR),
("A quota field is present but does not determine permission.",CR),
("Determine access from principal identity and authorization edges, not independent gates.",CR),

# BUDGET
("Choose the next railway diagnostic under a finite maintenance budget and differing expected evidence gains.",CB),
("Schedule loan-model tests to reach target confidence without exceeding remaining compute.",CB),
("Ownership is already resolved; select an affordable sequence of bridge inspections under quota.",CB),
("Several robotic diagnostics are valid but costly; allocate the finite verification allowance among them.",CB),
("Do not merely ask whether all gates pass; choose the next experiment from cost and information gain.",CB),
("External documents are available, but deeper investigations must fit the remaining resources.",CB),
("Find the least expensive staged verification path capable of reaching the confidence target.",CB),
("Plan escalation after previous checks while respecting spent quota and remaining budget.",CB),
("Identity relationships are irrelevant; optimize the order of diagnostic stages.",CB),
("Allocate limited observation time among measurements with different expected gains.",CB),
("Select the next validation stage under a hard resource ceiling.",CB),
("The objective is resource-constrained evidence gathering, not outside fact retrieval.",CB),

# RESOURCE
("Railway logs do not contain the decisive braking tolerance, so retrieve a current authoritative engineering standard.",CE),
("Stored loan records cannot establish the applicable regulation; consult a current public legal source.",CE),
("All bridge ownership relations are known, but the missing load requirement must come from external documentation.",CE),
("Do not run another robot test; obtain the absent specification from a public technical reference.",CE),
("Remaining compute cannot reveal a fact absent from the system; retrieve the vendor documentation.",CE),
("Find an outside surgical standard because the repository lacks the required fact.",CE),
("The next action is external evidence acquisition rather than additional internal inference.",CE),
("Consult an authoritative reference beyond stored memory to resolve the uncertainty.",CE),
("Internal validation succeeded, but the unknown requirement must be verified from public documentation.",CE),
("Use a trustworthy external source because available evidence is insufficient.",CE),
("Do not choose another internal stage; fetch the missing rule from an eligible outside source.",CE),
("The unresolved information is external to the system, so retrieve it before deciding.",CE),
]
traps=[
("External standards and owner fields are mentioned, but release still requires every mandatory readiness condition.",C1),
("A budget number is present, yet access depends on account-owner identity and membership relations.",CR),
("The stage is named outside-review, but choose an affordable diagnostic sequence under the finite allowance.",CB),
("Owner and quota information are complete; the missing requirement still needs an authoritative external specification.",CE),
("Team relationships are known, but approval is simply whether all independent safeguards pass.",C1),
("Documentation is attached; permission nevertheless follows from entity links.",CR),
("All prerequisites are satisfied; now optimize which test to run within remaining credits.",CB),
("Budget remains, but the missing standard can only be obtained from an outside reference.",CE),
("Ignore the word search: each required condition must be true.",C1),
("Do not evaluate an all-of gate; infer access from owner and group relationships.",CR),
("External evidence is already available; allocate the finite budget across diagnostic stages.",CB),
("Cost and ownership metadata are distractions; obtain the absent fact from a public authority.",CE),
("The word local does not decide this case; all required validation gates must pass.",C1),
("Local ownership is known, but authorization depends on the requester-owner relationship.",CR),
("Local evidence is sufficient; the remaining task is choosing an affordable test sequence.",CB),
("Local files are insufficient, so retrieve the missing requirement from a current external source.",CE),
]

pf=acc(fresh,parent.predict_capability);cf=acc(fresh,child.predict_capability)
pt=acc(traps,parent.predict_capability);ct=acc(traps,child.predict_capability)
def perturb(x,i):return ("Assessment: ","Incoming case: ","Control note: ","Request packet: ")[i%4]+(x.upper() if i%2==0 else x.lower())+(" [job=711]","; unrelated metadata"," -- routine"," [trace=v6]")[i%4]
pert=[(perturb(x,i),y) for i,(x,y) in enumerate(fresh)];cp=acc(pert,child.predict_capability)
prev_rows=[(r['text'],r['expected']) for r in prev['rows']];prev_repro=acc(prev_rows,child.predict_capability)
base_rows=[(r['raw_text'],r['expected']) for r in base['raw_unstructured']['rows']];base_reg=acc(base_rows,child.predict_capability)

skills=[
 {'skill_id':'KEEP_RAW_V2','artifact_digest':v2['component_digest'],'structural_valid':True,'semantic_consistency':1.0,
  'fit_baseline':float(prev['metrics']['parent_fresh_accuracy']),'fit_candidate':float(prev['metrics']['parent_fresh_accuracy']),
  'heldout_baseline':pf,'heldout_candidate':pf,'regression_pass':True,'state_integrity':True,'rollback_available':True},
 {'skill_id':'ADMIT_STRUCTURAL_RAW_V3','artifact_digest':cand['candidate_digest'],'structural_valid':True,'semantic_consistency':1.0,
  'fit_baseline':float(prev['metrics']['parent_fresh_accuracy']),'fit_candidate':float(prev['metrics']['fresh_accuracy']),
  'heldout_baseline':pf,'heldout_candidate':cf,
  'regression_pass':prev_repro>=.97 and base_reg>=.95,'state_integrity':True,'rollback_available':True}
]
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_raw_v3_admission.sqlite'))
try:selection=k.select_evolution_skills(skills,max_skills=1,min_semantic_consistency=.90,min_fit_gain=.05,max_heldout_drop=0,min_heldout_gain=.04)
finally:k.close()
selected=(selection.get('selected_skill_ids') or [None])[0]
metrics={'parent_fresh_v6':pf,'v3_fresh_v6':cf,'parent_trap_v6':pt,'v3_trap_v6':ct,'v3_perturbation_v6':cp,'previous_structural_fresh_reproduction':prev_repro,'base_regression_accuracy':base_reg}
checks={
 'candidate_fixed_before_fresh_v6':cand['candidate_digest']=='42e8762202434018f949ee0fd48af72db94a56f49dfc7b14d4198ddb77591894',
 'kernel_selects_v3':selected=='ADMIT_STRUCTURAL_RAW_V3',
 'fresh_v6_accuracy':cf>=.94,'fresh_v6_gain':cf-pf>=.04,'fresh_v6_traps':ct>=.875,'fresh_v6_perturbation':cp>=.90,
 'previous_structural_fresh_reproduction':prev_repro>=.97,'base_regression':base_reg>=.95,
 'v2_rollback_available':v2.get('canonical_active') is True,'architecture_family_unchanged':head.get('architecture_family')=='TYPED_RECURRENT_CAPABILITY_GRAPH',
 'g3_not_started':head.get('g3_genesis_performed') is False}
admit=all(checks.values());next_cap='KERNEL_G2_RAW_REPRESENTATION_V3_POST_ADMISSION_AUDIT_V1' if admit else 'KERNEL_G2_RAW_REPRESENTATION_V2_POST_ADMISSION_REPAIR_V3'

canonical_art=None
if admit:
 canonical_art={'schema':'yado.g2.raw_task_representation.canonical.v3','canonical_active':True,'component_id':V3,'supersedes':V2,
  'historical_parent_artifact':'canonical/yado-raw-task-representation-v2.json','family':'STRUCTURAL_RAW_TEXT_TO_CAPABILITY_ROUTING_DESCRIPTOR_V3',
  'learner_family':cand['model']['family'],'selected_mode':cand['selected_mode'],'selected_pivot':cand['selected_pivot'],
  'pivot_discovery':'DATA_DISCOVERED_FROM_SPENT_TRAINING_TEXT','model':cand['model'],'model_digest':h(cand['model']),
  'source_candidate_digest':cand['candidate_digest'],'candidate_runtime_source':'runtime/yado_raw_task_representation_candidate_v3.py',
  'candidate_runtime_sha256':fsha(V3SRC),'admission_metrics':metrics,'fresh_structural_dataset_digest':cand['fresh_dataset_digest'],
  'claim_boundary':'BOUNDED STRUCTURAL RAW-TEXT CAPABILITY ROUTING V3; NOT GENERAL LANGUAGE UNDERSTANDING OR ENTITY-LEVEL SEMANTIC GROUNDING.'}
 canonical_art['component_digest']=cdig(canonical_art,'component_digest');write(CANON,canonical_art)

prev_head=head['canonical_head_digest']
if admit:
 src=UNIFIED.read_text(encoding='utf-8')
 old_import='from yado_raw_task_representation_candidate_v2 import RawTaskRepresentationRuntimeV2'
 new_import='from yado_raw_task_representation_candidate_v3 import RawTaskRepresentationRuntimeV3'
 old_init="self.raw_representation=RawTaskRepresentationRuntimeV2(self._load('canonical/yado-raw-task-representation-v2.json'))"
 new_init="self.raw_representation=RawTaskRepresentationRuntimeV3(self._load('canonical/yado-raw-task-representation-v3.json'))"
 if old_import not in src or old_init not in src:raise RuntimeError('UNIFIED_V2_BINDING_ANCHOR_MISSING')
 src=src.replace(old_import,new_import).replace(old_init,new_init);UNIFIED.write_text(src,encoding='utf-8');unified_sha=fsha(UNIFIED)
 plane=next((p for p in core.get('planes',[]) if p.get('plane_id')=='REPRESENTATION_AND_GROUNDING'),None)
 if plane is None:raise RuntimeError('REPRESENTATION_PLANE_MISSING')
 plane['active_components']=sorted(set(V3 if x==V2 else x for x in plane.get('active_components',[])));plane['frontier']='POST_COMPOSITE_STRUCTURAL_RAW_REPRESENTATION_V3'
 core['active_runtime_sources']=sorted([x for x in core.get('active_runtime_sources',[]) if x!='runtime/yado_raw_task_representation_candidate_v2.py']+['runtime/yado_raw_task_representation_candidate_v3.py'])
 rim=core.get('runtime_integrity_manifest',{})
 if not isinstance(rim.get('sources'),dict):raise RuntimeError('RUNTIME_MANIFEST_MISSING')
 rim['sources'].pop('runtime/yado_raw_task_representation_candidate_v2.py',None);rim['sources']['runtime/yado_raw_task_representation_candidate_v3.py']=fsha(V3SRC)
 rim['sources']={k:rim['sources'][k] for k in sorted(rim['sources'])};rim['manifest_digest']=h(rim['sources'])
 core['raw_task_representation']={'component_id':V3,'component_digest':canonical_art['component_digest'],'model_digest':canonical_art['model_digest'],
  'admission_run_id':str(os.getenv('GITHUB_RUN_ID') or 'LOCAL'),'supersedes':V2,'selected_mode':cand['selected_mode'],'selected_pivot':cand['selected_pivot']}
 if not any(x.get('component_id')==V2 for x in core.get('superseded_components',[])):
  core.setdefault('superseded_components',[]).append({'component_id':V2,'superseded_by':V3,'historical_evidence_retained':True,
   'reason':'POST_ADMISSION_V2_COUNTEREXAMPLES_REQUIRED_STRUCTURAL_POSITION_CLAUSE_AND_DATA_DISCOVERED_PIVOT_REPRESENTATION'})
 core['runtime_sha256']=unified_sha
 head['active_capabilities']=sorted(set(V3 if x==V2 else x for x in head.get('active_capabilities',[])));head['new_capabilities']=sorted(set(head.get('new_capabilities',[])+[V3]))
 head['raw_task_representation_v3']={'status':'CANONICAL_ACTIVE','component_id':V3,'component_digest':canonical_art['component_digest'],'model_digest':canonical_art['model_digest'],
  'supersedes':V2,'selected_mode':cand['selected_mode'],'selected_pivot':cand['selected_pivot'],'admission_metrics':metrics}
 head['unified_core']['raw_task_representation_component_digest']=canonical_art['component_digest'];head['unified_core']['runtime_sha256']=unified_sha;head['unified_core']['runtime_integrity_manifest_digest']=rim['manifest_digest']

prov['current_g2_binding'].update({'current_execution_label':'G2_STRUCTURAL_RAW_REPRESENTATION_V3_CANONICAL' if admit else 'G2_RAW_REPRESENTATION_REPAIR_V3_PENDING','frontier':next_cap,
 'frontier_native_method':'select_evolution_skills','frontier_native_owner':'UnifiedYADOKernelV30RC8ExternalCognitive','raw_representation_active_component':V3 if admit else V2,
 'raw_representation_candidate_digest':cand['candidate_digest'],'raw_representation_structural_mode':cand['selected_mode'],'raw_representation_discovered_pivot':cand['selected_pivot']})
prov['registry_digest']=cdig(prov,'registry_digest');write(PROV,prov)
core['algorithm_provenance_registry_digest']=prov['registry_digest'];core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits'
core['raw_representation_v3_canonical_admission_v1']={'status':'CANONICAL_ACTIVE' if admit else 'WITHHOLD','candidate_digest':cand['candidate_digest'],'selected_skill_id':selected,'metrics':metrics,'canonical_mechanism_mutation':admit}
core['core_digest']=cdig(core,'core_digest');write(CORE,core)
head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest'];head['algorithm_provenance_registry']['current_execution_label']=prov['current_g2_binding']['current_execution_label']
head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest'];head['unified_core']['core_digest']=core['core_digest'];head['raw_representation_v3_canonical_admission_v1']={'status':'CANONICAL_ACTIVE' if admit else 'WITHHOLD','candidate_digest':cand['candidate_digest'],'metrics':metrics}
head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits';head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)
ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap]
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.raw_representation_v3_canonical_admission.receipt.v1','status':'PASS_G2_RAW_REPRESENTATION_V3_CANONICAL_ADMISSION_V1' if admit else 'WITHHOLD_G2_RAW_REPRESENTATION_V3_CANONICAL_ADMISSION_V1',
 'candidate_digest':cand['candidate_digest'],'selected_skill_id':selected,'kernel_selection':selection,'metrics':metrics,'checks':checks,
 'canonical_component_digest':None if canonical_art is None else canonical_art['component_digest'],'previous_head_digest':prev_head,'new_head_digest':head['canonical_head_digest'],
 'canonical_mechanism_mutation':admit,'architecture_mutation':False,'generation_transition':False,'g3_genesis_performed':False,'next_required_capability':next_cap,
 'semantic_boundary':'INDEPENDENT FRESH CANONICAL ADMISSION OF STRUCTURAL RAW-TEXT ROUTING V3. SAME-G2 COMPONENT REPLACEMENT; NOT GENERAL LANGUAGE UNDERSTANDING OR G3.'}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_RAW_REPRESENTATION_V3_CANONICAL_ADMISSION_V1",'event_type':'G2_STRUCTURAL_RAW_REPRESENTATION_CANONICAL_ADMISSION',
 'status':'PASS_CANONICAL' if admit else 'WITHHOLD','generation':ledger['current_head'],'deficit':front,
 'effect':f"SELECTED={selected}; MODE={cand['selected_mode']}; PIVOT={cand['selected_pivot']}; PARENT_FRESH={pf:.6f}; V3_FRESH={cf:.6f}; TRAP={ct:.6f}; PERT={cp:.6f}; PREV_REPRO={prev_repro:.6f}; CANONICAL={admit}; G3=False; NEXT={next_cap}",
 'source_path':f'receipts/yado-g2-raw-representation-v3-canonical-admission-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':True,'canonical_mechanism_mutation':admit,'architecture_mutation':False,'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':prev_head,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);write(LEDGER,ledger)
ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_V3_ADMISSION_CONTEXT_INCONSISTENT')
post=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=60)
if post.returncode!=0:raise RuntimeError('POST_V3_ADMISSION_GUARD_FAILED:'+post.stdout[-5000:]+post.stderr[-1000:])
log('complete',admit=admit,selected=selected,metrics=metrics,checks=checks,next=next_cap)
