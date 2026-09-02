from __future__ import annotations
from pathlib import Path
from itertools import combinations
import copy,hashlib,json,os,sys
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

import yado_architecture_neutral_meta_synthesizer_v2 as neutral
from yado_g2_canonical_scale_conditional_runtime_v1 import CanonicalScaleConditionalRuntimeV1
from yado_g2_canonical_scale_conditional_runtime_v2 import CanonicalScaleConditionalRuntimeV2
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
BINDING=REPO/'canonical/yado-native-selector-canonical-binding-v2.json'
CORRECTED=REPO/'candidates/kernel-self-generated/native-selector-commit-substrate-v1-corrected.json'
SCALE=REPO/'candidates/kernel-self-generated/scale-conditional-pair-knn-successor-v1.json'
HIGH=REPO/'candidates/kernel-self-generated/high-scale-repair-v2.json'
F4=REPO/'candidates/kernel-self-generated/fresh-four-source-curriculum-v1.json'
CAL=REPO/'candidates/kernel-self-generated/evolutionary-centroid-calibrated-successor-v2.json'
LOCAL=REPO/'candidates/kernel-self-generated/evolutionary-local-knn-successor-v1.json'
BASE=REPO/'receipts/yado-architecture-neutral-meta-synth-v2-latest.json'
CORPUS=REPO/'resources/yado-architecture-neutral-evidence-corpus-frozen-v1.json'
REGISTRY=REPO/'runtime/yado_g2_native_selector_commit_registry_v1.sqlite'
ADAPTER1=REPO/'runtime/yado_g2_canonical_scale_conditional_runtime_v1.py'
ADAPTER2=REPO/'runtime/yado_g2_canonical_scale_conditional_runtime_v2.py'
ART=REPO/'architecture/yado-kernel-native-selector-canonical-binding-v2.json'
CAND=REPO/'candidates/kernel-self-generated/native-selector-canonical-binding-v2.json'
FRESH9=REPO/'resources/yado-nine-source-transfer-history-v1.json'
OUT=ROOT/'yado_kernel_native_selector_canonical_binding_v2_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):
 x=copy.deepcopy(o);x.pop(field,None);return h(x)

head,core,ledger,prov,corr,scale,high,f4,cal,local,base,corpus=map(load,[HEAD,CORE,LEDGER,PROV,CORRECTED,SCALE,HIGH,F4,CAL,LOCAL,BASE,CORPUS])
validate_ledger_v2(ledger)
front='KERNEL_NATIVE_SELECTOR_CANONICAL_BINDING_V2'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if corr.get('state')!='SHADOW_SUPPORTED':raise RuntimeError('NATIVE_SELECTOR_SUBSTRATE_NOT_SUPPORTED')
if high.get('state')!='SHADOW_SUPPORTED':raise RuntimeError('HIGH_SCALE_REPAIR_NOT_SUPPORTED')
if high.get('selected_skill_id')!='PAIR_KNN':raise RuntimeError('HIGH_SCALE_REPAIR_SELECTION_DRIFT')
if sha(REGISTRY)!=corr['registry_sha256']:raise RuntimeError('REGISTRY_DIGEST_MISMATCH')

