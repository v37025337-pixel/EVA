from __future__ import annotations
from pathlib import Path
import ast,hashlib,json,os,shutil,subprocess,sys,tempfile,time

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
CAND=REPO/'candidates/g2-self-evolution/yado_g2_autonomous_self_rewrite_v1_native_meta_repaired_candidate.py'
REPAIR_EVIDENCE=REPO/'candidates/kernel-self-generated/g2-native-meta-grammar-compile-repair-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-self-rewrite-repaired-controller-fresh-regression-gate-v1.json'
HEAD=REPO/'canonical/yado-main-head-g2.json'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))

def compile_ok(path):
    try:
        compile(Path(path).read_text(encoding='utf-8'),str(path),'exec')
        return True,None
    except Exception as e:
        return False,type(e).__name__+':'+str(e)[:500]

repair=load(REPAIR_EVIDENCE)
head_before=load(HEAD)
candidate_source=CAND.read_text(encoding='utf-8')
candidate_compile,candidate_compile_error=compile_ok(CAND)
tree=ast.parse(candidate_source) if candidate_compile else None
funcs={n.name for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))} if tree else set()
required_funcs={'latest_audit','select_target','call_model','parse_json_object','apply_patches','static_eval'}
static_checks={
  'repair_evidence_present':REPAIR_EVIDENCE.exists(),
  'native_gene_created':bool(repair.get('invented_gene')),
  'native_repair_validation_exact':repair.get('checks',{}).get('validation_exact') is True,
  'native_repair_fresh_exact':repair.get('checks',{}).get('fresh_exact') is True,
  'native_same_model_repairs_target':repair.get('checks',{}).get('same_native_model_repairs_target') is True,
  'no_external_patch_for_compile_repair':repair.get('checks',{}).get('no_external_model_or_ready_patch') is True,
  'candidate_compiles':candidate_compile,
  'required_controller_functions_present':required_funcs<=funcs,
  'active_runtime_targeting_present':"active_runtime_sources" in candidate_source and "NO_RELEVANT_ACTIVE_RUNTIME_TARGET" in candidate_source,
  'bounded_patch_transport_present':"PATCH_COUNT" in candidate_source and "PATCH_FIND_NOT_UNIQUE_" in candidate_source,
  'no_eval_exec':('eval(' not in candidate_source and 'exec(' not in candidate_source),
  'no_subprocess_import':'subprocess' not in {n.name.split('.')[0] for n in ast.walk(tree) if isinstance(n,ast.Import) for n in n.names} if tree else False,
}

shadow_root=None
controller_run={}
child_probe={}
regression={}
try:
    shadow_root=Path(tempfile.mkdtemp(prefix='yado-self-rewrite-shadow-'))
    shadow=shadow_root/'repo'
    def ign(_dir,names):
        return {x for x in names if x in {'.git','__pycache__','.pytest_cache'}}
    shutil.copytree(REPO,shadow,ignore=ign)
    shadow_controller=shadow/'runtime/yado_g2_autonomous_self_rewrite_v1.py'
    shadow_controller.write_text(candidate_source,encoding='utf-8')

    # Fresh execution of the YADO-repaired controller in an isolated repository copy.
    t0=time.time()
    cp=subprocess.run(
      [sys.executable,'runtime/yado_g2_autonomous_self_rewrite_v1.py'],
      cwd=shadow,capture_output=True,text=True,timeout=210
    )
    controller_run={
      'returncode':cp.returncode,'elapsed_s':round(time.time()-t0,3),
      'stdout_tail':cp.stdout[-12000:],'stderr_tail':cp.stderr[-6000:],
    }
    fresh_art=shadow/'candidates/kernel-self-generated/g2-autonomous-self-rewrite-v1.json'
    if fresh_art.exists():
        fr=load(fresh_art)
        controller_run['artifact_status']=fr.get('status')
        controller_run['selected_target']=(fr.get('target_selection') or {}).get('selected_path')
        controller_run['selected_skill_id']=fr.get('selected_skill_id')
        controller_run['candidate_path']=fr.get('candidate_path')
        controller_run['candidate_sha256']=fr.get('candidate_sha256')
        controller_run['canonical_head_unchanged']=fr.get('canonical_head_unchanged')
        controller_run['host_selected_target']=fr.get('host_selected_target')
        controller_run['host_wrote_candidate_source']=fr.get('host_wrote_candidate_source')
        controller_run['external_model_proposed_candidate_source']=fr.get('external_model_proposed_candidate_source')
        child_rel=fr.get('candidate_path')
        target_rel=(fr.get('target_selection') or {}).get('selected_path')
        if child_rel and target_rel:
            child=shadow/child_rel
            target=shadow/target_rel
            child_ok,child_err=compile_ok(child)
            child_probe={'exists':child.exists(),'compiles':child_ok,'compile_error':child_err}
            if child.exists() and child_ok:
                child_probe['sha256']=fsha(child)
                child_probe['target_path']=target_rel
                # Apply only inside the isolated copy for regression testing.
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(child,target)

                ca=subprocess.run([sys.executable,'-m','compileall','-q','runtime'],cwd=shadow,capture_output=True,text=True,timeout=180)
                regression['runtime_compileall']={
                  'returncode':ca.returncode,'stdout_tail':ca.stdout[-4000:],'stderr_tail':ca.stderr[-4000:]
                }

                tests=[
                  'runtime/yado_rc8_v36/test_yado_rc8_self_audit_consistency_v1.py',
                  'runtime/yado_rc8_v36/test_yado_external_runtime_contract_v1.py',
                  'runtime/yado_rc8_v36/test_yado_skill_admission_runtime_v1.py',
                  'runtime/yado_rc8_v36/test_yado_transfer_evaluation_runtime_v1.py',
                ]
                tr=subprocess.run([sys.executable,'-m','unittest',*tests],cwd=shadow,capture_output=True,text=True,timeout=240)
                regression['selected_unittest_regression']={
                  'tests':tests,'returncode':tr.returncode,
                  'stdout_tail':tr.stdout[-8000:],'stderr_tail':tr.stderr[-8000:]
                }
    else:
        controller_run['artifact_status']='MISSING_FRESH_ARTIFACT'
