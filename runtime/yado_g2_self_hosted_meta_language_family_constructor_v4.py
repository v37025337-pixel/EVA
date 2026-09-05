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
from yado_evolutionary_genome_v1 import PolynomialReturnRepairGeneV1

V3=REPO/'candidates/kernel-self-generated/g2-self-generated-primitive-algebra-genesis-v3.json'
V2=REPO/'candidates/kernel-self-generated/g2-self-extending-string-transducer-meta-language-genesis-v2.json'
PROCESS=REPO/'candidates/kernel-self-generated/g2-native-source-construction-process-evolution-v2.json'
RESEARCH=REPO/'candidates/kernel-self-generated/g2-native-seedless-source-constructor-research-v1.json'
HIDDEN=REPO/'candidates/kernel-self-generated/g2-native-hidden-code-gene-source-emission-observation-v3.json'
META_REPAIR=REPO/'candidates/kernel-self-generated/g2-native-meta-grammar-compile-repair-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-self-hosted-meta-language-family-constructor-v4.json'
CAND=REPO/'candidates/g2-self-evolution/yado_self_hosted_meta_language_family_constructor_v4.py'
DB=ROOT/'yado_self_hosted_meta_language_family_constructor_v4.sqlite'

FAMILY_SOURCES=[
 REPO/'runtime/yado_generic_compile_repair_meta_language_v1.py',
 REPO/'runtime/yado_generic_history_compile_repair_meta_language_v1.py',
 REPO/'runtime/yado_generic_relational_meta_language_v1.py',
 REPO/'runtime/yado_generic_event_state_meta_language_v1.py',
 REPO/'runtime/yado_generic_weighted_state_meta_language_v1.py',
]

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def fsha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def shas(s):return hashlib.sha256(s.encode()).hexdigest()

v3,v2,process,research,hidden,meta_repair=map(load,[V3,V2,PROCESS,RESEARCH,HIDDEN,META_REPAIR])
if v3.get('status')!='WITHHOLD_G2_SELF_GENERATED_PRIMITIVE_ALGEBRA_GENESIS_V3':
    raise RuntimeError('V3_PRIMITIVE_ALGEBRA_WITHHOLD_REQUIRED')
if v3.get('next_required_capability')!='SELF_HOSTED_META_LANGUAGE_FAMILY_CONSTRUCTOR_V4':
    raise RuntimeError('V3_FRONTIER_MISMATCH')
if process.get('status')!='PASS_NATIVE_SOURCE_CONSTRUCTION_PROCESS_EVOLUTION_V2':
    raise RuntimeError('NATIVE_SOURCE_PROCESS_PASS_REQUIRED')
if hidden.get('status')!='PASS_SHADOW_G2_NATIVE_HIDDEN_CODE_GENE_SOURCE_EMISSION_OBSERVATION_V3':
    raise RuntimeError('HIDDEN_NATIVE_SOURCE_EMISSION_PASS_REQUIRED')

core=UnifiedYADOCoreV1(REPO)
head_before=copy.deepcopy(core.head)
if core.execution_fabric_cls.COMPONENT_ID!='RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V5':
    raise RuntimeError('CANONICAL_V5_CONTINUITY_REQUIRED')

family_history=[]
known_source_hashes=set()
for p in FAMILY_SOURCES:
    src=p.read_text(encoding='utf-8')
    known_source_hashes.add(shas(src))
    tree=ast.parse(src)
    classes=[n.name for n in tree.body if isinstance(n,ast.ClassDef)]
    methods=sorted({n.name for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and not n.name.startswith('_')})
    family_history.append({
      'path':str(p.relative_to(REPO)),'sha256':shas(src),
      'classes':classes,'public_methods':methods,
    })

