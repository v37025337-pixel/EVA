from __future__ import annotations
from pathlib import Path
import hashlib,json,os

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
import sys
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

LEDGER=REPO/'architecture'/'evolution-ledger.json'
HEAD=REPO/'canonical'/'yado-main-head-g2.json'
DEV=REPO/'architecture'/'g2-development-state-v1.json'
BURN=REPO/'architecture'/'g2-burnin-state-v1.json'
WORK=REPO/'architecture'/'g2-applied-workload-state-v1.json'
CAND=REPO/'candidates'/'g2-development'/'contextual-stream-capability-adapter-v1.json'
OUT=ROOT/'yado_g2_post_workload_capability_audit_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

ledger=json.loads(LEDGER.read_text());head=json.loads(HEAD.read_text())
dev=json.loads(DEV.read_text());burn=json.loads(BURN.read_text());work=json.loads(WORK.read_text());cand=json.loads(CAND.read_text())
validate_ledger_v2(ledger)
if ledger['current_head']!='G2_CANDIDATE_TRCG_V1':raise RuntimeError('G2_NOT_HEAD')
if burn.get('status')!='BURNIN_PASS':raise RuntimeError('BURNIN_NOT_PASS')
if work.get('status')!='APPLIED_WORKLOAD_PASS':raise RuntimeError('WORKLOAD_NOT_PASS')
head_before=fsha(HEAD)

# Evidence-backed proven region.
proven={
 'canonical_g2_integrity':head['capability_scores']['integrity'],
 'logic':head['capability_scores']['logic'],
 'thinking':head['capability_scores']['thinking'],
 'intelligence':head['capability_scores']['intelligence'],
 'rollback':head['capability_scores']['rollback'],
 'capability_routing':head['extended_capability_scores']['capability_routing'],
 'end_to_end_runtime':head['extended_capability_scores']['end_to_end_runtime'],
 'recurrent_memory_base':head['extended_capability_scores']['recurrent_memory'],
 'relational_policy':head['extended_capability_scores']['relational_policy'],
 'resource_intelligence_structured':head['extended_capability_scores']['resource_intelligence'],
 'scalar_rule_induction':head['extended_capability_scores']['scalar_rule_induction'],
 'burnin_pass_streak':burn['stable_pass_streak'],
 'burnin_min_accuracy':burn['min_pass_accuracy'],
 'applied_workload_pass_streak':work['stable_pass_streak'],
 'applied_min_domain_accuracy':work['min_domain_accuracy'],
 'contextual_stream_memory_fresh':cand['fresh_blind']['score'],
 'contextual_stream_memory_representation_transfer':cand['representation_transfer']['score'],
}

# Deliberately distinguish tested from untested capabilities.
limitations=[
 {
  'id':'REAL_UNSTRUCTURED_INPUT_TRANSFER',
  'severity':'HIGH',
  'evidence':'Applied workload receipt explicitly says bounded synthetic applied workloads.',
  'status':'NOT_PROVEN',
  'required_test':'Feed raw/unstructured real task descriptions and require autonomous representation/routing without host-provided structured fields.'
 },
 {
  'id':'REAL_PROGRAM_EXECUTION_TRANSFER',
  'severity':'HIGH',
  'evidence':'Programming workload models release/test/budget policies but is not a real compiler/runtime benchmark.',
  'status':'NOT_PROVEN',
  'required_test':'Run fresh real code tasks with executable tests, hidden cases, failure repair, and regression.'
 },
 {
  'id':'REAL_MATHEMATICAL_REASONING_TRANSFER',
  'severity':'HIGH',
  'evidence':'Mathematics workload uses symbolic proof-gate contracts; not theorem proving.',
  'status':'NOT_PROVEN',
  'required_test':'Use fresh formal or checkable mathematical problems with independent answer verification.'
 },
 {
  'id':'REAL_SCIENCE_DATA_TRANSFER',
  'severity':'HIGH',
  'evidence':'Exact-science workload uses evidence-policy simulation, not external scientific datasets or measurements.',
  'status':'NOT_PROVEN',
  'required_test':'Use public datasets/documents with quantitative predictions or evidence integration verified independently.'
 },
 {
  'id':'LIVE_EXTERNAL_RESOURCE_ROBUSTNESS',
  'severity':'MEDIUM',
  'evidence':'Resource routing is proven against stored portfolio; live availability/content drift not tested in workload suite.',
  'status':'NOT_PROVEN',
  'required_test':'Live-fetch a bounded sample of eligible public resources and handle unavailable/stale/conflicting sources.'
 },
 {
  'id':'STREAM_MEMORY_BEYOND_1024_ACTIVE_CONTEXTS',
  'severity':'MEDIUM',
  'evidence':'LRU semantics verified exactly at 1024; older contexts are intentionally evicted.',
  'status':'BOUNDED_LIMITATION',
  'required_test':'Either accept/document capacity bound or synthesize hierarchical/persistent context retrieval before claiming broader memory.'
 },
 {
  'id':'CONTEXT_ADAPTER_CANONICALIZATION',
  'severity':'MEDIUM',
  'evidence':'ALG-G2-CONTEXTUAL-STREAM-CAPABILITY-ADAPTER-V1 remains canonical_active=false.',
  'status':'SHADOW_ONLY',
  'required_test':'Independent fresh admission gate before integrating into canonical G2 or inheriting to G3.'
 },
 {
  'id':'HOST_SCAFFOLD_DEPENDENCE',
  'severity':'HIGH',
  'evidence':'Current developmental task generators and strategy bank are host-scaffolded bounded environments.',
  'status':'NOT_PROVEN',
  'required_test':'Require G2 to derive task representation/strategy from less prestructured inputs and compare against host-scaffold ablation.'
 },
]

