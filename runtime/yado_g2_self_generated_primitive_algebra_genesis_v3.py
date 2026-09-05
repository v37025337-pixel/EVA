from __future__ import annotations

from pathlib import Path
from dataclasses import asdict
import copy,hashlib,inspect,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_generic_relational_meta_language_v1 import GenericRelationalMetaLanguageV1
from yado_generic_event_state_meta_language_v1 import GenericEventStateMetaLanguageV1
from yado_generic_weighted_state_meta_language_v1 import GenericWeightedStateMetaLanguageV1

V2=REPO/'candidates/kernel-self-generated/g2-self-extending-string-transducer-meta-language-genesis-v2.json'
V1=REPO/'candidates/kernel-self-generated/g2-native-compositional-string-transducer-gene-genesis-v1.json'
V5=REPO/'candidates/kernel-self-generated/g2-task-conditioned-semantic-source-edit-meta-language-genesis-v5.json'
OUT=REPO/'candidates/kernel-self-generated/g2-self-generated-primitive-algebra-genesis-v3.json'
DB=ROOT/'yado_self_generated_primitive_algebra_genesis_v3.sqlite'

LANG_SOURCES=[
 ('RELATIONAL',REPO/'runtime/yado_generic_relational_meta_language_v1.py',GenericRelationalMetaLanguageV1),
 ('EVENT_STATE',REPO/'runtime/yado_generic_event_state_meta_language_v1.py',GenericEventStateMetaLanguageV1),
 ('WEIGHTED_STATE',REPO/'runtime/yado_generic_weighted_state_meta_language_v1.py',GenericWeightedStateMetaLanguageV1),
]

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def fsha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

v2,v1,v5=map(load,[V2,V1,V5])
if v2.get('status')!='WITHHOLD_G2_SELF_EXTENDING_STRING_TRANSDUCER_META_LANGUAGE_GENESIS_V2':
    raise RuntimeError('V2_WITHHOLD_REQUIRED')
if v2.get('next_required_capability')!='SELF_GENERATED_PRIMITIVE_ALGEBRA_GENESIS_V3':
    raise RuntimeError('V2_FRONTIER_MISMATCH')

core=UnifiedYADOCoreV1(REPO)
head_before=copy.deepcopy(core.head)

families=[]
for name,path,cls in LANG_SOURCES:
    component=cls.component()
    families.append({
      'family_name':name,
      'component':component,
      'component_id':component.get('component_id'),
      'source_path':str(path.relative_to(REPO)),
      'source_sha256':fsha(path),
      'public_methods':sorted(x for x in dir(cls) if not x.startswith('_') and callable(getattr(cls,x,None))),
      'semantic_boundary':component.get('semantic_boundary'),
    })

# The host does not derive a new primitive set. It transports only YADO's own existing
# family descriptors plus the exact current failure lineage.
if DB.exists():DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    pre_meta=k.meta_grammar_snapshot() if hasattr(k,'meta_grammar_snapshot') else None
    pre_alg=k.algorithm_genesis_snapshot() if hasattr(k,'algorithm_genesis_snapshot') else None
    goal=k.executive.create_goal(
      objective='SELF_GENERATED_PRIMITIVE_ALGEBRA_GENESIS_V3',
      required_capabilities={'SELF_GENERATED_PRIMITIVE_ALGEBRA_GENESIS_V3':1.0},
      success_criteria={'new_primitive_algebra':True,'new_interpreter_family':True,'rollback':True},
    )
    deficits=k.executive.detect_deficits(goal.goal_id)
    native_goal={'goal_id':goal.goal_id,'deficits':[asdict(d) for d in deficits]}
    kernel_outputs={}
    for name in sorted(dir(k)):
        if name.startswith('_') or not any(t in name.lower() for t in ('meta','grammar','language','genesis','evol','construct','synth','primitive','algorithm')):
            continue
        fn=getattr(k,name,None)
        if not callable(fn):continue
        try:sig=inspect.signature(fn)
        except Exception:continue
        required=[p for p in sig.parameters.values() if p.default is inspect._empty and p.kind in (p.POSITIONAL_ONLY,p.POSITIONAL_OR_KEYWORD)]
        if required:continue
        try:kernel_outputs[name]=fn()
        except Exception as e:kernel_outputs[name]={'error':type(e).__name__+':'+str(e)[:500]}
finally:
    try:k.close()
    except Exception:pass

