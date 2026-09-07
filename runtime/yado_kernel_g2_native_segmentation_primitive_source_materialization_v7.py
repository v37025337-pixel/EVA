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
from yado_algorithm_component_runtime_native_v1 import predict_intel_component

TASK=REPO/'architecture/yado-kernel-g2-native-segmentation-primitive-source-materialization-v7-request.json'
SEG=REPO/'candidates/kernel-self-generated/raw-task-representation-segmentation-primitive-v6.json'
SEG_REPORT=REPO/'architecture/yado-kernel-g2-native-raw-representation-segmentation-primitive-genesis-v6.json'
EMITTER=REPO/'candidates/kernel-self-generated/g2-experience-conditioned-native-emitter-gene-genesis-v3.json'
AST_TOOL=REPO/'candidates/kernel-self-generated/g2-target-semantic-source-constructor-genesis-v5.json'
V18=REPO/'candidates/kernel-self-generated/g2-native-context-bound-ast-source-realization-v18.json'
V19=REPO/'candidates/kernel-self-generated/g2-native-self-hosted-ast-source-realization-transport-v19.json'
OUT=REPO/'candidates/kernel-self-generated/g2-native-segmentation-primitive-source-materialization-v7.json'
CAND=REPO/'candidates/g2-self-evolution/yado_native_segmentation_primitive_source_v7.py'
DB=ROOT/'yado_native_segmentation_source_materialization_v7.sqlite'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def sha_text(s):return hashlib.sha256(s.encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))

task,seg,seg_report,emitter,ast_tool,v18,v19=map(load,[TASK,SEG,SEG_REPORT,EMITTER,AST_TOOL,V18,V19])

if seg_report.get('status')!='PASS_SHADOW_G2_NATIVE_RAW_REPRESENTATION_SEGMENTATION_PRIMITIVE_GENESIS_V6':
    raise RuntimeError('SEGMENTATION_V6_PASS_REQUIRED')
if seg.get('status')!='PASS_SHADOW_G2_NATIVE_RAW_REPRESENTATION_SEGMENTATION_PRIMITIVE_GENESIS_V6':
    raise RuntimeError('SEGMENTATION_CANDIDATE_PASS_REQUIRED')
if seg.get('candidate_digest')!=seg_report.get('candidate_digest'):
    raise RuntimeError('SEGMENTATION_CANDIDATE_DIGEST_MISMATCH')
if emitter.get('status')!='PASS_SHADOW_G2_EXPERIENCE_CONDITIONED_NATIVE_EMITTER_GENE_GENESIS_V3':
    raise RuntimeError('NATIVE_EMITTER_GENE_PASS_REQUIRED')
if ast_tool.get('status')!='PASS_SHADOW_G2_TARGET_SEMANTIC_SOURCE_CONSTRUCTOR_GENESIS_V5':
    raise RuntimeError('AST_SOURCE_TOOL_PASS_REQUIRED')
if v18.get('status')!='PASS_SHADOW_G2_NATIVE_CONTEXT_BOUND_AST_SOURCE_REALIZATION_V18':
    raise RuntimeError('V18_SOURCE_REALIZATION_HISTORY_REQUIRED')
if not str(v19.get('status','')).startswith('PASS_'):
    raise RuntimeError('V19_SOURCE_TRANSPORT_HISTORY_REQUIRED')

model=seg.get('model')
algorithm=seg.get('selected_algorithm')
contract=list(seg.get('feature_contract') or [])
if not isinstance(model,dict) or not algorithm or len(contract)<4:
    raise RuntimeError('SEGMENTATION_MODEL_CONTRACT_MISSING')
leaf={'op':'LEAF','algorithm':algorithm,'model':model}

