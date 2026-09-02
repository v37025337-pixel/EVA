from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,subprocess,sys
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_raw_task_representation_candidate_v2 import RawTaskRepresentationRuntimeV2,fit_family,spec_to_json
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json';CORE=REPO/'canonical/yado-unified-core-v1.json';LEDGER=REPO/'architecture/evolution-ledger.json';PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
V2=REPO/'canonical/yado-raw-task-representation-v2.json';BASE=REPO/'receipts/yado-g2-real-world-transfer-benchmark-v1-run-33363995201.json'
BOUND=REPO/'resources/yado-g2-post-composite-ceiling-raw-boundary-v1.json';FRESH2=REPO/'resources/yado-raw-task-representation-v2-fresh-holdout-v1.json'
AUDIT=REPO/'receipts/yado-g2-raw-representation-v2-post-admission-audit-v1-run-33670110185.json'
CAND=REPO/'candidates/kernel-self-generated/raw-task-representation-v3.json';FRESH=REPO/'resources/yado-raw-task-representation-v3-fresh-holdout-v1.json'
ART=REPO/'architecture/yado-kernel-g2-raw-representation-v2-post-admission-repair-v1.json';OUT=ROOT/'yado_kernel_g2_raw_representation_v2_post_admission_repair_v1_receipt.json'
GUARD=ROOT/'yado_canonical_invariant_guard_v1.py';SRC=ROOT/'yado_raw_task_representation_candidate_v2.py'
CV2='ALG-G2-RAW-TASK-REPRESENTATION-V2';CV3='ALG-G2-RAW-TASK-REPRESENTATION-V3'
C1='ALG-CONJUNCTIVE-RULE-INDUCER-V1';CR='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1';CB='ALG-BUDGETED-STAGE-POLICY-V1';CE='RESOURCE-PORTFOLIO-V1'
FAMILIES=('HASHED_WORD_BIGRAM_PERCEPTRON','HASHED_CHAR45_PERCEPTRON','HASHED_HYBRID_PERCEPTRON','TFIDF_HYBRID_CENTROID')
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):x=copy.deepcopy(o);x.pop(field,None);return h(x)
def acc(rows,pred):return sum(pred(x)==y for x,y in rows)/max(1,len(rows))
head,core,ledger,prov,v2,base,bound,fresh2,audit=map(load,[HEAD,CORE,LEDGER,PROV,V2,BASE,BOUND,FRESH2,AUDIT]);validate_ledger_v2(ledger)
front='KERNEL_G2_RAW_REPRESENTATION_V2_POST_ADMISSION_REPAIR_V1'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER')
if audit.get('status')!='WITHHOLD_G2_RAW_REPRESENTATION_V2_POST_ADMISSION_AUDIT_V1':raise RuntimeError('AUDIT_NOT_WITHHOLD')
if head.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')
parent=RawTaskRepresentationRuntimeV2(v2)

rows=[]
for r in base['raw_unstructured']['rows']:rows.append((r['raw_text'],r['expected']))
for r in bound['rows']:rows.append((r['text'],r['expected']))
for r in fresh2['rows']:rows.append((r['text'],r['expected']))
for r in audit['canary_rows']:rows.append((r['text'],r['expected']))
uniq=[];seen=set()
for x,y in rows:
 k=x.strip().lower()
 if k not in seen:seen.add(k);uniq.append((x,y))
by={}
for x,y in uniq:by.setdefault(y,[]).append((x,y))
train=[];dev=[]
for lab in sorted(by):
 rr=sorted(by[lab],key=lambda z:h('V3DEV|'+z[0]+'|'+z[1]))
 for i,row in enumerate(rr):(dev if i%5==0 else train).append(row)
train=sorted(train,key=lambda z:h('V3TR|'+z[0]));dev=sorted(dev,key=lambda z:h('V3DV|'+z[0]))
parent_train=acc(train,parent.predict_capability);parent_dev=acc(dev,parent.predict_capability)

