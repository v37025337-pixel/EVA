from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,random,subprocess,sys

ROOT=Path(__file__).resolve().parent; REPO=ROOT.parent; PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_raw_task_representation_runtime_v1 import RawTaskRepresentationRuntimeV1
from yado_raw_task_representation_candidate_v2 import fit_family,spec_to_json
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
RAW_CANON=REPO/'canonical/yado-raw-task-representation-v1.json'
BASE=REPO/'receipts/yado-g2-real-world-transfer-benchmark-v1-run-33363995201.json'
SPENT=REPO/'resources/yado-g2-post-composite-ceiling-raw-boundary-v1.json'
CAND=REPO/'candidates/kernel-self-generated/raw-task-representation-v2.json'
ART=REPO/'architecture/yado-kernel-g2-raw-representation-post-composite-self-evolution-v1.json'
FRESH_DATA=REPO/'resources/yado-raw-task-representation-v2-fresh-holdout-v1.json'
OUT=ROOT/'yado_kernel_g2_raw_representation_post_composite_self_evolution_v1_receipt.json'
GUARD=ROOT/'yado_canonical_invariant_guard_v1.py'
CAND_SRC=ROOT/'yado_raw_task_representation_candidate_v2.py'

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'

FAMILIES=(
 'HASHED_WORD_BIGRAM_PERCEPTRON',
 'HASHED_CHAR45_PERCEPTRON',
 'HASHED_HYBRID_PERCEPTRON',
 'TFIDF_HYBRID_CENTROID',
)

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):
    x=copy.deepcopy(o);x.pop(field,None);return h(x)
def acc(rows,pred):return sum(pred(x)==y for x,y in rows)/max(1,len(rows))
def log(stage,**kw):print(json.dumps({'stage':stage,**kw},sort_keys=True,default=str),flush=True)

head,core,ledger,prov,raw_art,base,spent=map(load,[HEAD,CORE,LEDGER,PROV,RAW_CANON,BASE,SPENT])
validate_ledger_v2(ledger)
front='KERNEL_G2_RAW_REPRESENTATION_POST_COMPOSITE_SELF_EVOLUTION_V1'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if head.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')
if raw_art.get('canonical_active') is not True:raise RuntimeError('RAW_V1_NOT_CANONICAL')
if float(spent.get('raw_accuracy',1.0))>=.985:raise RuntimeError('SPENT_BOUNDARY_DOES_NOT_SHOW_RESIDUAL')
if head.get('post_composite_architectural_ceiling_reassessment_v1',{}).get('selected_residual')!='RAW_TASK_REPRESENTATION_CROSS_DOMAIN':
    raise RuntimeError('RAW_RESIDUAL_NOT_KERNEL_SELECTED')

base_rows=[(r['raw_text'],r['expected']) for r in base['raw_unstructured']['rows']]
spent_rows=[(r['text'],r['expected']) for r in spent['rows']]
all_rows=[];seen=set()
for x,y in base_rows+spent_rows:
    k=x.strip().lower()
    if k not in seen:seen.add(k);all_rows.append((x,y))

# Deterministic stratified development split using spent evidence only.
by={}
for x,y in all_rows:by.setdefault(y,[]).append((x,y))
train=[];dev=[]
for label in sorted(by):
    rows=sorted(by[label],key=lambda r:h('DEV|'+r[0]+'|'+r[1]))
    for i,row in enumerate(rows):
        (dev if i%4==0 else train).append(row)
train=sorted(train,key=lambda r:h('TR|'+r[0]+'|'+r[1]))
dev=sorted(dev,key=lambda r:h('DV|'+r[0]+'|'+r[1]))
if len(dev)<12 or len(train)<36:raise RuntimeError('DEVELOPMENT_SPLIT_TOO_SMALL')

parent=RawTaskRepresentationRuntimeV1(raw_art)
parent_train=acc(train,parent.predict_capability);parent_dev=acc(dev,parent.predict_capability)

