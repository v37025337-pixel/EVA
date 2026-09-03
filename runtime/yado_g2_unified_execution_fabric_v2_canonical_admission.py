from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,subprocess,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(PKG))

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_g2_unified_execution_fabric_v2 import G2UnifiedExecutionFabricV2

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
FRESH=REPO/'candidates/kernel-self-generated/g2-unified-execution-fabric-v2.json'
CANON=REPO/'canonical/yado-g2-unified-execution-fabric-v2.json'
UNIFIED=ROOT/'yado_unified_core_v1.py'
OUT=ROOT/'yado_g2_unified_execution_fabric_v2_canonical_admission_receipt.json'
GUARD=ROOT/'yado_canonical_invariant_guard_v1.py'

V1='RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V1'
V2='RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V2'
API_EXEC='ALG-G2-OPENAPI-READONLY-EXECUTOR-V1'
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
if fresh.get('status')!='PASS_SHADOW_G2_UNIFIED_EXECUTION_FABRIC_V2':raise RuntimeError('FABRIC_V2_FRESH_NOT_PASS')
if V1 not in head.get('active_capabilities',[]):raise RuntimeError('FABRIC_V1_NOT_ACTIVE_BEFORE_REPLACEMENT')
if V2 in head.get('active_capabilities',[]):raise RuntimeError('FABRIC_V2_ALREADY_ACTIVE')
if API_EXEC not in head.get('active_capabilities',[]):raise RuntimeError('READONLY_API_EXECUTOR_NOT_ACTIVE')

component=G2UnifiedExecutionFabricV2.component()
canon_art={
 'schema':'yado.g2.unified_execution_fabric.v2.canonical',
 'status':'CANONICAL_ACTIVE',
 'component_id':V2,
 'parent_component':V1,
 'component':component,
 'runtime_source':'runtime/yado_g2_unified_execution_fabric_v2.py',
 'runtime_sha256':fsha(ROOT/'yado_g2_unified_execution_fabric_v2.py'),
 'fresh_gate_artifact':'candidates/kernel-self-generated/g2-unified-execution-fabric-v2.json',
 'fresh_gate_receipt_sha256':fresh.get('receipt_sha256'),
 'fresh_checks':fresh.get('checks'),
 'external_evidence_memory':'BOUNDED_METADATA_ONLY',
 'network_execution':{'enabled':True,'read_only_only':True,'methods':['GET','HEAD'],'credentials_allowed':False,'redirects_followed':False},
 'architecture_mutation':False,
 'semantic_boundary':'CURRENT G2 UNIFIED EXECUTION FABRIC. READ-ONLY API EXECUTION IS DISPATCHABLE BY INTELLIGENCE AND LIVE OUTCOMES ENTER RECURRENT WORKSPACE AS BOUNDED METADATA-ONLY EXTERNAL EVIDENCE.'
}
canon_art['canonical_component_digest']=cdig(canon_art,'canonical_component_digest');write(CANON,canon_art)

# Patch UnifiedYADOCoreV1 to instantiate V2.
src=UNIFIED.read_text(encoding='utf-8')
import_v1='from yado_g2_unified_execution_fabric_v1 import G2UnifiedExecutionFabricV1\n'
import_v2='from yado_g2_unified_execution_fabric_v2 import G2UnifiedExecutionFabricV2\n'
if import_v2 not in src:
    if import_v1 not in src:raise RuntimeError('UNIFIED_FABRIC_IMPORT_ANCHOR_MISSING')
    src=src.replace(import_v1,import_v1+import_v2)