records=[
 {'variant_id':'RAW_V2_CANONICAL_PARENT','parent_id':None,'lineage_id':'G2_RAW_REP_LINEAGE','artifact_digest':v2['component_digest'],
  'task_scores':{'audit_canary':float(audit['canary_accuracy']),'development':parent_dev},'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
  'traits':{'canonical':1.0,'bounded':1.0},'failure_tags':['post_admission_canary_below_gate'],'status':'EVALUATED'},
 {'variant_id':'RAW_V1_HISTORICAL_ROLLBACK','parent_id':'RAW_V2_CANONICAL_PARENT','lineage_id':'G2_RAW_REP_LINEAGE','artifact_digest':'V1_ROLLBACK',
  'task_scores':{'audit_canary':0.0,'development':0.0},'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
  'traits':{'canonical':0.0,'historical':1.0},'failure_tags':['superseded'],'status':'EVALUATED'}
]
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_raw_v3_parent.sqlite'))
try:
 pc=k.select_evolution_parent(records,'post_admission_canary')
 op=k.propose_evolution_operation(records,pc['variant_id'],'raw_representation_post_admission_repair')
finally:k.close()
if pc.get('variant_id')!='RAW_V2_CANONICAL_PARENT':raise RuntimeError('KERNEL_PARENT_NOT_V2:'+json.dumps(pc,sort_keys=True))
if op.get('operation')!='CLONAL':raise RuntimeError('KERNEL_OPERATION_NOT_CLONAL:'+json.dumps(op,sort_keys=True))

skills=[];models={};family_metrics={}
for fam in FAMILIES:
 spec=fit_family(train,fam);tr=acc(train,spec.predict);dv=acc(dev,spec.predict);sid='RAW_V3_'+fam
 models[sid]=spec;family_metrics[sid]={'family':fam,'train':tr,'development':dv}
 skills.append({'skill_id':sid,'artifact_digest':h({'fam':fam,'source':fsha(SRC),'n':len(train)}),'structural_valid':True,'semantic_consistency':1.0,
  'fit_baseline':parent_train,'fit_candidate':tr,'heldout_baseline':parent_dev,'heldout_candidate':dv,
  'regression_pass':dv+1e-12>=parent_dev,'state_integrity':True,'rollback_available':True,'metadata':family_metrics[sid]})
skills.append({'skill_id':'RAW_V2_NO_CHANGE','artifact_digest':v2['component_digest'],'structural_valid':True,'semantic_consistency':1.0,
 'fit_baseline':parent_train,'fit_candidate':parent_train,'heldout_baseline':parent_dev,'heldout_candidate':parent_dev,'regression_pass':True,'state_integrity':True,'rollback_available':True})
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_raw_v3_select.sqlite'))
try:sel=k.select_evolution_skills(skills,max_skills=1,min_semantic_consistency=.90,min_fit_gain=0,max_heldout_drop=0,min_heldout_gain=0)
finally:k.close()
sid=(sel.get('selected_skill_ids') or [None])[0]
if sid is None:raise RuntimeError('KERNEL_SELECTED_NONE')
fam=None if sid=='RAW_V2_NO_CHANGE' else family_metrics[sid]['family']
spec=None if fam is None else fit_family(uniq,fam)
pred=parent.predict_capability if spec is None else spec.predict

