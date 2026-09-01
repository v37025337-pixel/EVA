from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,sys,multiprocessing as mp,queue as queue_mod

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(PKG))

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
import yado_architecture_neutral_meta_synthesizer_v2 as neutral

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json'
CORE=REPO/'canonical'/'yado-unified-core-v1.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
PREV=REPO/'receipts'/'yado-kernel-self-repair-from-self-assessment-v1-run-33508125975.json'
CAND_DIR=REPO/'candidates'/'kernel-self-generated'
CAND=CAND_DIR/'architecture-neutral-selector-algorithm-genesis-v1.json'
ART=REPO/'architecture'/'yado-kernel-self-expand-architecture-selector-constructor-v1.json'
OUT=ROOT/'yado_kernel_self_expand_architecture_selector_constructor_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sc(x,k):return float(x.get(k,0.0)) if isinstance(x,dict) else 0.0

head=load(HEAD);ledger=load(LEDGER);prev=load(PREV)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['KERNEL_SELF_EXPAND_ARCHITECTURE_SELECTOR_CONSTRUCTOR_V1']:
    raise RuntimeError('UNEXPECTED_FRONTIER')
if prev.get('candidate_state')!='WITHHOLD':
    raise RuntimeError('EXPECTED_PRIOR_CONSTRUCTOR_WITHHOLD')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):
    raise RuntimeError('HEAD_LEDGER_MISMATCH')

arch_sha=fsha(ARCH);head_sha=fsha(HEAD);core_sha=fsha(CORE)
fit=list(neutral.fit);validation=list(neutral.validation);revealed=list(neutral.revealed);blind=list(neutral.blind)
baseline=max(float(prev.get('fresh_blind',0.0)),float((neutral.receipt.get('kernel_result') or {}).get('fresh_blind',0.0)))

GENERATOR_TIMEOUT_SECONDS=int(os.getenv('YADO_GENERATOR_TIMEOUT_SECONDS','120'))

def _generator_worker(method_name,db_path,fit_data,validation_data,revealed_data,blind_data,outq):
    k=None
    try:
        k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(db_path))
        fn=getattr(k,method_name)
        result=fn(fit_data,validation_data,revealed_data,blind_data)
        outq.put({'ok':True,'result':result})
    except BaseException as exc:
        outq.put({'ok':False,'error':type(exc).__name__+':'+str(exc)[:900]})
    finally:
        if k is not None:
            try:k.close()
            except Exception:pass

def _run_bounded_generator(label,method_name):
    ctx=mp.get_context('fork')
    outq=ctx.Queue(maxsize=1)
    db=ROOT/f'kernel_self_expand_architecture_selector_constructor_v1_{label.lower()}.sqlite'
    proc=ctx.Process(
        target=_generator_worker,
        args=(method_name,db,fit,validation,revealed,blind,outq),
        name=f'yado-{label.lower()}',
    )
    print(json.dumps({'event':'GENERATOR_START','label':label,'method':method_name,'timeout_seconds':GENERATOR_TIMEOUT_SECONDS},sort_keys=True),flush=True)
    proc.start()
    proc.join(GENERATOR_TIMEOUT_SECONDS)
    if proc.is_alive():
        proc.terminate()
        proc.join(10)
        if proc.is_alive():
            proc.kill();proc.join(5)
        print(json.dumps({'event':'GENERATOR_TIMEOUT','label':label,'timeout_seconds':GENERATOR_TIMEOUT_SECONDS},sort_keys=True),flush=True)
        return None,f'TIMEOUT:{GENERATOR_TIMEOUT_SECONDS}s'
    try:
        msg=outq.get(timeout=5)
    except queue_mod.Empty:
        err=f'NO_RESULT:exitcode={proc.exitcode}'
        print(json.dumps({'event':'GENERATOR_NO_RESULT','label':label,'exitcode':proc.exitcode},sort_keys=True),flush=True)
        return None,err
    if not msg.get('ok'):
        err=str(msg.get('error') or 'UNKNOWN_GENERATOR_ERROR')
        print(json.dumps({'event':'GENERATOR_ERROR','label':label,'error':err},sort_keys=True),flush=True)
        return None,err
    result=msg.get('result')
    print(json.dumps({'event':'GENERATOR_DONE','label':label,'validation':sc(result,'validation'),'fresh_blind':sc(result,'fresh_blind')},sort_keys=True),flush=True)
    return result,None

probe_db=ROOT/'kernel_self_expand_architecture_selector_constructor_v1_probe.sqlite'
probe=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(probe_db))
try:
    available={
     'synthesize_intelligence_algorithm_component':hasattr(probe,'synthesize_intelligence_algorithm_component'),
     'synthesize_intelligence_with_extended_meta_grammar':hasattr(probe,'synthesize_intelligence_with_extended_meta_grammar'),
    }
finally:
    probe.close()

results={}
errors={}
for label,method_name in (
    ('RC5_ALGORITHM_GENESIS','synthesize_intelligence_algorithm_component'),
    ('RC6_EXTENDED_META_GRAMMAR','synthesize_intelligence_with_extended_meta_grammar'),
):
    if not available[method_name]:
        continue
    result,error=_run_bounded_generator(label,method_name)
    if result is not None:results[label]=result
    if error is not None:errors[label]=error