coverage={
 'tested_domains':['PROGRAMMING_POLICY','MATHEMATICS_PROOF_GATE','EXACT_SCIENCE_EVIDENCE_POLICY','CAUSAL_PLANNING','MULTI_AGENT_COORDINATION'],
 'workload_runs':len(work['runs']),
 'burnin_runs':len(burn['runs']),
 'development_cycles':len(dev['cycles']),
 'workload_steps_total':sum(
   sum(v['steps'] for v in r['domain_results'].values())+r['mixed_steps'] for r in work['runs']
 ),
 'burnin_operations_total':sum(
   r['metrics']['hot_operations']+r['metrics']['sequential_operations']+1800+2500 for r in burn['runs']
 ),
}
# Next stage is intentionally NOT G3.
high_unproven=sum(x['severity']=='HIGH' and x['status']=='NOT_PROVEN' for x in limitations)
ready_for_real_transfer=all(v>=.99 for k,v in proven.items() if isinstance(v,(int,float)) and 'streak' not in k) and high_unproven>=1
audit_status='PASS_G2_POST_WORKLOAD_CAPABILITY_AUDIT_V1' if ready_for_real_transfer else 'WITHHOLD_G2_POST_WORKLOAD_CAPABILITY_AUDIT_V1'

report={
 'schema':'yado.g2.post_workload_capability_audit.receipt.v1',
 'status':audit_status,'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),
 'generation':ledger['current_head'],'generation_head_digest':ledger['current_head_digest'],
 'proven_region':proven,'coverage':coverage,'limitations':limitations,
 'high_unproven_count':high_unproven,
 'audit_conclusion':'G2 IS STABLE INSIDE THE CURRENT BOUNDED STRUCTURED TEST REGION, BUT REAL-WORLD/UNSTRUCTURED TRANSFER IS NOT YET PROVEN.',
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
 'next_required_capability':'G2_REAL_WORLD_TRANSFER_BENCHMARK_V1',
 'semantic_boundary':'AUDIT DISTINGUISHES VERIFIED SOFTWARE CAPABILITIES FROM UNPROVEN REAL-WORLD GENERALIZATION. IT DOES NOT CLAIM AGI, SUBJECTIVE CONSCIOUSNESS, OR GENERAL THEOREM/PROGRAM/SCIENCE COMPETENCE.'
}
report['receipt_sha256']=h(report);OUT.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')

passed=audit_status.startswith('PASS_') and fsha(HEAD)==head_before
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_POST_WORKLOAD_AUDIT",
   'event_type':'G2_CAPABILITY_AUDIT','status':'PASS' if passed else 'WITHHOLD','generation':ledger['current_head'],
   'deficit':'G2_POST_WORKLOAD_CAPABILITY_AUDIT_V1',
   'effect':'BOUNDED_REGION_STABLE; REAL_WORLD_TRANSFER_REQUIRED_BEFORE_G3' if passed else 'POST_WORKLOAD_AUDIT_WITHHELD',
   'source_path':f'receipts/yado-g2-post-workload-capability-audit-v1-run-{run_id}.json','source_digest':report['receipt_sha256'],
   'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
if passed:
    ledger['open_deficits']=[x for x in ledger.get('open_deficits',[]) if x!='G2_POST_WORKLOAD_CAPABILITY_AUDIT_V1']
    ledger['open_deficits']=sorted(set(ledger['open_deficits']+['G2_REAL_WORLD_TRANSFER_BENCHMARK_V1']))
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':report['status'],'coverage':coverage,'high_unproven_count':high_unproven,
 'limitations':[{'id':x['id'],'severity':x['severity'],'status':x['status']} for x in limitations],
 'next_required_capability':report['next_required_capability'],'receipt_sha256':report['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('G2_POST_WORKLOAD_AUDIT_WITHHELD')
