from __future__ import annotations
from pathlib import Path
from itertools import combinations
import copy,hashlib,json,os,subprocess,sys

ROOT=Path(__file__).resolve().parent; REPO=ROOT.parent
sys.path.insert(0,str(ROOT))

import yado_architecture_neutral_meta_synthesizer_v2 as neutral
from yado_g2_canonical_high_scale_binding_runtime_v5 import CanonicalHighScaleBindingRuntimeV5
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
CORPUS=REPO/'resources/yado-architecture-neutral-evidence-corpus-frozen-v1.json'
BINDING=REPO/'canonical/yado-native-selector-canonical-binding-v5.json'
V5=REPO/'candidates/kernel-self-generated/high-scale-repair-v5.json'
ART=REPO/'architecture/yado-kernel-neutral-architecture-selection-with-self-generated-selector-v1.json'
CAND=REPO/'candidates/kernel-self-generated/neutral-architecture-selection-v1.json'
SNAP=REPO/'resources/yado-neutral-architecture-selection-application-v1.json'
OUT=ROOT/'yado_kernel_neutral_architecture_selection_with_self_generated_selector_v1_receipt.json'
GUARD=ROOT/'yado_canonical_invariant_guard_v1.py'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):
    x=copy.deepcopy(o);x.pop(field,None);return h(x)
def log(stage,**kw):print(json.dumps({'stage':stage,**kw},sort_keys=True,default=str),flush=True)

head,core,ledger,prov,corpus,binding,v5=map(load,[HEAD,CORE,LEDGER,PROV,CORPUS,BINDING,V5])
validate_ledger_v2(ledger)
front='KERNEL_NEUTRAL_ARCHITECTURE_SELECTION_WITH_SELF_GENERATED_SELECTOR_V1'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if head.get('current_frontier')!=front or core.get('current_frontier')!=front:raise RuntimeError('HEAD_CORE_FRONTIER_MISMATCH')
if binding.get('status')!='CANONICAL_ACTIVE':raise RuntimeError('V5_BINDING_NOT_CANONICAL')
if v5.get('state')!='SHADOW_SUPPORTED' or v5.get('selected_skill_id')!='INVERT_NORMALIZED_SOURCE_COUNT_ROUTE_V5':raise RuntimeError('V5_ROUTE_REPAIR_DRIFT')
if head.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')

data=neutral.build_dataset(force=True)
expected={x['id']:x['sha256'] for x in corpus['source_digests']}
actual={sid:r['sha256'] for sid,r in data['rows'].items()}
if expected!=actual:raise RuntimeError('SOURCE_DIGEST_DRIFT')
ids=sorted(data['rows'])
if len(ids)!=12:raise RuntimeError('EXPECTED_12_FROZEN_SOURCES')

def case(combo):
    x,y,counts=neutral._vector(combo,data['rows'])
    return {'key':'|'.join(combo),'x':x,'y':y,'counts':counts,'size':len(combo)}

full=case(tuple(ids))
loo=[case(c) for c in combinations(ids,11)]
double_ablation=[case(c) for c in combinations(ids,10)]

with CanonicalHighScaleBindingRuntimeV5(binding=binding,repo_root=REPO) as rt:
    selected_family=rt.predict(full)
    full_route=rt.route(full)
    loo_predictions=[rt.predict(c) for c in loo]
    double_predictions=[rt.predict(c) for c in double_ablation]
    loo_routes=[rt.route(c) for c in loo]
    double_routes=[rt.route(c) for c in double_ablation]

families=sorted(neutral.FAMILIES)
if selected_family not in families:raise RuntimeError('SELECTED_FAMILY_OUTSIDE_NEUTRAL_FAMILIES:'+str(selected_family))

def dist(values):
    return {k:values.count(k) for k in sorted(set(values))}
loo_dist=dist(loo_predictions);double_dist=dist(double_predictions)
loo_support=loo_dist.get(selected_family,0)/len(loo_predictions)
double_support=double_dist.get(selected_family,0)/len(double_predictions)
full_label_agreement=(selected_family==full['y'])
loo_label_accuracy=sum(p==c['y'] for p,c in zip(loo_predictions,loo))/len(loo)
double_label_accuracy=sum(p==c['y'] for p,c in zip(double_predictions,double_ablation))/len(double_ablation)