records=[
 {'variant_id':'RAW_V1_CANONICAL_PARENT','parent_id':None,'lineage_id':'G2_RAW_REP_LINEAGE',
  'artifact_digest':raw_art['component_digest'],
  'task_scores':{'residual_boundary':float(spent['raw_accuracy']),'development':parent_dev},
  'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
  'traits':{'canonical':1.0,'bounded':1.0},'failure_tags':['cross_domain_residual'],'status':'EVALUATED'},
 {'variant_id':'RAW_V0_PRE_REPRESENTATION_BASELINE','parent_id':'RAW_V1_CANONICAL_PARENT','lineage_id':'G2_RAW_REP_LINEAGE',
  'artifact_digest':'raw-v0-structured-default','task_scores':{'residual_boundary':.25,'development':.25},
  'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
  'traits':{'canonical':0.0,'bounded':1.0},'failure_tags':['raw_representation_gap'],'status':'EVALUATED'}
]
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_raw_rep_v2_parent.sqlite'))
try:
    parent_choice=k.select_evolution_parent(records,'cross_domain_residual')
    operation=k.propose_evolution_operation(records,parent_choice['variant_id'],'raw_representation_self_evolution')
finally:k.close()
if parent_choice.get('variant_id')!='RAW_V1_CANONICAL_PARENT':
    raise RuntimeError('KERNEL_SELECTED_UNSUPPORTED_PARENT:'+json.dumps(parent_choice,sort_keys=True))
if operation.get('operation')!='CLONAL':
    raise RuntimeError('KERNEL_DID_NOT_SELECT_CLONAL:'+json.dumps(operation,sort_keys=True))
log('parent_operation',parent=parent_choice,operation=operation,parent_train=parent_train,parent_dev=parent_dev)

skill_rows=[];models={};metrics={}
for fam in FAMILIES:
    spec=fit_family(train,fam)
    tr=acc(train,spec.predict);dv=acc(dev,spec.predict)
    sid='RAW_V2_'+fam
    models[sid]=spec
    metrics[sid]={'family':fam,'train':tr,'development':dv}
    skill_rows.append({
      'skill_id':sid,'artifact_digest':h({'family':fam,'source_sha256':fsha(CAND_SRC),'train_count':len(train)}),
      'structural_valid':True,'semantic_consistency':1.0,
      'fit_baseline':parent_train,'fit_candidate':tr,
      'heldout_baseline':parent_dev,'heldout_candidate':dv,
      'regression_pass':dv+1e-12>=parent_dev,
      'state_integrity':True,'rollback_available':True,
      'metadata':metrics[sid],
    })
# Parent is also a selectable no-change control.
skill_rows.append({
 'skill_id':'RAW_V1_NO_CHANGE','artifact_digest':raw_art['component_digest'],
 'structural_valid':True,'semantic_consistency':1.0,
 'fit_baseline':parent_train,'fit_candidate':parent_train,
 'heldout_baseline':parent_dev,'heldout_candidate':parent_dev,
 'regression_pass':True,'state_integrity':True,'rollback_available':True,
 'metadata':{'family':'CHAR_NGRAM_CENTROID_V1','train':parent_train,'development':parent_dev}
})
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_raw_rep_v2_select.sqlite'))
try:
    selection=k.select_evolution_skills(skill_rows,max_skills=1,min_semantic_consistency=.90,min_fit_gain=0.0,max_heldout_drop=0.0,min_heldout_gain=0.0)
finally:k.close()
selected_ids=list(selection.get('selected_skill_ids') or [])
selected_id=selected_ids[0] if selected_ids else None
if selected_id is None:raise RuntimeError('KERNEL_SELECTED_NO_REPRESENTATION_SKILL')
selected_family=None if selected_id=='RAW_V1_NO_CHANGE' else metrics[selected_id]['family']
log('kernel_selection',selection=selection,metrics=metrics,parent_dev=parent_dev)

# Refit selected family on all allowed spent evidence. Fresh rows below are not consulted until now.
selected_spec=None if selected_family is None else fit_family(all_rows,selected_family)
selected_pred=parent.predict_capability if selected_spec is None else selected_spec.predict

