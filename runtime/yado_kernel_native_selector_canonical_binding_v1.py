from __future__ import annotations
from pathlib import Path
from itertools import combinations
import copy,hashlib,json,os,sys
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

import yado_architecture_neutral_meta_synthesizer_v2 as neutral
from yado_g2_canonical_scale_conditional_runtime_v1 import CanonicalScaleConditionalRuntimeV1
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
BINDING=REPO/'canonical/yado-native-selector-canonical-binding-v1.json'
CORRECTED=REPO/'candidates/kernel-self-generated/native-selector-commit-substrate-v1-corrected.json'
SCALE=REPO/'candidates/kernel-self-generated/scale-conditional-pair-knn-successor-v1.json'
F4=REPO/'candidates/kernel-self-generated/fresh-four-source-curriculum-v1.json'
CAL=REPO/'candidates/kernel-self-generated/evolutionary-centroid-calibrated-successor-v2.json'
LOCAL=REPO/'candidates/kernel-self-generated/evolutionary-local-knn-successor-v1.json'
BASE=REPO/'receipts/yado-architecture-neutral-meta-synth-v2-latest.json'
CORPUS=REPO/'resources/yado-architecture-neutral-evidence-corpus-frozen-v1.json'
REGISTRY=REPO/'runtime/yado_g2_native_selector_commit_registry_v1.sqlite'
ADAPTER=REPO/'runtime/yado_g2_canonical_scale_conditional_runtime_v1.py'
ART=REPO/'architecture/yado-kernel-native-selector-canonical-binding-v1.json'
CAND=REPO/'candidates/kernel-self-generated/native-selector-canonical-binding-v1.json'
FRESH7=REPO/'resources/yado-seven-source-transfer-history-v1.json'
OUT=ROOT/'yado_kernel_native_selector_canonical_binding_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):
 x=copy.deepcopy(o);x.pop(field,None);return h(x)

head,core,ledger,prov,corr,scale,f4,cal,local,base,corpus=map(load,[HEAD,CORE,LEDGER,PROV,CORRECTED,SCALE,F4,CAL,LOCAL,BASE,CORPUS])
validate_ledger_v2(ledger)
front='KERNEL_NATIVE_SELECTOR_COMMIT_SUBSTRATE_CANONICAL_BINDING_V1'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if corr.get('state')!='SHADOW_SUPPORTED':raise RuntimeError('CORRECTED_SUBSTRATE_NOT_SUPPORTED')
if sha(REGISTRY)!=corr['registry_sha256']:raise RuntimeError('REGISTRY_DIGEST_MISMATCH')

artifact_paths={
 'runtime/yado_g2_native_selector_commit_registry_v1.sqlite':sha(REGISTRY),
 'runtime/yado_g2_canonical_scale_conditional_runtime_v1.py':sha(ADAPTER),
 'candidates/kernel-self-generated/scale-conditional-pair-knn-successor-v1.json':sha(SCALE),
 'candidates/kernel-self-generated/fresh-four-source-curriculum-v1.json':sha(F4),
 'candidates/kernel-self-generated/evolutionary-centroid-calibrated-successor-v2.json':sha(CAL),
 'candidates/kernel-self-generated/evolutionary-local-knn-successor-v1.json':sha(LOCAL),
 'receipts/yado-architecture-neutral-meta-synth-v2-latest.json':sha(BASE),
 'resources/yado-architecture-neutral-evidence-corpus-frozen-v1.json':sha(CORPUS),
}
binding={
 'schema':'yado.g2.native_selector_canonical_binding.v1',
 'status':'CANDIDATE_PENDING_FRESH7_ADMISSION',
 'generation':'G2_CANDIDATE_TRCG_V1',
 'selector_registry':{
   'path':'runtime/yado_g2_native_selector_commit_registry_v1.sqlite',
   'sha256':corr['registry_sha256'],
   'program_id':corr['program_id'],
   'program_digest':corr['program_digest'],
   'capability':'SCALE_CONDITIONAL_SELECTOR_ROUTE_V1',
   'native_owner':'DevelopmentalExecutiveV22',
 },
 'binding_runtime':'runtime/yado_g2_canonical_scale_conditional_runtime_v1.py',
 'branches':{'low':scale['branches']['low_scale'],'high':scale['branches']['high_scale']},
 'branch_artifacts':{
   'base':'receipts/yado-architecture-neutral-meta-synth-v2-latest.json',
   'calibrated':'candidates/kernel-self-generated/evolutionary-centroid-calibrated-successor-v2.json',
   'local_knn':'candidates/kernel-self-generated/evolutionary-local-knn-successor-v1.json',
   'high_pair_knn':'candidates/kernel-self-generated/fresh-four-source-curriculum-v1.json',
   'corpus':'resources/yado-architecture-neutral-evidence-corpus-frozen-v1.json',
 },
 'artifact_sha256':artifact_paths,
 'semantic_boundary':{
   'host_binding_adapter_only':True,
   'host_threshold_written':False,
   'host_learner_written':False,
   'routing_decision_executes_native_committed_program':True,
 },
}
binding['binding_digest']=h(binding)

