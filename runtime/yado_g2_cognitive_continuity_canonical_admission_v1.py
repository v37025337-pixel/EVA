from __future__ import annotations

from pathlib import Path
import copy,hashlib,json,os,subprocess,sys,tempfile

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_bounded_capability_router_v1 import BoundedCapabilityRouterLearnerV1
from yado_conjunctive_rule_inducer_v1 import ConjunctiveRuleInducerV1
from yado_g2_typed_recurrent_capability_graph_runtime_v1 import G2TypedRecurrentCapabilityGraphRuntimeV1
from yado_g2_unified_execution_fabric_v1 import CAP_BUD,CAP_THINK_V2
from yado_g2_unified_execution_fabric_v4 import G2UnifiedExecutionFabricV4

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
ARCH=REPO/'canonical/yado-g2-architecture-v1.json'
PORT=REPO/'resources/yado-unified-external-resource-portfolio-v1.json'
FRESH=REPO/'candidates/kernel-self-generated/g2-cognitive-continuity-checkpoint-v1.json'
CANON=REPO/'canonical/yado-g2-cognitive-continuity-checkpoint-v1.json'
UNIFIED=ROOT/'yado_unified_core_v1.py'
GUARD=ROOT/'yado_canonical_invariant_guard_v1.py'
OUT=ROOT/'yado_g2_cognitive_continuity_canonical_admission_v1_receipt.json'

V3='RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V3'
V4='RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V4'
CLOCK='RUNTIME-G2-COGNITIVE-TEMPORAL-KERNEL-V1'
BASE='RUNTIME-G2-TYPED-RECURRENT-CAPABILITY-GRAPH-V1'
CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,o):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):
    x=copy.deepcopy(o);x.pop(field,None);return h(x)

head,core,prov,ledger,arch,portfolio,fresh=map(load,[HEAD,CORE,PROV,LEDGER,ARCH,PORT,FRESH])
validate_ledger_v2(ledger)
fronts=list(ledger.get('open_deficits') or [])
if len(fronts)!=1:raise RuntimeError('FRONTIER_NOT_SINGLE')
FRONT=fronts[0]
if head.get('current_frontier')!=FRONT or core.get('current_frontier')!=FRONT:
    raise RuntimeError('FRONTIER_DRIFT')
if head.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')
if fresh.get('status')!='PASS_SHADOW_G2_COGNITIVE_CONTINUITY_CHECKPOINT_V1':
    raise RuntimeError('CONTINUITY_SHADOW_GATE_NOT_PASS')
if not all(fresh.get('checks',{}).values()):
    raise RuntimeError('CONTINUITY_SHADOW_CHECK_FAILED')
if V3 not in head.get('active_capabilities',[]):raise RuntimeError('FABRIC_V3_NOT_ACTIVE')
if V4 in head.get('active_capabilities',[]):raise RuntimeError('FABRIC_V4_ALREADY_ACTIVE')

# ---------- Independent fresh restart admission gate ----------
def desc(cap):
    d={'budget_limited':False,'quota_limited':False,'external_evidence_needed':False,'relation_needed':False,'disjunction_needed':False}
    if cap==CAP_BUD:d['budget_limited']=True
    elif cap==CAP_RES:d['external_evidence_needed']=True
    elif cap==CAP_REL:d['relation_needed']=True
    return d

route=[]
for i in range(18):
    for cap in [CAP_CONJ,CAP_REL,CAP_BUD,CAP_RES]:
        route.append({'input':desc(cap)|{'nonce':(i*7)%5},'expected':cap})
router=BoundedCapabilityRouterLearnerV1.synthesize(route,route,CAP_CONJ,min_support=4)
rows=[]
for a in [False,True]:
  for b in [False,True]:
    for c in [False,True]:
      for _ in range(4):
        rows.append({'input':{'condition_a':a,'condition_b':b,'condition_c':c},'expected':'PASS' if a and b and c else 'HOLD'})
scalar=ConjunctiveRuleInducerV1.synthesize('CONTINUITY_CANONICAL_SCALAR','LOGIC',rows,min_support=2,max_rules=12)
class Rel:
    def execute(self,x):return 'ALLOW' if x.get('allow') else 'DENY'