# Independent fresh V2 holdout: new domains and contrastive distractors.
fresh=[
# CONJ
("In a hospital release workflow, outside references may exist, but discharge is allowed only when consent, identity verification, and safety review all pass together.",CAP_CONJ),
("A spacecraft command is accepted iff checksum validity, authorization, and rollback readiness are simultaneously true; cost is not being optimized.",CAP_CONJ),
("For this legal filing, ownership details are irrelevant: every mandatory signature, jurisdiction, and integrity condition must succeed.",CAP_CONJ),
("The trading model stays blocked if any one of audit approval, data integrity, or recovery readiness is false.",CAP_CONJ),
("No further experiment is requested; decide whether all required deployment invariants hold at once.",CAP_CONJ),
("The shipment may depart only after customs clearance, seal verification, and route safety each pass.",CAP_CONJ),
("Even though compute credits are listed, approval is simply the conjunction of three mandatory readiness checks.",CAP_CONJ),
("External documentation has already been obtained; commit only if provenance, validation, and restore readiness all hold.",CAP_CONJ),
("A medical record is trusted only when source authenticity, patient match, and validation are jointly satisfied.",CAP_CONJ),
("One failed mandatory safeguard is sufficient to withhold the operation, regardless of team membership.",CAP_CONJ),
("This is an all-required-conditions decision, not a search or relationship problem.",CAP_CONJ),
("Proceed exactly when each independent prerequisite is true; otherwise withhold.",CAP_CONJ),

# REL
("For a clinical dataset, decide whether the requester is the owner, a member of the approved research group, or a verified custodian.",CAP_REL),
("The satellite command permission depends on relationships among operator, asset owner, mission team, and verified role.",CAP_REL),
("Do not inspect the budget; determine whether two account identifiers denote the same principal or share the required organization link.",CAP_REL),
("All safety gates are green, yet access still depends on claimant-owner identity and membership edges.",CAP_REL),
("A public manual is available, but authorization follows from who owns the resource and how the actors are related.",CAP_REL),
("Determine whether the physician belongs to the patient's authorized care group or is the registered owner of the record.",CAP_REL),
("The decision changes when entity equality or group membership changes, not when compute allowance changes.",CAP_REL),
("Infer permission from tenant, owner, subject, and role relations rather than independent boolean readiness gates.",CAP_REL),
("Check whether the logistics agent and warehouse share the required ownership or authorized-cohort relationship.",CAP_REL),
("This task asks about identity and membership structure; no outside evidence retrieval is needed.",CAP_REL),
("Resolve access from same-principal and same-group links among the named entities.",CAP_REL),
("Even with a quota field present, permission is determined by relational structure.",CAP_REL),

# BUDGET
("Choose the next medical diagnostic under a fixed testing allowance, balancing cost and expected information gain.",CAP_BUD),
("For spacecraft troubleshooting, schedule checks so the target confidence is reached without exceeding remaining compute.",CAP_BUD),
("Ownership is known; the task is to choose an affordable sequence of verification stages under quota.",CAP_BUD),
("A legal review has several valid checks with different costs; pick the next stage within the remaining allowance.",CAP_BUD),
("Do not merely test whether all gates pass; optimize which experiment to run next under finite resources.",CAP_BUD),
("External sources are already available, but the problem is allocating limited credits among deeper investigations.",CAP_BUD),
("Select the least costly set of diagnostics likely to reach the confidence threshold.",CAP_BUD),
("Plan escalation after prior tests while respecting spent budget, remaining quota, and expected evidence gain.",CAP_BUD),
("Entity relationships do not decide this task; choose among staged searches with different costs.",CAP_BUD),
("Allocate a finite observation budget across cheap and expensive measurements.",CAP_BUD),
("Pick the next validation action under hard cost and quota limits.",CAP_BUD),
("The objective is resource-constrained evidence gathering, not external lookup.",CAP_BUD),

# RESOURCE
("The clinical record lacks the decisive fact; retrieve a current authoritative medical reference before deciding.",CAP_RES),
("Local spacecraft telemetry cannot establish the required specification, so consult current public technical documentation.",CAP_RES),
("All identity relations are already known; the missing information must come from an outside standards source.",CAP_RES),
("Do not schedule more internal tests: obtain the unresolved fact from current vendor documentation.",CAP_RES),
("Even with remaining compute budget, local state is insufficient and an external reference is required.",CAP_RES),
("Find a public legal source because the repository does not contain the rule needed for the decision.",CAP_RES),
("The next action is to acquire outside scientific evidence, not infer further from local claims.",CAP_RES),
("Retrieve an authoritative specification beyond local memory to settle the uncertainty.",CAP_RES),
("Local validation succeeded, but the missing behavior must be verified from a current public source.",CAP_RES),
("Use external documentation because internal evidence cannot answer the question.",CAP_RES),
("Obtain the missing fact from an eligible public resource rather than choosing another local stage.",CAP_RES),
("The information gap lies outside the system; fetch a trustworthy reference.",CAP_RES),
]