# Native goal: no constructor skeleton, implementation, target source or source template.
if DB.exists():DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    goal=k.executive.create_goal(
      objective='Create a self-hosted meta-language family constructor able to create a new primitive/interpreter family when existing meta-languages cannot express the current deficit',
      required_capabilities={'SELF_HOSTED_META_LANGUAGE_FAMILY_CONSTRUCTOR_V4':1.0},
      success_criteria={'new_python_source':True,'new_family_constructor_identity':True,'rollback':True},
    )
    deficits=k.executive.detect_deficits(goal.goal_id)
    native_goal={'goal_id':goal.goal_id,'deficits':[asdict(d) for d in deficits]}
    kernel_outputs={}
    for name in sorted(dir(k)):
        if name.startswith('_') or not any(t in name.lower() for t in ('meta','grammar','language','genesis','evol','construct','synth','primitive','source','code')):
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
  'role':'YADO_CURRENT_SELF_HOSTED_FAMILY_CONSTRUCTOR_DEFICIT',
  'artifact':str(V3.relative_to(REPO)),'receipt_sha256':v3.get('receipt_sha256'),
  'status':v3.get('status'),'next_required_capability':v3.get('next_required_capability'),
  'architecture_boundary':v3.get('architecture_boundary'),
 },
 {
  'role':'YADO_PREVIOUS_STRING_META_LANGUAGE_FAILURE',
  'artifact':str(V2.relative_to(REPO)),'receipt_sha256':v2.get('receipt_sha256'),
  'status':v2.get('status'),
 },
 {
  'role':'YADO_NATIVE_SOURCE_CONSTRUCTION_PROCESS',
  'artifact':str(PROCESS.relative_to(REPO)),'receipt_sha256':process.get('receipt_sha256'),
  'status':process.get('status'),'learned_process':process.get('learned_process'),
 },
 {
  'role':'YADO_NATIVE_SOURCE_RESEARCH_HISTORY',
  'artifact':str(RESEARCH.relative_to(REPO)),'receipt_sha256':research.get('receipt_sha256'),
  'status':research.get('status'),'checks':research.get('checks'),
 },
 {
  'role':'YADO_PROVEN_INTERNAL_SOURCE_EMISSION',
  'artifact':str(HIDDEN.relative_to(REPO)),'receipt_sha256':hidden.get('receipt_sha256'),
  'status':hidden.get('status'),'selected_source_sha256':hidden.get('selected_source_sha256'),
 },
 {
  'role':'YADO_NATIVE_META_GRAMMAR_REPAIR_HISTORY',
  'artifact':str(META_REPAIR.relative_to(REPO)),'receipt_sha256':meta_repair.get('receipt_sha256'),
  'status':meta_repair.get('status'),'invented_gene':meta_repair.get('invented_gene'),
 },
 {
  'role':'YADO_EXISTING_META_LANGUAGE_SOURCE_HISTORY',
  'families':family_history,
  'host_constructor_source_supplied':False,
  'host_constructor_skeleton_supplied':False,
 }
]

controller=core.evolutionary_genome_cls(state['parent'],experience_sources=experience)
captures=[]
orig=PolynomialReturnRepairGeneV1.__dict__['synthesize']
orig_bound=PolynomialReturnRepairGeneV1.synthesize
def observe(cls,source,function_name,examples):
    r=orig_bound(source,function_name,examples)
    out=r.get('source') if isinstance(r,dict) else None
    captures.append({
      'caller_stack':[x.function for x in inspect.stack()[1:12]],
      'input_source_sha256':shas(source) if isinstance(source,str) else None,
      'result_source_sha256':shas(out) if isinstance(out,str) and out else None,
      'result_source':out,
      'observer_modified_arguments':False,'observer_modified_return':False,
    })
    return r

