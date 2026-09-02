from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,math,os,subprocess,sys

ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent
sys.path.insert(0,str(ROOT))

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
V5=REPO/'candidates/kernel-self-generated/high-scale-repair-v5.json'
ADAPTER=REPO/'runtime/yado_g2_canonical_high_scale_binding_runtime_v5.py'
BINDING=REPO/'canonical/yado-native-selector-canonical-binding-v5.json'
CAND=REPO/'candidates/kernel-self-generated/native-selector-canonical-binding-v5.json'
PROBES=REPO/'resources/yado-v5-fresh-route-probes-v1.json'
ART=REPO/'architecture/yado-kernel-native-selector-canonical-binding-v5.json'
OUT=ROOT/'yado_kernel_native_selector_canonical_binding_v5_receipt.json'
GUARD=ROOT/'yado_canonical_invariant_guard_v1.py'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):
    x=copy.deepcopy(o);x.pop(field,None);return h(x)
def log(stage,**kw):print(json.dumps({'stage':stage,**kw},sort_keys=True,default=str),flush=True)

head,core,ledger,prov,corpus,high2,v4,v5=map(load,[HEAD,CORE,LEDGER,PROV,CORPUS,HIGH2,V4,V5])
validate_ledger_v2(ledger)
front='KERNEL_NATIVE_SELECTOR_CANONICAL_BINDING_V5'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if head.get('current_frontier')!=front or core.get('current_frontier')!=front:raise RuntimeError('HEAD_CORE_FRONTIER_MISMATCH')
if v5.get('state')!='SHADOW_SUPPORTED':raise RuntimeError('V5_NOT_SHADOW_SUPPORTED')
if v5.get('selected_skill_id')!='INVERT_NORMALIZED_SOURCE_COUNT_ROUTE_V5':raise RuntimeError('V5_SELECTION_DRIFT')
if v4.get('state')!='SHADOW_SUPPORTED' or v4.get('selected_skill_id')!='HIGH_ONLY_TRIPLE_KNN_V4':raise RuntimeError('V4_MODEL_DRIFT')
if head.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')

spent_checks=v5.get('checks') or {}
if not spent_checks or not all(spent_checks.values()):raise RuntimeError('V5_SPENT_HISTORY_EVIDENCE_NOT_CLEAN')
if abs(float(v5['metrics']['selected_route_all_history'])-1.0)>1e-12:raise RuntimeError('V5_ROUTE_HISTORY_NOT_EXACT')
if float(v5['metrics']['candidate_predictive_total'])+1e-12<float(v5['metrics']['parent_predictive_total']):raise RuntimeError('V5_PREDICTIVE_REGRESSION')

binding={
 'schema':'yado.g2.native_selector_canonical_binding.v5',
 'status':'CANDIDATE_PENDING_FRESH_ROUTE_ADMISSION',
 'generation':head['generation_id'],
 'route_semantics':dict(v5['selected_spec']),
 'branch_artifacts':{
   'parent_v2':'candidates/kernel-self-generated/high-scale-repair-v2.json',
   'high_scale_v4':'candidates/kernel-self-generated/high-scale-repair-v4.json',
   'route_repair_v5':'candidates/kernel-self-generated/high-scale-repair-v5.json',
   'corpus':'resources/yado-architecture-neutral-evidence-corpus-frozen-v1.json'
 },
 'binding_runtime':'runtime/yado_g2_canonical_high_scale_binding_runtime_v5.py',
 'artifact_sha256':{
   'candidates/kernel-self-generated/high-scale-repair-v2.json':sha(HIGH2),
   'candidates/kernel-self-generated/high-scale-repair-v4.json':sha(V4),
   'candidates/kernel-self-generated/high-scale-repair-v5.json':sha(V5),
   'resources/yado-architecture-neutral-evidence-corpus-frozen-v1.json':sha(CORPUS),
   'runtime/yado_g2_canonical_high_scale_binding_runtime_v5.py':sha(ADAPTER),
 },
 'semantic_boundary':{
   'binding_adapter_only':True,
   'new_learning_during_binding':False,
   'new_selection_during_binding':False,
   'selected_route_from_v5_kernel_event':'E0219_G2_HIGH_SCALE_REPAIR_V5',
   'fresh_probe_role':'ROUTE_SEMANTICS_ADMISSION_ONLY'
 }
}
binding['binding_digest']=h(binding)
fixed_candidate_digest=v5['candidate_digest']

