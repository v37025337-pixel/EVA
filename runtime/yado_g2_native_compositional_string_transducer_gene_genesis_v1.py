from __future__ import annotations

from pathlib import Path
from dataclasses import asdict
import ast,copy,hashlib,inspect,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive

TASK=REPO/'architecture/yado-kernel-native-compositional-string-transducer-gene-genesis-v1-request.json'
V6=REPO/'candidates/kernel-self-generated/g2-history-derived-semantic-source-edit-serialization-v6.json'
V5=REPO/'candidates/kernel-self-generated/g2-task-conditioned-semantic-source-edit-meta-language-genesis-v5.json'
OLD=REPO/'candidates/kernel-self-generated/g2-native-source-primitive-execution-serialization-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-native-compositional-string-transducer-gene-genesis-v1.json'
DB=ROOT/'yado_native_compositional_string_transducer_gene_genesis_v1.sqlite'

SOURCES=[
 REPO/'runtime/yado_evolutionary_genome_v1.py',
 REPO/'runtime/yado_ambiguity_aware_program_repair_v11.py',
 REPO/'runtime/yado_generic_compile_repair_meta_language_v1.py',
 REPO/'runtime/yado_generic_history_compile_repair_meta_language_v1.py',
]

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def fsha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

task,v6,v5,old=map(load,[TASK,V6,V5,OLD])
if v6.get('status')!='WITHHOLD_G2_HISTORY_DERIVED_SEMANTIC_SOURCE_EDIT_SERIALIZATION_V6':
    raise RuntimeError('V6_WITHHOLD_REQUIRED')
if v6.get('next_required_capability')!='NATIVE_COMPOSITIONAL_STRING_TRANSDUCER_GENE_GENESIS_V1':
    raise RuntimeError('V6_FRONTIER_MISMATCH')
if v5.get('status')!='PASS_SHADOW_G2_TASK_CONDITIONED_SEMANTIC_SOURCE_EDIT_META_LANGUAGE_GENESIS_V5':
    raise RuntimeError('V5_META_GENE_PASS_REQUIRED')
if old.get('status')!='WITHHOLD_G2_NATIVE_SOURCE_PRIMITIVE_EXECUTION_SERIALIZATION_V1':
    raise RuntimeError('PRIOR_SERIALIZER_WITHHOLD_REQUIRED')

core=UnifiedYADOCoreV1(REPO)
head_before=copy.deepcopy(core.head)

# Reconstruct the same YADO-own-source AST/source memory mechanically.
# ast.unparse remains label-oracle only; no grammar/operator/template is exposed.
allowed=(ast.BinOp,ast.BoolOp,ast.Compare,ast.IfExp,ast.Call,ast.Subscript,ast.List,ast.Tuple,ast.Dict,ast.UnaryOp)
rows=[]
source_provenance=[]
for p in SOURCES:
    text=p.read_text(encoding='utf-8')
    tree=ast.parse(text)
    source_provenance.append({'path':str(p.relative_to(REPO)),'sha256':hashlib.sha256(text.encode()).hexdigest()})
    for n in ast.walk(tree):
        if not isinstance(n,allowed):continue
        try:expected=ast.unparse(n)
        except Exception:continue
        if not (3<=len(expected)<=160):continue
        rows.append({
          'ast_structure':ast.dump(n,annotate_fields=True,include_attributes=False),
          'node_type':type(n).__name__,
          'child_count':sum(1 for _ in ast.iter_child_nodes(n)),
          'expected_source':expected,
        })
seen=set();examples=[]
for r in rows:
    k=canon(r)
    if k in seen:continue
    seen.add(k);examples.append(r)
if len(examples)<1000:
    raise RuntimeError('EXPECTED_YADO_AST_MEMORY_NOT_RECONSTRUCTED:'+str(len(examples)))

# Content-addressed partitions; the blind labels are not placed into experience.
def bucket(r):
    return int(hashlib.sha256(canon(r).encode()).hexdigest()[:8],16)%10
