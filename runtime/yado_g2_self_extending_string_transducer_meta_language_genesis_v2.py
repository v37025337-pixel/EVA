from __future__ import annotations

from pathlib import Path
from dataclasses import asdict
import ast,copy,hashlib,inspect,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_evolutionary_genome_v2 import YADOEvolutionaryGenomeV2
from yado_evolutionary_genome_v3 import YADOEvolutionaryGenomeV3
from yado_meta_grammar_genesis_cycle1 import LowLevelCoordinateSynthesizer
from yado_phase_a_shadow import Case
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive

TASK=REPO/'architecture/yado-kernel-self-extending-string-transducer-meta-language-genesis-v2-request.json'
V1=REPO/'candidates/kernel-self-generated/g2-native-compositional-string-transducer-gene-genesis-v1.json'
V6=REPO/'candidates/kernel-self-generated/g2-history-derived-semantic-source-edit-serialization-v6.json'
OLD=REPO/'candidates/kernel-self-generated/g2-native-source-primitive-execution-serialization-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-self-extending-string-transducer-meta-language-genesis-v2.json'
DB=ROOT/'yado_self_extending_string_transducer_meta_language_genesis_v2.sqlite'
SOURCES=[
 REPO/'runtime/yado_evolutionary_genome_v1.py',
 REPO/'runtime/yado_ambiguity_aware_program_repair_v11.py',
 REPO/'runtime/yado_generic_compile_repair_meta_language_v1.py',
 REPO/'runtime/yado_generic_history_compile_repair_meta_language_v1.py',
]

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))

task,v1,v6,old=map(load,[TASK,V1,V6,OLD])
if v1.get('status')!='WITHHOLD_G2_NATIVE_COMPOSITIONAL_STRING_TRANSDUCER_GENE_GENESIS_V1':
    raise RuntimeError('V1_TRANSDUCER_GENESIS_WITHHOLD_REQUIRED')
if v1.get('next_required_capability')!='SELF_EXTENDING_STRING_TRANSDUCER_META_LANGUAGE_GENESIS_V2':
    raise RuntimeError('V1_FRONTIER_MISMATCH')
if old.get('status')!='WITHHOLD_G2_NATIVE_SOURCE_PRIMITIVE_EXECUTION_SERIALIZATION_V1':
    raise RuntimeError('PRIOR_SERIALIZER_WITHHOLD_REQUIRED')

core=UnifiedYADOCoreV1(REPO)
head_before=copy.deepcopy(core.head)

# Reconstruct YADO-own AST/source memory. The source labels remain hidden from native
# family-genesis routes except for the bounded coordinate expressiveness probe.
allowed=(ast.BinOp,ast.BoolOp,ast.Compare,ast.IfExp,ast.Call,ast.Subscript,ast.List,ast.Tuple,ast.Dict,ast.UnaryOp)
rows=[]
for p in SOURCES:
    tree=ast.parse(p.read_text(encoding='utf-8'))
    for n in ast.walk(tree):
        if not isinstance(n,allowed):continue
        try:expected=ast.unparse(n)
        except Exception:continue
        if not (3<=len(expected)<=160):continue
        rows.append({
          'ast_structure':ast.dump(n,annotate_fields=True,include_attributes=False),
          'node_type':type(n).__name__,
          'expected_source':expected,
        })
seen=set();examples=[]
for r in rows:
    k=canon(r)
    if k in seen:continue
    seen.add(k);examples.append(r)
if len(examples)<1000:raise RuntimeError('SELF_SOURCE_MEMORY_TOO_SMALL')

# Content-addressed split.
def bucket(r):return int(hashlib.sha256(canon(r).encode()).hexdigest()[:8],16)%10
fit=[r for r in examples if bucket(r)<6]
validation=[r for r in examples if 6<=bucket(r)<8]
blind=[r for r in examples if bucket(r)>=8]

# Existing meta-grammar family induction receives only character sequences.
# No AST node names or string grammar are added. This is an expressiveness probe
# of the already-existing low-level coordinate algebra, not a new serializer.
probe_rows=[]
for i,r in enumerate(fit[:48]):
    inp=list(r['ast_structure'])
    out=list(r['expected_source'])
    probe_rows.append(Case(f'ASTSRC-{i}',inp,out))
syn=LowLevelCoordinateSynthesizer()
best,generated=syn.search(probe_rows)
coordinate_train_exact=0.0 if best is None else float(best.exact)
coordinate_program=asdict(best.program) if best is not None else None

