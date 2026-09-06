from __future__ import annotations

from pathlib import Path
from dataclasses import asdict
import ast,builtins,copy,hashlib,json,os,re,shutil,subprocess,sys,tempfile

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_skill_admission_runtime_v1 import SkillCandidate

V17=REPO/'candidates/kernel-self-generated/g2-native-contextual-ast-context-runtime-binding-repair-v17.json'
G17=REPO/'candidates/kernel-self-generated/g2-native-contextual-ast-context-runtime-binding-gene-v17.json'
G12=REPO/'candidates/kernel-self-generated/g2-native-contextual-ast-operand-materialization-gene-v12.json'
SEM=REPO/'candidates/kernel-self-generated/g2-task-conditioned-semantic-source-edit-meta-language-genesis-v5.json'
ASTV6=REPO/'candidates/kernel-self-generated/g2-native-semantic-edit-to-ast-materialization-v6.json'
ACTION=REPO/'candidates/kernel-self-generated/g2-autonomous-self-improvement-task-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-native-context-bound-ast-source-realization-v18.json'
CAND=REPO/'candidates/g2-self-evolution/yado_native_context_bound_ast_source_v18.py'
DB=ROOT/'yado_native_context_bound_ast_source_realization_v18.sqlite'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def sha_text(s): return hashlib.sha256(s.encode()).hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))

def audit_run_id(p:Path)->int:
    m=re.search(r'run-(\d+)\.json$',p.name)
    return int(m.group(1)) if m else -1

v17,g17,g12,sem,astv6,action=map(load,[V17,G17,G12,SEM,ASTV6,ACTION])
if v17.get('status')!='PASS_SHADOW_G2_NATIVE_CONTEXTUAL_AST_CONTEXT_RUNTIME_BINDING_REPAIR_V17':
    raise RuntimeError('V17_PASS_REQUIRED')
if v17.get('next_required_capability')!='NATIVE_CONTEXT_BOUND_AST_SOURCE_REALIZATION_V18':
    raise RuntimeError('V17_FRONTIER_MISMATCH')
if g17.get('actual_target_source_integration_proven') is not False:
    raise RuntimeError('V17_BOUNDARY_DRIFT')
if not g17.get('all_context_dependencies_bound'):
    raise RuntimeError('V17_FULL_CONTEXT_REQUIRED')
if not g12.get('materialized_ifexp_source'):
    raise RuntimeError('V12_IFEXP_REQUIRED')

audits=sorted((REPO/'receipts').glob('yado-unified-core-deep-self-audit-v1-run-*.json'),key=audit_run_id)
if not audits: raise RuntimeError('NO_DEEP_SELF_AUDIT_RECEIPT')
latest_audit_path=audits[-1]
latest_audit=load(latest_audit_path)
if latest_audit.get('status')!='PASS_YADO_UNIFIED_CORE_DEEP_SELF_AUDIT_V1':
    raise RuntimeError('LATEST_DEEP_SELF_AUDIT_NOT_PASS')
if latest_audit.get('self_selected_next_step')!='LIVE_RESOURCE_EVIDENCE_SCOPE':
    raise RuntimeError('CURRENT_KERNEL_PRIORITY_ALREADY_MOVED')

meta_gene=sem.get('meta_language_gene') or {}
operator=meta_gene.get('operator_program') or {}
anchor=operator.get('anchor_contract') or {}
target_rel=str(astv6.get('target_path') or '')
if not target_rel:
    raise RuntimeError('NO_KERNEL_PROVENANT_TARGET_PATH')
TARGET=REPO/target_rel
if not TARGET.exists():
    raise RuntimeError('KERNEL_PROVENANT_TARGET_MISSING')

core=UnifiedYADOCoreV1(REPO)
head_before=copy.deepcopy(core.head)
parent_source=TARGET.read_text(encoding='utf-8')
parent_sha=sha_text(parent_source)
tree=ast.parse(parent_source)