fit=[r for r in examples if bucket(r)<6]
validation=[r for r in examples if 6<=bucket(r)<8]
blind=[r for r in examples if bucket(r)>=8]
if min(len(fit),len(validation),len(blind))<50:
    raise RuntimeError('TRANSDUCER_PARTITION_TOO_SMALL')

kernel=None
pre_meta=None
pre_alg=None
native_goal=None
kernel_outputs={}
if DB.exists():DB.unlink()
kernel=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    pre_meta=kernel.meta_grammar_snapshot() if hasattr(kernel,'meta_grammar_snapshot') else None
    pre_alg=kernel.algorithm_genesis_snapshot() if hasattr(kernel,'algorithm_genesis_snapshot') else None
    goal=kernel.executive.create_goal(
      objective=str(task['objective']),
      required_capabilities={'NATIVE_COMPOSITIONAL_STRING_TRANSDUCER_GENE_GENESIS_V1':1.0},
      success_criteria={'new_transducer_gene':True,'new_language_family':True,'rollback':True},
    )
    deficits=kernel.executive.detect_deficits(goal.goal_id)
    native_goal={'goal_id':goal.goal_id,'deficits':[asdict(d) for d in deficits]}
    for name in sorted(dir(kernel)):
        if name.startswith('_') or not any(t in name.lower() for t in ('meta','evol','genesis','construct','synth','grammar','language')):
            continue
        fn=getattr(kernel,name,None)
        if not callable(fn):continue
        try:sig=inspect.signature(fn)
        except Exception:continue
        required=[p for p in sig.parameters.values() if p.default is inspect._empty and p.kind in (p.POSITIONAL_ONLY,p.POSITIONAL_OR_KEYWORD)]
        if required:continue
        try:kernel_outputs[name]=fn()
        except Exception as e:kernel_outputs[name]={'error':type(e).__name__+':'+str(e)[:500]}
finally:
    try:kernel.close()
    except Exception:pass

parent_state=core.evolutionary_parent_genome()
experience=copy.deepcopy(parent_state.get('experience') or [])
experience += [
  {
    'role':'YADO_OWN_STRING_TRANSDUCER_FAMILY_DEFICIT',
    'artifact':str(V6.relative_to(REPO)),
    'status':v6.get('status'),
    'next_required_capability':v6.get('next_required_capability'),
    'receipt_sha256':v6.get('receipt_sha256'),
    'gap_proven':v6.get('gap_proven'),
    'checks':v6.get('checks'),
  },
  {
    'role':'YADO_OWN_SEMANTIC_SOURCE_EDIT_META_LANGUAGE_GENE',
    'artifact':str(V5.relative_to(REPO)),
    'status':v5.get('status'),
    'receipt_sha256':v5.get('receipt_sha256'),
    'meta_language_gene':v5.get('meta_language_gene'),
  },
  {
    'role':'YADO_OWN_PRIOR_SERIALIZER_FAMILY_FAILURE',
    'artifact':str(OLD.relative_to(REPO)),
    'status':old.get('status'),
    'receipt_sha256':old.get('receipt_sha256'),
    'example_count':old.get('example_count'),
    'selector_error':old.get('selector_error'),
    'next_required_capability':old.get('next_required_capability'),
  },
  {
    'role':'YADO_OWN_AST_SOURCE_MEMORY_FIT',
    'source_provenance':source_provenance,
    'example_count':len(fit),
    'examples':fit,
    'blind_labels_exposed':False,
  },
  {
    'role':'YADO_OWN_AST_SOURCE_MEMORY_VALIDATION',
    'example_count':len(validation),
    'examples':validation,
    'blind_labels_exposed':False,
  },
]

controller=core.evolutionary_genome_cls(parent_state['parent'],experience_sources=experience)
controller_outputs={}
for name in sorted(dir(controller)):
    if name.startswith('_') or not any(t in name.lower() for t in ('meta','evol','genesis','construct','synth','grammar','language','gene','mutat')):
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