core=UnifiedYADOCoreV1(REPO)
head_before=copy.deepcopy(core.head)
parent=core.evolutionary_parent_genome()
experience=copy.deepcopy(parent.get('experience') or [])
experience += [
 {'role':'CURRENT_YADO_SEGMENTATION_PRIMITIVE','artifact':str(SEG.relative_to(REPO)),
  'receipt_sha256':seg_report.get('receipt_sha256'),'candidate_digest':seg.get('candidate_digest'),
  'selected_algorithm':algorithm,'feature_contract':contract},
 {'role':'YADO_NATIVE_EMITTER_GENE','artifact':str(EMITTER.relative_to(REPO)),
  'receipt_sha256':emitter.get('receipt_sha256'),'gene_id':(emitter.get('emitter_gene') or {}).get('gene_id')},
 {'role':'YADO_AST_TO_SOURCE_TOOL_PASS','artifact':str(AST_TOOL.relative_to(REPO)),
  'receipt_sha256':ast_tool.get('receipt_sha256'),'selected_primitive':ast_tool.get('selected_primitive')},
 {'role':'YADO_PRIOR_SOURCE_REALIZATION_PASS','artifact':str(V18.relative_to(REPO)),
  'receipt_sha256':v18.get('receipt_sha256'),'candidate_source_sha256':v18.get('candidate_source_sha256')},
 {'role':'YADO_PRIOR_SOURCE_TRANSPORT_PASS','artifact':str(V19.relative_to(REPO)),
  'receipt_sha256':v19.get('receipt_sha256')},
]

controller=core.evolutionary_genome_cls(parent['parent'],experience_sources=experience)

# Snapshot Python files before native source/code calls so YADO-created files can be
# distinguished from all pre-existing repository source.
pre_python_files={}
for p in REPO.rglob('*.py'):
    try:
        pre_python_files[str(p.relative_to(REPO)).replace('\\','/')]=hashlib.sha256(p.read_bytes()).hexdigest()
    except Exception:
        pass

if DB.exists():DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    goal=k.executive.create_goal(
      objective='Materialize the current YADO-born segmentation primitive as new executable Python source using only YADO native code/evolution/source-emission capabilities and retained source-construction experience.',
      required_capabilities={'NATIVE_SEGMENTATION_PRIMITIVE_SOURCE_MATERIALIZATION_V7':1.0},
      success_criteria={'new_source_bytes':True,'compile':True,'fresh_behavioral_equivalence':.98,'regression_equivalence':.98,'rollback':True},
    )
    deficits=k.executive.detect_deficits(goal.goal_id)
    native_goal={'goal_id':goal.goal_id,'deficits':[asdict(d) for d in deficits]}
finally:
    try:k.close()
    except Exception:pass

# Only zero-argument YADO-native routes are invoked. No source seed/template/AST is passed.
native_calls={}
for owner_name,obj in [('core',core),('controller',controller)]:
    for name in sorted(dir(obj)):
        if name.startswith('_') or not any(t in name.lower() for t in ('source','emit','synth','code','evol','genesis','construct','program')):
            continue
        fn=getattr(obj,name,None)
        if not callable(fn):continue
        try:sig=inspect.signature(fn)
        except Exception:continue
        required=[p for p in sig.parameters.values()
                  if p.default is inspect._empty and p.kind in (p.POSITIONAL_ONLY,p.POSITIONAL_OR_KEYWORD)]
        if required:continue
        key=owner_name+'.'+name
        try:native_calls[key]=fn()
        except Exception as e:native_calls[key]={'error':type(e).__name__+':'+str(e)[:600]}
if 'controller.evolve_once' not in native_calls:
    native_calls['controller.evolve_once']=controller.evolve_once()

# A candidate must be actual parseable Python with at least one function/class and must not
# already exist anywhere in the repository before the native calls.
existing_source_sha=set(pre_python_files.values())

source_candidates=[]
def consider_source(x,path):
    if isinstance(x,bytes):
        try:x=x.decode('utf-8')
        except Exception:return
    if not isinstance(x,str) or len(x)<80:return
    try:t=ast.parse(x)
    except Exception:return
    if not any(isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)) for n in ast.walk(t)):return
    h=sha_text(x)
    source_candidates.append({
      'path':path,'sha256':h,'source':x,
      'preexisting_repository_source':h in existing_source_sha,
    })

