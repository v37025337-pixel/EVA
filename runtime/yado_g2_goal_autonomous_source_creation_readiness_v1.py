from __future__ import annotations
from pathlib import Path
import ast,copy,hashlib,inspect,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_evolutionary_genome_v1 import PolynomialReturnRepairGeneV1
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive

TASK=REPO/'architecture/yado-g2-goal-autonomous-source-creation-readiness-v1-request.json'
OUT=REPO/'candidates/kernel-self-generated/g2-goal-autonomous-source-creation-readiness-v1.json'
EXP=REPO/'experience/yado-goal-autonomous-source-creation-readiness-v1.json'
SRC_DIR=REPO/'candidates/g2-self-evolution'

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def sha(s):return hashlib.sha256(s.encode()).hexdigest()

task=load(TASK)
core=UnifiedYADOCoreV1(REPO)
head_before=copy.deepcopy(core.head)
parent_state=core.evolutionary_parent_genome()

goals=[
 {
  'goal_id':'FRESH-GOAL-A',
  'objective':'Create a new executable mechanism for the supplied fresh input-output relation and validate it without modifying canonical state.',
  'train_examples':[[[-4],-51],[[-3],-20],[[-2],-5],[[-1],0],[[0],1],[[1],4],[[2],15]],
  'fresh_examples':[[[-5],-104],[[3],40],[[4],85]],
 },
 {
  'goal_id':'FRESH-GOAL-B',
  'objective':'Create a different new executable mechanism for this second fresh input-output relation and validate it without modifying canonical state.',
  'train_examples':[[[-4],-9],[[-3],-7],[[-2],-5],[[-1],-3],[[0],-1],[[1],1],[[2],3]],
  'fresh_examples':[[[-5],-11],[[3],5],[[4],7]],
 },
]

def run_goal(goal):
    experience=copy.deepcopy(parent_state.get('experience') or [])
    experience.append({
      'role':'USER_FRESH_GOAL_CONTRACT',
      'goal_id':goal['goal_id'],
      'objective':goal['objective'],
      'train_examples':copy.deepcopy(goal['train_examples']),
      'fresh_examples_digest':digest(goal['fresh_examples']),
      'required_result':'NEW_PYTHON_SOURCE',
    })
    controller=core.evolutionary_genome_cls(parent_state['parent'],experience_sources=experience)
    captures=[]
    orig_bound=PolynomialReturnRepairGeneV1.synthesize
    orig_func=PolynomialReturnRepairGeneV1.__dict__['synthesize']

    def observe(cls,source,function_name,examples):
        r=orig_bound(source,function_name,examples)
        src=r.get('source') if isinstance(r,dict) else None
        captures.append({
          'input_source_sha256':sha(source) if isinstance(source,str) else None,
          'function_name_sha256':sha(str(function_name)),
          'example_digest':digest(examples),
          'example_count':len(examples) if hasattr(examples,'__len__') else None,
          'result_source_sha256':sha(src) if isinstance(src,str) and src else None,
          'result_source':src,
          'metadata':{k:v for k,v in (r.items() if isinstance(r,dict) else []) if k!='source'},
        })
        return r

    try:
        PolynomialReturnRepairGeneV1.synthesize=classmethod(observe)
        evo=controller.evolve_once()
    finally:
        PolynomialReturnRepairGeneV1.synthesize=orig_func

    valid=[]
    for c in captures:
        s=c.get('result_source')
        if not isinstance(s,str) or not s.strip():continue
        try:
            ast.parse(s);compile(s,'<goal-conditioned-source>','exec')
        except Exception:continue
        valid.append(c)
    winner=valid[0] if valid else None
    emitted=winner.get('result_source') if winner else None

    task_conditioning_visible=False
    if winner:
        task_train_digest=digest(goal['train_examples'])
        task_conditioning_visible=(winner.get('example_digest')==task_train_digest)

    fresh_score=None
    if emitted:
        try:
            tree=ast.parse(emitted)
            fn=next((n.name for n in tree.body if isinstance(n,ast.FunctionDef)),None)
            env={'__builtins__':{}}
            exec(compile(tree,'<goal-conditioned-source>','exec'),env,env)
            if fn and callable(env.get(fn)):
                ok=0
                for args,expected in goal['fresh_examples']:
                    try:ok+=env[fn](*args)==expected
                    except Exception:pass
                fresh_score=ok/len(goal['fresh_examples'])
        except Exception:
            fresh_score=0.0
    return {
      'goal_id':goal['goal_id'],
      'goal_train_digest':digest(goal['train_examples']),
      'goal_fresh_digest':digest(goal['fresh_examples']),
      'evolution_run_digest':evo.get('run_digest'),
      'selection':evo.get('selection'),
      'capture_count':len(captures),
      'valid_source_count':len(valid),
      'emitted_source_sha256':sha(emitted) if emitted else None,
      'emitted_source':emitted,
      'native_source_input_sha256':winner.get('input_source_sha256') if winner else None,
      'native_examples_digest':winner.get('example_digest') if winner else None,
      'native_example_count':winner.get('example_count') if winner else None,
      'task_conditioning_visible_in_native_call':task_conditioning_visible,
      'fresh_goal_score':fresh_score,
    }

