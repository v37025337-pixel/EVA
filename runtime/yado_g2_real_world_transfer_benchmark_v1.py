from __future__ import annotations
from pathlib import Path
import hashlib,json,os,sys,urllib.request,urllib.error,subprocess

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_bounded_capability_router_v1 import BoundedCapabilityRouterLearnerV1,router_acc

LEDGER=REPO/'architecture'/'evolution-ledger.json'
HEAD=REPO/'canonical'/'yado-main-head-g2.json'
AUDIT=REPO/'receipts'/'yado-g2-post-workload-capability-audit-v1-run-33363851997.json'
PORT=REPO/'resources'/'yado-unified-external-resource-portfolio-v1.json'
OUT=ROOT/'yado_g2_real_world_transfer_benchmark_v1_receipt.json'

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

ledger=json.loads(LEDGER.read_text());head=json.loads(HEAD.read_text());audit=json.loads(AUDIT.read_text());portfolio=json.loads(PORT.read_text())
validate_ledger_v2(ledger)
if ledger['current_head']!='G2_CANDIDATE_TRCG_V1':raise RuntimeError('G2_NOT_HEAD')
if audit.get('status')!='PASS_G2_POST_WORKLOAD_CAPABILITY_AUDIT_V1':raise RuntimeError('POST_WORKLOAD_AUDIT_NOT_PASS')
head_before=fsha(HEAD);head_digest=head['canonical_head_digest']

# Learn the same structured routing contract from fresh examples.
def expected_structured(x):
    if x['budget_limited'] or x['quota_limited']:return CAP_BUD
    if x['external_evidence_needed']:return CAP_RES
    if x['relation_needed'] or x['disjunction_needed']:return CAP_REL
    return CAP_CONJ

train=[]
for i in range(640):
    x={
      'budget_limited':i%7==0,'quota_limited':i%13==0,
      'external_evidence_needed':i%5==0,'relation_needed':i%3==0,
      'disjunction_needed':i%11==0,'noise':i
    }
    train.append({'input':x,'expected':expected_structured(x)})
val=[]
for i in range(300):
    x={
      'budget_limited':i%8==0,'quota_limited':i%17==0,
      'external_evidence_needed':i%6==0,'relation_needed':i%4==0,
      'disjunction_needed':i%9==0,'noise':10000+i
    }
    val.append({'input':x,'expected':expected_structured(x)})
router=BoundedCapabilityRouterLearnerV1.synthesize(train,val,CAP_CONJ,min_support=4)

# Realistic unstructured task descriptions. Expected capability is independently declared,
# but G2 receives raw text only; no host-created feature fields are supplied.
raw_tasks=[
 ('A repository has failing tests and a release must wait until all checks and rollback conditions are satisfied.',CAP_CONJ,'PROGRAMMING'),
 ('Choose the cheapest sequence of CI stages that can reach the required confidence without exceeding the compute budget.',CAP_BUD,'PROGRAMMING'),
 ('Decide whether this contributor may modify the protected artifact given ownership, team and verified role relationships.',CAP_REL,'PROGRAMMING'),
 ('Find an external public source that documents the API behavior needed to resolve this implementation uncertainty.',CAP_RES,'PROGRAMMING'),

 ('Check whether all premises, the derivation step and the absence of a counterexample jointly justify accepting the proof.',CAP_CONJ,'MATHEMATICS'),
 ('Allocate a limited search budget among lemma checking, local search and formal verification.',CAP_BUD,'MATHEMATICS'),
 ('Determine whether two symbolic entities refer to the same object and whether that relation permits the inference.',CAP_REL,'MATHEMATICS'),
 ('Consult an external mathematical reference because the current evidence is insufficient.',CAP_RES,'MATHEMATICS'),

 ('Accept the experimental conclusion only if calibration, replication and evidence quality all pass.',CAP_CONJ,'EXACT_SCIENCE'),
 ('Choose which experiment or dataset to inspect next under a limited acquisition budget.',CAP_BUD,'EXACT_SCIENCE'),
 ('Determine whether a measurement belongs to the same experimental group and satisfies the verified-role relation.',CAP_REL,'EXACT_SCIENCE'),
 ('Retrieve a public scientific source to resolve a conflict between two stored claims.',CAP_RES,'EXACT_SCIENCE'),

 ('Commit an intervention only when the causal assumption, confounder control and rollback condition all hold.',CAP_CONJ,'CAUSAL_PLANNING'),
 ('Select the next intervention or simulation under a fixed cost budget.',CAP_BUD,'CAUSAL_PLANNING'),
 ('Reason about whether the acting entity is the owner or belongs to the same authorized group.',CAP_REL,'CAUSAL_PLANNING'),
 ('Seek external causal evidence because the local model is underdetermined.',CAP_RES,'CAUSAL_PLANNING'),

 ('Proceed only if identity, goal compatibility and safety constraints all hold.',CAP_CONJ,'MULTI_AGENT'),
 ('Choose the next coordination stage while respecting cost and quota limits.',CAP_BUD,'MULTI_AGENT'),
 ('Resolve whether the requesting agent is owner, same-team member, or verified lead.',CAP_REL,'MULTI_AGENT'),
 ('Consult an external coordination resource because local evidence is incomplete.',CAP_RES,'MULTI_AGENT'),
]