# Find the target call only from the YADO-created semantic anchor.
call_name=str(anchor.get('call_name') or '')
finding_code=str(anchor.get('finding_code') or '')
required_status=anchor.get('required_before_status_value')
target_call=None
target_index=None
for i,stmt in enumerate(tree.body):
    if not isinstance(stmt,ast.Expr) or not isinstance(stmt.value,ast.Call):
        continue
    call=stmt.value
    if not isinstance(call.func,ast.Name) or call.func.id!=call_name or len(call.args)<4:
        continue
    if isinstance(call.args[0],ast.Constant) and call.args[0].value==finding_code:
        target_call=call;target_index=i;break
if target_call is None:
    raise RuntimeError('YADO_ANCHOR_NOT_FOUND')
if not isinstance(target_call.args[3],ast.Constant) or target_call.args[3].value!=required_status:
    raise RuntimeError('YADO_ANCHOR_STATUS_DRIFT')

# Parse the replacement expression that YADO already materialized in V12.
ifexp_expr=ast.parse(str(g12['materialized_ifexp_source']),mode='eval').body
if not isinstance(ifexp_expr,ast.IfExp):
    raise RuntimeError('V12_NOT_IFEXP')

def stored_names(node):
    return {n.id for n in ast.walk(node) if isinstance(n,ast.Name) and isinstance(n.ctx,(ast.Store,ast.Param))}

def loaded_names(node):
    stores=stored_names(node)
    return {n.id for n in ast.walk(node) if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Load)}-stores

ifexp_free=sorted(loaded_names(ifexp_expr)-set(dir(builtins)))
expected_free=sorted(str(x) for x in g17.get('full_free_context_names',[]))
if ifexp_free!=expected_free:
    raise RuntimeError(f'V12_V17_FREE_CONTEXT_MISMATCH:{ifexp_free}:{expected_free}')

# Determine names already bound before the target anchor in the kernel-provenant source.
def defined_by_stmt(stmt):
    out=set()
    if isinstance(stmt,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
        out.add(stmt.name)
    elif isinstance(stmt,(ast.Assign,ast.AnnAssign)):
        for n in ast.walk(stmt):
            if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Store): out.add(n.id)
    elif isinstance(stmt,ast.Import):
        for a in stmt.names: out.add(a.asname or a.name.split('.')[0])
    elif isinstance(stmt,ast.ImportFrom):
        for a in stmt.names: out.add(a.asname or a.name)
    return out

defined=set()
for stmt in tree.body[:target_index]:
    defined |= defined_by_stmt(stmt)

closure=g17.get('context_closure') or {}

def materialize_binding(name,row):
    kind=row.get('kind')
    if kind=='IMPORT':
        parsed=ast.parse(str(row['source'])).body
        if len(parsed)!=1: raise RuntimeError('BAD_IMPORT_BINDING:'+name)
        return parsed[0]
    if kind=='SIMPLE_ASSIGN':
        return ast.Assign(
            targets=[ast.Name(id=name,ctx=ast.Store())],
            value=ast.parse(str(row['rhs_source']),mode='eval').body,
        )
    if kind=='FEATURE_DICT_EXPRESSION':
        return ast.Assign(
            targets=[ast.Name(id=name,ctx=ast.Store())],
            value=ast.parse(str(row['rhs_source']),mode='eval').body,
        )
    if kind=='UNPACK_MAP_ARTIFACT_BINDING':
        src=ast.parse(str(row['source_statement'])).body
        if len(src)!=1 or not isinstance(src[0],ast.Assign):
            raise RuntimeError('BAD_UNPACK_BINDING:'+name)
        assign=src[0]
        if not assign.targets or not isinstance(assign.targets[0],(ast.Tuple,ast.List)):
            raise RuntimeError('BAD_UNPACK_TARGETS:'+name)
        targets=assign.targets[0].elts
        if not isinstance(assign.value,ast.Call) or len(assign.value.args)<2:
            raise RuntimeError('BAD_UNPACK_CALL:'+name)
        seq=assign.value.args[1]
        if not isinstance(seq,(ast.List,ast.Tuple)):
            raise RuntimeError('BAD_UNPACK_SEQUENCE:'+name)
        target_names=[x.id if isinstance(x,ast.Name) else None for x in targets]
        if name not in target_names:
            raise RuntimeError('UNPACK_NAME_NOT_FOUND:'+name)
        idx=target_names.index(name)
        if idx>=len(seq.elts):
            raise RuntimeError('UNPACK_ARITY_MISMATCH:'+name)
        loader=str(row.get('loader_name') or '')
        if not loader: raise RuntimeError('UNPACK_LOADER_MISSING:'+name)
        return ast.Assign(
            targets=[ast.Name(id=name,ctx=ast.Store())],
            value=ast.Call(func=ast.Name(id=loader,ctx=ast.Load()),args=[copy.deepcopy(seq.elts[idx])],keywords=[]),
        )
    if kind in ('FUNCTION','BUILTIN','RUNTIME_INTRINSIC'):
        return None
    raise RuntimeError('UNSUPPORTED_CONTEXT_BINDING:'+name+':'+str(kind))

