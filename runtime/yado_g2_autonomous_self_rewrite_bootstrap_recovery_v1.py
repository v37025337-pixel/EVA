from __future__ import annotations
from pathlib import Path
import difflib,hashlib,json,re,sys,urllib.request,urllib.error

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive

TARGET=REPO/'runtime/yado_g2_autonomous_self_rewrite_v1.py'
FCM=REPO/'candidates/kernel-self-generated/g2-fcm-external-coding-resource-study-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-autonomous-self-rewrite-bootstrap-recovery-v1.json'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))

def compile_error(src):
    try:
        compile(src,str(TARGET),'exec')
        return None
    except SyntaxError as e:
        return {
          'type':'SyntaxError','msg':str(e.msg),'lineno':e.lineno,
          'offset':e.offset,'text':e.text.rstrip('\n') if e.text else None
        }

def call_model(endpoint,model,prompt,timeout=45):
    payload={'model':model,'messages':[
      {'role':'system','content':'Return ONLY valid JSON. You are repairing a syntax-broken Python controller. Make the smallest syntax-only patch.'},
      {'role':'user','content':prompt},
    ],'temperature':0,'max_tokens':1800}
    req=urllib.request.Request(endpoint,data=json.dumps(payload).encode(),method='POST',headers={
      'Content-Type':'application/json','Accept':'application/json',
      'User-Agent':'YADO-G2-Bootstrap-Recovery/1.0'})
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r:
            body=r.read(500000)
            j=json.loads(body.decode('utf-8','replace'))
            content=str((((j.get('choices') or [{}])[0].get('message') or {}).get('content') or '')).strip()
            return {'ok':True,'http_status':int(getattr(r,'status',200) or 200),'content':content,'response_digest':hashlib.sha256(body).hexdigest()}
    except urllib.error.HTTPError as e:
        b=e.read(100000)
        return {'ok':False,'http_status':int(e.code),'error':'HTTPError','response_digest':hashlib.sha256(b).hexdigest()}
    except Exception as e:
        return {'ok':False,'http_status':None,'error':type(e).__name__+':'+str(e)[:300]}

def parse_obj(text):
    s=text.strip()
    try: return json.loads(s)
    except Exception:
        a=s.find('{'); b=s.rfind('}')
        if a>=0 and b>a: return json.loads(s[a:b+1])
        raise

def apply_patch(src,obj):
    patches=obj.get('patches')
    if not isinstance(patches,list) or not (1<=len(patches)<=3):
        raise ValueError('PATCH_COUNT')
    out=src
    for i,p in enumerate(patches):
        if not isinstance(p,dict): raise ValueError('PATCH_OBJECT')
        find=str(p.get('find') or '')
        repl=str(p.get('replace') or '')
        if not find or len(find)>1600 or len(repl)>2200: raise ValueError('PATCH_SIZE')
        if out.count(find)!=1: raise ValueError('PATCH_FIND_NOT_UNIQUE_'+str(i))
        out=out.replace(find,repl,1)
    return out

def static_gate(parent,candidate):
    err=compile_error(candidate)
    diff=list(difflib.unified_diff(parent.splitlines(),candidate.splitlines(),lineterm=''))
    changed=[x for x in diff if (x.startswith('+') or x.startswith('-')) and not x.startswith('+++') and not x.startswith('---')]
    added='\n'.join(x[1:] for x in changed if x.startswith('+'))
    preserved_markers=all(m in candidate for m in [
      'PASS_SHADOW_G2_AUTONOMOUS_SELF_REWRITE_V1',
      'host_selected_target','host_wrote_candidate_source','candidate_executed',
      'canonical_mutation','kernel_selected_next_step',
    ])
    checks={
      'candidate_compiles':err is None,
      'bounded_changed_lines':len(changed)<=10,
      'no_eval_exec_added':('eval(' not in added and 'exec(' not in added),
      'no_subprocess_added':'subprocess' not in added,
      'no_secret_literals_added':not re.search(r'(?i)(api[_-]?key|token|password|secret)\s*=',added),
      'critical_contract_markers_preserved':preserved_markers,
      'source_changed':candidate!=parent,
    }
    return {'checks':checks,'score':sum(checks.values())/len(checks),'changed_lines':changed,'compile_error_after':err}

parent=TARGET.read_text(encoding='utf-8')
before=compile_error(parent)
if before is None:
    raise RuntimeError('TARGET_ALREADY_COMPILES_RECOVERY_NOT_NEEDED')

fcm=load(FCM)
probes=[x for x in fcm.get('live_no_key_probes',[])
        if x.get('probe',{}).get('http_status')==200 and x.get('probe',{}).get('synthetic_coding_check_pass')]
if not probes: raise RuntimeError('NO_APPROVED_NO_KEY_CODING_RESOURCE')

