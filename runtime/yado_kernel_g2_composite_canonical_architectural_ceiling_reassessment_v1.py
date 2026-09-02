from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,subprocess,sys

ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_bounded_capability_router_v1 import BoundedCapabilityRouterLearnerV1
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
OLD_PLATEAU=REPO/'receipts/yado-g2-lti-empirical-plateau-confirmation-v1-run-33504316236.json'
BURN=REPO/'receipts/yado-g2-composite-canonical-burnin-v1-run-33665203676.json'
ART=REPO/'architecture/yado-kernel-g2-composite-canonical-architectural-ceiling-reassessment-v1.json'
DATA=REPO/'resources/yado-g2-post-composite-ceiling-raw-boundary-v1.json'
OUT=ROOT/'yado_kernel_g2_composite_canonical_architectural_ceiling_reassessment_v1_receipt.json'
GUARD=ROOT/'yado_canonical_invariant_guard_v1.py'

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):
    x=copy.deepcopy(o);x.pop(field,None);return h(x)
def log(stage,**kw):print(json.dumps({'stage':stage,**kw},sort_keys=True,default=str),flush=True)

head,core_doc,ledger,prov,old_plateau,burn=map(load,[HEAD,CORE,LEDGER,PROV,OLD_PLATEAU,BURN])
validate_ledger_v2(ledger)
front='KERNEL_G2_COMPOSITE_CANONICAL_ARCHITECTURAL_CEILING_REASSESSMENT_V1'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if burn.get('status')!='PASS_G2_COMPOSITE_CANONICAL_BURNIN_V1':raise RuntimeError('CANONICAL_BURNIN_NOT_PASS')
if head.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')
if head.get('architecture_family')!='TYPED_RECURRENT_CAPABILITY_GRAPH':raise RuntimeError('ARCHITECTURE_FAMILY_DRIFT')

# Generic structured router used only downstream of the already-canonical raw representation.
router_rows=[]
for i,label in enumerate([CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES]*160):
    x={'budget_limited':label==CAP_BUD,'quota_limited':False,'external_evidence_needed':label==CAP_RES,
       'relation_needed':label==CAP_REL,'disjunction_needed':False,'noise':i}
    router_rows.append({'input':x,'expected':label})
router=BoundedCapabilityRouterLearnerV1.synthesize(router_rows,router_rows,CAP_CONJ,min_support=8)
ucore=UnifiedYADOCoreV1(REPO)

