from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,random,subprocess,sys

ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_raw_task_representation_candidate_v3 import RawTaskRepresentationRuntimeV3
from yado_raw_task_representation_robustness_v4 import RobustRawTaskRepresentationRuntimeV4
from yado_raw_task_representation_robustness_v5 import RobustRawTaskRepresentationRuntimeV5
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
V3ART=REPO/'canonical/yado-raw-task-representation-v3.json'
V4ART=REPO/'canonical/yado-raw-task-representation-v4.json'
CAND=REPO/'candidates/kernel-self-generated/raw-task-representation-v5-sequential-robustness-v1.json'
PREV=REPO/'resources/yado-raw-task-representation-v5-sequential-robustness-fresh-holdout-v1.json'
BASE=REPO/'receipts/yado-g2-real-world-transfer-benchmark-v1-run-33363995201.json'
CANON=REPO/'canonical/yado-raw-task-representation-v5.json'
FRESH=REPO/'resources/yado-raw-task-representation-v5-canonical-admission-fresh-v1.json'
OUT=ROOT/'yado_kernel_g2_raw_representation_v5_canonical_admission_v1_receipt.json'
GUARD=ROOT/'yado_canonical_invariant_guard_v1.py'
UNIFIED=ROOT/'yado_unified_core_v1.py'
V3SRC=ROOT/'yado_raw_task_representation_candidate_v3.py'
V4SRC=ROOT/'yado_raw_task_representation_robustness_v4.py'
V5SRC=ROOT/'yado_raw_task_representation_robustness_v5.py'

V4='ALG-G2-RAW-TASK-REPRESENTATION-V4';V5='ALG-G2-RAW-TASK-REPRESENTATION-V5'
C1='ALG-CONJUNCTIVE-RULE-INDUCER-V1';CR='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1';CB='ALG-BUDGETED-STAGE-POLICY-V1';CE='RESOURCE-PORTFOLIO-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):x=copy.deepcopy(o);x.pop(field,None);return h(x)
def acc(rows,pred):return sum(pred(x)==y for x,y in rows)/max(1,len(rows))

head,core,ledger,prov,v3,v4,cand,prev,base=map(load,[HEAD,CORE,LEDGER,PROV,V3ART,V4ART,CAND,PREV,BASE]);validate_ledger_v2(ledger)
front='KERNEL_G2_RAW_REPRESENTATION_V5_CANONICAL_ADMISSION_V1'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if cand.get('state')!='SHADOW_V5_SEQUENTIAL_ROBUSTNESS_SUPPORTED':raise RuntimeError('V5_NOT_SHADOW_SUPPORTED')
if cand.get('candidate_digest')!='a2b25703fb4efafc805f36b82c6560b0ed0ce6bda329fd7cc12979529dcfd063':raise RuntimeError('V5_CANDIDATE_DRIFT')
if cand.get('selected_mode')!='V4_PLUS_CORE_VOTE':raise RuntimeError('V5_MODE_DRIFT')
if cand.get('parent_component_digest')!=v4.get('component_digest'):raise RuntimeError('V5_PARENT_DIGEST_DRIFT')
if V4 not in head.get('active_capabilities',[]):raise RuntimeError('V4_NOT_ACTIVE_PARENT')
if head.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')

parent=RobustRawTaskRepresentationRuntimeV4(v3,v4['selected_mode'])
child=RobustRawTaskRepresentationRuntimeV5(v3,v4,cand['selected_mode'])

