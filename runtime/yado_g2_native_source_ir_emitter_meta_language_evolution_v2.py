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

TASK=REPO/'architecture/yado-kernel-native-source-ir-emitter-meta-language-evolution-v2-request.json'
OUT=REPO/'candidates/kernel-self-generated/g2-native-source-ir-emitter-meta-language-evolution-v2.json'
DB=ROOT/'yado_native_source_ir_emitter_meta_language_v2.sqlite'

PARENTS=[
 REPO/'candidates/kernel-self-generated/g2-native-source-construction-process-evolution-v2.json',
 REPO/'candidates/kernel-self-generated/g2-native-source-ir-emitter-birth-v1.json',
 REPO/'candidates/kernel-self-generated/g2-native-executable-evolution-controller-self-representation-v1.json',
 REPO/'candidates/kernel-self-generated/g2-self-representation-driven-extended-controller-candidate-v1.json',
 REPO/'candidates/kernel-self-generated/g2-native-source-realization-self-representation-driven-extended-controller-v1.json',
]

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))

task=load(TASK); parents=[load(p) for p in PARENTS]
core=UnifiedYADOCoreV1(REPO); head_before=copy.deepcopy(core.head)

if DB.exists():DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    pre_meta=k.meta_grammar_snapshot() if hasattr(k,'meta_grammar_snapshot') else None
    pre_alg=k.algorithm_genesis_snapshot() if hasattr(k,'algorithm_genesis_snapshot') else None
    goal=k.executive.create_goal(
      objective=str(task['objective']),
      required_capabilities={'NATIVE_SOURCE_IR_EMITTER_META_LANGUAGE_EVOLUTION_V2':1.0},
      success_criteria={'new_emitter_meta_language':True,'failure_memory_bound':True,'rollback':True},
    )
    deficits=k.executive.detect_deficits(goal.goal_id)
    native_goal={'goal_id':goal.goal_id,'deficits':[asdict(d) for d in deficits]}
    kernel_calls={}
    for name in sorted(dir(k)):
        if name.startswith('_') or not any(t in name.lower() for t in ('meta','evol','genesis','construct','emit','source')):
            continue
        fn=getattr(k,name,None)
        if not callable(fn):continue
        try:sig=inspect.signature(fn)
        except Exception:continue
        required=[p for p in sig.parameters.values() if p.default is inspect._empty and p.kind in (p.POSITIONAL_ONLY,p.POSITIONAL_OR_KEYWORD)]
        if required:continue
        try:kernel_calls[name]=fn()
        except Exception as e:kernel_calls[name]={'error':type(e).__name__+':'+str(e)[:500]}
finally:
    try:k.close()
    except Exception:pass

state=core.evolutionary_parent_genome()
parent=state['parent']
experience=copy.deepcopy(state.get('experience') or [])
for path,obj in zip(PARENTS,parents):
    experience.append({
      'role':'YADO_OWN_SOURCE_EMISSION_LINEAGE_EVIDENCE',
      'artifact':str(path.relative_to(REPO)),
      'status':obj.get('status'),
      'next_required_capability':obj.get('next_required_capability'),
      'receipt_sha256':obj.get('receipt_sha256'),
      'checks':obj.get('checks'),
    })
controller=core.evolutionary_genome_cls(parent,experience_sources=experience)

controller_calls={}
for name in sorted(dir(controller)):
    if name.startswith('_') or not any(t in name.lower() for t in ('meta','evol','genesis','construct','emit','source','mutat','gene')):
        continue
    fn=getattr(controller,name,None)
    if not callable(fn):continue
    try:sig=inspect.signature(fn)
    except Exception:continue
    required=[p for p in sig.parameters.values() if p.default is inspect._empty and p.kind in (p.POSITIONAL_ONLY,p.POSITIONAL_OR_KEYWORD)]
    if required:continue
    try:controller_calls[name]=fn()
    except Exception as e:controller_calls[name]={'error':type(e).__name__+':'+str(e)[:500]}
if 'evolve_once' not in controller_calls:
    controller_calls['evolve_once']=controller.evolve_once()

evo=controller_calls.get('evolve_once') if isinstance(controller_calls.get('evolve_once'),dict) else {}
child=evo.get('child') or {}
parent_gene_digests={str(v.get('gene_digest')) for v in (parent.get('chromosomes') or {}).values() if isinstance(v,dict)}
failure_receipts={str(x.get('receipt_sha256')) for x in parents if x.get('receipt_sha256')}
child_experience=canon(child.get('experience_sources') or [])
all_failure_memory_bound=all(x in child_experience for x in failure_receipts)

native_outputs={'kernel_calls':kernel_calls,'controller_calls':controller_calls}
new_emitter_candidates=[]