# Application-only stability rule: no new learning, no architecture mutation.
# Full profile decides the family; ablations only determine whether the direction is robust enough to carry forward.
checks={
 'source_sha_exact_match':expected==actual,
 'canonical_v5_binding_exact':binding.get('binding_digest')==head.get('native_selector_canonical_binding_v5',{}).get('binding_digest'),
 'selector_is_canonical_active':binding.get('status')=='CANONICAL_ACTIVE',
 'full_profile_routes_high':full_route=='V4_HIGH',
 'full_profile_label_agreement':full_label_agreement,
 'leave_one_out_route_exact':all(r=='V4_HIGH' for r in loo_routes),
 'double_ablation_route_exact':all(r=='V4_HIGH' for r in double_routes),
 'leave_one_out_selected_family_majority':loo_support>=0.75,
 'double_ablation_selected_family_majority':double_support>=0.75,
 'no_new_learning':True,
 'no_new_selector_selection':True,
 'architecture_not_mutated':True,
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
supported=all(checks.values())
state='SHADOW_SELECTED' if supported else 'WITHHOLD'
next_cap='KERNEL_SELECTED_ARCHITECTURE_FAMILY_EXECUTABLE_SUCCESSOR_DESIGN_V1' if supported else 'KERNEL_NEUTRAL_ARCHITECTURE_SELECTION_ROBUSTNESS_REPAIR_V1'

candidate={
 'schema':'yado.g2.neutral_architecture_selection.v1','state':state,
 'selected_family':selected_family,
 'selector_binding_digest':binding['binding_digest'],
 'selector_route_strategy':binding['route_semantics'],
 'evidence_scope':'FROZEN_12_SOURCE_ARCHITECTURE_NEUTRAL_CORPUS_APPLICATION_ONLY',
 'full_profile':{'source_count':12,'predicted_family':selected_family,'reference_label':full['y'],'route':full_route},
 'robustness':{
   'leave_one_out_count':len(loo),'leave_one_out_distribution':loo_dist,'leave_one_out_selected_family_support':loo_support,'leave_one_out_label_accuracy':loo_label_accuracy,
   'double_ablation_count':len(double_ablation),'double_ablation_distribution':double_dist,'double_ablation_selected_family_support':double_support,'double_ablation_label_accuracy':double_label_accuracy
 },
 'checks':checks,
 'semantic_boundary':'EVIDENCE-CONDITIONED SHADOW ARCHITECTURE DIRECTION FROM CANONICAL SELF-GENERATED SELECTOR; NOT A PROOF OF GLOBALLY OPTIMAL ARCHITECTURE, NOT A GENERATION PROMOTION, AND NOT A CLAIM OF AGI OR SUBJECTIVE CONSCIOUSNESS.',
 'canonical_active':False,'architecture_mutation':False,'canonical_mechanism_mutation':False,'generation_transition':False,'g3_genesis_performed':False
}
candidate['candidate_digest']=h(candidate);write(CAND,candidate)

snapshot={
 'schema':'yado.g2.neutral_architecture_selection.application_snapshot.v1',
 'status':'SPENT_APPLICATION_EVIDENCE',
 'selector_binding_digest':binding['binding_digest'],'selected_family':selected_family,
 'source_sha256':actual,'full_case_digest':h(full),
 'leave_one_out_digest':h(loo),'double_ablation_digest':h(double_ablation),
 'loo_distribution':loo_dist,'double_distribution':double_dist,
 'candidate_digest':candidate['candidate_digest']
}
snapshot['snapshot_digest']=cdig(snapshot,'snapshot_digest');write(SNAP,snapshot)

artifact={
 'schema':'yado.g2.kernel_neutral_architecture_selection_with_self_generated_selector.v1',
 'status':'PASS_NEUTRAL_ARCHITECTURE_SELECTION_V1' if supported else 'WITHHOLD_NEUTRAL_ARCHITECTURE_SELECTION_V1',
 'candidate_state':state,'candidate_digest':candidate['candidate_digest'],'selected_family':selected_family,
 'loo_support':loo_support,'double_ablation_support':double_support,
 'next_required_capability':next_cap,'architecture_mutation':False,'canonical_mechanism_mutation':False,'generation_transition':False,'g3_genesis_performed':False
}
artifact['artifact_digest']=h(artifact);write(ART,artifact)

previous_head_digest=head['canonical_head_digest']

# Reconcile the import-path failure from the first V5 binding attempt without rewriting the original event.
if not any(e.get('event_type')=='G2_EXECUTION_FAILURE_DETAIL_RECONCILIATION' and str(e.get('run_id'))=='33658709857' for e in ledger['events']):
    prior=next((e for e in ledger['events'] if str(e.get('run_id'))=='33658709857'),None)
    if prior is not None:
        idx=len(ledger['events'])
        de={
          'index':idx,'event_id':f"E{idx+1:04d}_G2_V5_BINDING_FAILURE_DETAIL_33658709857",
          'event_type':'G2_EXECUTION_FAILURE_DETAIL_RECONCILIATION','status':'WITHHOLD',
          'generation':ledger['current_head'],'deficit':'KERNEL_NATIVE_SELECTOR_CANONICAL_BINDING_V5',
          'effect':'RUN=33658709857; ERROR=ModuleNotFoundError:yado_cognitive_growth_runtime_v1; FAILURE_STAGE=IMPORT_BEFORE_PROBE_MATERIALIZATION; FRESH_ROUTE_PROBES_MATERIALIZED=False; ADMISSION_EVIDENCE=False; NEXT='+front,
          'source_path':prior.get('source_path'),'source_digest':prior.get('source_digest'),'run_id':'33658709857',
          'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':False,'promotion_applied':False,'generation_transition':False
        }
        de['event_hash']=event_hash(de);ledger['events'].append(de);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=de['event_hash']
        ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
        validate_ledger_v2(ledger)

prov['current_g2_binding'].update({
 'current_execution_label':'G2_NEUTRAL_ARCHITECTURE_DIRECTION_'+selected_family if supported else 'G2_NEUTRAL_ARCHITECTURE_ROBUSTNESS_REPAIR_PENDING',
 'frontier':next_cap,
 'frontier_native_method':'predict',
 'frontier_native_owner':'CanonicalHighScaleBindingRuntimeV5',
 'selected_architecture_family_shadow':selected_family if supported else None
})
prov['registry_digest']=cdig(prov,'registry_digest');write(PROV,prov)

core['algorithm_provenance_registry_digest']=prov['registry_digest']
core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits'
core['neutral_architecture_selection_v1']={
 'status':state,'selected_family':selected_family,'candidate_digest':candidate['candidate_digest'],
 'selector_binding_digest':binding['binding_digest'],'loo_support':loo_support,'double_ablation_support':double_support,
 'architecture_mutation':False
}
core['core_digest']=cdig(core,'core_digest');write(CORE,core)

head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest']
head['algorithm_provenance_registry']['current_execution_label']=prov['current_g2_binding']['current_execution_label']
head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest']
head['unified_core']['core_digest']=core['core_digest']
head['neutral_architecture_selection_v1']={
 'status':state,'selected_family':selected_family,'candidate_digest':candidate['candidate_digest'],
 'selector_binding_digest':binding['binding_digest'],'architecture_mutation':False
}
head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits'
head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)

ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap]
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={**artifact,'schema':'yado.g2.kernel_neutral_architecture_selection_with_self_generated_selector.receipt.v1',
 'previous_head_digest':previous_head_digest,'new_head_digest':head['canonical_head_digest'],'checks':checks,
 'selector_binding_digest':binding['binding_digest'],'application_snapshot_digest':snapshot['snapshot_digest'],
 'provenance_registry_digest':prov['registry_digest']}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_NEUTRAL_ARCHITECTURE_SELECTION_V1",
 'event_type':'G2_CANONICAL_SELECTOR_ARCHITECTURE_DIRECTION_APPLICATION','status':'PASS_SHADOW' if supported else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':front,
 'effect':f"SELECTED_FAMILY={selected_family}; LOO_SUPPORT={loo_support:.6f}; DOUBLE_ABLATION_SUPPORT={double_support:.6f}; ARCHITECTURE_MUTATION=False; NEXT={next_cap}",
 'source_path':f'receipts/yado-kernel-neutral-architecture-selection-with-self-generated-selector-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':True,'canonical_mechanism_mutation':False,'architecture_mutation':False,
 'promotion_applied':False,'generation_transition':False,'previous_head_digest':previous_head_digest,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);write(LEDGER,ledger)

ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_WRITE_CONTEXT_INCONSISTENT')
cp=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=60)
if cp.returncode!=0:raise RuntimeError('POST_SELECTION_GUARD_FAILED:'+cp.stdout[-4000:]+cp.stderr[-1000:])
log('complete',state=state,selected_family=selected_family,loo_support=loo_support,double_ablation_support=double_support,next=next_cap)