controller_outputs={}
try:
    PolynomialReturnRepairGeneV1.synthesize=classmethod(observe)
    # Only native zero-argument evolution/genesis routes; no host semantic arguments.
    for name in sorted(dir(controller)):
        if name.startswith('_') or not any(t in name.lower() for t in ('meta','grammar','language','genesis','evol','construct','synth','primitive','source','gene','mutat')):
            continue
        fn=getattr(controller,name,None)
        if not callable(fn) or name=='evolve_once':continue
        try:sig=inspect.signature(fn)
        except Exception:continue
        required=[p for p in sig.parameters.values() if p.default is inspect._empty and p.kind in (p.POSITIONAL_ONLY,p.POSITIONAL_OR_KEYWORD)]
        if required:continue
        try:controller_outputs[name]=fn()
        except Exception as e:controller_outputs[name]={'error':type(e).__name__+':'+str(e)[:500]}
    try:controller_outputs['evolve_once']=controller.evolve_once()
    except Exception as e:controller_outputs['evolve_once']={'error':type(e).__name__+':'+str(e)[:500]}
finally:
    PolynomialReturnRepairGeneV1.synthesize=orig

native_outputs={'kernel':kernel_outputs,'controller':controller_outputs}
failure_receipt=str(v3.get('receipt_sha256'))
child=((controller_outputs.get('evolve_once') or {}).get('child') or {})
failure_retained=failure_receipt in canon(child.get('experience_sources') or [])
rollback=bool(((controller_outputs.get('evolve_once') or {}).get('parent') or {}).get('genome_digest'))

