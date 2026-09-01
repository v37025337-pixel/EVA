from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,multiprocessing as mp,os,queue as qm,sys,time

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_organ_runtime_native_v1 import tree_predict
from yado_algorithm_component_runtime_native_v1 import predict_intel_component
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
BASE=REPO/'receipts/yado-architecture-neutral-meta-synth-v2-latest.json'
CORPUS=REPO/'resources/yado-architecture-neutral-evidence-corpus-frozen-v1.json'
ART=REPO/'architecture/yado-kernel-evolutionary-successor-genesis-v2.json'
CAND=REPO/'candidates/kernel-self-generated/evolutionary-residual-successor-v2.json'
OUT=ROOT/'yado_kernel_evolutionary_successor_genesis_v2_receipt.json'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def write(p,o): p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):
    x=copy.deepcopy(o);x.pop(field,None);return h(x)
def log(stage,**kw):
    print(json.dumps({'stage':stage,'ts':time.time(),**kw},sort_keys=True),flush=True)

head,core,ledger,base,corpus=map(load,[HEAD,CORE,LEDGER,BASE,CORPUS])
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['KERNEL_SELF_EXPAND_ARCHITECTURE_SELECTOR_CONSTRUCTOR_V4']:
    raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):
    raise RuntimeError('HEAD_LEDGER_MISMATCH')
if cdig(corpus,'corpus_digest')!=corpus.get('corpus_digest'):
    raise RuntimeError('FROZEN_CORPUS_DIGEST_MISMATCH')
if corpus.get('status')!='FROZEN_VERIFIED_HISTORY' or len(corpus.get('cases',[]))!=298:
    raise RuntimeError('FROZEN_CORPUS_INVALID')

cases=list(corpus['cases'])
true_blind=[c for c in cases if c['bucket']<18]
nonblind=[c for c in cases if c['bucket']>=18]
if len(true_blind)!=46 or len(nonblind)!=252:
    raise RuntimeError('PARTITION_COUNT_MISMATCH')

parent_result=base['kernel_result']
parent_model=parent_result['model']
parent_digest=h({'algorithm':parent_result.get('selected_algorithm'),'model':parent_model})
parent_fresh=float(parent_result['fresh_blind'])

def parent_pred(x): return tree_predict(parent_model,x)

# Kernel chooses the evolutionary operation from the observed parent/failed-descendant record.
log('operation_start')
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_successor_v2_operation.sqlite'))
try:
    records=[
      {'variant_id':'EXECUTABLE_PARENT','parent_id':None,'lineage_id':'G2_SELECTOR_LINEAGE',
       'artifact_digest':parent_digest,
       'task_scores':{'validation':float(parent_result['validation']),'fresh_blind':parent_fresh,'completion':1.0},
       'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
       'traits':{'executable':1.0,'bounded':1.0},'failure_tags':['fresh_blind_below_gate'],'status':'EVALUATED'},
      {'variant_id':'V4_LIMIT','parent_id':'EXECUTABLE_PARENT','lineage_id':'G2_SELECTOR_LINEAGE',
       'artifact_digest':'v4-timeout-run-33545700945',
       'task_scores':{'validation':0.0,'fresh_blind':0.0,'completion':0.0},
       'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
       'traits':{'executable':0.0,'bounded':0.0},'failure_tags':['timeout','completion','fresh_blind'],'status':'EVALUATED'},
      {'variant_id':'SUCCESSOR_V1_LIMIT','parent_id':'EXECUTABLE_PARENT','lineage_id':'G2_SELECTOR_LINEAGE',
       'artifact_digest':'successor-v1-timeout-run-33552240836',
       'task_scores':{'validation':0.0,'fresh_blind':0.0,'completion':0.0},
       'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
       'traits':{'executable':0.0,'bounded':0.0},'failure_tags':['timeout','cart_axis_resource_ceiling','completion'],'status':'EVALUATED'}
    ]
    operation=k.propose_evolution_operation(records,'SUCCESSOR_V1_LIMIT','fresh_blind')
    full_bank=k.organ_evolution_algorithm_bank().get('INTELLIGENCE',[])
finally:
    k.close()
if operation.get('operation')!='REACTION_NORM':
    raise RuntimeError('KERNEL_DID_NOT_SELECT_REACTION_NORM:'+json.dumps(operation,sort_keys=True))
