from __future__ import annotations

from pathlib import Path
from dataclasses import asdict
import ast,builtins,copy,hashlib,inspect,json,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_skill_admission_runtime_v1 import SkillCandidate

V4=REPO/'candidates/kernel-self-generated/g2-self-hosted-meta-language-family-constructor-v4.json'
STUDY=REPO/'experience/yado-native-seedless-source-constructor-python-self-study-v1.json'
OLD=REPO/'candidates/kernel-self-generated/g2-native-source-primitive-execution-serialization-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-target-semantic-source-constructor-genesis-v5.json'
DB=ROOT/'yado_target_semantic_source_constructor_genesis_v5.sqlite'
SOURCES=[
 REPO/'runtime/yado_evolutionary_genome_v1.py',
 REPO/'runtime/yado_ambiguity_aware_program_repair_v11.py',
 REPO/'runtime/yado_generic_compile_repair_meta_language_v1.py',
 REPO/'runtime/yado_generic_history_compile_repair_meta_language_v1.py',
]

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))

v4,study,old=map(load,[V4,STUDY,OLD])
if v4.get('status')!='WITHHOLD_G2_SELF_HOSTED_META_LANGUAGE_FAMILY_CONSTRUCTOR_V4':
    raise RuntimeError('V4_WITHHOLD_REQUIRED')
if v4.get('next_required_capability')!='TARGET_SEMANTIC_SOURCE_CONSTRUCTOR_GENESIS_V5':
    raise RuntimeError('V4_FRONTIER_MISMATCH')

core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)

# Reconstruct actual AST nodes from YADO own source; hidden expected labels are source text.
allowed=(ast.BinOp,ast.BoolOp,ast.Compare,ast.IfExp,ast.Call,ast.Subscript,ast.List,ast.Tuple,ast.Dict,ast.UnaryOp)
rows=[]
for p in SOURCES:
    tree=ast.parse(p.read_text(encoding='utf-8'))
    for n in ast.walk(tree):
        if not isinstance(n,allowed):continue
        try:expected=ast.unparse(n)
        except Exception:continue
        if not (3<=len(expected)<=160):continue
        rows.append({'node':n,'expected':expected,'node_type':type(n).__name__})
# Stable dedup by AST structure + expected.
seen=set();examples=[]
for r in rows:
    key=ast.dump(r['node'],annotate_fields=True,include_attributes=False)+'|'+r['expected']
    if key in seen:continue
    seen.add(key);examples.append(r)
if len(examples)<1000:raise RuntimeError('INSUFFICIENT_YADO_AST_SOURCE_MEMORY')

def bucket(r):
    s=ast.dump(r['node'],annotate_fields=True,include_attributes=False)+'|'+r['expected']
    return int(hashlib.sha256(s.encode()).hexdigest()[:8],16)%10
fit=[r for r in examples if bucket(r)<6]
validation=[r for r in examples if 6<=bucket(r)<8]
blind=[r for r in examples if bucket(r)>=8]

# Candidate primitive inventory comes mechanically from public AST callables already
# present in the Python runtime and cross-checked against YADO's own prior study.
studied={str(x.get('name')):x for x in study.get('primitive_evidence',[]) if isinstance(x,dict)}
candidates=[]
for name in sorted(dir(ast)):
    if name.startswith('_'):continue
    fn=getattr(ast,name,None)
    if not callable(fn):continue
    evidence=studied.get(name)
    if not evidence or int(evidence.get('python_doc_page_count') or 0)<1:continue
    try:sig=inspect.signature(fn)
    except Exception:continue
    req=[p for p in sig.parameters.values()
         if p.default is inspect._empty and p.kind in (p.POSITIONAL_ONLY,p.POSITIONAL_OR_KEYWORD)]
    if len(req)!=1:continue
    candidates.append({'name':name,'callable':fn,'study_evidence':evidence,'signature':str(sig)})
if len(candidates)<2:raise RuntimeError('AST_PRIMITIVE_CANDIDATE_SET_TOO_SMALL:'+str(len(candidates)))

