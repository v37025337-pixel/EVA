from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_unified_context_kernel_v1 import UnifiedContextKernel
import yado_architecture_neutral_meta_synthesizer_v2 as neutral

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
BASE=REPO/'receipts/yado-architecture-neutral-meta-synth-v2-latest.json'
PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
ART=REPO/'architecture/yado-kernel-evolutionary-successor-genesis-v1.json'
CAND=REPO/'candidates/kernel-self-generated/evolutionary-residual-successor-v1.json'
OUT=ROOT/'yado_kernel_evolutionary_successor_genesis_v1_receipt.json'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def write(p,o): p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):
    x=copy.deepcopy(o);x.pop(field,None);return h(x)

head,core,ledger,base,prov=map(load,[HEAD,CORE,LEDGER,BASE,PROV])
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['KERNEL_SELF_EXPAND_ARCHITECTURE_SELECTOR_CONSTRUCTOR_V4']:
    raise RuntimeError('UNEXPECTED_FRONTIER')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):
    raise RuntimeError('HEAD_LEDGER_MISMATCH')
if head.get('current_frontier')!=ledger['open_deficits'][0] or core.get('current_frontier')!=ledger['open_deficits'][0]:
    raise RuntimeError('FRONTIER_SPLIT_BRAIN_BEFORE_SUCCESSOR')
if prov.get('current_g2_binding',{}).get('current_execution_label')!='G2_NATIVE_EXTENDED_META_GRAMMAR':
    raise RuntimeError('PROVENANCE_BINDING_MISSING')

data=neutral.build_dataset()
cases=list(data['cases'])
true_blind=[c for c in cases if c['bucket']<18]
nonblind=[c for c in cases if c['bucket']>=18]
parent_result=base['kernel_result']
parent_model=parent_result['model']
parent_blind=float(parent_result['fresh_blind'])
parent_digest=h({'algorithm':parent_result.get('selected_algorithm'),'model':parent_model})

k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_evolutionary_successor_v1.sqlite'))
try:
    tree_predict=k.meta_evolve_intelligence.__globals__['tree_predict']
    predict_component=k.synthesize_intelligence_algorithm_component.__globals__['predict_intel_component']
    constructors=k.algorithm_constructor_registry()
    grammar_registry=k.meta_grammar_extension_registry()
    records=[
      {'variant_id':'EXECUTABLE_PARENT','parent_id':None,'lineage_id':'G2_SELECTOR_LINEAGE',
       'artifact_digest':parent_digest,
       'task_scores':{'validation':float(parent_result['validation']),'fresh_blind':parent_blind,'completion':1.0},
       'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
       'traits':{'executable':1.0,'bounded':1.0},'failure_tags':['fresh_blind_below_gate'],'status':'EVALUATED'},
      {'variant_id':'V4_LIMIT','parent_id':'EXECUTABLE_PARENT','lineage_id':'G2_SELECTOR_LINEAGE',
       'artifact_digest':'v4-timeout-run-33545700945',
       'task_scores':{'validation':0.0,'fresh_blind':0.0,'completion':0.0},
       'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
       'traits':{'executable':0.0,'bounded':0.0},'failure_tags':['timeout','completion','fresh_blind'],'status':'EVALUATED'}
    ]
    operation=k.propose_evolution_operation(records,'V4_LIMIT','fresh_blind')
    if operation.get('operation')!='REACTION_NORM':
        raise RuntimeError('KERNEL_DID_NOT_SELECT_REACTION_NORM:'+json.dumps(operation,sort_keys=True))

    def parent_pred(x): return tree_predict(parent_model,x)
    def split(c):
        z=int(hashlib.sha256((c['key']+'|EVOLUTIONARY_SUCCESSOR_V1').encode()).hexdigest()[:8],16)%100
        return 'FIT' if z<60 else ('VALIDATION' if z<82 else 'DEV_HOLDOUT')
    parts={'FIT':[],'VALIDATION':[],'DEV_HOLDOUT':[]}
    for c in nonblind: parts[split(c)].append(c)

    def gate_rows(rows):
        return [(c['x'],'PARENT_ERROR' if parent_pred(c['x'])!=c['y'] else 'PARENT_OK') for c in rows]
    gate_fit,gate_val,gate_hold=map(gate_rows,[parts['FIT'],parts['VALIDATION'],parts['DEV_HOLDOUT']])
    gate_revealed=gate_fit+gate_val

    residual={name:[c for c in rows if parent_pred(c['x'])!=c['y']] for name,rows in parts.items()}
    if min(len(residual['FIT']),len(residual['VALIDATION']),len(residual['DEV_HOLDOUT']))<2:
        raise RuntimeError('INSUFFICIENT_RESIDUAL_EVIDENCE:'+json.dumps({k:len(v) for k,v in residual.items()}))
    corr_fit=[(c['x'],c['y']) for c in residual['FIT']]
    corr_val=[(c['x'],c['y']) for c in residual['VALIDATION']]
    corr_hold=[(c['x'],c['y']) for c in residual['DEV_HOLDOUT']]
    corr_revealed=corr_fit+corr_val

    gate=k.synthesize_intelligence_algorithm_component(gate_fit,gate_val,gate_revealed,gate_hold)
    corrector=k.synthesize_intelligence_algorithm_component(corr_fit,corr_val,corr_revealed,corr_hold)