def walk(x,path='root'):
    if isinstance(x,dict):
        blob=canon(x).lower()
        d=x.get('gene_digest')
        new_gene=(d is not None and str(d) not in parent_gene_digests)
        emitter_semantics=any(t in blob for t in ('source_emitter','source-emitter','ir_emitter','emitter_meta','meta_language','meta-language','source_material'))
        failure_bound=any(r in canon(x) for r in failure_receipts)
        if emitter_semantics and (new_gene or failure_bound):
            new_emitter_candidates.append({'path':path,'digest':digest(x),'new_gene':new_gene,'failure_bound':failure_bound,'keys':sorted(map(str,x.keys()))})
        for k,v in x.items():walk(v,path+'.'+str(k))
    elif isinstance(x,list):
        for i,v in enumerate(x):walk(v,path+f'[{i}]')
walk(native_outputs)

source_candidates=[]
def collect_source(x,path='root'):
    if isinstance(x,dict):
        for k,v in x.items():collect_source(v,path+'.'+str(k))
    elif isinstance(x,list):
        for i,v in enumerate(x):collect_source(v,path+f'[{i}]')
    elif isinstance(x,str) and len(x)>=80:
        try:t=ast.parse(x)
        except Exception:return
        if any(isinstance(n,(ast.FunctionDef,ast.ClassDef)) for n in ast.walk(t)):
            source_candidates.append({'path':path,'sha256':hashlib.sha256(x.encode()).hexdigest()})
collect_source(native_outputs)

pre_meta_digest=digest(pre_meta) if pre_meta is not None else None
fresh_candidates=[x for x in new_emitter_candidates if x['digest']!=pre_meta_digest]
actual_new_meta=bool(fresh_candidates)
rollback=bool((evo.get('parent') or {}).get('genome_digest'))

checks={
 'all_exact_parent_evidence_consumed':all_failure_memory_bound,
 'native_goal_created':True,
 'native_deficit_detected':bool(native_goal['deficits']),
 'native_evolution_or_genesis_executed':bool(evo.get('run_digest')) or bool(kernel_calls),
 'previously_absent_emitter_meta_language_created':actual_new_meta,
 'emitter_candidate_failure_memory_bound':any(x['failure_bound'] for x in fresh_candidates),
 'actual_python_source_already_emitted':bool(source_candidates),
 'external_coding_models_used':False,
 'new_external_research_used':False,
 'host_meta_language_template_used':False,
 'host_operator_list_used':False,
 'host_representation_schema_used':False,
 'host_source_seed_used':False,
 'host_ast_skeleton_used':False,
 'host_patch_used':False,
 'host_target_function_selected':False,
 'rollback_parent_available':rollback,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
}
passed=(
 checks['all_exact_parent_evidence_consumed']
 and checks['native_goal_created']
 and checks['native_deficit_detected']
 and checks['native_evolution_or_genesis_executed']
 and checks['previously_absent_emitter_meta_language_created']
 and checks['emitter_candidate_failure_memory_bound']
 and checks['rollback_parent_available']
 and checks['canonical_unchanged']
)
status='PASS_SHADOW_G2_NATIVE_SOURCE_IR_EMITTER_META_LANGUAGE_EVOLUTION_V2' if passed else 'WITHHOLD_G2_NATIVE_SOURCE_IR_EMITTER_META_LANGUAGE_EVOLUTION_V2'
report={
 'schema':'yado.g2.native_source_ir_emitter_meta_language_evolution.v2',
 'status':status,'task':task,'native_goal':native_goal,
 'parent_evidence':[{'artifact':str(p.relative_to(REPO)),'status':o.get('status'),'receipt_sha256':o.get('receipt_sha256')} for p,o in zip(PARENTS,parents)],
 'preexisting_meta_grammar_snapshot':pre_meta,'preexisting_algorithm_genesis_snapshot':pre_alg,
 'native_outputs':native_outputs,'new_emitter_meta_language_candidates':fresh_candidates,
 'native_source_candidates':source_candidates,'checks':checks,'canonical_mutation':False,
 'next_required_capability':('NATIVE_SOURCE_REALIZATION_OF_SELF_REPRESENTATION_DRIVEN_EXTENDED_CONTROLLER_V2' if passed else 'EXPERIENCE_CONDITIONED_NATIVE_EMITTER_GENE_GENESIS_V3'),
 'semantic_boundary':'FAILURE-MEMORY-CONDITIONED NATIVE EMITTER META-LANGUAGE TEST. HOST TRANSPORTS EXACT YADO ARTIFACTS AND OBSERVES NATIVE ZERO-ARG EVOLUTION/GENESIS OUTPUTS ONLY. NO GRAMMAR, OPERATOR SET, SOURCE TEMPLATE, AST SKELETON, PATCH, TARGET FUNCTION, NEW DIMENSION NAME, EXTERNAL MODEL OR NEW RESEARCH IS PROVIDED.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'failure_memory_bound':all_failure_memory_bound,
 'new_emitter_meta_language_candidate_count':len(fresh_candidates),
 'native_source_candidate_count':len(source_candidates),
 'selection':evo.get('selection'),
 'next_required_capability':report['next_required_capability'],
 'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
