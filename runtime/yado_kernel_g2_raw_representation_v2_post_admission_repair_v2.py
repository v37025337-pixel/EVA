from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,subprocess,sys
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_raw_task_representation_candidate_v2 import RawTaskRepresentationRuntimeV2
from yado_raw_task_representation_candidate_v3 import fit_structural_perceptron,discover_pivot_candidates,spec_to_json
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json';CORE=REPO/'canonical/yado-unified-core-v1.json';LEDGER=REPO/'architecture/evolution-ledger.json';PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
V2=REPO/'canonical/yado-raw-task-representation-v2.json';BASE=REPO/'receipts/yado-g2-real-world-transfer-benchmark-v1-run-33363995201.json';BOUND=REPO/'resources/yado-g2-post-composite-ceiling-raw-boundary-v1.json'
F2=REPO/'resources/yado-raw-task-representation-v2-fresh-holdout-v1.json';AUD=REPO/'receipts/yado-g2-raw-representation-v2-post-admission-audit-v1-run-33670110185.json';F3=REPO/'resources/yado-raw-task-representation-v3-fresh-holdout-v1.json'
CAND=REPO/'candidates/kernel-self-generated/raw-task-representation-v3-structural.json';FRESH=REPO/'resources/yado-raw-task-representation-v3-structural-fresh-holdout-v1.json';ART=REPO/'architecture/yado-kernel-g2-raw-representation-v2-post-admission-repair-v2.json'
OUT=ROOT/'yado_kernel_g2_raw_representation_v2_post_admission_repair_v2_receipt.json';GUARD=ROOT/'yado_canonical_invariant_guard_v1.py';SRC=ROOT/'yado_raw_task_representation_candidate_v3.py'
V2ID='ALG-G2-RAW-TASK-REPRESENTATION-V2';V3ID='ALG-G2-RAW-TASK-REPRESENTATION-V3'
C1='ALG-CONJUNCTIVE-RULE-INDUCER-V1';CR='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1';CB='ALG-BUDGETED-STAGE-POLICY-V1';CE='RESOURCE-PORTFOLIO-V1'
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):x=copy.deepcopy(o);x.pop(field,None);return h(x)
def acc(rows,pred):return sum(pred(x)==y for x,y in rows)/max(1,len(rows))
head,core,ledger,prov,v2,base,bound,f2,aud,f3=map(load,[HEAD,CORE,LEDGER,PROV,V2,BASE,BOUND,F2,AUD,F3]);validate_ledger_v2(ledger)
front='KERNEL_G2_RAW_REPRESENTATION_V2_POST_ADMISSION_REPAIR_V2'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER')
if head.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')
if V2ID not in head.get('active_capabilities',[]):raise RuntimeError('V2_NOT_CANONICAL')
parent=RawTaskRepresentationRuntimeV2(v2)

rows=[]
for r in base['raw_unstructured']['rows']:rows.append((r['raw_text'],r['expected']))
for src in (bound,f2,f3):
 for r in src['rows']:rows.append((r['text'],r['expected']))
for r in aud['canary_rows']:rows.append((r['text'],r['expected']))
uniq=[];seen=set()
for x,y in rows:
 k=x.strip().lower()
 if k not in seen:seen.add(k);uniq.append((x,y))
by={}
for x,y in uniq:by.setdefault(y,[]).append((x,y))
train=[];dev=[]
for lab in sorted(by):
 rr=sorted(by[lab],key=lambda z:h('STRUCTDEV|'+z[0]+'|'+z[1]))
 for i,row in enumerate(rr):(dev if i%5==0 else train).append(row)
train=sorted(train,key=lambda z:h('STRUCTTR|'+z[0]));dev=sorted(dev,key=lambda z:h('STRUCTDV|'+z[0]))
p_train=acc(train,parent.predict_capability);p_dev=acc(dev,parent.predict_capability)

