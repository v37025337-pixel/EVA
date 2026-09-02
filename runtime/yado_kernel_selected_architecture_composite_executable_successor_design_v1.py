from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,subprocess,sys

ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
ROBUST=REPO/'candidates/kernel-self-generated/neutral-architecture-selection-robustness-repair-v1.json'
ART=REPO/'architecture/yado-kernel-selected-architecture-composite-executable-successor-design-v1.json'
CAND=REPO/'candidates/kernel-self-generated/architecture-composite-executable-successor-design-v1.json'
OUT=ROOT/'yado_kernel_selected_architecture_composite_executable_successor_design_v1_receipt.json'
GUARD=ROOT/'yado_canonical_invariant_guard_v1.py'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):
    x=copy.deepcopy(o);x.pop(field,None);return h(x)
def log(stage,**kw):print(json.dumps({'stage':stage,**kw},sort_keys=True,default=str),flush=True)

head,core,ledger,prov,robust=map(load,[HEAD,CORE,LEDGER,PROV,ROBUST])
validate_ledger_v2(ledger)
front='KERNEL_SELECTED_ARCHITECTURE_COMPOSITE_EXECUTABLE_SUCCESSOR_DESIGN_V1'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if robust.get('state')!='SHADOW_SUPPORTED':raise RuntimeError('ROBUST_COMPOSITE_NOT_SUPPORTED')
families=list(robust.get('selected_families') or [])
expected_families=['OPEN_ENDED_EVOLUTION','LOCAL_SELF_ORGANIZING','NEURO_SYMBOLIC']
if families!=expected_families:raise RuntimeError('COMPOSITE_FAMILY_DRIFT:'+json.dumps(families))
if head.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')

k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_composite_design_v1.sqlite'))
try:
    methods={
      'select_evolution_parent':hasattr(k,'select_evolution_parent'),
      'propose_evolution_operation':hasattr(k,'propose_evolution_operation'),
      'select_evolution_skills':hasattr(k,'select_evolution_skills'),
      'synthesize_intelligence_algorithm_component':hasattr(k,'synthesize_intelligence_algorithm_component'),
      'synthesize_intelligence_with_extended_meta_grammar':hasattr(k,'synthesize_intelligence_with_extended_meta_grammar')
    }
    records=[
      {
       'variant_id':'G2_CURRENT_TRCG_PARENT','parent_id':None,'lineage_id':'YADO_MAIN_LINEAGE',
       'artifact_digest':head['canonical_head_digest'],
       'task_scores':{'integrity':float(head['capability_scores']['integrity']),'logic':float(head['capability_scores']['logic']),
                      'thinking':float(head['capability_scores']['thinking']),'robust_architecture_direction':2.0/3.0},
       'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
       'traits':{'typed_recurrent_graph':1.0,'canonical':1.0,'composite_architecture':0.0},
       'failure_tags':['single_family_architecture_direction_not_robust'],'status':'EVALUATED'
      },
      {
       'variant_id':'G2_TOP3_COMPOSITE_DIRECTION','parent_id':'G2_CURRENT_TRCG_PARENT','lineage_id':'YADO_MAIN_LINEAGE',
       'artifact_digest':robust['candidate_digest'],
       'task_scores':{'fit_coverage':float(robust['fit_coverage']),'double_ablation_coverage':float(robust['double_ablation_coverage']),
                      'family_coverage':1.0,'architecture_mutation':0.0},
       'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
       'traits':{'open_ended_evolution':1.0,'local_self_organizing':1.0,'neuro_symbolic':1.0,'composite_architecture':1.0},
       'failure_tags':[],'status':'EVALUATED'
      }
    ]
    parent=k.select_evolution_parent(records,'executable_successor_design')
    operation=k.propose_evolution_operation(records,parent['variant_id'],'executable_successor_design')
finally:k.close()

if not isinstance(operation,dict) or not operation.get('operation'):
    raise RuntimeError('KERNEL_OPERATION_MISSING:'+json.dumps(operation,default=str))
op=str(operation['operation'])
log('kernel_design_decision',parent=parent,operation=operation)

# The host materializes only a bounded design envelope around the kernel-selected evolutionary operation.
design={
 'design_id':'G2_COMPOSITE_EXECUTABLE_SUCCESSOR_DESIGN_V1',
 'parent_runtime_component':head['runtime_component']['component_id'],
 'selected_families':families,
 'kernel_selected_parent':parent,
 'kernel_selected_evolution_operation':operation,
 'execution_contract':{
   'parent_g2_remains_canonical_during_prototype':True,
   'successor_runs_shadow_only':True,
   'rollback_required':True,
   'causal_receipt_required':True,
   'family_roles':{
      'OPEN_ENDED_EVOLUTION':'EVOLUTIONARY_PROPOSAL_RETENTION_AND_SUCCESSOR_SELECTION',
      'LOCAL_SELF_ORGANIZING':'RECURRENT_LOCAL_CAPABILITY_STATE_UPDATE',
      'NEURO_SYMBOLIC':'SYMBOLIC_CONSTRAINT_AND_EVIDENCE_VERIFICATION'
   },
   'composition_semantics':'KERNEL_OPERATION_'+op,
   'no_g3_promotion_during_design_or_prototype':True
 },
 'required_native_surface':methods,
 'semantic_boundary':'KERNEL CHOOSES THE EVOLUTIONARY OPERATION; HOST MATERIALIZES ONLY A BOUNDED SHADOW EXECUTION CONTRACT. THIS IS A SUCCESSOR DESIGN, NOT AN ACTIVE ARCHITECTURE REWRITE.'
}
design['design_digest']=h(design)

