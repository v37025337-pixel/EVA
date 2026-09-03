from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,subprocess,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_g2_unified_execution_fabric_v3 import G2UnifiedExecutionFabricV3
from yado_g2_cognitive_clock_v1 import G2CognitiveClockV1

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
FRESH=REPO/'candidates/kernel-self-generated/g2-cognitive-temporal-kernel-v1.json'
CANON=REPO/'canonical/yado-g2-cognitive-temporal-kernel-v1.json'
UNIFIED=ROOT/'yado_unified_core_v1.py'
OUT=ROOT/'yado_g2_cognitive_temporal_kernel_canonical_admission_v1_receipt.json'
GUARD=ROOT/'yado_canonical_invariant_guard_v1.py'

V2='RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V2'
V3='RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V3'
CLOCK='RUNTIME-G2-COGNITIVE-TEMPORAL-KERNEL-V1'
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
if fresh.get('status')!='PASS_SHADOW_G2_COGNITIVE_TEMPORAL_KERNEL_V1':raise RuntimeError('TEMPORAL_FRESH_GATE_NOT_PASS')
if not all(fresh.get('checks',{}).values()):raise RuntimeError('TEMPORAL_FRESH_CHECK_FAILED')
if V2 not in head.get('active_capabilities',[]):raise RuntimeError('FABRIC_V2_NOT_ACTIVE_BEFORE_REPLACEMENT')
if V3 in head.get('active_capabilities',[]):raise RuntimeError('FABRIC_V3_ALREADY_ACTIVE')
if CLOCK in head.get('active_capabilities',[]):raise RuntimeError('CLOCK_MUST_NOT_BE_SEPARATE_ACTIVE_CAPABILITY')

fabric_component=G2UnifiedExecutionFabricV3.component()
clock_component=G2CognitiveClockV1.component()
canon_art={
 'schema':'yado.g2.cognitive_temporal_kernel.canonical.v1',
 'status':'CANONICAL_EMBEDDED',
 'temporal_kernel_id':CLOCK,
 'execution_fabric_id':V3,
 'parent_execution_fabric':V2,
 'temporal_kernel':clock_component,
 'execution_fabric':fabric_component,
 'clock_runtime_source':'runtime/yado_g2_cognitive_clock_v1.py',
 'clock_runtime_sha256':fsha(ROOT/'yado_g2_cognitive_clock_v1.py'),
 'fabric_runtime_source':'runtime/yado_g2_unified_execution_fabric_v3.py',
 'fabric_runtime_sha256':fsha(ROOT/'yado_g2_unified_execution_fabric_v3.py'),
 'fresh_gate_artifact':'candidates/kernel-self-generated/g2-cognitive-temporal-kernel-v1.json',
 'fresh_gate_receipt_sha256':fresh.get('receipt_sha256'),
 'fresh_checks':fresh.get('checks'),
 'separate_active_capability':False,
 'logical_tick_ordering':True,
 'episode_time':True,
 'causal_predecessor_time':True,
 'wall_time_external_sync_only':True,
 'entity_age':True,
 'no_progress_ticks':True,
 'stall_threshold':G2CognitiveClockV1.DEFAULT_STALL_THRESHOLD,
 'temporal_stall_to_evolution_signal':True,
 'temporal_state_persistence':'EXPLICIT_EXPORT_RESTORE_CHECKPOINT',
 'automatic_canonical_promotion':False,
 'architecture_mutation':False,
 'semantic_boundary':'CANONICAL EMBEDDED TEMPORAL KERNEL INSIDE FABRIC V3. LOGICAL TICKS DEFINE COGNITIVE ORDER; WALL TIME IS EXTERNAL SYNCHRONIZATION METADATA. TEMPORAL STALL MAY TRIGGER SHADOW EVOLUTION ONLY.'
}
canon_art['canonical_component_digest']=cdig(canon_art,'canonical_component_digest');write(CANON,canon_art)

# Patch UnifiedYADOCoreV1 to instantiate V3 and expose explicit temporal checkpoint/evolution bridges.
src=UNIFIED.read_text(encoding='utf-8')
v2_import='from yado_g2_unified_execution_fabric_v2 import G2UnifiedExecutionFabricV2\n'
v3_import='from yado_g2_unified_execution_fabric_v3 import G2UnifiedExecutionFabricV3\n'
if v3_import not in src:
    if v2_import not in src:raise RuntimeError('UNIFIED_V2_IMPORT_ANCHOR_MISSING')
    src=src.replace(v2_import,v2_import+v3_import)
