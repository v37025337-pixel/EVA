from __future__ import annotations
from pathlib import Path
import copy,hashlib,importlib.util,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(PKG))

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_raw_task_representation_learner_v1 import RawTaskRepresentationLearnerV1
from yado_raw_task_representation_runtime_v1 import RawTaskRepresentationRuntimeV1
from yado_bounded_capability_router_v1 import BoundedCapabilityRouterLearnerV1

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
CORE=REPO/'canonical'/'yado-unified-core-v1.json'
RUNTIME=REPO/'runtime'/'yado_unified_core_v1.py'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
AUDIT=REPO/'receipts'/'yado-unified-core-deep-self-audit-v1-run-33391906770.json'
REAL=REPO/'receipts'/'yado-g2-real-world-transfer-benchmark-v1-run-33363995201.json'
CAND=REPO/'candidates'/'g2-self-repair'/'raw-task-representation-v1.json'
ADMIT=REPO/'receipts'/'yado-raw-task-representation-fresh-admission-v1-run-33391307653.json'
ART=REPO/'canonical'/'yado-raw-task-representation-v1.json'
OUT=ROOT/'yado_raw_task_representation_canonical_integration_v1_receipt.json'

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

head=load(HEAD);core=load(CORE);ledger=load(LEDGER);audit=load(AUDIT);real=load(REAL);cand=load(CAND);admit=load(ADMIT)
validate_ledger_v2(ledger)
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
if audit.get('self_selected_next_step')!='RAW_TASK_REPRESENTATION_GAP':raise RuntimeError('KERNEL_PRIORITY_NOT_RAW')
binding=next(x for x in audit['findings'] if x['code']=='RUNTIME_CONTROL_PLANE_BINDING')
if binding.get('status')!='PASS':raise RuntimeError('CONTROL_PLANE_NOT_REPAIRED')
if cand.get('state')!='AUTHORIZED_FOR_SHADOW_REPAIR':raise RuntimeError('RAW_CANDIDATE_NOT_AUTHORIZED')
if admit.get('status')!='PASS_G2_RAW_TASK_REPRESENTATION_FRESH_ADMISSION_V1':raise RuntimeError('RAW_FRESH_ADMISSION_NOT_PASS')
if cand.get('learner_family')!='CHAR_NGRAM_CENTROID':raise RuntimeError('UNEXPECTED_SELECTED_FAMILY')

head_before=fsha(HEAD);runtime_before=fsha(RUNTIME)

# Reconstruct exactly the admitted learned model from its original training provenance.
rows=[(x['raw_text'],x['expected']) for x in real['raw_unstructured']['rows']]
by={}
for text,label in rows:by.setdefault(label,[]).append(text)
train=[]
for label in sorted(by):train.extend((x,label) for x in by[label][:3])
spec=RawTaskRepresentationLearnerV1.fit(train,cand['learner_family'])
model={'family':spec.family,'labels':spec.labels,'payload':spec.payload}
model_digest=h(model)

artifact={
 'schema':'yado.g2.raw_task_representation.canonical.v1',
 'component_id':'ALG-G2-RAW-TASK-REPRESENTATION-V1',
 'family':'LEARNED_RAW_TEXT_TO_CAPABILITY_ROUTING_DESCRIPTOR',
 'generation':ledger['current_head'],
 'parent_head_digest':head['canonical_head_digest'],
 'learner_family':cand['learner_family'],
 'training_provenance':{
   'source_receipt':'receipts/yado-g2-real-world-transfer-benchmark-v1-run-33363995201.json',
   'training_count':len(train),
   'shadow_candidate_digest':cand['candidate_digest'],
   'fresh_admission_receipt_sha256':admit['receipt_sha256'],
 },
 'model':model,'model_digest':model_digest,
 'fresh_admission_metrics':admit['metrics'],
 'canonical_active':True,
 'claim_boundary':'BOUNDED RAW-TEXT CAPABILITY ROUTING; NOT GENERAL LANGUAGE UNDERSTANDING OR ENTITY-LEVEL SEMANTIC GROUNDING.'
}
artifact['component_digest']=h(artifact)

# Build bounded unified-core source patch.
src=RUNTIME.read_text(encoding='utf-8')
patched=src
import_anchor="from yado_g2_contextual_stream_capability_adapter_v1 import ContextualStreamCapabilityAdapterV1"
import_line=import_anchor+"\nfrom yado_raw_task_representation_runtime_v1 import RawTaskRepresentationRuntimeV1"
if "from yado_raw_task_representation_runtime_v1 import RawTaskRepresentationRuntimeV1" not in patched:
    patched=patched.replace(import_anchor,import_line)

init_anchor="        self.shadow_context=self._load('candidates/g2-development/contextual-stream-capability-adapter-v1.json')"
init_line=init_anchor+"\n        self.raw_representation=RawTaskRepresentationRuntimeV1.from_path(self.repo/'canonical/yado-raw-task-representation-v1.json')"
if "self.raw_representation=RawTaskRepresentationRuntimeV1" not in patched:
    patched=patched.replace(init_anchor,init_line)

