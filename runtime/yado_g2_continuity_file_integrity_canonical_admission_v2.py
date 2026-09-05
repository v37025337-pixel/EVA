from __future__ import annotations

from pathlib import Path
import copy,hashlib,json,os,subprocess,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent

sys.path[:0]=[str(ROOT),str(ROOT/'yado_rc8_v36')]

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_g2_unified_execution_fabric_v5 import G2UnifiedExecutionFabricV5

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
CONT=REPO/'canonical/yado-g2-cognitive-continuity-checkpoint-v1.json'
INTEGRITY=REPO/'canonical/yado-g2-continuity-file-integrity-v2.json'
SHADOW=REPO/'candidates/kernel-self-generated/g2-continuity-file-integrity-v2.json'
UNIFIED=ROOT/'yado_unified_core_v1.py'
GUARD=ROOT/'yado_canonical_invariant_guard_v1.py'
OUT=ROOT/'yado_g2_continuity_file_integrity_canonical_admission_v2_receipt.json'
TEST=REPO/'tests/test_g2_continuity_file_integrity.py'

V4='RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V4'
V5='RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V5'

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def cdig(o,field):
    x=copy.deepcopy(o);x.pop(field,None);return h(x)
def write(p,o):
    Path(p).write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

head,core,prov,ledger,cont,shadow=map(load,[HEAD,CORE,PROV,LEDGER,CONT,SHADOW])
validate_ledger_v2(ledger)
fronts=list(ledger.get('open_deficits') or [])
if len(fronts)!=1:raise RuntimeError('FRONTIER_NOT_SINGLE')
front=fronts[0]
if head.get('current_frontier')!=front or core.get('current_frontier')!=front:
    raise RuntimeError('FRONTIER_DRIFT')
if head.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')
if shadow.get('status')!='PASS_SHADOW_G2_CONTINUITY_FILE_INTEGRITY_V2':
    raise RuntimeError('FILE_INTEGRITY_SHADOW_NOT_PASS')
if os.getenv('YADO_CONTINUITY_FILE_TESTS_PASS')!='1':
    raise RuntimeError('FOCUSED_FILE_INTEGRITY_REGRESSIONS_NOT_PROVEN')
if V4 not in head.get('active_capabilities',[]):raise RuntimeError('V4_NOT_CANONICAL_ACTIVE')
if V5 in head.get('active_capabilities',[]):raise RuntimeError('V5_ALREADY_ACTIVE')

component=G2UnifiedExecutionFabricV5.component()
source_sha=fsha(ROOT/'yado_g2_unified_execution_fabric_v5.py')
test_sha=fsha(TEST)

integrity={
 'schema':'yado.g2.continuity_file_integrity.canonical.v2',
 'status':'CANONICAL_ACTIVE',
 'component_id':V5,
 'parent_execution_fabric':V4,
 'checkpoint_schema':G2UnifiedExecutionFabricV5.CHECKPOINT_SCHEMA,
 'file_schema':G2UnifiedExecutionFabricV5.FILE_SCHEMA,
 'file_encoding':G2UnifiedExecutionFabricV5.FILE_ENCODING,
 'runtime_source':'runtime/yado_g2_unified_execution_fabric_v5.py',
 'runtime_sha256':source_sha,
 'focused_test':'tests/test_g2_continuity_file_integrity.py',
 'focused_test_sha256':test_sha,
 'shadow_gate_artifact':'candidates/kernel-self-generated/g2-continuity-file-integrity-v2.json',
 'shadow_gate_receipt_sha256':shadow.get('receipt_sha256'),
 'component':component,
 'preserves_integer_dict_keys':True,
 'preserves_tuples':True,
 'preserves_fraction_exactness':True,
 'legacy_plain_json_v1_compatibility':True,
 'pre_restore_full_integrity_validation':True,
 'failed_replace_preserves_previous_checkpoint':True,
 'max_checkpoint_file_bytes':G2UnifiedExecutionFabricV5.MAX_CHECKPOINT_FILE_BYTES,
 'executable_object_deserialization':False,
 'authorship':'ASSISTANT_AUTHORED_INFRASTRUCTURE_REPAIR',
 'kernel_generated_source':False,
 'general_intelligence_gain_evidence':False,
 'architecture_mutation':False,
 'generation_transition':False,
 'automatic_canonical_promotion':False,
 'semantic_boundary':'SAME-G2 FILE-INTEGRITY SUCCESSOR V4->V5. IT PRESERVES EXACT CHECKPOINT VALUE TYPES AND FAILS CLOSED BEFORE BASE-RUNTIME RESTORE. THIS IS ASSISTANT-AUTHORED INFRASTRUCTURE REPAIR, NOT KERNEL-GENERATED SOURCE OR GENERAL-INTELLIGENCE EVIDENCE.'
}
integrity['canonical_component_digest']=cdig(integrity,'canonical_component_digest')
write(INTEGRITY,integrity)

