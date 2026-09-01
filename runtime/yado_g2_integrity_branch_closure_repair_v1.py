from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,subprocess,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
REG=REPO/'canonical/yado-unified-experience-registry-v1.json'
CTX=REPO/'canonical/yado-unified-context-kernel-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
OUT=ROOT/'yado_g2_integrity_branch_closure_repair_v1_receipt.json'
ACTIVE='yado-architecture-shadow-search'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):p.write_text(json.dumps(o,indent=2,sort_keys=True)+'\n',encoding='utf-8')
def content_digest(o,field):
    x=copy.deepcopy(o);x.pop(field,None);return h(x)

head,core,reg,ctx,ledger=map(load,[HEAD,CORE,REG,CTX,LEDGER])
validate_ledger_v2(ledger)
if ledger.get('current_head')!=head.get('generation_id'):raise RuntimeError('GENERATION_SPLIT_BRAIN')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_DIGEST_SPLIT_BRAIN')
if len(ledger.get('open_deficits',[]))!=1:raise RuntimeError('EXPECTED_ONE_FRONTIER')
frontier=ledger['open_deficits'][0]
generation=head['generation_id']

cp=subprocess.run(['git','ls-remote','--heads','origin'],cwd=REPO,capture_output=True,text=True,timeout=30)
if cp.returncode!=0:raise RuntimeError('REMOTE_BRANCH_INVENTORY_UNAVAILABLE:'+cp.stderr[-500:])
remote={}
for line in cp.stdout.splitlines():
    parts=line.split()
    if len(parts)==2 and parts[1].startswith('refs/heads/'):
        remote[parts[1][len('refs/heads/'):]]=parts[0]
registered={x.get('branch') for x in reg.get('branches',[])}
if set(remote)!=registered:
    raise RuntimeError('REMOTE_REGISTRY_BRANCH_SET_MISMATCH:'+json.dumps({'remote_only':sorted(set(remote)-registered),'registry_only':sorted(registered-set(remote))}))

trigger_sha=str(os.getenv('GITHUB_SHA') or remote[ACTIVE])
for entry in reg['branches']:
    name=entry['branch']
    if name==ACTIVE:
        entry['mode']='ACTIVE_LINEAGE'
        entry['runtime_active']=True
        entry['history_only']=False
        entry['generation']=generation
        entry['head_sha']=trigger_sha
        entry['head_sha_semantics']='REPAIR_INPUT_CHECKPOINT_NOT_SELF_REFERENTIAL_LIVE_TIP'
        entry.pop('closed_into_generation',None)
        entry.pop('closure_target',None)
        entry.pop('branch_tip_at_closure',None)
    else:
        entry['mode']='EXPERIENCE_ONLY'
        entry['runtime_active']=False
        entry['history_only']=True
        entry['closed_into_generation']=generation
        entry['closure_target']='YADO_UNIFIED_CONTEXT_KERNEL_V1'
        entry['branch_tip_at_closure']=remote[name]
        entry['head_sha']=remote[name]
        entry['legacy_auto_execution']=False
        entry['reuse_requires_fresh_admission']=True

legacy=[x for x in reg['branches'] if x['branch']!=ACTIVE]
reg['activation_mode']='SINGLE_ACTIVE_G2_WITH_READ_ONLY_HISTORY'
reg['closure']={
  'schema':'yado.branch_history_closure.v1',
  'active_branch':ACTIVE,'active_generation':generation,
  'remote_branch_count':len(remote),'active_lineage_count':1,'historical_branch_count':len(legacy),
  'all_remote_branches_registered':True,
  'all_non_active_branches_history_only':all(x.get('history_only') is True for x in legacy),
  'physical_branches_preserved':True,'physical_merge_or_deletion_required':False,
  'semantic_rule':'NON_ACTIVE_BRANCH_TIPS ARE IMMUTABLE HISTORY SOURCES; ONLY G2 IS RUNTIME-ACTIVE.'
}
reg['policy']['active_branch']=ACTIVE
reg['policy']['single_active_lineage']=True
reg['policy']['legacy_branches_are_runtime_inactive']=True
reg['policy']['g3_genesis_blocked']=True
reg['registry_digest']=content_digest(reg,'registry_digest')
write(REG,reg)

core['current_frontier']=frontier
core['frontier_source']='architecture/evolution-ledger.json:open_deficits'
core['experience_registry']='canonical/yado-unified-experience-registry-v1.json'
core['experience_registry_digest']=reg['registry_digest']
core['legacy_branch_count']=len(legacy)
for plane in core.get('planes',[]):
    if plane.get('plane_id')=='MEMORY_AND_EXPERIENCE':
        plane['experience_components']=['canonical/yado-unified-experience-registry-v1.json']
        plane['historical_branch_count']=len(legacy)
        plane['branch_closure_mode']='READ_ONLY_HISTORY_INTO_G2'
core['core_digest']=content_digest(core,'core_digest')
write(CORE,core)