method_anchor="    def instantiate_runtime(self,router_program,scalar_program,relation_program,enable_shadow_context:bool=True):"
methods=(
"    def represent_raw_task(self,raw_text:str)->dict[str,Any]:\n"
"        return self.raw_representation.descriptor(raw_text)\n\n"
"    def route_raw_task(self,raw_text:str,router_program)->dict[str,Any]:\n"
"        rep=self.represent_raw_task(raw_text)\n"
"        selected=router_program.execute(rep['routing_descriptor'])\n"
"        return {'representation':rep,'selected_capability':selected}\n\n"
+method_anchor)
if "    def represent_raw_task(" not in patched:
    patched=patched.replace(method_anchor,methods)

# Ensure patch changed only expected integration points.
allowed_markers=[
 'from yado_raw_task_representation_runtime_v1 import RawTaskRepresentationRuntimeV1',
 "self.raw_representation=RawTaskRepresentationRuntimeV1.from_path(self.repo/'canonical/yado-raw-task-representation-v1.json')",
 'def represent_raw_task','def route_raw_task'
]
patch_markers_present=all(m in patched for m in allowed_markers)
control_plane_preserved=(
 "self.manifest=self._load('canonical/yado-unified-core-v1.json')" in patched and
 "self.experience=self._load('canonical/yado-unified-experience-registry-v1.json')" in patched
)

# Ephemeral artifact + candidate module for fresh end-to-end validation.
ART.write_text(json.dumps(artifact,indent=2,sort_keys=True)+'\n')
tmp=ROOT/'_raw_integration_candidate_unified_core.py'
tmp.write_text(patched,encoding='utf-8')

def route_label(x):
    if x['budget_limited'] or x['quota_limited']:return CAP_BUD
    if x['external_evidence_needed']:return CAP_RES
    if x['relation_needed'] or x['disjunction_needed']:return CAP_REL
    return CAP_CONJ
router_rows=[]
for i,label in enumerate([CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES]*100):
    x={'budget_limited':label==CAP_BUD,'quota_limited':False,'external_evidence_needed':label==CAP_RES,
       'relation_needed':label==CAP_REL,'disjunction_needed':False,'noise':i}
    router_rows.append({'input':x,'expected':label})
router=BoundedCapabilityRouterLearnerV1.synthesize(router_rows,router_rows,CAP_CONJ,min_support=8)

smoke=[
("All mandatory integrity, recovery, and verification gates must pass together before acceptance.",CAP_CONJ),
("Determine whether the service principal owns the object or belongs to its authorized group.",CAP_REL),
("Choose the next diagnostic under a fixed credit limit and remaining quota.",CAP_BUD),
("Local evidence is incomplete, so consult current public documentation.",CAP_RES),
("One failed prerequisite is enough to keep the candidate on hold.",CAP_CONJ),
("Permission depends on actor-owner identity and membership relationships.",CAP_REL),
("Find the cheapest staged search that reaches the required confidence without overspending.",CAP_BUD),
("Retrieve an outside reference because internal information cannot settle the issue.",CAP_RES),
("Accept only if provenance, validation, and rollback readiness all hold.",CAP_CONJ),
("Reason over ownership and team links between the named entities.",CAP_REL),
("Allocate finite compute among checks with different expected gains.",CAP_BUD),
("Use an external public source to fill the missing evidence.",CAP_RES),
]
try:
    specmod=importlib.util.spec_from_file_location('_raw_integration_candidate_unified_core',tmp)
    mod=importlib.util.module_from_spec(specmod);specmod.loader.exec_module(mod)
    obj=mod.UnifiedYADOCoreV1(REPO)
    smoke_rows=[]
    for text,expected in smoke:
        got=obj.route_raw_task(text,router)
        smoke_rows.append({'text':text,'expected':expected,'got':got['selected_capability'],'representation':got['representation']['capability']})
    smoke_acc=sum(x['got']==x['expected'] for x in smoke_rows)/len(smoke_rows)
    candidate_audit=obj.audit()
finally:
    try:tmp.unlink()
    except FileNotFoundError:pass

checks={
 'kernel_priority_raw':True,
 'control_plane_binding_preserved':control_plane_preserved,
 'patch_markers_present':patch_markers_present,
 'artifact_model_digest_valid':artifact['model_digest']==h(artifact['model']),
 'component_digest_valid':artifact['component_digest']==h({k:v for k,v in artifact.items() if k!='component_digest'}),
 'unified_core_candidate_audit_pass':candidate_audit.get('pass') is True,
 'fresh_unified_core_raw_smoke':smoke_acc>=.83,
 'head_immutable_before_commit':fsha(HEAD)==head_before and fsha(RUNTIME)==runtime_before,
}
passed=all(checks.values())

