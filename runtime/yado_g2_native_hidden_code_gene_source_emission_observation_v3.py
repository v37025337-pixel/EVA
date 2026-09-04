from __future__ import annotations
from pathlib import Path
import ast,copy,hashlib,inspect,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_evolutionary_genome_v1 import PolynomialReturnRepairGeneV1

TASK=REPO/'architecture/yado-kernel-native-hidden-code-gene-source-emission-observation-v3-request.json'
FAIL=REPO/'candidates/kernel-self-generated/g2-native-source-ir-emitter-meta-language-evolution-v2.json'
OUT=REPO/'candidates/kernel-self-generated/g2-native-hidden-code-gene-source-emission-observation-v3.json'
SRC=REPO/'candidates/g2-self-evolution/yado_native_hidden_code_gene_emission_v3.py'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def sha(s):return hashlib.sha256(s.encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))

task=load(TASK);failure=load(FAIL)
if failure.get('status')!='WITHHOLD_G2_NATIVE_SOURCE_IR_EMITTER_META_LANGUAGE_EVOLUTION_V2':
    raise RuntimeError('CORRECTED_V2_FAILURE_REQUIRED')

core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)
state=core.evolutionary_parent_genome()
experience=copy.deepcopy(state.get('experience') or [])
experience.append({
 'role':'YADO_OWN_CORRECTED_EMITTER_META_LANGUAGE_FAILURE',
 'artifact':str(FAIL.relative_to(REPO)),
 'status':failure.get('status'),
 'next_required_capability':failure.get('next_required_capability'),
 'receipt_sha256':failure.get('receipt_sha256'),
 'checks':failure.get('checks'),
})
controller=core.evolutionary_genome_cls(state['parent'],experience_sources=experience)

captures=[]
orig_bound=PolynomialReturnRepairGeneV1.synthesize
orig_func=PolynomialReturnRepairGeneV1.__dict__['synthesize']

def observe(cls,source,function_name,examples):
    # Instrumentation only: call the original native gene with the exact arguments
    # supplied by YADO itself, return the exact original result unchanged.
    r=orig_bound(source,function_name,examples)
    src=r.get('source') if isinstance(r,dict) else None
    stack=[x.function for x in inspect.stack()[1:12]]
    captures.append({
      'caller_stack':stack,
      'input_source_sha256':sha(source) if isinstance(source,str) else None,
      'function_name_sha256':sha(str(function_name)),
      'example_count':len(examples) if hasattr(examples,'__len__') else None,
      'result_source_sha256':sha(src) if isinstance(src,str) and src else None,
      'result_source':src,
      'result_metadata':{k:v for k,v in (r.items() if isinstance(r,dict) else []) if k!='source'},
      'observer_modified_arguments':False,
      'observer_modified_return':False,
    })
    return r

try:
    PolynomialReturnRepairGeneV1.synthesize=classmethod(observe)
    evolution=controller.evolve_once()
finally:
    PolynomialReturnRepairGeneV1.synthesize=orig_func

failure_bound=str(failure.get('receipt_sha256')) in canon(((evolution.get('child') or {}).get('experience_sources') or []))
native_calls=[x for x in captures if 'evaluate' in x.get('caller_stack',[]) or 'evolve_once' in x.get('caller_stack',[])]
changed=[]
for x in native_calls:
    s=x.get('result_source')
    if not isinstance(s,str) or not s.strip():continue
    if x.get('result_source_sha256')==x.get('input_source_sha256'):continue
    try:
        ast.parse(s);compile(s,'<yado-native-code-gene-emission>','exec')
    except Exception:continue
    changed.append(x)

winner=changed[0] if changed else None
if winner:
    SRC.parent.mkdir(parents=True,exist_ok=True)
    SRC.write_text(winner['result_source'],encoding='utf-8')

fitness=((evolution.get('fitness') or {}).get('child') or {})
checks={
 'corrected_v2_failure_consumed':failure_bound,
 'native_evolve_once_executed':bool(evolution.get('run_digest')),
 'native_code_gene_synthesis_called_internally':bool(native_calls),
 'actual_changed_source_returned_by_native_code_gene':winner is not None,
 'captured_source_compiles':winner is not None,
 'native_code_fresh_fitness_exact':float(fitness.get('CODE') or 0.0)>=1.0,
 'observer_supplied_source_seed':False,
 'observer_supplied_function_name':False,
 'observer_supplied_training_examples':False,
 'observer_supplied_ast_skeleton':False,
 'observer_supplied_patch':False,
 'observer_modified_native_arguments':False,
 'observer_modified_native_return':False,
 'external_coding_models_used':False,
 'new_external_research_used':False,
 'rollback_parent_available':bool((evolution.get('parent') or {}).get('genome_digest')),
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
}
passed=all([
 checks['corrected_v2_failure_consumed'],checks['native_evolve_once_executed'],
 checks['native_code_gene_synthesis_called_internally'],checks['actual_changed_source_returned_by_native_code_gene'],
 checks['captured_source_compiles'],checks['native_code_fresh_fitness_exact'],
 checks['rollback_parent_available'],checks['canonical_unchanged']
])
status='PASS_SHADOW_G2_NATIVE_HIDDEN_CODE_GENE_SOURCE_EMISSION_OBSERVATION_V3' if passed else 'WITHHOLD_G2_NATIVE_HIDDEN_CODE_GENE_SOURCE_EMISSION_OBSERVATION_V3'

safe_captures=[]
for x in captures:
    z=dict(x);z.pop('result_source',None);safe_captures.append(z)
report={
 'schema':'yado.g2.native_hidden_code_gene_source_emission_observation.v3',
 'status':status,'task':task,
 'parent_failure_receipt':failure.get('receipt_sha256'),
 'native_evolution':{
   'run_digest':evolution.get('run_digest'),'selection':evolution.get('selection'),
   'fitness':evolution.get('fitness'),
   'child_genome_digest':((evolution.get('child') or {}).get('genome_digest')),
 },
 'capture_count':len(captures),'native_internal_capture_count':len(native_calls),
 'changed_compiling_source_count':len(changed),
 'selected_source_sha256':winner.get('result_source_sha256') if winner else None,
 'selected_source_artifact':str(SRC.relative_to(REPO)) if winner else None,
 'capture_provenance':safe_captures,
 'checks':checks,'canonical_mutation':False,
 'next_required_capability':('NATIVE_SOURCE_EMISSION_SELF_OBSERVABILITY_AND_CONTROLLER_BINDING_V4' if passed else 'EXPERIENCE_CONDITIONED_NATIVE_EMITTER_GENE_GENESIS_V3'),
 'semantic_boundary':'PASS MEANS YADO CURRENT CODE GENE ALREADY MATERIALIZES CHANGED PYTHON SOURCE INTERNALLY DURING ITS OWN EVOLUTION FITNESS PATH, OBSERVED WITHOUT ALTERING INPUTS OR RETURNS. THIS IS BOUNDED FUNCTION-LEVEL SOURCE EMISSION, NOT YET SELF-REPRESENTATION-DRIVEN CONTROLLER SOURCE REALIZATION.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'capture_count':len(captures),'native_internal_capture_count':len(native_calls),
 'changed_compiling_source_count':len(changed),'selected_source_sha256':report['selected_source_sha256'],
 'native_code_fitness':fitness.get('CODE'),'next_required_capability':report['next_required_capability'],
 'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