src=src.replace('        self.execution_fabric_cls=G2UnifiedExecutionFabricV2\n','        self.execution_fabric_cls=G2UnifiedExecutionFabricV3\n')
old_inst="""    def instantiate_execution_fabric(self,router_program,scalar_program,relation_program,api_state=None):
        base=G2TypedRecurrentCapabilityGraphRuntimeV1(
            self.architecture,router_program,scalar_program,relation_program,self.portfolio
        )
        return self.execution_fabric_cls(base,api_state=api_state)
"""
new_inst="""    def instantiate_execution_fabric(self,router_program,scalar_program,relation_program,api_state=None,temporal_state=None):
        base=G2TypedRecurrentCapabilityGraphRuntimeV1(
            self.architecture,router_program,scalar_program,relation_program,self.portfolio
        )
        return self.execution_fabric_cls(base,api_state=api_state,temporal_state=temporal_state)
"""
if old_inst in src:src=src.replace(old_inst,new_inst)
elif 'def instantiate_execution_fabric(self,router_program,scalar_program,relation_program,api_state=None,temporal_state=None):' not in src:
    raise RuntimeError('UNIFIED_INSTANTIATE_FABRIC_ANCHOR_MISSING')

snap_anchor='    def snapshot(self)->dict[str,Any]:\n'
temporal_methods="""    def export_cognitive_temporal_state(self,execution_fabric)->dict[str,Any]:
        if not hasattr(execution_fabric,'export_temporal_state'):
            raise TypeError('TEMPORAL_EXECUTION_FABRIC_REQUIRED')
        return execution_fabric.export_temporal_state()

    def temporal_evolution_on_stall(self,execution_fabric,stream_id:str)->dict[str,Any]:
        if not hasattr(execution_fabric,'temporal_evolution_signal'):
            raise TypeError('TEMPORAL_EXECUTION_FABRIC_REQUIRED')
        signal=execution_fabric.temporal_evolution_signal(stream_id)
        if not signal.get('mechanism_change_required'):
            return {'status':'CONTINUE_CURRENT_MECHANISM','temporal_signal':signal,'promotion_authorized':False}
        evolution=self.evolve_cognitive_code_genome()
        return {
          'status':'SHADOW_EVOLUTION_TRIGGERED',
          'temporal_signal':signal,
          'evolution':evolution,
          'promotion_authorized':False,
          'semantic_boundary':'TEMPORAL STALL MAY TRIGGER SHADOW GENOME EVOLUTION BUT CANNOT PROMOTE THE CHILD.'
        }

"""
if 'def temporal_evolution_on_stall(' not in src:
    if snap_anchor not in src:raise RuntimeError('UNIFIED_SNAPSHOT_ANCHOR_MISSING')
    src=src.replace(snap_anchor,temporal_methods+snap_anchor)
if 'self.execution_fabric_cls=G2UnifiedExecutionFabricV3' not in src:raise RuntimeError('UNIFIED_FABRIC_V3_BINDING_FAILED')
UNIFIED.write_text(src,encoding='utf-8')
unified_sha=fsha(UNIFIED)

def plane(pid):
    p=next((x for x in core.get('planes',[]) if x.get('plane_id')==pid),None)
    if p is None:raise RuntimeError('MISSING_PLANE:'+pid)
    return p

identity=plane('IDENTITY_AND_LINEAGE')
memory=plane('MEMORY_AND_EXPERIENCE')
thinking=plane('THINKING_AND_PLANNING')
intel=plane('INTELLIGENCE_AND_META_SELECTION')
workspace=plane('WORKSPACE_AND_INTEGRATION')
resource=plane('RESOURCE_AND_EVIDENCE')
audit=plane('SELF_AUDIT_AND_REPAIR')