relation=Rel()

def make_base():
    return G2TypedRecurrentCapabilityGraphRuntimeV1(arch,router,scalar,relation,portfolio)

stream='CANON-RESTART-FRESH'
stages=[
 {'stage_id':'FAILED_C','cost':1.0,'expected_gain':.5,'quota_remaining':1,'available':True,'latency':1.2},
 {'stage_id':'NEXT_D','cost':2.0,'expected_gain':.6,'quota_remaining':1,'available':True,'latency':.8},
]
cp=Path(tempfile.mkdtemp(prefix='yado-canon-continuity-'))/'checkpoint.json'
f1=G2UnifiedExecutionFabricV4(make_base(),api_state={},checkpoint_path=cp)
initial=f1.execute_capability(CAP_BUD,{
 'kind':'budget','descriptor':desc(CAP_BUD),'stream_id':stream,
 'current_confidence':.2,'target_confidence':.7,'remaining_budget':4.0,'stages':stages,
 'goal_id':'CANON-GOAL','deficit_id':'CANON-CONTINUITY-DEFICIT'
})
outcome=f1.record_outcome(stream,'FAILED_C',0.0)
before=f1.execute_capability(CAP_BUD,{
 'kind':'budget','descriptor':desc(CAP_BUD),'stream_id':stream,
 'current_confidence':.2,'target_confidence':.7,'remaining_budget':4.0,'stages':stages,
 'goal_id':'CANON-GOAL','deficit_id':'CANON-CONTINUITY-DEFICIT'
})
state=G2UnifiedExecutionFabricV4.load_continuity_checkpoint(cp)
pre_tick=int(state['cross_layer']['temporal_tick_id'])
pre_seq=int(state['cross_layer']['recurrent_sequence'])
pre_last=int(state['temporal_state']['streams'][stream]['last_tick'])
pre_attempts=list(state['recurrent_memory_state']['stream_attempts'].get(stream,[]))
pre_eps=len(state['recurrent_memory_state']['episodes'])
del f1

f2=G2UnifiedExecutionFabricV4(make_base(),api_state={},checkpoint_path=cp)
restored_tick=f2.clock.tick_id
restored_seq=f2.base.sequence
restored_eps=len(f2.base.episodes)
restored_attempts=list(f2.base.stream_attempts.get(stream,[]))
after=f2.execute_capability(CAP_BUD,{
 'kind':'budget','descriptor':desc(CAP_BUD),'stream_id':stream,
 'current_confidence':.2,'target_confidence':.7,'remaining_budget':4.0,'stages':stages,
 'goal_id':'CANON-GOAL','deficit_id':'CANON-CONTINUITY-DEFICIT'
})
think=f2.execute_capability(CAP_THINK_V2,{
 'operation':'auto_feedback_plan','stream_id':stream,
 'current_confidence':.2,'target_confidence':.7,'remaining_budget':4.0,
 'stages':stages,'completed':(),
 'goal_id':'CANON-GOAL','deficit_id':'CANON-CONTINUITY-DEFICIT'
})

fresh_checks={
 'fresh_initial_selects_failed_c':initial.get('result')=='FAILED_C',
 'fresh_failure_outcome_recorded':outcome.get('stage_id')=='FAILED_C' and float(outcome.get('observed_gain'))==0.0,
 'fresh_before_restart_selects_next_d':before.get('result')=='NEXT_D',
 'fresh_checkpoint_has_failed_attempt':'FAILED_C' in pre_attempts,
 'fresh_restart_restores_tick':restored_tick==pre_tick,
 'fresh_restart_restores_sequence':restored_seq==pre_seq,
 'fresh_restart_restores_episode_count':restored_eps==pre_eps,
 'fresh_restart_restores_attempts':restored_attempts==pre_attempts and 'FAILED_C' in restored_attempts,
 'fresh_after_restart_same_decision':after.get('result')==before.get('result')=='NEXT_D',
 'fresh_failed_stage_not_retried':after.get('result')!='FAILED_C',
 'fresh_post_restart_tick_monotonic':after.get('temporal',{}).get('tick_id')==pre_tick+1,
 'fresh_post_restart_predecessor':after.get('temporal',{}).get('predecessor_tick')==pre_last,
 'fresh_thinking_memory_feedback':think.get('meta',{}).get('memory_feedback_used') is True,
 'fresh_thinking_avoids_failed_stage':think.get('result',{}).get('action')=='NEXT_D',
}
if not all(fresh_checks.values()):
    raise RuntimeError('CONTINUITY_CANONICAL_FRESH_GATE_FAILED:'+json.dumps(fresh_checks,sort_keys=True))

