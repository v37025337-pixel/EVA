from pathlib import Path
import copy,hashlib,json,os,sys,multiprocessing as mp,queue as qm
ROOT=Path(__file__).resolve().parent; REPO=ROOT.parent; PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
import yado_architecture_neutral_meta_synthesizer_v2 as neutral

HEAD=REPO/'canonical/yado-main-head-g2.json'; ARCH=REPO/'canonical/yado-g2-architecture-v1.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'; LEDGER=REPO/'architecture/evolution-ledger.json'
V1=REPO/'architecture/yado-kernel-self-expand-architecture-selector-constructor-v1.json'
V2=REPO/'receipts/yado-kernel-self-expand-architecture-selector-constructor-v2-run-33538562733.json'
PROBE=REPO/'receipts/yado-kernel-v3-operation-probe-run-33540595745.json'
ART=REPO/'architecture/yado-kernel-self-expand-architecture-selector-constructor-v3.json'
CAND=REPO/'candidates/kernel-self-generated/architecture-neutral-selector-reaction-norm-v3.json'
OUT=ROOT/'yado_kernel_self_expand_architecture_selector_constructor_v3_receipt.json'

def load(p): return json.loads(p.read_text())
def canon(x): return json.dumps(x,sort_keys=True,separators=(',',':'),default=str)
def h(x): return hashlib.sha256(canon(x).encode()).hexdigest()
def fsha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def score(x,k): return float((x or {}).get(k,0.0))
def subset(rows,n):
    return sorted(list(rows),key=lambda x:hashlib.sha256(canon(x).encode()).hexdigest())[:n]

head,ledger,v1,v2,probe=map(load,[HEAD,LEDGER,V1,V2,PROBE])
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['KERNEL_SELF_EXPAND_ARCHITECTURE_SELECTOR_CONSTRUCTOR_V3']: raise RuntimeError('UNEXPECTED_FRONTIER')
if probe.get('kernel_operation',{}).get('operation')!='REACTION_NORM' or probe.get('host_selected_operation') is not False: raise RuntimeError('REACTION_NORM_NOT_KERNEL_SELECTED')
if ledger['current_head_digest']!=head['canonical_head_digest']: raise RuntimeError('HEAD_LEDGER_MISMATCH')
before={p.name:fsha(p) for p in (HEAD,ARCH,CORE)}
baseline=max(score(v1,'fresh_blind'),score(v2,'fresh_blind'),score(neutral.receipt.get('kernel_result'),'fresh_blind'))
fit,val,revealed,blind=map(list,[neutral.fit,neutral.validation,neutral.revealed,neutral.blind])

def worker(db,fa,va,ra,ba,q):
    k=None
    try:
        k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(db))
        q.put({'ok':True,'result':k.synthesize_intelligence_with_extended_meta_grammar(fa,va,ra,ba)})
    except BaseException as e: q.put({'ok':False,'error':type(e).__name__+':'+str(e)[:900]})
    finally:
        if k:
            try:k.close()
            except Exception:pass

stages=[('RN24',24,18,64,70),('RN40',40,24,96,90),('RN64',64,32,128,110)]
results=[]; errors=[]
for name,nf,nv,nr,timeout in stages:
    q=mp.get_context('fork').Queue(1); db=ROOT/f'yado_v3_{name.lower()}.sqlite'
    p=mp.get_context('fork').Process(target=worker,args=(db,subset(fit,nf),subset(val,nv),subset(revealed,nr),blind,q))
    print(json.dumps({'stage':name,'timeout':timeout,'event':'START'}),flush=True); p.start(); p.join(timeout)
    if p.is_alive():
        p.terminate();p.join(5); errors.append({'stage':name,'error':f'TIMEOUT:{timeout}s'}); continue
    try:m=q.get(timeout=5)
    except qm.Empty: errors.append({'stage':name,'error':f'NO_RESULT:{p.exitcode}'}); continue
    if not m.get('ok'): errors.append({'stage':name,'error':m.get('error')}); continue
    r=m['result']; results.append({'stage':name,'validation':score(r,'validation'),'fresh_blind':score(r,'fresh_blind'),'result':r})