records=[
 {'variant_id':'RAW_V2_CANONICAL_PARENT','parent_id':None,'lineage_id':'G2_RAW_REP_STRUCTURAL','artifact_digest':v2['component_digest'],
  'task_scores':{'development':p_dev,'latest_fresh':float(f3['metrics']['fresh_accuracy'])},'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
  'traits':{'canonical':1.0,'bag_ngram':1.0},'failure_tags':['contrastive_clause_boundary'],'status':'EVALUATED'},
 {'variant_id':'SAME_PRIMITIVE_REFIT_V1','parent_id':'RAW_V2_CANONICAL_PARENT','lineage_id':'G2_RAW_REP_STRUCTURAL','artifact_digest':'WITHHOLD_33670393238',
  'task_scores':{'development':p_dev,'latest_fresh':float(f3['metrics']['fresh_accuracy'])},'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
  'traits':{'canonical':0.0,'bag_ngram':1.0},'failure_tags':['no_change_selected'],'status':'EVALUATED'}
]
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_struct_parent.sqlite'))
try:
 pc=k.select_evolution_parent(records,'contrastive_clause_boundary')
 op=k.propose_evolution_operation(records,pc['variant_id'],'structural_raw_representation_repair')
finally:k.close()
allowed_parents={'RAW_V2_CANONICAL_PARENT','SAME_PRIMITIVE_REFIT_V1'}
if pc.get('variant_id') not in allowed_parents:raise RuntimeError('KERNEL_PARENT_OUTSIDE_V2_LINEAGE:'+json.dumps(pc,sort_keys=True))
effective_parent=V2ID
if op.get('operation')!='CLONAL':raise RuntimeError('KERNEL_OPERATION_NOT_CLONAL:'+json.dumps(op,sort_keys=True))

models={};skills=[];met={}
def add(sid,spec,meta):
 tr=acc(train,spec.predict);dv=acc(dev,spec.predict);models[sid]=spec;met[sid]={**meta,'train':tr,'development':dv}
 skills.append({'skill_id':sid,'artifact_digest':h({'sid':sid,'src':fsha(SRC),'n':len(train)}),'structural_valid':True,'semantic_consistency':1.0,
  'fit_baseline':p_train,'fit_candidate':tr,'heldout_baseline':p_dev,'heldout_candidate':dv,'regression_pass':dv+1e-12>=p_dev,'state_integrity':True,'rollback_available':True,'metadata':met[sid]})
add('RAW_V3_STRUCT_POSITIONAL',fit_structural_perceptron(train,'POSITIONAL'),{'mode':'POSITIONAL','pivot':None})
add('RAW_V3_STRUCT_CLAUSE',fit_structural_perceptron(train,'CLAUSE'),{'mode':'CLAUSE','pivot':None})
pivots=discover_pivot_candidates(train,max_candidates=28,min_df=3)
for pivot in pivots:
 sid='RAW_V3_PIVOT_'+hashlib.sha256(pivot.encode()).hexdigest()[:10]
 add(sid,fit_structural_perceptron(train,'PIVOT_CLAUSE',pivot=pivot),{'mode':'PIVOT_CLAUSE','pivot':pivot})
skills.append({'skill_id':'RAW_V2_NO_CHANGE','artifact_digest':v2['component_digest'],'structural_valid':True,'semantic_consistency':1.0,'fit_baseline':p_train,'fit_candidate':p_train,'heldout_baseline':p_dev,'heldout_candidate':p_dev,'regression_pass':True,'state_integrity':True,'rollback_available':True,'metadata':{'mode':'V2_NO_CHANGE'}})
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_struct_select.sqlite'))
try:sel=k.select_evolution_skills(skills,max_skills=1,min_semantic_consistency=.90,min_fit_gain=0,max_heldout_drop=0,min_heldout_gain=0)
finally:k.close()
sid=(sel.get('selected_skill_ids') or [None])[0]
if sid is None:raise RuntimeError('NO_STRUCTURAL_SELECTION')
chosen_meta=met.get(sid);chosen_mode=None if chosen_meta is None else chosen_meta['mode'];chosen_pivot=None if chosen_meta is None else chosen_meta.get('pivot')
spec=None if sid=='RAW_V2_NO_CHANGE' else fit_structural_perceptron(uniq,chosen_mode,pivot=chosen_pivot)
pred=parent.predict_capability if spec is None else spec.predict