def walk(x,path='root'):
    if isinstance(x,dict):
        for kk,vv in x.items():walk(vv,path+'.'+str(kk))
    elif isinstance(x,(list,tuple)):
        for i,vv in enumerate(x):walk(vv,path+f'[{i}]')
    elif isinstance(x,(str,bytes)):
        consider_source(x,path)
    elif hasattr(x,'__dict__'):
        try:walk(vars(x),path+'.__dict__')
        except Exception:pass
walk(native_calls)

# Also detect Python files materialized directly by YADO native calls.
post_python_files={}
for p in REPO.rglob('*.py'):
    try:
        rel=str(p.relative_to(REPO)).replace('\\','/')
        h=hashlib.sha256(p.read_bytes()).hexdigest()
        post_python_files[rel]=h
        if rel not in pre_python_files:
            try:consider_source(p.read_text(encoding='utf-8'),'native_filesystem.new:'+rel)
            except Exception:pass
    except Exception:
        pass
changed_existing_python=[
  {'path':rel,'before_sha256':pre_python_files[rel],'after_sha256':sha}
  for rel,sha in post_python_files.items()
  if rel in pre_python_files and pre_python_files[rel]!=sha
]
novel=[x for x in source_candidates if not x['preexisting_repository_source']]

def feature_case(i,salt):
    row={}
    for j,name in enumerate(contract):
        h=int(hashlib.sha256(f'{salt}|{i}|{j}|{name}'.encode()).hexdigest()[:8],16)
        # Generic bounded numeric contract fuzzing. No task words or class labels are supplied.
        row[str(name)]=(h%1001)/1000.0
    return row

fresh_features=[feature_case(i,'FRESH_SOURCE_V7') for i in range(96)]
reg_features=[feature_case(i,'REGRESSION_SOURCE_V7') for i in range(160)]
# Include neutral edge states.
fresh_features += [{str(k):0.0 for k in contract},{str(k):1.0 for k in contract}]
reg_features += [{str(k):.5 for k in contract}]

fresh_expected=[predict_intel_component(leaf,x) for x in fresh_features]
reg_expected=[predict_intel_component(leaf,x) for x in reg_features]

def required_positional(fn):
    try:sig=inspect.signature(fn)
    except Exception:return None
    return [p for p in sig.parameters.values()
            if p.default is inspect._empty and p.kind in (p.POSITIONAL_ONLY,p.POSITIONAL_OR_KEYWORD)]

def discover_interfaces(source):
    ns={'__name__':'_yado_seg_source_v7_'}
    try:exec(compile(source,'<yado-native-seg-source-v7>','exec'),ns,ns)
    except Exception as e:return [],type(e).__name__+':'+str(e)[:600]
    calls=[]
    for name,obj in list(ns.items()):
        if name.startswith('_'):continue
        if inspect.isfunction(obj) and getattr(obj,'__module__',None)=='_yado_seg_source_v7_':
            req=required_positional(obj)
            if req is not None and len(req)==1:calls.append((name,obj))
        elif inspect.isclass(obj) and getattr(obj,'__module__',None)=='_yado_seg_source_v7_':
            init_req=required_positional(obj)
            # Class signature normally excludes self; only no-required-arg classes are instantiated.
            if init_req is None or len(init_req)>0:continue
            try:inst=obj()
            except Exception:continue
            for mname in sorted(dir(inst)):
                if mname.startswith('_'):continue
                fn=getattr(inst,mname,None)
                if not callable(fn):continue
                req=required_positional(fn)
                if req is not None and len(req)==1:calls.append((name+'.'+mname,fn))
    return calls,None

def score_callable(fn,cases,expected):
    ok=0;outs=[]
    for x,y in zip(cases,expected):
        try:got=fn(copy.deepcopy(x))
        except Exception as e:
            if len(outs)<6:outs.append({'error':type(e).__name__})
            continue
        ok+=int(got==y)
        if len(outs)<6:outs.append({'got':got,'expected':y,'ok':got==y})
    return ok/max(1,len(cases)),outs