ctx['generation']=generation
ctx['active_context']['frontier_source']='architecture/evolution-ledger.json:open_deficits'
ctx['branch_policy']['active_branch']=ACTIVE
ctx['branch_policy']['active_lineage_count']=1
ctx['branch_policy']['historical_branch_count']=len(legacy)
ctx['branch_policy']['remote_branch_count']=len(remote)
ctx['branch_policy']['all_non_active_branches_closed_into_generation']=generation
ctx['branch_policy']['non_active_branch_role']='MEMORY_HISTORY_ONLY'
ctx['branch_policy']['physical_branches_preserved']=True
ctx['branch_policy']['physical_merge_or_deletion_required']=False
write(CTX,ctx)

previous_head_digest=head['canonical_head_digest']
head['current_frontier']=frontier
head['frontier_source']='architecture/evolution-ledger.json:open_deficits'
head['unified_core']['core_digest']=core['core_digest']
head['unified_core']['experience_registry_digest']=reg['registry_digest']
head['unified_core']['legacy_branch_count']=len(legacy)
head['unified_context_kernel']['legacy_branches_as_memory']=True
head['unified_context_kernel']['single_active_context']=True
head['branch_history_closure']={
  'active_branch':ACTIVE,'historical_branch_count':len(legacy),'closed_into_generation':generation
}
head['canonical_head_digest']=content_digest(head,'canonical_head_digest')
write(HEAD,head)

evidence_digest=h({
 'generation':generation,'frontier':frontier,
 'previous_head_digest':previous_head_digest,'new_head_digest':head['canonical_head_digest'],
 'core_digest':core['core_digest'],'registry_digest':reg['registry_digest'],
 'historical_branch_tips':{x['branch']:x['head_sha'] for x in legacy},
})
ledger['current_head_digest']=head['canonical_head_digest']
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
event={
 'index':len(ledger['events']),
 'event_id':f"E{len(ledger['events'])+1:04d}_G2_INTEGRITY_AND_BRANCH_HISTORY_CLOSURE_REPAIR_V1",
 'event_type':'G2_CONTROL_PLANE_INTEGRITY_AND_BRANCH_HISTORY_CLOSURE_REPAIR',
 'status':'PASS','generation':generation,
 'deficit':'G2_CONTROL_PLANE_SPLIT_BRAIN_AND_BRANCH_HISTORY_CLOSURE',
 'effect':f"FRONTIER_SOURCE=LEDGER; ACTIVE_BRANCH={ACTIVE}; HISTORY_BRANCHES={len(legacy)}; NEXT={frontier}",
 'source_path':f'receipts/yado-g2-integrity-branch-closure-repair-v1-run-{run_id}.json',
 'source_digest':evidence_digest,'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':True,'promotion_applied':False,
 'generation_transition':False,'previous_head_digest':previous_head_digest,'new_head_digest':head['canonical_head_digest']
}
event['event_hash']=event_hash(event)
ledger['events'].append(event)
ledger['event_count']=len(ledger['events'])
ledger['tail_event_hash']=event['event_hash']
ledger['audit_advisory_only']=True
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger)
write(LEDGER,ledger)

from yado_unified_context_kernel_v1 import UnifiedContextKernel
from yado_unified_core_v1 import UnifiedYADOCoreV1
ctx_runtime=UnifiedContextKernel()
core_runtime=UnifiedYADOCoreV1(REPO)
core_audit=core_runtime.audit()
checks={
 'remote_registry_exact_match':set(remote)=={x['branch'] for x in reg['branches']},
 'one_active_lineage':sum(x.get('mode')=='ACTIVE_LINEAGE' for x in reg['branches'])==1,
 'thirteen_history_branches':len(legacy)==13 and all(x.get('mode')=='EXPERIENCE_ONLY' for x in legacy),
 'all_history_closed_into_g2':all(x.get('closed_into_generation')==generation and x.get('runtime_active') is False and x.get('history_only') is True for x in legacy),
 'frontier_head_core_ledger_equal':head['current_frontier']==core['current_frontier']==ledger['open_deficits'][0],
 'head_ledger_digest_equal':head['canonical_head_digest']==ledger['current_head_digest'],
 'context_kernel_validates':ctx_runtime.snapshot()['current_frontier']==frontier,
 'unified_core_frontier_coherent':core_audit['checks']['developmental_frontier_coherent'],
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
if not all(checks.values()):
    raise RuntimeError('REPAIR_CHECK_FAILED:'+json.dumps(checks,sort_keys=True))

receipt={
 'schema':'yado.g2.integrity_branch_history_closure_repair.receipt.v1',
 'status':'PASS_G2_INTEGRITY_BRANCH_HISTORY_CLOSURE_REPAIR_V1',
 'generation':generation,'previous_head_digest':previous_head_digest,'new_head_digest':head['canonical_head_digest'],
 'frontier':frontier,'active_branch':ACTIVE,'remote_branch_count':len(remote),
 'historical_branch_count':len(legacy),'historical_branches':sorted(x['branch'] for x in legacy),
 'evidence_digest':evidence_digest,'checks':checks,
 'canonical_mutation':True,'architecture_mutation':False,'generation_transition':False,
 'g3_genesis_performed':False,
 'semantic_boundary':'CONTROL-PLANE CONSISTENCY REPAIR AND LOGICAL BRANCH HISTORY CLOSURE INTO G2. HISTORICAL BRANCHES REMAIN PHYSICALLY PRESERVED AND RUNTIME-INACTIVE.'
}
receipt['receipt_sha256']=h(receipt)
OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps(receipt,indent=2,sort_keys=True))
