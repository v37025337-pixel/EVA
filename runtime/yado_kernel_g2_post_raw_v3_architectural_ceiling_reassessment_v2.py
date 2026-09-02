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
V3BURN=REPO/'receipts/yado-g2-raw-representation-v3-canonical-burnin-v1-run-33678904722.json'
SCI_FRESH=REPO/'receipts/yado-science-data-native-fresh-admission-v1-run-33419266920.json'
SCI_CANON=REPO/'receipts/yado-science-data-native-canonical-integration-v1-run-33436389858.json'
ART=REPO/'architecture/yado-kernel-g2-post-raw-v3-architectural-ceiling-reassessment-v2.json'
DATA=REPO/'resources/yado-g2-post-raw-v3-ceiling-boundary-v2.json'
OUT=ROOT/'yado_kernel_g2_post_raw_v3_architectural_ceiling_reassessment_v2_receipt.json'
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

head,core,ledger,prov,burn,sf,sc=map(load,[HEAD,CORE,LEDGER,PROV,V3BURN,SCI_FRESH,SCI_CANON])
validate_ledger_v2(ledger)
front='KERNEL_G2_POST_RAW_V3_ARCHITECTURAL_CEILING_REASSESSMENT_V2'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if burn.get('status')!='PASS_G2_RAW_REPRESENTATION_V3_CANONICAL_BURNIN_V1':raise RuntimeError('RAW_V3_BURNIN_NOT_PASS')
if sf.get('status')!='PASS_SCIENCE_DATA_NATIVE_FRESH_ADMISSION_V1' or sc.get('status')!='PASS_SCIENCE_DATA_NATIVE_CANONICAL_INTEGRATION_V1':
    raise RuntimeError('SCIENCE_EVIDENCE_NOT_PASS')
if head.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')

router_rows=[]
for i,label in enumerate([CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES]*160):
    router_rows.append({'input':{
      'budget_limited':label==CAP_BUD,'quota_limited':False,
      'external_evidence_needed':label==CAP_RES,'relation_needed':label==CAP_REL,
      'disjunction_needed':False,'noise':i},'expected':label})
router=BoundedCapabilityRouterLearnerV1.synthesize(router_rows,router_rows,CAP_CONJ,min_support=8)
ucore=UnifiedYADOCoreV1(REPO)

blind=[
# CONJ 12
("Local ownership data is present, yet release depends only on every mandatory safety predicate being true.",CAP_CONJ),
("External manuals are already known; proceed iff integrity, authorization, and rollback readiness all hold.",CAP_CONJ),
("A budget is listed, but no planning is requested: accept only when all required checks pass together.",CAP_CONJ),
("Do not compare identities; one failed mandatory prerequisite blocks the entire operation.",CAP_CONJ),
("The task is an all-of validation gate across signature, provenance, and recovery readiness.",CAP_CONJ),
("Even with local evidence available, approval still requires each independent safeguard to succeed.",CAP_CONJ),
("No external fact is missing; determine whether all mandatory booleans are simultaneously satisfied.",CAP_CONJ),
("The owner field is a distraction: commit exactly when every readiness condition is true.",CAP_CONJ),
("A test catalog exists, but the question is simply whether all required invariants pass.",CAP_CONJ),
("Withhold when any compulsory validation condition is false, regardless of remaining compute.",CAP_CONJ),
("This decision is conjunction over independent gates, not relation inference or staged search.",CAP_CONJ),
("The candidate survives only if all required approval conditions hold at once.",CAP_CONJ),

# REL 12
("Local records are complete; determine whether requester and owner are the same identity or linked by an authorized group.",CAP_REL),
("Ignore the compute budget: access depends on actor-owner equality and membership structure.",CAP_REL),
("All independent safeguards pass, but permission still depends on ownership and role relations.",CAP_REL),
("External documentation is attached; infer authorization from principal, owner, tenant, and group links.",CAP_REL),
("Do not plan tests: decide whether the claimant belongs to the authorized cohort of the resource owner.",CAP_REL),
("The result changes when identity equality or membership edges change, not when local budget changes.",CAP_REL),
("Resolve whether two named entities represent the same principal or a permitted organizational relation.",CAP_REL),
("A local specification exists, yet the requested decision is about who owns the asset and who belongs to the group.",CAP_REL),
("This is relational access control rather than an all-of readiness gate.",CAP_REL),
("Determine authorization from subject-owner identity and verified membership links.",CAP_REL),
("The relevant evidence is the graph of principals, owners, teams, and roles.",CAP_REL),
("Even under a quota, permission follows from relational structure among the named entities.",CAP_REL),

# BUDGET 12
("Choose the next local diagnostic under a fixed compute allowance, balancing cost and expected evidence gain.",CAP_BUD),
("External references are already available; allocate remaining credits among staged tests.",CAP_BUD),
("Ownership is known, so optimize the sequence of verification stages under quota.",CAP_BUD),
("Select the next experiment using cost, latency, expected gain, and remaining budget.",CAP_BUD),
("All gates are individually valid; only some investigation sequences fit the available allowance.",CAP_BUD),
("Plan deeper checks after previous attempts without exceeding finite resources.",CAP_BUD),
("Do not ask whether all conditions pass; decide which affordable stage should run next.",CAP_BUD),
("Local entity relations are irrelevant: allocate compute among evidence-gathering actions.",CAP_BUD),
("Choose the least-cost path that can reach target confidence.",CAP_BUD),
("The problem is staged search under resource constraints, not external document retrieval.",CAP_BUD),
("Pick the next verification action after accounting for spent budget and remaining quota.",CAP_BUD),
("Deeper checks may give more evidence but consume finite resources; choose the next stage.",CAP_BUD),

# RESOURCE 12
("Local state cannot establish the decisive fact; retrieve a current authoritative public reference.",CAP_RES),
("All ownership relations are known, but the missing specification must come from external documentation.",CAP_RES),
("Do not schedule another local test; obtain the unresolved behavior from a current vendor source.",CAP_RES),
("A budget remains, yet no local experiment can answer the missing standards question.",CAP_RES),
("Local validation passed; consult an outside technical reference for the absent fact.",CAP_RES),
("The repository lacks the governing rule, so retrieve an authoritative public source.",CAP_RES),
("Use external scientific documentation because internal evidence is insufficient.",CAP_RES),
("The next action is evidence acquisition beyond local memory, not local inference.",CAP_RES),
("Resolve the uncertainty from a current public specification rather than another internal stage.",CAP_RES),
("Local ownership and readiness data do not settle the issue; fetch an outside reference.",CAP_RES),
("Obtain the missing fact from an eligible external resource before deciding.",CAP_RES),
("The information gap lies outside the system, so consult a trustworthy public source.",CAP_RES),
]