# New post-composite cross-domain boundary set. It deliberately mixes vocabulary
# from competing classes; expected labels are semantic task requirements, not keywords.
blind=[
("Ignore the remaining compute allowance: the release is valid only when provenance, rollback readiness, and signature verification all succeed together.",CAP_CONJ),
("Even with public documentation available, acceptance still requires every mandatory safety gate to be true.",CAP_CONJ),
("Do not schedule another diagnostic; decide the commit only from the simultaneous truth of integrity, freshness, and recovery readiness.",CAP_CONJ),
("One failed prerequisite is enough to block the candidate, even though ownership information is present.",CAP_CONJ),
("The decision is an all-of requirement across validation, causal evidence, and rollback, not a search-budget problem.",CAP_CONJ),
("Before using external sources, check whether all three required approval conditions hold at once.",CAP_CONJ),
("No relation between identities matters here: commit iff each required independent gate passes.",CAP_CONJ),
("Although several tests have costs, this question asks only whether all mandatory booleans are satisfied.",CAP_CONJ),
("Withhold if any required invariant is false; there is no optimization over stages.",CAP_CONJ),
("The candidate survives only when integrity, verification, and restore readiness are jointly true.",CAP_CONJ),
("Treat this as conjunction of mandatory conditions rather than evidence acquisition.",CAP_CONJ),
("External references and quotas are distractions; every prerequisite must pass for acceptance.",CAP_CONJ),

("Budget is irrelevant here: determine whether requester and registered owner are identical or linked by the authorized group relation.",CAP_REL),
("Before any outside lookup, decide permission from actor-owner equality and membership edges.",CAP_REL),
("All scalar checks may pass, but authorization still depends on who owns the object and how the principals are related.",CAP_REL),
("Do not optimize stages; infer access from identity equality, team membership, and verified role.",CAP_REL),
("The required reasoning is over links between account, tenant, owner, and asset rather than independent gates.",CAP_REL),
("Resolve whether two named entities denote the same principal or share the required organizational relation.",CAP_REL),
("Even under a tight compute limit, the decision criterion is the relation between claimant and owner.",CAP_REL),
("Public documentation is available, but the requested result follows from ownership and membership structure.",CAP_REL),
("Infer permission from relational structure: same owner, same group, or verified leadership.",CAP_REL),
("This is not all-of boolean acceptance; compare identifiers and membership edges to decide access.",CAP_REL),
("Determine whether the subject belongs to the resource owner or its authorized cohort.",CAP_REL),
("The outcome changes when entity equality or group links change, regardless of remaining credits.",CAP_REL),

("All checks are individually well-defined; choose which verification stage to run next given cost, quota, and remaining credits.",CAP_BUD),
("No ownership decision is requested: schedule evidence-gathering stages under a hard compute ceiling.",CAP_BUD),
("The prerequisites are known; optimize the next diagnostic sequence so confidence rises without overspending.",CAP_BUD),
("Select among cheap and deep tests using expected gain, latency, quota, and remaining budget.",CAP_BUD),
("Even though every candidate stage is valid, only some sequences fit the available allowance.",CAP_BUD),
("Plan escalation after previous checks while respecting both spent resources and remaining quota.",CAP_BUD),
("Do not merely ask whether all gates pass; choose an affordable order of investigations.",CAP_BUD),
("Entity relations are irrelevant: allocate finite compute among tests with different evidence gains.",CAP_BUD),
("Pick the least-cost sequence that can reach the target confidence under the current resource cap.",CAP_BUD),
("Choose the next experiment after accounting for attempted stages, cost, and quota.",CAP_BUD),
("The task is resource-constrained planning over verification stages, not external document retrieval.",CAP_BUD),
("Determine what to run next when deeper checks provide more evidence but consume more of the finite budget.",CAP_BUD),

("Do not infer the missing fact from local ownership data; retrieve a current public reference that can resolve it.",CAP_RES),
("All local gates are satisfied but the decisive specification is absent, so consult an external authoritative source.",CAP_RES),
("Instead of scheduling more internal diagnostics, obtain current vendor documentation for the unresolved behavior.",CAP_RES),
("The relation among local entities is known; what is missing is outside evidence from a public standard.",CAP_RES),
("A hard budget exists, but local reasoning cannot answer the question without a current external source.",CAP_RES),
("Use an outside scientific or technical reference because the repository contains no evidence for the required fact.",CAP_RES),
("The next action is retrieval of public documentation, not another local inference step.",CAP_RES),
("Resolve the uncertainty by consulting a current external specification rather than guessing from stored state.",CAP_RES),
("Local validation and rollback checks do not establish the missing fact; fetch an authoritative reference.",CAP_RES),
("Find a current public source that settles the issue before making the decision.",CAP_RES),
("The information gap is external to the system, so acquire evidence beyond the local memory and codebase.",CAP_RES),
("Do not choose among internal tests; obtain the missing fact from an eligible outside resource.",CAP_RES),
]
rows=[]
for text,expected in blind:
    out=ucore.route_raw_task(text,router)
    got=out['selected_capability']
    rows.append({'text':text,'expected':expected,'got':got,'representation':out['representation']['capability'],'correct':got==expected})
raw_fresh=sum(x['correct'] for x in rows)/len(rows)

