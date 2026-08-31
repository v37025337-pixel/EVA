from __future__ import annotations
from pathlib import Path
import hashlib,json,os,subprocess,sys,urllib.request

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(PKG))

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_bounded_capability_router_v1 import BoundedCapabilityRouterLearnerV1
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
INTEGRATION=REPO/'receipts'/'yado-raw-task-representation-canonical-integration-v1-run-33392211618.json'
OUT=ROOT/'yado_g2_real_world_transfer_recheck_canonical_representation_v1_receipt.json'
LATEST=REPO/'receipts'/'yado-g2-real-world-transfer-recheck-canonical-v1-latest.json'

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);ledger=load(LEDGER);integration=load(INTEGRATION)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['G2_REAL_WORLD_TRANSFER_RECHECK_WITH_CANONICAL_REPRESENTATION_V1']:
    raise RuntimeError('UNEXPECTED_FRONTIER')
if integration.get('status')!='PASS_G2_RAW_TASK_REPRESENTATION_CANONICAL_INTEGRATION_V1':
    raise RuntimeError('RAW_CANONICAL_INTEGRATION_NOT_PASS')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):
    raise RuntimeError('HEAD_LEDGER_MISMATCH')

core=UnifiedYADOCoreV1(REPO)
if core.head.get('canonical_head_digest')!=head.get('canonical_head_digest'):
    raise RuntimeError('UNIFIED_CORE_HEAD_STALE')

# Fresh generic structured router used only after canonical raw representation.
router_rows=[]
for i,label in enumerate([CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES]*120):
    x={'budget_limited':label==CAP_BUD,'quota_limited':False,'external_evidence_needed':label==CAP_RES,
       'relation_needed':label==CAP_REL,'disjunction_needed':False,'noise':i}
    router_rows.append({'input':x,'expected':label})
router=BoundedCapabilityRouterLearnerV1.synthesize(router_rows,router_rows,CAP_CONJ,min_support=8)

blind=[
("A production change may proceed only after integrity, rollback, and verification conditions have all passed.",CAP_CONJ),
("Keep the migration blocked whenever any mandatory safety prerequisite is false.",CAP_CONJ),
("The record is accepted only if provenance, consistency, and validation all hold together.",CAP_CONJ),
("Every required gate must succeed before the deployment is committed.",CAP_CONJ),
("Approval requires simultaneous success of three independent mandatory checks.",CAP_CONJ),
("One missing prerequisite is sufficient to withhold acceptance.",CAP_CONJ),
("The candidate passes only when all required safeguards evaluate to true.",CAP_CONJ),
("Commit only if validation, recovery readiness, and integrity are jointly satisfied.",CAP_CONJ),
("Trust the result iff each of the mandatory conditions is satisfied.",CAP_CONJ),
("This is an all-of-these-conditions acceptance decision.",CAP_CONJ),

("Decide whether the service account owns the resource or belongs to its authorized group.",CAP_REL),
("Permission follows from relationships among requester, owner, tenant, and verified role.",CAP_REL),
("Determine whether two identifiers refer to the same principal or share the required membership link.",CAP_REL),
("Access depends on actor-owner equality and team membership relations.",CAP_REL),
("Reason about ownership and organizational links connecting the entities.",CAP_REL),
("The outcome changes when identity fields match or when the group relation matches.",CAP_REL),
("Evaluate authorization from relational structure rather than independent scalar gates.",CAP_REL),
("Check whether the requesting principal is the owner, a same-group member, or a verified lead.",CAP_REL),
("Resolve entity equality and membership edges before deciding permission.",CAP_REL),
("Infer the decision from who owns the object and how the actors are related.",CAP_REL),

("Choose the next verification stage without exceeding the remaining compute allowance.",CAP_BUD),
("Select a sequence of diagnostics with different costs and evidence gains under a hard limit.",CAP_BUD),
("Plan escalation while respecting remaining credits, quotas, and previously attempted checks.",CAP_BUD),
("Find the least costly set of tests that can reach the target confidence.",CAP_BUD),
("Allocate finite resources among cheap and deep investigations.",CAP_BUD),
("Pick the next stage under cost and quota constraints.",CAP_BUD),
("Optimize evidence gathering without spending beyond the available allowance.",CAP_BUD),
("Choose a staged search plan with a fixed resource ceiling.",CAP_BUD),
("Select among tests of different costs while respecting the remaining budget.",CAP_BUD),
("Plan the next investigation step given limited compute and expected gains.",CAP_BUD),

("Internal evidence cannot settle the issue; retrieve a current public reference.",CAP_RES),
("Consult outside documentation because the local state is underdetermined.",CAP_RES),
("Find an external standards source to resolve the missing fact.",CAP_RES),
("Use a public technical reference beyond the repository before deciding.",CAP_RES),
("Acquire external evidence because stored information is insufficient.",CAP_RES),
("Retrieve current vendor documentation to verify the unresolved behavior.",CAP_RES),
("Seek an outside scientific or technical source for the missing evidence.",CAP_RES),
("The next step is to obtain evidence from a public external resource.",CAP_RES),
("Look up a current public specification rather than relying only on local assumptions.",CAP_RES),
("Resolve the uncertainty with an external source, not additional local inference.",CAP_RES),
]
rows=[]
for text,expected in blind:
    out=core.route_raw_task(text,router)
    rows.append({'raw_text':text,'expected':expected,
                 'representation_capability':out['representation']['capability'],
                 'selected_capability':out['selected_capability'],
                 'correct':out['selected_capability']==expected})