traps=[
("The ticket mentions owners and outside docs, but the only question is whether every mandatory integrity check succeeds.",CAP_CONJ),
("A budget number appears in the record, yet authorization depends on requester-owner identity and group membership.",CAP_REL),
("The word 'external' appears in a stage name; nevertheless the task is to choose tests under a finite compute allowance.",CAP_BUD),
("Several local gates and ownership fields are present, but the unresolved fact must be obtained from a public specification.",CAP_RES),
("Although team membership is recorded, acceptance still requires all independent safeguards to be true.",CAP_CONJ),
("Documentation is attached and costs are listed, but permission still follows from entity relations.",CAP_REL),
("All prerequisites are true; now choose the least costly next investigation within quota.",CAP_BUD),
("A cost limit exists, but no local experiment can reveal the missing standard, so retrieve it externally.",CAP_RES),
("No search is needed: the release rule is simply that every required condition must hold.",CAP_CONJ),
("Do not treat this as an all-of gate; compare actor, owner, and membership links.",CAP_REL),
("The owner field is irrelevant; allocate remaining credits across diagnostic stages.",CAP_BUD),
("Do not infer from ownership or budget fields; consult an outside authoritative source.",CAP_RES),
]

fresh_acc=acc(fresh,selected_pred);trap_acc=acc(traps,selected_pred)
parent_fresh=acc(fresh,parent.predict_capability);parent_trap=acc(traps,parent.predict_capability)
base_reg=acc(base_rows,selected_pred)

def perturb(text,i):
    pre=("Case file: ","Incoming request: ","System note: ","Review item: ")[i%4]
    post=(" [ref=K9]","; metadata omitted"," -- normal priority"," [trace=2718]")[i%4]
    t=text.upper() if i%2==0 else text.lower()
    return pre+t+post
pert=[(perturb(x,i),y) for i,(x,y) in enumerate(fresh)]
pert_acc=acc(pert,selected_pred)

fresh_doc={
 'schema':'yado.g2.raw_task_representation_v2.fresh_holdout.v1',
 'status':'SPENT_AFTER_SINGLE_V2_ADMISSION',
 'selection_completed_before_fresh_evaluation':True,
 'selected_skill_id':selected_id,'selected_family':selected_family,
 'task_count':len(fresh),'trap_count':len(traps),'perturbation_count':len(pert),
 'metrics':{'fresh_accuracy':fresh_acc,'trap_accuracy':trap_acc,'perturbation_accuracy':pert_acc,
            'parent_fresh_accuracy':parent_fresh,'parent_trap_accuracy':parent_trap,'base_regression_accuracy':base_reg},
 'rows':[{'text':x,'expected':y,'got':selected_pred(x),'correct':selected_pred(x)==y} for x,y in fresh]
}
fresh_doc['dataset_digest']=cdig(fresh_doc,'dataset_digest');write(FRESH_DATA,fresh_doc)