post_head=None;post_core=None
if passed:
    # Apply the already-tested source.
    RUNTIME.write_text(patched,encoding='utf-8')
    runtime_sha=fsha(RUNTIME)

    new_core=copy.deepcopy(core);new_core.pop('core_digest',None)
    planes=new_core.get('planes',[])
    rep_plane=next(x for x in planes if x.get('plane_id')=='REPRESENTATION_AND_GROUNDING')
    rep_plane['active_components']=sorted(set(rep_plane.get('active_components',[])+['ALG-G2-RAW-TASK-REPRESENTATION-V1']))
    rep_plane['status']='ACTIVE_BOUNDED'
    rep_plane['frontier']='REAL_WORLD_TRANSFER_RECHECK'
    new_core['active_runtime_sources']=sorted(set(new_core.get('active_runtime_sources',[])+[
      'runtime/yado_raw_task_representation_learner_v1.py',
      'runtime/yado_raw_task_representation_runtime_v1.py'
    ]))
    new_core['runtime_sha256']=runtime_sha
    new_core['raw_task_representation']={
      'component_id':'ALG-G2-RAW-TASK-REPRESENTATION-V1',
      'component_digest':artifact['component_digest'],
      'model_digest':artifact['model_digest'],
      'admission_run_id':str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
    }
    new_core['current_frontier']='G2_REAL_WORLD_TRANSFER_RECHECK_WITH_CANONICAL_REPRESENTATION_V1'
    new_core['core_digest']=h(new_core);CORE.write_text(json.dumps(new_core,indent=2,sort_keys=True)+'\n')

    new_head=copy.deepcopy(head);new_head.pop('canonical_head_digest',None)
    new_head['new_capabilities']=sorted(set(new_head.get('new_capabilities',[])+['ALG-G2-RAW-TASK-REPRESENTATION-V1']))
    new_head.setdefault('extended_capability_scores',{})['raw_task_representation_cross_domain']=admit['metrics']['cross_domain_raw_accuracy']
    new_head['unified_core']['runtime_sha256']=runtime_sha
    new_head['unified_core']['core_digest']=new_core['core_digest']
    new_head['unified_core']['raw_task_representation_component_digest']=artifact['component_digest']
    new_head['current_frontier']='G2_REAL_WORLD_TRANSFER_RECHECK_WITH_CANONICAL_REPRESENTATION_V1'
    new_head['canonical_head_digest']=h(new_head);HEAD.write_text(json.dumps(new_head,indent=2,sort_keys=True)+'\n')
    post_head=new_head['canonical_head_digest'];post_core=new_core['core_digest']
    status='PASS_G2_RAW_TASK_REPRESENTATION_CANONICAL_INTEGRATION_V1'
    next_cap='G2_REAL_WORLD_TRANSFER_RECHECK_WITH_CANONICAL_REPRESENTATION_V1'
else:
    # Remove ephemeral canonical artifact if integration is withheld.
    try:ART.unlink()
    except FileNotFoundError:pass
    status='WITHHOLD_G2_RAW_TASK_REPRESENTATION_CANONICAL_INTEGRATION_V1'
    next_cap='G2_RAW_TASK_REPRESENTATION_EXPRESSIVENESS_GAP_V1'

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
 'schema':'yado.g2.raw_task_representation_canonical_integration.receipt.v1',
 'status':status,'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),
 'candidate_digest':cand['candidate_digest'],'fresh_admission_receipt':admit['receipt_sha256'],
 'component_digest':artifact['component_digest'] if passed else None,
 'model_digest':artifact['model_digest'] if passed else None,
 'smoke_accuracy':smoke_acc,'smoke_rows':smoke_rows,'checks':checks,
 'canonical_mutation':passed,'promotion_applied':False,'generation_transition':False,
 'post_core_digest':post_core,'post_head_digest':post_head,'next_required_capability':next_cap,
 'semantic_boundary':'SAME-GENERATION BOUNDED RAW-TEXT ROUTING COMPONENT INTEGRATION. DOES NOT CLAIM GENERAL LANGUAGE UNDERSTANDING, FULL SEMANTIC GROUNDING, OR AGI.'
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_RAW_REPRESENTATION_CANONICAL_INTEGRATION",
   'event_type':'GENERATION_INTERNAL_SELF_REPAIR_ADMISSION','status':'PASS' if passed else 'WITHHOLD',
   'generation':ledger['current_head'],'deficit':'RAW_TASK_REPRESENTATION_GAP',
   'effect':'RAW_TASK_REPRESENTATION_BOUND_TO_UNIFIED_CORE' if passed else 'RAW_TASK_REPRESENTATION_CANONICAL_INTEGRATION_WITHHELD',
   'source_path':f'receipts/yado-raw-task-representation-canonical-integration-v1-run-{run_id}.json',
   'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
   'canonical_mutation':passed,'promotion_applied':False,'generation_transition':False}
if passed:
    e['previous_head_digest']=ledger['current_head_digest'];e['new_head_digest']=post_head
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
if passed:ledger['current_head_digest']=post_head
ledger['open_deficits']=[next_cap]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({'status':status,'smoke_accuracy':smoke_acc,'checks':checks,
 'post_head_digest':post_head,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('RAW_REPRESENTATION_CANONICAL_INTEGRATION_WITHHELD')