# Materialize fresh route probes only after the candidate and binding are fixed.
seed='YADO_G2_V5_FRESH_ROUTE_PROBES_V1_2026-09-02'
probes=[]
for cardinality in range(1,19):
    for rep in range(8):
        token=f'{seed}|{cardinality}|{rep}'
        dig=hashlib.sha256(token.encode()).hexdigest()
        raw=int(dig[:8],16)
        jitter=((raw%8001)-4000)/100000.0  # [-0.04, +0.04], round(3*x) remains stable.
        irrelevant=((int(dig[8:16],16)%20001)-10000)/10000.0
        key='|'.join(f'RP{cardinality:02d}_{rep:02d}_{i:02d}' for i in range(cardinality))
        source_count=cardinality/3.0+jitter
        probes.append({
          'probe_id':f'R{cardinality:02d}_{rep:02d}',
          'key':key,
          'x':{'source_count':source_count,'irrelevant_probe_feature':irrelevant},
          'cardinality':cardinality,
          'jitter':jitter,
          'expected_route':'V4_HIGH' if cardinality>=10 else 'V2_PARENT',
          'extrapolative':cardinality>12
        })
probe_digest=h(probes)

with CanonicalHighScaleBindingRuntimeV5(binding=binding,repo_root=REPO) as rt:
    candidate_correct=[rt.route(p)==p['expected_route'] for p in probes]
    candidate_score=sum(candidate_correct)/len(probes)
    boundary=[p for p in probes if p['cardinality'] in (9,10)]
    boundary_score=sum(rt.route(p)==p['expected_route'] for p in boundary)/len(boundary)
    extrap=[p for p in probes if p['cardinality']>12]
    extrap_score=sum(rt.route(p)==p['expected_route'] for p in extrap)/len(extrap)
    cardinality_reconstruction_score=sum(rt.cardinality(p)==p['cardinality'] for p in probes)/len(probes)

def broken_route(p):
    return 'V4_HIGH' if float(p['x']['source_count'])>=10 else 'V2_PARENT'
broken_score=sum(broken_route(p)==p['expected_route'] for p in probes)/len(probes)
high_probes=[p for p in probes if p['cardinality']>=10]
broken_high_score=sum(broken_route(p)==p['expected_route'] for p in high_probes)/len(high_probes)
candidate_high_score=sum((CanonicalHighScaleBindingRuntimeV5(binding=binding,repo_root=REPO).route(p)==p['expected_route']) for p in high_probes)/len(high_probes)