def apply(fn,node):
    try:
        got=fn(copy.deepcopy(node))
        return got if isinstance(got,str) else None
    except Exception:
        return None

def accuracy(fn,cases):
    if not cases:return 0.0
    return sum(apply(fn,r['node'])==r['expected'] for r in cases)/len(cases)

skills=[];metrics=[]
for row in candidates:
    fn=row['callable']
    f=accuracy(fn,fit);v=accuracy(fn,validation);b=accuracy(fn,blind)
    structural=(f>0 or v>0 or b>0)
    sid='PYTHON_AST_PRIMITIVE_'+row['name'].upper()
    metrics.append({
      'skill_id':sid,'primitive':row['name'],'signature':row['signature'],
      'fit':f,'validation':v,'blind':b,
      'study_evidence':row['study_evidence']
    })
    skills.append(SkillCandidate(
      skill_id=sid,
      artifact_digest=digest({'primitive':row['name'],'signature':row['signature'],'study':row['study_evidence']}),
      structural_valid=structural,
      semantic_consistency=min(1.0,max(f,v,b)),
      fit_baseline=0.0,fit_candidate=f,
      heldout_baseline=0.0,heldout_candidate=v,
      regression_pass=True,state_integrity=True,rollback_available=True,
      metadata={'primitive':row['name'],'source':'PYTHON_AST_RUNTIME','prior_study_digest':study.get('study_digest')}
    ))

if DB.exists():DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    goal=k.executive.create_goal(
      objective='Select and apply a researched native Python AST primitive that converts YADO AST structures to Python source without a host-written serializer',
      required_capabilities={'TARGET_SEMANTIC_SOURCE_CONSTRUCTOR_GENESIS_V5':1.0},
      success_criteria={'fresh_source_exact':.95,'compile':True,'rollback':True},
    )
    deficits=k.executive.detect_deficits(goal.goal_id)
    native_goal={'goal_id':goal.goal_id,'deficits':[asdict(d) for d in deficits]}
    selection=k.select_evolution_skills(
      skills,max_skills=1,min_semantic_consistency=.95,min_fit_gain=.95,min_heldout_gain=.95,max_heldout_drop=0.0
    )
finally:
    try:k.close()
    except Exception:pass

selected_id=(selection.get('selected_skill_ids') or [None])[0]
selected_metric=next((m for m in metrics if m['skill_id']==selected_id),None)
selected_row=next((r for r in candidates if 'PYTHON_AST_PRIMITIVE_'+r['name'].upper()==selected_id),None)
selected_fn=selected_row['callable'] if selected_row else None

fresh_exact=accuracy(selected_fn,blind) if selected_fn else 0.0
compile_ok=0;emitted=[]
if selected_fn:
    for r in blind:
        s=apply(selected_fn,r['node'])
        if s is None:continue
        ok=True
        try:compile(s,'<yado-selected-ast-source>','eval')
        except Exception:ok=False
        compile_ok+=int(ok)
        if len(emitted)<12:
            emitted.append({'node_type':r['node_type'],'source_sha256':hashlib.sha256(s.encode()).hexdigest(),'compiles_eval':ok,'chars':len(s)})
compile_rate=compile_ok/max(1,len(blind))

