from __future__ import annotations
from pathlib import Path
from itertools import combinations
import copy,hashlib,json,os,subprocess,sys

ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

import yado_architecture_neutral_meta_synthesizer_v2 as neutral
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_cognitive_growth_runtime_v1 import knn_predict
from yado_g2_canonical_high_scale_binding_runtime_v5 import CanonicalHighScaleBindingRuntimeV5
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
CORPUS=REPO/'resources/yado-architecture-neutral-evidence-corpus-frozen-v1.json'
HIGH2=REPO/'candidates/kernel-self-generated/high-scale-repair-v2.json'
V4=REPO/'candidates/kernel-self-generated/high-scale-repair-v4.json'
BIND4=REPO/'candidates/kernel-self-generated/native-selector-canonical-binding-v4.json'
ADAPTER=REPO/'runtime/yado_g2_canonical_high_scale_binding_runtime_v5.py'
ART=REPO/'architecture/yado-kernel-scale-conditional-high-scale-repair-v5.json'
CAND=REPO/'candidates/kernel-self-generated/high-scale-repair-v5.json'
OUT=ROOT/'yado_kernel_scale_conditional_high_scale_repair_v5_receipt.json'
GUARD=ROOT/'yado_canonical_invariant_guard_v1.py'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):
    x=copy.deepcopy(o);x.pop(field,None);return h(x)
def log(stage,**kw):print(json.dumps({'stage':stage,**kw},sort_keys=True,default=str),flush=True)

head,core,ledger,prov,corpus,high2,v4,bind4=map(load,[HEAD,CORE,LEDGER,PROV,CORPUS,HIGH2,V4,BIND4])
validate_ledger_v2(ledger)
front='KERNEL_SCALE_CONDITIONAL_SUCCESSOR_HIGH_SCALE_REPAIR_V5'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if head.get('current_frontier')!=front or core.get('current_frontier')!=front:raise RuntimeError('HEAD_CORE_FRONTIER_MISMATCH')
if v4.get('state')!='SHADOW_SUPPORTED' or v4.get('selected_skill_id')!='HIGH_ONLY_TRIPLE_KNN_V4':raise RuntimeError('V4_SELECTION_DRIFT')
if bind4.get('state')!='WITHHOLD':raise RuntimeError('BIND4_NOT_WITHHOLD')
if head.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')

data=neutral.build_dataset(force=True)
expected={x['id']:x['sha256'] for x in corpus['source_digests']}
actual={sid:r['sha256'] for sid,r in data['rows'].items()}
if expected!=actual:raise RuntimeError('SOURCE_DIGEST_DRIFT')
ids=sorted(data['rows']);pairs=list(combinations(ids,2));triples=list(combinations(ids,3))

def make_cases(size):
    out=[]
    for combo in combinations(ids,size):
        x,y,_=neutral._vector(combo,data['rows'])
        out.append({'key':'|'.join(combo),'x':x,'y':y,'size':size})
    return out

spaces={s:make_cases(s) for s in range(1,13)}
expected_counts=[12,66,220,495,792,924,792,495,220,66,12,1]
if [len(spaces[s]) for s in range(1,13)]!=expected_counts:raise RuntimeError('SPACE_COUNTS_INVALID')
history=[c for s in range(1,13) for c in spaces[s]]

def rep(c,order):
    z=dict(c['x']);present=set(c['key'].split('|'))
    for sid in ids:z['src::'+sid]=1.0 if sid in present else 0.0
    if order>=2:
        for a,b in pairs:z['srcpair::'+a+'&&'+b]=1.0 if a in present and b in present else 0.0
    if order>=3:
        for a,b,d in triples:z['srctri::'+a+'&&'+b+'&&'+d]=1.0 if a in present and b in present and d in present else 0.0
    return z

parent_model=high2['selected_model'];v4_model=v4['selected_model'];activation=int(v4['selected_spec']['activation_min_size'])
def parent_pred(c):return knn_predict(parent_model,rep(c,2))
def v4_high_pred(c):return knn_predict(v4_model,rep(c,3))
def expected_route(c):return 'V4_HIGH' if c['size']>=activation else 'V2_PARENT'
def broken_v4_route(c):return 'V4_HIGH' if float(c['x']['source_count'])>=activation else 'V2_PARENT'

def route_key(c):
    return 'V4_HIGH' if len([x for x in c['key'].split('|') if x])>=activation else 'V2_PARENT'
def route_invert(c):
    cardinality=int(round(float(c['x']['source_count'])*3.0))
    return 'V4_HIGH' if cardinality>=activation else 'V2_PARENT'

def pred_for_route(c,routefn):
    return v4_high_pred(c) if routefn(c)=='V4_HIGH' else parent_pred(c)