selected=max(results,key=lambda x:(x['validation'],-len(canon(x['result'])))) if results else None
sv=0.0 if not selected else selected['validation']; sb=0.0 if not selected else selected['fresh_blind']
supported=bool(selected and sv>=.90 and sb>=.90 and sb>baseline)
next_cap='KERNEL_NEUTRAL_ARCHITECTURE_SELECTION_WITH_SELF_GENERATED_SELECTOR_V1' if supported else 'KERNEL_SELF_EXPAND_ARCHITECTURE_SELECTOR_CONSTRUCTOR_V4'
candidate={'schema':'yado.g2.selector.reaction_norm.v3','state':'SHADOW_SUPPORTED' if supported else 'WITHHOLD',
 'kernel_operation':probe['kernel_operation'],'native_method':'synthesize_intelligence_with_extended_meta_grammar',
 'stage_results':[{k:v for k,v in x.items() if k!='result'} for x in results],'stage_errors':errors,
 'selected_stage':None if not selected else selected['stage'],'validation':sv,'fresh_blind':sb,'baseline':baseline,
 'selected_model':copy.deepcopy((selected or {}).get('result',{}).get('model')),
 'selected_algorithm':copy.deepcopy((selected or {}).get('result',{}).get('selected_algorithm')),
 'canonical_active':False,'promotion_applied':False,
 'semantic_boundary':'KERNEL SELECTED REACTION_NORM; HOST PROVIDED ONLY BOUNDED DATA/COMPUTE ENVELOPES. BLIND WAS NOT USED TO SELECT THE STAGE.'}
candidate['candidate_digest']=h(candidate); CAND.parent.mkdir(parents=True,exist_ok=True); CAND.write_text(json.dumps(candidate,indent=2,sort_keys=True,default=str)+'\n')
checks={'kernel_selected_reaction_norm':True,'blind_not_used_for_stage_selection':True,
 'bounded_total_seconds':sum(x[-1] for x in stages)<=300,
 'head_immutable':fsha(HEAD)==before[HEAD.name],'architecture_immutable':fsha(ARCH)==before[ARCH.name],
 'core_immutable':fsha(CORE)==before[CORE.name],'g3_not_started':head.get('g3_genesis_performed') is False}
status='PASS_KERNEL_SELF_EXPAND_ARCHITECTURE_SELECTOR_CONSTRUCTOR_V3' if all(checks.values()) else 'WITHHOLD_INFRASTRUCTURE_V3'
artifact={'schema':'yado.g2.kernel_self_expand_architecture_selector_constructor.v3','status':status,
 'candidate_state':candidate['state'],'candidate_digest':candidate['candidate_digest'],'kernel_operation':probe['kernel_operation'],
 'selected_stage':candidate['selected_stage'],'stage_errors':errors,'validation':sv,'fresh_blind':sb,'baseline':baseline,
 'checks':checks,'assistant_candidate_algorithm_written':False,'canonical_mutation':False,'architecture_mutation':False,
 'g3_genesis_performed':False,'next_required_capability':next_cap}
artifact['artifact_digest']=h(artifact); ART.write_text(json.dumps(artifact,indent=2,sort_keys=True)+'\n')
receipt=dict(artifact); receipt['schema']='yado.g2.kernel_self_expand_architecture_selector_constructor.receipt.v3'; receipt['receipt_sha256']=h(receipt)
OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_KERNEL_SELF_EXPAND_ARCHITECTURE_SELECTOR_CONSTRUCTOR_V3",
 'event_type':'KERNEL_NATIVE_REACTION_NORM_META_GRAMMAR_SELF_CONSTRUCTION','status':'PASS_SHADOW' if supported else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'KERNEL_SELF_EXPAND_ARCHITECTURE_SELECTOR_CONSTRUCTOR_V3',
 'effect':f"OP=REACTION_NORM; STAGE={candidate['selected_stage']}; CANDIDATE={candidate['state']}; VAL={sv:.6f}; BLIND={sb:.6f}; BASE={baseline:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-kernel-self-expand-architecture-selector-constructor-v3-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'promotion_applied':False,'generation_transition':False}
e['event_hash']=event_hash(e); ledger['events'].append(e); ledger['event_count']=len(ledger['events']); ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap]; ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger); LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':status,'candidate_state':candidate['state'],'selected_stage':candidate['selected_stage'],
 'validation':sv,'fresh_blind':sb,'baseline':baseline,'stage_errors':errors,'next_required_capability':next_cap},indent=2))