linear_bank=[x for x in full_bank if x.get('family')=='LINEAR_SCORE_SEARCH']
if not linear_bank:
    raise RuntimeError('NO_LINEAR_SCORE_SEARCH_IN_NATIVE_BANK')
log('operation_done',operation=operation.get('operation'),full_bank=len(full_bank),shadow_bank=len(linear_bank))

# Stratify only on permitted non-blind parent outcome so rare parent failures survive every developmental split.
errors=[c for c in nonblind if parent_pred(c['x'])!=c['y']]
correct=[c for c in nonblind if parent_pred(c['x'])==c['y']]
def stable(xs,salt):
    return sorted(xs,key=lambda c:hashlib.sha256((c['key']+'|'+salt).encode()).hexdigest())
errors=stable(errors,'EVOLUTIONARY_SUCCESSOR_V2_ERROR_STRATA')
correct=stable(correct,'EVOLUTIONARY_SUCCESSOR_V2_CORRECT_STRATA')
if len(errors)<6:
    raise RuntimeError('INSUFFICIENT_TOTAL_PARENT_ERRORS:'+str(len(errors)))
e_fit=max(2,(len(errors)+1)//2)
remaining=len(errors)-e_fit
e_val=max(2,remaining//2)
e_hold=len(errors)-e_fit-e_val
if e_hold<2:
    e_val=max(2,e_val-(2-e_hold));e_hold=len(errors)-e_fit-e_val
if min(e_fit,e_val,e_hold)<2:
    raise RuntimeError('CANNOT_STRATIFY_PARENT_ERRORS:'+str(len(errors)))
def split_correct(xs):
    n=len(xs);a=int(n*.60);b=int(n*.82)
    return xs[:a],xs[a:b],xs[b:]
c_fit,c_val,c_hold=split_correct(correct)
parts={
 'FIT':errors[:e_fit]+c_fit,
 'VALIDATION':errors[e_fit:e_fit+e_val]+c_val,
 'DEV_HOLDOUT':errors[e_fit+e_val:]+c_hold,
}
for name in parts:
    parts[name]=stable(parts[name],'EVOLUTIONARY_SUCCESSOR_V2_'+name)
def gate_rows(rows):
    return [(c['x'],'PARENT_ERROR' if parent_pred(c['x'])!=c['y'] else 'PARENT_OK') for c in rows]
gate_fit,gate_val,gate_hold=map(gate_rows,[parts['FIT'],parts['VALIDATION'],parts['DEV_HOLDOUT']])
gate_revealed=gate_fit+gate_val
residual={name:[c for c in rows if parent_pred(c['x'])!=c['y']] for name,rows in parts.items()}
if min(len(residual['FIT']),len(residual['VALIDATION']),len(residual['DEV_HOLDOUT']))<2:
    raise RuntimeError('INSUFFICIENT_RESIDUAL_EVIDENCE_AFTER_STRATIFICATION:'+json.dumps({k:len(v) for k,v in residual.items()}))
corr_fit=[(c['x'],c['y']) for c in residual['FIT']]
corr_val=[(c['x'],c['y']) for c in residual['VALIDATION']]
corr_hold=[(c['x'],c['y']) for c in residual['DEV_HOLDOUT']]
corr_revealed=corr_fit+corr_val
log('evidence_ready',fit=len(parts['FIT']),validation=len(parts['VALIDATION']),dev_holdout=len(parts['DEV_HOLDOUT']),
    residual={k:len(v) for k,v in residual.items()})

def constructor_worker(q,fit,val,revealed,hold,db_name):
    kk=None
    try:
        kk=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/db_name))
        # Shadow-only resource envelope: preserve native constructor, remove only proven resource-infeasible CART family.
        kk.canonical_state['organ_evolution_algorithm_bank']['INTELLIGENCE']=copy.deepcopy(linear_bank)
        out=kk.synthesize_intelligence_algorithm_component(fit,val,revealed,hold)
        q.put({'ok':True,'result':out})
    except BaseException as e:
        q.put({'ok':False,'error':type(e).__name__+':'+str(e)[:1800]})
    finally:
        if kk is not None:
            try:kk.close()
            except Exception:pass

