from __future__ import annotations
from pathlib import Path
from itertools import combinations
import copy,hashlib,json,os,subprocess,sys

ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
import yado_architecture_neutral_meta_synthesizer_v2 as neutral
from yado_cognitive_growth_runtime_v1 import knn_predict
from yado_g2_canonical_high_scale_binding_runtime_v4 import CanonicalHighScaleBindingRuntimeV4
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
CORPUS=REPO/'resources/yado-architecture-neutral-evidence-corpus-frozen-v1.json'
HIGH2=REPO/'candidates/kernel-self-generated/high-scale-repair-v2.json'
V4=REPO/'candidates/kernel-self-generated/high-scale-repair-v4.json'
ADAPTER=REPO/'runtime/yado_g2_canonical_high_scale_binding_runtime_v4.py'
BINDING=REPO/'canonical/yado-native-selector-canonical-binding-v4.json'
CAND=REPO/'candidates/kernel-self-generated/native-selector-canonical-binding-v4.json'
FRESH12=REPO/'resources/yado-twelve-source-transfer-history-v1.json'
ART=REPO/'architecture/yado-kernel-native-selector-canonical-binding-v4.json'
OUT=ROOT/'yado_kernel_native_selector_canonical_binding_v4_receipt.json'
GUARD=ROOT/'yado_canonical_invariant_guard_v1.py'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):
    x=copy.deepcopy(o);x.pop(field,None);return h(x)
def log(stage,**kw):print(json.dumps({'stage':stage,**kw},sort_keys=True,default=str),flush=True)

head,core,ledger,prov,corpus,high2,v4=map(load,[HEAD,CORE,LEDGER,PROV,CORPUS,HIGH2,V4])
validate_ledger_v2(ledger)
front='KERNEL_NATIVE_SELECTOR_CANONICAL_BINDING_V4'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if head.get('current_frontier')!=front or core.get('current_frontier')!=front:raise RuntimeError('HEAD_CORE_FRONTIER_MISMATCH')
if v4.get('state')!='SHADOW_SUPPORTED':raise RuntimeError('V4_NOT_SHADOW_SUPPORTED')
if v4.get('selected_skill_id')!='HIGH_ONLY_TRIPLE_KNN_V4':raise RuntimeError('V4_SELECTION_DRIFT')
if high2.get('state')!='SHADOW_SUPPORTED':raise RuntimeError('HIGH2_PARENT_NOT_SUPPORTED')
if head.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')

data=neutral.build_dataset(force=True)
expected={x['id']:x['sha256'] for x in corpus['source_digests']}
actual={sid:r['sha256'] for sid,r in data['rows'].items()}
if expected!=actual:raise RuntimeError('SOURCE_DIGEST_DRIFT')
ids=sorted(data['rows']);pairs=list(combinations(ids,2))

def make_cases(size):
    out=[]
    for combo in combinations(ids,size):
        x,y,_=neutral._vector(combo,data['rows'])
        out.append({'key':'|'.join(combo),'x':x,'y':y,'size':size})
    return out

def rep_pair(c):
    z=dict(c['x']);present=set(c['key'].split('|'))
    for sid in ids:z['src::'+sid]=1.0 if sid in present else 0.0
    for a,b in pairs:z['srcpair::'+a+'&&'+b]=1.0 if a in present and b in present else 0.0
    return z
parent_model=high2['selected_model']
def old_pred(c):return knn_predict(parent_model,rep_pair(c))
def acc(rows,pred):return sum(pred(c)==c['y'] for c in rows)/max(1,len(rows))