workspace['active_components']=[V3 if x==V2 else x for x in workspace.get('active_components',[])]
workspace['active_components']=sorted(set(workspace['active_components']))
identity['responsibilities']=sorted(set(identity.get('responsibilities',[])+['logical_tick_lineage','causal_predecessor_tick_lineage']))
memory['responsibilities']=sorted(set(memory.get('responsibilities',[])+[
 'temporal_transition_memory','tick_created_and_last_used_metadata','entity_age_ticks','no_progress_tick_state'
]))
thinking['responsibilities']=sorted(set(thinking.get('responsibilities',[])+['temporal_no_progress_awareness','ordered_observation_to_next_decision']))
intel['responsibilities']=sorted(set(intel.get('responsibilities',[])+['temporal_stall_to_shadow_evolution_signal']))
workspace['responsibilities']=sorted(set(workspace.get('responsibilities',[])+[
 'global_monotonic_cognitive_ticks','per_stream_episode_time','nested_parent_tick_causality','temporal_state_export_restore'
]))
resource['responsibilities']=sorted(set(resource.get('responsibilities',[])+['wall_time_external_synchronization_only']))
audit['responsibilities']=sorted(set(audit.get('responsibilities',[])+['stall_threshold_mechanism_change_signal']))

core['execution_fabric_v2']=core.get('execution_fabric_v2',{})|{
 'status':'SUPERSEDED_BY_V3','canonical_active':False,'superseded_by':V3
}
core['execution_fabric_v3']={
 'status':'CANONICAL_ACTIVE','component_id':V3,
 'canonical_component_digest':canon_art['canonical_component_digest'],
 'runtime_sha256':canon_art['fabric_runtime_sha256'],
 'fresh_gate_receipt_sha256':fresh.get('receipt_sha256'),
 'temporal_kernel':CLOCK,'temporal_kernel_embedded':True,
 'logical_tick_ordering':True,'no_progress_detection':True,
 'temporal_stall_to_evolution_signal':True,'architecture_mutation':False
}
core['cognitive_temporal_kernel_v1']={
 'status':'CANONICAL_EMBEDDED','component_id':CLOCK,
 'execution_fabric':V3,'separate_active_capability':False,
 'runtime_sha256':canon_art['clock_runtime_sha256'],
 'fresh_gate_receipt_sha256':fresh.get('receipt_sha256'),
 'logical_tick':True,'episode_time':True,'causal_time':True,'wall_time':True,
 'wall_time_external_sync_only':True,'entity_age':True,'no_progress_ticks':True,
 'stall_threshold':G2CognitiveClockV1.DEFAULT_STALL_THRESHOLD,
 'state_persistence':'EXPLICIT_EXPORT_RESTORE_CHECKPOINT',
 'automatic_canonical_promotion':False
}

active_sources=set(core.get('active_runtime_sources',[]))
active_sources.update({'runtime/yado_g2_cognitive_clock_v1.py','runtime/yado_g2_unified_execution_fabric_v3.py'})
core['active_runtime_sources']=sorted(active_sources)
rim=core.get('runtime_integrity_manifest')
if not isinstance(rim,dict) or not isinstance(rim.get('sources'),dict):raise RuntimeError('RUNTIME_INTEGRITY_MANIFEST_MISSING')
rim['sources']={rel:fsha(REPO/rel) for rel in core['active_runtime_sources']}
rim['manifest_digest']=h(rim['sources'])
core['runtime_sha256']=unified_sha

prev=head['canonical_head_digest']
prov['current_g2_binding'].update({
 'current_execution_label':'G2_UNIFIED_EXECUTION_FABRIC_V3_TEMPORAL_CONTINUITY_ACTIVE',
 'frontier':FRONT,
 'execution_fabric_component':V3,
 'execution_fabric_parent_component':V2,
 'execution_fabric_v3_source_sha256':canon_art['fabric_runtime_sha256'],
 'cognitive_temporal_kernel':CLOCK,
 'cognitive_temporal_kernel_source_sha256':canon_art['clock_runtime_sha256'],
 'cognitive_temporal_kernel_fresh_receipt_sha256':fresh.get('receipt_sha256'),
 'temporal_stall_to_shadow_evolution':True,
 'automatic_temporal_child_promotion':False,
})
prov['registry_digest']=cdig(prov,'registry_digest');write(PROV,prov)