# Rebind the unified runtime to V5.
src=UNIFIED.read_text(encoding='utf-8')
v4_import='from yado_g2_unified_execution_fabric_v4 import G2UnifiedExecutionFabricV4\n'
v5_import='from yado_g2_unified_execution_fabric_v5 import G2UnifiedExecutionFabricV5\n'
if v5_import not in src:
    if v4_import not in src:raise RuntimeError('UNIFIED_V4_IMPORT_ANCHOR_MISSING')
    src=src.replace(v4_import,v4_import+v5_import)
old='        self.execution_fabric_cls=G2UnifiedExecutionFabricV4\n'
new='        self.execution_fabric_cls=G2UnifiedExecutionFabricV5\n'
if old not in src:raise RuntimeError('UNIFIED_V4_ACTIVE_BINDING_MISSING')
src=src.replace(old,new)
UNIFIED.write_text(src,encoding='utf-8')
unified_sha=fsha(UNIFIED)

# Canonical continuity artifact now records V5 file persistence on the same v1 in-memory contract.
cont['status']='CANONICAL_ACTIVE'
cont['component_id']=V5
cont['parent_execution_fabric']=V4
cont['component']=component
cont['runtime_source']='runtime/yado_g2_unified_execution_fabric_v5.py'
cont['runtime_sha256']=source_sha
cont['checkpoint_schema']=G2UnifiedExecutionFabricV5.CHECKPOINT_SCHEMA
cont['file_schema']=G2UnifiedExecutionFabricV5.FILE_SCHEMA
cont['file_encoding']=G2UnifiedExecutionFabricV5.FILE_ENCODING
cont['typed_file_integrity']=True
cont['preserves_integer_dict_keys']=True
cont['preserves_tuples']=True
cont['preserves_fraction_exactness']=True
cont['file_integrity_canonical_artifact']='canonical/yado-g2-continuity-file-integrity-v2.json'
cont['file_integrity_shadow_receipt_sha256']=shadow.get('receipt_sha256')
cont['semantic_boundary']='SAME-G2 CONTINUITY CONTRACT WITH V5 FILE-INTEGRITY PERSISTENCE. IN-MEMORY CHECKPOINT REMAINS V1; NEW FILES USE TYPED V2 ENVELOPES. INFRASTRUCTURE REPAIR ONLY.'
cont['canonical_component_digest']=cdig(cont,'canonical_component_digest')
write(CONT,cont)

def plane(pid):
    p=next((x for x in core.get('planes',[]) if x.get('plane_id')==pid),None)
    if p is None:raise RuntimeError('MISSING_PLANE:'+pid)
    return p

workspace=plane('WORKSPACE_AND_INTEGRATION')
memory=plane('MEMORY_AND_EXPERIENCE')
audit=plane('SELF_AUDIT_AND_REPAIR')
workspace['active_components']=sorted(set(V5 if x==V4 else x for x in workspace.get('active_components',[])))
memory['responsibilities']=sorted(set(memory.get('responsibilities',[])+[
 'typed_checkpoint_value_preservation','exact_fraction_tuple_integer_key_restore'
]))
workspace['responsibilities']=sorted(set(workspace.get('responsibilities',[])+[
 'typed_continuity_file_v2','pre_restore_checkpoint_integrity'
]))
audit['responsibilities']=sorted(set(audit.get('responsibilities',[])+[
 'continuity_file_digest_validation','typed_checkpoint_decode_fail_closed'
]))