source_candidates=[]
def inspect_source(s,origin):
    if not isinstance(s,str) or len(s)<80 or len(s)>300000:return
    h=shas(s)
    if h in known_source_hashes:return
    try:
        tree=ast.parse(s);compile(s,'<yado-self-hosted-family-constructor>','exec')
    except Exception:return
    classes=[n for n in tree.body if isinstance(n,ast.ClassDef)]
    funcs=[n.name for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
    text_low=s.lower()
    semantic_hits=sum(tok in text_low for tok in ('meta_language','meta-language','primitive','family','constructor','interpreter','synth'))
    if not classes or semantic_hits<2:return
    source_candidates.append({
      'origin':origin,'sha256':h,'source':s,
      'class_names':[n.name for n in classes],
      'function_names':sorted(set(funcs)),
      'semantic_hit_count':semantic_hits,
    })

def walk(obj,path='root'):
    if isinstance(obj,dict):
        for k,v in obj.items():walk(v,path+'.'+str(k))
    elif isinstance(obj,list):
        for i,v in enumerate(obj):walk(v,path+f'[{i}]')
    elif isinstance(obj,str):
        inspect_source(obj,path)
walk(native_outputs)
for i,c in enumerate(captures):
    inspect_source(c.get('result_source'),f'capture[{i}]')

# Deduplicate candidate source.
uniq={}
for c in source_candidates:uniq.setdefault(c['sha256'],c)
source_candidates=list(uniq.values())
winner=source_candidates[0] if source_candidates else None
if winner:
    CAND.parent.mkdir(parents=True,exist_ok=True)
    CAND.write_text(winner['source'],encoding='utf-8')

native_calls=[x for x in captures if 'evolve_once' in x.get('caller_stack',[]) or 'evaluate' in x.get('caller_stack',[])]
old_polynomial_only=bool(native_calls) and winner is None
checks={
 'canonical_v5_continuity_active':True,
 'v3_constructor_deficit_consumed':True,
 'family_history_count_ge_5':len(family_history)>=5,
 'native_source_process_history_consumed':process.get('status')=='PASS_NATIVE_SOURCE_CONSTRUCTION_PROCESS_EVOLUTION_V2',
 'native_hidden_source_emission_history_consumed':hidden.get('status')=='PASS_SHADOW_G2_NATIVE_HIDDEN_CODE_GENE_SOURCE_EMISSION_OBSERVATION_V3',
 'native_goal_created':True,
 'native_deficit_detected':bool(native_goal['deficits']),
 'native_meta_source_evolution_routes_executed':bool(kernel_outputs or controller_outputs),
 'current_failure_retained_by_child':failure_retained,
 'native_code_source_emission_observed':bool(native_calls),
 'new_target_semantic_python_source_created':winner is not None,
 'new_source_compiles':winner is not None,
 'new_source_identity_not_existing_family':winner is not None and winner['sha256'] not in known_source_hashes,
 'new_source_has_family_constructor_semantics':winner is not None and winner['semantic_hit_count']>=2,
 'rollback_parent_available':rollback,
 'host_constructor_source_supplied':False,
 'host_constructor_skeleton_supplied':False,
 'host_target_patch_supplied':False,
 'host_source_template_supplied':False,
 'external_models_used':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'automatic_canonical_promotion':False,
}
positive=(
 'canonical_v5_continuity_active','v3_constructor_deficit_consumed','family_history_count_ge_5',
 'native_source_process_history_consumed','native_hidden_source_emission_history_consumed',
 'native_goal_created','native_deficit_detected','native_meta_source_evolution_routes_executed',
 'current_failure_retained_by_child','native_code_source_emission_observed',
 'new_target_semantic_python_source_created','new_source_compiles',
 'new_source_identity_not_existing_family','new_source_has_family_constructor_semantics',
 'rollback_parent_available','canonical_unchanged'
)
negative=(
 'host_constructor_source_supplied','host_constructor_skeleton_supplied','host_target_patch_supplied',
 'host_source_template_supplied','external_models_used','automatic_canonical_promotion'
)
passed=all(checks[k] is True for k in positive) and all(checks[k] is False for k in negative)
status='PASS_SHADOW_G2_SELF_HOSTED_META_LANGUAGE_FAMILY_CONSTRUCTOR_V4' if passed else 'WITHHOLD_G2_SELF_HOSTED_META_LANGUAGE_FAMILY_CONSTRUCTOR_V4'
next_cap=(
 'SELF_HOSTED_META_LANGUAGE_FAMILY_CONSTRUCTOR_APPLICATION_V5'
 if passed else 'TARGET_SEMANTIC_SOURCE_CONSTRUCTOR_GENESIS_V5'
)

safe_caps=[]
for c in captures:
    z=dict(c);z.pop('result_source',None);safe_caps.append(z)
report={
 'schema':'yado.g2.self_hosted_meta_language_family_constructor.v4',
 'status':status,
 'parent_v3_receipt':v3.get('receipt_sha256'),
 'native_goal':native_goal,
 'family_history':family_history,
 'native_outputs':native_outputs,
 'native_source_capture_provenance':safe_caps,
 'native_internal_source_call_count':len(native_calls),
 'old_polynomial_source_path_only':old_polynomial_only,
 'candidate_source_count':len(source_candidates),
 'selected_source_candidate':None if winner is None else {k:v for k,v in winner.items() if k!='source'},
 'candidate_source_artifact':str(CAND.relative_to(REPO)) if winner else None,
 'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'GOAL-ONLY SELF-HOSTED FAMILY-CONSTRUCTOR SOURCE MILESTONE. YADO RECEIVES ITS OWN CURRENT DEFICIT, EXISTING META-LANGUAGE SOURCE HISTORY, NATIVE SOURCE-CONSTRUCTION PROCESS, SOURCE-RESEARCH HISTORY AND PROVEN INTERNAL CODE-SOURCE EMISSION. HOST PROVIDES NO CONSTRUCTOR SOURCE, SKELETON, PATCH OR TEMPLATE. PASS REQUIRES NATIVE YADO OUTPUT TO MATERIALIZE NEW COMPILING PYTHON SOURCE WITH META-LANGUAGE/FAMILY-CONSTRUCTION SEMANTICS AND NEW SOURCE IDENTITY. A REPLAY OF THE FIXED POLYNOMIAL CODE GENE DOES NOT COUNT.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'native_internal_source_call_count':len(native_calls),
 'candidate_source_count':len(source_candidates),
 'selected_source_candidate':report['selected_source_candidate'],
 'old_polynomial_source_path_only':old_polynomial_only,
 'next_required_capability':next_cap,
 'checks':checks,'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True,default=str))
if not passed:raise SystemExit(2)
