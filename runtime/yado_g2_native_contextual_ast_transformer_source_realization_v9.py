from __future__ import annotations

from pathlib import Path
from dataclasses import asdict
import ast,copy,hashlib,inspect,json,shutil,subprocess,sys,tempfile

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_evolutionary_genome_v1 import PolynomialReturnRepairGeneV1

V8=REPO/'candidates/kernel-self-generated/g2-native-contextual-ast-transformer-policy-repair-v8.json'
GENE=REPO/'candidates/kernel-self-generated/g2-native-contextual-ast-transformer-gene-v8.json'
V5SRC=REPO/'candidates/kernel-self-generated/g2-target-semantic-source-constructor-genesis-v5.json'
SRCBIND=REPO/'candidates/kernel-self-generated/g2-task-conditioned-source-binding-v3.json'
PROCESS=REPO/'candidates/kernel-self-generated/g2-native-source-construction-process-evolution-v2.json'
HIDDEN=REPO/'candidates/kernel-self-generated/g2-native-hidden-code-gene-source-emission-observation-v3.json'
SEM=REPO/'candidates/kernel-self-generated/g2-task-conditioned-semantic-source-edit-meta-language-genesis-v5.json'
BINDER=REPO/'candidates/kernel-self-generated/g2-native-self-created-evidence-binder-gene-v1.json'
ACTION=REPO/'candidates/kernel-self-generated/g2-autonomous-self-improvement-task-v1.json'
TARGET=REPO/'runtime/yado_unified_core_deep_self_audit_v1.py'
OUT=REPO/'candidates/kernel-self-generated/g2-native-contextual-ast-transformer-source-realization-v9.json'
CAND=REPO/'candidates/g2-self-evolution/yado_native_contextual_ast_transformer_v9.py'
DB=ROOT/'yado_native_contextual_ast_transformer_source_realization_v9.sqlite'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(s):return hashlib.sha256(s.encode()).hexdigest()

v8,gene,v5src,srcbind,process,hidden,sem,binder,action=map(load,[V8,GENE,V5SRC,SRCBIND,PROCESS,HIDDEN,SEM,BINDER,ACTION])
if v8.get('status')!='PASS_SHADOW_G2_NATIVE_CONTEXTUAL_AST_TRANSFORMER_POLICY_REPAIR_V8':
    raise RuntimeError('V8_POLICY_PASS_REQUIRED')
if v8.get('next_required_capability')!='NATIVE_CONTEXTUAL_AST_TRANSFORMER_SOURCE_REALIZATION_V9':
    raise RuntimeError('V8_FRONTIER_MISMATCH')
if gene.get('actual_ast_materialization_proven') is not False or gene.get('python_source_emission_proven') is not False:
    raise RuntimeError('V8_GENE_BOUNDARY_DRIFT')
if v5src.get('selected_primitive')!='unparse':
    raise RuntimeError('V5_UNPARSE_BINDING_REQUIRED')
if srcbind.get('status')!='PASS_SHADOW_G2_TASK_CONDITIONED_SOURCE_BINDING_V3':
    raise RuntimeError('SOURCE_BINDING_V3_REQUIRED')
if process.get('status')!='PASS_NATIVE_SOURCE_CONSTRUCTION_PROCESS_EVOLUTION_V2':
    raise RuntimeError('SOURCE_PROCESS_V2_REQUIRED')
if hidden.get('status')!='PASS_SHADOW_G2_NATIVE_HIDDEN_CODE_GENE_SOURCE_EMISSION_OBSERVATION_V3':
    raise RuntimeError('HIDDEN_SOURCE_EMISSION_V3_REQUIRED')

core=UnifiedYADOCoreV1(REPO);head_before=copy.deepcopy(core.head)
target_source=TARGET.read_text(encoding='utf-8')
target_sha=sha(target_source)

if DB.exists():DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    goal=k.executive.create_goal(
      objective='Realize the YADO V8 contextual AST-transformer policy gene into a changed target-bound Python source candidate and preserve fail-closed counterfactual semantics.',
      required_capabilities={'NATIVE_CONTEXTUAL_AST_TRANSFORMER_SOURCE_REALIZATION_V9':1.0},
      success_criteria={'new_target_source':True,'compile':True,'counterfactual_fail_closed':True,'rollback':True},
    )
    deficits=k.executive.detect_deficits(goal.goal_id)
    native_goal={'goal_id':goal.goal_id,'deficits':[asdict(d) for d in deficits]}
