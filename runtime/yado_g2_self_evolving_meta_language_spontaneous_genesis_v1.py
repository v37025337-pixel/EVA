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

TASK=REPO/'architecture/yado-kernel-self-evolving-meta-language-spontaneous-genesis-v1-request.json'
OUT=REPO/'candidates/kernel-self-generated/g2-self-evolving-meta-language-spontaneous-genesis-v1.json'
DB=ROOT/'yado_self_evolving_meta_language_spontaneous_genesis_v1.sqlite'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))

def py_source_candidate(s):
    if not isinstance(s,str) or len(s)<8 or len(s)>200000: return False
    try:
        t=ast.parse(s)
    except Exception:
        return False
    return any(isinstance(n,(ast.FunctionDef,ast.ClassDef)) for n in ast.walk(t))

def walk(obj,path='root'):
    out=[]
    if isinstance(obj,dict):
        out.append((path,obj))
        for k,v in obj.items(): out.extend(walk(v,path+'.'+str(k)))
    elif isinstance(obj,list):
        for i,v in enumerate(obj): out.extend(walk(v,path+f'[{i}]'))
    return out

task=load(TASK)
core=UnifiedYADOCoreV1(REPO)
head_before=copy.deepcopy(core.head)

if DB.exists(): DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    pre_meta = k.meta_grammar_snapshot() if hasattr(k,'meta_grammar_snapshot') else None
    pre_alg = k.algorithm_genesis_snapshot() if hasattr(k,'algorithm_genesis_snapshot') else None

    # The host gives only the capability goal. It does not provide a grammar,
    # operator inventory, representation schema, source seed, target file, or patch.
    goal=k.executive.create_goal(
      objective=str(task.get('task')),
      required_capabilities={'SELF_EVOLVING_META_LANGUAGE_V1':1.0},
      success_criteria={'self_extension':True,'source_materialization':True,'fresh_execution':True,'rollback':True},
    )
    deficits=k.executive.detect_deficits(goal.goal_id)
    goal_state={'goal_id':goal.goal_id,'deficits':[asdict(x) for x in deficits]}

    # Discover only zero-argument native introspection/evolution entrypoints.
    # We invoke no task-specific constructor and feed no examples/templates.
    zero_arg_methods=[]
    zero_arg_results={}
    for name in sorted(dir(k)):
        if not any(tok in name.lower() for tok in ('meta','evol','genesis','construct','synth')):
            continue
        fn=getattr(k,name,None)
        if not callable(fn) or name.startswith('_'): continue
        try: sig=inspect.signature(fn)
        except Exception: continue
        required=[p for p in sig.parameters.values()
                  if p.default is inspect._empty and p.kind in (p.POSITIONAL_ONLY,p.POSITIONAL_OR_KEYWORD)]
        if required: continue
        zero_arg_methods.append(name)
        try:
            zero_arg_results[name]=fn()
        except Exception as e:
            zero_arg_results[name]={'error':type(e).__name__+':'+str(e)[:500]}
finally:
    try:k.close()
    except Exception:pass

# One native spontaneous evolution pass through the active unified core.
evolution=core.evolve_cognitive_code_genome()

native_outputs={'zero_arg_native_results':zero_arg_results,'unified_core_evolution':evolution}
dict_nodes=walk(native_outputs)

meta_candidates=[]
for path,d in dict_nodes:
    keys={str(x).lower() for x in d.keys()}
    blob=' '.join(keys)+' '+canon(d)[:8000].lower()
    if any(tok in blob for tok in ('meta_language','meta-language','meta_grammar','grammar_extension',
                                    'extension_policy','operator_registry','self_extension','self-evolving')):
        meta_candidates.append({'path':path,'digest':digest(d),'keys':sorted(d.keys())})

source_candidates=[]
def collect_strings(obj,path='root'):
    if isinstance(obj,dict):
        for k,v in obj.items(): collect_strings(v,path+'.'+str(k))
    elif isinstance(obj,list):
        for i,v in enumerate(obj): collect_strings(v,path+f'[{i}]')
    elif isinstance(obj,str) and py_source_candidate(obj):
        source_candidates.append({'path':path,'sha256':hashlib.sha256(obj.encode()).hexdigest(),'source':obj})
collect_strings(native_outputs)