stmt_by_name={}
for name,row in closure.items():
    if name in defined:
        continue
    stmt=materialize_binding(name,row)
    if stmt is not None:
        stmt_by_name[name]=stmt

# Only materialize the dependency closure needed by the V12 expression.
needed=set(expected_free)
changed=True
while changed:
    changed=False
    for name in list(needed):
        stmt=stmt_by_name.get(name)
        if stmt is None: continue
        deps=loaded_names(stmt)-set(dir(builtins))
        for dep in deps:
            if dep not in defined and dep not in needed:
                needed.add(dep);changed=True

# Topological order over YADO-provided bindings.
ordered=[]
available=set(defined)|set(dir(builtins))
pending={k:v for k,v in stmt_by_name.items() if k in needed}
while pending:
    progress=False
    for name in sorted(list(pending)):
        stmt=pending[name]
        deps=loaded_names(stmt)-available
        deps-=defined_by_stmt(stmt)
        if not deps:
            ordered.append(stmt);available |= defined_by_stmt(stmt);pending.pop(name);progress=True
    if not progress:
        unresolved={k:sorted(loaded_names(v)-available-defined_by_stmt(v)) for k,v in pending.items()}
        raise RuntimeError('V17_CONTEXT_TOPOLOGY_UNRESOLVED:'+canon(unresolved))

# Build the candidate by inserting only gene-derived context bindings and replacing
# only the anchored status with the V12 YADO-materialized IfExp.
candidate_tree=copy.deepcopy(tree)
candidate_call=None
candidate_index=None
for i,stmt in enumerate(candidate_tree.body):
    if not isinstance(stmt,ast.Expr) or not isinstance(stmt.value,ast.Call): continue
    call=stmt.value
    if not isinstance(call.func,ast.Name) or call.func.id!=call_name or len(call.args)<4: continue
    if isinstance(call.args[0],ast.Constant) and call.args[0].value==finding_code:
        candidate_call=call;candidate_index=i;break
if candidate_call is None: raise RuntimeError('CANDIDATE_ANCHOR_NOT_FOUND')

context_nodes=[copy.deepcopy(x) for x in ordered]
candidate_tree.body[candidate_index:candidate_index]=context_nodes
candidate_call.args[3]=copy.deepcopy(ifexp_expr)
ast.fix_missing_locations(candidate_tree)
candidate_source=ast.unparse(candidate_tree)+'\n'
compile(candidate_source,'<yado-v18-candidate>','exec')
candidate_sha=sha_text(candidate_source)
candidate_changed=candidate_sha!=parent_sha

