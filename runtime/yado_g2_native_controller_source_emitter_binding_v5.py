from __future__ import annotations
from pathlib import Path
import ast,copy,hashlib,inspect,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_evolutionary_genome_v1 import PolynomialReturnRepairGeneV1

TASK=REPO/'architecture/yado-g2-native-controller-source-emitter-binding-v5-request.json'
CTRL=REPO/'runtime/yado_evolutionary_genome_v1.py'
OUT=REPO/'candidates/kernel-self-generated/g2-native-controller-source-emitter-binding-v5.json'
CAND=REPO/'candidates/g2-self-evolution/yado_evolutionary_genome_native_bound_candidate_v5.py'
PARENTS=[
 REPO/'candidates/kernel-self-generated/g2-native-hidden-code-gene-source-emission-observation-v3.json',
 REPO/'candidates/kernel-self-generated/g2-native-source-emission-self-observability-controller-binding-v4.json',
 REPO/'candidates/kernel-self-generated/g2-native-executable-evolution-controller-self-representation-v1.json',
 REPO/'candidates/kernel-self-generated/g2-self-representation-driven-extended-controller-candidate-v1.json',
 REPO/'candidates/kernel-self-generated/g2-experience-conditioned-native-emitter-gene-genesis-v3.json',
]

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(s):return hashlib.sha256(s.encode()).hexdigest()

task=load(TASK);parents=[load(p) for p in PARENTS]
required_status_prefixes=('PASS_SHADOW','PASS_')
if any(not str(o.get('status','')).startswith(required_status_prefixes) for o in parents):
    raise RuntimeError('PARENT_PASS_EVIDENCE_REQUIRED')

core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)
controller_source=CTRL.read_text(encoding='utf-8');controller_sha=sha(controller_source)

ext=parents[3].get('candidate_controller') or {}
parent_dims=sorted(ext.get('parent_dimensions') or [])
target_dim=str(ext.get('yado_selected_new_dimension') or parents[3].get('selected_target') or '')
expected_dims=sorted(ext.get('candidate_dimensions') or [])
if not target_dim:raise RuntimeError('YADO_EXTENDED_DIMENSION_MISSING')

state=core.evolutionary_parent_genome()
experience=copy.deepcopy(state.get('experience') or [])
for p,o in zip(PARENTS,parents):
    experience.append({
      'role':'YADO_CONTROLLER_SOURCE_BINDING_PARENT_EVIDENCE',
      'artifact':str(p.relative_to(REPO)),'status':o.get('status'),
      'receipt_sha256':o.get('receipt_sha256'),'next_required_capability':o.get('next_required_capability'),
    })
experience.append({
 'role':'YADO_CURRENT_EVOLUTION_CONTROLLER_SELF_SOURCE_IDENTITY',
 'path':str(CTRL.relative_to(REPO)),'source_sha256':controller_sha,
 'parent_dimensions':parent_dims,'yado_selected_extended_dimension':target_dim,'expected_dimensions':expected_dims,
})
controller=core.evolutionary_genome_cls(state['parent'],experience_sources=experience)

captures=[]
orig_bound=PolynomialReturnRepairGeneV1.synthesize
orig_func=PolynomialReturnRepairGeneV1.__dict__['synthesize']
def observe(cls,source,function_name,examples):
    result=orig_bound(source,function_name,examples)
    out=result.get('source') if isinstance(result,dict) else None
    captures.append({
      'input_source_sha256':sha(source) if isinstance(source,str) else None,
      'input_is_current_controller_source':isinstance(source,str) and sha(source)==controller_sha,
      'function_name_sha256':sha(str(function_name)),
      'example_count':len(examples) if hasattr(examples,'__len__') else None,
      'result_source_sha256':sha(out) if isinstance(out,str) and out else None,
      'result_source':out,
      'result_changed_from_input':isinstance(out,str) and isinstance(source,str) and sha(out)!=sha(source),
      'caller_stack':[x.function for x in inspect.stack()[1:12]],
      'observer_modified_arguments':False,'observer_modified_return':False,
    })
    return result
try:
    PolynomialReturnRepairGeneV1.synthesize=classmethod(observe)
    evolution=controller.evolve_once()
finally:
    PolynomialReturnRepairGeneV1.synthesize=orig_func

child_exp=canon(((evolution.get('child') or {}).get('experience_sources') or []))
receipts=[str(o.get('receipt_sha256')) for o in parents if o.get('receipt_sha256')]
parents_consumed=all(r in child_exp for r in receipts)