component=G2UnifiedExecutionFabricV4.component()
canon_art={
 'schema':'yado.g2.cognitive_continuity_checkpoint.canonical.v1',
 'status':'CANONICAL_ACTIVE',
 'component_id':V4,
 'parent_execution_fabric':V3,
 'temporal_kernel':CLOCK,
 'recurrent_memory_runtime':BASE,
 'component':component,
 'runtime_source':'runtime/yado_g2_unified_execution_fabric_v4.py',
 'runtime_sha256':fsha(ROOT/'yado_g2_unified_execution_fabric_v4.py'),
 'shadow_gate_artifact':'candidates/kernel-self-generated/g2-cognitive-continuity-checkpoint-v1.json',
 'shadow_gate_receipt_sha256':fresh.get('receipt_sha256'),
 'shadow_gate_checks':fresh.get('checks'),
 'canonical_fresh_checks':fresh_checks,
 'checkpoint_schema':G2UnifiedExecutionFabricV4.CHECKPOINT_SCHEMA,
 'temporal_and_recurrent_memory_one_checkpoint':True,
 'atomic_local_file_persistence':True,
 'auto_checkpoint_after_top_level_state_change':True,
 'stage_outcome_restore':True,
 'attempt_history_restore':True,
 'decision_continuity_after_restart':True,
 'failed_stage_retry_suppression_after_restore':True,
 'cross_layer_digest_validation':True,
 'fail_closed_on_tamper':True,
 'automatic_canonical_promotion':False,
 'architecture_mutation':False,
 'semantic_boundary':'SAME-G2 CONTINUITY MECHANISM. V4 REPLACES V3 AS THE ACTIVE EXECUTION FABRIC AND PERSISTS TEMPORAL ORDER PLUS ACTIONABLE RECURRENT MEMORY IN ONE ATOMIC LOCAL CHECKPOINT. THIS IS PROCESS-RESTART CONTINUITY, NOT DISTRIBUTED CONSENSUS.'
}
canon_art['canonical_component_digest']=cdig(canon_art,'canonical_component_digest')
write(CANON,canon_art)

# ---------- Bind V4 into UnifiedYADOCoreV1 ----------
src=UNIFIED.read_text(encoding='utf-8')
v3_import='from yado_g2_unified_execution_fabric_v3 import G2UnifiedExecutionFabricV3\n'
v4_import='from yado_g2_unified_execution_fabric_v4 import G2UnifiedExecutionFabricV4\n'
if v4_import not in src:
    if v3_import not in src:raise RuntimeError('UNIFIED_V3_IMPORT_ANCHOR_MISSING')
    src=src.replace(v3_import,v3_import+v4_import)
if '        self.execution_fabric_cls=G2UnifiedExecutionFabricV3\n' not in src:
    raise RuntimeError('UNIFIED_ACTIVE_V3_BINDING_MISSING')
src=src.replace('        self.execution_fabric_cls=G2UnifiedExecutionFabricV3\n','        self.execution_fabric_cls=G2UnifiedExecutionFabricV4\n')