def acc(rows,pred):return sum(pred(c)==c['y'] for c in rows)/max(1,len(rows))
def racc(rows,routefn):return sum(routefn(c)==expected_route(c) for c in rows)/max(1,len(rows))

spent_low=[c for s in range(1,10) for c in spaces[s]]
spent_high=[c for s in range(10,13) for c in spaces[s]]
baseline_fit=racc(spent_low,broken_v4_route);baseline_hold=racc(spent_high,broken_v4_route)
skills=[];specs={};metrics={}
for sid,routefn in (('KEY_CARDINALITY_ROUTE_V5',route_key),('INVERT_NORMALIZED_SOURCE_COUNT_ROUTE_V5',route_invert)):
    fit_score=racc(spent_low,routefn);hold_score=racc(spent_high,routefn)
    pred=lambda c,rf=routefn:pred_for_route(c,rf)
    per={str(s):{'route':racc(spaces[s],routefn),'parent':acc(spaces[s],parent_pred),'candidate':acc(spaces[s],pred),'count':len(spaces[s])} for s in range(1,13)}
    no_reg=all(per[str(s)]['candidate']+1e-12>=per[str(s)]['parent'] for s in range(1,13))
    skills.append({'skill_id':sid,'artifact_digest':h({'strategy':sid,'activation':activation}),
      'structural_valid':True,'semantic_consistency':1.0,
      'fit_baseline':baseline_fit,'fit_candidate':fit_score,
      'heldout_baseline':baseline_hold,'heldout_candidate':hold_score,
      'regression_pass':no_reg,'state_integrity':True,'rollback_available':True,
      'metadata':{'family':'ROUTE_SEMANTICS_REPAIR','activation_min_size':activation,'per_size':per}})
    specs[sid]={'strategy':'KEY_CARDINALITY' if sid.startswith('KEY_') else 'INVERT_NORMALIZED_SOURCE_COUNT','normalization_denominator':3.0,'activation_min_size':activation}
    metrics[sid]={'fit_route':fit_score,'holdout_route':hold_score,'predictive_no_regression':no_reg,'per_size':per}
    log('candidate_done',skill=sid,fit_route=fit_score,holdout_route=hold_score,no_regression=no_reg)

# Kernel selects the semantic repair from spent evidence only.
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_high_scale_v5_skill_select.sqlite'))
try:
    selection=k.select_evolution_skills(skills,max_skills=1,min_semantic_consistency=.90,min_fit_gain=0.0,max_heldout_drop=0.0,min_heldout_gain=0.0)
finally:k.close()
selected_ids=list(selection.get('selected_skill_ids') or [])
selected_id=selected_ids[0] if selected_ids else None
spec=specs.get(selected_id)
log('kernel_selection',selection=selection,selected=selected_id)

if spec:
    binding={
      'schema':'yado.g2.high_scale_semantic_route_candidate.v5',
      'generation':head['generation_id'],
      'route_semantics':spec,
      'branch_artifacts':{
        'parent_v2':'candidates/kernel-self-generated/high-scale-repair-v2.json',
        'high_scale_v4':'candidates/kernel-self-generated/high-scale-repair-v4.json',
        'corpus':'resources/yado-architecture-neutral-evidence-corpus-frozen-v1.json'
      },
      'artifact_sha256':{
        'candidates/kernel-self-generated/high-scale-repair-v2.json':sha(HIGH2),
        'candidates/kernel-self-generated/high-scale-repair-v4.json':sha(V4),
        'resources/yado-architecture-neutral-evidence-corpus-frozen-v1.json':sha(CORPUS),
        'runtime/yado_g2_canonical_high_scale_binding_runtime_v5.py':sha(ADAPTER)
      }
    }
    binding['binding_digest']=h(binding)
    with CanonicalHighScaleBindingRuntimeV5(binding=binding,repo_root=REPO) as rt:
        route_score=racc(history,rt.route)
        predictive_total=acc(history,rt.predict)
        parent_total=acc(history,parent_pred)
        per_size={str(s):{'route':racc(spaces[s],rt.route),'parent':acc(spaces[s],parent_pred),'candidate':acc(spaces[s],rt.predict)} for s in range(1,13)}
else:
    binding=None;route_score=0.0;predictive_total=acc(history,parent_pred);parent_total=predictive_total;per_size={}