# A new language must be more than the already-existing RC6 meta-grammar snapshot.
pre_digest=digest(pre_meta) if pre_meta is not None else None
new_meta=[x for x in meta_candidates if x['digest']!=pre_digest]
actual_source=source_candidates[0]['source'] if source_candidates else None
source_compiles=False
source_executes=False
if actual_source:
    try:
        compile(actual_source,'<yado-spontaneous-meta-language-source>','exec')
        source_compiles=True
    except Exception:
        source_compiles=False

# We do not execute arbitrary candidate source unless it is produced and structurally simple;
# no actual source is expected unless YADO has a native emitter path.
if actual_source and source_compiles:
    try:
        t=ast.parse(actual_source)
        banned=(ast.Import,ast.ImportFrom,ast.Attribute,ast.With,ast.Try,ast.Raise,ast.Global,ast.Nonlocal)
        source_executes=not any(isinstance(n,banned) for n in ast.walk(t))
    except Exception:
        source_executes=False

# Existing snapshots do not count as a newly-created self-evolving language.
created_new_meta=bool(new_meta)
self_extension_exposed=any(
    any(tok in canon(x).lower() for tok in ('extension','self_evol','self-evol','mutat','operator'))
    for x in [d for _,d in dict_nodes]
) and created_new_meta
source_produced=actual_source is not None

checks={
 'task_only_transport':True,
 'external_coding_models_used':False,
 'new_external_research_used':False,
 'host_meta_language_template_used':False,
 'host_operator_list_used':False,
 'host_representation_schema_used':False,
 'host_source_seed_used':False,
 'host_patch_used':False,
 'host_target_file_selected':False,
 'native_goal_created':True,
 'native_deficit_detected':bool(goal_state['deficits']),
 'native_spontaneous_evolution_executed':bool(evolution.get('run_digest')),
 'new_meta_language_created_by_native_run':created_new_meta,
 'self_extension_or_evolution_exposed':self_extension_exposed,
 'actual_source_produced_by_yado':source_produced,
 'candidate_source_compiles':source_compiles,
 'fresh_execution_gate_reachable':source_executes,
 'rollback_parent_available':bool((evolution.get('parent') or {}).get('genome_digest')),
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
}

passed=(
 checks['new_meta_language_created_by_native_run']
 and checks['self_extension_or_evolution_exposed']
 and checks['actual_source_produced_by_yado']
 and checks['candidate_source_compiles']
 and checks['fresh_execution_gate_reachable']
 and checks['rollback_parent_available']
 and checks['canonical_unchanged']
)
status='PASS_SHADOW_G2_SELF_EVOLVING_META_LANGUAGE_SPONTANEOUS_GENESIS_V1' if passed else 'WITHHOLD_G2_SELF_EVOLVING_META_LANGUAGE_SPONTANEOUS_GENESIS_V1'

report={
 'schema':'yado.g2.self_evolving_meta_language_spontaneous_genesis.v1',
 'status':status,'task':task,'goal_state':goal_state,
 'preexisting_meta_grammar_snapshot':pre_meta,
 'preexisting_algorithm_genesis_snapshot':pre_alg,
 'zero_arg_native_methods_invoked':zero_arg_methods,
 'native_outputs':native_outputs,
 'new_meta_language_candidates':new_meta,
 'candidate_source_sha256':hashlib.sha256(actual_source.encode()).hexdigest() if actual_source else None,
 'checks':checks,
 'canonical_mutation':False,
 'next_required_capability':None if passed else 'NATIVE_TASK_CONDITIONED_META_LANGUAGE_SELF_GENESIS_V2',
 'semantic_boundary':'SPONTANEOUS TASK-ONLY ATTEMPT. HOST PROVIDED THE GOAL AND STRICT PASS CONDITIONS ONLY. NO META-LANGUAGE SCHEMA, OPERATOR SET, REPRESENTATION, SOURCE SEED, PATCH, TARGET FILE, NEW EXTERNAL RESEARCH OR EXTERNAL CODING MODEL WAS PROVIDED. PREEXISTING RC6 META-GRAMMAR SNAPSHOTS DO NOT COUNT AS A NEW LANGUAGE.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,
 'native_deficit_count':len(goal_state['deficits']),
 'zero_arg_native_methods_invoked':zero_arg_methods,
 'new_meta_language_created':created_new_meta,
 'self_extension_exposed':self_extension_exposed,
 'source_produced':source_produced,
 'source_compiles':source_compiles,
 'next_required_capability':report['next_required_capability'],
 'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True,default=str))
if not passed: raise SystemExit(2)