raw_accuracy=sum(x['correct'] for x in rows)/len(rows)

# Live resource availability is rechecked now; availability != comprehension.
urls=[
 'https://docs.github.com/en/rest',
 'https://huggingface.co/docs/datasets/v4.7.0/stream',
 'https://arxiv.org/abs/2608.14595',
 'https://github.com/ripienaar/free-for-dev',
 'https://arxiv.org/abs/2608.19854',
]
live=[]
for url in urls:
    try:
        rq=urllib.request.Request(url,headers={'User-Agent':'YADO-G2-Canonical-Raw-Recheck/1.0'})
        with urllib.request.urlopen(rq,timeout=12) as resp:
            data=resp.read(4096)
            live.append({'url':url,'ok':200<=getattr(resp,'status',200)<400,'status':getattr(resp,'status',200),
                         'sample_bytes':len(data),'sample_sha256':hashlib.sha256(data).hexdigest()})
    except Exception as exc:
        live.append({'url':url,'ok':False,'error':type(exc).__name__+':'+str(exc)[:160]})
live_score=sum(x['ok'] for x in live)/len(live)

compile_paths=[
 'runtime/yado_unified_core_v1.py',
 'runtime/yado_raw_task_representation_learner_v1.py',
 'runtime/yado_raw_task_representation_runtime_v1.py',
 'runtime/yado_g2_typed_recurrent_capability_graph_runtime_v1.py',
]
compile_rows=[]
for rel in compile_paths:
    cp=subprocess.run([sys.executable,'-m','py_compile',str(REPO/rel)],capture_output=True,text=True)
    compile_rows.append({'path':rel,'ok':cp.returncode==0,'stderr':cp.stderr[-300:]})
compile_score=sum(x['ok'] for x in compile_rows)/len(compile_rows)

checks={
 'canonical_raw_routing_accuracy':raw_accuracy>=.80,
 'live_resource_infrastructure':live_score>=.60,
 'real_runtime_compile':compile_score==1.0,
 'head_ledger_coherent':ledger.get('current_head_digest')==head.get('canonical_head_digest'),
}
passed=all(checks.values())
next_cap='UNIFIED_CORE_POST_RAW_REPRESENTATION_SELF_AUDIT_V1' if passed else 'G2_RAW_TASK_REPRESENTATION_EXPRESSIVENESS_GAP_V1'
status='PASS_G2_REAL_WORLD_TRANSFER_RECHECK_CANONICAL_REPRESENTATION_V1' if passed else 'WITHHOLD_G2_REAL_WORLD_TRANSFER_RECHECK_CANONICAL_REPRESENTATION_V1'

receipt={
 'schema':'yado.g2.real_world_transfer_recheck_canonical_representation.v1',
 'status':status,'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),
 'generation':ledger['current_head'],'generation_head_digest':head['canonical_head_digest'],
 'canonical_raw_routing':{'accuracy':raw_accuracy,'task_count':len(rows),'rows':rows},
 'live_resource_availability':{'score':live_score,'rows':live},
 'real_runtime_compile':{'score':compile_score,'rows':compile_rows},
 'checks':checks,
 'remaining_scope_limitations':[
  'REAL_PROGRAM_EXECUTION_COMPETENCE_NOT_ESTABLISHED',
  'REAL_MATHEMATICAL_PROBLEM_SOLVING_NOT_ESTABLISHED',
  'REAL_SCIENTIFIC_DATA_REASONING_NOT_ESTABLISHED',
  'RAW_ROUTING_IS_NOT_FULL_ENTITY_LEVEL_SEMANTIC_GROUNDING',
  'HOST_SCAFFOLD_DEPENDENCE_REMAINS_PARTIALLY_UNTESTED'
 ],
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'CANONICAL RAW-TEXT INPUT ROUTING RECHECK THROUGH UNIFIED YADO CORE. PASS PROVES A BOUNDED INPUT-REPRESENTATION/Routing CAPABILITY, NOT GENERAL REAL-WORLD PROGRAMMING, MATHEMATICS, SCIENCE, OR AGI.'
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
LATEST.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_REAL_WORLD_TRANSFER_RECHECK_CANONICAL_RAW",
   'event_type':'CANONICAL_CAPABILITY_TRANSFER_RECHECK','status':'PASS' if passed else 'WITHHOLD',
   'generation':ledger['current_head'],'deficit':'G2_REAL_WORLD_TRANSFER_RECHECK_WITH_CANONICAL_REPRESENTATION_V1',
   'effect':'CANONICAL_RAW_TEXT_ROUTING_TRANSFER_PASS' if passed else 'CANONICAL_RAW_TEXT_ROUTING_TRANSFER_WITHHELD',
   'source_path':f'receipts/yado-g2-real-world-transfer-recheck-canonical-v1-run-{run_id}.json',
   'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
   'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({'status':status,'raw_accuracy':raw_accuracy,'live_score':live_score,'compile_score':compile_score,
 'checks':checks,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('CANONICAL_RAW_TRANSFER_RECHECK_WITHHELD')