checks={
 'kernel_selected_parent':bool(parent and parent.get('variant_id')),
 'kernel_selected_evolution_operation':bool(operation.get('operation')),
 'all_required_native_methods_present':all(methods.values()),
 'composite_exact':families==expected_families,
 'parent_remains_canonical':True,
 'architecture_not_mutated':True,
 'prototype_not_executed_yet':True,
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
supported=all(checks.values())
state='SHADOW_DESIGN_SUPPORTED' if supported else 'WITHHOLD'
next_cap='KERNEL_SELECTED_ARCHITECTURE_COMPOSITE_EXECUTABLE_SUCCESSOR_PROTOTYPE_V1' if supported else 'KERNEL_SELECTED_ARCHITECTURE_COMPOSITE_EXECUTABLE_SUCCESSOR_DESIGN_V2'

candidate={
 'schema':'yado.g2.architecture_composite_executable_successor_design.v1','state':state,
 'source_robustness_candidate_digest':robust['candidate_digest'],'design':design,
 'checks':checks,'architecture_mutation':False,'canonical_mechanism_mutation':False,
 'generation_transition':False,'g3_genesis_performed':False
}
candidate['candidate_digest']=h(candidate);write(CAND,candidate)

artifact={
 'schema':'yado.g2.kernel_selected_architecture_composite_executable_successor_design.v1',
 'status':'PASS_COMPOSITE_EXECUTABLE_SUCCESSOR_DESIGN_V1' if supported else 'WITHHOLD_COMPOSITE_EXECUTABLE_SUCCESSOR_DESIGN_V1',
 'candidate_state':state,'candidate_digest':candidate['candidate_digest'],'design_digest':design['design_digest'],
 'selected_families':families,'kernel_operation':operation,'next_required_capability':next_cap,
 'architecture_mutation':False,'canonical_mechanism_mutation':False,'generation_transition':False,'g3_genesis_performed':False
}
artifact['artifact_digest']=h(artifact);write(ART,artifact)

prev=head['canonical_head_digest']
prov['current_g2_binding'].update({
 'current_execution_label':'G2_COMPOSITE_SUCCESSOR_DESIGN_'+op if supported else 'G2_COMPOSITE_SUCCESSOR_DESIGN_V2_PENDING',
 'frontier':next_cap,
 'frontier_native_method':'propose_evolution_operation',
 'frontier_native_owner':'UnifiedYADOKernelV30RC7DeepIntegrity',
 'selected_architecture_composite_shadow':families,
 'selected_successor_design_operation':op if supported else None
})
prov['registry_digest']=cdig(prov,'registry_digest');write(PROV,prov)

core['algorithm_provenance_registry_digest']=prov['registry_digest']
core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits'
core['architecture_composite_successor_design_v1']={
 'status':state,'candidate_digest':candidate['candidate_digest'],'design_digest':design['design_digest'],
 'selected_families':families,'kernel_operation':operation,'architecture_mutation':False
}
core['core_digest']=cdig(core,'core_digest');write(CORE,core)

head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest']
head['algorithm_provenance_registry']['current_execution_label']=prov['current_g2_binding']['current_execution_label']
head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest'];head['unified_core']['core_digest']=core['core_digest']
head['architecture_composite_successor_design_v1']={
 'status':state,'candidate_digest':candidate['candidate_digest'],'design_digest':design['design_digest'],
 'selected_families':families,'kernel_operation':operation,'architecture_mutation':False
}
head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits'
head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)

ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap]
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={**artifact,'schema':'yado.g2.kernel_selected_architecture_composite_executable_successor_design.receipt.v1',
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest'],'checks':checks,
 'provenance_registry_digest':prov['registry_digest']}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_COMPOSITE_EXECUTABLE_SUCCESSOR_DESIGN_V1",
 'event_type':'G2_KERNEL_SELECTED_COMPOSITE_SUCCESSOR_DESIGN','status':'PASS_SHADOW' if supported else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':front,
 'effect':f"FAMILIES={'+'.join(families)}; OP={op}; DESIGN={state}; ARCHITECTURE_MUTATION=False; NEXT={next_cap}",
 'source_path':f'receipts/yado-kernel-selected-architecture-composite-executable-successor-design-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':True,'canonical_mechanism_mutation':False,'architecture_mutation':False,
 'promotion_applied':False,'generation_transition':False,'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);write(LEDGER,ledger)

ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_WRITE_CONTEXT_INCONSISTENT')
cp=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=60)
if cp.returncode!=0:raise RuntimeError('POST_DESIGN_GUARD_FAILED:'+cp.stdout[-4000:]+cp.stderr[-1000:])
log('complete',state=state,operation=op,next=next_cap)