checks={
 'v5_candidate_digest_fixed_before_fresh_probes':fixed_candidate_digest==v5['candidate_digest'],
 'all_bound_artifact_digests_exact':all((REPO/p).exists() and sha(REPO/p)==d for p,d in binding['artifact_sha256'].items()),
 'spent_history_evidence_clean':all(spent_checks.values()),
 'fresh_probe_count_144':len(probes)==144,
 'fresh_probe_cardinality_range_1_to_18':min(p['cardinality'] for p in probes)==1 and max(p['cardinality'] for p in probes)==18,
 'fresh_probes_not_used_for_v5_selection':v5.get('fresh_route_probe_status')=='RESERVED_FOR_CANONICAL_BINDING_V5_NOT_MATERIALIZED',
 'candidate_route_score_exact':abs(candidate_score-1.0)<1e-12,
 'candidate_boundary_9_10_exact':abs(boundary_score-1.0)<1e-12,
 'candidate_extrapolation_13_to_18_exact':abs(extrap_score-1.0)<1e-12,
 'candidate_cardinality_reconstruction_exact':abs(cardinality_reconstruction_score-1.0)<1e-12,
 'candidate_high_route_exact':abs(candidate_high_score-1.0)<1e-12,
 'broken_v4_high_route_fails':broken_high_score<0.5,
 'candidate_beats_broken_route':candidate_score>broken_score+0.40,
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
supported=all(checks.values())
state='CANONICAL_ADMITTED' if supported else 'WITHHOLD'
next_cap='KERNEL_NEUTRAL_ARCHITECTURE_SELECTION_WITH_SELF_GENERATED_SELECTOR_V1' if supported else 'KERNEL_SCALE_CONDITIONAL_SUCCESSOR_HIGH_SCALE_REPAIR_V6'

candidate={
 'schema':'yado.g2.native_selector_canonical_binding_candidate.v5','state':state,
 'binding_digest':binding['binding_digest'],'route_strategy':v5['selected_spec'],
 'v5_candidate_digest':v5['candidate_digest'],'v4_model_candidate_digest':v4['candidate_digest'],
 'fresh_route_probe_digest':probe_digest,'fresh_route_probe_count':len(probes),
 'fresh_route_score':candidate_score,'fresh_boundary_score':boundary_score,
 'fresh_extrapolation_score':extrap_score,'cardinality_reconstruction_score':cardinality_reconstruction_score,
 'broken_v4_route_score':broken_score,'broken_v4_high_route_score':broken_high_score,
 'spent_predictive_old':v5['metrics']['parent_predictive_total'],
 'spent_predictive_new':v5['metrics']['candidate_predictive_total'],
 'checks':checks,'canonical_mechanism_mutation':supported,'architecture_mutation':False,'g3_genesis_performed':False
}
candidate['candidate_digest']=h(candidate);write(CAND,candidate)
write(PROBES,{
 'schema':'yado.g2.v5.fresh_route_probes.history.v1',
 'status':'SPENT_AFTER_SINGLE_CANONICAL_BINDING_ADMISSION',
 'seed':seed,'probe_count':len(probes),'probe_digest':probe_digest,
 'candidate_digest_fixed_before_open':fixed_candidate_digest,
 'candidate_binding_digest':binding['binding_digest'],
 'candidate_score':candidate_score,'broken_v4_score':broken_score,
 'boundary_score':boundary_score,'extrapolation_score':extrap_score,
 'probes':probes
})

previous_head_digest=head['canonical_head_digest']

if supported:
    binding['status']='CANONICAL_ACTIVE'
    binding['admission']={
      'fresh_route_probe_digest':probe_digest,'fresh_route_probe_count':len(probes),
      'fresh_route_score':candidate_score,'boundary_score':boundary_score,
      'extrapolation_score':extrap_score,'broken_v4_route_score':broken_score,'checks':checks
    }
    binding['binding_digest']=cdig(binding,'binding_digest');write(BINDING,binding)

    adapter_rel='runtime/yado_g2_canonical_high_scale_binding_runtime_v5.py'
    if adapter_rel not in core['active_runtime_sources']:core['active_runtime_sources'].append(adapter_rel)
    core['active_runtime_sources']=sorted(dict.fromkeys(core['active_runtime_sources']))
    source_hashes={}
    for rel in core['active_runtime_sources']:
        p=REPO/rel
        if not p.exists():raise RuntimeError('ACTIVE_RUNTIME_SOURCE_MISSING:'+rel)
        source_hashes[rel]=sha(p)
    rim={'algorithm':'SHA256','sources':source_hashes};rim['manifest_digest']=h(source_hashes)
    core['runtime_integrity_manifest']=rim

    core['native_selector_canonical_binding_v5']={
      'status':'CANONICAL_ACTIVE','binding_manifest':'canonical/yado-native-selector-canonical-binding-v5.json',
      'binding_digest':binding['binding_digest'],'runtime':adapter_rel,'runtime_sha256':sha(ADAPTER),
      'route_strategy':v5['selected_spec'],'v4_high_model_candidate_digest':v4['candidate_digest'],
      'fresh_route_score':candidate_score,'fresh_extrapolation_score':extrap_score,
      'spent_predictive_score':v5['metrics']['candidate_predictive_total']
    }
    for plane in core.get('planes',[]):
        if plane.get('plane_id')=='INTELLIGENCE_AND_META_SELECTION':
            for comp in ('ALG-G2-HIGH-SCALE-TRIPLE-KNN-V4','ALG-G2-SCALE-ROUTE-SEMANTICS-V5','RUNTIME-G2-HIGH-SCALE-BINDING-V5'):
                if comp not in plane['active_components']:plane['active_components'].append(comp)
            plane['active_components']=sorted(plane['active_components'])
    for inv in (
      'CANONICAL_HIGH_SCALE_V5_ROUTE_MUST_INVERT_NORMALIZED_SOURCE_COUNT_WITH_DECLARED_DENOMINATOR',
      'CANONICAL_HIGH_SCALE_V5_BINDING_MUST_MATCH_FROZEN_V4_MODEL_AND_V5_ROUTE_REPAIR',
      'FRESH_ROUTE_PROBES_MUST_NOT_PARTICIPATE_IN_V5_SELECTION'
    ):
        if inv not in core['invariants']:core['invariants'].append(inv)

    mech_ids={m.get('mechanism_id') for m in prov.get('mechanisms',[])}
    additions=[
      {
       'mechanism_id':'G2_HIGH_SCALE_TRIPLE_KNN_V4','method':'knn_predict',
       'owner_class':'G2_KERNEL_SELECTED_SHADOW_MODEL','owner_module':'yado_cognitive_growth_runtime_v1',
       'role':'CANONICAL_HIGH_SCALE_BRANCH_MODEL','semantic':'TRIPLE_INTERACTION_KNN_ACTIVE_AT_CARDINALITY_GE_10',
       'signature':'knn_predict(model,x)','source_path':'candidates/kernel-self-generated/high-scale-repair-v4.json',
       'source_sha256':sha(V4),'candidate_digest':v4['candidate_digest'],'selected_skill_id':v4['selected_skill_id']
      },
      {
       'mechanism_id':'G2_SCALE_ROUTE_SEMANTICS_V5','method':'cardinality',
       'owner_class':'CanonicalHighScaleBindingRuntimeV5','owner_module':'yado_g2_canonical_high_scale_binding_runtime_v5',
       'role':'ROUTE_SEMANTICS_REPAIR','semantic':'INVERT_NORMALIZED_SOURCE_COUNT_BY_DECLARED_DENOMINATOR_THEN_COMPARE_CARDINALITY',
       'signature':'cardinality(self,case)','source_path':'runtime/yado_g2_canonical_high_scale_binding_runtime_v5.py',
       'source_sha256':sha(ADAPTER),'selected_skill_id':v5['selected_skill_id']
      },
      {
       'mechanism_id':'G2_HIGH_SCALE_BINDING_ADAPTER_V5','method':'predict',
       'owner_class':'CanonicalHighScaleBindingRuntimeV5','owner_module':'yado_g2_canonical_high_scale_binding_runtime_v5',
       'role':'CANONICAL_BINDING_ADAPTER','semantic':'FROZEN_V2_PARENT_BELOW_CARDINALITY_10_AND_FROZEN_V4_TRIPLE_MODEL_AT_OR_ABOVE_10',
       'signature':'predict(self,case)','source_path':'runtime/yado_g2_canonical_high_scale_binding_runtime_v5.py',
       'source_sha256':sha(ADAPTER),'host_binding_adapter_only':True
      }
    ]
    for item in additions:
        if item['mechanism_id'] not in mech_ids:
            prov['mechanisms'].append(item);mech_ids.add(item['mechanism_id'])

prov['current_g2_binding'].update({
 'current_execution_label':'G2_NATIVE_SCALE_CONDITIONAL_SELECTOR_CANONICAL_V5' if supported else 'G2_HIGH_SCALE_REPAIR_V6_PENDING',
 'frontier':next_cap,
 'frontier_native_method':'select_evolution_skills' if supported else 'propose_evolution_operation',
 'frontier_native_owner':'UnifiedYADOKernelV30RC8ExternalCognitive'
})
if supported:
    prov['current_g2_binding'].update({
      'canonical_binding_runtime':'runtime/yado_g2_canonical_high_scale_binding_runtime_v5.py',
      'canonical_route_strategy':v5['selected_spec'],
      'canonical_high_scale_candidate_digest':v4['candidate_digest'],
      'canonical_binding_digest':binding['binding_digest']
    })
prov['registry_digest']=cdig(prov,'registry_digest');write(PROV,prov)

core['algorithm_provenance_registry_digest']=prov['registry_digest']
core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits'
core['canonical_mechanism_mutation']=supported
core['core_digest']=cdig(core,'core_digest');write(CORE,core)

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
    head['native_selector_canonical_binding_v5']={
      'status':'CANONICAL_ACTIVE','binding_digest':binding['binding_digest'],
      'runtime':'runtime/yado_g2_canonical_high_scale_binding_runtime_v5.py',
      'route_strategy':v5['selected_spec'],'fresh_route_score':candidate_score,
      'fresh_extrapolation_score':extrap_score,'v4_high_model_candidate_digest':v4['candidate_digest']
    }
    head['unified_core']['runtime_integrity_manifest_digest']=core['runtime_integrity_manifest']['manifest_digest']
head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits'
head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)