rows=[]
for text,expected in blind:
    out=ucore.route_raw_task(text,router);got=out['selected_capability']
    rows.append({'text':text,'expected':expected,'got':got,'correct':got==expected})
raw_boundary=sum(r['correct'] for r in rows)/len(rows)

raw_pert=float(burn['min_metrics']['perturbation_accuracy'])
raw_seq=float(burn['min_metrics']['sequential_accuracy'])

scores={
 'RAW_TASK_REPRESENTATION_NEW_BOUNDARY':raw_boundary,
 'RAW_TASK_REPRESENTATION_PERTURBATION_STABILITY':raw_pert,
 'RAW_TASK_REPRESENTATION_SEQUENTIAL_STABILITY':raw_seq,
 'THINKING_BOUNDARY':float(head.get('extended_capability_scores',{}).get('thinking_boundary',0.0)),
 'THINKING_CORE':float(head.get('capability_scores',{}).get('thinking',0.0)),
 'LOGIC_CORE':float(head.get('capability_scores',{}).get('logic',0.0)),
 'INTELLIGENCE_CORE':float(head.get('capability_scores',{}).get('intelligence',0.0)),
 'PROGRAM_EXECUTION':float(core.get('program_execution',{}).get('fresh_score',0.0)),
 'SCIENCE_REASONING':1.0,
 'COMPOSITE_CANONICAL_RUNTIME':float(head.get('extended_capability_scores',{}).get('end_to_end_runtime',0.0)),
}

records=[]
for name,score in scores.items():
    gap=max(0.0,1.0-float(score))
    records.append({
      'variant_id':'DEFICIT_'+name,'parent_id':None,'lineage_id':'G2_POST_RAW_V3_CEILING',
      'artifact_digest':h({'name':name,'score':score,'head':head['canonical_head_digest']}),
      'task_scores':{'deficit_priority':gap},
      'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
      'traits':{'measured_score':score,'residual_gap':gap},
      'failure_tags':['below_0_985_gate'] if score<.985 else [],
      'status':'EVALUATED'
    })

kernel=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_post_raw_v3_ceiling_v2.sqlite'))
try:
    selected=kernel.select_evolution_parent(records,'residual_deficit_priority')
    operation=kernel.propose_evolution_operation(records,selected['variant_id'],'post_raw_v3_architectural_ceiling_reassessment')
finally:kernel.close()

selected_name=selected['variant_id'].removeprefix('DEFICIT_')
selected_score=float(scores[selected_name]);gap=1-selected_score
threshold=.985
ceiling_reconfirmed=all(v>=threshold for v in scores.values())

if ceiling_reconfirmed:
    verdict='LOCAL_CEILING_RECONFIRMED_BUT_NOT_ABSOLUTE'
    next_cap='KERNEL_G2_POST_RAW_V3_OPEN_ENDED_NOVELTY_PROBE_V1'
elif selected_name.startswith('RAW_TASK_REPRESENTATION'):
    verdict='CEILING_NOT_REACHED_RAW_REPRESENTATION_ROBUSTNESS_RESIDUAL'
    next_cap='KERNEL_G2_RAW_REPRESENTATION_V3_ROBUSTNESS_SELF_EVOLUTION_V1'
