from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,subprocess,sys

ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_raw_task_representation_runtime_v1 import RawTaskRepresentationRuntimeV1
from yado_raw_task_representation_candidate_v2 import RawTaskRepresentationRuntimeV2
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json';CORE=REPO/'canonical/yado-unified-core-v1.json';LEDGER=REPO/'architecture/evolution-ledger.json'
PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json';RAW_V1=REPO/'canonical/yado-raw-task-representation-v1.json'
CAND=REPO/'candidates/kernel-self-generated/raw-task-representation-v2.json';PREV_FRESH=REPO/'resources/yado-raw-task-representation-v2-fresh-holdout-v1.json'
CANON_V2=REPO/'canonical/yado-raw-task-representation-v2.json';BASE=REPO/'receipts/yado-g2-real-world-transfer-benchmark-v1-run-33363995201.json'
OUT=ROOT/'yado_kernel_g2_raw_representation_v2_canonical_admission_v1_receipt.json';GUARD=ROOT/'yado_canonical_invariant_guard_v1.py'
UNIFIED=ROOT/'yado_unified_core_v1.py';V2_SRC=ROOT/'yado_raw_task_representation_candidate_v2.py'

V1='ALG-G2-RAW-TASK-REPRESENTATION-V1';V2='ALG-G2-RAW-TASK-REPRESENTATION-V2'
CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1';CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1';CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1';CAP_RES='RESOURCE-PORTFOLIO-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):
    x=copy.deepcopy(o);x.pop(field,None);return h(x)
def acc(rows,pred):return sum(pred(x)==y for x,y in rows)/max(1,len(rows))
def log(stage,**kw):print(json.dumps({'stage':stage,**kw},sort_keys=True,default=str),flush=True)

head,core,ledger,prov,raw_v1,cand,prev_fresh,base=map(load,[HEAD,CORE,LEDGER,PROV,RAW_V1,CAND,PREV_FRESH,BASE])
validate_ledger_v2(ledger)
front='KERNEL_G2_RAW_REPRESENTATION_V2_CANONICAL_ADMISSION_V1'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if cand.get('state')!='SHADOW_V2_SUPPORTED':raise RuntimeError('RAW_V2_NOT_SHADOW_SUPPORTED')
if cand.get('component_id')!=V2:raise RuntimeError('RAW_V2_COMPONENT_ID_MISMATCH')
if head.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')
if V1 not in head.get('active_capabilities',[]):raise RuntimeError('RAW_V1_NOT_ACTIVE_PARENT')

parent=RawTaskRepresentationRuntimeV1(raw_v1)
child=RawTaskRepresentationRuntimeV2(cand)