# Inspect proven self-invention controllers. They may invent genes only inside
# fixed meta-language families; they expose no generic language-family constructor.
v2_methods=sorted(x for x in dir(YADOEvolutionaryGenomeV2) if not x.startswith('_') and callable(getattr(YADOEvolutionaryGenomeV2,x,None)))
v3_methods=sorted(x for x in dir(YADOEvolutionaryGenomeV3) if not x.startswith('_') and callable(getattr(YADOEvolutionaryGenomeV3,x,None)))
v2_fixed=YADOEvolutionaryGenomeV2.component()
v3_fixed=YADOEvolutionaryGenomeV3.component()
fixed_family_only=(
    'invent_operator_from_examples' in v2_methods
    and 'invent_event_state_operator_from_examples' in v3_methods
    and v2_fixed.get('meta_language',{}).get('component_id')=='LANG-G2-GENERIC-RELATIONAL-STATE-META-V1'
    and v3_fixed.get('meta_language',{}).get('component_id')=='LANG-G2-GENERIC-EVENT-STATE-META-V1'
)

# Give the exact failure lineage to current native meta/evolution/genesis routes.
if DB.exists():DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    pre_meta=k.meta_grammar_snapshot() if hasattr(k,'meta_grammar_snapshot') else None
    goal=k.executive.create_goal(
      objective=str(task['objective']),
      required_capabilities={'SELF_EXTENDING_STRING_TRANSDUCER_META_LANGUAGE_GENESIS_V2':1.0},
      success_criteria={'new_primitive_family':True,'new_meta_language':True,'rollback':True},
    )
    deficits=k.executive.detect_deficits(goal.goal_id)
    native_goal={'goal_id':goal.goal_id,'deficits':[asdict(d) for d in deficits]}
    kernel_outputs={}
    for name in sorted(dir(k)):
        if name.startswith('_') or not any(t in name.lower() for t in ('meta','grammar','language','genesis','evol','construct','synth')):
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
    'role':'YADO_SELF_EXTENDING_META_LANGUAGE_FAILURE',
    'artifact':str(V1.relative_to(REPO)),
    'receipt_sha256':v1.get('receipt_sha256'),
    'status':v1.get('status'),
    'next_required_capability':v1.get('next_required_capability'),
    'checks':v1.get('checks'),
  },
  {
    'role':'YADO_SOURCE_SERIALIZATION_GAP',
    'artifact':str(V6.relative_to(REPO)),
    'receipt_sha256':v6.get('receipt_sha256'),
    'status':v6.get('status'),
    'next_required_capability':v6.get('next_required_capability'),
  },
  {
    'role':'YADO_PRIOR_BOUNDED_SELECTOR_EXPRESSIVENESS_FAILURE',
    'artifact':str(OLD.relative_to(REPO)),
    'receipt_sha256':old.get('receipt_sha256'),
    'example_count':old.get('example_count'),
    'selector_error':old.get('selector_error'),
  },
  {
    'role':'YADO_EXISTING_META_GRAMMAR_EXPRESSIVENESS_PROBE',
    'coordinate_programs_generated':generated,
    'coordinate_train_exact':coordinate_train_exact,
    'selected_program':coordinate_program,
    'host_supplied_coordinate_algebra_is_preexisting':True,
  },
]
controller=core.evolutionary_genome_cls(state['parent'],experience_sources=experience)
controller_outputs={}
for name in sorted(dir(controller)):
    if name.startswith('_') or not any(t in name.lower() for t in ('meta','grammar','language','genesis','evol','construct','synth','gene','mutat')):
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
baseline=canon({'pre_meta':pre_meta,'v2':v2_fixed,'v3':v3_fixed,'parent':state['parent']}).lower()
failure_receipt=str(v1.get('receipt_sha256'))

candidates=[]
identity_keys=('gene_id','language_gene_id','meta_language_id','grammar_extension_id','primitive_family_id','component_id','program_id')
def walk(x,path='root'):
    if isinstance(x,dict):
        local={k:v for k,v in x.items() if k not in ('experience_sources','examples')}
        blob=canon(local).lower()
        ids=[str(x.get(k)) for k in identity_keys if x.get(k) not in (None,'')]
        novel_ids=[z for z in ids if z.lower() not in baseline]
        self_extending=any(t in blob for t in ('self_extend','self-extend','primitive_family','primitive-family','language_family','language-family','meta_language','meta-language'))
        string_semantics=any(t in blob for t in ('string','source_serializer','source-serializer','source_transducer','source-transducer','structure_to_source','structure-to-source'))
        if novel_ids and self_extending and string_semantics:
            candidates.append({
              'path':path,'digest':digest(x),'novel_identities':novel_ids,
              'failure_bound':failure_receipt in canon(x),'keys':sorted(map(str,x.keys()))
            })
        for k,v in x.items():walk(v,path+'.'+str(k))
    elif isinstance(x,list):
        for i,v in enumerate(x):walk(v,path+f'[{i}]')
walk(native_outputs)

child=((controller_outputs.get('evolve_once') or {}).get('child') or {})
failure_retained=failure_receipt in canon(child.get('experience_sources') or [])
selected=candidates[0] if candidates else None