finally:
    try:k.close()
    except Exception:pass

state=core.evolutionary_parent_genome()
experience=copy.deepcopy(state.get('experience') or [])
experience += [
 {
  'role':'YADO_CONTEXTUAL_AST_TRANSFORMER_GENE_V8',
  'artifact':str(GENE.relative_to(REPO)),'gene_id':gene.get('gene_id'),'gene_digest':gene.get('gene_digest'),
  'policy_program_id':gene.get('policy_program_id'),'transition_semantics':gene.get('transition_semantics'),
  'anchor_contract':gene.get('anchor_contract'),'history_derived_target_status_shape':gene.get('history_derived_target_status_shape'),
 },
 {
  'role':'YADO_V8_POLICY_EVIDENCE','artifact':str(V8.relative_to(REPO)),
  'receipt_sha256':v8.get('receipt_sha256'),'native_policy':v8.get('native_policy'),
  'actual_prediction':v8.get('actual_prediction'),'counterfactual_predictions':v8.get('counterfactual_predictions'),
 },
 {
  'role':'YADO_AST_TO_SOURCE_TOOL_V5','artifact':str(V5SRC.relative_to(REPO)),
  'receipt_sha256':v5src.get('receipt_sha256'),'selected_primitive':v5src.get('selected_primitive'),
 },
 {
  'role':'YADO_TASK_CONDITIONED_SOURCE_BINDING','artifact':str(SRCBIND.relative_to(REPO)),
  'receipt_sha256':srcbind.get('receipt_sha256'),'gene':srcbind.get('gene'),
 },
 {
  'role':'YADO_NATIVE_SOURCE_PROCESS','artifact':str(PROCESS.relative_to(REPO)),
  'receipt_sha256':process.get('receipt_sha256'),'learned_process':process.get('learned_process'),
 },
 {
  'role':'YADO_PROVEN_INTERNAL_SOURCE_EMISSION','artifact':str(HIDDEN.relative_to(REPO)),
  'receipt_sha256':hidden.get('receipt_sha256'),'selected_source_artifact':hidden.get('selected_source_artifact'),
 },
 {
  'role':'YADO_SEMANTIC_EDIT_GENE','artifact':str(SEM.relative_to(REPO)),
  'receipt_sha256':sem.get('receipt_sha256'),'meta_language_gene':sem.get('meta_language_gene'),
 },
 {
  'role':'YADO_EVIDENCE_BINDER_GENE','artifact':str(BINDER.relative_to(REPO)),
  'gene_id':binder.get('gene_id'),'gene_digest':binder.get('gene_digest'),'model':binder.get('model'),
 },
 {
  'role':'YADO_DIRECT_ACTION_EVIDENCE','artifact':str(ACTION.relative_to(REPO)),
  'receipt_sha256':action.get('receipt_sha256'),'selected_action':action.get('selected_action'),
  'direct_priority_evidence':action.get('direct_priority_evidence'),'goal_action_binding':action.get('goal_action_binding'),
 },
 {
  'role':'KERNEL_PROVENANT_TARGET_SOURCE',
  'path':str(TARGET.relative_to(REPO)),'sha256':target_sha,'source':target_source,
 }
]

controller=core.evolutionary_genome_cls(state['parent'],experience_sources=experience)
captures=[]
orig_func=PolynomialReturnRepairGeneV1.__dict__['synthesize']
orig_bound=PolynomialReturnRepairGeneV1.synthesize
def observe(cls,source,function_name,examples):
    result=orig_bound(source,function_name,examples)
    out=result.get('source') if isinstance(result,dict) else None
    captures.append({
      'caller_stack':[x.function for x in inspect.stack()[1:12]],
      'input_source_sha256':sha(source) if isinstance(source,str) else None,
      'result_source_sha256':sha(out) if isinstance(out,str) and out else None,
      'result_source':out,
      'observer_modified_arguments':False,'observer_modified_return':False,
    })
    return result