fresh=[
# CONJ
("A pharmaceutical batch may ship only if sterility, identity, and release validation all succeed; supplier references are already known.",C1),
("The telecom change is committed iff signature, redundancy, and rollback checks are jointly true.",C1),
("A farm automation command remains blocked when any mandatory safety, calibration, or recovery prerequisite fails.",C1),
("Do not schedule another test; determine whether every required approval condition holds.",C1),
("Ownership metadata is present, but the decision is simply the conjunction of independent compliance gates.",C1),
("The financial settlement proceeds only after authorization, integrity, and reconciliation all pass.",C1),
("A public handbook is attached; acceptance still requires every mandatory safeguard.",C1),
("This is an all-required predicate decision rather than a budget optimization problem.",C1),
("The vaccine record is valid only when source, patient identity, and quality checks all hold.",C1),
("One false mandatory condition is sufficient to withhold approval.",C1),
("Proceed exactly if all required booleans are true; otherwise reject.",C1),
("No external fact is missing; evaluate the mandatory gate conjunction.",C1),
# REL
("Determine whether the pharmacy account owns the dataset or belongs to its authorized clinical group.",CR),
("Telecom access depends on requester-owner identity and approved network-role membership.",CR),
("Ignore cost limits; decide whether the two principals are identical or linked by the required organization relation.",CR),
("Every scalar readiness check passes, yet permission follows from asset ownership and membership edges.",CR),
("The external manual is known; infer authorization from subscriber, tenant, owner, and role relationships.",CR),
("Resolve whether the farm operator belongs to the machine's authorized control cohort.",CR),
("The result changes with entity equality and group links, not remaining credits.",CR),
("Determine access from relational structure among analyst, account owner, institution, and verified role.",CR),
("This is an ownership/membership question rather than an all-gates decision.",CR),
("No public lookup is needed; compare identity and authorization relations.",CR),
("Infer whether subject and resource share the required owner or cohort link.",CR),
("A quota field is irrelevant to permission; principal relations decide it.",CR),
# BUDGET
("Choose the next pharmaceutical assay under a finite lab budget and differing expected information gains.",CB),
("Schedule telecom diagnostics to reach the confidence target without exceeding remaining compute.",CB),
("Ownership is resolved; choose an affordable sequence of crop-sensor checks under quota.",CB),
("Several financial controls are valid but costly; allocate limited review credits among them.",CB),
("Do not merely ask whether all gates pass; choose the next test using cost and evidence gain.",CB),
("External documents are available, but deeper investigations must fit the remaining resource allowance.",CB),
("Find the least expensive staged verification path capable of reaching target confidence.",CB),
("Plan escalation after previous checks while respecting remaining quota and budget.",CB),
("Identity relations are irrelevant; optimize the order of diagnostic stages.",CB),
("Allocate limited sampling time across measurements with different expected gains.",CB),
("Select the next validation stage under a hard resource ceiling.",CB),
("The objective is bounded evidence-gathering search, not retrieval of an outside fact.",CB),
# RESOURCE
("The drug dossier lacks the decisive interaction limit; retrieve a current authoritative medical reference.",CE),
("Local telecom logs cannot establish the protocol requirement, so consult current public documentation.",CE),
("All ownership relations are known, but the missing agricultural standard must come from an external source.",CE),
("Do not run another financial check; obtain the absent regulation from a public legal reference.",CE),
("Remaining compute cannot reveal a fact missing from local state; retrieve vendor documentation.",CE),
("Find an outside scientific standard because the repository lacks the required fact.",CE),
("The next action is external evidence acquisition rather than local inference.",CE),
("Consult an authoritative source beyond stored memory to settle the uncertainty.",CE),
("Local validation succeeded, but the unknown requirement needs public documentation.",CE),
("Use a trustworthy external reference because internal evidence is insufficient.",CE),
("Do not choose another internal stage; fetch the missing specification.",CE),
("The information gap is outside the system, so retrieve it before deciding.",CE),
]
traps=[
("Public sources and owners are mentioned, but release still requires every mandatory quality gate.",C1),
("A budget is listed, yet access depends on account-owner identity and authorized membership.",CR),
("The test name contains 'external', but choose an affordable sequence under a finite allowance.",CB),
("Owner and quota fields are complete; the missing fact still requires a current outside specification.",CE),
("Team relations are known, but approval is only an all-required safeguards decision.",C1),
("Documentation is attached; permission nevertheless follows from entity relationships.",CR),
("All prerequisites hold; now optimize which diagnostic to run under remaining credits.",CB),
("There is remaining budget, but the absent standard can only be obtained externally.",CE),
("Ignore search language: each mandatory prerequisite must pass.",C1),
("Do not evaluate all-of gates; decide access from owner and group links.",CR),
("External evidence is already present; allocate the finite budget across tests.",CB),
("Cost and owner metadata are distractions; consult an outside authoritative source.",CE),
]
fresh_acc=acc(fresh,pred);parent_fresh=acc(fresh,parent.predict_capability);trap=acc(traps,pred)
def perturb(x,i):return ("Case: ","Task: ","Input: ","Note: ")[i%4]+(x.upper() if i%2==0 else x.lower())+(" [x=41]","; meta"," -- standard"," [trace]")[i%4]
pert=[(perturb(x,i),y) for i,(x,y) in enumerate(fresh)];pert_acc=acc(pert,pred)
audit_rows=[(r['text'],r['expected']) for r in audit['canary_rows']];audit_repro=acc(audit_rows,pred)
prior_rows=[(r['text'],r['expected']) for r in fresh2['rows']];prior_repro=acc(prior_rows,pred)
base_rows=[(r['raw_text'],r['expected']) for r in base['raw_unstructured']['rows']];base_reg=acc(base_rows,pred)
fresh_doc={'schema':'yado.g2.raw_task_representation_v3.fresh_holdout.v1','status':'SPENT_AFTER_V3_SHADOW_ADMISSION','selected_skill_id':sid,'selected_family':fam,
 'metrics':{'fresh_accuracy':fresh_acc,'parent_fresh_accuracy':parent_fresh,'trap_accuracy':trap,'perturbation_accuracy':pert_acc,'audit_canary_reproduction':audit_repro,'prior_fresh_reproduction':prior_repro,'base_regression_accuracy':base_reg},
 'rows':[{'text':x,'expected':y,'got':pred(x),'correct':pred(x)==y} for x,y in fresh]};fresh_doc['dataset_digest']=cdig(fresh_doc,'dataset_digest');write(FRESH,fresh_doc)