evaluated=[]
for c in novel:
    source=c['source']
    compile_ok=True;compile_error=None
    try:compile(source,'<yado-native-seg-source-v7>','exec')
    except Exception as e:compile_ok=False;compile_error=type(e).__name__+':'+str(e)[:600]
    if not compile_ok:
        evaluated.append({**{k:v for k,v in c.items() if k!='source'},'compile':False,'compile_error':compile_error})
        continue
    interfaces,exec_error=discover_interfaces(source)
    best=None
    for iname,fn in interfaces:
        fs,samples=score_callable(fn,fresh_features,fresh_expected)
        rs,_=score_callable(fn,reg_features,reg_expected)
        row={'interface':iname,'fresh_score':fs,'regression_score':rs,'samples':samples}
        if best is None or (fs,rs,iname)>(best['fresh_score'],best['regression_score'],best['interface']):best=row
    evaluated.append({
      **{k:v for k,v in c.items() if k!='source'},'compile':True,'exec_error':exec_error,
      'interface_count':len(interfaces),'best_interface':best
    })

eligible=[]
for c,e in zip(novel,evaluated):
    b=e.get('best_interface') or {}
    if e.get('compile') and float(b.get('fresh_score') or 0)>=.98 and float(b.get('regression_score') or 0)>=.98:
        eligible.append((c,e))
eligible.sort(key=lambda z:(z[1]['best_interface']['fresh_score'],z[1]['best_interface']['regression_score'],
                            len(z[0]['source']),z[0]['sha256']),reverse=True)
winner,winner_eval=eligible[0] if eligible else (None,None)

if winner:
    CAND.parent.mkdir(parents=True,exist_ok=True)
    CAND.write_text(winner['source'],encoding='utf-8')

evo=native_calls.get('controller.evolve_once') or {}
child_exp=((evo.get('child') or {}).get('experience_sources') or []) if isinstance(evo,dict) else []
all_current_visible=all(str(x) in canon(child_exp) for x in (
    seg_report.get('receipt_sha256'),emitter.get('receipt_sha256'),
    ast_tool.get('receipt_sha256'),v18.get('receipt_sha256'),v19.get('receipt_sha256')
))

checks={
 'segmentation_v6_pass_consumed':True,
 'segmentation_candidate_digest_exact':seg.get('candidate_digest')==seg_report.get('candidate_digest'),
 'prior_yado_source_capabilities_consumed':all_current_visible,
 'native_goal_created':True,
 'native_deficit_detected':bool(native_goal['deficits']),
 'native_source_paths_executed':bool(native_calls),
 'actual_new_python_source_bytes_produced_by_yado':winner is not None,
 'candidate_source_not_preexisting_in_repository':winner is not None and not winner['preexisting_repository_source'],
 'candidate_source_compiles':winner_eval is not None and winner_eval.get('compile') is True,
 'candidate_interface_discovered_without_host_name':winner_eval is not None and bool(winner_eval.get('best_interface')),
 'fresh_behavioral_equivalence_ge_0_98':winner_eval is not None and float((winner_eval.get('best_interface') or {}).get('fresh_score') or 0)>=.98,
 'regression_behavioral_equivalence_ge_0_98':winner_eval is not None and float((winner_eval.get('best_interface') or {}).get('regression_score') or 0)>=.98,
 'rollback_parent_available':bool((evo.get('parent') or {}).get('genome_digest')) if isinstance(evo,dict) else False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'external_coding_models_used':False,
 'new_external_research_used':False,
 'host_source_template_used':False,
 'host_ast_skeleton_used':False,
 'host_patch_used':False,
 'host_target_function_selected':False,
 'host_callable_name_selected':False,
 'automatic_canonical_promotion':False,
}
positive=(
 'segmentation_v6_pass_consumed','segmentation_candidate_digest_exact','prior_yado_source_capabilities_consumed',
 'native_goal_created','native_deficit_detected','native_source_paths_executed',
 'actual_new_python_source_bytes_produced_by_yado','candidate_source_not_preexisting_in_repository',
 'candidate_source_compiles','candidate_interface_discovered_without_host_name',
 'fresh_behavioral_equivalence_ge_0_98','regression_behavioral_equivalence_ge_0_98',
 'rollback_parent_available','canonical_unchanged'
)
negative=(
 'external_coding_models_used','new_external_research_used','host_source_template_used',
 'host_ast_skeleton_used','host_patch_used','host_target_function_selected',
 'host_callable_name_selected','automatic_canonical_promotion'
)
passed=all(checks[k] is True for k in positive) and all(checks[k] is False for k in negative)
status='PASS_SHADOW_G2_NATIVE_SEGMENTATION_PRIMITIVE_SOURCE_MATERIALIZATION_V7' if passed else 'WITHHOLD_G2_NATIVE_SEGMENTATION_PRIMITIVE_SOURCE_MATERIALIZATION_V7'
next_cap='NATIVE_SEGMENTATION_PRIMITIVE_SOURCE_ADMISSION_V8' if passed else 'NATIVE_SEGMENTATION_PRIMITIVE_SOURCE_EMITTER_GENESIS_V8'

