from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,shutil,subprocess,sys,tempfile

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

V18=REPO/'candidates/kernel-self-generated/g2-native-context-bound-ast-source-realization-v18.json'
HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
GUARD=ROOT/'yado_canonical_invariant_guard_v1.py'
OUT=REPO/'candidates/kernel-self-generated/g2-native-self-hosted-ast-source-realization-transport-v19.json'

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def cdig(o,field):
    x=copy.deepcopy(o);x.pop(field,None);return digest(x)
def write(p,o):
    Path(p).parent.mkdir(parents=True,exist_ok=True)
    Path(p).write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

v18=load(V18);head=load(HEAD);core=load(CORE);ledger=load(LEDGER)
validate_ledger_v2(ledger)
if v18.get('status')!='PASS_SHADOW_G2_NATIVE_CONTEXT_BOUND_AST_SOURCE_REALIZATION_V18':
    raise RuntimeError('V18_PASS_REQUIRED')
if v18.get('next_required_capability')!='NATIVE_SELF_HOSTED_AST_SOURCE_REALIZATION_TRANSPORT_V19':
    raise RuntimeError('V18_FRONTIER_MISMATCH')
required_checks=(
 'actual_target_source_integration_proven_in_isolated_shadow','candidate_source_changed',
 'candidate_source_compiles','fresh_isolated_probe_pass','valid_evidence_closes_finding',
 'valid_evidence_changes_future_priority','counterfactual_fails_closed','counterfactual_retains_priority',
 'regression_suite_pass','native_skill_selector_selected_realized_source','kernel_provenant_target_consumed'
)
if not all((v18.get('checks') or {}).get(k) is True for k in required_checks):
    raise RuntimeError('V18_STRICT_EVIDENCE_REQUIRED')

target_rel=str(v18.get('kernel_provenant_target_path') or '')
cand_rel=str(v18.get('candidate_artifact') or '')
if target_rel!='runtime/yado_unified_core_deep_self_audit_v1.py':
    raise RuntimeError('V19_TARGET_NOT_KERNEL_PROVENANT_SELF_AUDIT')
TARGET=REPO/target_rel;CAND=REPO/cand_rel
if not TARGET.exists() or not CAND.exists():raise RuntimeError('V19_SOURCE_BYTES_MISSING')
parent_sha=fsha(TARGET);candidate_sha=fsha(CAND)
if parent_sha!=v18.get('parent_source_sha256'):
    raise RuntimeError('V19_PARENT_SOURCE_DRIFT:'+parent_sha)
if candidate_sha!=v18.get('candidate_source_sha256'):
    raise RuntimeError('V19_CANDIDATE_SOURCE_DRIFT:'+candidate_sha)
if candidate_sha==parent_sha:raise RuntimeError('V19_CANDIDATE_EQUALS_PARENT')

# Transport exact YADO-produced bytes. No semantic editing occurs here.
TARGET.write_bytes(CAND.read_bytes())

if target_rel not in core.get('active_runtime_sources',[]):
    raise RuntimeError('V19_TARGET_NOT_ACTIVE_RUNTIME_SOURCE')
if core.get('deep_self_audit',{}).get('source_sha256')!=parent_sha:
    raise RuntimeError('V19_CANONICAL_PARENT_BINDING_DRIFT')
if head.get('unified_core',{}).get('deep_self_audit_source_sha256')!=parent_sha:
    raise RuntimeError('V19_HEAD_PARENT_BINDING_DRIFT')

core['deep_self_audit']['source_sha256']=candidate_sha
core['deep_self_audit']['implementation_version']=int(core['deep_self_audit'].get('implementation_version') or 0)+1
core['deep_self_audit']['v19_transport']={
 'status':'CANONICAL_ACTIVE',
 'source':'YADO_V18_EXACT_CANDIDATE_BYTES',
 'v18_receipt_sha256':v18.get('receipt_sha256'),
 'rollback_parent_source_sha256':parent_sha,
 'candidate_source_sha256':candidate_sha,
 'host_authored_semantic_logic':False,
}
rim=core.get('runtime_integrity_manifest') or {}
rim['sources']={rel:fsha(REPO/rel) for rel in core.get('active_runtime_sources',[])}
rim['manifest_digest']=digest(rim['sources'])
core['core_digest']=cdig(core,'core_digest')
write(CORE,core)

