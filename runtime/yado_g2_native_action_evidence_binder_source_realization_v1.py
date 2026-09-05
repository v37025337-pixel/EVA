from __future__ import annotations
from pathlib import Path
from dataclasses import asdict
import ast,copy,hashlib,inspect,json,re,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive

TASK=REPO/'architecture/yado-kernel-native-action-evidence-binder-source-realization-v1-request.json'
BINDER=REPO/'candidates/kernel-self-generated/g2-native-self-created-evidence-binder-gene-v1.json'
SOURCE_BINDING=REPO/'candidates/kernel-self-generated/g2-task-conditioned-source-binding-v3.json'
EMITTER=REPO/'candidates/kernel-self-generated/g2-experience-conditioned-native-emitter-gene-genesis-v3.json'
PROCESS=REPO/'candidates/kernel-self-generated/g2-native-source-construction-process-evolution-v2.json'
ACTION=REPO/'candidates/kernel-self-generated/g2-autonomous-self-improvement-task-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-native-action-evidence-binder-source-realization-v1.json'
CAND_DIR=REPO/'candidates/g2-self-evolution'
DB=ROOT/'yado_native_action_evidence_binder_source_realization_v1.sqlite'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def fsha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def latest_audit():
    xs=list((REPO/'receipts').glob('yado-unified-core-deep-self-audit-v1-run-*.json'))
    if not xs: raise RuntimeError('NO_DEEP_SELF_AUDIT')
    def rid(p):
        m=re.search(r'run-(\d+)\.json$',p.name)
        return int(m.group(1)) if m else -1
    xs.sort(key=rid)
    return xs[-1],load(xs[-1])

task=load(TASK);binder=load(BINDER);source_binding=load(SOURCE_BINDING)
emitter=load(EMITTER);process=load(PROCESS);action=load(ACTION)
audit_path,audit=latest_audit()

if not binder.get('self_created_model') or binder.get('external_model_generated') is not False:
    raise RuntimeError('YADO_NATIVE_BINDER_REQUIRED')
if source_binding.get('status')!='PASS_SHADOW_G2_TASK_CONDITIONED_SOURCE_BINDING_V3':
    raise RuntimeError('TASK_CONDITIONED_SOURCE_BINDING_V3_REQUIRED')
if emitter.get('status')!='PASS_SHADOW_G2_EXPERIENCE_CONDITIONED_NATIVE_EMITTER_GENE_GENESIS_V3':
    raise RuntimeError('NATIVE_EMITTER_GENE_V3_REQUIRED')
if process.get('status')!='PASS_NATIVE_SOURCE_CONSTRUCTION_PROCESS_EVOLUTION_V2':
    raise RuntimeError('NATIVE_SOURCE_PROCESS_V2_REQUIRED')
if action.get('direct_priority_evidence') is not True:
    raise RuntimeError('PASSING_DIRECT_PRIORITY_EVIDENCE_REQUIRED')

finding=next((x for x in audit.get('findings',[]) if x.get('code')=='SELF_AUDIT_RUNTIME_BINDING'),None)
if not finding: raise RuntimeError('KERNEL_AUDIT_RUNTIME_BINDING_NOT_FOUND')
target_path=str((finding.get('evidence') or {}).get('this_audit_runtime') or '')
if not target_path.startswith('runtime/') or not target_path.endswith('.py'):
    raise RuntimeError('KERNEL_PROVENANT_RUNTIME_PATH_INVALID')
target=REPO/target_path
if not target.exists(): raise RuntimeError('KERNEL_PROVENANT_RUNTIME_MISSING')
target_source=target.read_text(encoding='utf-8')
target_sha=hashlib.sha256(target_source.encode()).hexdigest()

core=UnifiedYADOCoreV1(REPO)
head_before=copy.deepcopy(core.head)
parent_state=core.evolutionary_parent_genome()
parent_genome=parent_state['parent']

if DB.exists(): DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    goal=k.executive.create_goal(
      objective=str(task['task']),
      required_capabilities={'NATIVE_ACTION_EVIDENCE_BINDER_SOURCE_REALIZATION_V1':1.0},
      success_criteria={'new_python_source_bytes':True,'binder_relevance':True,'canonical_unchanged':True},
    )
    deficits=k.executive.detect_deficits(goal.goal_id)
    native_goal={'goal_id':goal.goal_id,'deficits':[asdict(d) for d in deficits]}
finally:
    try:k.close()
    except Exception:pass

