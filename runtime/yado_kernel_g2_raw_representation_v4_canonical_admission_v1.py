from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,subprocess,sys

ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_raw_task_representation_candidate_v3 import RawTaskRepresentationRuntimeV3
from yado_raw_task_representation_robustness_v4 import RobustRawTaskRepresentationRuntimeV4
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
V3ART=REPO/'canonical/yado-raw-task-representation-v3.json'
CAND=REPO/'candidates/kernel-self-generated/raw-task-representation-v4-robustness-v2.json'
PREV=REPO/'resources/yado-raw-task-representation-v4-robustness-fresh-holdout-v2.json'
BASE=REPO/'receipts/yado-g2-real-world-transfer-benchmark-v1-run-33363995201.json'
CANON=REPO/'canonical/yado-raw-task-representation-v4.json'
FRESH=REPO/'resources/yado-raw-task-representation-v4-canonical-admission-fresh-v1.json'
OUT=ROOT/'yado_kernel_g2_raw_representation_v4_canonical_admission_v1_receipt.json'
GUARD=ROOT/'yado_canonical_invariant_guard_v1.py'
UNIFIED=ROOT/'yado_unified_core_v1.py'
V4SRC=ROOT/'yado_raw_task_representation_robustness_v4.py'
V3SRC=ROOT/'yado_raw_task_representation_candidate_v3.py'

V3='ALG-G2-RAW-TASK-REPRESENTATION-V3';V4='ALG-G2-RAW-TASK-REPRESENTATION-V4'
C1='ALG-CONJUNCTIVE-RULE-INDUCER-V1';CR='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1';CB='ALG-BUDGETED-STAGE-POLICY-V1';CE='RESOURCE-PORTFOLIO-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):x=copy.deepcopy(o);x.pop(field,None);return h(x)
def acc(rows,pred):return sum(pred(x)==y for x,y in rows)/max(1,len(rows))

head,core,ledger,prov,v3,cand,prev,base=map(load,[HEAD,CORE,LEDGER,PROV,V3ART,CAND,PREV,BASE]);validate_ledger_v2(ledger)
front='KERNEL_G2_RAW_REPRESENTATION_V4_CANONICAL_ADMISSION_V1'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if cand.get('state')!='SHADOW_V4_ROBUSTNESS_SUPPORTED':raise RuntimeError('V4_NOT_SHADOW_SUPPORTED')
if cand.get('candidate_digest')!='973444a994300c959e2971c24cd6f4fe4a44842a169e254550c100a9851fdbd4':raise RuntimeError('V4_CANDIDATE_DRIFT')
if cand.get('selected_mode')!='MULTIVIEW_EDGE_TIE_CORE':raise RuntimeError('V4_MODE_DRIFT')
if V3 not in head.get('active_capabilities',[]):raise RuntimeError('V3_NOT_ACTIVE_PARENT')
if head.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')

parent=RawTaskRepresentationRuntimeV3(v3)
child=RobustRawTaskRepresentationRuntimeV4(v3,cand['selected_mode'])

fresh_base=[
("Authorize release only when signature, validation, and rollback readiness all succeed.",C1),
("The manual is attached, but every mandatory readiness condition must still pass.",C1),
("One failed prerequisite blocks the operation even though ownership data exists.",C1),
("No search is requested; decide whether all compulsory checks are true.",C1),
("This is an all-of safety gate, not a relation problem.",C1),
("Proceed iff every independent safeguard succeeds together.",C1),
("Budget metadata is present, but acceptance depends only on all required invariants.",C1),
("The candidate remains withheld unless each mandatory condition holds.",C1),

("Access depends on requester-owner identity and approved-group membership.",CR),
("Remaining compute is irrelevant; infer permission from principal and role relations.",CR),
("All independent safeguards pass, yet authorization still depends on ownership links.",CR),
("Determine whether the claimant belongs to the owner's permitted cohort.",CR),
("Resolve whether two identifiers denote the same principal or an authorized relation.",CR),
("The result changes with entity equality and membership edges, not with budget.",CR),
("This is relational access control rather than an all-of gate.",CR),
("Infer permission from ownership, tenant, group, and verified-role structure.",CR),

("Choose the next diagnostic under a hard compute allowance.",CB),
("Allocate remaining credits among tests with different expected gains.",CB),
("Ownership is resolved; select an affordable sequence of verification stages.",CB),
("Pick the next experiment from cost, quota, latency, and expected evidence gain.",CB),
("Plan deeper checks without exceeding remaining resources.",CB),
("Choose the least-cost sequence capable of reaching target confidence.",CB),
("This is staged evidence gathering under resource constraints.",CB),
("Select what to run next after accounting for spent budget.",CB),

("Local evidence cannot establish the missing fact; retrieve a current authoritative source.",CE),
("All ownership relations are known, but the absent rule must come from public documentation.",CE),
("Do not run another local test; obtain the missing specification externally.",CE),
("A budget remains, yet the decisive fact lies outside local state.",CE),
("Consult a current technical reference because internal evidence is insufficient.",CE),
("The repository lacks the governing fact, so retrieve an outside source.",CE),
("The next action is external evidence acquisition rather than local inference.",CE),
("Fetch a trustworthy public reference to resolve the information gap.",CE),
]