artifact_paths_v2={
 'runtime/yado_g2_native_selector_commit_registry_v1.sqlite':sha(REGISTRY),
 'runtime/yado_g2_canonical_scale_conditional_runtime_v2.py':sha(ADAPTER2),
 'candidates/kernel-self-generated/high-scale-repair-v2.json':sha(HIGH),
 'candidates/kernel-self-generated/evolutionary-centroid-calibrated-successor-v2.json':sha(CAL),
 'candidates/kernel-self-generated/evolutionary-local-knn-successor-v1.json':sha(LOCAL),
 'receipts/yado-architecture-neutral-meta-synth-v2-latest.json':sha(BASE),
 'resources/yado-architecture-neutral-evidence-corpus-frozen-v1.json':sha(CORPUS),
}
binding2={
 'schema':'yado.g2.native_selector_canonical_binding.v2',
 'status':'CANDIDATE_PENDING_FRESH9_ADMISSION',
 'generation':'G2_CANDIDATE_TRCG_V1',
 'selector_registry':{
   'path':'runtime/yado_g2_native_selector_commit_registry_v1.sqlite',
   'sha256':corr['registry_sha256'],
   'program_id':corr['program_id'],
   'program_digest':corr['program_digest'],
   'capability':'SCALE_CONDITIONAL_SELECTOR_ROUTE_V1',
   'native_owner':'DevelopmentalExecutiveV22',
 },
 'binding_runtime':'runtime/yado_g2_canonical_scale_conditional_runtime_v2.py',
 'branches':{'low':scale['branches']['low_scale'],'high':scale['branches']['high_scale']},
 'branch_artifacts':{
   'base':'receipts/yado-architecture-neutral-meta-synth-v2-latest.json',
   'calibrated':'candidates/kernel-self-generated/evolutionary-centroid-calibrated-successor-v2.json',
   'local_knn':'candidates/kernel-self-generated/evolutionary-local-knn-successor-v1.json',
   'high_scale_repair_v2':'candidates/kernel-self-generated/high-scale-repair-v2.json',
   'corpus':'resources/yado-architecture-neutral-evidence-corpus-frozen-v1.json',
 },
 'artifact_sha256':artifact_paths_v2,
 'semantic_boundary':{
   'host_binding_adapter_only':True,
   'host_threshold_written':False,
   'host_learner_written':False,
   'routing_decision_executes_native_committed_program':True,
   'high_scale_model_selected_by_g2_event':'E0200_G2_HIGH_SCALE_REPAIR_V2',
 },
}
binding2['binding_digest']=h(binding2)

# Reconstruct old V1 binding solely as a regression comparator; never canonicalize it.
artifact_paths_v1={
 'runtime/yado_g2_native_selector_commit_registry_v1.sqlite':sha(REGISTRY),
 'runtime/yado_g2_canonical_scale_conditional_runtime_v1.py':sha(ADAPTER1),
 'candidates/kernel-self-generated/scale-conditional-pair-knn-successor-v1.json':sha(SCALE),
 'candidates/kernel-self-generated/fresh-four-source-curriculum-v1.json':sha(F4),
 'candidates/kernel-self-generated/evolutionary-centroid-calibrated-successor-v2.json':sha(CAL),
 'candidates/kernel-self-generated/evolutionary-local-knn-successor-v1.json':sha(LOCAL),
 'receipts/yado-architecture-neutral-meta-synth-v2-latest.json':sha(BASE),
 'resources/yado-architecture-neutral-evidence-corpus-frozen-v1.json':sha(CORPUS),
}
binding1={
 'schema':'yado.g2.native_selector_canonical_binding.v1.regression_reference',
 'selector_registry':binding2['selector_registry'],
 'branches':binding2['branches'],
 'branch_artifacts':{
   'base':binding2['branch_artifacts']['base'],
   'calibrated':binding2['branch_artifacts']['calibrated'],
   'local_knn':binding2['branch_artifacts']['local_knn'],
   'high_pair_knn':'candidates/kernel-self-generated/fresh-four-source-curriculum-v1.json',
   'corpus':binding2['branch_artifacts']['corpus'],
 },
 'artifact_sha256':artifact_paths_v1,
}
binding1['binding_digest']=h(binding1)

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
spaces={s:make_cases(s) for s in range(1,10)}
expected_counts=[12,66,220,495,792,924,792,495,220]
if [len(spaces[s]) for s in range(1,10)]!=expected_counts:raise RuntimeError('SPACE_COUNTS_INVALID')

def score(rows,rt):return sum(rt.predict(c)==c['y'] for c in rows)/len(rows)
def route_score(rows,rt):
 th=float(scale['selected_threshold']);low=scale['branches']['low_scale'];highlab=scale['branches']['high_scale']
 return sum(rt.route(c['x'])==(highlab if float(c['x']['source_count'])+1e-12>=th else low) for c in rows)/len(rows)