parent_gene_ids={
 str(v.get('gene_id')) for v in ((parent_state.get('parent') or {}).get('chromosomes') or {}).values()
 if isinstance(v,dict) and v.get('gene_id')
}
baseline_blob=canon({
 'parent_genes':sorted(parent_gene_ids),
 'pre_meta':pre_meta,
 'pre_alg':pre_alg,
 'v5_gene_id':(v5.get('meta_language_gene') or {}).get('gene_id'),
}).lower()

candidates=[]
identity_keys=('gene_id','grammar_extension_id','language_gene_id','transducer_gene_id','component_id','program_id','constructor_id')
def walk(x,path='root'):
    if isinstance(x,dict):
        local={k:v for k,v in x.items() if k not in ('experience_sources','examples','native_outputs')}
        blob=canon(local).lower()
        identities=[str(x.get(k)) for k in identity_keys if x.get(k) not in (None,'')]
        novel_ids=[z for z in identities if z.lower() not in baseline_blob]
        gene_id=str(x.get('gene_id') or '')
        gene_new=bool(gene_id and gene_id not in parent_gene_ids and gene_id!=(v5.get('meta_language_gene') or {}).get('gene_id'))
        semantics=any(t in blob for t in (
          'string_transducer','string-transducer','compositional_string','source_serializer',
          'source-serializer','structure_to_source','structure-to-source','string_emitter',
          'string-emitter','source_transducer','source-transducer'
        ))
        language_semantics=any(t in blob for t in ('language_gene','meta_language','meta-language','grammar','transducer'))
        mechanism_identity=bool(gene_new or novel_ids)
        if semantics and language_semantics and mechanism_identity:
            candidates.append({
              'path':path,'digest':digest(x),'gene_id':gene_id or None,
              'novel_identities':novel_ids,'new_gene_id':gene_new,
              'keys':sorted(map(str,x.keys())),
              'failure_receipt_bound':str(v6.get('receipt_sha256')) in canon(x),
            })
        for k,v in x.items():walk(v,path+'.'+str(k))
    elif isinstance(x,list):
        for i,v in enumerate(x):walk(v,path+f'[{i}]')
walk(native_outputs)

# Do not pretend we can validate held-out serialization unless an executable transducer
# program/gene is actually exposed by the native output.
selected=candidates[0] if candidates else None
new_gene=selected is not None
rollback=bool(((controller_outputs.get('evolve_once') or {}).get('parent') or {}).get('genome_digest'))
experience_blob=canon(((controller_outputs.get('evolve_once') or {}).get('child') or {}).get('experience_sources') or [])
failure_bound=str(v6.get('receipt_sha256')) in experience_blob

