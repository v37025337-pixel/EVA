from __future__ import annotations
from pathlib import Path
import copy,hashlib,inspect,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
REG=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
OUT=ROOT/'yado_g2_algorithm_provenance_registry_v1_receipt.json'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def write(p,o): p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def file_sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def content_digest(o,field):
    x=copy.deepcopy(o);x.pop(field,None);return h(x)

head,core,ledger=map(load,[HEAD,CORE,LEDGER])
validate_ledger_v2(ledger)
if ledger.get('current_head')!='G2_CANDIDATE_TRCG_V1': raise RuntimeError('NOT_G2')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'): raise RuntimeError('HEAD_LEDGER_MISMATCH')
if ledger.get('open_deficits')!=['KERNEL_SELF_EXPAND_ARCHITECTURE_SELECTOR_CONSTRUCTOR_V4']:
    raise RuntimeError('UNEXPECTED_FRONTIER')

cls=UnifiedYADOKernelV30RC8ExternalCognitive
mro=list(cls.__mro__)
name_to_class={c.__name__:c for c in mro if c is not object}

def owner(method_name):
    for c in mro:
        if method_name in getattr(c,'__dict__',{}):
            fn=getattr(c,method_name)
            path=Path(inspect.getsourcefile(fn)).resolve()
            return {
              'method':method_name,
              'owner_class':c.__name__,
              'owner_module':c.__module__,
              'source_path':str(path.relative_to(REPO.resolve())) if REPO.resolve() in path.parents else str(path),
              'source_sha256':file_sha(path),
              'signature':str(inspect.signature(fn)),
            }
    raise RuntimeError('METHOD_OWNER_NOT_FOUND:'+method_name)

mechanism_specs=[
 ('RC4_META_EVOLUTION','meta_evolve_intelligence','META_EVOLUTION','REVEALED_VALIDATION_ALGORITHM_SELECTION'),
 ('RC5_ALGORITHM_CONSTRUCTOR','synthesize_intelligence_algorithm_component','ALGORITHM_CONSTRUCTION','CONSTRUCTOR_FROM_OBSERVED_SIGNAL_STRUCTURE'),
 ('RC6_EXTENDED_META_GRAMMAR','synthesize_intelligence_with_extended_meta_grammar','META_GRAMMAR','PREDICATE_PROGRAM_ROUTING_OVER_EVOLUTION_ALGORITHMS'),
 ('RC7_EVOLUTION_OPERATION_CONTROL','propose_evolution_operation','EVOLUTION_CONTROL','REACTION_NORM_CROSS_LINEAGE_CLONAL_OPERATION_SELECTION'),
 ('RC7_DURABLE_COMMIT_GUARD','durable_commit_evolution_bundle','DURABLE_COMMIT_CONTROL','ACTIVE_STATE_ONLY_DURABLE_EVOLUTION_COMMIT'),
 ('RC8_EXTERNAL_COGNITIVE_ASSESSMENT','assess_external_runtime_candidate','EXTERNAL_COGNITIVE_CONTROL','EXTERNAL_RUNTIME_CANDIDATE_ASSESSMENT'),
]
mechanisms=[]
for mid,meth,role,semantic in mechanism_specs:
    rec=owner(meth)
    rec.update({'mechanism_id':mid,'role':role,'semantic':semantic})
    mechanisms.append(rec)

transition_order=[
 'RC4_META_EVOLUTION',
 'RC5_ALGORITHM_CONSTRUCTOR',
 'RC6_EXTENDED_META_GRAMMAR',
 'RC7_EVOLUTION_OPERATION_CONTROL',
 'RC8_EXTERNAL_COGNITIVE_ASSESSMENT',
 'G2_ACTIVE_GENERATION'
]
by_id={m['mechanism_id']:m for m in mechanisms}
transitions=[]
for a,b in zip(transition_order,transition_order[1:]):
    if b=='G2_ACTIVE_GENERATION':
        transitions.append({
          'from':a,'to':b,'relation':'RUNTIME_EXPOSED_TO_G2',
          'executable_inheritance_confirmed':True,
          'formal_promotion_event_present':any(e.get('event_id')=='E0044_G2_PROMOTION' for e in ledger['events']),
          'formal_promotion_event_id':'E0044_G2_PROMOTION',
          'note':'G2 promotion is formal; the inherited RC8 runtime is the execution substrate.'
        })
    else:
        transitions.append({
          'from':a,'to':b,'relation':'PYTHON_MRO_INHERITANCE_AND_METHOD_AVAILABILITY',
          'executable_inheritance_confirmed':True,
          'formal_promotion_event_present':False,
          'formal_promotion_event_id':None,
          'note':'Executable inheritance is verified from reconstructed RC8v36 MRO; no separate ledger promotion event exists for this RC-to-RC step.'
        })