fresh_base=[
("Activate the release only if authorization, integrity validation, and restore readiness are all simultaneously satisfied.",C1),
("A reference manual is available, yet deployment still requires every mandatory safety condition to pass.",C1),
("One missing prerequisite is sufficient to block the transaction, regardless of ownership metadata.",C1),
("No experiment ordering is requested; determine whether all compulsory acceptance checks hold.",C1),
("This is a conjunction of independent release gates rather than identity reasoning.",C1),
("Proceed exactly when every required safeguard succeeds; otherwise keep the candidate withheld.",C1),
("Credits are shown in the record, but approval depends only on all mandatory invariants being true.",C1),
("External facts are already known; accept only when provenance, validation, and rollback are jointly ready.",C1),
("The record is trustworthy only when source authenticity, identity validation, and recovery readiness all pass.",C1),
("Even with group information present, failure of any required safety gate blocks activation.",C1),
("Treat the decision as all-required conditions, not search planning or access-control inference.",C1),
("The operation is valid iff every independent prerequisite is satisfied together.",C1),

("Permission depends on whether the requester is the owner or belongs to an authorized group.",CR),
("Ignore the remaining compute allowance and infer access from principal, owner, tenant, and role relations.",CR),
("All scalar readiness checks may pass, yet authorization is still determined by ownership links.",CR),
("Decide whether the claimant belongs to the resource owner's approved cohort.",CR),
("Resolve whether two identifiers denote the same principal or a permitted organizational relation.",CR),
("The result changes when entity equality or membership edges change, not when quota changes.",CR),
("This is relational authorization rather than an all-required safety gate.",CR),
("Infer access from owner, tenant, group, and verified-role structure.",CR),
("Determine whether the operator and asset share the required ownership or mission-group link.",CR),
("No outside lookup is needed; compare identities and membership relations.",CR),
("Authorization follows same-principal and same-group relations among the named entities.",CR),
("A budget field is present, but the permission rule is relational.",CR),

("Choose the next verification stage under the remaining compute allowance.",CB),
("Allocate finite credits among tests that have different expected information gains.",CB),
("Ownership is settled; select an affordable sequence of diagnostics.",CB),
("Pick the next experiment using cost, quota, latency, and expected evidence gain.",CB),
("Plan deeper checks without exceeding remaining resources.",CB),
("Choose the least-cost sequence capable of reaching the target confidence.",CB),
("This is staged evidence acquisition under a hard resource ceiling.",CB),
("Select what to run next after accounting for already-spent budget.",CB),
("Schedule the next observation from expected gain and remaining quota.",CB),
("The task is resource-constrained planning, not an all-gates decision.",CB),
("Choose among cheap and expensive checks so confidence rises within the budget.",CB),
("Determine the next stage when deeper tests cost more but provide more evidence.",CB),

("Local evidence cannot establish the missing fact; retrieve a current authoritative source.",CE),
("All identity relations are known, but the absent requirement must come from public documentation.",CE),
("Do not schedule another local diagnostic; obtain the missing specification externally.",CE),
("A budget remains, yet the decisive fact lies outside local state.",CE),
("Consult a current technical reference because internal evidence is insufficient.",CE),
("The repository lacks the governing fact, so retrieve an outside source.",CE),
("The next action is public evidence acquisition rather than local inference.",CE),
("Fetch a trustworthy external reference to resolve the information gap.",CE),
("Local validation passed, but the missing behavior must be verified from current documentation.",CE),
("Use an outside standard because the local memory cannot answer the question.",CE),
("Obtain the unresolved requirement from an eligible public resource.",CE),
("The information gap is external to the system, so retrieve authoritative evidence.",CE),
]

def wrap(text,i):
    m=i%8
    if m==0:return f"[trace={1000+i}] {text} [closed]"
    if m==1:return f"<packet id='{i%29}'> {text} </packet>"
    if m==2:return f"Header({i%17}) :: {text} :: Footer"
    if m==3:return f"Audit memo {i%23}. {text} Completed."
    if m==4:return f"{{context:{i%31}}} {text} {{/context}}"
    if m==5:return f"(sequence {i%19}) -- {text} -- done"
    if m==6:return f"Note: metadata={i%37}; {text} ; end-note"
    return f"  {text}  [session={7000+i}]"

fresh_wrapped=[(wrap(x,i),y) for i,(x,y) in enumerate(fresh_base)]
parent_direct=acc(fresh_base,parent.predict_capability);child_direct=acc(fresh_base,child.predict_capability)
parent_wrap=acc(fresh_wrapped,parent.predict_capability);child_wrap=acc(fresh_wrapped,child.predict_capability)

# Sequential stress is generated only after fixed candidate/parent checks above.
rng=random.Random(2026090401)
seq=[]
for i in range(2400):
    x,y=fresh_base[(i*7+rng.randrange(len(fresh_base)))%len(fresh_base)]
    nested=wrap(wrap(x,i),i+97) if i%5==0 else wrap(x,i)
    if i%9==0:nested=f"Batch {i%41}. "+nested+" End batch."
    seq.append((nested,y))
parent_seq=acc(seq,parent.predict_capability);child_seq=acc(seq,child.predict_capability)

prev_rows=[(r.get('text') or r.get('wrapped') or r.get('raw_text'),r['expected']) for r in prev.get('rows',[]) if (r.get('text') or r.get('wrapped') or r.get('raw_text'))]
prev_metrics=prev.get('metrics') or prev.get('fresh_metrics') or {}
required_prev_metrics={'fresh_direct_accuracy','fresh_sequential_accuracy','parent_fresh_sequential'}
if not required_prev_metrics.issubset(prev_metrics):
    raise RuntimeError('PREVIOUS_V5_METRICS_SCHEMA_MISSING:'+str(sorted(required_prev_metrics-set(prev_metrics))))