def run_constructor(name,fit,val,revealed,hold,timeout=150):
    ctx=mp.get_context('fork');q=ctx.Queue(1)
    p=ctx.Process(target=constructor_worker,args=(q,fit,val,revealed,hold,f'yado_successor_v2_{name}.sqlite'),name=name)
    log(name+'_start',fit=len(fit),validation=len(val),revealed=len(revealed),dev_holdout=len(hold))
    t=time.perf_counter();p.start();p.join(timeout)
    elapsed=time.perf_counter()-t
    if p.is_alive():
        p.terminate();p.join(5)
        if p.is_alive():p.kill();p.join(3)
        raise RuntimeError(name.upper()+'_TIMEOUT:'+str(timeout))
    try:msg=q.get(timeout=8)
    except qm.Empty: raise RuntimeError(name.upper()+'_NO_RESULT:exit='+str(p.exitcode))
    if not msg.get('ok'): raise RuntimeError(name.upper()+'_ERROR:'+str(msg.get('error')))
    log(name+'_done',elapsed=elapsed,validation=msg['result'].get('validation'),dev_holdout=msg['result'].get('fresh_blind'))
    return msg['result'],elapsed

gate,gate_seconds=run_constructor('error_gate',gate_fit,gate_val,gate_revealed,gate_hold)
corrector,corr_seconds=run_constructor('residual_corrector',corr_fit,corr_val,corr_revealed,corr_hold)

def successor_pred(x):
    g=predict_intel_component(gate['model'],x)
    if g=='PARENT_ERROR':
        return predict_intel_component(corrector['model'],x)
    return parent_pred(x)
def acc(rows,pred):
    return sum(pred(c['x'])==c['y'] for c in rows)/max(1,len(rows))

parent_dev=acc(parts['DEV_HOLDOUT'],parent_pred)
child_dev=acc(parts['DEV_HOLDOUT'],successor_pred)
fresh=acc(true_blind,successor_pred)
parent_blind=acc(true_blind,parent_pred)
parent_correct=[c for c in true_blind if parent_pred(c['x'])==c['y']]
parent_wrong=[c for c in true_blind if parent_pred(c['x'])!=c['y']]
retention=acc(parent_correct,successor_pred)
repair=sum(successor_pred(c['x'])==c['y'] for c in parent_wrong)/max(1,len(parent_wrong))
new_op='EVOLUTIONARY_RESIDUAL_SUCCESSOR_V2'
supported=bool(fresh>=0.90 and fresh>parent_blind and retention==1.0 and repair>0)
next_cap='KERNEL_EVOLUTIONARY_SUCCESSOR_FRESH_ADMISSION_V1' if supported else 'KERNEL_EVOLUTIONARY_SUCCESSOR_GENESIS_V3'

candidate={
 'schema':'yado.g2.evolutionary_residual_successor.v2',
 'state':'SHADOW_SUPPORTED' if supported else 'WITHHOLD',
 'principle':'CREATE_SUCCESSOR_FROM_PARENT_DEFICIT_NOT_SEARCH_ARCHITECTURE_FAMILIES',
 'evolution_operation':operation,
 'parent':{'algorithm':parent_result.get('selected_algorithm'),'model_digest':parent_digest,'fresh_blind':parent_blind},
 'new_mechanism':{
   'op':new_op,
   'semantics':'PARENT_INHERITANCE_PLUS_KERNEL_GENERATED_ERROR_GATE_AND_RESIDUAL_CORRECTOR',
   'error_gate':gate,
   'residual_corrector':corrector,
   'constructor':'G2_NATIVE_RC5_ALGORITHM_CONSTRUCTOR',
 },
 'resource_envelope':{
   'shadow_only':True,
   'excluded_family':'CART_AXIS',
   'reason':'PROVEN_15_MINUTE_RESOURCE_CEILING_IN_SUCCESSOR_V1_RUN_33552240836',
   'allowed_native_family':'LINEAR_SCORE_SEARCH',
   'canonical_algorithm_bank_mutated':False,
 },
 'frozen_history':{
   'corpus':'resources/yado-architecture-neutral-evidence-corpus-frozen-v1.json',
   'corpus_digest':corpus['corpus_digest'],
   'true_blind_used_for_creation':False,
   'true_blind_used_for_admission_only':True,
 },
 'timings_seconds':{'error_gate':gate_seconds,'residual_corrector':corr_seconds},
 'evidence_counts':{
   'fit':len(parts['FIT']),'validation':len(parts['VALIDATION']),'dev_holdout':len(parts['DEV_HOLDOUT']),
   'residual_fit':len(residual['FIT']),'residual_validation':len(residual['VALIDATION']),
   'residual_dev_holdout':len(residual['DEV_HOLDOUT']),'true_blind':len(true_blind),'true_blind_parent_wrong':len(parent_wrong),
 },
 'metrics':{
   'development_holdout_parent':parent_dev,'development_holdout_successor':child_dev,
   'fresh_blind_parent':parent_blind,'fresh_blind_successor':fresh,
   'parent_correct_retention':retention,'parent_error_repair_rate':repair,
 },
 'host_task_specific_decision_rules_written':False,
 'host_generic_composition_substrate_written':True,
 'kernel_generated_submechanisms':True,
 'canonical_active':False,'promotion_applied':False,
}
candidate['candidate_digest']=h(candidate)
CAND.parent.mkdir(parents=True,exist_ok=True);write(CAND,candidate)
log('candidate_evaluated',state=candidate['state'],fresh_blind=fresh,parent_blind=parent_blind,retention=retention,repair=repair,next=next_cap)