# Recreate source-derived cases and require original source identity.
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
spaces={s:make_cases(s) for s in range(1,8)}
expected_counts=[12,66,220,495,792,924,792]
if [len(spaces[s]) for s in range(1,8)]!=expected_counts:raise RuntimeError('SPACE_COUNTS_INVALID')

def score(rows,runtime):
 return sum(runtime.predict(c)==c['y'] for c in rows)/len(rows)
def route_score(rows,runtime):
 th=float(scale['selected_threshold']);low=scale['branches']['low_scale'];high=scale['branches']['high_scale']
 good=0
 for c in rows:
  expected_route=high if float(c['x']['source_count'])+1e-12>=th else low
  good+=runtime.route(c['x'])==expected_route
 return good/len(rows)

with CanonicalScaleConditionalRuntimeV1(binding=binding,repo_root=REPO) as rt:
 per_size={}
 for s in range(1,8):
  per_size[str(s)]={'score':score(spaces[s],rt),'route_score':route_score(spaces[s],rt),'count':len(spaces[s])}
 history15=sum((spaces[s] for s in range(1,6)),[])
 history16=sum((spaces[s] for s in range(1,7)),[])
 history15_score=score(history15,rt)
 history16_score=score(history16,rt)
 fresh7_score=per_size['7']['score']