scores={
 'RAW_TASK_REPRESENTATION_CROSS_DOMAIN':raw_fresh,
 'THINKING_BOUNDARY':float(head.get('extended_capability_scores',{}).get('thinking_boundary',0.0)),
 'THINKING_CORE':float(head.get('capability_scores',{}).get('thinking',0.0)),
 'LOGIC_CORE':float(head.get('capability_scores',{}).get('logic',0.0)),
 'INTELLIGENCE_CORE':float(head.get('capability_scores',{}).get('intelligence',0.0)),
 'COMPOSITE_CANONICAL_BURNIN':min(
   float(burn.get('min_metrics',{}).get('explicit_accuracy',0)),
   float(burn.get('min_metrics',{}).get('ambiguous_accuracy',0)),
   float(burn.get('min_metrics',{}).get('sequential_accuracy',0)),
   float(burn.get('min_metrics',{}).get('budget_accuracy',0)),
   float(burn.get('min_metrics',{}).get('lru_recent_accuracy',0))
 ),
 'PROGRAM_EXECUTION':float(core_doc.get('program_execution',{}).get('fresh_score',0.0)),
 'SCIENCE_REASONING':float(core_doc.get('science_reasoning',{}).get('fresh_score',0.0)),
}
records=[]
for name,score in scores.items():
    gap=max(0.0,1.0-float(score))
    records.append({
      'variant_id':'DEFICIT_'+name,'parent_id':None,'lineage_id':'G2_POST_COMPOSITE_CEILING',
      'artifact_digest':h({'name':name,'score':score,'head':head['canonical_head_digest']}),
      'task_scores':{'deficit_priority':gap},
      'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
      'traits':{'measured_score':score,'residual_gap':gap},
      'failure_tags':['below_0_985_gate'] if score<.985 else [],
      'status':'EVALUATED'
    })

kernel=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_ceiling_reassessment_v1.sqlite'))
try:
    selected=kernel.select_evolution_parent(records,'residual_deficit_priority')
    operation=kernel.propose_evolution_operation(records,selected['variant_id'],'architectural_ceiling_reassessment')
finally:
    kernel.close()
selected_id=selected['variant_id']
selected_name=selected_id.removeprefix('DEFICIT_')
selected_score=scores[selected_name]
gap=1.0-selected_score
log('kernel_reassessment',scores=scores,selected=selected,operation=operation)

threshold=.985
ceiling_reconfirmed=all(v>=threshold for v in scores.values())
if ceiling_reconfirmed:
    next_cap='KERNEL_G2_POST_COMPOSITE_OPEN_ENDED_NOVELTY_PROBE_V1'
    verdict='LOCAL_CEILING_RECONFIRMED_BUT_NOT_ABSOLUTE'
else:
    if selected_name=='RAW_TASK_REPRESENTATION_CROSS_DOMAIN':
        next_cap='KERNEL_G2_RAW_REPRESENTATION_POST_COMPOSITE_SELF_EVOLUTION_V1'
    elif selected_name.startswith('THINKING'):
        next_cap='KERNEL_G2_THINKING_POST_COMPOSITE_SELF_EVOLUTION_V1'
    elif selected_name=='PROGRAM_EXECUTION':
        next_cap='KERNEL_G2_PROGRAM_EXECUTION_POST_COMPOSITE_SELF_EVOLUTION_V1'
    elif selected_name=='SCIENCE_REASONING':
        next_cap='KERNEL_G2_SCIENCE_REASONING_POST_COMPOSITE_SELF_EVOLUTION_V1'
    else:
        next_cap='KERNEL_G2_GENERAL_RESIDUAL_SELF_EVOLUTION_V1'
    verdict='CEILING_NOT_REACHED_RESIDUAL_G2_DEFICIT'

dataset={'schema':'yado.g2.post_composite_ceiling.raw_boundary.v1','status':'SPENT_AFTER_CEILING_REASSESSMENT',
 'head_digest_fixed_before_boundary':head['canonical_head_digest'],'task_count':len(rows),'raw_accuracy':raw_fresh,'rows':rows}
dataset['dataset_digest']=cdig(dataset,'dataset_digest');write(DATA,dataset)