native=[x for x in captures if 'evaluate' in x.get('caller_stack',[]) or 'evolve_once' in x.get('caller_stack',[])]
bound=[x for x in native if x.get('input_is_current_controller_source') and x.get('result_changed_from_input') and x.get('result_source')]
winner=bound[0] if bound else None
compile_pass=False;candidate_dims=[];preserves=False;extends=False;source_error=None
if winner:
    try:
        src=winner['result_source'];compile(src,'<yado-controller-v5>','exec');compile_pass=True
        ns={'__name__':'_yado_controller_v5_'};exec(compile(src,'<yado-controller-v5>','exec'),ns,ns)
        C=ns.get('YADOEvolutionaryGenomeV1')
        if C is not None and hasattr(C,'component'):
            candidate_dims=sorted(C.component().get('chromosomes') or [])
            preserves=set(parent_dims)<=set(candidate_dims)
            extends=preserves and target_dim in candidate_dims and len(candidate_dims)>len(parent_dims)
        CAND.parent.mkdir(parents=True,exist_ok=True);CAND.write_text(src,encoding='utf-8')
    except Exception as e:source_error=type(e).__name__+':'+str(e)[:800]

checks={
 'all_parent_receipts_consumed':parents_consumed,
 'native_evolve_once_executed':bool(evolution.get('run_digest')),
 'native_code_source_emission_observed':bool(native),
 'native_emission_targeted_current_controller_source':bool(bound),
 'changed_controller_source_returned':winner is not None,
 'candidate_source_compiles':compile_pass,
 'parent_dimensions_preserved':preserves,
 'yado_selected_extended_dimension_present':extends,
 'observer_modified_arguments':False,'observer_modified_return':False,
 'external_models_used':False,'new_external_research_used':False,
 'host_source_seed_used':False,'host_target_function_selected':False,'host_patch_used':False,'host_ast_skeleton_used':False,
 'rollback_parent_available':bool((evolution.get('parent') or {}).get('genome_digest')),
 'automatic_canonical_promotion':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
}
positive=('all_parent_receipts_consumed','native_evolve_once_executed','native_code_source_emission_observed',
          'native_emission_targeted_current_controller_source','changed_controller_source_returned','candidate_source_compiles',
          'parent_dimensions_preserved','yado_selected_extended_dimension_present','rollback_parent_available','canonical_unchanged')
negative=('observer_modified_arguments','observer_modified_return','external_models_used','new_external_research_used',
          'host_source_seed_used','host_target_function_selected','host_patch_used','host_ast_skeleton_used','automatic_canonical_promotion')
passed=all(checks[k] for k in positive) and all(checks[k] is False for k in negative)
status='PASS_SHADOW_G2_NATIVE_CONTROLLER_SOURCE_EMITTER_BINDING_V5' if passed else 'WITHHOLD_G2_NATIVE_CONTROLLER_SOURCE_EMITTER_BINDING_V5'
next_cap=None if passed else 'NATIVE_CONTROLLER_STRUCTURAL_SOURCE_MUTATION_GENE_V1'
safe=[]
for x in captures:
    z=dict(x);z.pop('result_source',None);safe.append(z)
report={
 'schema':'yado.g2.native_controller_source_emitter_binding.v5','status':status,'task':task,
 'parent_evidence':[{'artifact':str(p.relative_to(REPO)),'status':o.get('status'),'receipt_sha256':o.get('receipt_sha256')} for p,o in zip(PARENTS,parents)],
 'controller_source_sha256':controller_sha,'parent_dimensions':parent_dims,'yado_selected_extended_dimension':target_dim,
 'expected_extended_dimensions':expected_dims,'native_evolution':{
   'run_digest':evolution.get('run_digest'),'selection':evolution.get('selection'),
   'child_genome_digest':((evolution.get('child') or {}).get('genome_digest')),
 },
 'capture_count':len(captures),'native_internal_capture_count':len(native),'controller_bound_capture_count':len(bound),
 'capture_provenance':safe,'candidate_source_sha256':winner.get('result_source_sha256') if winner else None,
 'candidate_artifact_path':str(CAND.relative_to(REPO)) if winner else None,'candidate_dimensions':candidate_dims,'source_error':source_error,
 'checks':checks,'canonical_mutation':False,'promotion_applied':False,'next_required_capability':next_cap,
 'semantic_boundary':'V5 DOES NOT SUPPLY CONTROLLER SOURCE AS A SOURCE-SEED ARGUMENT TO THE NATIVE CODE GENE. IT ONLY RECORDS THE CURRENT SELF-SOURCE IDENTITY IN YADO EXPERIENCE AND OBSERVES THE ARGUMENTS YADO ITSELF CHOOSES DURING EVOLVE_ONCE. PASS REQUIRES YADO TO TARGET ITS OWN CONTROLLER SOURCE NATIVELY AND RETURN A CHANGED COMPILING EXTENDED CONTROLLER.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({'status':status,'native_internal_capture_count':len(native),'controller_bound_capture_count':len(bound),
 'candidate_source_sha256':report['candidate_source_sha256'],'next_required_capability':next_cap,'receipt_sha256':report['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