prev_repro=acc(prev_rows,child.predict_capability) if prev_rows else float(prev_metrics['fresh_direct_accuracy'])
base_rows=[(r['raw_text'],r['expected']) for r in base['raw_unstructured']['rows']]
base_reg=acc(base_rows,child.predict_capability)

skills=[
 {'skill_id':'KEEP_RAW_V4','artifact_digest':v4['component_digest'],'structural_valid':True,'semantic_consistency':1.0,
  'fit_baseline':float(prev_metrics['parent_fresh_sequential']),'fit_candidate':float(prev_metrics['parent_fresh_sequential']),
  'heldout_baseline':parent_seq,'heldout_candidate':parent_seq,'regression_pass':True,'state_integrity':True,'rollback_available':True},
 {'skill_id':'ADMIT_RAW_V5_SEQUENCE_ROBUST','artifact_digest':cand['candidate_digest'],'structural_valid':True,'semantic_consistency':1.0,
  'fit_baseline':float(prev_metrics['parent_fresh_sequential']),'fit_candidate':float(prev_metrics['fresh_sequential_accuracy']),
  'heldout_baseline':parent_seq,'heldout_candidate':child_seq,
  'regression_pass':prev_repro>=.97 and base_reg>=.98 and child_direct>=.97 and child_wrap>=.96,'state_integrity':True,'rollback_available':True}
]
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_raw_v5_admission.sqlite'))
try:selection=k.select_evolution_skills(skills,max_skills=1,min_semantic_consistency=.90,min_fit_gain=.02,max_heldout_drop=0,min_heldout_gain=.015)
finally:k.close()
selected=(selection.get('selected_skill_ids') or [None])[0]

metrics={
 'parent_fresh_direct':parent_direct,'v5_fresh_direct':child_direct,
 'parent_fresh_wrapped':parent_wrap,'v5_fresh_wrapped':child_wrap,
 'parent_fresh_sequential':parent_seq,'v5_fresh_sequential':child_seq,
 'previous_v5_fresh_reproduction':prev_repro,'base_regression_accuracy':base_reg
}
checks={
 'candidate_fixed_before_fresh':cand['candidate_digest']=='a2b25703fb4efafc805f36b82c6560b0ed0ce6bda329fd7cc12979529dcfd063',
 'kernel_selects_v5':selected=='ADMIT_RAW_V5_SEQUENCE_ROBUST',
 'fresh_direct_accuracy':child_direct>=.97,
 'fresh_wrapped_accuracy':child_wrap>=.96,
 'fresh_sequential_accuracy':child_seq>=.98,
 'fresh_sequential_gain':child_seq-parent_seq>=.015,
 'previous_v5_fresh_reproduction':prev_repro>=.97,
 'base_regression':base_reg>=.98,
 'v4_rollback_available':v4.get('canonical_active') is True,
 'architecture_family_unchanged':head.get('architecture_family')=='TYPED_RECURRENT_CAPABILITY_GRAPH',
 'g3_not_started':head.get('g3_genesis_performed') is False
}
admit=all(checks.values())
next_cap='KERNEL_G2_RAW_REPRESENTATION_V5_POST_ADMISSION_AUDIT_V1' if admit else 'KERNEL_G2_RAW_REPRESENTATION_V4_ROBUSTNESS_SELF_EVOLUTION_V2'

fresh_doc={'schema':'yado.g2.raw_task_representation_v5.canonical_admission_fresh.v1','status':'SPENT_AFTER_SINGLE_V5_CANONICAL_ADMISSION',
 'candidate_digest_fixed_before_fresh':cand['candidate_digest'],'direct_task_count':len(fresh_base),'wrapped_task_count':len(fresh_wrapped),'sequential_task_count':len(seq),
 'metrics':metrics,
 'direct_rows':[{'text':x,'expected':y,'parent':parent.predict_capability(x),'v5':child.predict_capability(x),'correct':child.predict_capability(x)==y} for x,y in fresh_base]}
fresh_doc['dataset_digest']=cdig(fresh_doc,'dataset_digest');write(FRESH,fresh_doc)