old_inst="""    def instantiate_execution_fabric(self,router_program,scalar_program,relation_program,api_state=None,temporal_state=None):
        base=G2TypedRecurrentCapabilityGraphRuntimeV1(
            self.architecture,router_program,scalar_program,relation_program,self.portfolio
        )
        return self.execution_fabric_cls(base,api_state=api_state,temporal_state=temporal_state)
"""
new_inst="""    def instantiate_execution_fabric(self,router_program,scalar_program,relation_program,api_state=None,temporal_state=None,continuity_state=None,checkpoint_path=None):
        base=G2TypedRecurrentCapabilityGraphRuntimeV1(
            self.architecture,router_program,scalar_program,relation_program,self.portfolio
        )
        return self.execution_fabric_cls(
            base,api_state=api_state,temporal_state=temporal_state,
            continuity_state=continuity_state,checkpoint_path=checkpoint_path
        )
"""
if old_inst not in src:raise RuntimeError('UNIFIED_INSTANTIATE_V3_ANCHOR_MISSING')
src=src.replace(old_inst,new_inst)

anchor="""    def temporal_evolution_on_stall(self,execution_fabric,stream_id:str)->dict[str,Any]:
"""
methods="""    def export_cognitive_continuity_state(self,execution_fabric)->dict[str,Any]:
        if not hasattr(execution_fabric,'export_continuity_state'):
            raise TypeError('CONTINUITY_EXECUTION_FABRIC_REQUIRED')
        return execution_fabric.export_continuity_state()

    def save_cognitive_continuity_checkpoint(self,execution_fabric,path)->dict[str,Any]:
        if not hasattr(execution_fabric,'save_continuity_checkpoint'):
            raise TypeError('CONTINUITY_EXECUTION_FABRIC_REQUIRED')
        return execution_fabric.save_continuity_checkpoint(path)

    def load_cognitive_continuity_checkpoint(self,path)->dict[str,Any]:
        return self.execution_fabric_cls.load_continuity_checkpoint(path)

"""
if 'def export_cognitive_continuity_state(' not in src:
    if anchor not in src:raise RuntimeError('UNIFIED_TEMPORAL_METHOD_ANCHOR_MISSING')
    src=src.replace(anchor,methods+anchor)
UNIFIED.write_text(src,encoding='utf-8')
unified_sha=fsha(UNIFIED)

def plane(pid):
    p=next((x for x in core.get('planes',[]) if x.get('plane_id')==pid),None)
    if p is None:raise RuntimeError('MISSING_PLANE:'+pid)
    return p

identity=plane('IDENTITY_AND_LINEAGE')
memory=plane('MEMORY_AND_EXPERIENCE')
workspace=plane('WORKSPACE_AND_INTEGRATION')
audit=plane('SELF_AUDIT_AND_REPAIR')

workspace['active_components']=[V4 if x==V3 else x for x in workspace.get('active_components',[])]
workspace['active_components']=sorted(set(workspace['active_components']))
identity['responsibilities']=sorted(set(identity.get('responsibilities',[])+['cognitive_continuity_checkpoint_digest_lineage']))
memory['responsibilities']=sorted(set(memory.get('responsibilities',[])+[
 'durable_stage_outcome_checkpoint','durable_attempt_history_checkpoint','restart_actionable_memory_restore'
]))
workspace['responsibilities']=sorted(set(workspace.get('responsibilities',[])+[
 'atomic_temporal_recurrent_checkpoint','restart_decision_continuity','failed_stage_retry_suppression_after_restore'
]))
audit['responsibilities']=sorted(set(audit.get('responsibilities',[])+[
 'continuity_checkpoint_digest_validation','temporal_recurrent_cross_layer_consistency'
]))