core['algorithm_provenance_registry_digest']=prov['registry_digest']
core['current_frontier']=FRONT
core['core_digest']=cdig(core,'core_digest');write(CORE,core)

head['active_capabilities']=[V3 if x==V2 else x for x in head.get('active_capabilities',[])]
head['active_capabilities']=sorted(set(head['active_capabilities']))
head['new_capabilities']=sorted(set(head.get('new_capabilities',[])+[V3]))
head['execution_fabric_v2']=head.get('execution_fabric_v2',{})|{'status':'SUPERSEDED_BY_V3','canonical_active':False,'superseded_by':V3}
head['execution_fabric_v3']={
 'status':'CANONICAL_ACTIVE','component_id':V3,
 'canonical_component_digest':canon_art['canonical_component_digest'],
 'fresh_gate_receipt_sha256':fresh.get('receipt_sha256'),
 'temporal_kernel':CLOCK,'temporal_kernel_embedded':True,
 'temporal_stall_to_evolution_signal':True
}
head['cognitive_temporal_kernel_v1']={
 'status':'CANONICAL_EMBEDDED','component_id':CLOCK,
 'execution_fabric':V3,'separate_active_capability':False,
 'fresh_gate_receipt_sha256':fresh.get('receipt_sha256'),
 'stall_threshold':G2CognitiveClockV1.DEFAULT_STALL_THRESHOLD,
 'automatic_canonical_promotion':False
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
 'schema':'yado.g2.cognitive_temporal_kernel.canonical_admission.receipt.v1',
 'status':'PASS_G2_COGNITIVE_TEMPORAL_KERNEL_CANONICAL_ADMISSION_V1',
 'execution_fabric':V3,'parent_execution_fabric':V2,'temporal_kernel':CLOCK,
 'temporal_kernel_separate_active_capability':False,
 'active_capability_count_after':len(head['active_capabilities']),
 'fresh_gate_receipt_sha256':fresh.get('receipt_sha256'),
 'stall_threshold':G2CognitiveClockV1.DEFAULT_STALL_THRESHOLD,
 'temporal_stall_to_shadow_evolution':True,'automatic_canonical_promotion':False,
 'state_persistence':'EXPLICIT_EXPORT_RESTORE_CHECKPOINT',
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest'],
 'frontier_unchanged':FRONT,'canonical_mutation':True,'canonical_mechanism_mutation':True,
 'architecture_mutation':False,'generation_transition':False,'g3_genesis_performed':False,
 'semantic_boundary':'SAME-G2 REPLACEMENT V2->V3 ADDING EMBEDDED LOGICAL COGNITIVE TIME. NO CLAIM THAT TEMPORAL CONTINUITY ALONE IMPLIES CONSCIOUSNESS.'
}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)
e={
 'index':len(ledger['events']),
 'event_id':f"E{len(ledger['events'])+1:04d}_G2_COGNITIVE_TEMPORAL_KERNEL_CANONICAL_ADMISSION_V1",
 'event_type':'G2_COGNITIVE_TEMPORAL_KERNEL_CANONICAL_ADMISSION','status':'PASS_CANONICAL',
 'generation':ledger['current_head'],'deficit':'NO_GLOBAL_LOGICAL_COGNITIVE_TIME_OR_CAUSAL_TICK_CONTINUITY',
 'effect':f"REPLACED_ACTIVE={V2}->{V3}; EMBEDDED={CLOCK}; STALL_THRESHOLD=20; AUTO_PROMOTION=False; ACTIVE_CAPS={len(head['active_capabilities'])}; FRONTIER_UNCHANGED={FRONT}",
 'source_path':f'receipts/yado-g2-cognitive-temporal-kernel-canonical-admission-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':True,'canonical_mechanism_mutation':True,'architecture_mutation':False,'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']
}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);write(LEDGER,ledger)

post=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=90)
if post.returncode!=0:raise RuntimeError('POST_TEMPORAL_CANONICAL_GUARD_FAILED:'+post.stdout[-6000:]+post.stderr[-2000:])
print(json.dumps({
 'status':receipt['status'],'execution_fabric':V3,'temporal_kernel':CLOCK,
 'active_capability_count_after':len(head['active_capabilities']),
 'temporal_kernel_separate_active_capability':False,'frontier':FRONT
},indent=2,sort_keys=True))