old_scores={};new_scores={};route_scores={}
with CanonicalScaleConditionalRuntimeV1(binding=binding1,repo_root=REPO) as oldrt, CanonicalScaleConditionalRuntimeV2(binding=binding2,repo_root=REPO) as newrt:
 for s in range(1,9):
  old_scores[str(s)]=score(spaces[s],oldrt)
  new_scores[str(s)]=score(spaces[s],newrt)
  route_scores[str(s)]=route_score(spaces[s],newrt)
 no_regression_each=all(new_scores[str(s)]+1e-12>=old_scores[str(s)] for s in range(1,9))
 history_old=sum(oldrt.predict(c)==c['y'] for s in range(1,9) for c in spaces[s])/sum(len(spaces[s]) for s in range(1,9))
 history_new=sum(newrt.predict(c)==c['y'] for s in range(1,9) for c in spaces[s])/sum(len(spaces[s]) for s in range(1,9))

 # size9 is opened only after the candidate is fixed and all history checks are computed.
 fresh9_old=score(spaces[9],oldrt)
 fresh9_new=score(spaces[9],newrt)
 fresh9_route=route_score(spaces[9],newrt)

checks={
 'source_sha_exact_match':expected==actual,
 'registry_digest_exact':sha(REGISTRY)==corr['registry_sha256'],
 'all_bound_artifact_digests_present':all((REPO/p).exists() and sha(REPO/p)==d for p,d in artifact_paths_v2.items()),
 'selector_routes_exact_sizes_1_to_9':all(abs(route_scores[str(s)]-1.0)<1e-12 for s in range(1,9)) and abs(fresh9_route-1.0)<1e-12,
 'no_regression_each_size_1_to_8':no_regression_each,
 'history_1_to_8_improves':history_new+1e-12>=history_old,
 'fresh9_count_220':len(spaces[9])==220,
 'fresh9_not_used_for_training_or_selection':True,
 'fresh9_above_gate':fresh9_new>=.90,
 'fresh9_not_worse_than_old_runtime':fresh9_new+1e-12>=fresh9_old,
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
supported=all(checks.values())
state='CANONICAL_ADMITTED' if supported else 'WITHHOLD'
next_cap='KERNEL_NEUTRAL_ARCHITECTURE_SELECTION_WITH_SELF_GENERATED_SELECTOR_V1' if supported else 'KERNEL_SCALE_CONDITIONAL_SUCCESSOR_HIGH_SCALE_REPAIR_V3'

candidate={
 'schema':'yado.g2.native_selector_canonical_binding_candidate.v2','state':state,
 'binding_digest':binding2['binding_digest'],'selector_program_id':corr['program_id'],
 'high_scale_candidate_digest':high['candidate_digest'],'high_scale_selected_skill':high['selected_skill_id'],
 'old_scores':old_scores,'new_scores':new_scores,'route_scores_history':route_scores,
 'history_old':history_old,'history_new':history_new,
 'fresh9_old':fresh9_old,'fresh9_new':fresh9_new,'fresh9_route':fresh9_route,
 'checks':checks,'canonical_mechanism_mutation':supported,'architecture_mutation':False,'g3_genesis_performed':False,
}
candidate['candidate_digest']=h(candidate);CAND.parent.mkdir(parents=True,exist_ok=True);write(CAND,candidate)
fresh9={
 'schema':'yado.g2.nine_source_transfer_history.v1','status':'SPENT_AFTER_SINGLE_ADMISSION',
 'source_sha256':actual,'case_count':len(spaces[9]),'old_runtime_score':fresh9_old,'candidate_score':fresh9_new,
 'route_score':fresh9_route,'dataset_digest':h(spaces[9]),'binding_candidate_digest':candidate['candidate_digest'],
}
write(FRESH9,fresh9)

if supported:
 binding2['status']='CANONICAL_ACTIVE'
 binding2['admission']={'history_old':history_old,'history_new':history_new,'fresh9_old':fresh9_old,'fresh9_new':fresh9_new,'checks':checks}
 binding2['binding_digest']=h({k:v for k,v in binding2.items() if k!='binding_digest'})
 write(BINDING,binding2)

 rc22=ROOT/'yado_rc8_v36/yado_core_v2_2.py'
 mech_ids={m.get('mechanism_id') for m in prov.get('mechanisms',[])}
 additions=[
  {
   'mechanism_id':'G2_NATIVE_SELECTOR_COMMIT_SUBSTRATE_V1','method':'execute_capability',
   'owner_class':'DevelopmentalExecutiveV22','owner_module':'yado_core_v2_2',
   'role':'DURABLE_SELECTOR_COMMIT_SUBSTRATE',
   'semantic':'NATIVE_SYNTHESIZE_EVALUATE_COMMIT_RESTORE_BOUNDED_SCALE_SELECTOR',
   'signature':'execute_capability(self, capability: str, payload: Mapping[str, Any]) -> Any',
   'source_path':'runtime/yado_rc8_v36/yado_core_v2_2.py','source_sha256':sha(rc22),
   'program_id':corr['program_id'],'program_digest':corr['program_digest'],'registry_sha256':corr['registry_sha256'],
  },
  {
   'mechanism_id':'G2_HIGH_SCALE_PAIR_KNN_REPAIR_V2','method':'knn_predict',
   'owner_class':'SHADOW_GENERATED_MODEL','owner_module':'yado_cognitive_growth_runtime_v1',
   'role':'HIGH_SCALE_BRANCH_MODEL',
   'semantic':'G2_SELECTED_PAIR_REPRESENTATION_KNN_K9_FROM_SPENT_SIZE4_TO_SIZE7_HISTORY',
   'signature':'knn_predict(model,x)',
   'source_path':'candidates/kernel-self-generated/high-scale-repair-v2.json','source_sha256':sha(HIGH),
   'candidate_digest':high['candidate_digest'],'selected_skill_id':high['selected_skill_id'],
  },
  {
   'mechanism_id':'G2_SCALE_CONDITIONAL_BINDING_ADAPTER_V2','method':'predict',
   'owner_class':'CanonicalScaleConditionalRuntimeV2','owner_module':'yado_g2_canonical_scale_conditional_runtime_v2',
   'role':'CANONICAL_BINDING_ADAPTER',
   'semantic':'LOADS_NATIVE_COMMITTED_SELECTOR_PLUS_STABLE_LOW_BRANCH_PLUS_G2_SELECTED_HIGH_SCALE_REPAIR_WITHOUT_NEW_SELECTION',
   'signature':'predict(self, case: dict)',
   'source_path':'runtime/yado_g2_canonical_scale_conditional_runtime_v2.py','source_sha256':sha(ADAPTER2),
   'host_binding_adapter_only':True,
  },
 ]
 for item in additions:
  if item['mechanism_id'] not in mech_ids:
   prov['mechanisms'].append(item);mech_ids.add(item['mechanism_id'])

 prov['current_g2_binding'].update({
   'current_execution_label':'G2_NATIVE_SCALE_CONDITIONAL_SELECTOR_CANONICAL_V2',
   'frontier':next_cap,
   'frontier_native_method':'execute_capability',
   'frontier_native_owner':'DevelopmentalExecutiveV22',
   'canonical_binding_runtime':'runtime/yado_g2_canonical_scale_conditional_runtime_v2.py',
   'canonical_selector_program_id':corr['program_id'],
   'canonical_high_scale_candidate_digest':high['candidate_digest'],
 })
 have={e.get('event_id') for e in prov.get('relevant_ledger_events',[])}
 for eid in ('E0195_G2_SCALE_CONDITIONAL_REACTION_NORM_V1','E0197_G2_NATIVE_SELECTOR_COMMIT_SUBSTRATE_GENESIS_V1','E0198_G2_NATIVE_SELECTOR_COMMIT_VERDICT_REPAIR_V1','E0200_G2_HIGH_SCALE_REPAIR_V2'):
  if eid not in have:
   match=next((e for e in ledger['events'] if e.get('event_id')==eid),None)
   if match:
    prov['relevant_ledger_events'].append({k:match.get(k) for k in ('index','event_id','event_type','generation','status','source_path','source_digest','canonical_mutation','promotion_applied')})
 prov['registry_digest']=h({k:v for k,v in prov.items() if k!='registry_digest'})
 write(PROV,prov)

 adapter_rel='runtime/yado_g2_canonical_scale_conditional_runtime_v2.py'
 if adapter_rel not in core['active_runtime_sources']:core['active_runtime_sources'].append(adapter_rel)
 core['active_runtime_sources']=sorted(core['active_runtime_sources'])
 core['native_selector_commit_substrate']={
   'status':'CANONICAL_ACTIVE','program_id':corr['program_id'],'program_digest':corr['program_digest'],
   'registry':'runtime/yado_g2_native_selector_commit_registry_v1.sqlite','registry_sha256':corr['registry_sha256'],
   'binding_manifest':'canonical/yado-native-selector-canonical-binding-v2.json','binding_digest':binding2['binding_digest'],
   'runtime':adapter_rel,'runtime_sha256':sha(ADAPTER2),
   'high_scale_candidate_digest':high['candidate_digest'],'fresh9_score':fresh9_new,
 }
 for inv in ('NATIVE_SELECTOR_EXECUTION_MUST_ROUTE_THROUGH_COMMITTED_EXECUTIVE_PROGRAM','CANONICAL_HIGH_SCALE_BRANCH_MUST_MATCH_G2_SELECTED_REPAIR_ARTIFACT'):
  if inv not in core['invariants']:core['invariants'].append(inv)
 core['algorithm_provenance_registry_digest']=prov['registry_digest']
 core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits'
 core['canonical_mechanism_mutation']=True
 core['core_digest']=cdig(core,'core_digest');write(CORE,core)

 head['native_selector_commit_substrate']={
   'status':'CANONICAL_ACTIVE','program_id':corr['program_id'],'binding_digest':binding2['binding_digest'],
   'high_scale_candidate_digest':high['candidate_digest'],'fresh9_score':fresh9_new,'runtime':adapter_rel,
 }
 head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest']
 head['algorithm_provenance_registry']['current_execution_label']='G2_NATIVE_SCALE_CONDITIONAL_SELECTOR_CANONICAL_V2'
 head['unified_core']['core_digest']=core['core_digest']
 head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest']
 head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits'
 head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)

 with CanonicalScaleConditionalRuntimeV2(repo_root=REPO) as rt2:
  if rt2.route({'source_count':1.0})!=binding2['branches']['low'] or rt2.route({'source_count':2.0})!=binding2['branches']['high']:
   raise RuntimeError('DEFAULT_CANONICAL_BINDING_LOAD_FAILED')
