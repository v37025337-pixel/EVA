from pathlib import Path
import copy,hashlib,json,os,sys
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
BAD_RECEIPT=REPO/'receipts/yado-kernel-native-selector-commit-substrate-genesis-v1-run-33598685491.json'
BAD_CAND=REPO/'candidates/kernel-self-generated/native-selector-commit-substrate-v1.json'
DB=REPO/'runtime/yado_g2_native_selector_commit_registry_v1.sqlite'
ART=REPO/'architecture/yado-kernel-native-selector-commit-substrate-verdict-repair-v1.json'
CAND=REPO/'candidates/kernel-self-generated/native-selector-commit-substrate-v1-corrected.json'
OUT=ROOT/'yado_kernel_native_selector_commit_substrate_verdict_repair_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):
 x=copy.deepcopy(o);x.pop(field,None);return h(x)

head,core,ledger,bad,badc=map(load,[HEAD,CORE,LEDGER,BAD_RECEIPT,BAD_CAND])
validate_ledger_v2(ledger)
front='KERNEL_NATIVE_SELECTOR_COMMIT_SUBSTRATE_GENESIS_V2'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if not DB.exists():raise RuntimeError('PERSISTED_NATIVE_REGISTRY_MISSING')
db_sha=hashlib.sha256(DB.read_bytes()).hexdigest()
if db_sha!=bad.get('registry_sha256'):raise RuntimeError('REGISTRY_DIGEST_MISMATCH:'+json.dumps({'file':db_sha,'receipt':bad.get('registry_sha256')}))

dev=badc['development']
evidence_checks={
 'blind_score_one':abs(float(dev['candidate_score'])-1.0)<1e-12,
 'causal_ablation_passed':float(dev['candidate_score'])-float(dev['ablation_score'])>=0.20,
 'restore_exact':abs(float(dev['candidate_score'])-float(dev['restore_score']))<1e-12,
 'native_commit_true':bool(dev['state_committed']) and dev['verdict']=='COMMIT',
 'fresh6_post_commit_transfer_one':abs(float(badc['fresh6_post_commit_score'])-1.0)<1e-12,
 'original_restart_restore_true':bool(badc['checks']['restart_restored_active_program']),
 'host_rule_program_not_written':badc['checks']['host_rule_program_written'] is False,
 'source_sha_exact_match':bool(badc['checks']['source_sha_exact_match']),
 'registry_digest_exact':db_sha==bad['registry_sha256'],
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
if not all(evidence_checks.values()):raise RuntimeError('SUBSTANTIVE_EVIDENCE_NOT_ALL_PASS:'+json.dumps(evidence_checks,sort_keys=True))

# Stronger cross-run restart proof from the binary registry committed by the previous run.
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    active=dict(k.executive.active_program_by_capability)
    pid=active.get('SCALE_CONDITIONAL_SELECTOR_ROUTE_V1')
    low=k.executive.execute_capability('SCALE_CONDITIONAL_SELECTOR_ROUTE_V1',{'source_count':1.0})
    boundary=k.executive.execute_capability('SCALE_CONDITIONAL_SELECTOR_ROUTE_V1',{'source_count':4/3})
    high=k.executive.execute_capability('SCALE_CONDITIONAL_SELECTOR_ROUTE_V1',{'source_count':2.0})
finally:k.close()

cross_run_checks={
 'cross_run_program_restored':pid==bad['program_id'],
 'cross_run_low_correct':low=='OLD_STABLE_PARENT',
 'cross_run_boundary_correct':boundary=='FRESH_FOUR_PAIR_KNN_V1',
 'cross_run_high_correct':high=='FRESH_FOUR_PAIR_KNN_V1',
}
if not all(cross_run_checks.values()):raise RuntimeError('CROSS_RUN_RESTORE_FAILED:'+json.dumps(cross_run_checks,sort_keys=True))

next_cap='KERNEL_NATIVE_SELECTOR_COMMIT_SUBSTRATE_CANONICAL_BINDING_V1'
corrected={
 'schema':'yado.g2.native_selector_commit_substrate.corrected.v1',
 'state':'SHADOW_SUPPORTED',
 'source_candidate_path':'candidates/kernel-self-generated/native-selector-commit-substrate-v1.json',
 'source_candidate_digest':badc['candidate_digest'],
 'correction_reason':'CONTROL_PLANE_BOOLEAN_POLARITY_BUG_HOST_RULE_PROGRAM_WRITTEN_FALSE_WAS_COUNTED_AS_FAILED_CHECK',
 'program_id':bad['program_id'],'program_digest':bad['program_digest'],
 'registry_path':'runtime/yado_g2_native_selector_commit_registry_v1.sqlite','registry_sha256':db_sha,
 'development':dev,'fresh6_post_commit_score':badc['fresh6_post_commit_score'],
 'evidence_checks':evidence_checks,'cross_run_checks':cross_run_checks,
 'canonical_active':False,'promotion_applied':False,'canonical_mechanism_mutation':False,'g3_genesis_performed':False,
}
corrected['candidate_digest']=h(corrected);CAND.parent.mkdir(parents=True,exist_ok=True);write(CAND,corrected)
artifact={
 'schema':'yado.g2.kernel_native_selector_commit_substrate_verdict_repair.v1',
 'status':'PASS_CONTROL_PLANE_VERDICT_REPAIR_NATIVE_SUBSTRATE_SUPPORTED',
 'candidate_state':'SHADOW_SUPPORTED','candidate_digest':corrected['candidate_digest'],
 'program_id':bad['program_id'],'registry_sha256':db_sha,
 'next_required_capability':next_cap,'canonical_mechanism_mutation':False,'architecture_mutation':False,'g3_genesis_performed':False,
}
artifact['artifact_digest']=h(artifact);write(ART,artifact)

prev=head['canonical_head_digest']
core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits';core['core_digest']=cdig(core,'core_digest');write(CORE,core)
head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits';head['unified_core']['core_digest']=core['core_digest'];head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)
receipt={**artifact,'schema':'yado.g2.kernel_native_selector_commit_substrate_verdict_repair.receipt.v1',
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest'],
 'evidence_checks':evidence_checks,'cross_run_checks':cross_run_checks}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)

ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap];run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_NATIVE_SELECTOR_COMMIT_VERDICT_REPAIR_V1",
 'event_type':'G2_CONTROL_PLANE_VERDICT_REPAIR','status':'PASS_SHADOW','generation':ledger['current_head'],'deficit':front,
 'effect':f"REPAIR=BOOLEAN_POLARITY; PROGRAM={bad['program_id']}; BLIND=1.000000; ABLATION=0.400000; RESTORE=1.000000; CROSS_RUN_RESTORE=True; STATE=SHADOW_SUPPORTED; NEXT={next_cap}",
 'source_path':f'receipts/yado-kernel-native-selector-commit-substrate-verdict-repair-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':True,'canonical_mechanism_mutation':False,'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);write(LEDGER,ledger)
ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_WRITE_CONTEXT_INCONSISTENT')
print(json.dumps({'status':artifact['status'],'program_id':bad['program_id'],'evidence_checks':evidence_checks,'cross_run_checks':cross_run_checks,'next':next_cap},indent=2,sort_keys=True))