fresh=[
("A mining operation may resume only when ventilation, structural inspection, and emergency recovery checks all pass; outside reports are already attached.",C1),
("The cloud release is accepted iff provenance, signature validation, and rollback readiness are jointly true.",C1),
("Do not plan further diagnostics: every mandatory election-audit condition must be satisfied.",C1),
("Ownership is mentioned in the dossier, but approval depends only on all required safety predicates.",C1),
("No external evidence is missing; decide whether the full set of mandatory prerequisites holds.",C1),
("A robotics task proceeds only after calibration, authorization, and fail-safe readiness each pass.",C1),
("The manual is known; commit only when every independent invariant is true.",C1),
("This is an all-of readiness rule, not a relation or resource allocation question.",C1),
("One false mandatory check blocks the clinical release regardless of remaining quota.",C1),
("Proceed exactly when all required acceptance conditions hold simultaneously.",C1),
("The result is withheld unless each prerequisite evaluates true.",C1),
("Search vocabulary is incidental; evaluate the conjunction of safeguards.",C1),

("Determine whether the miner account owns the control asset or belongs to its authorized site group.",CR),
("Cloud access depends on caller-owner identity and approved tenant-role membership.",CR),
("Ignore the test budget; decide whether two voter identifiers denote the same principal or share the required district relation.",CR),
("All scalar checks pass, yet robot permission depends on ownership and team links.",CR),
("The documentation is known; infer access from subject, owner, organization, and role relations.",CR),
("Resolve whether the clinician belongs to the record's authorized care cohort.",CR),
("The outcome changes with entity equality and group membership rather than resource credits.",CR),
("This task concerns principal relations, not whether every independent gate is true.",CR),
("No external lookup is required; compare owner and membership edges.",CR),
("Infer permission from relational structure among the named entities.",CR),
("A quota value is present but authorization follows identity links.",CR),
("Determine whether requester and resource share the required owner or group relation.",CR),

("Choose the next mine-safety diagnostic under a finite inspection budget.",CB),
("Schedule cloud tests to reach target confidence without exceeding remaining compute.",CB),
("Ownership is already settled; select an affordable sequence of audit checks.",CB),
("Several robotics experiments have different costs and expected gains; allocate limited resources among them.",CB),
("Do not simply ask whether all gates pass; choose the next evidence-gathering stage.",CB),
("External reports are available, but deeper checks must fit the remaining allowance.",CB),
("Find the least costly sequence capable of reaching the confidence threshold.",CB),
("Plan escalation after prior tests while respecting spent quota and remaining budget.",CB),
("Identity relations are irrelevant; optimize staged investigation order.",CB),
("Allocate finite measurement time among experiments with unequal evidence gains.",CB),
("Select the next validation action under a hard resource ceiling.",CB),
("This is bounded search planning, not outside information retrieval.",CB),

("Local mining logs lack the decisive exposure limit; retrieve a current authoritative standard.",CE),
("Cloud telemetry cannot establish the vendor guarantee, so consult current public documentation.",CE),
("All voter identity relations are known, but the missing legal rule must come from an outside source.",CE),
("Do not run another robot test; obtain the absent specification from public technical documentation.",CE),
("Remaining budget cannot reveal a fact missing locally; retrieve the external reference.",CE),
("Find a current medical standard because the repository lacks the required fact.",CE),
("The next action is outside evidence acquisition rather than local inference.",CE),
("Consult an authoritative reference beyond stored memory to resolve the uncertainty.",CE),
("Local validation succeeded, but the unknown requirement needs a public source.",CE),
("Use external documentation because internal evidence is insufficient.",CE),
("Do not choose another internal stage; fetch the missing rule from a trustworthy source.",CE),
("The unresolved information lies outside the system, so retrieve it before deciding.",CE),
]
traps=[
("External reports and owner fields appear, but approval still requires every mandatory safety condition.",C1),
("A budget is stated, yet access is decided by principal-owner equality and membership.",CR),
("The stage name says public-check, but choose an affordable diagnostic sequence under finite resources.",CB),
("Owner and quota data are complete; the missing requirement still needs an outside standard.",CE),
("Team links are known, but the actual decision is all mandatory predicates together.",C1),
("A manual is attached; permission nevertheless follows entity relationships.",CR),
("All gates pass; now allocate remaining credits among deeper tests.",CB),
("Budget remains, but the missing specification can only be retrieved externally.",CE),
("Ignore the word search: each required safeguard must be true.",C1),
("Do not evaluate a conjunction; infer access from owner/group relations.",CR),
("External references are already present; optimize which test to run next.",CB),
("Cost and ownership are distractions; obtain the missing fact from an authoritative outside source.",CE),
]
fa=acc(fresh,pred);pf=acc(fresh,parent.predict_capability);ta=acc(traps,pred)
def perturb(x,i):return ("Work item: ","Case record: ","Input packet: ","Request: ")[i%4]+(x.upper() if i%2==0 else x.lower())+(" [id=909]","; meta only"," -- ordinary"," [trace=q]")[i%4]
pert=[(perturb(x,i),y) for i,(x,y) in enumerate(fresh)];pa=acc(pert,pred)
audit_rows=[(r['text'],r['expected']) for r in aud['canary_rows']];ar=acc(audit_rows,pred)
f3rows=[(r['text'],r['expected']) for r in f3['rows']];r3=acc(f3rows,pred)
base_rows=[(r['raw_text'],r['expected']) for r in base['raw_unstructured']['rows']];br=acc(base_rows,pred)
freshdoc={'schema':'yado.g2.raw_task_representation_v3_structural.fresh_holdout.v1','status':'SPENT_AFTER_STRUCTURAL_V3_SHADOW_ADMISSION','selected_skill_id':sid,'selected_mode':chosen_mode,'selected_pivot':chosen_pivot,
 'metrics':{'fresh_accuracy':fa,'parent_fresh_accuracy':pf,'trap_accuracy':ta,'perturbation_accuracy':pa,'audit_canary_reproduction':ar,'v3_prior_fresh_reproduction':r3,'base_regression_accuracy':br},
 'rows':[{'text':x,'expected':y,'got':pred(x),'correct':pred(x)==y} for x,y in fresh]};freshdoc['dataset_digest']=cdig(freshdoc,'dataset_digest');write(FRESH,freshdoc)
