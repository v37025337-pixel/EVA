from __future__ import annotations
from pathlib import Path
import hashlib,inspect,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive

TASK=REPO/'architecture/yado-kernel-native-source-ir-emitter-birth-v1-request.json'
PROCESS=REPO/'candidates/kernel-self-generated/g2-native-source-construction-process-evolution-v2.json'
STUDY=REPO/'experience/yado-native-seedless-source-constructor-python-self-study-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-native-source-ir-emitter-birth-v1.json'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))

task=load(TASK)
process=load(PROCESS)
study=load(STUDY)

if process.get('status')!='PASS_NATIVE_SOURCE_CONSTRUCTION_PROCESS_EVOLUTION_V2':
    raise RuntimeError('PARENT_PROCESS_NOT_PASS')
if process.get('next_required_capability')!='NATIVE_SOURCE_IR_EMITTER_BIRTH_V1':
    raise RuntimeError('UNEXPECTED_PARENT_DEFICIT')
if int(study.get('self_source_construction_history_count') or 0)<4:
    raise RuntimeError('SELF_STUDY_NOT_AVAILABLE')

core=UnifiedYADOCoreV1(REPO)

# Fresh benchmark is behavior-only. No source seed, source template, target file,
# or implementation string is given to any YADO native constructor.
benchmarks=[
  {
    'id':'Q1',
    'train':[{'x':x,'y':0,'expected':x*x+1} for x in (-4,-3,-2,-1,0,1,2,3,4)],
    'blind':[(-7,50),(-5,26),(5,26),(8,65)]
  },
  {
    'id':'Q2',
    'train':[{'x':x,'y':0,'expected':3*x+2} for x in (-5,-3,-1,0,2,4,6)],
    'blind':[(-9,-25),(1,5),(7,23),(11,35)]
  },
  {
    'id':'Q3',
    'train':[{'x':x,'y':0,'expected':x*x*x-x} for x in (-4,-3,-2,-1,0,1,2,3,4)],
    'blind':[(-6,-210),(-5,-120),(5,120),(7,336)]
  },
]

native_ir=[]
for b in benchmarks:
    r=core.synthesize_mathematical_expression(b['train'],max_ops=4,max_states_per_level=40000)
    blind=[]
    for x,expected in b['blind']:
        try:
            got=core.predict_mathematical_expression(r,x,0)
            ok=(got==expected)
        except Exception as e:
            got=type(e).__name__
            ok=False
        blind.append({'x':x,'expected':expected,'got':got,'ok':ok})
    native_ir.append({
      'id':b['id'],
      'native_expression_result':r,
      'fresh_blind':blind,
      'fresh_blind_score':sum(z['ok'] for z in blind)/len(blind),
      'actual_python_source':None,
    })

# Ask the native evolutionary genome for a child under the same no-source-seed condition.
evolution=core.evolve_cognitive_code_genome()
code_gene=((evolution.get('child') or {}).get('chromosomes') or {}).get('CODE') or {}
evolution_source=(
    evolution.get('candidate_source')
    or code_gene.get('candidate_source')
    or code_gene.get('source')
)
evolution_emits_source=isinstance(evolution_source,str) and bool(evolution_source.strip())

# Native capability inventory is evidence only. Nothing is invoked if it requires a
# source seed or an unknown task-specific host argument.
inventory=[]
for name in sorted(dir(core)):
    if not any(tok in name.lower() for tok in ('synth','emit','source','code','program','evol','repair')):
        continue
    obj=getattr(core,name,None)
    if not callable(obj):
        continue
    try:
        sig=str(inspect.signature(obj))
    except Exception:
        sig='UNKNOWN'
    inventory.append({'method':name,'signature':sig})

# Let YADO's own native skill-admission layer decide whether any current native path
# has actually crossed the source-emission boundary.
skills=[]
for row in native_ir:
    ir_ok=row['fresh_blind_score']>=.99
    skills.append({
      'skill_id':'IR_ONLY_'+row['id'],
      'artifact_digest':digest(row),
      'structural_valid':False,  # no source bytes
      'semantic_consistency':row['fresh_blind_score'],
      'fit_baseline':0.0,
      'fit_candidate':row['fresh_blind_score'],
      'heldout_baseline':0.0,
      'heldout_candidate':row['fresh_blind_score'],
      'regression_pass':ir_ok,
      'state_integrity':True,
      'rollback_available':True,
      'metadata':{'boundary':'EXPRESSION_IR_ONLY_NO_PYTHON_SOURCE'}
    })