core['execution_fabric_v3']=core.get('execution_fabric_v3',{})|{
 'status':'SUPERSEDED_BY_V4','canonical_active':False,'superseded_by':V4
}
core['execution_fabric_v4']={
 'status':'CANONICAL_ACTIVE','component_id':V4,
 'parent_component':V3,
 'canonical_component_digest':canon_art['canonical_component_digest'],
 'runtime_sha256':canon_art['runtime_sha256'],
 'shadow_gate_receipt_sha256':fresh.get('receipt_sha256'),
 'checkpoint_schema':G2UnifiedExecutionFabricV4.CHECKPOINT_SCHEMA,
 'temporal_and_recurrent_memory_one_checkpoint':True,
 'atomic_local_file_persistence':True,
 'auto_checkpoint_after_top_level_state_change':True,
 'decision_continuity_after_restart':True,
 'failed_stage_retry_suppression_after_restore':True,
 'architecture_mutation':False
}
core['cognitive_temporal_kernel_v1']=core.get('cognitive_temporal_kernel_v1',{})|{
 'execution_fabric':V4,
 'state_persistence':'UNIFIED_ATOMIC_TEMPORAL_RECURRENT_CHECKPOINT'
}
core['cognitive_continuity_checkpoint_v1']={
 'status':'CANONICAL_ACTIVE','component_id':V4,
 'parent_execution_fabric':V3,
 'canonical_component_digest':canon_art['canonical_component_digest'],
 'fresh_gate_receipt_sha256':fresh.get('receipt_sha256'),
 'checkpoint_schema':G2UnifiedExecutionFabricV4.CHECKPOINT_SCHEMA,
 'stage_outcome_restore':True,'attempt_history_restore':True,
 'decision_continuity_after_restart':True,
 'fail_closed_on_tamper':True,'automatic_canonical_promotion':False
}
active_sources=set(core.get('active_runtime_sources',[]))
active_sources.add('runtime/yado_g2_unified_execution_fabric_v4.py')
core['active_runtime_sources']=sorted(active_sources)
rim=core.get('runtime_integrity_manifest')
if not isinstance(rim,dict) or not isinstance(rim.get('sources'),dict):
    raise RuntimeError('RUNTIME_INTEGRITY_MANIFEST_MISSING')
rim['sources']={rel:fsha(REPO/rel) for rel in core['active_runtime_sources']}
rim['manifest_digest']=h(rim['sources'])

prev=head['canonical_head_digest']
prov['current_g2_binding'].update({
 'current_execution_label':'G2_COGNITIVE_CONTINUITY_V4_CANONICAL',
 'frontier':FRONT,
 'execution_fabric_component':V4,
 'execution_fabric_parent_component':V3,
 'execution_fabric_v4_source_sha256':canon_art['runtime_sha256'],
 'cognitive_continuity_checkpoint':'canonical/yado-g2-cognitive-continuity-checkpoint-v1.json',
 'cognitive_continuity_fresh_receipt_sha256':fresh.get('receipt_sha256'),
 'cognitive_continuity_checkpoint_schema':G2UnifiedExecutionFabricV4.CHECKPOINT_SCHEMA,
 'temporal_recurrent_unified_persistence':True,
 'restart_actionable_memory_restore':True,
 'failed_stage_retry_suppression_after_restore':True,
})
prov['registry_digest']=cdig(prov,'registry_digest')
write(PROV,prov)

core['algorithm_provenance_registry_digest']=prov['registry_digest']
core['current_frontier']=FRONT
core['runtime_sha256']=unified_sha
core['core_digest']=cdig(core,'core_digest')
write(CORE,core)

head['active_capabilities']=[V4 if x==V3 else x for x in head.get('active_capabilities',[])]
head['active_capabilities']=sorted(set(head['active_capabilities']))
head['new_capabilities']=sorted(set(head.get('new_capabilities',[])+[V4]))
head['execution_fabric_v3']=head.get('execution_fabric_v3',{})|{
 'status':'SUPERSEDED_BY_V4','canonical_active':False,'superseded_by':V4
}
head['execution_fabric_v4']={
 'status':'CANONICAL_ACTIVE','component_id':V4,'parent_component':V3,
 'canonical_component_digest':canon_art['canonical_component_digest'],
 'fresh_gate_receipt_sha256':fresh.get('receipt_sha256'),
 'checkpoint_schema':G2UnifiedExecutionFabricV4.CHECKPOINT_SCHEMA,
 'decision_continuity_after_restart':True,
 'failed_stage_retry_suppression_after_restore':True
}
head['cognitive_temporal_kernel_v1']=head.get('cognitive_temporal_kernel_v1',{})|{
 'execution_fabric':V4,
 'state_persistence':'UNIFIED_ATOMIC_TEMPORAL_RECURRENT_CHECKPOINT'
}
head['cognitive_continuity_checkpoint_v1']={
 'status':'CANONICAL_ACTIVE','component_id':V4,
 'fresh_gate_receipt_sha256':fresh.get('receipt_sha256'),
 'checkpoint_schema':G2UnifiedExecutionFabricV4.CHECKPOINT_SCHEMA,
 'stage_outcome_restore':True,'attempt_history_restore':True,
 'decision_continuity_after_restart':True
}
head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest']
head['algorithm_provenance_registry']['current_execution_label']=prov['current_g2_binding']['current_execution_label']
head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest']
head['unified_core']['core_digest']=core['core_digest']
head['unified_core']['runtime_sha256']=unified_sha
head['unified_core']['runtime_integrity_manifest_digest']=rim['manifest_digest']
head['current_frontier']=FRONT
head['canonical_head_digest']=cdig(head,'canonical_head_digest')
write(HEAD,head)