checks={
 'kernel_parent_current_raw_v1':parent_choice.get('variant_id')=='RAW_V1_CANONICAL_PARENT',
 'kernel_operation_clonal':operation.get('operation')=='CLONAL',
 'kernel_selected_candidate':selected_id is not None and selected_id!='RAW_V1_NO_CHANGE',
 'fresh_not_used_for_selection':True,
 'fresh_accuracy_gate':fresh_acc>=.90,
 'fresh_gain_over_parent':fresh_acc-parent_fresh>=.08,
 'trap_accuracy_gate':trap_acc>=.75,
 'perturbation_accuracy_gate':pert_acc>=.85,
 'base_regression_gate':base_reg>=.95,
 'canonical_parent_unchanged':raw_art.get('component_id')=='ALG-G2-RAW-TASK-REPRESENTATION-V1',
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
supported=all(checks.values())
state='SHADOW_V2_SUPPORTED' if supported else 'WITHHOLD'
next_cap='KERNEL_G2_RAW_REPRESENTATION_V2_CANONICAL_ADMISSION_V1' if supported else 'KERNEL_G2_RAW_REPRESENTATION_POST_COMPOSITE_SELF_EVOLUTION_V2'

model_json=None if selected_spec is None else spec_to_json(selected_spec)
candidate={
 'schema':'yado.g2.raw_task_representation_candidate.v2','state':state,
 'component_id':'ALG-G2-RAW-TASK-REPRESENTATION-V2',
 'parent_component_id':raw_art['component_id'],'parent_component_digest':raw_art['component_digest'],
 'principle':'KERNEL_SELECTED_CLONAL_GENERIC_TEXT_REPRESENTATION_SEARCH',
 'parent_choice':parent_choice,'evolution_operation':operation,'kernel_selection':selection,
 'development_split':{'train_count':len(train),'development_count':len(dev),'permitted_rows':len(all_rows)},
 'candidate_family_metrics':metrics,'selected_skill_id':selected_id,'learner_family':selected_family,
 'model':model_json,'candidate_runtime_source':'runtime/yado_raw_task_representation_candidate_v2.py',
 'candidate_runtime_sha256':fsha(CAND_SRC),'fresh_dataset_digest':fresh_doc['dataset_digest'],
 'metrics':fresh_doc['metrics'],'checks':checks,
 'host_task_specific_rules_written':False,'generic_feature_search_only':True,
 'canonical_active':False,'canonical_mechanism_mutation':False,'architecture_mutation':False,
 'generation_transition':False,'g3_genesis_performed':False,
 'semantic_boundary':'BOUNDED RAW-TEXT CAPABILITY ROUTING V2 USING KERNEL-SELECTED GENERIC TEXT REPRESENTATION. NOT GENERAL LANGUAGE UNDERSTANDING OR ENTITY-LEVEL SEMANTIC GROUNDING.'
}
candidate['candidate_digest']=h(candidate);write(CAND,candidate)
artifact={
 'schema':'yado.g2.kernel_raw_representation_post_composite_self_evolution.v1',
 'status':'PASS_G2_RAW_REPRESENTATION_POST_COMPOSITE_SELF_EVOLUTION_V1',
 'candidate_state':state,'candidate_digest':candidate['candidate_digest'],
 'selected_skill_id':selected_id,'selected_family':selected_family,'metrics':fresh_doc['metrics'],'checks':checks,
 'next_required_capability':next_cap,'canonical_mechanism_mutation':False,'architecture_mutation':False,'g3_genesis_performed':False
}
artifact['artifact_digest']=h(artifact);write(ART,artifact)

prev=head['canonical_head_digest']
prov['current_g2_binding'].update({
 'current_execution_label':'G2_RAW_REPRESENTATION_V2_SHADOW_SUPPORTED' if supported else 'G2_RAW_REPRESENTATION_SELF_EVOLUTION_V2_PENDING',
 'frontier':next_cap,'frontier_native_method':'select_evolution_parent+propose_evolution_operation+select_evolution_skills',
 'frontier_native_owner':'UnifiedYADOKernelV30RC8ExternalCognitive',
 'raw_representation_selected_family':selected_family,'raw_representation_candidate_digest':candidate['candidate_digest']
})
prov['registry_digest']=cdig(prov,'registry_digest');write(PROV,prov)
core['algorithm_provenance_registry_digest']=prov['registry_digest'];core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits'
core['raw_representation_post_composite_self_evolution_v1']={
 'state':state,'candidate_digest':candidate['candidate_digest'],'selected_family':selected_family,
 'metrics':fresh_doc['metrics'],'fresh_dataset_digest':fresh_doc['dataset_digest'],'canonical_active':False}
core['core_digest']=cdig(core,'core_digest');write(CORE,core)
head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest'];head['algorithm_provenance_registry']['current_execution_label']=prov['current_g2_binding']['current_execution_label']
head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest'];head['unified_core']['core_digest']=core['core_digest']
head['raw_representation_post_composite_self_evolution_v1']={
 'state':state,'candidate_digest':candidate['candidate_digest'],'selected_family':selected_family,
 'metrics':fresh_doc['metrics'],'canonical_active':False}
head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits';head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)
ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap]

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={**artifact,'schema':'yado.g2.kernel_raw_representation_post_composite_self_evolution.receipt.v1',
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest'],'provenance_registry_digest':prov['registry_digest']}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_RAW_REPRESENTATION_POST_COMPOSITE_SELF_EVOLUTION_V1",
 'event_type':'G2_RAW_REPRESENTATION_SELF_EVOLUTION','status':'PASS_SHADOW' if supported else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':front,
 'effect':f"OP={operation.get('operation')}; SELECTED={selected_family}; PARENT_FRESH={parent_fresh:.6f}; V2_FRESH={fresh_acc:.6f}; TRAP={trap_acc:.6f}; PERT={pert_acc:.6f}; BASE_REG={base_reg:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-g2-raw-representation-post-composite-self-evolution-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':True,'canonical_mechanism_mutation':False,'architecture_mutation':False,
 'promotion_applied':False,'generation_transition':False,'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);write(LEDGER,ledger)
ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_RAW_V2_CONTEXT_INCONSISTENT')
post=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=60)
if post.returncode!=0:raise RuntimeError('POST_RAW_V2_GUARD_FAILED:'+post.stdout[-4000:]+post.stderr[-1000:])
log('complete',state=state,selected_family=selected_family,metrics=fresh_doc['metrics'],checks=checks,next=next_cap)