native_outputs={}
try:
    PolynomialReturnRepairGeneV1.synthesize=classmethod(observe)
    objects={'controller':controller,'core':core}
    for owner,obj in objects.items():
        for name in sorted(dir(obj)):
            if name.startswith('_'):continue
            if not any(t in name.lower() for t in ('evol','mutat','genesis','source','code','self','genome','component','snapshot')):
                continue
            fn=getattr(obj,name,None)
            if not callable(fn):continue
            try:sig=inspect.signature(fn)
            except Exception:continue
            required=[p for p in sig.parameters.values()
                      if p.default is inspect._empty and p.kind in (p.POSITIONAL_ONLY,p.POSITIONAL_OR_KEYWORD)]
            if required:continue
            key=f'{owner}.{name}'
            try:native_outputs[key]=fn()
            except Exception as e:native_outputs[key]={'error':type(e).__name__+':'+str(e)[:500]}
    if 'controller.evolve_once' not in native_outputs:
        try:native_outputs['controller.evolve_once']=controller.evolve_once()
        except Exception as e:native_outputs['controller.evolve_once']={'error':type(e).__name__+':'+str(e)[:500]}
finally:
    PolynomialReturnRepairGeneV1.synthesize=orig_func

semantic_tokens={
 str(gene.get('gene_id')),str(gene.get('binder_gene_id')),str(gene.get('semantic_edit_gene_id')),
 'LIVE_RESOURCE_EVIDENCE_SCOPE',
 'CONDITIONALIZE_FINDING_AS_RESOLVED_BY_FRESH_EVIDENCE',
 'PRESERVE_EXISTING_PARTIAL_FINDING',
 'ACCEPT_FRESH_EVIDENCE','WITHHOLD_FRESH_EVIDENCE',
}
source_candidates=[];seen=set()

def consider(s,path):
    if not isinstance(s,str) or not s.strip() or len(s)>350000:return
    h=sha(s)
    if h in seen or h==target_sha:return
    seen.add(h)
    try:
        tree=ast.parse(s);compile(s,'<yado-v9-source-candidate>','exec')
    except Exception:return
    toks=sorted(t for t in semantic_tokens if t and t in s)
    target_bound=('LIVE_RESOURCE_EVIDENCE_SCOPE' in s and 'yado_unified_core_deep_self_audit' in s.lower()) or (
        'LIVE_RESOURCE_EVIDENCE_SCOPE' in s and s.count('def add')>=1
    )
    source_candidates.append({'path':path,'sha256':h,'source':s,'semantic_tokens':toks,'semantic_token_count':len(toks),'target_bound':target_bound})

source_keys={'candidate_source','source','mutated_source','controller_source','generated_source','python_source'}
def walk(x,path='root'):
    if isinstance(x,dict):
        for k,v in x.items():
            p=path+'.'+str(k)
            if str(k).lower() in source_keys and isinstance(v,str):consider(v,p)
            walk(v,p)
    elif isinstance(x,list):
        for i,v in enumerate(x):walk(v,path+f'[{i}]')
walk(native_outputs)
for i,c in enumerate(captures):
    consider(c.get('result_source'),f'capture[{i}]')

source_candidates.sort(key=lambda x:(-int(x['target_bound']),-x['semantic_token_count'],x['sha256']))
winner=next((x for x in source_candidates if x['target_bound'] and x['semantic_token_count']>=2),None)

candidate_artifact=None
if winner:
    CAND.parent.mkdir(parents=True,exist_ok=True)
    CAND.write_text(winner['source'],encoding='utf-8')
    candidate_artifact=str(CAND.relative_to(REPO))

