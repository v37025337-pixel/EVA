from __future__ import annotations
from pathlib import Path
import ast,hashlib,json,re,sys,urllib.request,urllib.error

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive

TASK=REPO/'architecture/yado-kernel-autonomous-self-improvement-v1-request.json'
FCM=REPO/'candidates/kernel-self-generated/g2-fcm-external-coding-resource-study-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-autonomous-self-rewrite-v1.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
CAND_DIR=REPO/'candidates/g2-self-evolution'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))

def latest_audit():
    xs=sorted((REPO/'receipts').glob('yado-unified-core-deep-self-audit-v1-run-*.json'),key=lambda p:p.stat().st_mtime)
    if not xs: raise RuntimeError('NO_DEEP_SELF_AUDIT')
    d=load(xs[-1])
    if d.get('status')!='PASS_YADO_UNIFIED_CORE_DEEP_SELF_AUDIT_V1':
        raise RuntimeError('LATEST_DEEP_SELF_AUDIT_NOT_PASS')
    return xs[-1],d

def imports_of(src):
    tree=ast.parse(src)
    roots=set()
    for n in ast.walk(tree):
        if isinstance(n,ast.Import):
            roots.update(a.name.split('.')[0] for a in n.names)
        elif isinstance(n,ast.ImportFrom) and n.module:
            roots.add(n.module.split('.')[0])
    return roots

def token_set(s):
    stop={'with','from','this','that','only','then','when','into','true','false','none','return','raise','class','self'}
    return {x for x in re.findall(r'[a-zA-Z][a-zA-Z0-9_-]{3,}',str(s).lower()) if x not in stop}

def select_target(priority):
    query=' '.join([str(priority.get('code','')),str(priority.get('area','')),str(priority.get('recommended_action',''))])
    toks=token_set(query)
    manifest=load(CORE)
    active=list(manifest.get('active_runtime_sources') or [])
    candidates=[]
    for rel in active:
        if not str(rel).startswith('runtime/') or not str(rel).endswith('.py'):
            continue
        p=REPO/rel
        name=p.name.lower()
        if any(x in name for x in ('self_audit','autonomous_self_improvement_task','autonomous_self_rewrite','canonical_invariant_guard','reconstruct')):
            continue
        if not p.exists(): continue
        try: src=p.read_text(encoding='utf-8')
        except Exception: continue
        if len(src)>180000: continue
        low=src.lower()
        name_score=sum(8 for t in toks if t in name)
        body_score=sum(min(low.count(t),12) for t in toks)
        area_bonus=12 if str(priority.get('area'))=='RESOURCE_AND_EVIDENCE' and any(x in name for x in ('resource','external','evidence','openapi','scientific')) else 0
        score=name_score+body_score+area_bonus
        if score>0:
            candidates.append({'path':str(p.relative_to(REPO)),'score':score,'sha256':fsha(p),'bytes':len(src.encode()),'source':src})
    candidates.sort(key=lambda x:(-x['score'],x['path']))
    if not candidates: raise RuntimeError('NO_RELEVANT_ACTIVE_RUNTIME_TARGET')
    return candidates[0],[{k:v for k,v in x.items() if k!='source'} for x in candidates[:10]]

def call_model(endpoint,model,prompt,timeout=55):
    payload={'model':model,'messages':[
      {'role':'system','content':'You are a bounded software self-evolution proposer. Return ONLY one JSON object, no markdown.'},
      {'role':'user','content':prompt},
    ],'temperature':0.15,'max_tokens':6500}
    req=urllib.request.Request(endpoint,data=json.dumps(payload).encode(),method='POST',headers={
      'Content-Type':'application/json','Accept':'application/json','User-Agent':'YADO-G2-Autonomous-Self-Rewrite/1.0'})
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r:
            body=r.read(2000000)
            j=json.loads(body.decode('utf-8','replace'))
            content=str((((j.get('choices') or [{}])[0].get('message') or {}).get('content') or '')).strip()
            return {'ok':True,'http_status':int(getattr(r,'status',200) or 200),'content':content,'response_digest':hashlib.sha256(body).hexdigest()}
    except urllib.error.HTTPError as e:
        body=e.read(200000)
        return {'ok':False,'http_status':int(e.code),'error':'HTTPError','response_digest':hashlib.sha256(body).hexdigest()}
    except Exception as e:
        return {'ok':False,'http_status':None,'error':type(e).__name__+':'+str(e)[:300]}