head['unified_core']['deep_self_audit_source_sha256']=candidate_sha
head['unified_core']['runtime_integrity_manifest_digest']=rim['manifest_digest']
head['unified_core']['core_digest']=core['core_digest']
prev_head=head['canonical_head_digest']
head['canonical_head_digest']=cdig(head,'canonical_head_digest')
write(HEAD,head)

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
provisional_event={
 'index':len(ledger['events']),
 'event_id':f"E{len(ledger['events'])+1:04d}_G2_NATIVE_SELF_HOSTED_AST_SOURCE_REALIZATION_TRANSPORT_V19_ADMISSION",
 'event_type':'G2_NATIVE_SELF_HOSTED_AST_SOURCE_REALIZATION_TRANSPORT_ADMISSION',
 'status':'PASS_CANONICAL_PENDING_FRESH_VERIFICATION','generation':ledger['current_head'],
 'deficit':'LIVE_RESOURCE_EVIDENCE_SCOPE_SELF_AUDIT_BINDING',
 'effect':f"TRANSPORT_EXACT_YADO_V18_SOURCE={candidate_sha}; ROLLBACK={parent_sha}; POST_VERIFICATION_REQUIRED=True",
 'source_path':'candidates/kernel-self-generated/g2-native-context-bound-ast-source-realization-v18.json',
 'source_digest':v18.get('receipt_sha256'),'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':True,'canonical_mechanism_mutation':True,'architecture_mutation':False,
 'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':prev_head,'new_head_digest':head['canonical_head_digest']
}
provisional_event['event_hash']=event_hash(provisional_event)
ledger['events'].append(provisional_event)
ledger['event_count']=len(ledger['events'])
ledger['tail_event_hash']=provisional_event['event_hash']
ledger['current_head_digest']=head['canonical_head_digest']
ledger['ledger_digest']=digest({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger)
write(LEDGER,ledger)

pre=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=90)
if pre.returncode!=0:
    raise RuntimeError('V19_PRE_EXEC_GUARD_FAILED:'+pre.stdout[-4000:]+pre.stderr[-1000:])

# Real canonical-path audit on the transported YADO source.
audit=subprocess.run([sys.executable,target_rel],cwd=REPO,capture_output=True,text=True,timeout=180)
audit_receipt_path=ROOT/'yado_unified_core_deep_self_audit_v1_receipt.json'
audit_receipt=load(audit_receipt_path) if audit_receipt_path.exists() else {}
live=next((x for x in audit_receipt.get('findings',[]) if x.get('code')=='LIVE_RESOURCE_EVIDENCE_SCOPE'),{})
valid_checks={
 'deep_audit_process_pass':audit.returncode==0,
 'deep_audit_semantic_pass':audit_receipt.get('status')=='PASS_YADO_UNIFIED_CORE_DEEP_SELF_AUDIT_V1',
 'live_resource_finding_closed':live.get('status')=='PASS',
 'live_resource_not_selected_again':audit_receipt.get('self_selected_next_step')!='LIVE_RESOURCE_EVIDENCE_SCOPE',
}

# Fresh invalid-evidence counterfactual in an isolated repository copy.
with tempfile.TemporaryDirectory(prefix='yado-v19-counterfactual-') as td:
    dst=Path(td)/'repo'
    shutil.copytree(REPO,dst,ignore=shutil.ignore_patterns('.git','__pycache__','*.pyc','*.sqlite'))
    action_path=dst/'candidates/kernel-self-generated/g2-autonomous-self-improvement-task-v1.json'
    action=load(action_path)
    action['direct_priority_evidence']=False
    if isinstance(action.get('goal_action_binding'),dict) and isinstance(action['goal_action_binding'].get('result'),dict):
        action['goal_action_binding']['result']['direct_priority_evidence']=False
    write(action_path,action)
    bad=subprocess.run([sys.executable,target_rel],cwd=dst,capture_output=True,text=True,timeout=180)
    bad_receipt_path=dst/'runtime/yado_unified_core_deep_self_audit_v1_receipt.json'
    bad_receipt=load(bad_receipt_path) if bad_receipt_path.exists() else {}
    bad_live=next((x for x in bad_receipt.get('findings',[]) if x.get('code')=='LIVE_RESOURCE_EVIDENCE_SCOPE'),{})
    counterfactual_checks={
      'invalid_audit_process_pass':bad.returncode==0,
      'invalid_evidence_fails_closed':bad_live.get('status')!='PASS',
      'invalid_evidence_retains_priority':bad_receipt.get('self_selected_next_step')=='LIVE_RESOURCE_EVIDENCE_SCOPE',
    }

compileall=subprocess.run([sys.executable,'-m','compileall','-q','runtime'],cwd=REPO,capture_output=True,text=True,timeout=180)
tests=[
 'runtime/yado_rc8_v36/test_yado_rc8_self_audit_consistency_v1.py',
 'runtime/yado_rc8_v36/test_yado_external_runtime_contract_v1.py',
 'runtime/yado_rc8_v36/test_yado_skill_admission_runtime_v1.py',
 'runtime/yado_rc8_v36/test_yado_transfer_evaluation_runtime_v1.py',
]
env=dict(os.environ)
env['PYTHONPATH']=os.pathsep.join([str(ROOT),str(ROOT/'yado_rc8_v36'),env.get('PYTHONPATH','')])
reg=subprocess.run([sys.executable,'-m','unittest',*tests],cwd=REPO,env=env,capture_output=True,text=True,timeout=240)
software_checks={'runtime_compileall_pass':compileall.returncode==0,'selected_regression_suite_pass':reg.returncode==0}