def isolated_probe(candidate_source):
    if not candidate_source:return {'pass':False,'reason':'NO_CANDIDATE'}
    with tempfile.TemporaryDirectory(prefix='yado-v9-') as td:
        dst=Path(td)/'repo'
        shutil.copytree(REPO,dst,ignore=shutil.ignore_patterns('.git','__pycache__','*.pyc','*.sqlite'))
        tp=dst/TARGET.relative_to(REPO)
        tp.write_text(candidate_source,encoding='utf-8')
        py=sys.executable
        comp=subprocess.run([py,'-m','py_compile',str(tp)],cwd=dst,capture_output=True,text=True,timeout=30)
        if comp.returncode!=0:return {'pass':False,'compile':False,'stderr':comp.stderr[-1200:]}
        action_path=dst/ACTION.relative_to(REPO)
        original=load(action_path)
        audit_path=dst/'runtime/yado_unified_core_deep_self_audit_v1_receipt.json'
        valid=subprocess.run([py,'runtime/yado_unified_core_deep_self_audit_v1.py'],cwd=dst,capture_output=True,text=True,timeout=120)
        audit=load(audit_path) if audit_path.exists() else {}
        live=next((x for x in audit.get('findings',[]) if x.get('code')=='LIVE_RESOURCE_EVIDENCE_SCOPE'),{})
        valid_pass=(valid.returncode==0 and live.get('status')=='PASS')

        invalid=copy.deepcopy(original);invalid['direct_priority_evidence']=False
        action_path.write_text(json.dumps(invalid,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        bad=subprocess.run([py,'runtime/yado_unified_core_deep_self_audit_v1.py'],cwd=dst,capture_output=True,text=True,timeout=120)
        bad_audit=load(audit_path) if audit_path.exists() else {}
        bad_live=next((x for x in bad_audit.get('findings',[]) if x.get('code')=='LIVE_RESOURCE_EVIDENCE_SCOPE'),{})
        fail_closed=(bad.returncode==0 and bad_live.get('status')!='PASS')
        action_path.write_text(json.dumps(original,indent=2,sort_keys=True)+'\n',encoding='utf-8')

        ca=subprocess.run([py,'-m','compileall','-q','runtime'],cwd=dst,capture_output=True,text=True,timeout=120)
        tests=[
          'runtime/yado_rc8_v36/test_yado_rc8_self_audit_consistency_v1.py',
          'runtime/yado_rc8_v36/test_yado_external_runtime_contract_v1.py',
          'runtime/yado_rc8_v36/test_yado_skill_admission_runtime_v1.py',
          'runtime/yado_rc8_v36/test_yado_transfer_evaluation_runtime_v1.py',
        ]
        rg=subprocess.run([py,'-m','unittest',*tests],cwd=dst,capture_output=True,text=True,timeout=180)
        checks={'candidate_compile':True,'valid_real_evidence_closes_finding':valid_pass,
                'invalid_counterfactual_fails_closed':fail_closed,'runtime_compileall_pass':ca.returncode==0,
                'selected_regression_suite_pass':rg.returncode==0}
        return {'pass':all(checks.values()),'checks':checks,'valid_live_finding':live,'invalid_live_finding':bad_live,
                'valid_stdout_tail':valid.stdout[-1200:],'invalid_stdout_tail':bad.stdout[-1200:],
                'regression_stdout_tail':rg.stdout[-1200:],'regression_stderr_tail':rg.stderr[-1200:]}

probe=isolated_probe(winner['source'] if winner else None)
evo=native_outputs.get('controller.evolve_once') or {}
experience_blob=canon(((evo.get('child') or {}).get('experience_sources') or []))
checks={
 'canonical_v5_continuity_active':core.execution_fabric_cls.COMPONENT_ID=='RUNTIME-G2-UNIFIED-EXECUTION-FABRIC-V5',
 'v8_gene_consumed':str(gene.get('gene_digest')) in canon(experience),
 'v8_policy_receipt_consumed':str(v8.get('receipt_sha256')) in canon(experience),
 'v5_unparse_tool_consumed':str(v5src.get('receipt_sha256')) in canon(experience),
 'source_binding_gene_consumed':str(srcbind.get('receipt_sha256')) in canon(experience),
 'native_source_process_consumed':str(process.get('receipt_sha256')) in canon(experience),
 'hidden_source_emission_consumed':str(hidden.get('receipt_sha256')) in canon(experience),
 'semantic_gene_consumed':str(sem.get('receipt_sha256')) in canon(experience),
 'binder_gene_consumed':str(binder.get('gene_digest')) in canon(experience),
 'direct_action_evidence_consumed':str(action.get('receipt_sha256')) in canon(experience),
 'native_goal_created':True,
 'native_deficit_detected':bool(native_goal['deficits']),
 'native_routes_executed':bool(native_outputs),
 'native_internal_source_emission_observed':bool(captures),
 'new_target_bound_source_candidate_created':winner is not None,
 'candidate_source_compiles':winner is not None,
 'candidate_source_semantically_bound':bool(winner and winner['semantic_token_count']>=2),
 'isolated_real_evidence_probe_pass':probe.get('pass') is True,
 'host_authored_ast_subtree':False,
 'host_authored_condition_expression':False,
 'host_authored_patch':False,
 'host_source_template_used':False,
 'external_models_used':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'automatic_canonical_promotion':False,
}
positive=(
 'canonical_v5_continuity_active','v8_gene_consumed','v8_policy_receipt_consumed','v5_unparse_tool_consumed',
 'source_binding_gene_consumed','native_source_process_consumed','hidden_source_emission_consumed',
 'semantic_gene_consumed','binder_gene_consumed','direct_action_evidence_consumed',
 'native_goal_created','native_deficit_detected','native_routes_executed','native_internal_source_emission_observed',
 'new_target_bound_source_candidate_created','candidate_source_compiles','candidate_source_semantically_bound',
 'isolated_real_evidence_probe_pass','canonical_unchanged'
)
negative=('host_authored_ast_subtree','host_authored_condition_expression','host_authored_patch','host_source_template_used','external_models_used','automatic_canonical_promotion')
passed=all(checks[k] is True for k in positive) and all(checks[k] is False for k in negative)
status='PASS_SHADOW_G2_NATIVE_CONTEXTUAL_AST_TRANSFORMER_SOURCE_REALIZATION_V9' if passed else 'WITHHOLD_G2_NATIVE_CONTEXTUAL_AST_TRANSFORMER_SOURCE_REALIZATION_V9'
next_cap='NATIVE_CONTEXTUAL_AST_TRANSFORMER_FRESH_REGRESSION_ADMISSION_V10' if passed else 'NATIVE_CONTEXTUAL_AST_CONSTRUCTOR_PRIMITIVE_GENESIS_V10'

safe_caps=[]
for c in captures:
    z=dict(c);z.pop('result_source',None);safe_caps.append(z)
report={
 'schema':'yado.g2.native_contextual_ast_transformer_source_realization.v9',
 'status':status,'parent_v8_receipt':v8.get('receipt_sha256'),'v8_gene_id':gene.get('gene_id'),
 'native_goal':native_goal,'native_outputs':native_outputs,
 'native_source_capture_provenance':safe_caps,'native_internal_source_call_count':len(captures),
 'source_candidate_count':len(source_candidates),
 'selected_source_candidate':None if winner is None else {k:v for k,v in winner.items() if k!='source'},
 'candidate_artifact':candidate_artifact,'isolated_probe':probe,
 'checks':checks,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'V9 IS A STRICT SOURCE-REALIZATION TEST OF THE YADO-CREATED V8 CONTEXTUAL AST-TRANSFORMER POLICY GENE. THE HOST BINDS ONLY YADO-OWN GENE/RECEIPT/SOURCE HISTORY AND THE KERNEL-PROVENANT TARGET INTO EXPERIENCE, OBSERVES NATIVE ZERO-ARG EVOLUTION/SOURCE OUTPUTS, AND RUNS A CANDIDATE ONLY IN AN ISOLATED COPY. NO AST SUBTREE, CONDITION, PATCH, SOURCE TEMPLATE OR EXTERNAL MODEL IS PROVIDED. PASS REQUIRES NEW TARGET-BOUND COMPILING SOURCE THAT CLOSES LIVE_RESOURCE_EVIDENCE_SCOPE ONLY FOR VALID REAL EVIDENCE AND FAILS CLOSED FOR A COUNTERFACTUAL.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'native_internal_source_call_count':len(captures),
 'source_candidate_count':len(source_candidates),
 'selected_source_candidate':report['selected_source_candidate'],
 'isolated_probe':probe,'next_required_capability':next_cap,
 'checks':checks,'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True,default=str))
if not passed:raise SystemExit(2)