fresh=[
# CONJ
("A nuclear maintenance action may proceed only when radiation clearance, identity verification, and rollback readiness all pass; vendor manuals are already present.",CAP_CONJ),
("The insurance payout is approved iff policy validity, fraud screening, and beneficiary verification all succeed together.",CAP_CONJ),
("A factory line restart remains blocked when any mandatory safety interlock, calibration check, or recovery condition is false.",CAP_CONJ),
("Do not allocate more compute: the question is simply whether every required compliance condition is satisfied.",CAP_CONJ),
("Although ownership and cost fields are included, acceptance depends only on all required audit gates being true.",CAP_CONJ),
("The aviation release is valid only after maintenance signoff, route clearance, and restore readiness jointly pass.",CAP_CONJ),
("External standards have been read already; commit exactly when integrity, validation, and recovery prerequisites all hold.",CAP_CONJ),
("This is a mandatory all-of decision across three safeguards, not a relationship or search-stage task.",CAP_CONJ),
("A genomic result is publishable only if consent, sample identity, and quality validation are all confirmed.",CAP_CONJ),
("One failed required condition is enough to withhold the transaction despite remaining budget.",CAP_CONJ),
("Proceed iff each independent readiness predicate is true; otherwise stop.",CAP_CONJ),
("No outside fact is missing: evaluate the conjunction of the mandatory acceptance conditions.",CAP_CONJ),

# REL
("For an energy grid control object, determine whether the operator is its owner, belongs to the authorized station group, or holds the verified control role.",CAP_REL),
("The insurance record can be accessed based on claimant-owner identity and approved-agent membership relations.",CAP_REL),
("Ignore the compute budget; decide whether the two identifiers name the same legal entity or share the required organizational link.",CAP_REL),
("Every scalar safety check passes, but permission still depends on who owns the asset and how the principals are related.",CAP_REL),
("The public standard is known; authorization must be inferred from account, tenant, owner, and role links.",CAP_REL),
("Resolve whether the maintenance engineer belongs to the aircraft's authorized service group.",CAP_REL),
("The outcome follows entity equality and membership edges rather than the number of credits available.",CAP_REL),
("Determine access from relational structure among researcher, dataset owner, institution, and verified role.",CAP_REL),
("This is an ownership and group-membership question, not an all-gates acceptance decision.",CAP_REL),
("Even though an external reference is cited, no lookup is needed; compare principal and ownership relations.",CAP_REL),
("Infer whether the requester and protected resource are connected by the required identity or cohort relation.",CAP_REL),
("A quota value is present, but it does not determine permission; the entity links do.",CAP_REL),

# BUDGET
("Choose which grid diagnostic to execute next under a fixed outage-response budget and differing expected information gains.",CAP_BUD),
("Schedule aircraft inspections so confidence can reach the target without exceeding remaining maintenance credits.",CAP_BUD),
("Ownership has already been resolved; now choose an affordable sequence of fraud checks under quota.",CAP_BUD),
("Several genomic analyses are valid but have different costs; allocate the finite compute allowance among them.",CAP_BUD),
("Do not ask whether every gate is true; choose the next experiment based on cost and expected evidence gain.",CAP_BUD),
("Public documents are already available, yet the task is to plan deeper tests within remaining resources.",CAP_BUD),
("Find the least costly verification sequence capable of reaching the required confidence.",CAP_BUD),
("Plan the next diagnostic after previous attempts while respecting remaining quota and budget.",CAP_BUD),
("Identity relationships are irrelevant here; optimize the order of staged investigations.",CAP_BUD),
("Allocate limited observation time among measurements with different costs and expected gains.",CAP_BUD),
("Select the next review stage without exceeding the remaining resource ceiling.",CAP_BUD),
("The objective is bounded search planning, not retrieval of an outside fact.",CAP_BUD),

# RESOURCE
("The reactor log does not contain the decisive material limit, so retrieve a current authoritative engineering reference.",CAP_RES),
("Local insurance records cannot establish the applicable regulation; consult a current public legal source.",CAP_RES),
("All ownership relationships are known, but the missing specification must come from external aviation documentation.",CAP_RES),
("Do not run another genomic analysis: obtain the unresolved reference value from a public scientific source.",CAP_RES),
("A compute budget remains, yet no local test can establish the missing vendor behavior; retrieve the documentation.",CAP_RES),
("Find an outside energy standard because the repository lacks the fact required for the decision.",CAP_RES),
("The next step is external evidence acquisition rather than additional local inference.",CAP_RES),
("Consult a current authoritative source beyond stored memory to resolve the uncertainty.",CAP_RES),
("Local validation has passed, but the unknown requirement must be verified from public documentation.",CAP_RES),
("Use an eligible outside reference because internal evidence is insufficient.",CAP_RES),
("Do not choose among internal stages; fetch the missing rule from a trustworthy external source.",CAP_RES),
("The unresolved information is external to the system, so retrieve it before deciding.",CAP_RES),
]
traps=[
("The description mentions public standards and owners, but acceptance still requires every mandatory safety gate to pass.",CAP_CONJ),
("A cost cap is listed, yet access is determined by claimant-owner equality and authorized membership.",CAP_REL),
("The stage is called external-review, but the actual task is to choose an affordable sequence of checks.",CAP_BUD),
("Ownership and quotas are known; the missing fact still has to be fetched from a current public specification.",CAP_RES),
("Team information is present, but this decision is only whether all required readiness conditions are true.",CAP_CONJ),
("All checks are green and a manual is attached; permission nevertheless depends on identity relations.",CAP_REL),
("No fact is missing; allocate the remaining compute among diagnostic stages.",CAP_BUD),
("There is remaining budget, but local tests cannot reveal the absent standard, so retrieve it externally.",CAP_RES),
("Ignore search terminology: every independent prerequisite must succeed for release.",CAP_CONJ),
("Do not evaluate a conjunction; determine access from owner and group links.",CAP_REL),
("External sources are already available; optimize the next test under cost and quota.",CAP_BUD),
("The ticket includes owner and cost metadata, but the answer requires an outside authoritative reference.",CAP_RES),
]
parent_fresh=acc(fresh,parent.predict_capability);child_fresh=acc(fresh,child.predict_capability)
parent_trap=acc(traps,parent.predict_capability);child_trap=acc(traps,child.predict_capability)