relevant=[]
for e in ledger.get('events',[]):
    blob=' '.join(str(e.get(k,'')) for k in ('event_id','event_type','deficit','effect'))
    if any(x in blob.upper() for x in ('ALGORITHM_GENESIS','META_GRAMMAR','G2_PROMOTION','REACTION_NORM','CONSTRUCTOR')):
        relevant.append({
          'event_id':e.get('event_id'),'index':e.get('index'),'status':e.get('status'),
          'generation':e.get('generation'),'event_type':e.get('event_type'),
          'source_path':e.get('source_path'),'source_digest':e.get('source_digest'),
          'canonical_mutation':e.get('canonical_mutation'),'promotion_applied':e.get('promotion_applied'),
        })

k=cls(db_path=str(ROOT/'yado_algorithm_provenance_registry.sqlite'))
try:
    meta_snapshot=k.meta_evolution_snapshot()
    grammar_snapshot=k.meta_grammar_snapshot()
    constructor_registry=k.algorithm_constructor_registry()
    bank=k.organ_evolution_algorithm_bank()
finally:
    k.close()

registry={
 'schema':'yado.algorithm_provenance_registry.v1',
 'registry_id':'YADO_G2_ALGORITHM_PROVENANCE_REGISTRY_V1',
 'status':'CANONICAL_ACTIVE',
 'generation':'G2_CANDIDATE_TRCG_V1',
 'runtime_profile':'YADO_V3_0_RC8_VERIFIED_EXTERNAL_COGNITIVE_RUNTIME',
 'runtime_package':{
   'reconstructor':'runtime/reconstruct_rc8v36.py',
   'package_meta':'runtime/package_meta.json',
   'package_sha256':load(ROOT/'package_meta.json').get('package_sha256'),
 },
 'lineage_semantics':{
   'rc_labels':'IMPLEMENTATION_RELEASE_CANDIDATE_LAYERS_WITHIN_RECONSTRUCTED_RC8V36_RUNTIME',
   'generation_labels':'FORMAL_CAUSAL_GENERATION_HEADS_TRACKED_BY_EVOLUTION_LEDGER',
   'rule':'DO_NOT_EQUATE_RC_LAYER_INHERITANCE_WITH_FORMAL_GENERATION_PROMOTION_WITHOUT_LEDGER_EVENT'
 },
 'mechanisms':mechanisms,
 'transition_chain':transitions,
 'current_g2_binding':{
   'generation':head['generation_id'],
   'frontier':ledger['open_deficits'][0],
   'active_runtime_class':cls.__name__,
   'frontier_native_method':'synthesize_intelligence_with_extended_meta_grammar',
   'frontier_native_owner':'UnifiedYADOKernelV30RC6MetaGrammar',
   'current_execution_label':'G2_NATIVE_EXTENDED_META_GRAMMAR',
   'historical_origin_label':'RC6_EXTENDED_META_GRAMMAR',
 },
 'runtime_state':{
   'meta_evolution_snapshot':meta_snapshot,
   'meta_grammar_snapshot':grammar_snapshot,
   'algorithm_bank_counts':{k:len(v) for k,v in bank.items()},
   'constructor_count':len(constructor_registry),
 },
 'relevant_ledger_events':relevant,
 'invariants':[
   'EVERY_ACTIVE_OR_SHADOW_MECHANISM_HAS_CURRENT_OWNER_AND_SOURCE_DIGEST',
   'RC_ORIGIN_LABEL_NEVER_OVERRIDES_CURRENT_G2_RUNTIME_LABEL',
   'ABSENT_RC_PROMOTION_EVENTS_ARE_RECORDED_AS_ABSENT_NOT_INFERRED',
   'FORMAL_GENERATION_TRANSITIONS_REQUIRE_LEDGER_PROMOTION_EVENT',
   'CURRENT_FRONTIER_CONSUMER_MUST_RESOLVE_TO_RECONSTRUCTED_RC8V36_RUNTIME',
 ],
}
registry['registry_digest']=content_digest(registry,'registry_digest')
write(REG,registry)

previous_head_digest=head['canonical_head_digest']
core['algorithm_provenance_registry']='canonical/yado-algorithm-provenance-registry-v1.json'
core['algorithm_provenance_registry_digest']=registry['registry_digest']
core.setdefault('invariants',[])
for inv in ('ALGORITHM_PROVENANCE_MUST_BE_EXPLICIT','RC_LAYER_INHERITANCE_IS_NOT_A_GENERATION_PROMOTION'):
    if inv not in core['invariants']:core['invariants'].append(inv)