checks={'kernel_parent_v2_lineage':pc.get('variant_id') in allowed_parents,'kernel_operation_clonal':op.get('operation')=='CLONAL','kernel_selected_structural_change':sid!='RAW_V2_NO_CHANGE',
 'pivot_candidates_self_discovered':True,'fresh_not_used_for_selection':True,'fresh_accuracy':fa>=.92,'fresh_gain':fa-pf>=.03,'trap_accuracy':ta>=.85,'perturbation_accuracy':pa>=.90,
 'audit_canary_repaired':ar>=.95,'prior_fresh_retained':r3>=.90,'base_regression':br>=.95,'v2_remains_canonical':V2ID in head.get('active_capabilities',[]),'g3_not_started':head.get('g3_genesis_performed') is False}
supported=all(checks.values());state='SHADOW_STRUCTURAL_V3_SUPPORTED' if supported else 'WITHHOLD';next_cap='KERNEL_G2_RAW_REPRESENTATION_V3_CANONICAL_ADMISSION_V1' if supported else 'KERNEL_G2_RAW_REPRESENTATION_V2_POST_ADMISSION_REPAIR_V3'
cand={'schema':'yado.g2.raw_task_representation_structural_candidate.v3','state':state,'component_id':V3ID,'parent_component_id':V2ID,'parent_component_digest':v2['component_digest'],'principle':'SELF_DISCOVERED_STRUCTURAL_POSITION_CLAUSE_PIVOT_REPRESENTATION','parent_choice':pc,'effective_executable_parent':effective_parent,'evolution_operation':op,'kernel_selection':sel,
 'pivot_candidates':pivots,'candidate_metrics':met,'selected_skill_id':sid,'selected_mode':chosen_mode,'selected_pivot':chosen_pivot,'model':None if spec is None else spec_to_json(spec),'candidate_runtime_source':'runtime/yado_raw_task_representation_candidate_v3.py','candidate_runtime_sha256':fsha(SRC),'fresh_dataset_digest':freshdoc['dataset_digest'],'metrics':freshdoc['metrics'],'checks':checks,'host_task_specific_rules_written':False,'pivot_markers_hand_authored':False,'canonical_active':False,'canonical_mechanism_mutation':False,'architecture_mutation':False,'g3_genesis_performed':False,
 'semantic_boundary':'SELF-DISCOVERED STRUCTURAL RAW-TEXT ROUTING PRIMITIVE USING POSITION, CLAUSE, AND DATA-DISCOVERED PIVOT VIEWS. NOT GENERAL LANGUAGE UNDERSTANDING.'};cand['candidate_digest']=h(cand);write(CAND,cand)