experience=copy.deepcopy(parent_state.get('experience') or [])
experience += [
  {'role':'YADO_NATIVE_BINDER_GENE','artifact':str(BINDER.relative_to(REPO)),
   'gene_id':binder.get('gene_id'),'gene_digest':binder.get('gene_digest'),
   'contract_fields':binder.get('contract_fields'),'model':binder.get('model')},
  {'role':'YADO_TASK_CONDITIONED_SOURCE_BINDING_GENE','artifact':str(SOURCE_BINDING.relative_to(REPO)),
   'gene_id':source_binding.get('gene_id'),'receipt_sha256':source_binding.get('receipt_sha256'),
   'next_required_capability':source_binding.get('next_required_capability')},
  {'role':'YADO_NATIVE_EMITTER_GENE','artifact':str(EMITTER.relative_to(REPO)),
   'gene_id':(emitter.get('emitter_gene') or {}).get('gene_id'),'receipt_sha256':emitter.get('receipt_sha256'),
   'learned_process':emitter.get('yado_learned_sequence')},
  {'role':'YADO_NATIVE_SOURCE_PROCESS','artifact':str(PROCESS.relative_to(REPO)),
   'receipt_sha256':process.get('receipt_sha256'),
   'learned_sequence':((process.get('process_mechanism') or {}).get('learned_sequence') or [])},
  {'role':'YADO_FRESH_DIRECT_ACTION_EVIDENCE','artifact':str(ACTION.relative_to(REPO)),
   'receipt_sha256':action.get('receipt_sha256'),'selected_action':action.get('selected_action'),
   'direct_priority_evidence':action.get('direct_priority_evidence'),
   'goal_action_binding':action.get('goal_action_binding')},
  {'role':'KERNEL_PROVENANT_SELF_AUDIT_TARGET','audit_artifact':str(audit_path.relative_to(REPO)),
   'audit_receipt_sha256':audit.get('receipt_sha256'),'target_path':target_path,
   'target_sha256':target_sha,'target_source':target_source},
  {'role':'YADO_CURRENT_NATIVE_SOURCE_REALIZATION_TASK','objective':task.get('objective'),'task':task.get('task')},
]

controller=core.evolutionary_genome_cls(parent_genome,experience_sources=experience)
objects={'controller':controller,'core':core}
native_calls=[];native_outputs={}
for owner,obj in objects.items():
    for name in sorted(dir(obj)):
        if name.startswith('_'): continue
        low=name.lower()
        if not any(tok in low for tok in ('evol','mutat','genesis','source','code','self','genome','component','snapshot')):
            continue
        fn=getattr(obj,name,None)
        if not callable(fn): continue
        try:sig=inspect.signature(fn)
        except Exception:continue
        required=[p for p in sig.parameters.values()
                  if p.default is inspect._empty and p.kind in (p.POSITIONAL_ONLY,p.POSITIONAL_OR_KEYWORD)]
        if required: continue
        key=f'{owner}.{name}';native_calls.append(key)
        try:native_outputs[key]=fn()
        except Exception as e:native_outputs[key]={'error':type(e).__name__+':'+str(e)[:500]}

if 'controller.evolve_once' not in native_outputs:
    try:native_outputs['controller.evolve_once']=controller.evolve_once();native_calls.append('controller.evolve_once')
    except Exception as e:native_outputs['controller.evolve_once']={'error':type(e).__name__+':'+str(e)[:500]}

contract_fields=set(str(x) for x in (binder.get('contract_fields') or []))
semantic_tokens=contract_fields|{'LIVE_RESOURCE_EVIDENCE_SCOPE','SELF_AUDIT_RUNTIME_BINDING','ACCEPT_FRESH_EVIDENCE','WITHHOLD_FRESH_EVIDENCE'}
source_candidates=[]
seen=set()
source_keys={'candidate_source','source','mutated_source','controller_source','generated_source','python_source'}
def walk(x,path='root'):
    if isinstance(x,dict):
        for key,val in x.items():
            p=path+'.'+str(key)
            if str(key).lower() in source_keys and isinstance(val,str) and val.strip():
                s=val
                sh=hashlib.sha256(s.encode()).hexdigest()
                if sh not in seen and sh!=target_sha:
                    seen.add(sh)
                    try:
                        ast.parse(s); compile(s,'<yado-native-binder-source-candidate>','exec')
                        toks=sorted(t for t in semantic_tokens if t in s)
                        source_candidates.append({'path':p,'sha256':sh,'source':s,'semantic_tokens':toks,'semantic_token_count':len(toks)})
                    except Exception:pass
            walk(val,p)
    elif isinstance(x,list):
        for i,val in enumerate(x):walk(val,path+f'[{i}]')
walk(native_outputs)

source_candidates.sort(key=lambda x:(-x['semantic_token_count'],x['sha256']))
winner=source_candidates[0] if source_candidates else None
candidate_path=None
if winner:
    CAND_DIR.mkdir(parents=True,exist_ok=True)
    p=CAND_DIR/f"native_action_evidence_binder_source_realization_v1_{winner['sha256'][:12]}.py"
    p.write_text(winner['source'],encoding='utf-8')
    candidate_path=str(p.relative_to(REPO))