checks={
 'canonical_v5_continuity_active':core.execution_fabric_cls.COMPONENT_ID=='RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V5',
 'v6_transducer_deficit_consumed':True,
 'v5_semantic_edit_gene_consumed':bool((v5.get('meta_language_gene') or {}).get('gene_id')),
 'prior_1012_example_failure_consumed':int(old.get('example_count') or 0)>=1000,
 'yado_own_ast_memory_reconstructed':len(examples)>=1000,
 'content_addressed_fit_validation_blind_split':bool(fit and validation and blind),
 'blind_labels_not_exposed_to_native_experience':True,
 'native_goal_created':native_goal is not None,
 'native_deficit_detected':bool((native_goal or {}).get('deficits')),
 'native_meta_evolution_genesis_routes_executed':bool(kernel_outputs or controller_outputs),
 'failure_experience_retained_by_child':failure_bound,
 'new_compositional_string_transducer_gene_created':new_gene,
 'new_transducer_gene_has_novel_identity':bool(selected and (selected['new_gene_id'] or selected['novel_identities'])),
 'new_transducer_gene_binds_current_failure':bool(selected and selected['failure_receipt_bound']),
 'rollback_parent_available':rollback,
 'host_string_grammar_used':False,
 'host_operator_inventory_used':False,
 'host_serializer_used':False,
 'host_ast_compiler_used':False,
 'host_source_template_used':False,
 'host_patch_used':False,
 'external_models_used':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'automatic_canonical_promotion':False,
}
positive=(
 'canonical_v5_continuity_active','v6_transducer_deficit_consumed','v5_semantic_edit_gene_consumed',
 'prior_1012_example_failure_consumed','yado_own_ast_memory_reconstructed',
 'content_addressed_fit_validation_blind_split','blind_labels_not_exposed_to_native_experience',
 'native_goal_created','native_deficit_detected','native_meta_evolution_genesis_routes_executed',
 'failure_experience_retained_by_child','new_compositional_string_transducer_gene_created',
 'new_transducer_gene_has_novel_identity','new_transducer_gene_binds_current_failure',
 'rollback_parent_available','canonical_unchanged'
)
negative=(
 'host_string_grammar_used','host_operator_inventory_used','host_serializer_used','host_ast_compiler_used',
 'host_source_template_used','host_patch_used','external_models_used','automatic_canonical_promotion'
)
passed=all(checks[k] is True for k in positive) and all(checks[k] is False for k in negative)
status='PASS_SHADOW_G2_NATIVE_COMPOSITIONAL_STRING_TRANSDUCER_GENE_GENESIS_V1' if passed else 'WITHHOLD_G2_NATIVE_COMPOSITIONAL_STRING_TRANSDUCER_GENE_GENESIS_V1'

report={
 'schema':'yado.g2.native_compositional_string_transducer_gene_genesis.v1',
 'status':status,'task':task,
 'parent_v6_receipt':v6.get('receipt_sha256'),
 'parent_v5_receipt':v5.get('receipt_sha256'),
 'prior_serializer_receipt':old.get('receipt_sha256'),
 'source_provenance':source_provenance,
 'example_count':len(examples),
 'split_counts':{'fit':len(fit),'validation':len(validation),'blind':len(blind)},
 'preexisting_meta_grammar_snapshot':pre_meta,
 'preexisting_algorithm_genesis_snapshot':pre_alg,
 'native_goal':native_goal,
 'native_outputs':native_outputs,
 'new_transducer_candidates':candidates,
 'selected_candidate':selected,
 'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':(
    'NATIVE_COMPOSITIONAL_STRING_TRANSDUCER_EXECUTION_AND_FRESH_SERIALIZATION_V2'
    if passed else 'SELF_EXTENDING_STRING_TRANSDUCER_META_LANGUAGE_GENESIS_V2'
 ),
 'semantic_boundary':'TASK-CONDITIONED NATIVE LANGUAGE-FAMILY GENESIS PROBE. YADO RECEIVES ITS OWN V6 TRANSDUCER DEFICIT, V5 SEMANTIC-EDIT GENE, PRIOR 1012-EXAMPLE SERIALIZER FAILURE, AND MECHANICALLY RECONSTRUCTED YADO-OWN AST/SOURCE IO MEMORY. BLIND LABELS ARE NOT EXPOSED. HOST PROVIDES NO STRING GRAMMAR, OPERATOR INVENTORY, SERIALIZER, AST COMPILER, SOURCE TEMPLATE OR PATCH. PASS REQUIRES A NEW NATIVE OUTPUT WITH COMPOSITIONAL STRING/SOURCE-TRANSDUCER SEMANTICS AND NOVEL MECHANISM IDENTITY BOUND TO THE CURRENT FAILURE.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'example_count':len(examples),'split_counts':report['split_counts'],
 'native_kernel_route_count':len(kernel_outputs),'native_controller_route_count':len(controller_outputs),
 'new_transducer_candidate_count':len(candidates),'selected_candidate':selected,
 'next_required_capability':report['next_required_capability'],
 'checks':checks,'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True,default=str))
if not passed:raise SystemExit(2)