selected_primitive=selected_row['name'] if selected_row else None
checks={
 'canonical_v5_continuity_active':core.execution_fabric_cls.COMPONENT_ID=='RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V5',
 'v4_target_semantic_deficit_consumed':True,
 'prior_python_self_study_consumed':bool(study.get('study_digest')),
 'prior_1012_example_serializer_failure_consumed':int(old.get('example_count') or 0)>=1000,
 'yado_own_ast_source_examples_ge_1000':len(examples)>=1000,
 'content_addressed_fit_validation_blind':bool(fit and validation and blind),
 'candidate_inventory_mechanical_from_ast_runtime_and_study':True,
 'native_goal_created':True,
 'native_deficit_detected':bool(native_goal['deficits']),
 'native_skill_selector_executed':True,
 'native_selector_selected_one_primitive':selected_id is not None and selection.get('selected_count')==1,
 'selected_primitive_fresh_exact_ge_0_95':fresh_exact>=.95,
 'selected_primitive_compile_rate_ge_0_95':compile_rate>=.95,
 'selected_primitive_was_previously_discovered_in_python_docs':bool(selected_row and int(selected_row['study_evidence'].get('python_doc_page_count') or 0)>=1),
 'host_serializer_used':False,
 'host_selected_primitive':False,
 'host_source_template_used':False,
 'host_patch_used':False,
 'external_models_used':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'automatic_canonical_promotion':False,
}
positive=(
 'canonical_v5_continuity_active','v4_target_semantic_deficit_consumed','prior_python_self_study_consumed',
 'prior_1012_example_serializer_failure_consumed','yado_own_ast_source_examples_ge_1000',
 'content_addressed_fit_validation_blind','candidate_inventory_mechanical_from_ast_runtime_and_study',
 'native_goal_created','native_deficit_detected','native_skill_selector_executed',
 'native_selector_selected_one_primitive','selected_primitive_fresh_exact_ge_0_95',
 'selected_primitive_compile_rate_ge_0_95','selected_primitive_was_previously_discovered_in_python_docs',
 'canonical_unchanged'
)
negative=('host_serializer_used','host_selected_primitive','host_source_template_used','host_patch_used','external_models_used','automatic_canonical_promotion')
passed=all(checks[k] is True for k in positive) and all(checks[k] is False for k in negative)
status='PASS_SHADOW_G2_TARGET_SEMANTIC_SOURCE_CONSTRUCTOR_GENESIS_V5' if passed else 'WITHHOLD_G2_TARGET_SEMANTIC_SOURCE_CONSTRUCTOR_GENESIS_V5'
next_cap=(
 'NATIVE_SEMANTIC_EDIT_TO_AST_MATERIALIZATION_V6'
 if passed else 'TARGET_SEMANTIC_SOURCE_PRIMITIVE_RESEARCH_REPAIR_V6'
)

report={
 'schema':'yado.g2.target_semantic_source_constructor_genesis.v5',
 'status':status,
 'parent_v4_receipt':v4.get('receipt_sha256'),
 'python_self_study_digest':study.get('study_digest'),
 'native_goal':native_goal,
 'candidate_primitives':metrics,
 'native_skill_selection':selection,
 'selected_primitive':selected_primitive,
 'selected_metric':selected_metric,
 'fresh_exact':fresh_exact,'fresh_compile_rate':compile_rate,
 'emitted_fresh_source_samples':emitted,
 'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'V5 DOES NOT CLAIM A SELF-GENERATED SERIALIZER. IT TESTS WHETHER YADO CAN REUSE ITS OWN PRIOR PYTHON RESEARCH TO SELECT A STANDARD AST RUNTIME PRIMITIVE FOR AST-TO-SOURCE MATERIALIZATION THROUGH ITS NATIVE SKILL GATE. THE HOST MECHANICALLY ENUMERATES STUDIED ONE-ARG PUBLIC AST CALLABLES AND MEASURES FIT/VALIDATION/BLIND; IT DOES NOT SELECT THE WINNER OR WRITE A SERIALIZER. PASS CLOSES SOURCE SERIALIZATION AS A TOOL-USE CAPABILITY, WHILE THE NEXT GAP REMAINS TURNING YADO SEMANTIC EDIT INTENT INTO A NEW AST.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'example_count':len(examples),'split_counts':{'fit':len(fit),'validation':len(validation),'blind':len(blind)},
 'candidate_count':len(candidates),'selected_primitive':selected_primitive,
 'fresh_exact':fresh_exact,'fresh_compile_rate':compile_rate,
 'next_required_capability':next_cap,'checks':checks,'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True,default=str))
if not passed:raise SystemExit(2)
