from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,multiprocessing as mp,os,queue as qm,sys
ROOT=Path(__file__).resolve().parent; REPO=ROOT.parent; PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
import yado_architecture_neutral_meta_synthesizer_v2 as neutral

LEDGER=REPO/'architecture/evolution-ledger.json'
HEAD=REPO/'canonical/yado-main-head-g2.json'
ARCH=REPO/'canonical/yado-g2-architecture-v1.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
BASE_RECEIPT=REPO/'receipts/yado-architecture-neutral-meta-synth-v2-latest.json'
ART=REPO/'architecture/yado-kernel-self-expand-architecture-selector-constructor-v4.json'
CAND=REPO/'candidates/kernel-self-generated/architecture-neutral-selector-memoized-meta-grammar-v4.json'
OUT=ROOT/'yado_kernel_self_expand_architecture_selector_constructor_v4_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def sc(x,k):return float((x or {}).get(k,0.0))

ledger=load(LEDGER);head=load(HEAD);base=load(BASE_RECEIPT)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['KERNEL_SELF_EXPAND_ARCHITECTURE_SELECTOR_CONSTRUCTOR_V4']:
    raise RuntimeError('UNEXPECTED_FRONTIER')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):
    raise RuntimeError('HEAD_LEDGER_MISMATCH')
before={str(p):fsha(p) for p in (HEAD,ARCH,CORE)}
data=neutral.build_dataset()
fit,validation,revealed,blind=map(list,[data['fit'],data['validation'],data['revealed'],data['blind']])
baseline=float((base.get('kernel_result') or {}).get('fresh_blind',0.0))

def worker(q):
    k=None
    try:
        k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_v4_memoized_meta_grammar.sqlite'))
        method=k.synthesize_intelligence_with_extended_meta_grammar
        mg=method.__globals__['mg']
        original=mg.best_intel_leaf
        cache={};stats={'hits':0,'misses':0}
        def memo(cases,algs):
            key=tuple(sorted(id(x) for x in cases))
            if key in cache:
                stats['hits']+=1
                return copy.deepcopy(cache[key])
            stats['misses']+=1
            out=original(cases,algs)
            cache[key]=copy.deepcopy(out)
            return out
        mg.best_intel_leaf=memo
        try:
            result=method(fit,validation,revealed,blind)
        finally:
            mg.best_intel_leaf=original
        q.put({'ok':True,'result':result,'cache_stats':dict(stats,entries=len(cache))})
    except BaseException as e:
        q.put({'ok':False,'error':type(e).__name__+':'+str(e)[:1600]})
    finally:
        if k is not None:
            try:k.close()
            except Exception:pass

ctx=mp.get_context('fork');q=ctx.Queue(1);p=ctx.Process(target=worker,args=(q,),name='yado-g2-v4')
p.start();p.join(300)
if p.is_alive():
    p.terminate();p.join(10)
    if p.is_alive():p.kill();p.join(5)
    msg={'ok':False,'error':'TIMEOUT:300s'}
else:
    try:msg=q.get(timeout=8)
    except qm.Empty:msg={'ok':False,'error':f'NO_RESULT:exitcode={p.exitcode}'}

result=msg.get('result') or {}
validation_score=sc(result,'validation');fresh=sc(result,'fresh_blind')
supported=bool(msg.get('ok') and validation_score>=0.90 and fresh>=0.90 and fresh>baseline)
next_cap='KERNEL_NEUTRAL_ARCHITECTURE_SELECTION_WITH_SELF_GENERATED_SELECTOR_V1' if supported else 'KERNEL_SELF_EXPAND_ARCHITECTURE_SELECTOR_CONSTRUCTOR_V5'
candidate={
 'schema':'yado.g2.kernel_self_generated.memoized_extended_meta_grammar_selector.v4',
 'state':'SHADOW_SUPPORTED' if supported else 'WITHHOLD',
 'native_method':'synthesize_intelligence_with_extended_meta_grammar',
 'native_result':result,
 'runtime_optimization':'MEMOIZE_IDENTICAL_BEST_INTEL_LEAF_SUBSETS_ONLY',
 'search_space_changed':False,'scoring_changed':False,'blind_used_for_selection':False,
 'cache_stats':msg.get('cache_stats'),'generator_error':msg.get('error'),
 'validation':validation_score,'fresh_blind':fresh,'baseline_best_prior_fresh_blind':baseline,
 'canonical_active':False,'promotion_applied':False,
 'semantic_boundary':'HOST OPTIMIZED ONLY REPEATED EXECUTION BY MEMOIZATION. CANDIDATE ENUMERATION, NATIVE LEAF FITTING, VALIDATION SELECTION AND BLIND EVALUATION REMAIN YADO META-GRAMMAR SEMANTICS.'
}
candidate['candidate_digest']=h(candidate);CAND.parent.mkdir(parents=True,exist_ok=True);CAND.write_text(json.dumps(candidate,indent=2,sort_keys=True,default=str)+'\n')
checks={
 'frontier_v4':True,'search_space_unchanged':True,'scoring_unchanged':True,'blind_not_used_for_selection':True,
 'head_immutable':fsha(HEAD)==before[str(HEAD)],'architecture_immutable':fsha(ARCH)==before[str(ARCH)],
 'core_immutable':fsha(CORE)==before[str(CORE)],'g3_not_started':head.get('g3_genesis_performed') is False
}
status='PASS_KERNEL_SELF_EXPAND_ARCHITECTURE_SELECTOR_CONSTRUCTOR_V4' if all(checks.values()) else 'WITHHOLD_INFRASTRUCTURE_V4'
artifact={
 'schema':'yado.g2.kernel_self_expand_architecture_selector_constructor.v4','status':status,
 'candidate_state':candidate['state'],'candidate_digest':candidate['candidate_digest'],
 'generator_error':candidate['generator_error'],'cache_stats':candidate['cache_stats'],
 'validation':validation_score,'fresh_blind':fresh,'baseline_best_prior_fresh_blind':baseline,
 'checks':checks,'assistant_candidate_algorithm_written':False,'host_runtime_optimization_written':True,
 'canonical_mutation':False,'architecture_mutation':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap
}
artifact['artifact_digest']=h(artifact);ART.write_text(json.dumps(artifact,indent=2,sort_keys=True,default=str)+'\n')
receipt=dict(artifact);receipt['schema']='yado.g2.kernel_self_expand_architecture_selector_constructor.receipt.v4';receipt['receipt_sha256']=h(receipt)
OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True,default=str)+'\n')
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_KERNEL_SELF_EXPAND_ARCHITECTURE_SELECTOR_CONSTRUCTOR_V4",
 'event_type':'KERNEL_NATIVE_EXTENDED_META_GRAMMAR_WITH_SEMANTICS_PRESERVING_MEMOIZATION','status':'PASS_SHADOW' if supported else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'KERNEL_SELF_EXPAND_ARCHITECTURE_SELECTOR_CONSTRUCTOR_V4',
 'effect':f"CANDIDATE={candidate['state']}; VAL={validation_score:.6f}; BLIND={fresh:.6f}; BASE={baseline:.6f}; CACHE={candidate['cache_stats']}; NEXT={next_cap}",
 'source_path':f'receipts/yado-kernel-self-expand-architecture-selector-constructor-v4-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'promotion_applied':False,'generation_transition':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':status,'candidate_state':candidate['state'],'generator_error':candidate['generator_error'],
 'cache_stats':candidate['cache_stats'],'validation':validation_score,'fresh_blind':fresh,'baseline':baseline,'next_required_capability':next_cap},indent=2,default=str))