state=core.evolutionary_parent_genome()
experience=copy.deepcopy(state.get('experience') or [])
experience += [
  {
    'role':'YADO_CURRENT_PRIMITIVE_ALGEBRA_GENESIS_DEFICIT',
    'artifact':str(V2.relative_to(REPO)),
    'receipt_sha256':v2.get('receipt_sha256'),
    'status':v2.get('status'),
    'next_required_capability':v2.get('next_required_capability'),
    'checks':v2.get('checks'),
  },
  {
    'role':'YADO_STRING_TRANSDUCER_GENE_FAILURE',
    'artifact':str(V1.relative_to(REPO)),
    'receipt_sha256':v1.get('receipt_sha256'),
    'status':v1.get('status'),
  },
  {
    'role':'YADO_SEMANTIC_SOURCE_EDIT_GENE',
    'artifact':str(V5.relative_to(REPO)),
    'receipt_sha256':v5.get('receipt_sha256'),
    'meta_language_gene':v5.get('meta_language_gene'),
  },
  {
    'role':'YADO_EXISTING_META_LANGUAGE_FAMILY_HISTORY',
    'families':families,
    'host_new_primitive_set_supplied':False,
    'host_new_interpreter_supplied':False,
  },
]
controller=core.evolutionary_genome_cls(state['parent'],experience_sources=experience)
controller_outputs={}
for name in sorted(dir(controller)):
    if name.startswith('_') or not any(t in name.lower() for t in ('meta','grammar','language','genesis','evol','construct','synth','primitive','gene','mutat')):
        continue
    fn=getattr(controller,name,None)
    if not callable(fn):continue
    try:sig=inspect.signature(fn)
    except Exception:continue
    required=[p for p in sig.parameters.values() if p.default is inspect._empty and p.kind in (p.POSITIONAL_ONLY,p.POSITIONAL_OR_KEYWORD)]
    if required:continue
    try:controller_outputs[name]=fn()
    except Exception as e:controller_outputs[name]={'error':type(e).__name__+':'+str(e)[:500]}
if 'evolve_once' not in controller_outputs:
    try:controller_outputs['evolve_once']=controller.evolve_once()
    except Exception as e:controller_outputs['evolve_once']={'error':type(e).__name__+':'+str(e)[:500]}

native_outputs={'kernel':kernel_outputs,'controller':controller_outputs}
baseline=canon({
 'families':families,
 'pre_meta':pre_meta,
 'pre_alg':pre_alg,
 'parent':state['parent'],
 'v5_gene_id':(v5.get('meta_language_gene') or {}).get('gene_id'),
}).lower()
failure_receipt=str(v2.get('receipt_sha256'))

candidates=[]
identity_keys=('gene_id','primitive_algebra_id','primitive_family_id','language_gene_id','meta_language_id','component_id','interpreter_id','grammar_extension_id','program_id')
def walk(x,path='root'):
    if isinstance(x,dict):
        local={k:v for k,v in x.items() if k not in ('experience_sources','families','examples')}
        blob=canon(local).lower()
        ids=[str(x.get(k)) for k in identity_keys if x.get(k) not in (None,'')]
        novel=[z for z in ids if z.lower() not in baseline]
        primitive=any(t in blob for t in ('primitive_algebra','primitive-algebra','primitive_family','primitive-family','operator_algebra','operator-algebra'))
        language=any(t in blob for t in ('meta_language','meta-language','language_family','language-family','interpreter'))
        source_string=any(t in blob for t in ('string','source','serializer','transducer'))
        if novel and primitive and language and source_string:
            candidates.append({
              'path':path,'digest':digest(x),'novel_identities':novel,
              'failure_bound':failure_receipt in canon(x),
              'keys':sorted(map(str,x.keys()))
            })
        for k,v in x.items():walk(v,path+'.'+str(k))
    elif isinstance(x,list):
        for i,v in enumerate(x):walk(v,path+f'[{i}]')
walk(native_outputs)

child=((controller_outputs.get('evolve_once') or {}).get('child') or {})
failure_retained=failure_receipt in canon(child.get('experience_sources') or [])
selected=candidates[0] if candidates else None
rollback=bool(((controller_outputs.get('evolve_once') or {}).get('parent') or {}).get('genome_digest'))

# Architecture boundary: every existing proven self-invention API is bound to an existing
# interpreter class; no generic create_meta_language_family/create_primitive_algebra API exists.
all_public=set()
for _,_,cls in LANG_SOURCES:
    all_public.update(x for x in dir(cls) if not x.startswith('_') and callable(getattr(cls,x,None)))
controller_public=set(x for x in dir(controller) if not x.startswith('_') and callable(getattr(controller,x,None)))
generic_family_constructor=any(
    any(tok in name.lower() for tok in ('create_meta_language','invent_meta_language','create_primitive_algebra','invent_primitive_algebra','synthesize_interpreter_family'))
    for name in controller_public
)