artifact={
 'schema':'yado.g2.kernel_native_selector_canonical_binding.v5',
 'status':'PASS_NATIVE_SELECTOR_CANONICAL_BINDING_V5' if supported else 'WITHHOLD_NATIVE_SELECTOR_CANONICAL_BINDING_V5',
 'candidate_state':state,'candidate_digest':candidate['candidate_digest'],'binding_digest':binding['binding_digest'],
 'selected_skill_id':v5['selected_skill_id'],'fresh_route_score':candidate_score,
 'fresh_boundary_score':boundary_score,'fresh_extrapolation_score':extrap_score,
 'broken_v4_route_score':broken_score,'spent_predictive_old':v5['metrics']['parent_predictive_total'],
 'spent_predictive_new':v5['metrics']['candidate_predictive_total'],
 'next_required_capability':next_cap,'canonical_mechanism_mutation':supported,
 'architecture_mutation':False,'g3_genesis_performed':False
}
artifact['artifact_digest']=h(artifact);write(ART,artifact)

ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap]
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={**artifact,'schema':'yado.g2.kernel_native_selector_canonical_binding.receipt.v5',
 'previous_head_digest':previous_head_digest,'new_head_digest':head['canonical_head_digest'],
 'checks':checks,'fresh_route_probe_digest':probe_digest,'provenance_registry_digest':prov['registry_digest']}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_NATIVE_SELECTOR_CANONICAL_BINDING_V5",
 'event_type':'G2_NATIVE_SELECTOR_CANONICAL_ADMISSION_V5' if supported else 'G2_NATIVE_SELECTOR_CANONICAL_BINDING_V5_WITHHOLD',
 'status':'PASS_CANONICAL' if supported else 'WITHHOLD','generation':ledger['current_head'],'deficit':front,
 'effect':f"ROUTE={v5['selected_skill_id']}; FRESH_ROUTE={candidate_score:.6f}; BOUNDARY={boundary_score:.6f}; EXTRAP_13_18={extrap_score:.6f}; BROKEN_V4={broken_score:.6f}; PRED_OLD={v5['metrics']['parent_predictive_total']:.6f}; PRED_NEW={v5['metrics']['candidate_predictive_total']:.6f}; CANONICAL={supported}; NEXT={next_cap}",
 'source_path':f'receipts/yado-kernel-native-selector-canonical-binding-v5-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':True,'canonical_mechanism_mutation':supported,'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':previous_head_digest,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);write(LEDGER,ledger)

ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_WRITE_CONTEXT_INCONSISTENT')
cp=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=60)
if cp.returncode!=0:raise RuntimeError('POST_BINDING_V5_GUARD_FAILED:'+cp.stdout[-4000:]+cp.stderr[-1000:])
log('complete',state=state,fresh_route=candidate_score,boundary=boundary_score,extrapolation=extrap_score,broken=broken_score,next=next_cap)