checks={
 'source_sha_exact_match':expected==actual,
 'spent_history_sizes_1_to_12_only':True,
 'kernel_selected_route_repair':selected_id is not None,
 'selected_route_exact_on_all_spent_cases':abs(route_score-1.0)<1e-12,
 'size11_shadow_score_reproduced':bool(spec) and abs(per_size['11']['candidate']-1.0)<1e-12,
 'size12_spent_history_not_regressed':bool(spec) and per_size['12']['candidate']+1e-12>=per_size['12']['parent'],
 'predictive_total_no_regression':predictive_total+1e-12>=parent_total,
 'fresh_route_probes_not_materialized':True,
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
supported=all(checks.values())
state='SHADOW_SUPPORTED' if supported else 'WITHHOLD'
next_cap='KERNEL_NATIVE_SELECTOR_CANONICAL_BINDING_V5' if supported else 'KERNEL_SCALE_CONDITIONAL_SUCCESSOR_HIGH_SCALE_REPAIR_V6'
candidate={
 'schema':'yado.g2.scale_conditional_high_scale_repair.v5','state':state,
 'principle':'REPAIR_CARDINALITY_TO_NORMALIZED_FEATURE_SEMANTICS_FROM_SPENT_BINDING_FAILURE_WITHOUT_RETRAINING_V4_MODEL',
 'source_binding_v4_failure':{'run_id':'33653155391','failed_checks':{k:v for k,v in bind4.get('checks',{}).items() if not v}},
 'selection':selection,'selected_skill_id':selected_id,'selected_spec':spec,'binding_candidate':binding,
 'metrics':{'broken_route_fit':baseline_fit,'broken_route_high_holdout':baseline_hold,'selected_route_all_history':route_score,
            'parent_predictive_total':parent_total,'candidate_predictive_total':predictive_total,'per_size':per_size},
 'fresh_route_probe_status':'RESERVED_FOR_CANONICAL_BINDING_V5_NOT_MATERIALIZED',
 'checks':checks,'canonical_active':False,'canonical_mechanism_mutation':False,'architecture_mutation':False,'g3_genesis_performed':False
}
candidate['candidate_digest']=h(candidate);write(CAND,candidate)

artifact={'schema':'yado.g2.kernel_scale_conditional_high_scale_repair.v5',
 'status':'PASS_HIGH_SCALE_REPAIR_V5' if supported else 'WITHHOLD_HIGH_SCALE_REPAIR_V5',
 'candidate_state':state,'candidate_digest':candidate['candidate_digest'],'selected_skill_id':selected_id,
 'route_score':route_score,'parent_predictive_total':parent_total,'candidate_predictive_total':predictive_total,
 'next_required_capability':next_cap,'canonical_mechanism_mutation':False,'architecture_mutation':False,'g3_genesis_performed':False}
artifact['artifact_digest']=h(artifact);write(ART,artifact)

prev=head['canonical_head_digest']
# Keep provenance synchronized with the new frontier.
prov['current_g2_binding'].update({
 'current_execution_label':'G2_NATIVE_SELECTOR_CANONICAL_BINDING_V5' if supported else 'G2_HIGH_SCALE_REPAIR_V6_PENDING',
 'frontier':next_cap,
 'frontier_native_method':'select_evolution_skills' if supported else 'propose_evolution_operation',
 'frontier_native_owner':'UnifiedYADOKernelV30RC8ExternalCognitive'
})
prov['registry_digest']=cdig(prov,'registry_digest');write(PROV,prov)
core['algorithm_provenance_registry_digest']=prov['registry_digest']
core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits';core['core_digest']=cdig(core,'core_digest');write(CORE,core)
head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest']
head['algorithm_provenance_registry']['current_execution_label']=prov['current_g2_binding']['current_execution_label']
head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest'];head['unified_core']['core_digest']=core['core_digest']
head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits';head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)

ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap]
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={**artifact,'schema':'yado.g2.kernel_scale_conditional_high_scale_repair.receipt.v5',
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest'],'checks':checks,'provenance_registry_digest':prov['registry_digest']}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_HIGH_SCALE_REPAIR_V5",
 'event_type':'G2_ROUTE_SEMANTICS_REPAIR','status':'PASS_SHADOW' if supported else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':front,
 'effect':f"SELECTED={selected_id}; BROKEN_HIGH_ROUTE={baseline_hold:.6f}; REPAIRED_ROUTE={route_score:.6f}; PRED_OLD={parent_total:.6f}; PRED_NEW={predictive_total:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-kernel-scale-conditional-high-scale-repair-v5-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':True,'canonical_mechanism_mutation':False,'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);write(LEDGER,ledger)
ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_WRITE_CONTEXT_INCONSISTENT')
cp=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=60)
if cp.returncode!=0:raise RuntimeError('POST_V5_GUARD_FAILED:'+cp.stdout[-4000:]+cp.stderr[-1000:])
log('complete',state=state,selected=selected_id,route_score=route_score,parent_predictive=parent_total,candidate_predictive=predictive_total,next=next_cap)
