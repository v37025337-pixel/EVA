from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,subprocess,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
V4BURN=REPO/'receipts/yado-g2-raw-representation-v4-canonical-burnin-v1-run-33680772147.json'
ART=REPO/'architecture/yado-kernel-g2-post-raw-v4-architectural-ceiling-reassessment-v3.json'
OUT=ROOT/'yado_kernel_g2_post_raw_v4_architectural_ceiling_reassessment_v3_receipt.json'
GUARD=ROOT/'yado_canonical_invariant_guard_v1.py'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):
    x=copy.deepcopy(o);x.pop(field,None);return h(x)

head,core,ledger,prov,burn=map(load,[HEAD,CORE,LEDGER,PROV,V4BURN])
validate_ledger_v2(ledger)
front='KERNEL_G2_POST_RAW_V4_ARCHITECTURAL_CEILING_REASSESSMENT_V3'
if ledger.get('open_deficits')!=[front]:
    raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if burn.get('status')!='PASS_G2_RAW_REPRESENTATION_V4_CANONICAL_BURNIN_V1':
    raise RuntimeError('RAW_V4_BURNIN_NOT_PASS')
if head.get('g3_genesis_performed') is not False:
    raise RuntimeError('G3_ALREADY_STARTED')
if head.get('raw_task_representation_v4',{}).get('status')!='CANONICAL_ACTIVE':
    raise RuntimeError('RAW_V4_NOT_CANONICAL')

m=burn['min_metrics']
scores={
    'RAW_V4_DIRECT_STABILITY':float(m['direct_accuracy']),
    'RAW_V4_WRAPPED_STABILITY':float(m['wrapped_accuracy']),
    'RAW_V4_SEQUENTIAL_STABILITY':float(m['sequential_accuracy']),
    'RAW_V4_RELOAD_EQUIVALENCE':float(m['reload_equivalence']),
    'RAW_V4_ROLLBACK':float(burn.get('rollback_v3_accuracy',0.0)),
    'THINKING_BOUNDARY':float(head.get('extended_capability_scores',{}).get('thinking_boundary',0.0)),
    'THINKING_CORE':float(head.get('capability_scores',{}).get('thinking',0.0)),
    'LOGIC_CORE':float(head.get('capability_scores',{}).get('logic',0.0)),
    'INTELLIGENCE_CORE':float(head.get('capability_scores',{}).get('intelligence',0.0)),
    'END_TO_END_RUNTIME':float(head.get('extended_capability_scores',{}).get('end_to_end_runtime',0.0)),
}

records=[]
for name,score in scores.items():
    gap=max(0.0,1.0-float(score))
    records.append({
        'variant_id':'DEFICIT_'+name,
        'parent_id':None,
        'lineage_id':'G2_POST_RAW_V4_CEILING',
        'artifact_digest':h({'name':name,'score':score,'head':head['canonical_head_digest']}),
        'task_scores':{'deficit_priority':gap},
        'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
        'traits':{'measured_score':score,'residual_gap':gap},
        'failure_tags':['below_0_985_gate'] if score<0.985 else [],
        'status':'EVALUATED'
    })

kernel=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_post_raw_v4_ceiling_v3.sqlite'))
try:
    selected=kernel.select_evolution_parent(records,'residual_deficit_priority')
    operation=kernel.propose_evolution_operation(
        records,selected['variant_id'],'post_raw_v4_architectural_ceiling_reassessment'
    )
finally:
    kernel.close()

selected_name=selected['variant_id'].removeprefix('DEFICIT_')
selected_score=float(scores[selected_name])
gap=1.0-selected_score
threshold=0.985
ceiling_reconfirmed=all(v>=threshold for v in scores.values())

if ceiling_reconfirmed:
    verdict='LOCAL_CEILING_RECONFIRMED_BUT_NOT_ABSOLUTE'
    next_cap='KERNEL_G2_POST_RAW_V4_OPEN_ENDED_NOVELTY_PROBE_V1'
elif selected_name.startswith('RAW_V4_'):
    verdict='CEILING_NOT_REACHED_RAW_V4_ROBUSTNESS_RESIDUAL'
    next_cap='KERNEL_G2_RAW_REPRESENTATION_V4_ROBUSTNESS_SELF_EVOLUTION_V1'
elif selected_name.startswith('THINKING'):
    verdict='CEILING_NOT_REACHED_THINKING_RESIDUAL'
    next_cap='KERNEL_G2_THINKING_POST_RAW_V4_SELF_EVOLUTION_V1'
else:
    verdict='CEILING_NOT_REACHED_GENERAL_RESIDUAL'
    next_cap='KERNEL_G2_GENERAL_POST_RAW_V4_SELF_EVOLUTION_V1'