core['execution_fabric_v4']=core.get('execution_fabric_v4',{})|{
 'status':'SUPERSEDED_BY_V5','canonical_active':False,'superseded_by':V5
}
core['execution_fabric_v5']={
 'status':'CANONICAL_ACTIVE','component_id':V5,'parent_component':V4,
 'canonical_component_digest':integrity['canonical_component_digest'],
 'runtime_sha256':source_sha,
 'shadow_gate_receipt_sha256':shadow.get('receipt_sha256'),
 'checkpoint_schema':G2UnifiedExecutionFabricV5.CHECKPOINT_SCHEMA,
 'file_schema':G2UnifiedExecutionFabricV5.FILE_SCHEMA,
 'file_encoding':G2UnifiedExecutionFabricV5.FILE_ENCODING,
 'typed_value_preservation':True,
 'pre_restore_full_integrity_validation':True,
 'architecture_mutation':False
}
core['cognitive_continuity_checkpoint_v1']=core.get('cognitive_continuity_checkpoint_v1',{})|{
 'status':'CANONICAL_ACTIVE','component_id':V5,'parent_execution_fabric':V4,
 'checkpoint_schema':G2UnifiedExecutionFabricV5.CHECKPOINT_SCHEMA,
 'file_schema':G2UnifiedExecutionFabricV5.FILE_SCHEMA,
 'file_integrity_artifact':'canonical/yado-g2-continuity-file-integrity-v2.json',
 'file_integrity_shadow_receipt_sha256':shadow.get('receipt_sha256'),
 'typed_value_preservation':True
}
core['cognitive_temporal_kernel_v1']=core.get('cognitive_temporal_kernel_v1',{})|{
 'execution_fabric':V5,
 'state_persistence':'UNIFIED_TYPED_ATOMIC_TEMPORAL_RECURRENT_CHECKPOINT'
}
active_sources=set(core.get('active_runtime_sources',[]))
active_sources.add('runtime/yado_g2_unified_execution_fabric_v5.py')
# V4 remains an active source dependency because V5 subclasses it.
active_sources.add('runtime/yado_g2_unified_execution_fabric_v4.py')
core['active_runtime_sources']=sorted(active_sources)
rim=core.get('runtime_integrity_manifest')
if not isinstance(rim,dict) or not isinstance(rim.get('sources'),dict):
    raise RuntimeError('RUNTIME_INTEGRITY_MANIFEST_MISSING')
rim['sources']={rel:fsha(REPO/rel) for rel in core['active_runtime_sources']}
rim['manifest_digest']=h(rim['sources'])

prev=head['canonical_head_digest']

prov['current_g2_binding'].update({
 'current_execution_label':'G2_COGNITIVE_CONTINUITY_FILE_INTEGRITY_V5_CANONICAL',
 'frontier':front,
 'execution_fabric_component':V5,
 'execution_fabric_parent_component':V4,
 'execution_fabric_v5_source_sha256':source_sha,
 'cognitive_continuity_checkpoint':'canonical/yado-g2-cognitive-continuity-checkpoint-v1.json',
 'cognitive_continuity_checkpoint_schema':G2UnifiedExecutionFabricV5.CHECKPOINT_SCHEMA,
 'cognitive_continuity_file_schema':G2UnifiedExecutionFabricV5.FILE_SCHEMA,
 'cognitive_continuity_file_integrity_artifact':'canonical/yado-g2-continuity-file-integrity-v2.json',
 'cognitive_continuity_file_integrity_shadow_receipt_sha256':shadow.get('receipt_sha256'),
 'typed_checkpoint_value_preservation':True,
 'pre_restore_full_integrity_validation':True,
})
prov['registry_digest']=cdig(prov,'registry_digest')
write(PROV,prov)

core['algorithm_provenance_registry_digest']=prov['registry_digest']
core['runtime_sha256']=unified_sha
core['current_frontier']=front
core['core_digest']=cdig(core,'core_digest')
write(CORE,core)

head['active_capabilities']=sorted(set(V5 if x==V4 else x for x in head.get('active_capabilities',[])))
head['new_capabilities']=sorted(set(head.get('new_capabilities',[])+[V5]))
head['execution_fabric_v4']=head.get('execution_fabric_v4',{})|{
 'status':'SUPERSEDED_BY_V5','canonical_active':False,'superseded_by':V5
}
head['execution_fabric_v5']={
 'status':'CANONICAL_ACTIVE','component_id':V5,'parent_component':V4,
 'canonical_component_digest':integrity['canonical_component_digest'],
 'shadow_gate_receipt_sha256':shadow.get('receipt_sha256'),
 'checkpoint_schema':G2UnifiedExecutionFabricV5.CHECKPOINT_SCHEMA,
 'file_schema':G2UnifiedExecutionFabricV5.FILE_SCHEMA,
 'typed_value_preservation':True,
 'pre_restore_full_integrity_validation':True
}
head['cognitive_continuity_checkpoint_v1']=head.get('cognitive_continuity_checkpoint_v1',{})|{
 'status':'CANONICAL_ACTIVE','component_id':V5,'parent_execution_fabric':V4,
 'checkpoint_schema':G2UnifiedExecutionFabricV5.CHECKPOINT_SCHEMA,
 'file_schema':G2UnifiedExecutionFabricV5.FILE_SCHEMA,
 'file_integrity_shadow_receipt_sha256':shadow.get('receipt_sha256'),
 'typed_value_preservation':True
}
head['cognitive_temporal_kernel_v1']=head.get('cognitive_temporal_kernel_v1',{})|{
 'execution_fabric':V5,
 'state_persistence':'UNIFIED_TYPED_ATOMIC_TEMPORAL_RECURRENT_CHECKPOINT'
}
head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest']
head['algorithm_provenance_registry']['current_execution_label']=prov['current_g2_binding']['current_execution_label']
head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest']
head['unified_core']['core_digest']=core['core_digest']
head['unified_core']['runtime_sha256']=unified_sha
head['unified_core']['runtime_integrity_manifest_digest']=rim['manifest_digest']
head['current_frontier']=front
head['canonical_head_digest']=cdig(head,'canonical_head_digest')
write(HEAD,head)