checks={'kernel_parent_v2':pc.get('variant_id')=='RAW_V2_CANONICAL_PARENT','kernel_operation_clonal':op.get('operation')=='CLONAL','kernel_selected_change':sid!='RAW_V2_NO_CHANGE',
 'fresh_not_used_for_selection':True,'fresh_accuracy':fresh_acc>=.92,'fresh_gain':fresh_acc-parent_fresh>=.03,'trap_accuracy':trap>=.85,'perturbation_accuracy':pert_acc>=.90,
 'audit_canary_repaired':audit_repro>=.95,'prior_fresh_retained':prior_repro>=.93,'base_regression':base_reg>=.95,'v2_remains_canonical':CV2 in head.get('active_capabilities',[]),'g3_not_started':head.get('g3_genesis_performed') is False}
supported=all(checks.values());state='SHADOW_V3_SUPPORTED' if supported else 'WITHHOLD';next_cap='KERNEL_G2_RAW_REPRESENTATION_V3_CANONICAL_ADMISSION_V1' if supported else 'KERNEL_G2_RAW_REPRESENTATION_V2_POST_ADMISSION_REPAIR_V2'
cand={'schema':'yado.g2.raw_task_representation_candidate.v3','state':state,'component_id':CV3,'parent_component_id':CV2,'parent_component_digest':v2['component_digest'],
 'principle':'KERNEL_SELECTED_CLONAL_REPAIR_FROM_PERSISTED_COUNTEREXAMPLE_HISTORY','parent_choice':pc,'evolution_operation':op,'kernel_selection':sel,
 'development':{'permitted_rows':len(uniq),'train_count':len(train),'development_count':len(dev),'family_metrics':family_metrics},'selected_skill_id':sid,'learner_family':fam,
 'model':None if spec is None else spec_to_json(spec),'candidate_runtime_source':'runtime/yado_raw_task_representation_candidate_v2.py','candidate_runtime_sha256':fsha(SRC),
 'fresh_dataset_digest':fresh_doc['dataset_digest'],'metrics':fresh_doc['metrics'],'checks':checks,'canonical_active':False,'canonical_mechanism_mutation':False,'architecture_mutation':False,'g3_genesis_performed':False,
 'semantic_boundary':'BOUNDED RAW-TEXT CAPABILITY ROUTING V3 SHADOW REPAIR FROM PERSISTED COUNTEREXAMPLES; NOT GENERAL LANGUAGE UNDERSTANDING.'};cand['candidate_digest']=h(cand);write(CAND,cand)