raw_correct=0
raw_rows=[]
for text,expected,domain in raw_tasks:
    # Existing G2 router has no raw-text representation layer. Passing only raw_text
    # intentionally measures that boundary rather than secretly extracting host features.
    got=router.execute({'raw_text':text})
    raw_correct+=got==expected
    raw_rows.append({'domain':domain,'raw_text':text,'expected':expected,'got':got,'correct':got==expected})
raw_accuracy=raw_correct/len(raw_tasks)

# Structured mirror: isolates the representation deficit from downstream routing.
structured_mirror=[]
for text,expected,domain in raw_tasks:
    x={'budget_limited':expected==CAP_BUD,'quota_limited':False,'external_evidence_needed':expected==CAP_RES,
       'relation_needed':expected==CAP_REL,'disjunction_needed':False,'raw_text_shadow':text}
    structured_mirror.append({'input':x,'expected':expected})
structured_accuracy=router_acc(router,structured_mirror)

# Live public resource availability. This is infrastructure evidence, not cognitive comprehension.
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
        req=urllib.request.Request(url,headers={'User-Agent':'YADO-G2-Transfer-Benchmark/1.0'})
        with urllib.request.urlopen(req,timeout=12) as resp:
            data=resp.read(4096)
            live.append({'url':url,'ok':200<=getattr(resp,'status',200)<400,'status':getattr(resp,'status',200),
                         'sample_sha256':hashlib.sha256(data).hexdigest(),'sample_bytes':len(data)})
    except Exception as exc:
        live.append({'url':url,'ok':False,'error':type(exc).__name__+':'+str(exc)[:160]})
live_success=sum(x['ok'] for x in live)
live_availability=live_success/len(live)

# Real repository execution sanity: compile actual runtime files. This proves executable infrastructure only.
compile_files=[
 REPO/'runtime'/'yado_g2_typed_recurrent_capability_graph_runtime_v1.py',
 REPO/'runtime'/'yado_g2_contextual_stream_capability_adapter_v1.py',
 REPO/'runtime'/'yado_budgeted_stage_policy_v1.py',
]
compile_rows=[]
for p in compile_files:
    cp=subprocess.run([sys.executable,'-m','py_compile',str(p)],capture_output=True,text=True)
    compile_rows.append({'path':str(p.relative_to(REPO)),'ok':cp.returncode==0,'stderr':cp.stderr[-300:]})
real_code_exec_infrastructure=sum(x['ok'] for x in compile_rows)/len(compile_rows)

checks={
 'structured_downstream_transfer':structured_accuracy>=.99,
 'live_resource_infrastructure':live_availability>=.60,
 'real_code_execution_infrastructure':real_code_exec_infrastructure==1.0,
 'raw_unstructured_transfer':raw_accuracy>=.80,
 'canonical_g2_immutable':fsha(HEAD)==head_before and ledger['current_head_digest']==head_digest,
}
# The expected honest outcome for current G2 is WITHHOLD if raw transfer is missing.
passed=all(checks.values())
status='PASS_G2_REAL_WORLD_TRANSFER_BENCHMARK_V1' if passed else 'WITHHOLD_G2_REAL_WORLD_TRANSFER_BENCHMARK_V1'
next_cap='G3_SUCCESSOR_GENESIS_FROM_G2_ENRICHED_HEAD_V1' if passed else 'G2_RAW_TASK_REPRESENTATION_AND_GROUNDING_V1'
receipt={
 'schema':'yado.g2.real_world_transfer_benchmark.receipt.v1','status':status,
 'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),
 'generation':ledger['current_head'],'generation_head_digest':head_digest,
 'raw_unstructured':{'accuracy':raw_accuracy,'task_count':len(raw_tasks),'rows':raw_rows},
 'structured_mirror_accuracy':structured_accuracy,
 'live_resource_availability':{'score':live_availability,'successes':live_success,'total':len(live),'rows':live},
 'real_code_execution_infrastructure':{'score':real_code_exec_infrastructure,'rows':compile_rows},
 'checks':checks,'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'REAL-WORLD TRANSFER BOUNDARY TEST. LIVE PUBLIC FETCH AND REAL REPOSITORY PYTHON COMPILATION ARE INFRASTRUCTURE CHECKS. RAW-TEXT ROUTING IS TESTED WITHOUT SECRET HOST FEATURE EXTRACTION. FAILURE THERE MEANS G2 LACKS A RAW TASK REPRESENTATION/GROUNDING LAYER.'
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_REAL_WORLD_TRANSFER",
   'event_type':'G2_REAL_WORLD_TRANSFER_BENCHMARK','status':'PASS' if passed else 'WITHHOLD','generation':ledger['current_head'],
   'deficit':'G2_REAL_WORLD_TRANSFER_BENCHMARK_V1',
   'effect':'REAL_WORLD_TRANSFER_PASS' if passed else 'RAW_UNSTRUCTURED_TRANSFER_BLOCKED; STRUCTURED_DOWNSTREAM_REMAINS_STRONG',
   'source_path':f'receipts/yado-g2-real-world-transfer-benchmark-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],
   'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[x for x in ledger.get('open_deficits',[]) if x!='G2_REAL_WORLD_TRANSFER_BENCHMARK_V1']
ledger['open_deficits']=sorted(set(ledger['open_deficits']+[next_cap]))
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':status,'raw_accuracy':raw_accuracy,'structured_accuracy':structured_accuracy,
 'live_availability':live_availability,'real_code_exec_infrastructure':real_code_exec_infrastructure,
 'checks':checks,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('REAL_WORLD_TRANSFER_WITHHELD')