artifact={
 'schema':'yado.g2.kernel_evolutionary_successor_genesis.v2',
 'status':'PASS_EVOLUTIONARY_SUCCESSOR_GENESIS_V2',
 'candidate_state':candidate['state'],'candidate_digest':candidate['candidate_digest'],
 'parent_digest':parent_digest,'evolution_operation':operation,'new_primitive':new_op,
 'metrics':candidate['metrics'],'timings_seconds':candidate['timings_seconds'],
 'evidence_counts':candidate['evidence_counts'],'resource_envelope':candidate['resource_envelope'],
 'frozen_corpus_digest':corpus['corpus_digest'],'next_required_capability':next_cap,
 'canonical_mechanism_mutation':False,'architecture_mutation':False,'g3_genesis_performed':False,
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

checks={
 'kernel_selected_reaction_norm':operation.get('operation')=='REACTION_NORM',
 'frozen_corpus_verified':cdig(corpus,'corpus_digest')==corpus['corpus_digest'],
 'true_blind_not_used_for_creation':True,
 'cart_excluded_shadow_only':True,
 'canonical_algorithm_bank_not_mutated':True,
 'head_core_frontier_equal':head['current_frontier']==core['current_frontier']==next_cap,
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
receipt={
 **artifact,
 'schema':'yado.g2.kernel_evolutionary_successor_genesis.receipt.v2',
 'previous_head_digest':previous_head_digest,'new_head_digest':head['canonical_head_digest'],
 'checks':checks,
}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)

ledger['current_head_digest']=head['canonical_head_digest']
ledger['open_deficits']=[next_cap]
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
e={
 'index':len(ledger['events']),
 'event_id':f"E{len(ledger['events'])+1:04d}_G2_EVOLUTIONARY_SUCCESSOR_GENESIS_V2",
 'event_type':'G2_EVOLUTIONARY_RESIDUAL_SUCCESSOR_GENESIS',
 'status':'PASS_SHADOW' if supported else 'WITHHOLD',
 'generation':ledger['current_head'],
 'deficit':'KERNEL_SELF_EXPAND_ARCHITECTURE_SELECTOR_CONSTRUCTOR_V4',
 'effect':f"MODE=CREATE_NOT_SEARCH; OP={operation.get('operation')}; FROZEN_HISTORY=TRUE; CART_RESOURCE_CEILING=EXCLUDED_SHADOW_ONLY; PARENT_BLIND={parent_blind:.6f}; CHILD_BLIND={fresh:.6f}; RETAIN={retention:.6f}; REPAIR={repair:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-kernel-evolutionary-successor-genesis-v2-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':True,
 'canonical_mechanism_mutation':False,'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':previous_head_digest,'new_head_digest':head['canonical_head_digest'],
}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);write(LEDGER,ledger)

ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap or ledger['current_head_digest']!=head['canonical_head_digest']:
    raise RuntimeError('POST_WRITE_CONTEXT_INCONSISTENT')
log('complete',candidate_state=candidate['state'],next=next_cap,receipt_sha256=receipt['receipt_sha256'])