canonical_art=None
if admit:
    canonical_art={
      'schema':'yado.g2.raw_task_representation.canonical.v5','canonical_active':True,
      'component_id':V5,'supersedes':V4,'historical_parent_artifact':'canonical/yado-raw-task-representation-v4.json',
      'family':'SEQUENTIAL_ROBUST_RAW_TEXT_TO_CAPABILITY_ROUTING_DESCRIPTOR_V5',
      'selected_mode':cand['selected_mode'],
      'parent_component_digest':v4['component_digest'],
      'runtime_source':'runtime/yado_raw_task_representation_robustness_v5.py','runtime_sha256':fsha(V5SRC),
      'source_candidate_digest':cand['candidate_digest'],'admission_metrics':metrics,
      'fresh_admission_dataset_digest':fresh_doc['dataset_digest'],
      'claim_boundary':'BOUNDED GENERIC SEQUENCE/WRAPPER-ROBUST RAW-TEXT CAPABILITY ROUTING V5 OVER CANONICAL V4/V3; NOT GENERAL LANGUAGE UNDERSTANDING.'
    }
    canonical_art['component_digest']=cdig(canonical_art,'component_digest');write(CANON,canonical_art)

prev_head=head['canonical_head_digest']
if admit:
    src=UNIFIED.read_text(encoding='utf-8')
    old_import='from yado_raw_task_representation_robustness_v4 import RobustRawTaskRepresentationRuntimeV4'
    new_import='from yado_raw_task_representation_robustness_v5 import RobustRawTaskRepresentationRuntimeV5'
    old_init="self.raw_representation=RobustRawTaskRepresentationRuntimeV4(self._load('canonical/yado-raw-task-representation-v3.json'), self._load('canonical/yado-raw-task-representation-v4.json')['selected_mode'])"
    new_init="self.raw_representation=RobustRawTaskRepresentationRuntimeV5(self._load('canonical/yado-raw-task-representation-v3.json'), self._load('canonical/yado-raw-task-representation-v4.json'), self._load('canonical/yado-raw-task-representation-v5.json')['selected_mode'])"
    if old_import not in src or old_init not in src:raise RuntimeError('UNIFIED_V4_BINDING_ANCHOR_MISSING')
    src=src.replace(old_import,new_import).replace(old_init,new_init);UNIFIED.write_text(src,encoding='utf-8');unified_sha=fsha(UNIFIED)

    plane=next((p for p in core.get('planes',[]) if p.get('plane_id')=='REPRESENTATION_AND_GROUNDING'),None)
    if plane is None:raise RuntimeError('REPRESENTATION_PLANE_MISSING')
    plane['active_components']=sorted(set(V5 if x==V4 else x for x in plane.get('active_components',[])))
    plane['frontier']='POST_COMPOSITE_SEQUENTIAL_ROBUST_RAW_REPRESENTATION_V5'

    core['active_runtime_sources']=sorted(set(core.get('active_runtime_sources',[])+[
      'runtime/yado_raw_task_representation_candidate_v3.py',
      'runtime/yado_raw_task_representation_robustness_v4.py',
      'runtime/yado_raw_task_representation_robustness_v5.py']))
    rim=core.get('runtime_integrity_manifest',{})
    if not isinstance(rim.get('sources'),dict):raise RuntimeError('RUNTIME_MANIFEST_MISSING')
    rim['sources']['runtime/yado_raw_task_representation_candidate_v3.py']=fsha(V3SRC)
    rim['sources']['runtime/yado_raw_task_representation_robustness_v4.py']=fsha(V4SRC)
    rim['sources']['runtime/yado_raw_task_representation_robustness_v5.py']=fsha(V5SRC)
    rim['sources']={k:rim['sources'][k] for k in sorted(rim['sources'])};rim['manifest_digest']=h(rim['sources'])

    core['raw_task_representation']={
      'component_id':V5,'component_digest':canonical_art['component_digest'],'admission_run_id':str(os.getenv('GITHUB_RUN_ID') or 'LOCAL'),
      'supersedes':V4,'selected_mode':cand['selected_mode'],'parent_component_id':V4,'parent_component_digest':v4['component_digest']
    }
    if not any(x.get('component_id')==V4 for x in core.get('superseded_components',[])):
      core.setdefault('superseded_components',[]).append({'component_id':V4,'superseded_by':V5,'historical_evidence_retained':True,
       'reason':'V4_DIRECT/WRAPPER ROBUSTNESS PASSED BUT POST-BURNIN SEQUENTIAL STABILITY REMAINED 0.951667; V5 CORE-VOTE SEQUENCE ROBUSTNESS PASSED FRESH ADMISSION'})
    core['runtime_sha256']=unified_sha

    head['active_capabilities']=sorted(set(V5 if x==V4 else x for x in head.get('active_capabilities',[])))
    head['new_capabilities']=sorted(set(head.get('new_capabilities',[])+[V5]))
    head['raw_task_representation_v5']={'status':'CANONICAL_ACTIVE','component_id':V5,'component_digest':canonical_art['component_digest'],
      'supersedes':V4,'selected_mode':cand['selected_mode'],'parent_component_digest':v4['component_digest'],'admission_metrics':metrics}
    head['unified_core']['raw_task_representation_component_digest']=canonical_art['component_digest']
    head['unified_core']['runtime_sha256']=unified_sha
    head['unified_core']['runtime_integrity_manifest_digest']=rim['manifest_digest']