def wrap(text,i):
    m=i%4
    if m==0:return f"[audit={i%23}] {text} [done={900+i}]"
    if m==1:return f"<routing {i%17}> {text} <closed>"
    if m==2:return f"{{session {i%19}}} {text} {{complete}}"
    return f"Memo {i%13}: {text} [tail={700+i}]"

fresh=[(wrap(x,i),y) for i,(x,y) in enumerate(fresh_base)]
parent_fresh=acc(fresh,parent.predict_capability);child_fresh=acc(fresh,child.predict_capability)
parent_plain=acc(fresh_base,parent.predict_capability);child_plain=acc(fresh_base,child.predict_capability)
prev_rows=[(r['wrapped'],r['expected']) for r in prev['rows']]
prev_repro=acc(prev_rows,child.predict_capability)
base_rows=[(r['raw_text'],r['expected']) for r in base['raw_unstructured']['rows']]
base_reg=acc(base_rows,child.predict_capability)

skills=[
 {'skill_id':'KEEP_RAW_V3','artifact_digest':v3['component_digest'],'structural_valid':True,'semantic_consistency':1.0,
  'fit_baseline':float(prev['metrics']['parent_fresh_wrapped']),'fit_candidate':float(prev['metrics']['parent_fresh_wrapped']),
  'heldout_baseline':parent_fresh,'heldout_candidate':parent_fresh,'regression_pass':True,'state_integrity':True,'rollback_available':True},
 {'skill_id':'ADMIT_ROBUST_RAW_V4','artifact_digest':cand['candidate_digest'],'structural_valid':True,'semantic_consistency':1.0,
  'fit_baseline':float(prev['metrics']['parent_fresh_wrapped']),'fit_candidate':float(prev['metrics']['fresh_wrapped_accuracy']),
  'heldout_baseline':parent_fresh,'heldout_candidate':child_fresh,
  'regression_pass':prev_repro>=.97 and base_reg>=.95 and child_plain>=.95,'state_integrity':True,'rollback_available':True}
]
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_raw_v4_admission.sqlite'))
try:selection=k.select_evolution_skills(skills,max_skills=1,min_semantic_consistency=.90,min_fit_gain=.05,max_heldout_drop=0,min_heldout_gain=.04)
finally:k.close()
selected=(selection.get('selected_skill_ids') or [None])[0]

metrics={
 'parent_fresh_wrapped':parent_fresh,'v4_fresh_wrapped':child_fresh,
 'parent_fresh_plain':parent_plain,'v4_fresh_plain':child_plain,
 'previous_v4_fresh_reproduction':prev_repro,'base_regression_accuracy':base_reg
}
checks={
 'candidate_fixed_before_fresh':cand['candidate_digest']=='973444a994300c959e2971c24cd6f4fe4a44842a169e254550c100a9851fdbd4',
 'kernel_selects_v4':selected=='ADMIT_ROBUST_RAW_V4',
 'fresh_wrapped_accuracy':child_fresh>=.95,
 'fresh_wrapped_gain':child_fresh-parent_fresh>=.05,
 'fresh_plain_accuracy':child_plain>=.95,
 'previous_v4_fresh_reproduction':prev_repro>=.97,
 'base_regression':base_reg>=.95,
 'v3_rollback_available':v3.get('canonical_active') is True,
 'architecture_family_unchanged':head.get('architecture_family')=='TYPED_RECURRENT_CAPABILITY_GRAPH',
 'g3_not_started':head.get('g3_genesis_performed') is False
}
admit=all(checks.values())
next_cap='KERNEL_G2_RAW_REPRESENTATION_V4_POST_ADMISSION_AUDIT_V1' if admit else 'KERNEL_G2_RAW_REPRESENTATION_V3_ROBUSTNESS_SELF_EVOLUTION_V3'

fresh_doc={'schema':'yado.g2.raw_task_representation_v4.canonical_admission_fresh.v1','status':'SPENT_AFTER_SINGLE_V4_CANONICAL_ADMISSION',
 'candidate_digest_fixed_before_fresh':cand['candidate_digest'],'task_count':len(fresh),'metrics':metrics,
 'rows':[{'text':x,'expected':y,'parent':parent.predict_capability(x),'v4':child.predict_capability(x),'v4_correct':child.predict_capability(x)==y} for x,y in fresh]}
