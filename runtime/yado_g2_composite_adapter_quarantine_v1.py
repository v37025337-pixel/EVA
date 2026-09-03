from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,subprocess,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
PATCH=REPO/'canonical/yado-g2-active-patch-registry-v1.json'
COMP_CANON=REPO/'canonical/yado-g2-composite-executable-successor-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
ABL=REPO/'candidates/kernel-self-generated/g2-composite-adapter-fresh-ablation-v2.json'
Q=REPO/'quarantine/compatibility-modules/yado-g2-composite-transfer-repair-adapter-v1.json'
OUT=ROOT/'yado_g2_composite_adapter_quarantine_v1_receipt.json'
GUARD=ROOT/'yado_canonical_invariant_guard_v1.py'

COMP='ALG-G2-COMPOSITE-TRANSFER-REPAIR-ADAPTER-V1'
SRC='runtime/yado_g2_composite_transfer_repair_adapter_v1.py'
FRONT='KERNEL_G2_RAW_REPRESENTATION_V5_CANONICAL_ADMISSION_V1'

def load(p):return json.loads(p.read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):x=copy.deepcopy(o);x.pop(field,None);return h(x)

head,core,prov,patches,compcanon,ledger,abl=map(load,[HEAD,CORE,PROV,PATCH,COMP_CANON,LEDGER,ABL])
validate_ledger_v2(ledger)
if head.get('current_frontier')!=FRONT or ledger.get('open_deficits')!=[FRONT]:raise RuntimeError('FRONTIER_DRIFT')
if head.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')
if abl.get('status')!='PASS_COMPOSITE_ADAPTER_REDUNDANT_PAIRED_FRESH_V2' or abl.get('removal_authorized') is not True:
    raise RuntimeError('ABLATION_DOES_NOT_AUTHORIZE_QUARANTINE')
if COMP not in head.get('active_capabilities',[]):raise RuntimeError('COMPOSITE_NOT_ACTIVE_BEFORE_QUARANTINE')
if SRC not in core.get('active_runtime_sources',[]):raise RuntimeError('COMPOSITE_SOURCE_NOT_ACTIVE_BEFORE_QUARANTINE')
src_sha=fsha(REPO/SRC)
if src_sha!=compcanon.get('runtime_sha256'):raise RuntimeError('COMPOSITE_SOURCE_HASH_DRIFT')

old_patch=next((x for x in patches.get('patches',[]) if x.get('component_id')==COMP),None)
if not old_patch:raise RuntimeError('ACTIVE_PATCH_BINDING_MISSING')

quarantine={
 'schema':'yado.g2.compatibility_module_quarantine.v1',
 'status':'QUARANTINED_REDUNDANT',
 'generation':head.get('generation_id'),
 'component_id':COMP,
 'source':SRC,
 'source_sha256':src_sha,
 'runtime_active':False,
 'source_retained_for_historical_reproducibility':True,
 'fresh_ablation':{
   'artifact':'candidates/kernel-self-generated/g2-composite-adapter-fresh-ablation-v2.json',
   'receipt_sha256':abl.get('receipt_sha256'),
   'status':abl.get('status'),
   'paired_count':abl.get('paired',{}).get('count'),
   'paired_exact':abl.get('paired',{}).get('ambiguous_exact'),
   'causal_drop_direct':abl.get('aggregate',{}).get('direct_context_fabric',{}).get('causal_drop'),
   'causal_drop_composite':abl.get('aggregate',{}).get('composite',{}).get('causal_drop'),
 },
 'prior_active_patch':old_patch,
 'prior_canonical_component':compcanon,
 'replacement_path':[
   'ALG-G2-CONTEXTUAL-STREAM-CAPABILITY-ADAPTER-V1',
   'RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V1'
 ],
 'readmission_policy':'FRESH_ADMISSION_REQUIRED',
 'semantic_boundary':'COMPONENT IS PRESERVED AS HISTORICAL REPRODUCIBILITY SOURCE BUT REMOVED FROM CURRENT ACTIVE G2 AFTER PAIRED FRESH EQUIVALENCE ABLATION.'
}
quarantine['quarantine_digest']=cdig(quarantine,'quarantine_digest');write(Q,quarantine)

