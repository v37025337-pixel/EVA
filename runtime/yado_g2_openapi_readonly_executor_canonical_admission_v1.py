from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,subprocess,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_g2_openapi_readonly_executor_v1 import G2OpenAPIReadOnlyExecutorV1

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
FRESH=REPO/'candidates/kernel-self-generated/g2-openapi-readonly-executor-v1.json'
CANON=REPO/'canonical/yado-g2-openapi-readonly-executor-v1.json'
UNIFIED=ROOT/'yado_unified_core_v1.py'
OUT=ROOT/'yado_g2_openapi_readonly_executor_canonical_admission_v1_receipt.json'
GUARD=ROOT/'yado_canonical_invariant_guard_v1.py'

COMP='ALG-G2-OPENAPI-READONLY-EXECUTOR-V1'
PARENT='ALG-G2-OPENAPI-CONTRACT-CAPABILITY-V1'
FRONT='KERNEL_G2_RAW_REPRESENTATION_V5_CANONICAL_ADMISSION_V1'

def load(p):return json.loads(p.read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):x=copy.deepcopy(o);x.pop(field,None);return h(x)

head,core,prov,ledger,fresh=map(load,[HEAD,CORE,PROV,LEDGER,FRESH])
validate_ledger_v2(ledger)
if head.get('current_frontier')!=FRONT or ledger.get('open_deficits')!=[FRONT]:raise RuntimeError('FRONTIER_DRIFT')
if head.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')
if fresh.get('status')!='PASS_SHADOW_G2_OPENAPI_READONLY_EXECUTOR_V1':raise RuntimeError('FRESH_GATE_NOT_PASS')
if COMP in head.get('active_capabilities',[]):raise RuntimeError('READONLY_EXECUTOR_ALREADY_ACTIVE')
if core.get('openapi_contract_capability_v1',{}).get('status')!='CANONICAL_ACTIVE':raise RuntimeError('PARENT_OPENAPI_PLAN_CAPABILITY_NOT_ACTIVE')
if core.get('openapi_contract_capability_v1',{}).get('network_execute') is not False:raise RuntimeError('PARENT_PLAN_NETWORK_BOUNDARY_DRIFT')

# Patch the single unified core entry point only after fresh live evidence exists.
src=UNIFIED.read_text(encoding='utf-8')
import_anchor='from yado_g2_openapi_contract_capability_v1 import G2OpenAPIContractCapabilityV1\n'
if 'from yado_g2_openapi_readonly_executor_v1 import G2OpenAPIReadOnlyExecutorV1' not in src:
    if import_anchor not in src:raise RuntimeError('UNIFIED_IMPORT_ANCHOR_MISSING')
    src=src.replace(import_anchor,import_anchor+'from yado_g2_openapi_readonly_executor_v1 import G2OpenAPIReadOnlyExecutorV1\n')
init_anchor='        self.openapi_contract_capability_cls=G2OpenAPIContractCapabilityV1\n'
if 'self.openapi_readonly_executor_cls=G2OpenAPIReadOnlyExecutorV1' not in src:
    if init_anchor not in src:raise RuntimeError('UNIFIED_INIT_ANCHOR_MISSING')
    src=src.replace(init_anchor,init_anchor+'        self.openapi_readonly_executor_cls=G2OpenAPIReadOnlyExecutorV1\n')
method_anchor='    def snapshot(self)->dict[str,Any]:\n'
method="""    def execute_openapi_readonly_plan(self,plan:dict[str,Any],base_url:str,allowed_hosts:list[str],query=None,headers=None,max_bytes:int=1048576,timeout:float=10.0)->dict[str,Any]:
        executor=self.openapi_readonly_executor_cls(allowed_hosts,max_bytes=max_bytes,timeout=timeout)
        return executor.execute(plan,base_url,query=query,headers=headers)

"""
if 'def execute_openapi_readonly_plan(' not in src:
    if method_anchor not in src:raise RuntimeError('UNIFIED_METHOD_ANCHOR_MISSING')
    src=src.replace(method_anchor,method+method_anchor)
UNIFIED.write_text(src,encoding='utf-8')
unified_sha=fsha(UNIFIED)

component=G2OpenAPIReadOnlyExecutorV1.component()
canon_art={
 'schema':'yado.g2.openapi_readonly_executor.canonical.v1','status':'CANONICAL_ACTIVE',
 'component_id':COMP,'parent_contract_capability':PARENT,'component':component,
 'runtime_source':'runtime/yado_g2_openapi_readonly_executor_v1.py','runtime_sha256':fsha(ROOT/'yado_g2_openapi_readonly_executor_v1.py'),
 'fresh_gate_artifact':'candidates/kernel-self-generated/g2-openapi-readonly-executor-v1.json',
 'fresh_gate_receipt_sha256':fresh.get('receipt_sha256'),'fresh_checks':fresh.get('checks'),
 'network_execute':True,'read_only_only':True,'methods':['GET','HEAD'],
 'credentials_allowed':False,'redirects_followed':False,'https_only':True,
 'explicit_host_allowlist':True,'private_address_access':False,
 'architecture_mutation':False,
 'semantic_boundary':'CANONICAL SAME-G2 REAL NETWORK EXECUTOR LIMITED TO PRE-APPROVED READ-ONLY OPENAPI GET/HEAD PLANS. CREDENTIALS, REDIRECTS, PRIVATE ADDRESSES AND NON-HTTPS ARE REJECTED.'
}
canon_art['canonical_component_digest']=cdig(canon_art,'canonical_component_digest');write(CANON,canon_art)

def plane(pid):
    p=next((x for x in core.get('planes',[]) if x.get('plane_id')==pid),None)
    if p is None:raise RuntimeError('MISSING_PLANE:'+pid)
    return p