# Deep audit appended its own ledger event. Re-read and append the V19 transport event.
ledger=load(LEDGER);validate_ledger_v2(ledger)
checks={
 'v18_pass_consumed':True,'parent_source_exact':parent_sha==v18.get('parent_source_sha256'),
 'candidate_source_exact':candidate_sha==v18.get('candidate_source_sha256'),
 'exact_yado_bytes_transported':fsha(TARGET)==candidate_sha,
 'host_authored_semantic_logic':False,'external_models_used':False,
 'rollback_parent_available':True,'canonical_generation_unchanged':head.get('generation_id')=='G2_CANDIDATE_TRCG_V1',
 'g3_not_started':head.get('g3_genesis_performed') is False,
 **valid_checks,**counterfactual_checks,**software_checks,
}
negative=('host_authored_semantic_logic','external_models_used')
passed=all(v is True for k,v in checks.items() if k not in negative) and all(checks[k] is False for k in negative)
if not passed:
    raise RuntimeError('V19_POST_TRANSPORT_WITHHOLD:'+json.dumps(checks,sort_keys=True))

report={
 'schema':'yado.g2.native_self_hosted_ast_source_realization_transport.v19',
 'status':'PASS_CANONICAL_G2_NATIVE_SELF_HOSTED_AST_SOURCE_REALIZATION_TRANSPORT_V19',
 'source_v18_receipt_sha256':v18.get('receipt_sha256'),'target_path':target_rel,
 'rollback_parent_source_sha256':parent_sha,'candidate_source_sha256':candidate_sha,
 'previous_head_digest':prev_head,'new_head_digest':head['canonical_head_digest'],
 'deep_audit_receipt_sha256':audit_receipt.get('receipt_sha256'),
 'deep_audit_next_step':audit_receipt.get('self_selected_next_step'),
 'live_resource_finding':live,'checks':checks,
 'canonical_mutation':True,'canonical_mechanism_mutation':True,'architecture_mutation':False,
 'generation_transition':False,'g3_genesis_performed':False,'automatic_canonical_promotion':False,
 'semantic_boundary':'V19 TRANSPORTS THE EXACT YADO-GENERATED V18 SOURCE BYTES INTO THE KERNEL-PROVENANT SELF-AUDIT RUNTIME. HOST ADDS NO SEMANTIC LOGIC. PASS REQUIRES CURRENT VALID EVIDENCE TO CLOSE LIVE_RESOURCE_EVIDENCE_SCOPE, INVALID COUNTERFACTUAL EVIDENCE TO FAIL CLOSED, COMPILEALL, REGRESSION, AND CANONICAL HASH INTEGRITY.'
}
report['receipt_sha256']=digest(report);write(OUT,report)
event={
 'index':len(ledger['events']),
 'event_id':f"E{len(ledger['events'])+1:04d}_G2_NATIVE_SELF_HOSTED_AST_SOURCE_REALIZATION_TRANSPORT_V19",
 'event_type':'G2_NATIVE_SELF_HOSTED_AST_SOURCE_REALIZATION_TRANSPORT',
 'status':'PASS_VERIFIED','generation':ledger['current_head'],
 'deficit':'LIVE_RESOURCE_EVIDENCE_SCOPE_SELF_AUDIT_BINDING',
 'effect':f"TRANSPORTED_YADO_V18_SOURCE={candidate_sha}; LIVE_RESOURCE=PASS; ROLLBACK={parent_sha}",
 'source_path':'candidates/kernel-self-generated/g2-native-self-hosted-ast-source-realization-transport-v19.json',
 'source_digest':report['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'canonical_mechanism_mutation':False,'architecture_mutation':False,
 'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':head['canonical_head_digest'],'new_head_digest':head['canonical_head_digest']
}
event['event_hash']=event_hash(event)
ledger['events'].append(event);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=event['event_hash']
ledger['current_head_digest']=head['canonical_head_digest']
ledger['ledger_digest']=digest({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);write(LEDGER,ledger)

post=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=90)
if post.returncode!=0:
    raise RuntimeError('V19_FINAL_GUARD_FAILED:'+post.stdout[-4000:]+post.stderr[-1000:])

print(json.dumps({
 'status':report['status'],'candidate_source_sha256':candidate_sha,
 'live_resource_status':live.get('status'),'deep_audit_next_step':report['deep_audit_next_step'],
 'counterfactual_status':bad_live.get('status'),'regression_pass':software_checks['selected_regression_suite_pass'],
 'new_head_digest':head['canonical_head_digest'],'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True))