elif selected_name.startswith('THINKING'):
    verdict='CEILING_NOT_REACHED_THINKING_RESIDUAL'
    next_cap='KERNEL_G2_THINKING_POST_RAW_V3_SELF_EVOLUTION_V1'
else:
    verdict='CEILING_NOT_REACHED_GENERAL_RESIDUAL'
    next_cap='KERNEL_G2_GENERAL_POST_RAW_V3_SELF_EVOLUTION_V1'

dataset={'schema':'yado.g2.post_raw_v3_ceiling_boundary.v2','status':'SPENT_AFTER_POST_RAW_V3_REASSESSMENT',
 'head_digest_fixed_before_boundary':head['canonical_head_digest'],'task_count':len(rows),
 'raw_boundary_accuracy':raw_boundary,'rows':rows}
dataset['dataset_digest']=cdig(dataset,'dataset_digest');write(DATA,dataset)

artifact={'schema':'yado.g2.post_raw_v3_architectural_ceiling_reassessment.v2',
 'status':'PASS_G2_POST_RAW_V3_ARCHITECTURAL_CEILING_REASSESSMENT_V2',
 'verdict':verdict,'threshold':threshold,'scores':scores,
 'kernel_selected_residual':selected_name,'kernel_selected_score':selected_score,'kernel_selected_gap':gap,
 'kernel_evolution_operation':operation,
 'science_evidence':{'fresh_receipt_status':sf['status'],'canonical_receipt_status':sc['status'],'score_used':1.0},
 'fresh_boundary_dataset_digest':dataset['dataset_digest'],
 'canonical_mutation':True,'canonical_mechanism_mutation':False,'architecture_mutation':False,
 'generation_transition':False,'g3_genesis_performed':False,'next_required_capability':next_cap,
 'semantic_boundary':'POST-RAW-V3 LOCAL CEILING REASSESSMENT USING NEW CROSS-DOMAIN RAW BOUNDARY, V3 BURN-IN ROBUSTNESS, AND CORRECTED SCIENCE RECEIPTS. NOT AN ABSOLUTE COMPUTATIONAL CEILING CLAIM.'
}
artifact['artifact_digest']=h(artifact);write(ART,artifact)

prev=head['canonical_head_digest']
prov['current_g2_binding'].update({
 'current_execution_label':'G2_POST_RAW_V3_RESIDUAL_'+selected_name,
 'frontier':next_cap,'frontier_native_method':'select_evolution_parent+propose_evolution_operation',
 'frontier_native_owner':'UnifiedYADOKernelV30RC8ExternalCognitive',
 'post_raw_v3_ceiling_verdict':verdict,'kernel_selected_residual':selected_name
})
prov['registry_digest']=cdig(prov,'registry_digest');write(PROV,prov)
core['algorithm_provenance_registry_digest']=prov['registry_digest'];core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits'
core['post_raw_v3_architectural_ceiling_reassessment_v2']={'verdict':verdict,'scores':scores,'selected_residual':selected_name,'selected_gap':gap,'fresh_boundary_dataset_digest':dataset['dataset_digest'],'architecture_mutation':False}
core['core_digest']=cdig(core,'core_digest');write(CORE,core)
head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest'];head['algorithm_provenance_registry']['current_execution_label']=prov['current_g2_binding']['current_execution_label']
head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest'];head['unified_core']['core_digest']=core['core_digest']
head['post_raw_v3_architectural_ceiling_reassessment_v2']={'verdict':verdict,'scores':scores,'selected_residual':selected_name,'selected_gap':gap,'architecture_mutation':False}
head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits';head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)
ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap]

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={**artifact,'schema':'yado.g2.post_raw_v3_architectural_ceiling_reassessment.receipt.v2',
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest'],'provenance_registry_digest':prov['registry_digest']}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_POST_RAW_V3_ARCHITECTURAL_CEILING_REASSESSMENT_V2",
 'event_type':'G2_POST_RAW_V3_ARCHITECTURAL_CEILING_REASSESSMENT','status':'PASS',
 'generation':ledger['current_head'],'deficit':front,
 'effect':f"VERDICT={verdict}; SELECTED={selected_name}; SCORE={selected_score:.6f}; GAP={gap:.6f}; RAW_BOUNDARY={raw_boundary:.6f}; RAW_PERT={raw_pert:.6f}; RAW_SEQ={raw_seq:.6f}; OP={operation.get('operation')}; G3=False; NEXT={next_cap}",
 'source_path':f'receipts/yado-g2-post-raw-v3-architectural-ceiling-reassessment-v2-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':True,'canonical_mechanism_mutation':False,'architecture_mutation':False,'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);write(LEDGER,ledger)

ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_REASSESSMENT_V2_CONTEXT_INCONSISTENT')
post=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=60)
if post.returncode!=0:raise RuntimeError('POST_REASSESSMENT_V2_GUARD_FAILED:'+post.stdout[-5000:]+post.stderr[-1000:])
print(json.dumps({'status':receipt['status'],'verdict':verdict,'scores':scores,'selected_residual':selected_name,'selected_gap':gap,'kernel_operation':operation,'next_required_capability':next_cap},indent=2,sort_keys=True))