binding={
 'schema':'yado.g2.native_selector_canonical_binding.v4',
 'status':'CANDIDATE_PENDING_FRESH12_ADMISSION',
 'generation':head['generation_id'],
 'activation':{
   'source':'candidates/kernel-self-generated/high-scale-repair-v4.json:selected_spec.activation_min_size',
   'activation_min_size':int(v4['selected_spec']['activation_min_size']),
   'host_new_threshold_written':False,
 },
 'branch_artifacts':{
   'parent_v2':'candidates/kernel-self-generated/high-scale-repair-v2.json',
   'high_scale_v4':'candidates/kernel-self-generated/high-scale-repair-v4.json',
   'corpus':'resources/yado-architecture-neutral-evidence-corpus-frozen-v1.json',
 },
 'binding_runtime':'runtime/yado_g2_canonical_high_scale_binding_runtime_v4.py',
 'artifact_sha256':{
   'candidates/kernel-self-generated/high-scale-repair-v2.json':sha(HIGH2),
   'candidates/kernel-self-generated/high-scale-repair-v4.json':sha(V4),
   'resources/yado-architecture-neutral-evidence-corpus-frozen-v1.json':sha(CORPUS),
   'runtime/yado_g2_canonical_high_scale_binding_runtime_v4.py':sha(ADAPTER),
 },
 'semantic_boundary':{
   'binding_adapter_only':True,
   'new_learning_during_binding':False,
   'new_selection_during_binding':False,
   'v4_candidate_selected_by_g2_event':'E0211_G2_HIGH_SCALE_REPAIR_V4',
   'activation_boundary_read_from_selected_candidate':True,
 },
}
binding['binding_digest']=h(binding)

# Candidate is now fixed. Evaluate all spent history sizes 1..11.
spaces={s:make_cases(s) for s in range(1,12)}
expected_counts=[12,66,220,495,792,924,792,495,220,66,12]
if [len(spaces[s]) for s in range(1,12)]!=expected_counts:raise RuntimeError('HISTORY_SPACE_COUNTS_INVALID')
history_old={};history_new={};route_scores={}
with CanonicalHighScaleBindingRuntimeV4(binding=binding,repo_root=REPO) as rt:
    for s in range(1,12):
        history_old[str(s)]=acc(spaces[s],old_pred)
        history_new[str(s)]=acc(spaces[s],rt.predict)
        expected_route='V4_HIGH' if s>=rt.activation_min_size else 'V2_PARENT'
        route_scores[str(s)]=sum(rt.route(c)==expected_route for c in spaces[s])/len(spaces[s])
    history_old_total=sum(old_pred(c)==c['y'] for s in range(1,12) for c in spaces[s])/sum(len(spaces[s]) for s in range(1,12))
    history_new_total=sum(rt.predict(c)==c['y'] for s in range(1,12) for c in spaces[s])/sum(len(spaces[s]) for s in range(1,12))
log('history_complete',history_old=history_old_total,history_new=history_new_total,size11_recheck=history_new['11'])

# The only never-used combination left in this 12-source universe is size12.
fresh12=make_cases(12)
if len(fresh12)!=1:raise RuntimeError('FRESH12_COUNT_INVALID')
with CanonicalHighScaleBindingRuntimeV4(binding=binding,repo_root=REPO) as rt:
    fresh12_old=acc(fresh12,old_pred)
    fresh12_new=acc(fresh12,rt.predict)
    fresh12_route=1.0 if rt.route(fresh12[0])=='V4_HIGH' else 0.0
log('fresh12_opened',count=1,old=fresh12_old,new=fresh12_new,route=fresh12_route)