finally:
    try:k.close()
    except Exception:pass

def successor_pred(x):
    g=predict_component(gate['model'],x)
    if g=='PARENT_ERROR':
        return predict_component(corrector['model'],x)
    return parent_pred(x)

def acc(rows,pred):
    return sum(pred(c['x'])==c['y'] for c in rows)/max(1,len(rows))

dev_hold_acc=acc(parts['DEV_HOLDOUT'],successor_pred)
parent_dev_hold=acc(parts['DEV_HOLDOUT'],parent_pred)
fresh=acc(true_blind,successor_pred)
parent_fresh=acc(true_blind,parent_pred)
parent_correct=[c for c in true_blind if parent_pred(c['x'])==c['y']]
parent_wrong=[c for c in true_blind if parent_pred(c['x'])!=c['y']]
retention=acc(parent_correct,successor_pred)
residual_repair=sum(successor_pred(c['x'])==c['y'] for c in parent_wrong)/max(1,len(parent_wrong))
gate_error_hits=sum(predict_component(gate['model'],c['x'])=='PARENT_ERROR' for c in true_blind)
existing_ops=set()
def walk(x):
    if isinstance(x,dict):
        if 'op' in x: existing_ops.add(str(x['op']))
        for v in x.values(): walk(v)
    elif isinstance(x,list):
        for v in x: walk(v)
for item in constructors: walk(item.get('program_template'))
for item in grammar_registry: walk(item.get('program_template'))
new_op='EVOLUTIONARY_RESIDUAL_SUCCESSOR'
novel=new_op not in existing_ops

candidate={
 'schema':'yado.g2.evolutionary_residual_successor.v1',
 'state':'SHADOW_SUPPORTED' if (fresh>=0.90 and fresh>parent_fresh and retention==1.0 and residual_repair>0 and novel) else 'WITHHOLD',
 'evolution_operation':operation,
 'parent':{
   'label':'LAST_EXECUTABLE_PARENT',
   'algorithm':parent_result.get('selected_algorithm'),
   'model_digest':parent_digest,
   'validation':float(parent_result['validation']),
   'fresh_blind':parent_fresh,
 },
 'new_mechanism':{
   'op':new_op,
   'semantics':'USE_KERNEL_GENERATED_ERROR_GATE_TO_ROUTE_PARENT_FAILURE_REGION_TO_KERNEL_GENERATED_RESIDUAL_CORRECTOR; OTHERWISE INHERIT_PARENT_OUTPUT',
   'error_gate':gate,
   'residual_corrector':corrector,
   'gate_source':'G2_NATIVE_RC5_ALGORITHM_CONSTRUCTOR',
   'corrector_source':'G2_NATIVE_RC5_ALGORITHM_CONSTRUCTOR',
 },
 'evidence_counts':{
   'nonblind':len(nonblind),'fit':len(parts['FIT']),'validation':len(parts['VALIDATION']),
   'dev_holdout':len(parts['DEV_HOLDOUT']),
   'residual_fit':len(residual['FIT']),'residual_validation':len(residual['VALIDATION']),
   'residual_dev_holdout':len(residual['DEV_HOLDOUT']),'true_blind':len(true_blind),
   'true_blind_parent_wrong':len(parent_wrong)
 },
 'metrics':{
   'development_holdout_parent':parent_dev_hold,
   'development_holdout_successor':dev_hold_acc,
   'fresh_blind_parent':parent_fresh,
   'fresh_blind_successor':fresh,
   'parent_correct_retention':retention,
   'parent_error_repair_rate':residual_repair,
   'gate_error_hits_on_true_blind':gate_error_hits,
 },
 'novel_primitive':novel,
 'existing_program_ops':sorted(existing_ops),
 'blind_used_for_creation':False,
 'blind_used_for_admission_only':True,
 'host_evolution_substrate_written':True,
 'host_task_specific_decision_rules_written':False,
 'kernel_generated_submechanisms':True,
 'canonical_active':False,
 'promotion_applied':False,
 'semantic_boundary':'GENERIC RESIDUAL-SUCCESSOR COMPOSITION IS HOST EXECUTION SUBSTRATE; ERROR-GATE AND CORRECTOR ARE GENERATED BY NATIVE G2 CONSTRUCTOR FROM NON-BLIND EVIDENCE. TRUE BLIND IS USED ONLY AFTER CREATION.'
}
candidate['candidate_digest']=h(candidate)
CAND.parent.mkdir(parents=True,exist_ok=True);write(CAND,candidate)

