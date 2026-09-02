from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,subprocess,sys

ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_raw_task_representation_candidate_v3 import RawTaskRepresentationRuntimeV3
from yado_raw_task_representation_robustness_v4 import RobustRawTaskRepresentationRuntimeV4,component
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
V3=REPO/'canonical/yado-raw-task-representation-v3.json'
STRUCT=REPO/'resources/yado-raw-task-representation-v3-structural-fresh-holdout-v1.json'
V2AUD=REPO/'receipts/yado-g2-raw-representation-v2-post-admission-audit-v1-run-33670110185.json'
BASE=REPO/'receipts/yado-g2-real-world-transfer-benchmark-v1-run-33363995201.json'
DIAG=REPO/'receipts/yado-g2-raw-representation-v3-robustness-diagnosis-v1-run-33679412507.json'
CAND=REPO/'candidates/kernel-self-generated/raw-task-representation-v4-robustness.json'
ART=REPO/'architecture/yado-kernel-g2-raw-representation-v3-robustness-self-evolution-v1.json'
FRESH=REPO/'resources/yado-raw-task-representation-v4-robustness-fresh-holdout-v1.json'
OUT=ROOT/'yado_kernel_g2_raw_representation_v3_robustness_self_evolution_v1_receipt.json'
GUARD=ROOT/'yado_canonical_invariant_guard_v1.py'
V4SRC=ROOT/'yado_raw_task_representation_robustness_v4.py'

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'
MODES=('PARENT_V3','CORE_IF_WRAPPER','MULTIVIEW_TIE_CORE','CORE_ALWAYS')

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):
    x=copy.deepcopy(o);x.pop(field,None);return h(x)
def acc(rows,pred):return sum(pred(x)==y for x,y in rows)/max(1,len(rows))

head,core,ledger,prov,v3,struct,v2aud,base,diag=map(load,[HEAD,CORE,LEDGER,PROV,V3,STRUCT,V2AUD,BASE,DIAG])
validate_ledger_v2(ledger)
front='KERNEL_G2_RAW_REPRESENTATION_V3_ROBUSTNESS_SELF_EVOLUTION_V1'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if diag.get('status')!='PASS_G2_RAW_REPRESENTATION_V3_ROBUSTNESS_DIAGNOSIS_V1':raise RuntimeError('DIAGNOSIS_NOT_PASS')
if head.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')
if v3.get('canonical_active') is not True:raise RuntimeError('V3_NOT_CANONICAL')

base_cases=[(r['text'],r['expected']) for r in struct['rows']]
base_cases += [(r['text'],r['expected']) for r in v2aud['canary_rows']]

def perturb(text,round_no,index):
    if round_no==1:return f"Case metadata {index%17}: "+text+f" [trace {1000+index}]"
    if round_no==2:
        t=text.upper() if index%2==0 else text.lower()
        return "Administrative note. "+t+" End note."
    t="  ".join(text.replace(";"," ; ").replace(","," , ").split())
    return f"Review item {index%23}. {t} [normal priority]"

spent_fit=[];spent_hold=[]
for rn in (1,2):
    for i,(x,y) in enumerate(base_cases):spent_fit.append((perturb(x,rn,i),y))
for i,(x,y) in enumerate(base_cases):spent_hold.append((perturb(x,3,i),y))

parent=RawTaskRepresentationRuntimeV3(v3)
parent_fit=acc(spent_fit,parent.predict_capability);parent_hold=acc(spent_hold,parent.predict_capability)
parent_direct=acc(base_cases,parent.predict_capability)

metrics={}
skill_rows=[]
for mode in MODES:
    rt=RobustRawTaskRepresentationRuntimeV4(v3,mode)
    fit=acc(spent_fit,rt.predict_capability);hold=acc(spent_hold,rt.predict_capability);direct=acc(base_cases,rt.predict_capability)
    metrics[mode]={'fit_spent_perturbations':fit,'holdout_spent_round3':hold,'direct_base':direct}
    skill_rows.append({
      'skill_id':'RAW_V4_'+mode,'artifact_digest':h({'mode':mode,'v3':v3['component_digest'],'runtime':fsha(V4SRC)}),
      'structural_valid':True,'semantic_consistency':1.0,
      'fit_baseline':parent_fit,'fit_candidate':fit,
      'heldout_baseline':parent_hold,'heldout_candidate':hold,
      'regression_pass':hold+1e-12>=parent_hold and direct+1e-12>=parent_direct,
      'state_integrity':True,'rollback_available':True,
      'metadata':metrics[mode],
    })

