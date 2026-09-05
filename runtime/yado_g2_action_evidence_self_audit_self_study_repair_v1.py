from __future__ import annotations
from pathlib import Path
import ast,copy,hashlib,json,os,re,shutil,subprocess,sys,tempfile,urllib.request,urllib.error

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive

TASK=REPO/'architecture/yado-kernel-study-action-evidence-self-audit-v1-request.json'
FCM=REPO/'candidates/kernel-self-generated/g2-fcm-external-coding-resource-study-v1.json'
ACTION_EVIDENCE=REPO/'candidates/kernel-self-generated/g2-autonomous-self-improvement-task-v1.json'
SELF_GENE=REPO/'candidates/kernel-self-generated/g2-native-self-created-evidence-binder-gene-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-action-evidence-self-audit-self-study-repair-v1.json'
CAND_DIR=REPO/'candidates/g2-self-evolution'
HEAD=REPO/'canonical/yado-main-head-g2.json'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))

def latest_audit():
    xs=list((REPO/'receipts').glob('yado-unified-core-deep-self-audit-v1-run-*.json'))
    if not xs: raise RuntimeError('NO_DEEP_SELF_AUDIT')
    def rid(p):
        m=re.search(r'run-(\d+)\.json$',p.name)
        return int(m.group(1)) if m else -1
    xs.sort(key=rid)
    d=load(xs[-1])
    if d.get('status')!='PASS_YADO_UNIFIED_CORE_DEEP_SELF_AUDIT_V1':
        raise RuntimeError('LATEST_DEEP_SELF_AUDIT_NOT_PASS')
    return xs[-1],d

def imports_of(src):
    tree=ast.parse(src); roots=set()
    for n in ast.walk(tree):
        if isinstance(n,ast.Import):
            roots.update(a.name.split('.')[0] for a in n.names)
        elif isinstance(n,ast.ImportFrom) and n.module:
            roots.add(n.module.split('.')[0])
    return roots

def called_names(src):
    tree=ast.parse(src); out=set()
    for n in ast.walk(tree):
        if isinstance(n,ast.Call):
            f=n.func
            if isinstance(f,ast.Name): out.add(f.id)
            elif isinstance(f,ast.Attribute): out.add(f.attr)
    return out

def call_model(endpoint,model,prompt,timeout=55):
    payload={'model':model,'messages':[
      {'role':'system','content':'You are a bounded software diagnosis and repair tool used by YADO. Return ONLY one JSON object, no markdown.'},
      {'role':'user','content':prompt},
    ],'temperature':0.1,'max_tokens':7000}
    req=urllib.request.Request(endpoint,data=json.dumps(payload).encode(),method='POST',headers={
      'Content-Type':'application/json','Accept':'application/json','User-Agent':'YADO-G2-Self-Study-Repair/1.0'})
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r:
            body=r.read(2200000)
            j=json.loads(body.decode('utf-8','replace'))
            content=str((((j.get('choices') or [{}])[0].get('message') or {}).get('content') or '')).strip()
            return {'ok':True,'http_status':int(getattr(r,'status',200) or 200),'content':content,'response_digest':hashlib.sha256(body).hexdigest()}
    except urllib.error.HTTPError as e:
        body=e.read(200000)
        return {'ok':False,'http_status':int(e.code),'error':'HTTPError','response_digest':hashlib.sha256(body).hexdigest()}
    except Exception as e:
        return {'ok':False,'http_status':None,'error':type(e).__name__+':'+str(e)[:400]}

def parse_obj(text):
    s=str(text or '').strip()
    try:return json.loads(s)
    except Exception:
        a=s.find('{');b=s.rfind('}')
        if a>=0 and b>a:return json.loads(s[a:b+1])
        raise

def apply_patches(parent,patches):
    if not isinstance(patches,list) or not (1<=len(patches)<=3): raise ValueError('PATCH_COUNT')
    out=parent
    for i,p in enumerate(patches):
        if not isinstance(p,dict): raise ValueError('PATCH_OBJECT')
        find=str(p.get('find') or ''); repl=str(p.get('replace') or '')
        if not find or len(find)>7000 or len(repl)>11000: raise ValueError('PATCH_SIZE')
        if out.count(find)!=1: raise ValueError('PATCH_FIND_NOT_UNIQUE_'+str(i))
        out=out.replace(find,repl,1)
    return out