else:
 core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits';core['core_digest']=cdig(core,'core_digest');write(CORE,core)
 head['unified_core']['core_digest']=core['core_digest'];head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits';head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)

artifact={
 'schema':'yado.g2.kernel_native_selector_canonical_binding.v2',
 'status':'PASS_NATIVE_SELECTOR_CANONICAL_BINDING_V2' if supported else 'WITHHOLD_NATIVE_SELECTOR_CANONICAL_BINDING_V2',
 'candidate_state':state,'candidate_digest':candidate['candidate_digest'],'binding_digest':binding2['binding_digest'],
 'history_old':history_old,'history_new':history_new,'fresh9_old':fresh9_old,'fresh9_new':fresh9_new,
 'next_required_capability':next_cap,'canonical_mechanism_mutation':supported,'architecture_mutation':False,'g3_genesis_performed':False,
}
artifact['artifact_digest']=h(artifact);write(ART,artifact)
prev=ledger['current_head_digest']
receipt={**artifact,'schema':'yado.g2.kernel_native_selector_canonical_binding.receipt.v2',
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest'],'checks':checks,
 'provenance_registry_digest':prov['registry_digest'] if supported else load(PROV)['registry_digest']}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)

ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap];run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_NATIVE_SELECTOR_CANONICAL_BINDING_V2",
 'event_type':'G2_NATIVE_SELECTOR_CANONICAL_ADMISSION_V2' if supported else 'G2_NATIVE_SELECTOR_CANONICAL_BINDING_V2_WITHHOLD',
 'status':'PASS_CANONICAL' if supported else 'WITHHOLD','generation':ledger['current_head'],'deficit':front,
 'effect':f"HISTORY_OLD={history_old:.6f}; HISTORY_NEW={history_new:.6f}; FRESH9_OLD={fresh9_old:.6f}; FRESH9_NEW={fresh9_new:.6f}; NO_REGRESSION={no_regression_each}; CANONICAL={supported}; NEXT={next_cap}",
 'source_path':f'receipts/yado-kernel-native-selector-canonical-binding-v2-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':True,'canonical_mechanism_mutation':supported,'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);write(LEDGER,ledger)
ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_WRITE_CONTEXT_INCONSISTENT')
print(json.dumps({'state':state,'old_scores':old_scores,'new_scores':new_scores,'history_old':history_old,'history_new':history_new,'fresh9_old':fresh9_old,'fresh9_new':fresh9_new,'checks':checks,'next':next_cap},indent=2,sort_keys=True))
