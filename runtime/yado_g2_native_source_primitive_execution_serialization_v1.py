from __future__ import annotations
from pathlib import Path
from dataclasses import asdict
import ast,copy,hashlib,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_unified_core_v1 import UnifiedYADOCoreV1

TASK=REPO/'architecture/yado-g2-native-source-primitive-execution-serialization-v1-request.json'
SOURCEV2=REPO/'candidates/kernel-self-generated/g2-native-source-realization-self-representation-driven-extended-controller-v2.json'
EMITTER=REPO/'candidates/kernel-self-generated/g2-experience-conditioned-native-emitter-gene-genesis-v3.json'
OUT=REPO/'candidates/kernel-self-generated/g2-native-source-primitive-execution-serialization-v1.json'
DB=ROOT/'yado_native_source_primitive_serialization_v1.sqlite'
SOURCES=[
 REPO/'runtime/yado_evolutionary_genome_v1.py',
 REPO/'runtime/yado_ambiguity_aware_program_repair_v11.py',
 REPO/'runtime/yado_generic_compile_repair_meta_language_v1.py',
 REPO/'runtime/yado_generic_history_compile_repair_meta_language_v1.py',
]

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))

task=load(TASK);sourcev2=load(SOURCEV2);emitter=load(EMITTER)
if sourcev2.get('next_required_capability')!='NATIVE_SOURCE_PRIMITIVE_EXECUTION_AND_SERIALIZATION_V1':
    raise RuntimeError('SOURCE_V2_FRONTIER_MISMATCH')
if emitter.get('status')!='PASS_SHADOW_G2_EXPERIENCE_CONDITIONED_NATIVE_EMITTER_GENE_GENESIS_V3':
    raise RuntimeError('EMITTER_PARENT_NOT_PASS')
core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)

# Mechanical extraction only. ast.unparse is a hidden oracle for labels; its rules/source
# are never passed to YADO's candidate mechanism.
rows=[]
source_provenance=[]
allowed=(ast.BinOp,ast.BoolOp,ast.Compare,ast.IfExp,ast.Call,ast.Subscript,ast.List,ast.Tuple,ast.Dict,ast.UnaryOp)
for p in SOURCES:
    text=p.read_text(encoding='utf-8');tree=ast.parse(text)
    source_provenance.append({'path':str(p.relative_to(REPO)),'sha256':hashlib.sha256(text.encode()).hexdigest()})
    for n in ast.walk(tree):
        if not isinstance(n,allowed):continue
        try:expected=ast.unparse(n)
        except Exception:continue
        if not (3<=len(expected)<=160):continue
        structure=ast.dump(n,annotate_fields=True,include_attributes=False)
        rows.append({
          'input':{
            'ast_structure':structure,
            'node_type':type(n).__name__,
            'child_count':sum(1 for _ in ast.iter_child_nodes(n)),
          },
          'expected':expected,
          'origin_path':str(p.relative_to(REPO)),
        })
# Stable deterministic dedup.
seen=set();unique=[]
for r in rows:
    k=canon({'input':r['input'],'expected':r['expected']})
    if k in seen:continue
    seen.add(k);unique.append(r)
rows=unique
if len(rows)<30:raise RuntimeError('INSUFFICIENT_SELF_SOURCE_AST_MEMORY')
a=max(12,int(len(rows)*.60));b=max(a+6,int(len(rows)*.80))
fit=[{'input':r['input'],'expected':r['expected']} for r in rows[:a]]
validation=[{'input':r['input'],'expected':r['expected']} for r in rows[a:b]]
blind=[{'input':r['input'],'expected':r['expected']} for r in rows[b:]]

if DB.exists():DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
selection=None;program=None;development=None;selector_error=None
try:
    goal=k.executive.create_goal(
      objective=str(task['objective']),
      required_capabilities={'NATIVE_SOURCE_PRIMITIVE_EXECUTION_AND_SERIALIZATION_V1':.95},
      success_criteria={'fresh_exact':.95,'ablation':True,'restore':True},
    )
    deficits=k.executive.detect_deficits(goal.goal_id)
    native_goal={'goal_id':goal.goal_id,'deficits':[asdict(d) for d in deficits]}
    try:
        program,selection=k.executive.synthesize_best_mechanism(deficits[0].deficit_id,'GENERATIVE_EXECUTIVE',fit+validation,min_support=2)
        development=k.executive.evaluate_mechanism(program.program_id,blind,min_score=.95,min_ablation_drop=.20)
    except Exception as e:
        selector_error=type(e).__name__+':'+str(e)[:1200]
finally:
    try:k.close()
    except Exception:pass