# Active patch registry: move the redundant adapter to quarantined history.
patches['patches']=[x for x in patches.get('patches',[]) if x.get('component_id')!=COMP]
qp=list(patches.get('quarantined_patches',[]))
qp=[x for x in qp if x.get('component_id')!=COMP]
qp.append({
 'patch_id':old_patch.get('patch_id'),'component_id':COMP,'status':'QUARANTINED_REDUNDANT',
 'source':SRC,'source_sha256':src_sha,'prior_evidence':old_patch.get('evidence',[]),
 'quarantine_artifact':'quarantine/compatibility-modules/yado-g2-composite-transfer-repair-adapter-v1.json',
 'quarantine_digest':quarantine['quarantine_digest'],'ablation_receipt_sha256':abl.get('receipt_sha256')
})
patches['quarantined_patches']=qp
patches['all_active_patch_bindings_verified']=all(x.get('status')=='PASS' and x.get('source_hash_ok') and x.get('evidence_ok') for x in patches['patches'])
patches['registry_digest']=cdig(patches,'registry_digest');write(PATCH,patches)

# Preserve canonical component artifact but mark inactive/quarantined.
compcanon['status']='QUARANTINED_REDUNDANT'
compcanon['canonical_active']=False
compcanon['quarantine_artifact']='quarantine/compatibility-modules/yado-g2-composite-transfer-repair-adapter-v1.json'
compcanon['quarantine_digest']=quarantine['quarantine_digest']
compcanon['paired_fresh_ablation_receipt_sha256']=abl.get('receipt_sha256')
compcanon['semantic_boundary']='HISTORICAL CANONICAL G2 ADAPTER, NOW QUARANTINED AFTER PAIRED FRESH EQUIVALENCE TO CONTEXT MEMORY + UNIFIED EXECUTION FABRIC. SOURCE RETAINED FOR REPRODUCIBILITY.'
compcanon['canonical_component_digest']=cdig(compcanon,'canonical_component_digest');write(COMP_CANON,compcanon)

# Remove from every active architecture plane and runtime integrity set.
for p in core.get('planes',[]):
    p['active_components']=[x for x in p.get('active_components',[]) if x!=COMP]
core['active_runtime_sources']=[x for x in core.get('active_runtime_sources',[]) if x!=SRC]
rim=core.get('runtime_integrity_manifest')
if not isinstance(rim,dict) or not isinstance(rim.get('sources'),dict):raise RuntimeError('RUNTIME_INTEGRITY_MANIFEST_MISSING')
rim['sources']={rel:fsha(REPO/rel) for rel in core['active_runtime_sources']}
rim['manifest_digest']=h(rim['sources'])

core['active_patch_registry']={'artifact':'canonical/yado-g2-active-patch-registry-v1.json','registry_digest':patches['registry_digest'],'status':'CANONICAL_ACTIVE'}
core.setdefault('composite_executable_successor_v1',{}).update({
 'status':'QUARANTINED_REDUNDANT','canonical_active':False,
 'quarantine_artifact':'quarantine/compatibility-modules/yado-g2-composite-transfer-repair-adapter-v1.json',
 'quarantine_digest':quarantine['quarantine_digest'],
 'paired_fresh_ablation_receipt_sha256':abl.get('receipt_sha256')
})
core['compatibility_quarantine_v1']={
 'component_id':COMP,'status':'QUARANTINED_REDUNDANT','quarantine_digest':quarantine['quarantine_digest'],
 'replacement':['ALG-G2-CONTEXTUAL-STREAM-CAPABILITY-ADAPTER-V1','RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V1']
}

prev=head['canonical_head_digest']
prov['current_g2_binding']['active_patch_registry_digest']=patches['registry_digest']
prov['current_g2_binding']['canonical_composite_component']=None
prov['current_g2_binding']['quarantined_composite_component']=COMP
prov['current_g2_binding']['composite_quarantine_digest']=quarantine['quarantine_digest']
prov['current_g2_binding']['current_execution_label']='G2_UNIFIED_EXECUTION_FABRIC_COMPOSITE_REDUNDANCY_CLOSED_V1'
prov['registry_digest']=cdig(prov,'registry_digest');write(PROV,prov)