checks={
 'canonical_v5_continuity_active':core.execution_fabric_cls.COMPONENT_ID=='RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V5',
 'v1_failure_consumed':True,
 'v6_serialization_gap_consumed':True,
 'prior_1012_example_failure_consumed':int(old.get('example_count') or 0)>=1000,
 'self_source_memory_at_least_1000':len(examples)>=1000,
 'content_addressed_partitions_present':bool(fit and validation and blind),
 'existing_coordinate_meta_grammar_executed':generated>0,
 'existing_coordinate_algebra_fails_exact_serialization':coordinate_train_exact<1.0,
 'genome_v2_v3_are_fixed_family_inventors':fixed_family_only,
 'native_goal_created':True,
 'native_deficit_detected':bool(native_goal['deficits']),
 'native_meta_evolution_routes_executed':bool(kernel_outputs or controller_outputs),
 'failure_experience_retained':failure_retained,
 'new_self_extending_string_meta_language_created':selected is not None,
 'new_language_has_novel_identity':bool(selected and selected['novel_identities']),
 'new_language_binds_current_failure':bool(selected and selected['failure_bound']),
 'host_string_grammar_used':False,
 'host_primitive_inventory_used':False,
 'host_serializer_used':False,
 'host_ast_compiler_used':False,
 'host_patch_used':False,
 'external_models_used':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'automatic_canonical_promotion':False,
}
positive=(
 'canonical_v5_continuity_active','v1_failure_consumed','v6_serialization_gap_consumed',
 'prior_1012_example_failure_consumed','self_source_memory_at_least_1000',
 'content_addressed_partitions_present','existing_coordinate_meta_grammar_executed',
 'existing_coordinate_algebra_fails_exact_serialization','genome_v2_v3_are_fixed_family_inventors',
 'native_goal_created','native_deficit_detected','native_meta_evolution_routes_executed',
 'failure_experience_retained','new_self_extending_string_meta_language_created',
 'new_language_has_novel_identity','new_language_binds_current_failure','canonical_unchanged'
)
negative=('host_string_grammar_used','host_primitive_inventory_used','host_serializer_used','host_ast_compiler_used','host_patch_used','external_models_used','automatic_canonical_promotion')
passed=all(checks[k] is True for k in positive) and all(checks[k] is False for k in negative)
status='PASS_SHADOW_G2_SELF_EXTENDING_STRING_TRANSDUCER_META_LANGUAGE_GENESIS_V2' if passed else 'WITHHOLD_G2_SELF_EXTENDING_STRING_TRANSDUCER_META_LANGUAGE_GENESIS_V2'

report={
 'schema':'yado.g2.self_extending_string_transducer_meta_language_genesis.v2',
 'status':status,'task':task,
 'parent_v1_receipt':v1.get('receipt_sha256'),
 'parent_v6_receipt':v6.get('receipt_sha256'),
 'prior_serializer_receipt':old.get('receipt_sha256'),
 'example_count':len(examples),
 'split_counts':{'fit':len(fit),'validation':len(validation),'blind':len(blind)},
 'existing_meta_grammar_probe':{
   'component':'LowLevelCoordinateSynthesizer',
   'generated_programs':generated,
   'train_case_count':len(probe_rows),
   'best_train_exact':coordinate_train_exact,
   'selected_program':coordinate_program,
   'preexisting_low_level_algebra':True,
 },
 'fixed_family_genome_evidence':{
   'v2_component':v2_fixed,'v2_methods':v2_methods,
   'v3_component':v3_fixed,'v3_methods':v3_methods,
 },
 'native_goal':native_goal,
 'native_outputs':native_outputs,
 'new_meta_language_candidates':candidates,
 'selected_candidate':selected,
 'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':(
    'STRING_TRANSDUCER_PRIMITIVE_FAMILY_EXECUTION_V3'
    if passed else 'SELF_GENERATED_PRIMITIVE_ALGEBRA_GENESIS_V3'
 ),
 'semantic_boundary':'V2 TESTS WHETHER YADO CAN MOVE FROM GENE-INVENTION INSIDE A FIXED META-LANGUAGE TO INVENTING A NEW STRING/SOURCE META-LANGUAGE FAMILY. THE PREEXISTING LOW-LEVEL COORDINATE META-GRAMMAR IS ALLOWED ONLY AS AN EXPRESSIVENESS PROBE AND ITS ALGEBRA IS NOT CLAIMED AS SELF-GENERATED. HOST PROVIDES NO STRING GRAMMAR, PRIMITIVE INVENTORY, SERIALIZER, AST COMPILER OR PATCH. WITHHOLD LOCALIZES THE NEXT GAP TO SELF-GENERATION OF A NEW PRIMITIVE ALGEBRA.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'example_count':len(examples),'split_counts':report['split_counts'],
 'coordinate_generated':generated,'coordinate_best_train_exact':coordinate_train_exact,
 'new_meta_language_candidate_count':len(candidates),'selected_candidate':selected,
 'next_required_capability':report['next_required_capability'],
 'checks':checks,'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True,default=str))
if not passed:raise SystemExit(2)