no_regression_each=all(history_new[str(s)]+1e-12>=history_old[str(s)] for s in range(1,12))
checks={
 'source_sha_exact_match':expected==actual,
 'binding_artifact_digests_exact':all((REPO/p).exists() and sha(REPO/p)==d for p,d in binding['artifact_sha256'].items()),
 'activation_boundary_from_frozen_v4_candidate':binding['activation']['activation_min_size']==10,
 'history_sizes_1_to_11_only_before_fresh12':True,
 'history_no_regression_each_size_1_to_11':no_regression_each,
 'history_total_no_regression':history_new_total+1e-12>=history_old_total,
 'size11_shadow_result_reproduced':abs(history_new['11']-1.0)<1e-12,
 'routes_exact_sizes_1_to_11':all(abs(v-1.0)<1e-12 for v in route_scores.values()),
 'fresh12_count_1':len(fresh12)==1,
 'fresh12_not_used_for_training_selection_or_refit':True,
 'fresh12_route_high':abs(fresh12_route-1.0)<1e-12,
 'fresh12_above_gate':fresh12_new>=.90,
 'fresh12_not_worse_than_parent':fresh12_new+1e-12>=fresh12_old,
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
supported=all(checks.values())
state='CANONICAL_ADMITTED' if supported else 'WITHHOLD'
next_cap='KERNEL_NEUTRAL_ARCHITECTURE_SELECTION_WITH_SELF_GENERATED_SELECTOR_V1' if supported else 'KERNEL_SCALE_CONDITIONAL_SUCCESSOR_HIGH_SCALE_REPAIR_V5'

candidate={
 'schema':'yado.g2.native_selector_canonical_binding_candidate.v4','state':state,
 'binding_digest':binding['binding_digest'],'v4_candidate_digest':v4['candidate_digest'],
 'selected_skill_id':v4['selected_skill_id'],'activation_min_size':binding['activation']['activation_min_size'],
 'history_old_scores':history_old,'history_new_scores':history_new,'route_scores':route_scores,
 'history_old_total':history_old_total,'history_new_total':history_new_total,
 'fresh12_old':fresh12_old,'fresh12_new':fresh12_new,'fresh12_route':fresh12_route,
 'fresh12_statistical_scope':'EXACT_SINGLE_COMPLETE_12_SOURCE_COMBINATION; LOW_N; USED_ONLY_AS_FINAL_INDEPENDENT_BINDING_GATE',
 'checks':checks,'canonical_mechanism_mutation':supported,'architecture_mutation':False,'g3_genesis_performed':False,
}
candidate['candidate_digest']=h(candidate);write(CAND,candidate)
write(FRESH12,{
 'schema':'yado.g2.twelve_source_transfer_history.v1','status':'SPENT_AFTER_SINGLE_BINDING_ADMISSION',
 'case_count':1,'old_parent_score':fresh12_old,'candidate_score':fresh12_new,'route_score':fresh12_route,
 'dataset_digest':h(fresh12),'binding_candidate_digest':candidate['candidate_digest'],
 'statistical_scope':'COMPLETE_COMBINATION_AT_SIZE12_BUT_N_EQUALS_1'
})

previous_head_digest=head['canonical_head_digest']

if supported:
    binding['status']='CANONICAL_ACTIVE'
    binding['admission']={
      'history_old_total':history_old_total,'history_new_total':history_new_total,
      'fresh12_old':fresh12_old,'fresh12_new':fresh12_new,'checks':checks,
      'statistical_scope':'FRESH12_N1_PLUS_EXHAUSTIVE_SPENT_HISTORY_SIZES1_TO11'
    }
    binding['binding_digest']=cdig(binding,'binding_digest');write(BINDING,binding)

    mech_ids={m.get('mechanism_id') for m in prov.get('mechanisms',[])}
    additions=[
      {
       'mechanism_id':'G2_HIGH_SCALE_TRIPLE_KNN_V4','method':'knn_predict',
       'owner_class':'G2_KERNEL_SELECTED_SHADOW_MODEL','owner_module':'yado_cognitive_growth_runtime_v1',
       'role':'CANONICAL_HIGH_SCALE_BRANCH_MODEL',
       'semantic':'KERNEL_SELECTED_TRIPLE_INTERACTION_KNN_ACTIVE_FOR_SOURCE_COUNT_GE_10',
       'signature':'knn_predict(model,x)',
       'source_path':'candidates/kernel-self-generated/high-scale-repair-v4.json','source_sha256':sha(V4),
       'candidate_digest':v4['candidate_digest'],'selected_skill_id':v4['selected_skill_id'],
      },
      {
       'mechanism_id':'G2_HIGH_SCALE_BINDING_ADAPTER_V4','method':'predict',
       'owner_class':'CanonicalHighScaleBindingRuntimeV4','owner_module':'yado_g2_canonical_high_scale_binding_runtime_v4',
       'role':'CANONICAL_BINDING_ADAPTER',
       'semantic':'EXECUTES_FROZEN_V2_PARENT_BELOW_SELECTED_V4_BOUNDARY_AND_FROZEN_V4_TRIPLE_MODEL_AT_OR_ABOVE_BOUNDARY',
       'signature':'predict(self, case: dict)',
       'source_path':'runtime/yado_g2_canonical_high_scale_binding_runtime_v4.py','source_sha256':sha(ADAPTER),
       'host_binding_adapter_only':True,
      }
    ]
    for item in additions:
        if item['mechanism_id'] not in mech_ids:
            prov['mechanisms'].append(item);mech_ids.add(item['mechanism_id'])

    adapter_rel='runtime/yado_g2_canonical_high_scale_binding_runtime_v4.py'
    if adapter_rel not in core['active_runtime_sources']:core['active_runtime_sources'].append(adapter_rel)
    core['active_runtime_sources']=sorted(dict.fromkeys(core['active_runtime_sources']))
    source_hashes={}
    for rel in core['active_runtime_sources']:
        p=REPO/rel
        if not p.exists():raise RuntimeError('ACTIVE_RUNTIME_SOURCE_MISSING:'+rel)
        source_hashes[rel]=sha(p)
    rim={'algorithm':'SHA256','sources':source_hashes};rim['manifest_digest']=h(source_hashes)
    core['runtime_integrity_manifest']=rim

    core['native_selector_canonical_binding_v4']={
      'status':'CANONICAL_ACTIVE','binding_manifest':'canonical/yado-native-selector-canonical-binding-v4.json',
      'binding_digest':binding['binding_digest'],'runtime':adapter_rel,'runtime_sha256':sha(ADAPTER),
      'selected_skill_id':v4['selected_skill_id'],'candidate_digest':v4['candidate_digest'],
      'activation_min_size':10,'fresh12_score':fresh12_new,
      'fresh12_statistical_scope':'N1_COMPLETE_SIZE12_COMBINATION'
    }
    for plane in core.get('planes',[]):
        if plane.get('plane_id')=='INTELLIGENCE_AND_META_SELECTION':
            for comp in ('G2_HIGH_SCALE_TRIPLE_KNN_V4','G2_HIGH_SCALE_BINDING_ADAPTER_V4'):
                if comp not in plane['active_components']:plane['active_components'].append(comp)
            plane['active_components']=sorted(plane['active_components'])
    for inv in ('CANONICAL_HIGH_SCALE_V4_BINDING_MUST_MATCH_FROZEN_SELECTED_CANDIDATE','V4_ACTIVATION_BOUNDARY_MUST_COME_FROM_SELECTED_CANDIDATE_METADATA'):
        if inv not in core['invariants']:core['invariants'].append(inv)
else:
    rim=core.get('runtime_integrity_manifest',{})

# Provenance always follows the new frontier; canonical mechanism fields are added only on PASS.
prov['current_g2_binding'].update({
 'current_execution_label':'G2_NATIVE_HIGH_SCALE_SELECTOR_CANONICAL_V4' if supported else 'G2_HIGH_SCALE_REPAIR_V5_PENDING',
 'frontier':next_cap,
 'frontier_native_method':'select_evolution_skills' if supported else 'propose_evolution_operation',
 'frontier_native_owner':'UnifiedYADOKernelV30RC8ExternalCognitive',
})
if supported:
    prov['current_g2_binding'].update({
      'canonical_binding_runtime':'runtime/yado_g2_canonical_high_scale_binding_runtime_v4.py',
      'canonical_high_scale_candidate_digest':v4['candidate_digest'],
      'canonical_high_scale_selected_skill_id':v4['selected_skill_id'],
      'canonical_activation_min_size':10,
    })
prov['registry_digest']=cdig(prov,'registry_digest');write(PROV,prov)

core['algorithm_provenance_registry_digest']=prov['registry_digest']
core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits'
core['canonical_mechanism_mutation']=supported
core['core_digest']=cdig(core,'core_digest');write(CORE,core)

# Keep explicit active capability semantics aligned with the core planes.
active_caps=sorted({
 str(x) for plane in core.get('planes',[]) for x in plane.get('active_components',[])
 if isinstance(x,str) and '/' not in x and not x.endswith('.json')
})
head['active_capabilities']=active_caps
head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest']
head['algorithm_provenance_registry']['current_execution_label']=prov['current_g2_binding']['current_execution_label']
head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest']
head['unified_core']['core_digest']=core['core_digest']
if supported:
    head['native_selector_canonical_binding_v4']={
      'status':'CANONICAL_ACTIVE','binding_digest':binding['binding_digest'],
      'runtime':'runtime/yado_g2_canonical_high_scale_binding_runtime_v4.py',
      'selected_skill_id':v4['selected_skill_id'],'activation_min_size':10,'fresh12_score':fresh12_new
    }
    head['unified_core']['runtime_integrity_manifest_digest']=rim['manifest_digest']
head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits'
head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)