artifact={'schema':'yado.g2.kernel_raw_representation_v2_post_admission_repair.v2','status':'PASS_G2_RAW_REPRESENTATION_V2_POST_ADMISSION_REPAIR_V2','candidate_state':state,'candidate_digest':cand['candidate_digest'],'selected_skill_id':sid,'selected_mode':chosen_mode,'selected_pivot':chosen_pivot,'metrics':freshdoc['metrics'],'checks':checks,'next_required_capability':next_cap,'canonical_mechanism_mutation':False,'architecture_mutation':False,'g3_genesis_performed':False};artifact['artifact_digest']=h(artifact);write(ART,artifact)
prev=head['canonical_head_digest'];prov['current_g2_binding'].update({'current_execution_label':'G2_RAW_REPRESENTATION_STRUCTURAL_V3_SHADOW_SUPPORTED' if supported else 'G2_RAW_REPRESENTATION_REPAIR_V3_PENDING','frontier':next_cap,'frontier_native_method':'select_evolution_parent+propose_evolution_operation+select_evolution_skills','frontier_native_owner':'UnifiedYADOKernelV30RC8ExternalCognitive','raw_representation_candidate_digest':cand['candidate_digest'],'raw_representation_structural_mode':chosen_mode,'raw_representation_discovered_pivot':chosen_pivot});prov['registry_digest']=cdig(prov,'registry_digest');write(PROV,prov)
core['algorithm_provenance_registry_digest']=prov['registry_digest'];core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits';core['raw_representation_v2_post_admission_repair_v2']={'state':state,'candidate_digest':cand['candidate_digest'],'selected_mode':chosen_mode,'selected_pivot':chosen_pivot,'metrics':freshdoc['metrics']};core['core_digest']=cdig(core,'core_digest');write(CORE,core)
head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest'];head['algorithm_provenance_registry']['current_execution_label']=prov['current_g2_binding']['current_execution_label'];head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest'];head['unified_core']['core_digest']=core['core_digest'];head['raw_representation_v2_post_admission_repair_v2']={'state':state,'candidate_digest':cand['candidate_digest'],'selected_mode':chosen_mode,'selected_pivot':chosen_pivot,'metrics':freshdoc['metrics']};head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits';head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)
ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap];run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={**artifact,'schema':'yado.g2.kernel_raw_representation_v2_post_admission_repair.receipt.v2','previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']};receipt['receipt_sha256']=h(receipt);write(OUT,receipt)
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_RAW_REPRESENTATION_V2_POST_ADMISSION_REPAIR_V2",'event_type':'G2_RAW_REPRESENTATION_STRUCTURAL_PRIMITIVE_GENESIS','status':'PASS_SHADOW' if supported else 'WITHHOLD','generation':ledger['current_head'],'deficit':front,'effect':f"OP={op.get('operation')}; SELECTED={sid}; MODE={chosen_mode}; PIVOT={chosen_pivot}; PARENT_FRESH={pf:.6f}; CHILD_FRESH={fa:.6f}; TRAP={ta:.6f}; PERT={pa:.6f}; AUDIT_REPRO={ar:.6f}; NEXT={next_cap}",'source_path':f'receipts/yado-g2-raw-representation-v2-post-admission-repair-v2-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':True,'canonical_mechanism_mutation':False,'architecture_mutation':False,'promotion_applied':False,'generation_transition':False,'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']};e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);write(LEDGER,ledger)
ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_STRUCT_V3_CONTEXT_INCONSISTENT')
post=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=60)
if post.returncode!=0:raise RuntimeError('POST_STRUCT_V3_GUARD_FAILED:'+post.stdout[-5000:]+post.stderr[-1000:])
print(json.dumps({'state':state,'selected_skill_id':sid,'selected_mode':chosen_mode,'selected_pivot':chosen_pivot,'metrics':freshdoc['metrics'],'checks':checks,'next_required_capability':next_cap},indent=2,sort_keys=True))