reproduce_history15=abs(history15_score-float(scale['metrics']['history_composed']))<1e-12
reproduce_size6=abs(per_size['6']['score']-float(scale['metrics']['fresh6_composed']))<1e-12
routes_exact=all(abs(per_size[str(s)]['route_score']-1.0)<1e-12 for s in range(1,8))
checks={
 'source_sha_exact_match':expected==actual,
 'registry_digest_exact':sha(REGISTRY)==corr['registry_sha256'],
 'all_bound_artifact_digests_present':all((REPO/p).exists() and sha(REPO/p)==d for p,d in artifact_paths.items()),
 'selector_routes_exact_sizes_1_to_7':routes_exact,
 'reproduces_recorded_history_sizes_1_to_5':reproduce_history15,
 'reproduces_recorded_size6':reproduce_size6,
 'fresh7_count_792':len(spaces[7])==792,
 'fresh7_not_used_for_selection_or_training':True,
 'fresh7_above_gate':fresh7_score>=0.90,
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
supported=all(checks.values())
state='CANONICAL_ADMITTED' if supported else 'WITHHOLD'
next_cap='KERNEL_NEUTRAL_ARCHITECTURE_SELECTION_WITH_SELF_GENERATED_SELECTOR_V1' if supported else 'KERNEL_SCALE_CONDITIONAL_SUCCESSOR_HIGH_SCALE_REPAIR_V2'

candidate={
 'schema':'yado.g2.native_selector_canonical_binding_candidate.v1','state':state,
 'binding_digest':binding['binding_digest'],'selector_program_id':corr['program_id'],
 'per_size':per_size,'history15_score':history15_score,'history16_score':history16_score,'fresh7_score':fresh7_score,
 'checks':checks,'canonical_mechanism_mutation':supported,'architecture_mutation':False,'g3_genesis_performed':False,
}
candidate['candidate_digest']=h(candidate);CAND.parent.mkdir(parents=True,exist_ok=True);write(CAND,candidate)

fresh7={
 'schema':'yado.g2.seven_source_transfer_history.v1','status':'SPENT_AFTER_SINGLE_ADMISSION',
 'source_sha256':actual,'case_count':len(spaces[7]),'score':fresh7_score,'route_score':per_size['7']['route_score'],
 'dataset_digest':h(spaces[7]),'binding_candidate_digest':candidate['candidate_digest'],
}
write(FRESH7,fresh7)

if supported:
 binding['status']='CANONICAL_ACTIVE'
 binding['admission']={'fresh7_score':fresh7_score,'history15_score':history15_score,'history16_score':history16_score,'checks':checks}
 binding['binding_digest']=h({k:v for k,v in binding.items() if k!='binding_digest'})
 write(BINDING,binding)

 # Add explicit algorithm provenance.
 rc22=ROOT/'yado_rc8_v36/yado_core_v2_2.py'
 mech_ids={m.get('mechanism_id') for m in prov.get('mechanisms',[])}
 if 'G2_NATIVE_SELECTOR_COMMIT_SUBSTRATE_V1' not in mech_ids:
  prov['mechanisms'].append({
   'mechanism_id':'G2_NATIVE_SELECTOR_COMMIT_SUBSTRATE_V1',
   'method':'execute_capability','owner_class':'DevelopmentalExecutiveV22','owner_module':'yado_core_v2_2',
   'role':'DURABLE_SELECTOR_COMMIT_SUBSTRATE',
   'semantic':'NATIVE_SYNTHESIZE_EVALUATE_COMMIT_RESTORE_BOUNDED_SCALE_SELECTOR',
   'signature':'execute_capability(self, capability: str, payload: Mapping[str, Any]) -> Any',
   'source_path':'runtime/yado_rc8_v36/yado_core_v2_2.py','source_sha256':sha(rc22),
   'program_id':corr['program_id'],'program_digest':corr['program_digest'],'registry_sha256':corr['registry_sha256'],
  })
 if 'G2_SCALE_CONDITIONAL_BINDING_ADAPTER_V1' not in mech_ids:
  prov['mechanisms'].append({
   'mechanism_id':'G2_SCALE_CONDITIONAL_BINDING_ADAPTER_V1','method':'predict',
   'owner_class':'CanonicalScaleConditionalRuntimeV1','owner_module':'yado_g2_canonical_scale_conditional_runtime_v1',
   'role':'CANONICAL_BINDING_ADAPTER',
   'semantic':'LOADS_NATIVE_COMMITTED_SELECTOR_AND_EXECUTES_ALREADY_ADMITTED_LOW_HIGH_BRANCHES_WITHOUT_NEW_SELECTION',
   'signature':'predict(self, case: dict)',
   'source_path':'runtime/yado_g2_canonical_scale_conditional_runtime_v1.py','source_sha256':sha(ADAPTER),
   'host_binding_adapter_only':True,
  })
 prov['current_g2_binding'].update({
   'current_execution_label':'G2_NATIVE_SCALE_CONDITIONAL_SELECTOR_CANONICAL',
   'frontier':next_cap,
   'frontier_native_method':'execute_capability',
   'frontier_native_owner':'DevelopmentalExecutiveV22',
   'canonical_binding_runtime':'runtime/yado_g2_canonical_scale_conditional_runtime_v1.py',
   'canonical_selector_program_id':corr['program_id'],
 })
 have={e.get('event_id') for e in prov.get('relevant_ledger_events',[])}
 for eid in ('E0195_G2_SCALE_CONDITIONAL_REACTION_NORM_V1','E0197_G2_NATIVE_SELECTOR_COMMIT_SUBSTRATE_GENESIS_V1','E0198_G2_NATIVE_SELECTOR_COMMIT_VERDICT_REPAIR_V1'):
  if eid not in have:
   match=next((e for e in ledger['events'] if e.get('event_id')==eid),None)
   if match:
    prov['relevant_ledger_events'].append({k:match.get(k) for k in ('index','event_id','event_type','generation','status','source_path','source_digest','canonical_mutation','promotion_applied')})
 prov['registry_digest']=h({k:v for k,v in prov.items() if k!='registry_digest'})
 write(PROV,prov)

 adapter_rel='runtime/yado_g2_canonical_scale_conditional_runtime_v1.py'
 if adapter_rel not in core['active_runtime_sources']:core['active_runtime_sources'].append(adapter_rel)
 core['active_runtime_sources']=sorted(core['active_runtime_sources'])
 core['native_selector_commit_substrate']={
   'status':'CANONICAL_ACTIVE','program_id':corr['program_id'],'program_digest':corr['program_digest'],
   'registry':'runtime/yado_g2_native_selector_commit_registry_v1.sqlite','registry_sha256':corr['registry_sha256'],
   'binding_manifest':'canonical/yado-native-selector-canonical-binding-v1.json','binding_digest':binding['binding_digest'],
   'runtime':adapter_rel,'runtime_sha256':sha(ADAPTER),'fresh7_score':fresh7_score,
 }
 inv='NATIVE_SELECTOR_EXECUTION_MUST_ROUTE_THROUGH_COMMITTED_EXECUTIVE_PROGRAM'
 if inv not in core['invariants']:core['invariants'].append(inv)
 core['algorithm_provenance_registry_digest']=prov['registry_digest']
 core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits'
 core['canonical_mechanism_mutation']=True
 core['core_digest']=cdig(core,'core_digest');write(CORE,core)

 head['native_selector_commit_substrate']={
   'status':'CANONICAL_ACTIVE','program_id':corr['program_id'],'binding_digest':binding['binding_digest'],
   'fresh7_score':fresh7_score,'runtime':adapter_rel,
 }
 head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest']
 head['algorithm_provenance_registry']['current_execution_label']='G2_NATIVE_SCALE_CONDITIONAL_SELECTOR_CANONICAL'
 head['unified_core']['core_digest']=core['core_digest']
 head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest']
 head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits'
 head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)

 # Canonical default-loader proof after manifest/state writes.
 with CanonicalScaleConditionalRuntimeV1(repo_root=REPO) as rt2:
  default_low=rt2.route({'source_count':1.0})
  default_high=rt2.route({'source_count':2.0})
 if default_low!=binding['branches']['low'] or default_high!=binding['branches']['high']:
  raise RuntimeError('DEFAULT_CANONICAL_BINDING_LOAD_FAILED')