def perturb(text,i):
    pre=("Audit packet: ","New case: ","Operator message: ","Review request: ")[i%4]
    post=(" [ticket=R17]","; unrelated id 442"," -- severity medium"," [source-local]")[i%4]
    return pre+(text.upper() if i%2==0 else text.lower())+post
pert=[(perturb(x,i),y) for i,(x,y) in enumerate(fresh)]
child_pert=acc(pert,child.predict_capability)

prior_rows=[(r['text'],r['expected']) for r in prev_fresh['rows']]
prior_repro=acc(prior_rows,child.predict_capability)
base_rows=[(r['raw_text'],r['expected']) for r in base['raw_unstructured']['rows']]
base_reg=acc(base_rows,child.predict_capability)

skills=[
 {'skill_id':'KEEP_RAW_V1','artifact_digest':raw_v1['component_digest'],'structural_valid':True,'semantic_consistency':1.0,
  'fit_baseline':float(prev_fresh['metrics']['parent_fresh_accuracy']),'fit_candidate':float(prev_fresh['metrics']['parent_fresh_accuracy']),
  'heldout_baseline':parent_fresh,'heldout_candidate':parent_fresh,'regression_pass':True,'state_integrity':True,'rollback_available':True},
 {'skill_id':'ADMIT_RAW_V2','artifact_digest':cand['candidate_digest'],'structural_valid':True,'semantic_consistency':1.0,
  'fit_baseline':float(prev_fresh['metrics']['parent_fresh_accuracy']),'fit_candidate':float(prev_fresh['metrics']['fresh_accuracy']),
  'heldout_baseline':parent_fresh,'heldout_candidate':child_fresh,
  'regression_pass':prior_repro>=.93 and base_reg>=.95,'state_integrity':True,'rollback_available':True}
]
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_raw_v2_admission.sqlite'))
try:
    selection=k.select_evolution_skills(skills,max_skills=1,min_semantic_consistency=.90,min_fit_gain=.05,max_heldout_drop=0.0,min_heldout_gain=.05)
finally:k.close()
selected=(selection.get('selected_skill_ids') or [None])[0]