skills.append({
  'skill_id':'EVOLUTIONARY_CODE_GENE',
  'artifact_digest':digest({'code_gene':code_gene,'run':evolution.get('run_digest')}),
  'structural_valid':evolution_emits_source,
  'semantic_consistency':1.0 if evolution_emits_source else 0.0,
  'fit_baseline':0.0,'fit_candidate':1.0 if evolution_emits_source else 0.0,
  'heldout_baseline':0.0,'heldout_candidate':1.0 if evolution_emits_source else 0.0,
  'regression_pass':bool((evolution.get('fitness') or {}).get('all_regressions_pass')),
  'state_integrity':True,'rollback_available':True,
  'metadata':{'gene_id':code_gene.get('gene_id'),'candidate_source_present':evolution_emits_source}
})

kernel=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_native_ir_emitter_birth_v1.sqlite'))
try:
    selection=kernel.select_evolution_skills(
      skills,max_skills=1,min_semantic_consistency=.95,min_fit_gain=.01,
      max_heldout_drop=0.0,min_heldout_gain=.01
    )
finally:
    kernel.close()

selected_ids=list(selection.get('selected_skill_ids') or [])
actual_source=None
if evolution_emits_source and 'EVOLUTIONARY_CODE_GENE' in selected_ids:
    actual_source=evolution_source

compile_pass=False
fresh_source_execution_pass=False
source_error=None
if isinstance(actual_source,str) and actual_source.strip():
    try:
        code=compile(actual_source,'<yado-native-seedless-source>','exec')
        compile_pass=True
        ns={'__builtins__':{}}
        exec(code,ns,ns)
        # Strictly require an actual callable generated by YADO. We do not provide its
        # function name, argument names, wrapper, or source seed.
        funcs=[v for v in ns.values() if callable(v)]
        fresh_source_execution_pass=bool(funcs)
    except Exception as e:
        source_error=type(e).__name__+':'+str(e)[:600]

ir_transfer=min((x['fresh_blind_score'] for x in native_ir),default=0.0)
checks={
 'parent_native_process_pass':True,
 'python_self_study_available':True,
 'external_coding_models_used':False,
 'host_source_seed_used':False,
 'host_source_template_used':False,
 'host_patch_used':False,
 'host_target_file_selected':False,
 'native_ir_behavior_transfer':ir_transfer>=.99,
 'native_skill_gate_ran':True,
 'candidate_source_produced_by_yado':isinstance(actual_source,str) and bool(actual_source.strip()),
 'candidate_source_compiles':compile_pass,
 'fresh_source_execution_pass':fresh_source_execution_pass,
 'rollback_parent_available':True,
 'canonical_mutation':False,
}

full_pass=all(checks.values())
status='PASS_SHADOW_G2_NATIVE_SOURCE_IR_EMITTER_BIRTH_V1' if full_pass else 'WITHHOLD_G2_NATIVE_SOURCE_IR_EMITTER_BIRTH_V1'
next_cap=None if full_pass else 'NATIVE_SOURCE_IR_EMITTER_META_LANGUAGE_EVOLUTION_V2'

report={
 'schema':'yado.g2.native_source_ir_emitter_birth.v1',
 'status':status,
 'task':task,
 'parent_process_receipt':process.get('receipt_sha256'),
 'study_digest':study.get('study_digest'),
 'native_ir_results':native_ir,
 'native_evolution':{
   'selection':evolution.get('selection'),
   'run_digest':evolution.get('run_digest'),
   'code_gene':code_gene,
   'candidate_source_present':evolution_emits_source,
 },
 'native_capability_inventory':inventory,
 'kernel_skill_selection':selection,
 'selected_skill_ids':selected_ids,
 'candidate_source_sha256':hashlib.sha256(actual_source.encode()).hexdigest() if isinstance(actual_source,str) and actual_source else None,
 'source_error':source_error,
 'checks':checks,
 'next_required_capability':next_cap,
 'canonical_mutation':False,
 'semantic_boundary':'STRICT NATIVE IR-TO-SOURCE MILESTONE. YADO MAY PRODUCE INTERNAL EXPRESSION IR AND EVOLVE CODE GENES, BUT PASS IS FORBIDDEN UNLESS A NATIVE PATH PRODUCES ACTUAL NEW PYTHON SOURCE WITHOUT HOST SOURCE SEED/TEMPLATE/PATCH/TARGET OR EXTERNAL CODING MODEL, AND THAT SOURCE COMPILES AND EXECUTES.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

print(json.dumps({
 'status':status,
 'ir_transfer':ir_transfer,
 'code_gene_id':code_gene.get('gene_id'),
 'evolution_source_present':evolution_emits_source,
 'selected_skill_ids':selected_ids,
 'candidate_source_produced_by_yado':checks['candidate_source_produced_by_yado'],
 'candidate_source_compiles':compile_pass,
 'fresh_source_execution_pass':fresh_source_execution_pass,
 'next_required_capability':next_cap,
 'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True))

if status!='PASS_SHADOW_G2_NATIVE_SOURCE_IR_EMITTER_BIRTH_V1':
    raise SystemExit(2)