core['core_digest']=content_digest(core,'core_digest')
write(CORE,core)

head.setdefault('unified_core',{})
head['unified_core']['core_digest']=core['core_digest']
head['unified_core']['algorithm_provenance_registry_digest']=registry['registry_digest']
head['algorithm_provenance_registry']={
 'registry_id':registry['registry_id'],
 'registry':'canonical/yado-algorithm-provenance-registry-v1.json',
 'registry_digest':registry['registry_digest'],
 'current_execution_label':'G2_NATIVE_EXTENDED_META_GRAMMAR',
}
head['canonical_head_digest']=content_digest(head,'canonical_head_digest')
write(HEAD,head)

ledger['current_head_digest']=head['canonical_head_digest']
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
event={
 'index':len(ledger['events']),
 'event_id':f"E{len(ledger['events'])+1:04d}_G2_ALGORITHM_PROVENANCE_REGISTRY_V1",
 'event_type':'G2_ALGORITHM_PROVENANCE_CANONICAL_BINDING',
 'status':'PASS','generation':ledger['current_head'],
 'deficit':'RC_LAYER_TO_G2_ALGORITHMIC_PROVENANCE_GAP',
 'effect':f"CHAIN=RC4>RC5>RC6>RC7>RC8>G2; FORMAL_RC_PROMOTIONS=ABSENT_NOT_INFERRED; EXECUTION_LABEL=G2_NATIVE_EXTENDED_META_GRAMMAR; NEXT={ledger['open_deficits'][0]}",
 'source_path':f'receipts/yado-g2-algorithm-provenance-registry-v1-run-{run_id}.json',
 'source_digest':registry['registry_digest'],'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':True,
 'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':previous_head_digest,'new_head_digest':head['canonical_head_digest'],
}
event['event_hash']=event_hash(event)
ledger['events'].append(event);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=event['event_hash']
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);write(LEDGER,ledger)

checks={
 'registry_digest_valid':content_digest(registry,'registry_digest')==registry['registry_digest'],
 'all_mechanisms_have_owner':all(m.get('owner_class') and m.get('source_sha256') for m in mechanisms),
 'rc4_owner_correct':by_id['RC4_META_EVOLUTION']['owner_class']=='UnifiedYADOKernelV30RC4MetaAutoEvolution',
 'rc5_owner_correct':by_id['RC5_ALGORITHM_CONSTRUCTOR']['owner_class']=='UnifiedYADOKernelV30RC5AlgorithmGenesis',
 'rc6_owner_correct':by_id['RC6_EXTENDED_META_GRAMMAR']['owner_class']=='UnifiedYADOKernelV30RC6MetaGrammar',
 'rc7_owner_correct':by_id['RC7_EVOLUTION_OPERATION_CONTROL']['owner_class']=='UnifiedYADOKernelV30RC7DeepIntegrity',
 'rc8_owner_correct':by_id['RC8_EXTERNAL_COGNITIVE_ASSESSMENT']['owner_class']=='UnifiedYADOKernelV30RC8ExternalCognitive',
 'rc_intermediate_promotions_not_inferred':all(t['formal_promotion_event_present'] is False for t in transitions[:-1]),
 'formal_g2_promotion_present':transitions[-1]['formal_promotion_event_present'] is True,
 'head_ledger_digest_match':ledger['current_head_digest']==head['canonical_head_digest'],
 'frontier_preserved':ledger['open_deficits']==['KERNEL_SELF_EXPAND_ARCHITECTURE_SELECTOR_CONSTRUCTOR_V4'],
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
if not all(checks.values()): raise RuntimeError('PROVENANCE_CHECK_FAILED:'+json.dumps(checks,sort_keys=True))

receipt={
 'schema':'yado.g2.algorithm_provenance_registry.receipt.v1',
 'status':'PASS_G2_ALGORITHM_PROVENANCE_REGISTRY_V1',
 'registry_digest':registry['registry_digest'],
 'previous_head_digest':previous_head_digest,
 'new_head_digest':head['canonical_head_digest'],
 'mechanism_count':len(mechanisms),
 'transition_count':len(transitions),
 'current_execution_label':'G2_NATIVE_EXTENDED_META_GRAMMAR',
 'historical_origin_label':'RC6_EXTENDED_META_GRAMMAR',
 'frontier':ledger['open_deficits'][0],
 'checks':checks,
 'canonical_mutation':True,'architecture_mutation':False,'generation_transition':False,
 'g3_genesis_performed':False,
}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)
print(json.dumps(receipt,indent=2,sort_keys=True))