checks={
 'candidate_fixed_before_fresh_v3':cand.get('candidate_digest')=='0581c3341eb045137ccaab0eda31e4bfb839fbdc381195d3795e9bea831697ae',
 'kernel_selects_v2':selected=='ADMIT_RAW_V2',
 'fresh_v3_accuracy':child_fresh>=.90,
 'fresh_v3_gain':child_fresh-parent_fresh>=.05,
 'fresh_v3_traps':child_trap>=.80,
 'fresh_v3_perturbation':child_pert>=.85,
 'previous_fresh_reproduction':prior_repro>=.93,
 'base_regression':base_reg>=.95,
 'rollback_parent_available':raw_v1.get('canonical_active') is True,
 'architecture_family_unchanged':head.get('architecture_family')=='TYPED_RECURRENT_CAPABILITY_GRAPH',
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
admit=all(checks.values())
next_cap='KERNEL_G2_RAW_REPRESENTATION_V2_POST_ADMISSION_AUDIT_V1' if admit else 'KERNEL_G2_RAW_REPRESENTATION_POST_COMPOSITE_SELF_EVOLUTION_V2'
metrics={'parent_fresh_v3':parent_fresh,'v2_fresh_v3':child_fresh,'parent_trap_v3':parent_trap,'v2_trap_v3':child_trap,
         'v2_perturbation_v3':child_pert,'previous_fresh_reproduction':prior_repro,'base_regression_accuracy':base_reg}

canonical_art=None
if admit:
    canonical_art={
      'schema':'yado.g2.raw_task_representation.canonical.v2','canonical_active':True,
      'component_id':V2,'supersedes':V1,'historical_parent_artifact':'canonical/yado-raw-task-representation-v1.json',
      'family':'LEARNED_RAW_TEXT_TO_CAPABILITY_ROUTING_DESCRIPTOR_V2','learner_family':cand['learner_family'],
      'model':cand['model'],'model_digest':h(cand['model']),
      'source_candidate_digest':cand['candidate_digest'],'candidate_runtime_source':'runtime/yado_raw_task_representation_candidate_v2.py',
      'candidate_runtime_sha256':fsha(V2_SRC),'admission_metrics':metrics,
      'fresh_v2_dataset_digest':cand['fresh_dataset_digest'],
      'claim_boundary':'BOUNDED RAW-TEXT CAPABILITY ROUTING V2; NOT GENERAL LANGUAGE UNDERSTANDING OR ENTITY-LEVEL SEMANTIC GROUNDING.'
    }
    canonical_art['component_digest']=cdig(canonical_art,'component_digest');write(CANON_V2,canonical_art)

prev=head['canonical_head_digest']
if admit:
    src=UNIFIED.read_text(encoding='utf-8')
    old_import='from yado_raw_task_representation_runtime_v1 import RawTaskRepresentationRuntimeV1'
    new_import='from yado_raw_task_representation_candidate_v2 import RawTaskRepresentationRuntimeV2'
    old_init="self.raw_representation=RawTaskRepresentationRuntimeV1.from_path(self.repo/'canonical/yado-raw-task-representation-v1.json')"
    new_init="self.raw_representation=RawTaskRepresentationRuntimeV2(self._load('canonical/yado-raw-task-representation-v2.json'))"
    if old_import not in src or old_init not in src:raise RuntimeError('UNIFIED_RAW_V1_BINDING_ANCHOR_MISSING')
    src=src.replace(old_import,new_import).replace(old_init,new_init)
    UNIFIED.write_text(src,encoding='utf-8')
    unified_sha=fsha(UNIFIED)

    # Replace active component in representation plane.
    plane=next((p for p in core.get('planes',[]) if p.get('plane_id')=='REPRESENTATION_AND_GROUNDING'),None)
    if plane is None:raise RuntimeError('REPRESENTATION_PLANE_MISSING')
    plane['active_components']=sorted(V2 if x==V1 else x for x in plane.get('active_components',[]))
    if V2 not in plane['active_components']:plane['active_components'].append(V2);plane['active_components']=sorted(set(plane['active_components']))
    plane['frontier']='POST_COMPOSITE_RAW_REPRESENTATION_V2'

    # Active runtime source swap + hash manifest.
    old_sources={'runtime/yado_raw_task_representation_learner_v1.py','runtime/yado_raw_task_representation_runtime_v1.py'}
    core['active_runtime_sources']=sorted([x for x in core.get('active_runtime_sources',[]) if x not in old_sources]+['runtime/yado_raw_task_representation_candidate_v2.py'])
    rim=core.get('runtime_integrity_manifest',{})
    if not isinstance(rim.get('sources'),dict):raise RuntimeError('RUNTIME_MANIFEST_MISSING')
    for x in old_sources:rim['sources'].pop(x,None)
    rim['sources']['runtime/yado_raw_task_representation_candidate_v2.py']=fsha(V2_SRC)
    rim['sources']={k:rim['sources'][k] for k in sorted(rim['sources'])};rim['manifest_digest']=h(rim['sources'])

    # Canonical semantic binding.
    core['raw_task_representation']={'component_id':V2,'component_digest':canonical_art['component_digest'],'model_digest':canonical_art['model_digest'],
                                     'admission_run_id':str(os.getenv('GITHUB_RUN_ID') or 'LOCAL'),'supersedes':V1}
    if not any(x.get('component_id')==V1 for x in core.get('superseded_components',[])):
        core.setdefault('superseded_components',[]).append({'component_id':V1,'superseded_by':V2,'historical_evidence_retained':True,
          'reason':'POST_COMPOSITE_CROSS_DOMAIN_RAW_BOUNDARY_EXPOSED_V1_LEXICAL_DISTRACTOR_LIMIT; V2 PASSED INDEPENDENT FRESH ADMISSION'})
    core['runtime_sha256']=unified_sha
    head['active_capabilities']=sorted(V2 if x==V1 else x for x in head.get('active_capabilities',[]))
    head['new_capabilities']=sorted(set(head.get('new_capabilities',[])+[V2]))
    head['raw_task_representation_v2']={'status':'CANONICAL_ACTIVE','component_id':V2,'component_digest':canonical_art['component_digest'],
       'model_digest':canonical_art['model_digest'],'supersedes':V1,'admission_metrics':metrics}
    head['unified_core']['raw_task_representation_component_digest']=canonical_art['component_digest']
    head['unified_core']['runtime_sha256']=unified_sha
    head['unified_core']['runtime_integrity_manifest_digest']=rim['manifest_digest']

prov['current_g2_binding'].update({
 'current_execution_label':'G2_RAW_REPRESENTATION_V2_CANONICAL' if admit else 'G2_RAW_REPRESENTATION_SELF_EVOLUTION_V2_PENDING',
 'frontier':next_cap,'frontier_native_method':'select_evolution_skills',
 'frontier_native_owner':'UnifiedYADOKernelV30RC8ExternalCognitive',
 'raw_representation_active_component':V2 if admit else V1,
 'raw_representation_candidate_digest':cand['candidate_digest']
})
prov['registry_digest']=cdig(prov,'registry_digest');write(PROV,prov)
core['algorithm_provenance_registry_digest']=prov['registry_digest'];core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits'
core['raw_representation_v2_canonical_admission_v1']={'status':'CANONICAL_ACTIVE' if admit else 'WITHHOLD','candidate_digest':cand['candidate_digest'],
 'selected_skill_id':selected,'metrics':metrics,'canonical_mechanism_mutation':admit}
core['core_digest']=cdig(core,'core_digest');write(CORE,core)
head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest'];head['algorithm_provenance_registry']['current_execution_label']=prov['current_g2_binding']['current_execution_label']
head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest'];head['unified_core']['core_digest']=core['core_digest']
head['raw_representation_v2_canonical_admission_v1']={'status':'CANONICAL_ACTIVE' if admit else 'WITHHOLD','candidate_digest':cand['candidate_digest'],'metrics':metrics}
head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits';head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)
ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap]

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
 'schema':'yado.g2.raw_representation_v2_canonical_admission.receipt.v1',
 'status':'PASS_G2_RAW_REPRESENTATION_V2_CANONICAL_ADMISSION_V1' if admit else 'WITHHOLD_G2_RAW_REPRESENTATION_V2_CANONICAL_ADMISSION_V1',
 'candidate_digest':cand['candidate_digest'],'selected_skill_id':selected,'kernel_selection':selection,'metrics':metrics,'checks':checks,
 'canonical_component_digest':None if canonical_art is None else canonical_art['component_digest'],
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest'],'canonical_mechanism_mutation':admit,
 'architecture_mutation':False,'generation_transition':False,'g3_genesis_performed':False,'next_required_capability':next_cap,
 'semantic_boundary':'INDEPENDENT FRESH CANONICAL ADMISSION OF RAW-TEXT ROUTING V2. THIS IS A SAME-G2 REPRESENTATION COMPONENT REPLACEMENT, NOT GENERAL LANGUAGE UNDERSTANDING OR G3.'
}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_RAW_REPRESENTATION_V2_CANONICAL_ADMISSION_V1",
 'event_type':'G2_RAW_REPRESENTATION_CANONICAL_ADMISSION','status':'PASS_CANONICAL' if admit else 'WITHHOLD','generation':ledger['current_head'],'deficit':front,
 'effect':f"SELECTED={selected}; PARENT_FRESH={parent_fresh:.6f}; V2_FRESH={child_fresh:.6f}; TRAP={child_trap:.6f}; PERT={child_pert:.6f}; PRIOR_REPRO={prior_repro:.6f}; CANONICAL={admit}; G3=False; NEXT={next_cap}",
 'source_path':f'receipts/yado-g2-raw-representation-v2-canonical-admission-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':True,'canonical_mechanism_mutation':admit,'architecture_mutation':False,'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);write(LEDGER,ledger)
ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_RAW_V2_ADMISSION_CONTEXT_INCONSISTENT')
post=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=60)
if post.returncode!=0:raise RuntimeError('POST_RAW_V2_ADMISSION_GUARD_FAILED:'+post.stdout[-5000:]+post.stderr[-1000:])
log('complete',admit=admit,selected=selected,metrics=metrics,checks=checks,next=next_cap)