goal_runs=[run_goal(g) for g in goals]
same_source=bool(goal_runs[0]['emitted_source_sha256']) and goal_runs[0]['emitted_source_sha256']==goal_runs[1]['emitted_source_sha256']
different_goal_digests=goal_runs[0]['goal_train_digest']!=goal_runs[1]['goal_train_digest']

for r in goal_runs:
    if r.get('emitted_source'):
        SRC_DIR.mkdir(parents=True,exist_ok=True)
        p=SRC_DIR/('goal_readiness_'+r['goal_id'].lower().replace('-','_')+'_'+r['emitted_source_sha256'][:12]+'.py')
        p.write_text(r['emitted_source'],encoding='utf-8')
        r['materialized_path']=str(p.relative_to(REPO))
        r['materialized_file_preexisted']=False
        r.pop('emitted_source',None)

# Probe developmental executive interface in a fresh DB.
db=ROOT/'yado_goal_autonomy_readiness_v1.sqlite'
if db.exists():db.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(db))
try:
    ex=k.executive
    methods=[]
    for name in sorted(dir(ex)):
        if name.startswith('_'):continue
        v=getattr(ex,name,None)
        if not callable(v):continue
        try:sig=str(inspect.signature(v))
        except Exception:sig='?'
        if any(t in name.lower() for t in ('goal','deficit','step','run','resume','advance','execute','act','plan','complete','evaluate','synth','commit')):
            methods.append({'name':name,'signature':sig})
    goal=ex.create_goal(
      objective='Autonomously create a task-conditioned new Python mechanism and continue until compile, fresh, ablation and regression are complete.',
      required_capabilities={'TASK_CONDITIONED_NATIVE_SOURCE_EMISSION':1.0,'PERSISTENT_GOAL_LOOP':1.0},
      success_criteria={'new_source':True,'compile':True,'fresh':True,'ablation':True,'regression':True,'autonomous_completion':True},
    )
    deficits=ex.detect_deficits(goal.goal_id)
    deficit_rows=[d.__dict__ if hasattr(d,'__dict__') else str(d) for d in deficits]
finally:
    try:k.close()
    except Exception:pass

native_loop_named_methods=[
 m for m in methods if any(t in m['name'].lower() for t in ('step','resume','advance','run_goal','execute_goal','complete_goal','act_on_goal'))
]
has_native_multistep_loop=bool(native_loop_named_methods)