artifact={
    'schema':'yado.g2.post_raw_v4_architectural_ceiling_reassessment.v3',
    'status':'PASS_G2_POST_RAW_V4_ARCHITECTURAL_CEILING_REASSESSMENT_V3',
    'verdict':verdict,
    'threshold':threshold,
    'scores':scores,
    'kernel_selected_residual':selected_name,
    'kernel_selected_score':selected_score,
    'kernel_selected_gap':gap,
    'kernel_evolution_operation':operation,
    'burnin_receipt_sha256':burn.get('receipt_sha256'),
    'burnin_rounds':len(burn.get('rounds',[])),
    'canonical_mutation':True,
    'canonical_mechanism_mutation':False,
    'architecture_mutation':False,
    'generation_transition':False,
    'g3_genesis_performed':False,
    'next_required_capability':next_cap,
    'semantic_boundary':'POST-RAW-V4 LOCAL CEILING REASSESSMENT FROM CANONICAL V4 BURN-IN EVIDENCE. NATIVE RC8 SELECTOR CHOOSES THE LARGEST MEASURED RESIDUAL. G3 IS FORBIDDEN UNLESS ALL LOCAL SCORES CLEAR THE FIXED 0.985 GATE. NOT AN ABSOLUTE COMPUTATIONAL CEILING CLAIM.'
}
artifact['artifact_digest']=h(artifact)
write(ART,artifact)

prev=head['canonical_head_digest']
prov['current_g2_binding'].update({
    'current_execution_label':'G2_POST_RAW_V4_RESIDUAL_'+selected_name,
    'frontier':next_cap,
    'frontier_native_method':'select_evolution_parent+propose_evolution_operation',
    'frontier_native_owner':'UnifiedYADOKernelV30RC8ExternalCognitive',
    'post_raw_v4_ceiling_verdict':verdict,
    'kernel_selected_residual':selected_name
})
prov['registry_digest']=cdig(prov,'registry_digest')
write(PROV,prov)

core['algorithm_provenance_registry_digest']=prov['registry_digest']
core['current_frontier']=next_cap
core['frontier_source']='architecture/evolution-ledger.json:open_deficits'
core['post_raw_v4_architectural_ceiling_reassessment_v3']={
    'verdict':verdict,
    'scores':scores,
    'selected_residual':selected_name,
    'selected_gap':gap,
    'kernel_evolution_operation':operation,
    'architecture_mutation':False
}
core['core_digest']=cdig(core,'core_digest')
write(CORE,core)

head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest']
head['algorithm_provenance_registry']['current_execution_label']=prov['current_g2_binding']['current_execution_label']
head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest']
head['unified_core']['core_digest']=core['core_digest']
head['post_raw_v4_architectural_ceiling_reassessment_v3']={
    'verdict':verdict,
    'scores':scores,
    'selected_residual':selected_name,
    'selected_gap':gap,
    'architecture_mutation':False
}
head['current_frontier']=next_cap
head['frontier_source']='architecture/evolution-ledger.json:open_deficits'
head['canonical_head_digest']=cdig(head,'canonical_head_digest')
write(HEAD,head)

ledger['current_head_digest']=head['canonical_head_digest']
ledger['open_deficits']=[next_cap]

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
    **artifact,
    'schema':'yado.g2.post_raw_v4_architectural_ceiling_reassessment.receipt.v3',
    'previous_head_digest':prev,
    'new_head_digest':head['canonical_head_digest'],
    'provenance_registry_digest':prov['registry_digest']
}
receipt['receipt_sha256']=h(receipt)
write(OUT,receipt)

e={
    'index':len(ledger['events']),
    'event_id':f"E{len(ledger['events'])+1:04d}_G2_POST_RAW_V4_ARCHITECTURAL_CEILING_REASSESSMENT_V3",
    'event_type':'G2_POST_RAW_V4_ARCHITECTURAL_CEILING_REASSESSMENT',
    'status':'PASS',
    'generation':ledger['current_head'],
    'deficit':front,
    'effect':f"VERDICT={verdict}; SELECTED={selected_name}; SCORE={selected_score:.6f}; GAP={gap:.6f}; DIRECT={scores['RAW_V4_DIRECT_STABILITY']:.6f}; WRAPPED={scores['RAW_V4_WRAPPED_STABILITY']:.6f}; SEQ={scores['RAW_V4_SEQUENTIAL_STABILITY']:.6f}; OP={operation.get('operation')}; G3=False; NEXT={next_cap}",
    'source_path':f'receipts/yado-g2-post-raw-v4-architectural-ceiling-reassessment-v3-run-{run_id}.json',
    'source_digest':receipt['receipt_sha256'],
    'run_id':run_id,
    'parent_event_hash':ledger['tail_event_hash'],
    'canonical_mutation':True,
    'canonical_mechanism_mutation':False,
    'architecture_mutation':False,
    'promotion_applied':False,
    'generation_transition':False,
    'previous_head_digest':prev,
    'new_head_digest':head['canonical_head_digest']
}
e['event_hash']=event_hash(e)
ledger['events'].append(e)
ledger['event_count']=len(ledger['events'])
ledger['tail_event_hash']=e['event_hash']
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger)
write(LEDGER,ledger)

ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:
    raise RuntimeError('POST_REASSESSMENT_V3_CONTEXT_INCONSISTENT')
post=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=60)
if post.returncode!=0:
    raise RuntimeError('POST_REASSESSMENT_V3_GUARD_FAILED:'+post.stdout[-5000:]+post.stderr[-1000:])

print(json.dumps({
    'status':receipt['status'],
    'verdict':verdict,
    'scores':scores,
    'selected_residual':selected_name,
    'selected_gap':gap,
    'kernel_operation':operation,
    'next_required_capability':next_cap
},indent=2,sort_keys=True))