core['algorithm_provenance_registry_digest']=prov['registry_digest']
core['current_frontier']=FRONT
core['core_digest']=cdig(core,'core_digest');write(CORE,core)

head['active_capabilities']=[x for x in head.get('active_capabilities',[]) if x!=COMP]
head['active_patch_registry']={'registry_digest':patches['registry_digest'],'status':'CANONICAL_ACTIVE'}
head.setdefault('composite_executable_successor_v1',{}).update({
 'status':'QUARANTINED_REDUNDANT','canonical_active':False,
 'quarantine_digest':quarantine['quarantine_digest'],
 'paired_fresh_ablation_receipt_sha256':abl.get('receipt_sha256')
})
head['compatibility_quarantine_v1']={
 'component_id':COMP,'status':'QUARANTINED_REDUNDANT',
 'quarantine_artifact':'quarantine/compatibility-modules/yado-g2-composite-transfer-repair-adapter-v1.json',
 'quarantine_digest':quarantine['quarantine_digest']
}
head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest']
head['algorithm_provenance_registry']['current_execution_label']=prov['current_g2_binding']['current_execution_label']
head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest']
head['unified_core']['core_digest']=core['core_digest']
head['unified_core']['runtime_integrity_manifest_digest']=rim['manifest_digest']
head['current_frontier']=FRONT
head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)

ledger['current_head_digest']=head['canonical_head_digest']
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
 'schema':'yado.g2.composite_adapter_quarantine.receipt.v1',
 'status':'PASS_G2_COMPOSITE_ADAPTER_QUARANTINE_V1',
 'component_id':COMP,'source_retained':True,'runtime_active':False,
 'active_capability_count_after':len(head['active_capabilities']),
 'active_patch_count_after':len(patches['patches']),
 'ablation_receipt_sha256':abl.get('receipt_sha256'),
 'quarantine_digest':quarantine['quarantine_digest'],
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest'],
 'frontier_unchanged':FRONT,'canonical_mutation':True,'canonical_mechanism_mutation':True,
 'architecture_mutation':False,'generation_transition':False,'g3_genesis_performed':False,
 'semantic_boundary':'SAME-G2 COMPATIBILITY CLEANUP. REDUNDANT ADAPTER REMOVED FROM ACTIVE EXECUTION AND PATCH REGISTRY AFTER PAIRED FRESH EQUIVALENCE; HISTORICAL SOURCE/EVIDENCE RETAINED.'
}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)
e={
 'index':len(ledger['events']),
 'event_id':f"E{len(ledger['events'])+1:04d}_G2_COMPOSITE_ADAPTER_QUARANTINE_V1",
 'event_type':'G2_COMPATIBILITY_MODULE_QUARANTINE','status':'PASS_CANONICAL',
 'generation':ledger['current_head'],'deficit':'REDUNDANT_COMPOSITE_COMPATIBILITY_ADAPTER',
 'effect':f"REMOVED_ACTIVE={COMP}; ACTIVE_CAPS={len(head['active_capabilities'])}; ACTIVE_PATCHES={len(patches['patches'])}; FRONTIER_UNCHANGED={FRONT}",
 'source_path':f'receipts/yado-g2-composite-adapter-quarantine-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':True,'canonical_mechanism_mutation':True,'architecture_mutation':False,'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']
}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);write(LEDGER,ledger)

post=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=90)
if post.returncode!=0:raise RuntimeError('POST_QUARANTINE_CANONICAL_GUARD_FAILED:'+post.stdout[-6000:]+post.stderr[-2000:])
print(json.dumps({'status':receipt['status'],'active_capability_count_after':len(head['active_capabilities']),'active_patch_count_after':len(patches['patches']),'quarantine_digest':quarantine['quarantine_digest'],'frontier':FRONT},indent=2,sort_keys=True))