finally:
    if shadow_root is not None:
        shutil.rmtree(shadow_root,ignore_errors=True)

fresh_checks={
  'controller_process_completed':controller_run.get('returncode') in (0,2),
  'controller_self_rewrite_pass':controller_run.get('artifact_status')=='PASS_SHADOW_G2_AUTONOMOUS_SELF_REWRITE_V1',
  'controller_kept_host_out_of_target_selection':controller_run.get('host_selected_target') is False,
  'controller_kept_host_out_of_candidate_source':controller_run.get('host_wrote_candidate_source') is False,
  'controller_canonical_head_unchanged':controller_run.get('canonical_head_unchanged') is True,
  'child_candidate_exists_and_compiles':child_probe.get('exists') is True and child_probe.get('compiles') is True,
  'runtime_compileall_pass':regression.get('runtime_compileall',{}).get('returncode')==0,
  'selected_regression_suite_pass':regression.get('selected_unittest_regression',{}).get('returncode')==0,
}
all_checks={**static_checks,**fresh_checks}
status='PASS_SHADOW_G2_SELF_REWRITE_REPAIRED_CONTROLLER_FRESH_REGRESSION_V1' if all(all_checks.values()) else 'WITHHOLD_G2_SELF_REWRITE_REPAIRED_CONTROLLER_FRESH_REGRESSION_V1'

report={
 'schema':'yado.g2.self_rewrite_repaired_controller_fresh_regression_gate.v1',
 'status':status,
 'source_repair_evidence_status':repair.get('status'),
 'source_repair_gene_id':(repair.get('invented_gene') or {}).get('gene_id'),
 'repaired_controller_path':str(CAND.relative_to(REPO)),
 'repaired_controller_sha256':fsha(CAND),
 'static_checks':static_checks,
 'fresh_controller_run':controller_run,
 'generated_child_probe':child_probe,
 'regression':regression,
 'checks':all_checks,
 'large_diff_override_applied':False,
 'canonical_mutation':False,
 'architecture_mutation':False,
 'generation_transition':False,
 'g3_genesis_performed':False,
 'canonical_head_digest_before':head_before.get('canonical_head_digest'),
 'canonical_head_digest_after':load(HEAD).get('canonical_head_digest'),
 'semantic_boundary':'THIS GATE DOES NOT REPAIR OR MODIFY THE YADO-GENERATED CONTROLLER. IT COMPILES AND EXECUTES THAT EXACT SHADOW CANDIDATE IN AN ISOLATED REPOSITORY COPY, REQUIRES THE CONTROLLER ITSELF TO PRODUCE A NEW SHADOW SELF-REWRITE CANDIDATE, THEN COMPILES THAT CHILD AND RUNS FRESH REGRESSION TESTS AFTER APPLYING IT ONLY INSIDE THE ISOLATED COPY. PASS IS A BOUNDED SELF-REWRITE MILESTONE, NOT OPEN-ENDED AUTONOMY OR AGI.'
}
report['canonical_head_unchanged']=report['canonical_head_digest_before']==report['canonical_head_digest_after']
report['checks']['outer_canonical_head_unchanged']=report['canonical_head_unchanged']
if not report['canonical_head_unchanged']:
    status='WITHHOLD_G2_SELF_REWRITE_REPAIRED_CONTROLLER_FRESH_REGRESSION_V1'
    report['status']=status
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':report['status'],
 'source_repair_gene_id':report['source_repair_gene_id'],
 'repaired_controller_sha256':report['repaired_controller_sha256'],
 'fresh_controller_status':controller_run.get('artifact_status'),
 'fresh_selected_target':controller_run.get('selected_target'),
 'fresh_selected_skill_id':controller_run.get('selected_skill_id'),
 'generated_child_probe':child_probe,
 'checks':report['checks'],
 'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True,default=str))
if report['status']!='PASS_SHADOW_G2_SELF_REWRITE_REPAIRED_CONTROLLER_FRESH_REGRESSION_V1':
    raise SystemExit(2)