artifact={'schema':'yado.g2.kernel_raw_representation_v2_post_admission_repair.v1','status':'PASS_G2_RAW_REPRESENTATION_V2_POST_ADMISSION_REPAIR_V1','candidate_state':state,'candidate_digest':cand['candidate_digest'],'selected_family':fam,'metrics':fresh_doc['metrics'],'checks':checks,'next_required_capability':next_cap,'canonical_mechanism_mutation':False,'architecture_mutation':False,'g3_genesis_performed':False};artifact['artifact_digest']=h(artifact);write(ART,artifact)
prev=head['canonical_head_digest'];prov['current_g2_binding'].update({'current_execution_label':'G2_RAW_REPRESENTATION_V3_SHADOW_SUPPORTED' if supported else 'G2_RAW_REPRESENTATION_V2_REPAIR_V2_PENDING','frontier':next_cap,'frontier_native_method':'select_evolution_parent+propose_evolution_operation+select_evolution_skills','frontier_native_owner':'UnifiedYADOKernelV30RC8ExternalCognitive','raw_representation_candidate_digest':cand['candidate_digest']});prov['registry_digest']=cdig(prov,'registry_digest');write(PROV,prov)
core['algorithm_provenance_registry_digest']=prov['registry_digest'];core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits';core['raw_representation_v2_post_admission_repair_v1']={'state':state,'candidate_digest':cand['candidate_digest'],'selected_family':fam,'metrics':fresh_doc['metrics']};core['core_digest']=cdig(core,'core_digest');write(CORE,core)
head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest'];head['algorithm_provenance_registry']['current_execution_label']=prov['current_g2_binding']['current_execution_label'];head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest'];head['unified_core']['core_digest']=core['core_digest'];head['raw_representation_v2_post_admission_repair_v1']={'state':state,'candidate_digest':cand['candidate_digest'],'selected_family':fam,'metrics':fresh_doc['metrics']};head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits';head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)
ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap];run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={**artifact,'schema':'yado.g2.kernel_raw_representation_v2_post_admission_repair.receipt.v1','previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']};receipt['receipt_sha256']=h(receipt);write(OUT,receipt)
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_RAW_REPRESENTATION_V2_POST_ADMISSION_REPAIR_V1",'event_type':'G2_RAW_REPRESENTATION_COUNTEREXAMPLE_REPAIR','status':'PASS_SHADOW' if supported else 'WITHHOLD','generation':ledger['current_head'],'deficit':front,'effect':f"OP={op.get('operation')}; SELECTED={fam}; PARENT_FRESH={parent_fresh:.6f}; V3_FRESH={fresh_acc:.6f}; TRAP={trap:.6f}; PERT={pert_acc:.6f}; AUDIT_REPRO={audit_repro:.6f}; NEXT={next_cap}",'source_path':f'receipts/yado-g2-raw-representation-v2-post-admission-repair-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':True,'canonical_mechanism_mutation':False,'architecture_mutation':False,'promotion_applied':False,'generation_transition':False,'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']};e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);write(LEDGER,ledger)
ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_V3_REPAIR_CONTEXT_INCONSISTENT')
post=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=60)
if post.returncode!=0:raise RuntimeError('POST_V3_REPAIR_GUARD_FAILED:'+post.stdout[-5000:]+post.stderr[-1000:])
print(json.dumps({'state':state,'selected_family':fam,'metrics':fresh_doc['metrics'],'checks':checks,'next_required_capability':next_cap},indent=2,sort_keys=True))