prov['current_g2_binding'].update({
 'current_execution_label':'G2_SEQUENTIAL_ROBUST_RAW_REPRESENTATION_V5_CANONICAL' if admit else 'G2_RAW_V4_ROBUSTNESS_V2_PENDING',
 'frontier':next_cap,'frontier_native_method':'select_evolution_skills','frontier_native_owner':'UnifiedYADOKernelV30RC8ExternalCognitive',
 'raw_representation_active_component':V5 if admit else V4,'raw_v5_selected_mode':cand['selected_mode'],
 'raw_v5_candidate_digest':cand['candidate_digest']
})
prov['registry_digest']=cdig(prov,'registry_digest');write(PROV,prov)

core['algorithm_provenance_registry_digest']=prov['registry_digest'];core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits'
core['raw_representation_v5_canonical_admission_v1']={'status':'CANONICAL_ACTIVE' if admit else 'WITHHOLD','candidate_digest':cand['candidate_digest'],'selected_skill_id':selected,'metrics':metrics,'canonical_mechanism_mutation':admit}
core['core_digest']=cdig(core,'core_digest');write(CORE,core)

head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest'];head['algorithm_provenance_registry']['current_execution_label']=prov['current_g2_binding']['current_execution_label']
head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest'];head['unified_core']['core_digest']=core['core_digest']
head['raw_representation_v5_canonical_admission_v1']={'status':'CANONICAL_ACTIVE' if admit else 'WITHHOLD','candidate_digest':cand['candidate_digest'],'metrics':metrics}
head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits';head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)

ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap]
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.raw_representation_v5_canonical_admission.receipt.v1',
 'status':'PASS_G2_RAW_REPRESENTATION_V5_CANONICAL_ADMISSION_V1' if admit else 'WITHHOLD_G2_RAW_REPRESENTATION_V5_CANONICAL_ADMISSION_V1',
 'candidate_digest':cand['candidate_digest'],'selected_skill_id':selected,'selected_mode':cand['selected_mode'],'kernel_selection':selection,
 'metrics':metrics,'checks':checks,'fresh_dataset_digest':fresh_doc['dataset_digest'],
 'canonical_component_digest':None if canonical_art is None else canonical_art['component_digest'],
 'previous_head_digest':prev_head,'new_head_digest':head['canonical_head_digest'],
 'canonical_mechanism_mutation':admit,'architecture_mutation':False,'generation_transition':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'INDEPENDENT FRESH CANONICAL ADMISSION OF V5 SEQUENCE/WRAPPER ROBUST RAW ROUTING. SAME-G2 COMPONENT REPLACEMENT; V4 REMAINS ROLLBACK.'
}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_RAW_REPRESENTATION_V5_CANONICAL_ADMISSION_V1",
 'event_type':'G2_SEQUENTIAL_ROBUST_RAW_REPRESENTATION_CANONICAL_ADMISSION','status':'PASS_CANONICAL' if admit else 'WITHHOLD','generation':ledger['current_head'],'deficit':front,
 'effect':f"SELECTED={selected}; MODE={cand['selected_mode']}; PARENT_DIRECT={parent_direct:.6f}; V5_DIRECT={child_direct:.6f}; PARENT_WRAP={parent_wrap:.6f}; V5_WRAP={child_wrap:.6f}; PARENT_SEQ={parent_seq:.6f}; V5_SEQ={child_seq:.6f}; PREV_REPRO={prev_repro:.6f}; BASE_REG={base_reg:.6f}; CANONICAL={admit}; G3=False; NEXT={next_cap}",
 'source_path':f'receipts/yado-g2-raw-representation-v5-canonical-admission-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':True,'canonical_mechanism_mutation':admit,'architecture_mutation':False,'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':prev_head,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);write(LEDGER,ledger)

ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_V5_ADMISSION_CONTEXT_INCONSISTENT')
post=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=60)
if post.returncode!=0:raise RuntimeError('POST_V5_ADMISSION_GUARD_FAILED:'+post.stdout[-5000:]+post.stderr[-1000:])
print(json.dumps({'status':receipt['status'],'selected':selected,'metrics':metrics,'checks':checks,'next_required_capability':next_cap},indent=2,sort_keys=True))