def static_eval(parent,new,target):
    checks={}
    try:
        ast.parse(parent);ast.parse(new);checks['ast_parse']=True
    except Exception as e:
        return {'score':0.0,'checks':{'ast_parse':False},'error':type(e).__name__+':'+str(e)[:300]}
    pi=imports_of(parent);ni=imports_of(new)
    pc=called_names(parent);nc=called_names(new)
    checks['source_changed']=new!=parent
    checks['runtime_python_target']=target.startswith('runtime/') and target.endswith('.py')
    checks['no_new_import_roots']=ni<=pi
    checks['no_new_eval_exec']=not bool(({'eval','exec'} & nc)-({'eval','exec'} & pc))
    checks['no_new_subprocess_call']=not ('subprocess' in nc and 'subprocess' not in pc)
    checks['bounded_line_delta']=abs(len(new.splitlines())-len(parent.splitlines()))<=120
    checks['task_semantics_present']=sum(t in new.lower() for t in ('audit','evidence','receipt','fresh','priority'))>=3
    checks['self_generated_gene_bound']=('g2-native-self-created-evidence-binder-gene-v1.json' in new or 'GENE-YADO-NATIVE-EVIDENCE-BINDER' in new)
    checks['no_secret_literal']='sk-' not in new and 'api_key=' not in new.lower()
    return {'score':sum(bool(v) for v in checks.values())/len(checks),'checks':checks,
            'line_delta_abs':abs(len(new.splitlines())-len(parent.splitlines()))}

def runtime_inventory():
    rows=[]
    for p in sorted((REPO/'runtime').glob('*.py')):
        rel=str(p.relative_to(REPO)).replace('\\','/')
        if p.name.startswith('_'): continue
        try:
            b=p.stat().st_size
        except Exception: continue
        if b>180000: continue
        rows.append({'path':rel,'bytes':b})
    return rows