src=src.replace('        self.execution_fabric_cls=G2UnifiedExecutionFabricV1\n','        self.execution_fabric_cls=G2UnifiedExecutionFabricV2\n')
if 'self.execution_fabric_cls=G2UnifiedExecutionFabricV2' not in src:raise RuntimeError('UNIFIED_FABRIC_V2_BINDING_FAILED')
bridge_anchor='    def snapshot(self)->dict[str,Any]:\n'
bridge_method="""    def execute_openapi_readonly_via_fabric(self,execution_fabric,plan:dict[str,Any],base_url:str,allowed_hosts:list[str],query=None,headers=None,max_bytes:int=1048576,timeout:float=10.0,stream_id:str='OPENAPI')->dict[str,Any]:
        if not hasattr(execution_fabric,'execute_capability'):
            raise TypeError('EXECUTION_FABRIC_REQUIRED')
        return execution_fabric.execute_capability(
            'ALG-G2-OPENAPI-READONLY-EXECUTOR-V1',
            {
              'plan':plan,'base_url':base_url,'allowed_hosts':allowed_hosts,
              'query':query,'headers':headers,'max_bytes':max_bytes,'timeout':timeout,
              'stream_id':stream_id,
            }
        )

"""
if 'def execute_openapi_readonly_via_fabric(' not in src:
    if bridge_anchor not in src:raise RuntimeError('UNIFIED_SNAPSHOT_ANCHOR_MISSING')
    src=src.replace(bridge_anchor,bridge_method+bridge_anchor)
UNIFIED.write_text(src,encoding='utf-8')
unified_sha=fsha(UNIFIED)

# Architecture plane rebinding.
workspace=next((p for p in core.get('planes',[]) if p.get('plane_id')=='WORKSPACE_AND_INTEGRATION'),None)
resource=next((p for p in core.get('planes',[]) if p.get('plane_id')=='RESOURCE_AND_EVIDENCE'),None)
memory=next((p for p in core.get('planes',[]) if p.get('plane_id')=='MEMORY_AND_EXPERIENCE'),None)
if not workspace or not resource or not memory:raise RuntimeError('REQUIRED_PLANE_MISSING')
workspace['active_components']=[V2 if x==V1 else x for x in workspace.get('active_components',[])]
workspace['active_components']=sorted(set(workspace['active_components']))
workspace['responsibilities']=sorted(set(workspace.get('responsibilities',[])+['intelligence_to_readonly_api_dispatch','external_evidence_to_recurrent_workspace']))
rr=set(resource.get('responsibilities',[]))
rr.discard('network_execution_disabled')
rr.update(['contract_planner_network_execution_disabled','readonly_executor_network_execution_enabled','api_outcome_to_workspace_memory'])
resource['responsibilities']=sorted(rr)
memory['responsibilities']=sorted(set(memory.get('responsibilities',[])+['bounded_external_evidence_metadata_memory']))

core['execution_fabric_v1']=core.get('execution_fabric_v1',{})|{
 'status':'SUPERSEDED_BY_V2','canonical_active':False,'superseded_by':V2
}
core['execution_fabric_v2']={
 'status':'CANONICAL_ACTIVE','component_id':V2,
 'canonical_component_digest':canon_art['canonical_component_digest'],
 'runtime_sha256':canon_art['runtime_sha256'],
 'fresh_gate_receipt_sha256':fresh.get('receipt_sha256'),
 'external_evidence_memory':'BOUNDED_METADATA_ONLY',
 'network_execution_readonly':True,
 'architecture_mutation':False
}

active_sources=set(core.get('active_runtime_sources',[]))
active_sources.add('runtime/yado_g2_unified_execution_fabric_v2.py')
# V1 source remains an active runtime dependency because V2 subclasses it.
core['active_runtime_sources']=sorted(active_sources)
rim=core.get('runtime_integrity_manifest')
if not isinstance(rim,dict) or not isinstance(rim.get('sources'),dict):raise RuntimeError('RUNTIME_INTEGRITY_MANIFEST_MISSING')
rim['sources']={rel:fsha(REPO/rel) for rel in core['active_runtime_sources']}
rim['manifest_digest']=h(rim['sources'])
core['runtime_sha256']=unified_sha