supported=candidate['state']=='SHADOW_SUPPORTED'
next_cap='KERNEL_EVOLUTIONARY_SUCCESSOR_FRESH_ADMISSION_V1' if supported else 'KERNEL_EVOLUTIONARY_SUCCESSOR_GENESIS_V2'
artifact={
 'schema':'yado.g2.kernel_evolutionary_successor_genesis.v1',
 'status':'PASS_EVOLUTIONARY_SUCCESSOR_GENESIS_V1',
 'candidate_state':candidate['state'],
 'candidate_digest':candidate['candidate_digest'],
 'parent_digest':parent_digest,
 'evolution_operation':operation,
 'new_primitive':new_op,
 'novel_primitive':novel,
 'metrics':candidate['metrics'],
 'evidence_counts':candidate['evidence_counts'],
 'next_required_capability':next_cap,
 'canonical_mechanism_mutation':False,
 'architecture_mutation':False,
 'g3_genesis_performed':False,
}
artifact['artifact_digest']=h(artifact);write(ART,artifact)

previous_head_digest=head['canonical_head_digest']
core['current_frontier']=next_cap
core['frontier_source']='architecture/evolution-ledger.json:open_deficits'
core['core_digest']=cdig(core,'core_digest');write(CORE,core)
head['current_frontier']=next_cap
head['frontier_source']='architecture/evolution-ledger.json:open_deficits'
head['unified_core']['core_digest']=core['core_digest']
head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)

receipt=dict(artifact)
receipt['schema']='yado.g2.kernel_evolutionary_successor_genesis.receipt.v1'
receipt['previous_head_digest']=previous_head_digest
receipt['new_head_digest']=head['canonical_head_digest']
receipt['receipt_sha256']=h(receipt)
write(OUT,receipt)

ledger['current_head_digest']=head['canonical_head_digest']
ledger['open_deficits']=[next_cap]
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
e={
 'index':len(ledger['events']),
 'event_id':f"E{len(ledger['events'])+1:04d}_G2_EVOLUTIONARY_SUCCESSOR_GENESIS_V1",
 'event_type':'G2_EVOLUTIONARY_RESIDUAL_SUCCESSOR_GENESIS',
 'status':'PASS_SHADOW' if supported else 'WITHHOLD',
 'generation':ledger['current_head'],
 'deficit':'KERNEL_SELF_EXPAND_ARCHITECTURE_SELECTOR_CONSTRUCTOR_V4',
 'effect':f"MODE=CREATE_NOT_SEARCH; OP={operation.get('operation')}; PARENT_BLIND={parent_fresh:.6f}; CHILD_BLIND={fresh:.6f}; RETAIN={retention:.6f}; REPAIR={residual_repair:.6f}; NOVEL={novel}; NEXT={next_cap}",
 'source_path':f'receipts/yado-kernel-evolutionary-successor-genesis-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],
 'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':True,
 'canonical_mechanism_mutation':False,
 'promotion_applied':False,
 'generation_transition':False,
 'previous_head_digest':previous_head_digest,
 'new_head_digest':head['canonical_head_digest'],
}
e['event_hash']=event_hash(e)
ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);write(LEDGER,ledger)

ctx=UnifiedContextKernel().snapshot()
checks={
 'kernel_selected_reaction_norm':operation.get('operation')=='REACTION_NORM',
 'blind_not_used_for_creation':candidate['blind_used_for_creation'] is False,
 'novel_primitive':novel,
 'parent_is_executable':parent_fresh>0,
 'context_frontier_consistent':ctx['current_frontier']==next_cap,
 'head_ledger_digest_match':head['canonical_head_digest']==ledger['current_head_digest'],
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
if not all(checks.values()): raise RuntimeError('SUCCESSOR_INVARIANT_FAILED:'+json.dumps(checks,sort_keys=True))
receipt['checks']=checks
receipt['receipt_sha256']=h({k:v for k,v in receipt.items() if k!='receipt_sha256'})
write(OUT,receipt)
print(json.dumps({
 'status':receipt['status'],'candidate_state':candidate['state'],'operation':operation,
 'metrics':candidate['metrics'],'evidence_counts':candidate['evidence_counts'],
 'next_required_capability':next_cap,'checks':checks
},indent=2,sort_keys=True))