checks={
 'canonical_v5_continuity_active':core.execution_fabric_cls.COMPONENT_ID=='RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V5',
 'v2_primitive_algebra_deficit_consumed':True,
 'existing_meta_language_history_count_ge_3':len(families)>=3,
 'existing_family_sources_digest_bound':all(bool(x['source_sha256']) for x in families),
 'host_new_primitive_set_supplied':False,
 'host_new_interpreter_supplied':False,
 'native_goal_created':True,
 'native_deficit_detected':bool(native_goal['deficits']),
 'native_meta_genesis_routes_executed':bool(kernel_outputs or controller_outputs),
 'current_failure_retained_by_child':failure_retained,
 'generic_family_constructor_already_present':generic_family_constructor,
 'new_self_generated_primitive_algebra_created':selected is not None,
 'new_algebra_has_novel_identity':bool(selected and selected['novel_identities']),
 'new_algebra_binds_current_failure':bool(selected and selected['failure_bound']),
 'rollback_parent_available':rollback,
 'host_string_grammar_used':False,
 'host_primitive_inventory_used':False,
 'host_interpreter_source_used':False,
 'host_patch_used':False,
 'external_models_used':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'automatic_canonical_promotion':False,
}

# A PASS requires an actual newly-created algebra. Absence of a preexisting generic family
# constructor is not itself a failure of the measurement; it is the likely localized cause.
positive=(
 'canonical_v5_continuity_active','v2_primitive_algebra_deficit_consumed',
 'existing_meta_language_history_count_ge_3','existing_family_sources_digest_bound',
 'native_goal_created','native_deficit_detected','native_meta_genesis_routes_executed',
 'current_failure_retained_by_child','new_self_generated_primitive_algebra_created',
 'new_algebra_has_novel_identity','new_algebra_binds_current_failure',
 'rollback_parent_available','canonical_unchanged'
)
negative=('host_new_primitive_set_supplied','host_new_interpreter_supplied','host_string_grammar_used','host_primitive_inventory_used','host_interpreter_source_used','host_patch_used','external_models_used','automatic_canonical_promotion')
passed=all(checks[k] is True for k in positive) and all(checks[k] is False for k in negative)
status='PASS_SHADOW_G2_SELF_GENERATED_PRIMITIVE_ALGEBRA_GENESIS_V3' if passed else 'WITHHOLD_G2_SELF_GENERATED_PRIMITIVE_ALGEBRA_GENESIS_V3'

report={
 'schema':'yado.g2.self_generated_primitive_algebra_genesis.v3',
 'status':status,
 'parent_v2_receipt':v2.get('receipt_sha256'),
 'meta_language_family_history':families,
 'native_goal':native_goal,
 'preexisting_meta_grammar_snapshot':pre_meta,
 'preexisting_algorithm_genesis_snapshot':pre_alg,
 'native_outputs':native_outputs,
 'new_primitive_algebra_candidates':candidates,
 'selected_candidate':selected,
 'architecture_boundary':{
   'controller_public_methods':sorted(controller_public),
   'existing_language_public_methods':sorted(all_public),
   'generic_family_constructor_present':generic_family_constructor,
   'observation':'EXISTING SELF-INVENTION PATHS REQUIRE AN ALREADY-IMPLEMENTED META-LANGUAGE INTERPRETER; NO GENERIC PRIMITIVE-ALGEBRA/INTERPRETER-FAMILY CONSTRUCTOR IS EXPOSED.' if not generic_family_constructor else 'GENERIC_FAMILY_CONSTRUCTOR_PRESENT',
 },
 'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':(
    'SELF_GENERATED_PRIMITIVE_ALGEBRA_EXECUTION_V4'
    if passed else 'SELF_HOSTED_META_LANGUAGE_FAMILY_CONSTRUCTOR_V4'
 ),
 'semantic_boundary':'V3 TRANSPORTS ONLY YADO OWN EXISTING META-LANGUAGE FAMILY DESCRIPTORS/SOURCES AND CURRENT FAILURE LINEAGE. IT DOES NOT SUPPLY A NEW PRIMITIVE SET, INTERPRETER, STRING GRAMMAR OR PATCH. PASS REQUIRES YADO NATIVE OUTPUT TO CREATE A NEW PRIMITIVE ALGEBRA WITH NEW IDENTITY BOUND TO THE CURRENT FAILURE. WITHHOLD LOCALIZES THE GAP TO A SELF-HOSTED META-LANGUAGE FAMILY CONSTRUCTOR.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'family_history_count':len(families),
 'generic_family_constructor_present':generic_family_constructor,
 'new_primitive_algebra_candidate_count':len(candidates),'selected_candidate':selected,
 'next_required_capability':report['next_required_capability'],
 'checks':checks,'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True,default=str))
if not passed:raise SystemExit(2)