prev=head['canonical_head_digest']
prov['current_g2_binding'].update({
 'current_execution_label':'G2_UNIFIED_EXECUTION_FABRIC_V2_LAYER_CONNECTED',
 'frontier':FRONT,
 'execution_fabric_component':V2,
 'execution_fabric_parent_component':V1,
 'execution_fabric_v2_source_sha256':canon_art['runtime_sha256'],
 'execution_fabric_v2_fresh_receipt_sha256':fresh.get('receipt_sha256'),
 'external_evidence_memory':'BOUNDED_METADATA_ONLY'
})
prov['registry_digest']=cdig(prov,'registry_digest');write(PROV,prov)

core['algorithm_provenance_registry_digest']=prov['registry_digest']
core['current_frontier']=FRONT
core['core_digest']=cdig(core,'core_digest');write(CORE,core)

head['active_capabilities']=[V2 if x==V1 else x for x in head.get('active_capabilities',[])]
head['active_capabilities']=sorted(set(head['active_capabilities']))
head['new_capabilities']=sorted(set(head.get('new_capabilities',[])+[V2]))
head['execution_fabric_v1']=head.get('execution_fabric_v1',{})|{'status':'SUPERSEDED_BY_V2','canonical_active':False,'superseded_by':V2}
head['execution_fabric_v2']={
 'status':'CANONICAL_ACTIVE','component_id':V2,
 'canonical_component_digest':canon_art['canonical_component_digest'],
 'fresh_gate_receipt_sha256':fresh.get('receipt_sha256'),
 'external_evidence_memory':'BOUNDED_METADATA_ONLY',
 'network_execution_readonly':True
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
 'schema':'yado.g2.unified_execution_fabric.v2.canonical_admission.receipt',
 'status':'PASS_G2_UNIFIED_EXECUTION_FABRIC_V2_CANONICAL_ADMISSION',
 'component_id':V2,'parent_component':V1,
 'fresh_gate_receipt_sha256':fresh.get('receipt_sha256'),
 'active_capability_count_after':len(head['active_capabilities']),
 'external_evidence_memory':'BOUNDED_METADATA_ONLY',
 'network_execution_readonly':True,
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest'],
 'frontier_unchanged':FRONT,'canonical_mutation':True,'canonical_mechanism_mutation':True,
 'architecture_mutation':False,'generation_transition':False,'g3_genesis_performed':False,
 'semantic_boundary':'SAME-G2 FABRIC REPLACEMENT V1->V2. NO FORMAL GENERATION TRANSITION.'
}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)
e={
 'index':len(ledger['events']),
 'event_id':f"E{len(ledger['events'])+1:04d}_G2_UNIFIED_EXECUTION_FABRIC_V2_CANONICAL_ADMISSION",
 'event_type':'G2_UNIFIED_EXECUTION_FABRIC_V2_CANONICAL_ADMISSION','status':'PASS_CANONICAL',
 'generation':ledger['current_head'],'deficit':'CROSS_LAYER_API_DISPATCH_AND_EXTERNAL_EVIDENCE_MEMORY_GAPS',
 'effect':f"REPLACED_ACTIVE={V1}->{V2}; API_DISPATCH=True; EXTERNAL_EVIDENCE_MEMORY=True; ACTIVE_CAPS={len(head['active_capabilities'])}; FRONTIER_UNCHANGED={FRONT}",
 'source_path':f'receipts/yado-g2-unified-execution-fabric-v2-canonical-admission-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':True,'canonical_mechanism_mutation':True,'architecture_mutation':False,'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']
}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);write(LEDGER,ledger)

post=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=90)
if post.returncode!=0:raise RuntimeError('POST_FABRIC_V2_CANONICAL_GUARD_FAILED:'+post.stdout[-6000:]+post.stderr[-2000:])
print(json.dumps({'status':receipt['status'],'active_capability_count_after':len(head['active_capabilities']),'component_id':V2,'frontier':FRONT},indent=2,sort_keys=True))