artifact={
 'schema':'yado.g2.kernel_native_selector_canonical_binding.v4',
 'status':'PASS_NATIVE_SELECTOR_CANONICAL_BINDING_V4' if supported else 'WITHHOLD_NATIVE_SELECTOR_CANONICAL_BINDING_V4',
 'candidate_state':state,'candidate_digest':candidate['candidate_digest'],
 'binding_digest':binding['binding_digest'],'selected_skill_id':v4['selected_skill_id'],
 'history_old_total':history_old_total,'history_new_total':history_new_total,
 'fresh12_old':fresh12_old,'fresh12_new':fresh12_new,'fresh12_statistical_scope':candidate['fresh12_statistical_scope'],
 'next_required_capability':next_cap,'canonical_mechanism_mutation':supported,
 'architecture_mutation':False,'g3_genesis_performed':False,
}
artifact['artifact_digest']=h(artifact);write(ART,artifact)

ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap]
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={**artifact,'schema':'yado.g2.kernel_native_selector_canonical_binding.receipt.v4',
 'previous_head_digest':previous_head_digest,'new_head_digest':head['canonical_head_digest'],
 'checks':checks,'provenance_registry_digest':prov['registry_digest']}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_NATIVE_SELECTOR_CANONICAL_BINDING_V4",
 'event_type':'G2_NATIVE_SELECTOR_CANONICAL_ADMISSION_V4' if supported else 'G2_NATIVE_SELECTOR_CANONICAL_BINDING_V4_WITHHOLD',
 'status':'PASS_CANONICAL' if supported else 'WITHHOLD','generation':ledger['current_head'],'deficit':front,
 'effect':f"HISTORY_OLD={history_old_total:.6f}; HISTORY_NEW={history_new_total:.6f}; FRESH12_OLD={fresh12_old:.6f}; FRESH12_NEW={fresh12_new:.6f}; N_FRESH12=1; CANONICAL={supported}; NEXT={next_cap}",
 'source_path':f'receipts/yado-kernel-native-selector-canonical-binding-v4-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':True,'canonical_mechanism_mutation':supported,
 'promotion_applied':False,'generation_transition':False,'previous_head_digest':previous_head_digest,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);write(LEDGER,ledger)

ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_WRITE_CONTEXT_INCONSISTENT')
cp=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=60)
if cp.returncode!=0:raise RuntimeError('POST_BINDING_GUARD_FAILED:'+cp.stdout[-4000:]+cp.stderr[-1000:])
log('complete',state=state,history_old=history_old_total,history_new=history_new_total,fresh12_old=fresh12_old,fresh12_new=fresh12_new,next=next_cap)