# Do not count host Python iteration as native goal autonomy.
checks={
 'different_fresh_goals_used':different_goal_digests,
 'native_source_emission_observed_for_both':all(r['valid_source_count']>=1 for r in goal_runs),
 'new_file_materialization_possible_from_native_source':all(bool(r.get('materialized_path')) for r in goal_runs),
 'source_compile_for_both':all(r['valid_source_count']>=1 for r in goal_runs),
 'goal_conditioning_visible_for_both':all(r['task_conditioning_visible_in_native_call'] for r in goal_runs),
 'goal_specific_sources_differ':not same_source,
 'fresh_goal_exact_for_both':all(r['fresh_goal_score']==1.0 for r in goal_runs),
 'native_multistep_goal_loop_present':has_native_multistep_loop,
 'autonomous_goal_deficits_created':len(deficit_rows)>=2,
 'host_supplied_source_seed':False,
 'host_supplied_function_name':False,
 'host_supplied_source_template':False,
 'host_supplied_patch':False,
 'host_used_external_coding_model':False,
 'host_counted_own_iteration_as_native_loop':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
}
positive=[
 'different_fresh_goals_used','native_source_emission_observed_for_both','new_file_materialization_possible_from_native_source',
 'source_compile_for_both','goal_conditioning_visible_for_both','goal_specific_sources_differ','fresh_goal_exact_for_both',
 'native_multistep_goal_loop_present','autonomous_goal_deficits_created','canonical_unchanged'
]
negative=['host_supplied_source_seed','host_supplied_function_name','host_supplied_source_template','host_supplied_patch','host_used_external_coding_model','host_counted_own_iteration_as_native_loop']
passed=all(checks[k] is True for k in positive) and all(checks[k] is False for k in negative)

missing=[]
if not checks['goal_conditioning_visible_for_both'] or not checks['goal_specific_sources_differ'] or not checks['fresh_goal_exact_for_both']:
    missing.append('TASK_CONDITIONED_NATIVE_SOURCE_EMISSION_V1')
if not checks['native_multistep_goal_loop_present']:
    missing.append('NATIVE_PERSISTENT_GOAL_LOOP_CONTROLLER_V1')
status='PASS_SHADOW_G2_GOAL_AUTONOMOUS_SOURCE_CREATION_READINESS_V1' if passed else 'WITHHOLD_G2_GOAL_AUTONOMOUS_SOURCE_CREATION_READINESS_V1'

experience={
 'schema':'yado.g2.goal_autonomous_source_creation_readiness.experience.v1',
 'status':'PASS' if passed else 'WITHHOLD',
 'goal_runs':goal_runs,
 'same_source_for_different_goals':same_source,
 'executive_methods':methods,
 'native_loop_named_methods':native_loop_named_methods,
 'autonomous_goal_deficits':deficit_rows,
 'missing_capabilities':missing,
 'canonical_mutation':False,
 'semantic_boundary':'READINESS EXAM ONLY. NATIVE SOURCE EMISSION IS OBSERVED WITHOUT OBSERVER-SUPPLIED SOURCE/FUNCTION/EXAMPLES, BUT SUCCESS REQUIRES THAT DIFFERENT USER GOALS ACTUALLY CONDITION THE NATIVE SOURCE CALL AND THAT A NATIVE MULTI-STEP GOAL CONTROLLER EXISTS. HOST MATERIALIZATION OF RETURNED SOURCE BYTES DOES NOT COUNT AS NATIVE GOAL AUTONOMY.'
}
experience['experience_digest']=digest(experience)
EXP.parent.mkdir(parents=True,exist_ok=True);EXP.write_text(json.dumps(experience,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

report={
 'schema':'yado.g2.goal_autonomous_source_creation_readiness.v1',
 'status':status,
 'goal_runs':goal_runs,
 'same_source_for_different_goals':same_source,
 'executive_type':type(ex).__module__+'.'+type(ex).__name__,
 'executive_methods':methods,
 'native_loop_named_methods':native_loop_named_methods,
 'autonomous_goal_deficits':deficit_rows,
 'checks':checks,
 'missing_capabilities':missing,
 'canonical_mutation':False,
 'next_required_capability':('G2_GOAL_AUTONOMOUS_SOURCE_CREATION_INTEGRATED_V1' if passed else ('+'.join(missing) if missing else 'READINESS_REPAIR_V2')),
 'semantic_boundary':experience['semantic_boundary'],
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,
 'goal_runs':[{k:v for k,v in r.items() if k!='emitted_source'} for r in goal_runs],
 'same_source_for_different_goals':same_source,
 'native_loop_named_methods':native_loop_named_methods,
 'missing_capabilities':missing,
 'next_required_capability':report['next_required_capability'],
 'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True,default=str))
if not passed:raise SystemExit(2)