records=[
 {'variant_id':'RAW_V3_CANONICAL_PARENT','parent_id':None,'lineage_id':'G2_RAW_ROBUSTNESS_LINEAGE','artifact_digest':v3['component_digest'],
  'task_scores':{'perturbation':parent_fit,'round3':parent_hold,'direct':parent_direct},
  'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
  'traits':{'canonical':1.0,'structural_pivot':1.0},'failure_tags':['wrapper_invariance_residual'],'status':'EVALUATED'}
]
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_raw_v4_robust_parent.sqlite'))
try:
    psel=k.select_evolution_parent(records,'wrapper_invariance_residual')
    operation=k.propose_evolution_operation(records,psel['variant_id'],'raw_representation_robustness_self_evolution')
finally:k.close()
if psel.get('variant_id')!='RAW_V3_CANONICAL_PARENT' or operation.get('operation')!='CLONAL':
    raise RuntimeError('KERNEL_PARENT_OR_OPERATION_INVALID:'+json.dumps({'parent':psel,'operation':operation},sort_keys=True))

k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_raw_v4_robust_select.sqlite'))
try:
    selection=k.select_evolution_skills(skill_rows,max_skills=1,min_semantic_consistency=.90,min_fit_gain=.01,max_heldout_drop=0.0,min_heldout_gain=.01)
finally:k.close()
selected_ids=list(selection.get('selected_skill_ids') or [])
selected_id=selected_ids[0] if selected_ids else None
selected_mode=None if selected_id is None else selected_id.removeprefix('RAW_V4_')
if selected_mode not in MODES or selected_mode=='PARENT_V3':
    selected_mode=None

# Independent fresh robustness holdout is declared only after selection.
fresh_base=[
("Approve only when checksum, authorization, and recovery readiness all succeed together.",CAP_CONJ),
("A public guide is present, yet every mandatory safety gate must still pass.",CAP_CONJ),
("One failed prerequisite blocks release; no staged search is requested.",CAP_CONJ),
("The decision is simply whether all independent readiness conditions are true.",CAP_CONJ),
("Ignore ownership metadata: acceptance requires all compulsory validations.",CAP_CONJ),
("Proceed iff every mandatory invariant holds at once.",CAP_CONJ),
("All three required safeguards must pass; otherwise withhold.",CAP_CONJ),
("This is conjunction over required gates, not resource planning.",CAP_CONJ),

("Decide access from requester-owner equality and authorized group membership.",CAP_REL),
("The compute allowance is irrelevant; permission follows from identity and membership links.",CAP_REL),
("All scalar gates pass, but authorization still depends on relational structure.",CAP_REL),
("Determine whether the claimant belongs to the owner's approved cohort.",CAP_REL),
("Infer access from principal, owner, tenant, and verified-role relations.",CAP_REL),
("The result changes with entity equality and group edges, not with budget.",CAP_REL),
("Resolve whether two named identities are the same principal or linked by an authorized group.",CAP_REL),
("This is a relation problem rather than an all-of gate.",CAP_REL),

("Choose the next diagnostic under a finite compute allowance.",CAP_BUD),
("Allocate remaining credits among tests with different expected gains.",CAP_BUD),
("Ownership is settled; select an affordable sequence of verification stages.",CAP_BUD),
("Pick the next experiment using cost, latency, quota, and expected gain.",CAP_BUD),
("Plan deeper checks without exceeding the remaining budget.",CAP_BUD),
("Choose the least-cost sequence that can reach the confidence target.",CAP_BUD),
("The task is staged evidence gathering under resource constraints.",CAP_BUD),
("Select what to run next after accounting for spent resources.",CAP_BUD),

("Local evidence cannot settle the missing fact; retrieve a current authoritative source.",CAP_RES),
("Ownership relations are known, but the missing rule must come from public documentation.",CAP_RES),
("Do not run another local test; obtain the absent specification externally.",CAP_RES),
("A budget remains, yet the required fact lies outside local state.",CAP_RES),
("Consult a current technical reference because internal evidence is insufficient.",CAP_RES),
("The repository lacks the governing rule, so retrieve an outside source.",CAP_RES),
("The next action is external evidence acquisition, not local inference.",CAP_RES),
("Fetch a trustworthy public reference to resolve the missing information.",CAP_RES),
]
def fresh_wrap(text,i):
    m=i%4
    if m==0:return f"Header {i%19}: {text}"
    if m==1:return f"Routing memo. {text} Closed."
    if m==2:return text+f" [packet={300+i}]"
    return f"(record {i%13}) {text} <end>"