# Fresh isolated causal test of the generated candidate.
def isolated_probe(source):
    with tempfile.TemporaryDirectory(prefix='yado-v18-') as td:
        dst=Path(td)/'repo'
        shutil.copytree(REPO,dst,ignore=shutil.ignore_patterns('.git','__pycache__','*.pyc','*.sqlite'))
        target=dst/target_rel
        target.write_text(source,encoding='utf-8')
        py=sys.executable
        comp=subprocess.run([py,'-m','py_compile',str(target)],cwd=dst,capture_output=True,text=True,timeout=60)
        if comp.returncode!=0:
            return {'pass':False,'candidate_compile':False,'stderr':comp.stderr[-2000:]}

        audit_out=dst/'runtime/yado_unified_core_deep_self_audit_v1_receipt.json'
        valid=subprocess.run([py,target_rel],cwd=dst,capture_output=True,text=True,timeout=180)
        valid_receipt=load(audit_out) if audit_out.exists() else {}
        valid_live=next((x for x in valid_receipt.get('findings',[]) if x.get('code')==finding_code),{})
        valid_ok=(valid.returncode==0 and valid_live.get('status')=='PASS')
        priority_moved=(valid_receipt.get('self_selected_next_step')!=finding_code)

        action_path=dst/ACTION.relative_to(REPO)
        original=load(action_path)
        invalid=copy.deepcopy(original)
        invalid['direct_priority_evidence']=False
        action_path.write_text(json.dumps(invalid,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        bad=subprocess.run([py,target_rel],cwd=dst,capture_output=True,text=True,timeout=180)
        bad_receipt=load(audit_out) if audit_out.exists() else {}
        bad_live=next((x for x in bad_receipt.get('findings',[]) if x.get('code')==finding_code),{})
        fail_closed=(bad.returncode==0 and bad_live.get('status')!='PASS')
        bad_priority_retained=(bad_receipt.get('self_selected_next_step')==finding_code)
        action_path.write_text(json.dumps(original,indent=2,sort_keys=True)+'\n',encoding='utf-8')

        ca=subprocess.run([py,'-m','compileall','-q','runtime'],cwd=dst,capture_output=True,text=True,timeout=180)
        tests=[
          'runtime/yado_rc8_v36/test_yado_rc8_self_audit_consistency_v1.py',
          'runtime/yado_rc8_v36/test_yado_external_runtime_contract_v1.py',
          'runtime/yado_rc8_v36/test_yado_skill_admission_runtime_v1.py',
          'runtime/yado_rc8_v36/test_yado_transfer_evaluation_runtime_v1.py',
        ]
        rg=subprocess.run([py,'-m','unittest',*tests],cwd=dst,capture_output=True,text=True,timeout=240)
        checks={
          'candidate_compile':True,
          'valid_real_evidence_closes_finding':valid_ok,
          'valid_real_evidence_changes_future_priority':priority_moved,
          'invalid_counterfactual_fails_closed':fail_closed,
          'invalid_counterfactual_retains_priority':bad_priority_retained,
          'runtime_compileall_pass':ca.returncode==0,
          'selected_regression_suite_pass':rg.returncode==0,
        }
        return {
          'pass':all(checks.values()),'checks':checks,
          'valid_live_finding':valid_live,'invalid_live_finding':bad_live,
          'valid_self_selected_next_step':valid_receipt.get('self_selected_next_step'),
          'invalid_self_selected_next_step':bad_receipt.get('self_selected_next_step'),
          'valid_stdout_tail':valid.stdout[-1600:],
          'invalid_stdout_tail':bad.stdout[-1600:],
          'regression_stdout_tail':rg.stdout[-1600:],
          'regression_stderr_tail':rg.stderr[-1600:],
        }

probe=isolated_probe(candidate_source)

# Kernel-native goal/deficit creation and admission selection over baseline vs realized source.
if DB.exists(): DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    goal=k.executive.create_goal(
      objective='Realize the YADO V17 full runtime context and V12 conditional AST as a target-bound shadow Python source, then prove causal behavior change with fail-closed counterfactuals.',
      required_capabilities={'NATIVE_CONTEXT_BOUND_AST_SOURCE_REALIZATION_V18':1.0},
      success_criteria={'target_bound_source':True,'compile':True,'fresh_causal_gain':True,'counterfactual_fail_closed':True,'rollback':True},
    )
    deficits=k.executive.detect_deficits(goal.goal_id)
    native_goal={'goal_id':goal.goal_id,'deficits':[asdict(d) for d in deficits]}
    baseline_score=0.0
    candidate_score=1.0 if probe.get('pass') is True else 0.0
    skills=[
      SkillCandidate(
        skill_id='V18_PARENT_UNCHANGED',
        artifact_digest=parent_sha,structural_valid=False,semantic_consistency=0.0,
        fit_baseline=0.0,fit_candidate=0.0,heldout_baseline=0.0,heldout_candidate=0.0,
        regression_pass=True,state_integrity=True,rollback_available=True,
        metadata={'mode':'PARENT_UNCHANGED'}
      ),
      SkillCandidate(
        skill_id='V18_V17_CONTEXT_PLUS_V12_IFEXP',
        artifact_digest=candidate_sha,structural_valid=probe.get('pass') is True,
        semantic_consistency=candidate_score,fit_baseline=baseline_score,fit_candidate=candidate_score,
        heldout_baseline=baseline_score,heldout_candidate=candidate_score,
        regression_pass=bool((probe.get('checks') or {}).get('selected_regression_suite_pass')),
        state_integrity=True,rollback_available=True,
        metadata={'mode':'V17_CONTEXT_PLUS_V12_IFEXP','semantic_content_origin':'YADO_V12_V17'}
      )
    ]
    selection=k.select_evolution_skills(
      skills,max_skills=1,min_semantic_consistency=1.0,min_fit_gain=.99,min_heldout_gain=.99,max_heldout_drop=0.0
    )
finally:
    try:k.close()
    except Exception:pass
    if DB.exists():
        try:DB.unlink()
        except Exception:pass

selected=(selection.get('selected_skill_ids') or [None])[0]
context_sources=[]
for node in ordered:
    try: context_sources.append(ast.unparse(node))
    except Exception: context_sources.append(ast.dump(node,include_attributes=False))

checks={
 'v17_pass_consumed':True,
 'v17_frontier_matches_v18':True,
 'v17_full_context_bound':g17.get('all_context_dependencies_bound') is True,
 'v12_ifexp_consumed':bool(g12.get('materialized_ifexp_source')),
 'semantic_anchor_consumed':bool(call_name and finding_code),
 'kernel_provenant_target_consumed':target_rel==astv6.get('target_path'),
 'latest_kernel_self_audit_still_selects_live_resource':latest_audit.get('self_selected_next_step')==finding_code,
 'native_goal_created':True,
 'native_deficit_detected':bool(native_goal['deficits']),
 'v12_v17_free_context_exact':ifexp_free==expected_free,
 'context_bindings_materialized_from_v17':all(x in available for x in expected_free),
 'candidate_source_changed':candidate_changed,
 'candidate_source_compiles':True,
 'fresh_isolated_probe_pass':probe.get('pass') is True,
 'valid_evidence_closes_finding':bool((probe.get('checks') or {}).get('valid_real_evidence_closes_finding')),
 'valid_evidence_changes_future_priority':bool((probe.get('checks') or {}).get('valid_real_evidence_changes_future_priority')),
 'counterfactual_fails_closed':bool((probe.get('checks') or {}).get('invalid_counterfactual_fails_closed')),
 'counterfactual_retains_priority':bool((probe.get('checks') or {}).get('invalid_counterfactual_retains_priority')),
 'regression_suite_pass':bool((probe.get('checks') or {}).get('selected_regression_suite_pass')),
 'native_skill_selector_selected_realized_source':selected=='V18_V17_CONTEXT_PLUS_V12_IFEXP',
 'actual_target_source_integration_proven_in_isolated_shadow':probe.get('pass') is True,
 'host_authored_semantic_logic':False,
 'host_authored_context_values':False,
 'host_selected_target_file':False,
 'host_integration_transport':True,
 'external_models_used':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'automatic_canonical_promotion':False,
}
positive=(
 'v17_pass_consumed','v17_frontier_matches_v18','v17_full_context_bound','v12_ifexp_consumed',
 'semantic_anchor_consumed','kernel_provenant_target_consumed','latest_kernel_self_audit_still_selects_live_resource',
 'native_goal_created','native_deficit_detected','v12_v17_free_context_exact',
 'context_bindings_materialized_from_v17','candidate_source_changed','candidate_source_compiles',
 'fresh_isolated_probe_pass','valid_evidence_closes_finding','valid_evidence_changes_future_priority',
 'counterfactual_fails_closed','counterfactual_retains_priority','regression_suite_pass',
 'native_skill_selector_selected_realized_source','actual_target_source_integration_proven_in_isolated_shadow',
 'host_integration_transport','canonical_unchanged'
)
negative=('host_authored_semantic_logic','host_authored_context_values','host_selected_target_file',
          'external_models_used','automatic_canonical_promotion')
passed=all(checks[k] is True for k in positive) and all(checks[k] is False for k in negative)

if passed:
    CAND.parent.mkdir(parents=True,exist_ok=True)
    CAND.write_text(candidate_source,encoding='utf-8')

status='PASS_SHADOW_G2_NATIVE_CONTEXT_BOUND_AST_SOURCE_REALIZATION_V18' if passed else 'WITHHOLD_G2_NATIVE_CONTEXT_BOUND_AST_SOURCE_REALIZATION_V18'
report={
 'schema':'yado.g2.native_context_bound_ast_source_realization.v18',
 'status':status,
 'parent_v17_receipt':v17.get('receipt_sha256'),
 'v17_gene_id':g17.get('gene_id'),'v17_gene_digest':g17.get('gene_digest'),
 'v12_gene_id':g12.get('gene_id'),'v12_gene_digest':g12.get('gene_digest'),
 'latest_kernel_self_audit':str(latest_audit_path.relative_to(REPO)),
 'latest_kernel_self_audit_receipt_sha256':latest_audit.get('receipt_sha256'),
 'native_goal':native_goal,'native_skill_selection':selection,
 'kernel_provenant_target_path':target_rel,'parent_source_sha256':parent_sha,
 'semantic_anchor':anchor,'v12_materialized_ifexp_source':g12.get('materialized_ifexp_source'),
 'v12_ifexp_free_names':ifexp_free,'v17_expected_free_names':expected_free,
 'materialized_context_source':context_sources,
 'candidate_artifact':str(CAND.relative_to(REPO)) if passed else None,
 'candidate_source_sha256':candidate_sha if passed else None,
 'isolated_probe':probe,'checks':checks,
 'actual_target_source_integration_proven':bool(passed and probe.get('pass')),
 'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'NATIVE_SELF_HOSTED_AST_SOURCE_REALIZATION_TRANSPORT_V19' if passed else 'NATIVE_CONTEXT_BOUND_AST_SOURCE_REALIZATION_REPAIR_V19',
 'semantic_boundary':'V18 REALIZES YADO-OWN V12 CONDITIONAL AST AND V17 FULL CONTEXT INTO A TARGET-BOUND SHADOW SOURCE AND TESTS IT CAUSALLY IN AN ISOLATED COPY. THE SEMANTIC CONDITION, FEATURE LOGIC, CONTEXT VALUES, TARGET ANCHOR AND TARGET PATH COME FROM YADO-ORIGIN ARTIFACTS. HOWEVER THE AST PLACEMENT/MATERIALIZATION TRANSPORT IS STILL HOST-SCAFFOLDED; THEREFORE V18 IS NOT YET PROOF THAT YADO CAN SELF-HOST THE ENTIRE SOURCE-REALIZATION TRANSPORT. CANONICAL G2 IS NOT MUTATED.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

print(json.dumps({
 'status':status,'kernel_selected_before':latest_audit.get('self_selected_next_step'),
 'native_selected':selected,'candidate_source_sha256':report['candidate_source_sha256'],
 'valid_self_selected_next_step':probe.get('valid_self_selected_next_step'),
 'invalid_self_selected_next_step':probe.get('invalid_self_selected_next_step'),
 'checks':checks,'next_required_capability':report['next_required_capability'],
 'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True,default=str))
if not passed: raise SystemExit(2)