ledger['current_head_digest']=head['canonical_head_digest']
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
 'schema':'yado.g2.continuity_file_integrity.canonical_admission.receipt.v2',
 'status':'PASS_G2_CONTINUITY_FILE_INTEGRITY_CANONICAL_ADMISSION_V2',
 'execution_fabric':V5,'parent_execution_fabric':V4,
 'checkpoint_schema':G2UnifiedExecutionFabricV5.CHECKPOINT_SCHEMA,
 'file_schema':G2UnifiedExecutionFabricV5.FILE_SCHEMA,
 'shadow_gate_receipt_sha256':shadow.get('receipt_sha256'),
 'focused_regressions_pass':True,
 'source_sha256':source_sha,'test_sha256':test_sha,
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest'],
 'frontier_unchanged':front,
 'canonical_mutation':True,'canonical_mechanism_mutation':True,
 'architecture_mutation':False,'generation_transition':False,'g3_genesis_performed':False,
 'assistant_authored_infrastructure_repair':True,
 'kernel_generated_source':False,'general_intelligence_gain_evidence':False,
 'automatic_canonical_promotion':False,
}
receipt['receipt_sha256']=h(receipt)
write(OUT,receipt)
receipt_path=REPO/'receipts'/f'yado-g2-continuity-file-integrity-canonical-admission-v2-run-{run_id}.json'
write(receipt_path,receipt)

e={
 'index':len(ledger['events']),
 'event_id':f"E{len(ledger['events'])+1:04d}_G2_CONTINUITY_FILE_INTEGRITY_CANONICAL_ADMISSION_V2",
 'event_type':'G2_CONTINUITY_FILE_INTEGRITY_CANONICAL_ADMISSION','status':'PASS_CANONICAL',
 'generation':ledger['current_head'],
 'deficit':'COGNITIVE_CONTINUITY_FILE_TYPE_INTEGRITY_GAP',
 'effect':f"REPLACED_ACTIVE={V4}->{V5}; FILE_SCHEMA={G2UnifiedExecutionFabricV5.FILE_SCHEMA}; TYPED_VALUE_PRESERVATION=True; PRE_RESTORE_VALIDATION=True; FRONTIER_UNCHANGED={front}",
 'source_path':str(receipt_path.relative_to(REPO)),
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':True,'canonical_mechanism_mutation':True,
 'architecture_mutation':False,'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']
}
e['event_hash']=event_hash(e)
ledger['events'].append(e)
ledger['event_count']=len(ledger['events'])
ledger['tail_event_hash']=e['event_hash']
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger)
write(LEDGER,ledger)

post=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=90)
if post.returncode!=0:
    raise RuntimeError('POST_V5_CANONICAL_GUARD_FAILED:'+post.stdout[-7000:]+post.stderr[-3000:])
probe=subprocess.run([
 sys.executable,'-c',
 "import sys;from pathlib import Path;sys.path[:0]=['runtime','runtime/yado_rc8_v36'];from yado_unified_core_v1 import UnifiedYADOCoreV1;c=UnifiedYADOCoreV1(Path('.'));assert c.execution_fabric_cls.COMPONENT_ID=='RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V5';print(c.execution_fabric_cls.COMPONENT_ID)"
],cwd=REPO,capture_output=True,text=True,timeout=90)
if probe.returncode!=0:
    raise RuntimeError('POST_V5_CORE_BINDING_FAILED:'+probe.stdout+probe.stderr)

print(json.dumps({
 'status':receipt['status'],'execution_fabric':V5,'parent_execution_fabric':V4,
 'checkpoint_schema':receipt['checkpoint_schema'],'file_schema':receipt['file_schema'],
 'frontier':front,'new_head_digest':head['canonical_head_digest'],
 'receipt_sha256':receipt['receipt_sha256']
},indent=2,sort_keys=True))