resource=plane('RESOURCE_AND_EVIDENCE')
resource['active_components']=sorted(set(resource.get('active_components',[])+[COMP]))
resource['responsibilities']=sorted(set(resource.get('responsibilities',[])+['bounded_real_readonly_openapi_execution','explicit_host_allowlist','credentialless_network_evidence']))

core['openapi_readonly_executor_v1']={
 'status':'CANONICAL_ACTIVE','component_id':COMP,'canonical_component_digest':canon_art['canonical_component_digest'],
 'runtime_sha256':canon_art['runtime_sha256'],'fresh_gate_receipt_sha256':fresh.get('receipt_sha256'),
 'network_execute':True,'read_only_only':True,'methods':['GET','HEAD'],
 'credentials_allowed':False,'redirects_followed':False,'https_only':True,
 'explicit_host_allowlist':True,'private_address_access':False
}
active_sources=set(core.get('active_runtime_sources',[]))
active_sources.add('runtime/yado_g2_openapi_readonly_executor_v1.py')
core['active_runtime_sources']=sorted(active_sources)
rim=core.get('runtime_integrity_manifest')
if not isinstance(rim,dict) or not isinstance(rim.get('sources'),dict):raise RuntimeError('RUNTIME_INTEGRITY_MANIFEST_MISSING')
rim['sources']={rel:fsha(REPO/rel) for rel in core['active_runtime_sources']}
rim['manifest_digest']=h(rim['sources'])
core['runtime_sha256']=unified_sha

prev=head['canonical_head_digest']
prov['current_g2_binding'].update({
 'current_execution_label':'G2_UNIFIED_EXECUTION_FABRIC_READONLY_API_ACTIVE_V1',
 'frontier':FRONT,'openapi_readonly_executor_component':COMP,
 'openapi_readonly_executor_source_sha256':canon_art['runtime_sha256'],
 'openapi_readonly_executor_fresh_receipt_sha256':fresh.get('receipt_sha256')
})
prov['registry_digest']=cdig(prov,'registry_digest');write(PROV,prov)

core['algorithm_provenance_registry_digest']=prov['registry_digest']
core['current_frontier']=FRONT
core['core_digest']=cdig(core,'core_digest');write(CORE,core)

head['active_capabilities']=sorted(set(head.get('active_capabilities',[])+[COMP]))
head['new_capabilities']=sorted(set(head.get('new_capabilities',[])+[COMP]))
head['openapi_readonly_executor_v1']={
 'status':'CANONICAL_ACTIVE','component_id':COMP,'canonical_component_digest':canon_art['canonical_component_digest'],
 'network_execute':True,'read_only_only':True,'credentials_allowed':False,'redirects_followed':False
}
head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest']
head['algorithm_provenance_registry']['current_execution_label']=prov['current_g2_binding']['current_execution_label']
head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest']
head['unified_core']['core_digest']=core['core_digest']
head['unified_core']['runtime_sha256']=unified_sha
head['unified_core']['runtime_integrity_manifest_digest']=rim['manifest_digest']
head['current_frontier']=FRONT
head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)

ledger['current_head_digest']=head['canonical_head_digest']
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
 'schema':'yado.g2.openapi_readonly_executor.canonical_admission.receipt.v1',
 'status':'PASS_G2_OPENAPI_READONLY_EXECUTOR_CANONICAL_ADMISSION_V1',
 'component_id':COMP,'parent_component':PARENT,'fresh_gate_receipt_sha256':fresh.get('receipt_sha256'),
 'active_capability_count_after':len(head['active_capabilities']),
 'network_execute':True,'read_only_only':True,'methods':['GET','HEAD'],
 'credentials_allowed':False,'redirects_followed':False,'https_only':True,
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest'],
 'frontier_unchanged':FRONT,'canonical_mutation':True,'canonical_mechanism_mutation':True,
 'architecture_mutation':False,'generation_transition':False,'g3_genesis_performed':False,
 'semantic_boundary':'SAME-G2 CANONICAL ADMISSION OF BOUNDED CREDENTIALLESS READ-ONLY NETWORK EXECUTION. WRITE METHODS AND UNBOUNDED NETWORK ACCESS REMAIN DISALLOWED.'
}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)
e={
 'index':len(ledger['events']),
 'event_id':f"E{len(ledger['events'])+1:04d}_G2_OPENAPI_READONLY_EXECUTOR_CANONICAL_ADMISSION_V1",
 'event_type':'G2_OPENAPI_READONLY_EXECUTOR_CANONICAL_ADMISSION','status':'PASS_CANONICAL',
 'generation':ledger['current_head'],'deficit':'OPENAPI_PLAN_ONLY_WITHOUT_BOUNDED_REAL_READ_EXECUTION',
 'effect':f"ADDED={COMP}; METHODS=GET,HEAD; CREDENTIALS=False; REDIRECTS=False; ACTIVE_CAPS={len(head['active_capabilities'])}; FRONTIER_UNCHANGED={FRONT}",
 'source_path':f'receipts/yado-g2-openapi-readonly-executor-canonical-admission-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':True,'canonical_mechanism_mutation':True,'architecture_mutation':False,'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']
}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);write(LEDGER,ledger)

post=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=90)
if post.returncode!=0:raise RuntimeError('POST_API_ADMISSION_CANONICAL_GUARD_FAILED:'+post.stdout[-6000:]+post.stderr[-2000:])
print(json.dumps({'status':receipt['status'],'component_id':COMP,'active_capability_count_after':len(head['active_capabilities']),'network_execute':True,'read_only_only':True,'frontier':FRONT},indent=2,sort_keys=True))