report={
 'schema':'yado.g2.native_segmentation_primitive_source_materialization.v7',
 'status':status,'task':task,
 'parent_segmentation_receipt':seg_report.get('receipt_sha256'),
 'segmentation_candidate_digest':seg.get('candidate_digest'),
 'segmentation_selected_algorithm':algorithm,'segmentation_feature_contract':contract,
 'native_goal':native_goal,
 'native_source_call_inventory':native_calls,
 'source_candidate_count':len(source_candidates),'novel_source_candidate_count':len(novel),
 'new_python_files_after_native_calls':[x for x in post_python_files if x not in pre_python_files],
 'changed_existing_python_files_after_native_calls':changed_existing_python,
 'evaluated_novel_source_candidates':evaluated,
 'selected_native_source_path':winner.get('path') if winner else None,
 'candidate_source_sha256':winner.get('sha256') if winner else None,
 'candidate_artifact_path':str(CAND.relative_to(REPO)) if winner else None,
 'selected_discovered_interface':(winner_eval.get('best_interface') or {}).get('interface') if winner_eval else None,
 'fresh_score':(winner_eval.get('best_interface') or {}).get('fresh_score') if winner_eval else None,
 'regression_score':(winner_eval.get('best_interface') or {}).get('regression_score') if winner_eval else None,
 'checks':checks,'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'V7 IS A STRICT SOURCE-LEVEL MILESTONE. THE HOST PASSES ONLY YADO-ORIGIN ARTIFACT RECEIPTS INTO YADO NATIVE EXPERIENCE, INVOKES ZERO-ARGUMENT YADO SOURCE/CODE/EVOLUTION ROUTES, AND OBSERVES THEIR OUTPUTS. NO SOURCE TEMPLATE, AST SKELETON, PATCH, TARGET FUNCTION OR CALLABLE NAME IS PROVIDED. PASS REQUIRES NOVEL PYTHON SOURCE BYTES NOT ALREADY PRESENT IN THE REPOSITORY, COMPILE SUCCESS, AND AUTOMATICALLY DISCOVERED ONE-ARG CALLABLE BEHAVIOR EQUIVALENT TO THE YADO-BORN SEGMENTATION MODEL ON INDEPENDENT FRESH AND REGRESSION CONTRACT FUZZ.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'source_candidate_count':len(source_candidates),'novel_source_candidate_count':len(novel),
 'candidate_source_sha256':report['candidate_source_sha256'],'selected_interface':report['selected_discovered_interface'],
 'fresh_score':report['fresh_score'],'regression_score':report['regression_score'],
 'next_required_capability':next_cap,'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True,default=str))
if not passed:raise SystemExit(2)