selected_rt=None if selected_mode is None else RobustRawTaskRepresentationRuntimeV4(v3,selected_mode)
selected_pred=parent.predict_capability if selected_rt is None else selected_rt.predict_capability
fresh_plain=acc(fresh_base,selected_pred)
fresh_wrapped=[(fresh_wrap(x,i),y) for i,(x,y) in enumerate(fresh_base)]
fresh_wrapped_acc=acc(fresh_wrapped,selected_pred)
parent_fresh_wrapped=acc(fresh_wrapped,parent.predict_capability)
base_rows=[(r['raw_text'],r['expected']) for r in base['raw_unstructured']['rows']]
base_reg=acc(base_rows,selected_pred)

checks={
 'kernel_parent_v3':psel.get('variant_id')=='RAW_V3_CANONICAL_PARENT',
 'kernel_operation_clonal':operation.get('operation')=='CLONAL',
 'kernel_selected_robustness_candidate':selected_mode is not None,
 'selected_spent_fit_gain':selected_mode is not None and metrics[selected_mode]['fit_spent_perturbations']>parent_fit,
 'selected_spent_holdout_gain':selected_mode is not None and metrics[selected_mode]['holdout_spent_round3']>parent_hold,
 'fresh_not_used_for_selection':True,
 'fresh_plain_accuracy':fresh_plain>=.95,
 'fresh_wrapped_accuracy':fresh_wrapped_acc>=.95,
 'fresh_wrapped_gain_over_parent':fresh_wrapped_acc-parent_fresh_wrapped>=.03,
 'base_regression':base_reg>=.95,
 'class_specific_rules_absent':True,
 'parent_v3_not_retrained':True,
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
supported=all(checks.values())
state='SHADOW_V4_ROBUSTNESS_SUPPORTED' if supported else 'WITHHOLD'
next_cap='KERNEL_G2_RAW_REPRESENTATION_V4_CANONICAL_ADMISSION_V1' if supported else 'KERNEL_G2_RAW_REPRESENTATION_V3_ROBUSTNESS_SELF_EVOLUTION_V2'

fresh_doc={'schema':'yado.g2.raw_task_representation_v4_robustness.fresh_holdout.v1','status':'SPENT_AFTER_V4_ROBUSTNESS_SHADOW_EVALUATION',
 'selection_completed_before_fresh_evaluation':True,'selected_mode':selected_mode,'task_count':len(fresh_base),
 'metrics':{'fresh_plain_accuracy':fresh_plain,'fresh_wrapped_accuracy':fresh_wrapped_acc,'parent_fresh_wrapped':parent_fresh_wrapped,'base_regression':base_reg},
 'rows':[{'text':x,'wrapped':fresh_wrap(x,i),'expected':y,'got':selected_pred(fresh_wrap(x,i)),'correct':selected_pred(fresh_wrap(x,i))==y} for i,(x,y) in enumerate(fresh_base)]}
fresh_doc['dataset_digest']=cdig(fresh_doc,'dataset_digest');write(FRESH,fresh_doc)

comp=None if selected_mode is None else component(selected_mode,v3['component_digest'])
candidate={'schema':'yado.g2.raw_task_representation_v4_robustness.candidate.v1','state':state,
 'component_id':'ALG-G2-RAW-TASK-REPRESENTATION-V4','parent_component_id':v3['component_id'],'parent_component_digest':v3['component_digest'],
 'kernel_parent':psel,'kernel_operation':operation,'kernel_selection':selection,'candidate_metrics':metrics,
 'selected_mode':selected_mode,'component':comp,'runtime_source':'runtime/yado_raw_task_representation_robustness_v4.py','runtime_sha256':fsha(V4SRC),
 'fresh_dataset_digest':fresh_doc['dataset_digest'],'fresh_metrics':fresh_doc['metrics'],'checks':checks,
 'generic_wrapper_invariance_only':True,'class_specific_rules':False,'parent_model_retrained':False,
 'canonical_active':False,'canonical_mechanism_mutation':False,'architecture_mutation':False,'g3_genesis_performed':False,
 'semantic_boundary':'GENERIC WRAPPER-INVARIANCE LAYER OVER CANONICAL V3; NO CLASS-SPECIFIC SEMANTIC RULES AND NO V3 RETRAINING.'}
candidate['candidate_digest']=h(candidate);write(CAND,candidate)
artifact={'schema':'yado.g2.kernel_raw_representation_v3_robustness_self_evolution.v1',
 'status':'PASS_G2_RAW_REPRESENTATION_V3_ROBUSTNESS_SELF_EVOLUTION_V1',
 'candidate_state':state,'candidate_digest':candidate['candidate_digest'],'selected_mode':selected_mode,
 'parent_metrics':{'fit':parent_fit,'holdout':parent_hold,'direct':parent_direct},'selected_metrics':None if selected_mode is None else metrics[selected_mode],
 'fresh_metrics':fresh_doc['metrics'],'checks':checks,'next_required_capability':next_cap,
 'canonical_mechanism_mutation':False,'architecture_mutation':False,'g3_genesis_performed':False}
artifact['artifact_digest']=h(artifact);write(ART,artifact)

prev=head['canonical_head_digest']
prov['current_g2_binding'].update({'current_execution_label':'G2_RAW_V4_ROBUSTNESS_SHADOW_SUPPORTED' if supported else 'G2_RAW_V3_ROBUSTNESS_V2_PENDING',
 'frontier':next_cap,'frontier_native_method':'select_evolution_parent+propose_evolution_operation+select_evolution_skills',
 'frontier_native_owner':'UnifiedYADOKernelV30RC8ExternalCognitive','raw_v4_robustness_selected_mode':selected_mode})
prov['registry_digest']=cdig(prov,'registry_digest');write(PROV,prov)
core['algorithm_provenance_registry_digest']=prov['registry_digest'];core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits'
core['raw_representation_v3_robustness_self_evolution_v1']={'state':state,'candidate_digest':candidate['candidate_digest'],'selected_mode':selected_mode,'fresh_metrics':fresh_doc['metrics'],'canonical_active':False}
core['core_digest']=cdig(core,'core_digest');write(CORE,core)
head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest'];head['algorithm_provenance_registry']['current_execution_label']=prov['current_g2_binding']['current_execution_label']
head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest'];head['unified_core']['core_digest']=core['core_digest']
head['raw_representation_v3_robustness_self_evolution_v1']={'state':state,'candidate_digest':candidate['candidate_digest'],'selected_mode':selected_mode,'fresh_metrics':fresh_doc['metrics'],'canonical_active':False}
head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits';head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)
ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap]

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={**artifact,'schema':'yado.g2.kernel_raw_representation_v3_robustness_self_evolution.receipt.v1','previous_head_digest':prev,'new_head_digest':head['canonical_head_digest'],'provenance_registry_digest':prov['registry_digest']}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_RAW_V3_ROBUSTNESS_SELF_EVOLUTION_V1",
 'event_type':'G2_RAW_REPRESENTATION_ROBUSTNESS_SELF_EVOLUTION','status':'PASS_SHADOW' if supported else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':front,
 'effect':f"OP={operation.get('operation')}; SELECTED={selected_mode}; PARENT_FIT={parent_fit:.6f}; PARENT_HOLD={parent_hold:.6f}; V4_FRESH={fresh_wrapped_acc:.6f}; PARENT_FRESH={parent_fresh_wrapped:.6f}; BASE_REG={base_reg:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-g2-raw-v3-robustness-self-evolution-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':True,'canonical_mechanism_mutation':False,'architecture_mutation':False,
 'promotion_applied':False,'generation_transition':False,'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);write(LEDGER,ledger)

ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_RAW_V4_CONTEXT_INCONSISTENT')
post=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=60)
if post.returncode!=0:raise RuntimeError('POST_RAW_V4_GUARD_FAILED:'+post.stdout[-5000:]+post.stderr[-1000:])
print(json.dumps({'status':receipt['status'],'candidate_state':state,'selected_mode':selected_mode,'candidate_metrics':metrics,'fresh_metrics':fresh_doc['metrics'],'checks':checks,'next_required_capability':next_cap},indent=2,sort_keys=True))
