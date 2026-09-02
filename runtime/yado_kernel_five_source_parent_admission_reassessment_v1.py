from __future__ import annotations
from pathlib import Path
from itertools import combinations
import copy,hashlib,json,os,sys,time
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

import yado_architecture_neutral_meta_synthesizer_v2 as neutral
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_organ_runtime_native_v1 import tree_predict
from yado_cognitive_growth_runtime_v1 import centroid_predict,knn_predict
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
BASE=REPO/'receipts/yado-architecture-neutral-meta-synth-v2-latest.json'
CORPUS=REPO/'resources/yado-architecture-neutral-evidence-corpus-frozen-v1.json'
CAL=REPO/'candidates/kernel-self-generated/evolutionary-centroid-calibrated-successor-v2.json'
KNN=REPO/'candidates/kernel-self-generated/evolutionary-local-knn-successor-v1.json'
F4=REPO/'candidates/kernel-self-generated/fresh-four-source-curriculum-v1.json'
F5H=REPO/'resources/yado-five-source-transfer-history-v1.json'
ART=REPO/'architecture/yado-kernel-five-source-parent-admission-reassessment-v1.json'
CAND=REPO/'candidates/kernel-self-generated/fresh-four-pair-knn-five-source-admission-v1.json'
OUT=ROOT/'yado_kernel_five_source_parent_admission_reassessment_v1_receipt.json'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def write(p,o): p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):
    x=copy.deepcopy(o);x.pop(field,None);return h(x)
def log(stage,**kw):
    print(json.dumps({'stage':stage,'ts':time.time(),**kw},sort_keys=True,default=str),flush=True)

head,core,ledger,base,corpus,cal,knn,f4,f5h=map(load,[HEAD,CORE,LEDGER,BASE,CORPUS,CAL,KNN,F4,F5H])
validate_ledger_v2(ledger)
front='KERNEL_FIVE_SOURCE_TRANSFER_REPAIR_V1'
if ledger.get('open_deficits')!=[front]:
    raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if f5h.get('five_source_result',{}).get('parent')!=0.9494949494949495:
    raise RuntimeError('FRESH5_PARENT_EVIDENCE_MISMATCH')
if f4.get('selected_skill_id')!='PAIR_KNN':
    raise RuntimeError('EXPECTED_FOUR_SOURCE_PAIR_KNN_PARENT')

data=neutral.build_dataset(force=True)
expected={x['id']:x['sha256'] for x in corpus['source_digests']}
actual={sid:r['sha256'] for sid,r in data['rows'].items()}
if expected!=actual:raise RuntimeError('SOURCE_DIGEST_DRIFT')
ids=sorted(data['rows'])
def make_cases(size):
    out=[]
    for combo in combinations(ids,size):
        x,y,counts=neutral._vector(combo,data['rows'])
        out.append({'key':'|'.join(combo),'x':x,'y':y,'size':size})
    return out
spaces={size:make_cases(size) for size in (1,2,3,4,5)}
if [len(spaces[s]) for s in (1,2,3,4,5)]!=[12,66,220,495,792]:
    raise RuntimeError('SPACE_COUNTS_INVALID')

# Previous parent behavior.
parent_model=base['kernel_result']['model']
g=cal['generator'];gate=g['gate_model'];corr=g['corrector_model'];th=float(cal['selected_threshold'])
def orig(x):return tree_predict(parent_model,x)
def dists(model,x):
    out=[]
    for label,center in model['centroids'].items():
        d=0.0
        for key in model['features']:
            scale=max(float(model['scales'].get(key,1.0)),1e-12)
            d+=((float(x.get(key,0.0))-float(center[key]))/scale)**2
        out.append((d,label))
    return sorted(out,key=lambda z:(z[0],z[1]))
def margin(model,x):
    r=dists(model,x);return 0.0 if len(r)<2 else max(0.0,r[1][0]-r[0][0])
def cal_pred(x):
    if centroid_predict(gate,x)!='PARENT_ERROR':return orig(x)
    if margin(gate,x)+1e-12<th:return orig(x)
    return centroid_predict(corr,x)
def ablated_pred(c):
    sm=knn.get('selected_model') or {}
    if not sm:return cal_pred(c['x'])
    return knn_predict(sm['corrector'],c['x']) if knn_predict(sm['gate'],c['x'])=='BASE_ERROR' else cal_pred(c['x'])

# Candidate behavior from F4 PAIR_KNN, unchanged.
source_ids=ids;pairs=list(combinations(source_ids,2))
def augment_pair(c):
    x=dict(c['x']);present=set(c['key'].split('|'))
    for s in source_ids:x['src::'+s]=1.0 if s in present else 0.0
    for a,b in pairs:x['srcpair::'+a+'&&'+b]=1.0 if a in present and b in present else 0.0
    return x