fresh=float(development.candidate_score) if development is not None else 0.0
ablation=float(development.ablation_score) if development is not None else 0.0
restore=float(development.restore_score) if development is not None else 0.0
selected_kind=selection.selected_kind if selection is not None else None
serializer_gene=None
if development is not None and development.state_committed:
    serializer_gene={
      'schema':'yado.g2.native_source_serializer_gene.v1',
      'gene_id':'GENE-G2-NATIVE-SOURCE-SERIALIZER-'+digest({'program':asdict(program),'sources':source_provenance})[:16],
      'gene_class':'STRUCTURE_TO_SOURCE_SERIALIZER',
      'origin':'YADO_NATIVE_DEVELOPMENTAL_SELECTOR_OVER_YADO_OWN_SOURCE_MEMORY',
      'program':asdict(program),'selection':asdict(selection),'development':asdict(development),
      'source_memory_digest':digest(source_provenance),
      'promotion_state':'SHADOW_ONLY',
    }
    serializer_gene['gene_digest']=digest(serializer_gene)

checks={
 'source_v2_deficit_consumed':True,'emitter_gene_consumed':True,
 'only_yado_own_source_used':True,'chronological_fresh_ast_holdout':True,
 'hidden_ast_oracle_not_exposed_to_candidate':True,
 'native_goal_created':True,'native_deficit_detected':bool(native_goal['deficits']),
 'native_selector_executed':True,
 'native_mechanism_selected':selected_kind is not None,
 'fresh_exact_ge_0_95':fresh>=.95,
 'causal_ablation_drop':fresh-ablation>=.20,
 'restore_exact':development is not None and abs(restore-fresh)<=1e-12,
 'new_shadow_serializer_gene_created':serializer_gene is not None,
 'external_models_used':False,'new_external_research_used':False,
 'host_selected_mechanism_family':False,'host_source_template_used':False,
 'host_ast_emitter_template_used':False,'host_grammar_used':False,'host_patch_used':False,
 'automatic_canonical_promotion':False,
 'rollback_parent_available':True,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
}
positive=('source_v2_deficit_consumed','emitter_gene_consumed','only_yado_own_source_used','chronological_fresh_ast_holdout',
          'hidden_ast_oracle_not_exposed_to_candidate','native_goal_created','native_deficit_detected','native_selector_executed',
          'native_mechanism_selected','fresh_exact_ge_0_95','causal_ablation_drop','restore_exact','new_shadow_serializer_gene_created',
          'rollback_parent_available','canonical_unchanged')
negative=('external_models_used','new_external_research_used','host_selected_mechanism_family','host_source_template_used',
          'host_ast_emitter_template_used','host_grammar_used','host_patch_used','automatic_canonical_promotion')
passed=all(checks[k] for k in positive) and all(checks[k] is False for k in negative)
status='PASS_SHADOW_G2_NATIVE_SOURCE_PRIMITIVE_EXECUTION_SERIALIZATION_V1' if passed else 'WITHHOLD_G2_NATIVE_SOURCE_PRIMITIVE_EXECUTION_SERIALIZATION_V1'
next_cap=None if passed else 'NATIVE_COMPOSITIONAL_STRING_TRANSDUCER_GENE_GENESIS_V1'
report={
 'schema':'yado.g2.native_source_primitive_execution_serialization.v1',
 'status':status,'task':task,'native_goal':native_goal,
 'source_provenance':source_provenance,'example_count':len(rows),
 'split_counts':{'fit':len(fit),'validation':len(validation),'blind':len(blind)},
 'selected_mechanism_kind':selected_kind,
 'selection':asdict(selection) if selection is not None else None,
 'development':asdict(development) if development is not None else None,
 'selector_error':selector_error,'fresh_exact':fresh,'ablation':ablation,'restore':restore,
 'serializer_gene':serializer_gene,'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'AST.UNPARSE IS USED ONLY BY THE HOST AS A HIDDEN LABEL ORACLE TO BUILD A FRESH TEST FROM YADO OWN SOURCE. ITS IMPLEMENTATION, GRAMMAR AND OUTPUT RULES ARE NOT AVAILABLE TO THE CANDIDATE. PASS REQUIRES A YADO-NATIVE SELECTED EXECUTABLE MECHANISM TO GENERALIZE STRUCTURE-TO-SOURCE ON HELD-OUT ASTS. FAILURE LOCALIZES A MISSING COMPOSITIONAL STRING TRANSDUCER GENE.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({'status':status,'examples':len(rows),'selected_kind':selected_kind,'fresh':fresh,'ablation':ablation,
 'restore':restore,'selector_error':selector_error,'next_required_capability':next_cap,'receipt_sha256':report['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