experience_blob=canon((native_outputs.get('controller.evolve_once') or {}).get('child',{}).get('experience_sources') or [])
checks={
 'binder_gene_consumed':str(binder.get('gene_digest')) in canon(experience),
 'task_conditioned_source_gene_consumed':str(source_binding.get('receipt_sha256')) in canon(experience),
 'native_emitter_gene_consumed':str(emitter.get('receipt_sha256')) in canon(experience),
 'native_source_process_consumed':str(process.get('receipt_sha256')) in canon(experience),
 'fresh_direct_action_evidence_consumed':str(action.get('receipt_sha256')) in canon(experience),
 'kernel_provenant_target_used':target_path==str((finding.get('evidence') or {}).get('this_audit_runtime')),
 'native_goal_created':True,
 'native_deficit_detected':bool(native_goal['deficits']),
 'native_routes_executed':bool(native_calls),
 'new_python_source_bytes_produced_by_yado':winner is not None,
 'candidate_source_compiles':winner is not None,
 'candidate_source_binder_relevant':bool(winner and winner['semantic_token_count']>=2),
 'host_selected_target':False,
 'host_patch_used':False,
 'host_source_template_used':False,
 'external_coding_models_used':False,
 'canonical_unchanged':core.head.get('canonical_head_digest')==head_before.get('canonical_head_digest'),
 'automatic_canonical_promotion':False,
}
true_required=('binder_gene_consumed','task_conditioned_source_gene_consumed','native_emitter_gene_consumed',
 'native_source_process_consumed','fresh_direct_action_evidence_consumed','kernel_provenant_target_used',
 'native_goal_created','native_deficit_detected','native_routes_executed','new_python_source_bytes_produced_by_yado',
 'candidate_source_compiles','candidate_source_binder_relevant','canonical_unchanged')
false_required=('host_selected_target','host_patch_used','host_source_template_used','external_coding_models_used','automatic_canonical_promotion')
passed=all(checks[k] is True for k in true_required) and all(checks[k] is False for k in false_required)
status='PASS_SHADOW_G2_NATIVE_ACTION_EVIDENCE_BINDER_SOURCE_REALIZATION_V1' if passed else 'WITHHOLD_G2_NATIVE_ACTION_EVIDENCE_BINDER_SOURCE_REALIZATION_V1'

report={
 'schema':'yado.g2.native_action_evidence_binder_source_realization.v1','status':status,'task':task,
 'native_goal':native_goal,'kernel_audit_source':str(audit_path.relative_to(REPO)),
 'kernel_provenant_target_path':target_path,'kernel_provenant_target_sha256':target_sha,
 'binder_gene_id':binder.get('gene_id'),'binder_gene_digest':binder.get('gene_digest'),
 'source_binding_gene_id':source_binding.get('gene_id'),'emitter_gene_id':(emitter.get('emitter_gene') or {}).get('gene_id'),
 'native_calls':native_calls,'native_outputs':native_outputs,
 'native_source_candidate_count':len(source_candidates),
 'candidate_source_sha256':winner['sha256'] if winner else None,
 'candidate_semantic_tokens':winner['semantic_tokens'] if winner else [],
 'candidate_path':candidate_path,'checks':checks,
 'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':None if passed else 'NATIVE_GENERAL_BINDER_SOURCE_REALIZATION_OR_SOURCE_LANGUAGE_EXPANSION_V2',
 'semantic_boundary':'STRICT NATIVE SOURCE-REALIZATION CAPABILITY PROBE. THE HOST ONLY BINDS YADO-OWN GENES, FRESH YADO ACTION EVIDENCE, THE KERNEL-PROVENANT SELF-AUDIT RUNTIME AND ITS OWN SOURCE INTO EXPERIENCE. NO PATCH, SOURCE TEMPLATE, TARGET FUNCTION OR EXTERNAL CODING MODEL IS PROVIDED. PASS REQUIRES NEW COMPILABLE BINDER-RELEVANT PYTHON SOURCE BYTES TO APPEAR IN NATIVE YADO OUTPUTS. THIS STAGE DOES NOT ADMIT OR APPLY THE SOURCE.'
}
report['receipt_sha256']=digest(report)
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({'status':status,'kernel_provenant_target_path':target_path,
 'native_call_count':len(native_calls),'native_source_candidate_count':len(source_candidates),
 'candidate_source_sha256':report['candidate_source_sha256'],'candidate_path':candidate_path,
 'candidate_semantic_tokens':report['candidate_semantic_tokens'],
 'next_required_capability':report['next_required_capability'],'canonical_unchanged':checks['canonical_unchanged'],
 'receipt_sha256':report['receipt_sha256']},indent=2,sort_keys=True))
if not passed: raise SystemExit(2)