fresh_doc['dataset_digest']=cdig(fresh_doc,'dataset_digest');write(FRESH,fresh_doc)

canonical_art=None
if admit:
    canonical_art={
      'schema':'yado.g2.raw_task_representation.canonical.v4','canonical_active':True,
      'component_id':V4,'supersedes':V3,'historical_parent_artifact':'canonical/yado-raw-task-representation-v3.json',
      'family':'ROBUST_STRUCTURAL_RAW_TEXT_TO_CAPABILITY_ROUTING_DESCRIPTOR_V4',
      'selected_mode':cand['selected_mode'],
      'parent_component_digest':v3['component_digest'],'parent_model_digest':v3['model_digest'],
      'runtime_source':'runtime/yado_raw_task_representation_robustness_v4.py','runtime_sha256':fsha(V4SRC),
      'source_candidate_digest':cand['candidate_digest'],'admission_metrics':metrics,
      'fresh_admission_dataset_digest':fresh_doc['dataset_digest'],
      'claim_boundary':'BOUNDED GENERIC WRAPPER-INVARIANT RAW-TEXT CAPABILITY ROUTING V4 OVER STRUCTURAL V3; NOT GENERAL LANGUAGE UNDERSTANDING.'
    }
    canonical_art['component_digest']=cdig(canonical_art,'component_digest');write(CANON,canonical_art)

prev_head=head['canonical_head_digest']
if admit:
    src=UNIFIED.read_text(encoding='utf-8')
    old_import='from yado_raw_task_representation_candidate_v3 import RawTaskRepresentationRuntimeV3'
    new_import='from yado_raw_task_representation_robustness_v4 import RobustRawTaskRepresentationRuntimeV4'
    old_init="self.raw_representation=RawTaskRepresentationRuntimeV3(self._load('canonical/yado-raw-task-representation-v3.json'))"
    new_init="self.raw_representation=RobustRawTaskRepresentationRuntimeV4(self._load('canonical/yado-raw-task-representation-v3.json'), self._load('canonical/yado-raw-task-representation-v4.json')['selected_mode'])"
    if old_import not in src or old_init not in src:raise RuntimeError('UNIFIED_V3_BINDING_ANCHOR_MISSING')
    src=src.replace(old_import,new_import).replace(old_init,new_init);UNIFIED.write_text(src,encoding='utf-8');unified_sha=fsha(UNIFIED)

    plane=next((p for p in core.get('planes',[]) if p.get('plane_id')=='REPRESENTATION_AND_GROUNDING'),None)
    if plane is None:raise RuntimeError('REPRESENTATION_PLANE_MISSING')
    plane['active_components']=sorted(set(V4 if x==V3 else x for x in plane.get('active_components',[])))
    plane['frontier']='POST_COMPOSITE_ROBUST_RAW_REPRESENTATION_V4'

    core['active_runtime_sources']=sorted(set(core.get('active_runtime_sources',[])+['runtime/yado_raw_task_representation_robustness_v4.py','runtime/yado_raw_task_representation_candidate_v3.py']))
    rim=core.get('runtime_integrity_manifest',{})
    if not isinstance(rim.get('sources'),dict):raise RuntimeError('RUNTIME_MANIFEST_MISSING')
    rim['sources']['runtime/yado_raw_task_representation_candidate_v3.py']=fsha(V3SRC)
    rim['sources']['runtime/yado_raw_task_representation_robustness_v4.py']=fsha(V4SRC)
    rim['sources']={k:rim['sources'][k] for k in sorted(rim['sources'])};rim['manifest_digest']=h(rim['sources'])

    core['raw_task_representation']={
      'component_id':V4,'component_digest':canonical_art['component_digest'],'admission_run_id':str(os.getenv('GITHUB_RUN_ID') or 'LOCAL'),
      'supersedes':V3,'selected_mode':cand['selected_mode'],'parent_component_id':V3,'parent_component_digest':v3['component_digest'],
      'parent_model_digest':v3['model_digest']
    }
    if not any(x.get('component_id')==V3 for x in core.get('superseded_components',[])):
      core.setdefault('superseded_components',[]).append({'component_id':V3,'superseded_by':V4,'historical_evidence_retained':True,
       'reason':'V3_SEMANTIC_BOUNDARY_REACHED_1_0_BUT_WRAPPER_PERTURBATION_STABILITY_REMAINED_0_925; V4_GENERIC_EDGE_MULTIVIEW_PASSED_FRESH_ADMISSION'})
    core['runtime_sha256']=unified_sha

    head['active_capabilities']=sorted(set(V4 if x==V3 else x for x in head.get('active_capabilities',[])))
    head['new_capabilities']=sorted(set(head.get('new_capabilities',[])+[V4]))
    head['raw_task_representation_v4']={'status':'CANONICAL_ACTIVE','component_id':V4,'component_digest':canonical_art['component_digest'],
      'supersedes':V3,'selected_mode':cand['selected_mode'],'parent_component_digest':v3['component_digest'],'admission_metrics':metrics}
    head['unified_core']['raw_task_representation_component_digest']=canonical_art['component_digest']
    head['unified_core']['runtime_sha256']=unified_sha
    head['unified_core']['runtime_integrity_manifest_digest']=rim['manifest_digest']