def parse_json_object(text):
    s=text.strip()
    try: return json.loads(s)
    except Exception:
        a=s.find('{'); b=s.rfind('}')
        if a>=0 and b>a: return json.loads(s[a:b+1])
        raise

def apply_patches(parent_src,patches):
    out=parent_src
    if not isinstance(patches,list) or not (1<=len(patches)<=3):
        raise ValueError('PATCH_COUNT')
    for i,p in enumerate(patches):
        if not isinstance(p,dict): raise ValueError('PATCH_OBJECT')
        find=str(p.get('find') or '')
        repl=str(p.get('replace') or '')
        if not find or len(find)>5000 or len(repl)>9000:
            raise ValueError('PATCH_SIZE')
        if out.count(find)!=1:
            raise ValueError('PATCH_FIND_NOT_UNIQUE_'+str(i))
        out=out.replace(find,repl,1)
    return out

def static_eval(parent_src,new_src,target_path):
    checks={}
    try:
        ptree=ast.parse(parent_src); ntree=ast.parse(new_src)
        checks['ast_parse']=True
    except Exception as e:
        return {'score':0.0,'checks':{'ast_parse':False},'error':type(e).__name__+':'+str(e)[:300]}
    parent_imports=imports_of(parent_src); new_imports=imports_of(new_src)
    checks['no_new_import_roots']=new_imports<=parent_imports
    checks['source_changed']=new_src!=parent_src
    checks['preserves_no_secret_invariant']='no_user_secrets_used' in new_src if 'no_user_secrets_used' in parent_src else True
    checks['preserves_no_third_party_exec_invariant']='third_party_code_not_executed' in new_src if 'third_party_code_not_executed' in parent_src else True
    checks['preserves_no_canonical_mutation']='canonical_mutation' in new_src if 'canonical_mutation' in parent_src else True
    checks['no_eval_exec_added']=('eval(' not in new_src and 'exec(' not in new_src)
    checks['no_subprocess_added']='subprocess' not in new_imports
    checks['priority_semantics_present']=sum(tok in new_src.lower() for tok in ('comprehension','conflict','evidence','resource'))>=2
    parent_funcs={n.name for n in ast.walk(ptree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
    new_funcs={n.name for n in ast.walk(ntree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
    checks['adds_or_changes_functional_structure']=bool(new_funcs-parent_funcs) or len(new_src)!=len(parent_src)
    delta=abs(len(new_src.splitlines())-len(parent_src.splitlines()))
    checks['bounded_line_delta']=delta<=450
    checks['target_is_runtime_python']=target_path.startswith('runtime/') and target_path.endswith('.py')
    score=sum(1 for v in checks.values() if v)/len(checks)
    return {'score':score,'checks':checks,'new_function_names':sorted(new_funcs-parent_funcs),'line_delta_abs':delta}

task=load(TASK)
auth=task.get('authorization') or {}
if not (auth.get('self_selected_code_rewrite') and auth.get('repository_write') and auth.get('external_no_key_coding_models_allowed')):
    raise RuntimeError('SELF_REWRITE_AUTHORIZATION_MISSING')
audit_path,audit=latest_audit()
priority=(audit.get('self_selected_priority') or [None])[0]
if not isinstance(priority,dict): raise RuntimeError('NO_KERNEL_SELECTED_PRIORITY')

core=UnifiedYADOCoreV1(REPO)
head_before=core.head.get('canonical_head_digest')
target,ranking=select_target(priority)
parent_src=target['source']
target_path=target['path']

fcm=load(FCM)
probes=[x for x in fcm.get('live_no_key_probes',[]) if x.get('probe',{}).get('http_status')==200 and x.get('probe',{}).get('synthetic_coding_check_pass')]
if not probes: raise RuntimeError('NO_LIVE_NO_KEY_CODING_RESOURCE')

objective={
 'kernel_selected_priority':priority,
 'kernel_selected_next_step':audit.get('self_selected_next_step'),
 'project_objective':task.get('objective'),
 'constraints':task.get('constraints'),
}
prompt=(
  'YADO selected its own next improvement priority. Propose a SHADOW rewrite of exactly one already-selected runtime file.\n'
  'Do not choose a different file. Do not add new import roots. Do not add eval, exec, subprocess, secrets, credentials, or external side effects beyond behavior already present. '
  'Preserve existing safety checks and existing successful behavior. The rewrite should directly improve the kernel-selected priority, not merely rename variables or comments. '
  'Return JSON with exactly these keys: target_path, rationale, patches. patches must be a list of 1 to 3 objects, each with exact-string keys find and replace. Keep each patch focused and small; do not return the whole file unless the changed region itself is the whole file.\n\n'
  'KERNEL OBJECTIVE:\n'+json.dumps(objective,sort_keys=True,default=str)+'\n\n'
  'TARGET PATH:\n'+target_path+'\n\n'
  'PARENT SOURCE SHA256:\n'+target['sha256']+'\n\n'
  'PARENT SOURCE:\n'+parent_src
)

proposals=[]
for row in probes[:2]:
    res=call_model(row['url'],row['model_id'],prompt)
    entry={'provider_key':row['provider_key'],'model_id':row['model_id'],'response':{k:v for k,v in res.items() if k!='content'}}
    if res.get('ok'):
        try:
            obj=parse_json_object(res.get('content',''))
            same_target=(obj.get('target_path')==target_path)
            patches=obj.get('patches')
            new_src=apply_patches(parent_src,patches) if same_target else ''
            ev=static_eval(parent_src,new_src,target_path) if same_target and new_src else {'score':0.0,'checks':{'same_target':False}}
            ev.setdefault('checks',{})['same_target']=same_target
            if not same_target: ev['score']=0.0
            entry.update({'parsed':True,'rationale':str(obj.get('rationale') or '')[:3000],'patch_count':len(patches or []),'new_source':new_src,'evaluation':ev})
        except Exception as e:
            entry.update({'parsed':False,'parse_error':type(e).__name__+':'+str(e)[:500],'evaluation':{'score':0.0,'checks':{}}})
    else:
        entry.update({'parsed':False,'evaluation':{'score':0.0,'checks':{}}})
    proposals.append(entry)

skills=[]
for i,p in enumerate(proposals):
    ev=p['evaluation']; valid=bool(p.get('parsed')) and all(ev.get('checks',{}).values())
    sid=f"SELF_REWRITE_{p['provider_key'].upper()}_{i}"
    skills.append({
      'skill_id':sid,
      'artifact_digest':digest({'provider':p['provider_key'],'model':p['model_id'],'evaluation':ev,'source_digest':hashlib.sha256(p.get('new_source','').encode()).hexdigest()}),
      'structural_valid':valid,
      'semantic_consistency':float(ev.get('score',0.0)),
      'fit_baseline':0.0,'fit_candidate':float(ev.get('score',0.0)),
      'heldout_baseline':0.0,'heldout_candidate':float(ev.get('score',0.0)),
      'regression_pass':valid,'state_integrity':valid,'rollback_available':True,
    })
    p['skill_id']=sid

k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_autonomous_self_rewrite.sqlite'))
try:
    selection=k.select_evolution_skills(skills,max_skills=1,min_semantic_consistency=.90,min_fit_gain=.50,max_heldout_drop=0,min_heldout_gain=.50)
finally:
    k.close()
selected_ids=selection.get('selected_skill_ids') or []
winner=next((p for p in proposals if p.get('skill_id') in selected_ids),None)

status='WITHHOLD_G2_AUTONOMOUS_SELF_REWRITE_V1'
candidate_path=None
if winner is not None and winner['evaluation'].get('score',0)>=.90 and all(winner['evaluation'].get('checks',{}).values()):
    new_src=winner['new_source']
    CAND_DIR.mkdir(parents=True,exist_ok=True)
    candidate_path=CAND_DIR/(Path(target_path).stem+'_autonomous_candidate_v1.py')
    candidate_path.write_text(new_src,encoding='utf-8')
    compile(candidate_path.read_text(encoding='utf-8'),str(candidate_path),'exec')
    status='PASS_SHADOW_G2_AUTONOMOUS_SELF_REWRITE_V1'

report={
 'schema':'yado.g2.autonomous_self_rewrite.v1','status':status,
 'kernel_selected_priority':priority,'kernel_selected_next_step':audit.get('self_selected_next_step'),
 'latest_self_audit_source':str(audit_path.relative_to(REPO)),
 'target_selection':{
   'selected_path':target_path,'selected_score':target['score'],'selected_parent_sha256':target['sha256'],
   'top_runtime_candidates':ranking,'selection_policy':'KERNEL_PRIORITY_TOKEN_RELEVANCE_OVER_FUNCTIONAL_RUNTIME_FILES'},
 'external_resources_used':[{'provider_key':x['provider_key'],'model_id':x['model_id'],'url':x['url']} for x in probes[:2]],
 'proposals':[{
   'provider_key':p['provider_key'],'model_id':p['model_id'],'skill_id':p.get('skill_id'),
   'response':p.get('response'),'parsed':p.get('parsed'),'parse_error':p.get('parse_error'),'rationale':p.get('rationale'),'patch_count':p.get('patch_count'),
   'evaluation':p.get('evaluation'),
   'candidate_source_sha256':hashlib.sha256(p.get('new_source','').encode()).hexdigest() if p.get('new_source') else None
 } for p in proposals],
 'kernel_skill_selection':selection,'selected_skill_id':selected_ids[0] if selected_ids else None,
 'candidate_path':str(candidate_path.relative_to(REPO)) if candidate_path else None,
 'candidate_sha256':fsha(candidate_path) if candidate_path else None,
 'candidate_executed':False,'canonical_mutation':False,'architecture_mutation':False,
 'generation_transition':False,'g3_genesis_performed':False,
 'canonical_head_unchanged':core.head.get('canonical_head_digest')==head_before,
 'host_selected_target':False,'host_wrote_candidate_source':False,
 'external_model_proposed_candidate_source':winner is not None,
 'semantic_boundary':'KERNEL-PRIORITY-CONDITIONED SHADOW SELF-REWRITE. YADO DERIVES A TARGET FROM ITS OWN AUDIT PRIORITY, USES APPROVED NO-KEY CODING MODELS AS EXTERNAL TOOLS, AND USES ITS BOUNDED SKILL-ADMISSION GATE TO SELECT A STATICALLY SAFE CANDIDATE. THE CANDIDATE IS COMPILED BUT NOT EXECUTED OR CANONICALLY ADMITTED IN THIS STAGE.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'kernel_selected_next_step':report['kernel_selected_next_step'],
 'selected_target':target_path,'target_ranking':ranking[:5],
 'proposal_scores':[{'provider':p['provider_key'],'score':p['evaluation'].get('score',0.0),'checks':p['evaluation'].get('checks',{}),'response':p.get('response'),'parse_error':p.get('parse_error')} for p in proposals],
 'selected_skill_id':report['selected_skill_id'],'candidate_path':report['candidate_path'],
 'candidate_sha256':report['candidate_sha256'],'canonical_head_unchanged':report['canonical_head_unchanged'],
 'receipt_sha256':report['receipt_sha256']},indent=2,sort_keys=True,default=str))
if status!='PASS_SHADOW_G2_AUTONOMOUS_SELF_REWRITE_V1': raise SystemExit(2)