model=f4['selected_model']
def candidate_pred(c):return knn_predict(model,augment_pair(c))
def acc(rows,pred):return sum(pred(c)==c['y'] for c in rows)/max(1,len(rows))

per_size={}
for s in (1,2,3,4,5):
    b=acc(spaces[s],ablated_pred);c=acc(spaces[s],candidate_pred)
    per_size[str(s)]={'ablation_previous_parent':b,'candidate':c,'gain':c-b,'count':len(spaces[s])}

history_rows=spaces[1]+spaces[2]+spaces[3]+spaces[4]
history_ablation=acc(history_rows,ablated_pred)
history_candidate=acc(history_rows,candidate_pred)
fresh5_ablation=per_size['5']['ablation_previous_parent']
fresh5_candidate=per_size['5']['candidate']
restore5=acc(spaces[5],candidate_pred)
recorded5=float(f5h['five_source_result']['parent'])
recorded4=float(f4['metrics']['fresh_four_candidate'])
recorded4_parent=float(f4['metrics']['fresh_four_parent'])

checks={
 'source_sha_exact_match':expected==actual,
 'recorded_fresh5_matches_reconstruction':abs(fresh5_candidate-recorded5)<1e-12,
 'fresh5_above_gate':fresh5_candidate>=0.90,
 'fresh5_beats_ablation':fresh5_candidate>fresh5_ablation,
 'restore_exact':abs(restore5-fresh5_candidate)<1e-12,
 'four_source_original_fresh_gain_positive':recorded4>recorded4_parent,
 'aggregate_history_no_regression':history_candidate>=history_ablation,
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
supported=all(checks.values())
state='SHADOW_SUPPORTED' if supported else 'WITHHOLD'
next_cap='KERNEL_FRESH_TRANSFER_SUCCESSOR_CANONICAL_ADMISSION_V1' if supported else 'KERNEL_FIVE_SOURCE_TRANSFER_REPAIR_V1'

candidate={
 'schema':'yado.g2.fresh_four_pair_knn_five_source_admission.v1',
 'state':state,
 'candidate_id':'FRESH_FOUR_PAIR_KNN_V1',
 'evidence':{
   'recorded_fresh_four':recorded4,
   'recorded_fresh_four_parent':recorded4_parent,
   'recorded_fresh_five_first_exposure':recorded5,
   'five_source_case_count':792,
   'per_size':per_size,
   'aggregate_sizes_1_to_4':{'ablation':history_ablation,'candidate':history_candidate,'gain':history_candidate-history_ablation},
   'five_source_ablation':fresh5_ablation,
   'five_source_restore':restore5,
 },
 'checks':checks,
 'canonical_active':False,
 'promotion_applied':False,
 'canonical_mechanism_mutation':False,
 'architecture_mutation':False,
 'g3_genesis_performed':False,
}
candidate['candidate_digest']=h(candidate);CAND.parent.mkdir(parents=True,exist_ok=True);write(CAND,candidate)
log('admission_reassessment',state=state,evidence=candidate['evidence'],checks=checks,next=next_cap)

artifact={
 'schema':'yado.g2.kernel_five_source_parent_admission_reassessment.v1',
 'status':'PASS_PARENT_ADMISSION_REASSESSMENT_V1',
 'candidate_state':state,
 'candidate_digest':candidate['candidate_digest'],
 'fresh5_score':fresh5_candidate,
 'fresh5_ablation':fresh5_ablation,
 'history_candidate':history_candidate,
 'history_ablation':history_ablation,
 'next_required_capability':next_cap,
 'canonical_mechanism_mutation':False,
 'architecture_mutation':False,
 'g3_genesis_performed':False,
}
artifact['artifact_digest']=h(artifact);write(ART,artifact)

prev=head['canonical_head_digest']
core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits';core['core_digest']=cdig(core,'core_digest');write(CORE,core)
head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits';head['unified_core']['core_digest']=core['core_digest'];head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)
receipt={**artifact,'schema':'yado.g2.kernel_five_source_parent_admission_reassessment.receipt.v1',
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest'],'checks':checks}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)

ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap]
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_FRESH_FOUR_PAIR_KNN_REASSESSMENT_V1",
 'event_type':'G2_CAUSAL_FRESH_TRANSFER_REASSESSMENT','status':'PASS_SHADOW' if supported else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':front,
 'effect':f"CANDIDATE=FRESH_FOUR_PAIR_KNN_V1; FRESH5={fresh5_candidate:.6f}; ABLATION5={fresh5_ablation:.6f}; HISTORY={history_candidate:.6f}; HISTORY_ABLATION={history_ablation:.6f}; STATE={state}; NEXT={next_cap}",
 'source_path':f'receipts/yado-kernel-five-source-parent-admission-reassessment-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':True,'canonical_mechanism_mutation':False,'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);write(LEDGER,ledger)
ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_WRITE_CONTEXT_INCONSISTENT')
log('complete',state=state,next=next_cap)