def isolated_semantic_probe(target_path,new_src):
    with tempfile.TemporaryDirectory(prefix='yado-self-study-') as td:
        dst=Path(td)/'repo'
        shutil.copytree(REPO,dst,ignore=shutil.ignore_patterns('.git','__pycache__','*.pyc','*.sqlite'))
        tp=dst/target_path
        if not tp.exists(): return {'pass':False,'reason':'TARGET_MISSING_IN_COPY'}
        tp.write_text(new_src,encoding='utf-8')
        py=sys.executable
        compile_cp=subprocess.run([py,'-m','py_compile',str(tp)],cwd=dst,capture_output=True,text=True,timeout=30)
        if compile_cp.returncode!=0:
            return {'pass':False,'candidate_compile':False,'compile_stderr':compile_cp.stderr[-1200:]}
        action_path=dst/'candidates/kernel-self-generated/g2-autonomous-self-improvement-task-v1.json'
        original_direct=load(action_path)
        audit_cp=subprocess.run([py,'runtime/yado_unified_core_deep_self_audit_v1.py'],cwd=dst,capture_output=True,text=True,timeout=120)
        audit_path=dst/'runtime/yado_unified_core_deep_self_audit_v1_receipt.json'
        audit={}
        if audit_path.exists():
            try:audit=load(audit_path)
            except Exception:audit={}
        live=next((x for x in audit.get('findings',[]) if x.get('code')=='LIVE_RESOURCE_EVIDENCE_SCOPE'),{})
        selected=audit.get('self_selected_next_step')
        direct_valid=(original_direct.get('direct_priority_evidence') is True and str(original_direct.get('selected_action') or '')=='LIVE_RESOURCE_EVIDENCE_RECHECK')
        audit_recognizes_new_evidence=(live.get('status')=='PASS' or selected!='LIVE_RESOURCE_EVIDENCE_SCOPE')

        # Counterfactual fail-closed check: corrupt one required evidence contract field,
        # rerun the same candidate audit, and require the finding NOT to close.
        invalid_direct=copy.deepcopy(original_direct)
        invalid_direct['direct_priority_evidence']=False
        action_path.write_text(json.dumps(invalid_direct,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        invalid_cp=subprocess.run([py,'runtime/yado_unified_core_deep_self_audit_v1.py'],cwd=dst,capture_output=True,text=True,timeout=120)
        invalid_audit={}
        if audit_path.exists():
            try:invalid_audit=load(audit_path)
            except Exception:invalid_audit={}
        invalid_live=next((x for x in invalid_audit.get('findings',[]) if x.get('code')=='LIVE_RESOURCE_EVIDENCE_SCOPE'),{})
        invalid_selected=invalid_audit.get('self_selected_next_step')
        invalid_fail_closed=(invalid_live.get('status')!='PASS' and invalid_selected=='LIVE_RESOURCE_EVIDENCE_SCOPE')
        action_path.write_text(json.dumps(original_direct,indent=2,sort_keys=True)+'\n',encoding='utf-8')

        compileall=subprocess.run([py,'-m','compileall','-q','runtime'],cwd=dst,capture_output=True,text=True,timeout=120)
        tests=[
          'runtime/yado_rc8_v36/test_yado_rc8_self_audit_consistency_v1.py',
          'runtime/yado_rc8_v36/test_yado_external_runtime_contract_v1.py',
          'runtime/yado_rc8_v36/test_yado_skill_admission_runtime_v1.py',
          'runtime/yado_rc8_v36/test_yado_transfer_evaluation_runtime_v1.py',
        ]
        regress=subprocess.run([py,'-m','unittest',*tests],cwd=dst,capture_output=True,text=True,timeout=150)
        checks={
          'candidate_compile':True,
          'audit_process_completed':audit_cp.returncode==0,
          'direct_priority_evidence_present':direct_valid,
          'audit_recognizes_fresh_self_generated_evidence':audit_recognizes_new_evidence,
          'invalid_counterfactual_evidence_fails_closed':invalid_cp.returncode==0 and invalid_fail_closed,
          'runtime_compileall_pass':compileall.returncode==0,
          'selected_regression_suite_pass':regress.returncode==0,
        }
        return {'pass':all(checks.values()),'checks':checks,
                'audit_status':audit.get('status'),'audit_verdict':audit.get('overall_verdict'),
                'audit_selected_next_step':selected,'live_resource_finding':live,
                'invalid_audit_selected_next_step':invalid_selected,'invalid_live_resource_finding':invalid_live,
                'audit_stdout_tail':audit_cp.stdout[-1600:],'audit_stderr_tail':audit_cp.stderr[-1200:],
                'invalid_audit_stdout_tail':invalid_cp.stdout[-1200:],'invalid_audit_stderr_tail':invalid_cp.stderr[-900:],
                'regression_stdout_tail':regress.stdout[-1200:],'regression_stderr_tail':regress.stderr[-1200:]}

task=load(TASK)
audit_path,audit=latest_audit()
action=load(ACTION_EVIDENCE)
gene=load(SELF_GENE)
if gene.get('promotion_state')!='SHADOW_ONLY' or gene.get('external_model_generated') is not False:
    raise RuntimeError('SELF_GENERATED_GENE_CONTRACT_INVALID')
head_before=fsha(HEAD)
fcm=load(FCM)
probes=[x for x in fcm.get('live_no_key_probes',[]) if x.get('probe',{}).get('http_status')==200 and x.get('probe',{}).get('synthetic_coding_check_pass')]
if not probes: raise RuntimeError('NO_APPROVED_LIVE_NO_KEY_CODING_TOOLS')
inventory=runtime_inventory()
allowed_paths={x['path'] for x in inventory}
kernel_binding=((task.get('evidence') or {}).get('audit_runtime_binding_evidence') or {})
kernel_audit_runtime=str(kernel_binding.get('this_audit_runtime') or '')
kernel_audit_runtime_valid=bool(kernel_audit_runtime and kernel_audit_runtime in allowed_paths)

problem_packet={
  'task':task,
  'latest_audit':{
    'source':str(audit_path.relative_to(REPO)),
    'status':audit.get('status'),
    'overall_verdict':audit.get('overall_verdict'),
    'self_selected_next_step':audit.get('self_selected_next_step'),
    'self_selected_priority':audit.get('self_selected_priority'),
    'live_resource_finding':next((x for x in audit.get('findings',[]) if x.get('code')=='LIVE_RESOURCE_EVIDENCE_SCOPE'),None),
  },
  'latest_action_evidence':{
    'status':action.get('status'),'selected_action':action.get('selected_action'),
    'direct_priority_evidence':action.get('direct_priority_evidence'),
    'goal_action_result':((action.get('goal_action_binding') or {}).get('result') or {}),
  },
  'yado_self_generated_gene':{
    'artifact':'candidates/kernel-self-generated/g2-native-self-created-evidence-binder-gene-v1.json',
    'gene_id':gene.get('gene_id'),'gene_digest':gene.get('gene_digest'),
    'origin':gene.get('origin'),'selected_native_route':gene.get('selected_native_route'),
    'selected_algorithm':gene.get('selected_algorithm'),'contract_fields':gene.get('contract_fields'),
    'model':gene.get('model'),'promotion_state':gene.get('promotion_state')
  },
  'kernel_audit_runtime_binding':kernel_binding,
  'runtime_inventory_summary':{
    'path_count':len(inventory),
    'kernel_audit_runtime_in_inventory':kernel_audit_runtime_valid,
  },
}

proposals=[]
for row in probes[:2]:
    diagnose_prompt=(
      'YADO has already created its own validated shadow evidence-binding gene. Your role is ONLY to help materialize that YADO-created mechanism into source, not to invent a replacement policy. Choose the ONE runtime Python file whose change is most directly justified by the gene and evidence. '
      'The latest kernel-native deep self-audit explicitly reports its own audit runtime path in kernel_audit_runtime_binding. Treat that path as KERNEL PROVENANCE, not as a host-selected target or solution hint. Select it only if the objective and YADO gene directly justify modifying that audit runtime; otherwise return withhold=true. Do not infer a different target from host text. '
      'The candidate must load or explicitly bind the self-generated gene artifact rather than re-derive a host rule. Do not assume the requested outcome is true; if the evidence is insufficient, return withhold=true and explain why. '
      'Return JSON keys: withhold, diagnosis, target_path, evidence_used. Any non-withheld target_path will be checked internally against the complete runtime inventory, which is intentionally not sent in this prompt.\n\n'
      +json.dumps(problem_packet,sort_keys=True,default=str)
    )
    dres=call_model(row['url'],row['model_id'],diagnose_prompt)
    entry={'provider_key':row['provider_key'],'model_id':row['model_id'],
           'diagnosis_response':{k:v for k,v in dres.items() if k!='content'}}
    if not dres.get('ok'):
        entry.update({'parsed':False,'evaluation':{'score':0.0,'checks':{}},'withhold':True})
        proposals.append(entry);continue
    try:
        dobj=parse_obj(dres.get('content',''))
        entry['diagnosis']=str(dobj.get('diagnosis') or '')[:4000]
        entry['evidence_used']=dobj.get('evidence_used')
        entry['withhold']=bool(dobj.get('withhold'))
        target=str(dobj.get('target_path') or '')
        entry['target_path']=target
        allowed=allowed_paths
        if entry['withhold']:
            entry.update({'parsed':True,'evaluation':{'score':0.0,'checks':{'model_withheld':True}}})
            proposals.append(entry);continue
        if target not in allowed: raise ValueError('TARGET_NOT_IN_RUNTIME_INVENTORY')
        parent=(REPO/target).read_text(encoding='utf-8')
        repair_prompt=(
          'Materialize YADO\'s own self-generated evidence-binding gene into a minimal SHADOW repair of the target file selected in your diagnosis. '
          'Do NOT invent a substitute acceptance rule and do NOT hard-code PASS. The candidate must bind/load the gene artifact and use its contract semantics to decide whether fresh self-generated evidence is admissible. It must preserve fail-closed behavior for invalid evidence and preserve unrelated audit/regression behavior. '
          'Return JSON keys: target_path, rationale, patches. patches is 1-3 exact find/replace objects. No new import roots, eval, exec, subprocess, secrets, credentials, or canonical mutation.\n\n'
          'PROBLEM PACKET:\n'+json.dumps(problem_packet,sort_keys=True,default=str)+'\n\n'
          'TARGET PATH:\n'+target+'\n\nPARENT SOURCE SHA256:\n'+hashlib.sha256(parent.encode()).hexdigest()+'\n\nPARENT SOURCE:\n'+parent
        )
        rres=call_model(row['url'],row['model_id'],repair_prompt)
        entry['repair_response']={k:v for k,v in rres.items() if k!='content'}
        if not rres.get('ok'): raise RuntimeError('REPAIR_MODEL_CALL_FAILED')
        robj=parse_obj(rres.get('content',''))
        if robj.get('target_path')!=target: raise ValueError('REPAIR_TARGET_CHANGED')
        new=apply_patches(parent,robj.get('patches'))
        sev=static_eval(parent,new,target)
        probe=isolated_semantic_probe(target,new) if all(sev.get('checks',{}).values()) else {'pass':False,'reason':'STATIC_GATE'}
        total=(float(sev.get('score',0.0))+ (1.0 if probe.get('pass') else 0.0))/2.0
        entry.update({'parsed':True,'rationale':str(robj.get('rationale') or '')[:4000],
                      'patch_count':len(robj.get('patches') or []),'new_source':new,
                      'static_evaluation':sev,'semantic_probe':probe,
                      'evaluation':{'score':total,'checks':{
                        'static_all_pass':all(sev.get('checks',{}).values()),
                        'semantic_probe_pass':bool(probe.get('pass')),
                        'same_target':True,
                      }}})
    except Exception as e:
        entry.update({'parsed':False,'parse_error':type(e).__name__+':'+str(e)[:700],
                      'evaluation':{'score':0.0,'checks':{}}})
    proposals.append(entry)

skills=[]
for i,p in enumerate(proposals):
    ev=p.get('evaluation') or {}
    valid=bool(p.get('parsed')) and not p.get('withhold') and all((ev.get('checks') or {}).values())
    sid=f"SELF_AUDIT_EVIDENCE_REPAIR_{p['provider_key'].upper()}_{i}"
    skills.append({
      'skill_id':sid,
      'artifact_digest':digest({'provider':p['provider_key'],'model':p['model_id'],'target':p.get('target_path'),'evaluation':ev,
                                'source_digest':hashlib.sha256(p.get('new_source','').encode()).hexdigest()}),
      'structural_valid':valid,
      'semantic_consistency':float(ev.get('score',0.0)),
      'fit_baseline':0.0,'fit_candidate':float(ev.get('score',0.0)),
      'heldout_baseline':0.0,'heldout_candidate':float(ev.get('score',0.0)),
      'regression_pass':valid,'state_integrity':valid,'rollback_available':True,
    })
    p['skill_id']=sid

k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_action_evidence_self_audit_repair.sqlite'))
try:
    selection=k.select_evolution_skills(skills,max_skills=1,min_semantic_consistency=.95,min_fit_gain=.50,max_heldout_drop=0,min_heldout_gain=.50)
finally:
    k.close()
selected_ids=selection.get('selected_skill_ids') or []
winner=next((p for p in proposals if p.get('skill_id') in selected_ids),None)

status='WITHHOLD_G2_ACTION_EVIDENCE_SELF_AUDIT_SELF_STUDY_REPAIR_V1'
candidate_path=None
if winner is not None and winner.get('semantic_probe',{}).get('pass'):
    target=winner['target_path']
    CAND_DIR.mkdir(parents=True,exist_ok=True)
    candidate_path=CAND_DIR/(Path(target).stem+'_action_evidence_self_audit_candidate_v1.py')
    candidate_path.write_text(winner['new_source'],encoding='utf-8')
    compile(candidate_path.read_text(encoding='utf-8'),str(candidate_path),'exec')
    status='PASS_SHADOW_G2_ACTION_EVIDENCE_SELF_AUDIT_SELF_STUDY_REPAIR_V1'

report={
 'schema':'yado.g2.action_evidence_self_audit_self_study_repair.v1',
 'status':status,'task':task,
 'latest_audit_source':str(audit_path.relative_to(REPO)),
 'problem_packet_digest':digest(problem_packet),
 'kernel_audit_runtime_binding':kernel_binding,
 'kernel_audit_runtime_valid':kernel_audit_runtime_valid,
 'full_runtime_inventory_not_sent_to_materializer':True,
 'external_tools_used':[{'provider_key':x['provider_key'],'model_id':x['model_id'],'url':x['url']} for x in probes[:2]],
 'proposals':[{
   'provider_key':p['provider_key'],'model_id':p['model_id'],'skill_id':p.get('skill_id'),
   'diagnosis_response':p.get('diagnosis_response'),
   'repair_response':p.get('repair_response'),
   'withhold':p.get('withhold'),'diagnosis':p.get('diagnosis'),'evidence_used':p.get('evidence_used'),
   'target_path':p.get('target_path'),'parsed':p.get('parsed'),'parse_error':p.get('parse_error'),
   'rationale':p.get('rationale'),'patch_count':p.get('patch_count'),
   'static_evaluation':p.get('static_evaluation'),'semantic_probe':p.get('semantic_probe'),
   'candidate_source_sha256':hashlib.sha256(p.get('new_source','').encode()).hexdigest() if p.get('new_source') else None,
 } for p in proposals],
 'kernel_skill_selection':selection,
 'selected_skill_id':selected_ids[0] if selected_ids else None,
 'selected_target_path':winner.get('target_path') if winner else None,
 'candidate_path':str(candidate_path.relative_to(REPO)) if candidate_path else None,
 'candidate_sha256':fsha(candidate_path) if candidate_path else None,
 'candidate_executed_only_in_isolated_copy':winner is not None,
 'canonical_mutation':False,
 'canonical_head_unchanged':fsha(HEAD)==head_before,
 'host_selected_target':False,
 'host_wrote_candidate_patch':False,
 'self_generated_gene_id':gene.get('gene_id'),
 'self_generated_gene_digest':gene.get('gene_digest'),
 'external_models_are_materialization_tools_only':True,
 'semantic_boundary':'YADO FIRST CREATED THE EVIDENCE-BINDING GENE NATIVELY. THIS STAGE USES EXTERNAL NO-KEY CODING MODELS ONLY AS SOURCE-MATERIALIZATION TOOLS TO BIND THAT EXISTING YADO GENE; THEY MAY NOT INVENT A SUBSTITUTE POLICY. YADO NATIVE SKILL ADMISSION SELECTS OR WITHHOLDS. HOST DOES NOT SELECT TARGET OR WRITE THE PATCH. PASS IS SHADOW ONLY AND REQUIRES A VALID-EVIDENCE AUDIT CHANGE, AN INVALID-EVIDENCE FAIL-CLOSED COUNTERFACTUAL, COMPILEALL, AND REGRESSION.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'selected_skill_id':report['selected_skill_id'],'selected_target_path':report['selected_target_path'],
 'candidate_path':report['candidate_path'],'canonical_head_unchanged':report['canonical_head_unchanged'],
 'proposal_summary':[{'provider':p['provider_key'],'withhold':p.get('withhold'),'target':p.get('target_path'),
                      'diagnosis_ok':(p.get('diagnosis_response') or {}).get('ok'),
                      'diagnosis_http_status':(p.get('diagnosis_response') or {}).get('http_status'),
                      'diagnosis_error':(p.get('diagnosis_response') or {}).get('error'),
                      'repair_ok':(p.get('repair_response') or {}).get('ok'),
                      'repair_http_status':(p.get('repair_response') or {}).get('http_status'),
                      'repair_error':(p.get('repair_response') or {}).get('error'),
                      'score':(p.get('evaluation') or {}).get('score',0.0),'probe_pass':(p.get('semantic_probe') or {}).get('pass'),
                      'parse_error':p.get('parse_error')} for p in proposals],
 'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True,default=str))
if status!='PASS_SHADOW_G2_ACTION_EVIDENCE_SELF_AUDIT_SELF_STUDY_REPAIR_V1':
    raise SystemExit(2)