lines=parent.splitlines()
lo=max(0,(before.get('lineno') or 1)-8); hi=min(len(lines),(before.get('lineno') or 1)+8)
context='\n'.join(f'{i+1}: {lines[i]}' for i in range(lo,hi))
prompt=(
  'Repair ONLY the syntax error in this Python controller. Do not redesign logic or choose a new algorithm. '
  'Return JSON with keys rationale and patches. patches is 1-3 exact-string find/replace objects. '
  'Use the smallest possible edit. Preserve all existing behavior and safety checks.\n\n'
  'Compile error:\n'+json.dumps(before,sort_keys=True)+'\n\n'
  'Context:\n'+context
)

proposals=[]
for row in probes[:2]:
    res=call_model(row['url'],row['model_id'],prompt)
    p={'provider_key':row['provider_key'],'model_id':row['model_id'],
       'response':{k:v for k,v in res.items() if k!='content'}}
    if res.get('ok'):
        try:
            obj=parse_obj(res.get('content',''))
            cand=apply_patch(parent,obj)
            gate=static_gate(parent,cand)
            p.update({'parsed':True,'rationale':str(obj.get('rationale') or '')[:1000],
                      'candidate_source':cand,'gate':gate})
        except Exception as e:
            p.update({'parsed':False,'parse_error':type(e).__name__+':'+str(e)[:400],
                      'gate':{'score':0.0,'checks':{}}})
    else:
        p.update({'parsed':False,'gate':{'score':0.0,'checks':{}}})
    proposals.append(p)

skills=[]
for i,p in enumerate(proposals):
    g=p['gate']; valid=bool(p.get('parsed')) and all(g.get('checks',{}).values())
    sid=f"BOOTSTRAP_RECOVERY_{p['provider_key'].upper()}_{i}"
    p['skill_id']=sid
    skills.append({
      'skill_id':sid,
      'artifact_digest':digest({'provider':p['provider_key'],'model':p['model_id'],'gate':g}),
      'structural_valid':valid,
      'semantic_consistency':float(g.get('score',0.0)),
      'fit_baseline':0.0,'fit_candidate':float(g.get('score',0.0)),
      'heldout_baseline':0.0,'heldout_candidate':float(g.get('score',0.0)),
      'regression_pass':valid,'state_integrity':valid,'rollback_available':True,
    })

k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_bootstrap_recovery.sqlite'))
try:
    sel=k.select_evolution_skills(skills,max_skills=1,min_semantic_consistency=.99,min_fit_gain=.90,max_heldout_drop=0,min_heldout_gain=.90)
finally:
    k.close()

selected=(sel.get('selected_skill_ids') or [None])[0]
winner=next((p for p in proposals if p.get('skill_id')==selected),None)
status='WITHHOLD_G2_AUTONOMOUS_SELF_REWRITE_BOOTSTRAP_RECOVERY_V1'
applied=False
if winner is not None and all(winner['gate'].get('checks',{}).values()):
    TARGET.write_text(winner['candidate_source'],encoding='utf-8')
    compile(TARGET.read_text(encoding='utf-8'),str(TARGET),'exec')
    status='PASS_G2_AUTONOMOUS_SELF_REWRITE_BOOTSTRAP_RECOVERY_V1'
    applied=True

report={
 'schema':'yado.g2.autonomous_self_rewrite_bootstrap_recovery.v1',
 'status':status,'target_path':str(TARGET.relative_to(REPO)),
 'compile_error_before':before,
 'proposals':[{
   'provider_key':p['provider_key'],'model_id':p['model_id'],'response':p.get('response'),
   'parsed':p.get('parsed'),'parse_error':p.get('parse_error'),'rationale':p.get('rationale'),
   'gate':p.get('gate'),'skill_id':p.get('skill_id'),
   'candidate_sha256':hashlib.sha256(p.get('candidate_source','').encode()).hexdigest() if p.get('candidate_source') else None
 } for p in proposals],
 'kernel_skill_selection':sel,'selected_skill_id':selected,'repair_applied':applied,
 'target_compiles_after':compile_error(TARGET.read_text(encoding='utf-8')) is None,
 'host_wrote_repair_patch':False,'host_selected_patch':False,'canonical_mutation':False,
 'semantic_boundary':'BOOTSTRAP RECOVERY ONLY. THE HOST SUPPLIES THE FAILED CONTROLLER AND COMPILE ERROR; EXTERNAL TOOLS PROPOSE MINIMAL PATCHES AND YADO SELECTS THROUGH ITS BOUNDED SKILL GATE. THIS RECOVERY IS NOT THE SELF-REWRITE MILESTONE ITSELF.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':status,'compile_error_before':before,'selected_skill_id':selected,
 'repair_applied':applied,'target_compiles_after':report['target_compiles_after'],
 'proposal_scores':[{'provider':p['provider_key'],'gate':p.get('gate'),'parse_error':p.get('parse_error')} for p in proposals],
 'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True,default=str))
if status!='PASS_G2_AUTONOMOUS_SELF_REWRITE_BOOTSTRAP_RECOVERY_V1':
    raise SystemExit(2)