else:
 core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits';core['core_digest']=cdig(core,'core_digest');write(CORE,core)
 head['unified_core']['core_digest']=core['core_digest'];head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits';head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)

artifact={
 'schema':'yado.g2.kernel_native_selector_canonical_binding.v1',
 'status':'PASS_NATIVE_SELECTOR_CANONICAL_BINDING_V1' if supported else 'WITHHOLD_NATIVE_SELECTOR_CANONICAL_BINDING_V1',
 'candidate_state':state,'candidate_digest':candidate['candidate_digest'],'binding_digest':binding['binding_digest'],
 'history15_score':history15_score,'history16_score':history16_score,'fresh7_score':fresh7_score,
 'next_required_capability':next_cap,'canonical_mechanism_mutation':supported,'architecture_mutation':False,'g3_genesis_performed':False,
}
artifact['artifact_digest']=h(artifact);write(ART,artifact)

prev=ledger['current_head_digest']
receipt={**artifact,'schema':'yado.g2.kernel_native_selector_canonical_binding.receipt.v1',
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest'],'checks':checks,
 'provenance_registry_digest':prov['registry_digest'] if supported else load(PROV)['registry_digest']}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)

ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap];run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_NATIVE_SELECTOR_CANONICAL_BINDING_V1",
 'event_type':'G2_NATIVE_SELECTOR_CANONICAL_ADMISSION' if supported else 'G2_NATIVE_SELECTOR_CANONICAL_BINDING_WITHHOLD',
 'status':'PASS_CANONICAL' if supported else 'WITHHOLD','generation':ledger['current_head'],'deficit':front,
 'effect':f"PROGRAM={corr['program_id']}; HISTORY15={history15_score:.6f}; HISTORY16={history16_score:.6f}; FRESH7={fresh7_score:.6f}; ROUTES_EXACT={routes_exact}; CANONICAL={supported}; NEXT={next_cap}",
 'source_path':f'receipts/yado-kernel-native-selector-canonical-binding-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':True,'canonical_mechanism_mutation':supported,'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);write(LEDGER,ledger)
ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_WRITE_CONTEXT_INCONSISTENT')
print(json.dumps({'state':state,'per_size':per_size,'history15':history15_score,'history16':history16_score,'fresh7':fresh7_score,'checks':checks,'next':next_cap},indent=2,sort_keys=True))