artifact={
 'schema':'yado.g2.composite_canonical_architectural_ceiling_reassessment.v1',
 'status':'PASS_G2_COMPOSITE_CANONICAL_ARCHITECTURAL_CEILING_REASSESSMENT_V1',
 'verdict':verdict,'threshold':threshold,'scores':scores,
 'kernel_selected_residual':selected_name,'kernel_selected_score':selected_score,'kernel_selected_gap':gap,
 'kernel_evolution_operation':operation,'old_empirical_plateau_status':old_plateau.get('status'),
 'old_empirical_plateau_absolute_ceiling_claimed':old_plateau.get('absolute_ceiling_claimed'),
 'old_empirical_plateau_head_digest':old_plateau.get('canonical_head_digest'),
 'current_head_before_reassessment':head['canonical_head_digest'],
 'old_plateau_reused_as_absolute_evidence':False,
 'fresh_boundary_dataset_digest':dataset['dataset_digest'],
 'canonical_mutation':True,'canonical_mechanism_mutation':False,'architecture_mutation':False,
 'generation_transition':False,'g3_genesis_performed':False,'next_required_capability':next_cap,
 'semantic_boundary':'POST-COMPOSITE REASSESSMENT OF THE EMPIRICAL LOCAL G2 CEILING. THE KERNEL PRIORITIZES THE LARGEST MEASURED RESIDUAL GAP. THIS DOES NOT CLAIM AN ABSOLUTE COMPUTATIONAL LIMIT, AGI, OR SUBJECTIVE CONSCIOUSNESS.'
}
artifact['artifact_digest']=h(artifact);write(ART,artifact)

prev=head['canonical_head_digest']
prov['current_g2_binding'].update({
 'current_execution_label':'G2_POST_COMPOSITE_RESIDUAL_'+selected_name,
 'frontier':next_cap,'frontier_native_method':'select_evolution_parent+propose_evolution_operation',
 'frontier_native_owner':'UnifiedYADOKernelV30RC8ExternalCognitive',
 'post_composite_ceiling_verdict':verdict,'kernel_selected_residual':selected_name
})
prov['registry_digest']=cdig(prov,'registry_digest');write(PROV,prov)
core_doc['algorithm_provenance_registry_digest']=prov['registry_digest'];core_doc['current_frontier']=next_cap;core_doc['frontier_source']='architecture/evolution-ledger.json:open_deficits'
core_doc['post_composite_architectural_ceiling_reassessment_v1']={
 'verdict':verdict,'scores':scores,'selected_residual':selected_name,'selected_gap':gap,
 'fresh_boundary_dataset_digest':dataset['dataset_digest'],'architecture_mutation':False}
core_doc['core_digest']=cdig(core_doc,'core_digest');write(CORE,core_doc)
head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest'];head['algorithm_provenance_registry']['current_execution_label']=prov['current_g2_binding']['current_execution_label']
head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest'];head['unified_core']['core_digest']=core_doc['core_digest']
head['post_composite_architectural_ceiling_reassessment_v1']={
 'verdict':verdict,'scores':scores,'selected_residual':selected_name,'selected_gap':gap,'architecture_mutation':False}
head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits';head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)
ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap]

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={**artifact,'schema':'yado.g2.composite_canonical_architectural_ceiling_reassessment.receipt.v1',
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest'],'provenance_registry_digest':prov['registry_digest']}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_POST_COMPOSITE_ARCHITECTURAL_CEILING_REASSESSMENT_V1",
 'event_type':'G2_POST_COMPOSITE_ARCHITECTURAL_CEILING_REASSESSMENT','status':'PASS',
 'generation':ledger['current_head'],'deficit':front,
 'effect':f"VERDICT={verdict}; SELECTED={selected_name}; SCORE={selected_score:.6f}; GAP={gap:.6f}; OP={operation.get('operation')}; G3=False; NEXT={next_cap}",
 'source_path':f'receipts/yado-g2-post-composite-architectural-ceiling-reassessment-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':True,'canonical_mechanism_mutation':False,'architecture_mutation':False,
 'promotion_applied':False,'generation_transition':False,'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);write(LEDGER,ledger)

ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_REASSESSMENT_CONTEXT_INCONSISTENT')
post=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=60)
if post.returncode!=0:raise RuntimeError('POST_REASSESSMENT_GUARD_FAILED:'+post.stdout[-4000:]+post.stderr[-1000:])
print(json.dumps({'status':receipt['status'],'verdict':verdict,'scores':scores,'selected_residual':selected_name,'selected_gap':gap,'kernel_operation':operation,'next_required_capability':next_cap},indent=2,sort_keys=True))