# Follow YADO's own existing binder selection convention: choose by validation only.
selected_origin=None;selected=None
if results:
    ordered=sorted(results.items(),key=lambda kv:(sc(kv[1],'validation'),kv[0]=='RC5_ALGORITHM_GENESIS'),reverse=True)
    selected_origin,selected=ordered[0]

val=sc(selected or {},'validation')
fresh=sc(selected or {},'fresh_blind')
supported=(
    selected is not None
    and val>=0.90
    and fresh>=0.90
    and fresh>baseline
)

candidate={
 'schema':'yado.kernel_self_generated.architecture_neutral_selector.algorithm_genesis.v1',
 'state':'SHADOW_SUPPORTED' if supported else 'WITHHOLD',
 'origin':selected_origin,
 'available_native_generators':available,
 'generator_results':results,
 'generator_errors':errors,
 'selected_validation':val,
 'selected_fresh_blind':fresh,
 'baseline_best_prior_fresh_blind':baseline,
 'selected_model':copy.deepcopy((selected or {}).get('model')),
 'selected_algorithm':copy.deepcopy((selected or {}).get('selected_algorithm')),
 'canonical_active':False,'promotion_applied':False,
 'architecture_sha256':arch_sha,'parent_head_digest':head.get('canonical_head_digest'),
 'semantic_boundary':'KERNEL-NATIVE ALGORITHM-GENESIS CANDIDATE FOR ARCHITECTURE-NEUTRAL FAMILY SELECTION; NO HOST-WRITTEN CANDIDATE ALGORITHM AND NO CANONICAL MUTATION.'
}
candidate['candidate_digest']=h(candidate)
CAND_DIR.mkdir(parents=True,exist_ok=True);CAND.write_text(json.dumps(candidate,indent=2,sort_keys=True,default=str)+'\n')

next_cap='KERNEL_NEUTRAL_ARCHITECTURE_SELECTION_WITH_SELF_GENERATED_SELECTOR_V1' if supported else 'KERNEL_SELF_EXPAND_ARCHITECTURE_SELECTOR_CONSTRUCTOR_V2'
checks={
 'prior_constructor_failed':prev.get('candidate_state')=='WITHHOLD',
 'at_least_one_native_generator_available':any(available.values()),
 'blind_not_used_for_generator_selection':True,
 'architecture_immutable':fsha(ARCH)==arch_sha,
 'head_immutable':fsha(HEAD)==head_sha,
 'core_immutable':fsha(CORE)==core_sha,
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
attempt_completed=all(checks.values())

artifact={
 'schema':'yado.g2.kernel_self_expand_architecture_selector_constructor.v1',
 'status':'PASS_KERNEL_SELF_EXPAND_ARCHITECTURE_SELECTOR_CONSTRUCTOR_V1' if attempt_completed else 'WITHHOLD_KERNEL_SELF_EXPAND_ARCHITECTURE_SELECTOR_CONSTRUCTOR_V1',
 'candidate_state':candidate['state'],'candidate_digest':candidate['candidate_digest'],
 'available_native_generators':available,'generator_errors':errors,'selected_origin':selected_origin,
 'validation':val,'fresh_blind':fresh,'baseline_best_prior_fresh_blind':baseline,
 'checks':checks,'assistant_candidate_algorithm_written':False,
 'canonical_mutation':False,'architecture_mutation':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,'claim_boundary':candidate['semantic_boundary']
}
artifact['artifact_digest']=h(artifact);ART.write_text(json.dumps(artifact,indent=2,sort_keys=True,default=str)+'\n')

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
 'schema':'yado.g2.kernel_self_expand_architecture_selector_constructor.receipt.v1',
 'status':artifact['status'],'candidate_state':candidate['state'],'candidate_digest':candidate['candidate_digest'],
 'available_native_generators':available,'generator_errors':errors,'selected_origin':selected_origin,
 'validation':val,'fresh_blind':fresh,'baseline_best_prior_fresh_blind':baseline,'checks':checks,
 'canonical_mutation':False,'architecture_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,'semantic_boundary':artifact['claim_boundary']
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True,default=str)+'\n')

e={
 'index':len(ledger['events']),
 'event_id':f"E{len(ledger['events'])+1:04d}_G2_KERNEL_SELF_EXPAND_ARCHITECTURE_SELECTOR_CONSTRUCTOR_V1",
 'event_type':'KERNEL_NATIVE_ALGORITHM_GENESIS_SELF_CONSTRUCTION',
 'status':'PASS_SHADOW' if supported else 'WITHHOLD','generation':ledger['current_head'],
 'deficit':'KERNEL_SELF_EXPAND_ARCHITECTURE_SELECTOR_CONSTRUCTOR_V1',
 'effect':f"ORIGIN={selected_origin}; CANDIDATE={candidate['state']}; VAL={val:.6f}; BLIND={fresh:.6f}; BASE={baseline:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-kernel-self-expand-architecture-selector-constructor-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'promotion_applied':False,'generation_transition':False
}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({
 'status':receipt['status'],'candidate_state':candidate['state'],'available_native_generators':available,
 'generator_errors':errors,'selected_origin':selected_origin,'validation':val,'fresh_blind':fresh,
 'baseline_best_prior_fresh_blind':baseline,'next_required_capability':next_cap,
 'receipt_sha256':receipt['receipt_sha256']
},indent=2,sort_keys=True,default=str))
if not attempt_completed:raise SystemExit('KERNEL_SELF_EXPAND_CONSTRUCTOR_INFRASTRUCTURE_WITHHELD')