ledger['current_head_digest']=head['canonical_head_digest']
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
 'schema':'yado.g2.cognitive_continuity.canonical_admission.receipt.v1',
 'status':'PASS_G2_COGNITIVE_CONTINUITY_CANONICAL_ADMISSION_V1',
 'execution_fabric':V4,'parent_execution_fabric':V3,
 'checkpoint_schema':G2UnifiedExecutionFabricV4.CHECKPOINT_SCHEMA,
 'shadow_gate_receipt_sha256':fresh.get('receipt_sha256'),
 'canonical_fresh_checks':fresh_checks,
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest'],
 'frontier_unchanged':FRONT,
 'canonical_mutation':True,'canonical_mechanism_mutation':True,
 'architecture_mutation':False,'generation_transition':False,'g3_genesis_performed':False,
 'automatic_canonical_promotion':False,
 'semantic_boundary':'SAME-G2 CANONICAL REPLACEMENT V3->V4 FOR PROCESS-RESTART CONTINUITY OF LOGICAL TIME PLUS ACTIONABLE RECURRENT MEMORY. NO ARCHITECTURE GENERATION TRANSITION.'
}
receipt['receipt_sha256']=h(receipt)
write(OUT,receipt)
receipt_path=REPO/'receipts'/f'yado-g2-cognitive-continuity-canonical-admission-v1-run-{run_id}.json'
write(receipt_path,receipt)

e={
 'index':len(ledger['events']),
 'event_id':f"E{len(ledger['events'])+1:04d}_G2_COGNITIVE_CONTINUITY_CANONICAL_ADMISSION_V1",
 'event_type':'G2_COGNITIVE_CONTINUITY_CANONICAL_ADMISSION','status':'PASS_CANONICAL',
 'generation':ledger['current_head'],
 'deficit':'COGNITIVE_RESTART_MEMORY_CONTINUITY_GAP',
 'effect':f"REPLACED_ACTIVE={V3}->{V4}; TEMPORAL_RECURRENT_CHECKPOINT=True; STAGE_OUTCOME_RESTORE=True; ATTEMPT_HISTORY_RESTORE=True; DECISION_RESTART_STABLE=True; FAILED_STAGE_RETRY_SUPPRESSED=True; FRONTIER_UNCHANGED={FRONT}",
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
    raise RuntimeError('POST_CONTINUITY_CANONICAL_GUARD_FAILED:'+post.stdout[-6000:]+post.stderr[-2000:])

probe=subprocess.run([
 sys.executable,'-c',
 "import sys;from pathlib import Path;sys.path[:0]=['runtime','runtime/yado_rc8_v36'];from yado_unified_core_v1 import UnifiedYADOCoreV1;c=UnifiedYADOCoreV1(Path('.'));assert c.execution_fabric_cls.COMPONENT_ID=='RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V4';print(c.execution_fabric_cls.COMPONENT_ID)"
],cwd=REPO,capture_output=True,text=True,timeout=90)
if probe.returncode!=0:
    raise RuntimeError('POST_CONTINUITY_CORE_BINDING_FAILED:'+probe.stdout+probe.stderr)

print(json.dumps({
 'status':receipt['status'],
 'execution_fabric':V4,
 'parent_execution_fabric':V3,
 'fresh_checks':fresh_checks,
 'frontier':FRONT,
 'new_head_digest':head['canonical_head_digest'],
 'receipt_sha256':receipt['receipt_sha256'],
},indent=2,sort_keys=True))