prov['current_g2_binding'].update({
 'current_execution_label':'G2_ROBUST_RAW_REPRESENTATION_V4_CANONICAL' if admit else 'G2_RAW_V3_ROBUSTNESS_V3_PENDING',
 'frontier':next_cap,'frontier_native_method':'select_evolution_skills','frontier_native_owner':'UnifiedYADOKernelV30RC8ExternalCognitive',
 'raw_representation_active_component':V4 if admit else V3,'raw_v4_selected_mode':cand['selected_mode'],
 'raw_v4_candidate_digest':cand['candidate_digest']
})
prov['registry_digest']=cdig(prov,'registry_digest');write(PROV,prov)

core['algorithm_provenance_registry_digest']=prov['registry_digest'];core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits'
core['raw_representation_v4_canonical_admission_v1']={'status':'CANONICAL_ACTIVE' if admit else 'WITHHOLD','candidate_digest':cand['candidate_digest'],'selected_skill_id':selected,'metrics':metrics,'canonical_mechanism_mutation':admit}
core['core_digest']=cdig(core,'core_digest');write(CORE,core)

head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest'];head['algorithm_provenance_registry']['current_execution_label']=prov['current_g2_binding']['current_execution_label']
head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest'];head['unified_core']['core_digest']=core['core_digest']
head['raw_representation_v4_canonical_admission_v1']={'status':'CANONICAL_ACTIVE' if admit else 'WITHHOLD','candidate_digest':cand['candidate_digest'],'metrics':metrics}
head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits';head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)

ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap]
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.raw_representation_v4_canonical_admission.receipt.v1',
 'status':'PASS_G2_RAW_REPRESENTATION_V4_CANONICAL_ADMISSION_V1' if admit else 'WITHHOLD_G2_RAW_REPRESENTATION_V4_CANONICAL_ADMISSION_V1',
 'candidate_digest':cand['candidate_digest'],'selected_skill_id':selected,'selected_mode':cand['selected_mode'],'kernel_selection':selection,
 'metrics':metrics,'checks':checks,'fresh_dataset_digest':fresh_doc['dataset_digest'],
 'canonical_component_digest':None if canonical_art is None else canonical_art['component_digest'],
 'previous_head_digest':prev_head,'new_head_digest':head['canonical_head_digest'],
 'canonical_mechanism_mutation':admit,'architecture_mutation':False,'generation_transition':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,'semantic_boundary':'INDEPENDENT FRESH CANONICAL ADMISSION OF GENERIC WRAPPER-INVARIANT RAW ROUTING V4 OVER V3. SAME-G2 COMPONENT REPLACEMENT; V3 REMAINS ROLLBACK.'
}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_RAW_REPRESENTATION_V4_CANONICAL_ADMISSION_V1",
 'event_type':'G2_ROBUST_RAW_REPRESENTATION_CANONICAL_ADMISSION','status':'PASS_CANONICAL' if admit else 'WITHHOLD','generation':ledger['current_head'],'deficit':front,
 'effect':f"SELECTED={selected}; MODE={cand['selected_mode']}; PARENT_FRESH={parent_fresh:.6f}; V4_FRESH={child_fresh:.6f}; PLAIN={child_plain:.6f}; PREV_REPRO={prev_repro:.6f}; BASE_REG={base_reg:.6f}; CANONICAL={admit}; G3=False; NEXT={next_cap}",
 'source_path':f'receipts/yado-g2-raw-representation-v4-canonical-admission-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':True,'canonical_mechanism_mutation':admit,'architecture_mutation':False,'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':prev_head,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);write(LEDGER,ledger)

ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_V4_ADMISSION_CONTEXT_INCONSISTENT')
post=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=60)
if post.returncode!=0:raise RuntimeError('POST_V4_ADMISSION_GUARD_FAILED:'+post.stdout[-5000:]+post.stderr[-1000:])
print(json.dumps({'status':receipt['status'],'selected':selected,'metrics':metrics,'checks':checks,'next_required_capability':next_cap},indent=2,sort_keys=True))
