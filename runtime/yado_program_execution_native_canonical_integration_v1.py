from __future__ import annotations
from pathlib import Path
import copy,hashlib,importlib.util,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
CORE=REPO/'canonical'/'yado-unified-core-v1.json'
RUNTIME=REPO/'runtime'/'yado_unified_core_v1.py'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
CAND_SRC=REPO/'candidates'/'g2-self-evolution'/'bounded_program_repair_v2.py'
CAND_META=REPO/'candidates'/'g2-self-evolution'/'bounded_program_repair_v2.json'
ADMIT=REPO/'receipts'/'yado-program-execution-native-fresh-admission-v1-run-33417688958.json'
TARGET=REPO/'runtime'/'yado_bounded_program_repair_v2.py'
OUT=ROOT/'yado_program_execution_native_canonical_integration_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);core=load(CORE);ledger=load(LEDGER);meta=load(CAND_META);admit=load(ADMIT)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['REAL_PROGRAM_EXECUTION_TRANSFER_CANONICAL_INTEGRATION_V1']:raise RuntimeError('UNEXPECTED_FRONTIER')
if admit.get('status')!='PASS_PROGRAM_EXECUTION_NATIVE_FRESH_ADMISSION_V1':raise RuntimeError('FRESH_ADMISSION_NOT_PASS')
if meta.get('state')!='AUTHORIZED_FOR_SHADOW_ADMISSION':raise RuntimeError('CANDIDATE_NOT_AUTHORIZED')
if fsha(CAND_SRC)!=meta.get('candidate_source_sha256'):raise RuntimeError('SOURCE_DRIFT')
if admit.get('candidate_source_sha256')!=meta.get('candidate_source_sha256'):raise RuntimeError('ADMISSION_SOURCE_DRIFT')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')

candidate_code=CAND_SRC.read_text(encoding='utf-8')
source_safety={
 'only_ast_copy_imports':'import ast,copy' in candidate_code and all(x not in candidate_code for x in ['subprocess','socket','requests','aiohttp','urllib']),
 'single_function_guard':'EXACTLY_ONE_FUNCTION_REQUIRED' in candidate_code,
 'call_allowlist_guard':'CALL_NOT_ALLOWED' in candidate_code,
 'loop_and_import_bans':'ast.While' in candidate_code and 'ast.For' in candidate_code and 'ast.Import' in candidate_code,
 'empty_builtins_execution':'env["__builtins__"]={}' in candidate_code,
 'bounded_candidate_count':'max_candidates=10000' in candidate_code,
}

src=RUNTIME.read_text(encoding='utf-8')
patched=src
import_anchor='from yado_semantic_expression_synthesizer_v1 import SemanticExpressionSynthesizerV1'
import_line=import_anchor+'\nfrom yado_bounded_program_repair_v2 import BoundedProgramRepairV1'
if 'from yado_bounded_program_repair_v2 import BoundedProgramRepairV1' not in patched:
    patched=patched.replace(import_anchor,import_line)
init_anchor='        self.semantic_expression_synthesizer=SemanticExpressionSynthesizerV1'
init_line=init_anchor+'\n        self.bounded_program_repair=BoundedProgramRepairV1'
if 'self.bounded_program_repair=BoundedProgramRepairV1' not in patched:
    patched=patched.replace(init_anchor,init_line)
method_anchor='    def synthesize_mathematical_expression(self,train_rows:list[dict[str,Any]],max_ops:int=3,max_states_per_level:int=30000)->dict[str,Any]:'
methods=(
"    def repair_program(self,source:str,function_name:str,train_examples:list[tuple[tuple[Any,...],Any]],max_candidates:int=10000)->dict[str,Any]:\n"
"        return self.bounded_program_repair.repair(source,function_name,train_examples,max_candidates=max_candidates)\n\n"
"    def execute_program_task(self,source:str,function_name:str,args:tuple[Any,...])->Any:\n"
"        return self.bounded_program_repair.execute(source,function_name,args)\n\n"
+method_anchor)
if '    def repair_program(' not in patched:
    patched=patched.replace(method_anchor,methods)
bounded_patch=(
 patched.count('from yado_bounded_program_repair_v2 import BoundedProgramRepairV1')==1 and
 patched.count('self.bounded_program_repair=BoundedProgramRepairV1')==1 and
 patched.count('def repair_program(')==1 and patched.count('def execute_program_task(')==1
)

TARGET.write_text(candidate_code,encoding='utf-8')
tmp=ROOT/'_program_integration_candidate_unified_core.py'
tmp.write_text(patched,encoding='utf-8')
try:
    sp=importlib.util.spec_from_file_location('_program_integration_candidate_unified_core',tmp)
    mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod)
    obj=mod.UnifiedYADOCoreV1(REPO)
    audit=obj.audit()
    source='def clamp(x,lo):\n    return max(x+1,lo)\n'
    train=[((5,0),4),((0,0),0),((-2,-5),-3)]
    res=obj.repair_program(source,'clamp',train)
    interface_ok=False
    if res.get('source'):
        blind=[((9,3),8),((3,3),3),((-8,-10),-9)]
        interface_ok=all(obj.execute_program_task(res['source'],'clamp',a)==e for a,e in blind)
    negative_ok=False
    try:obj.execute_program_task('import os\ndef f(x):\n    return x\n','f',(1,))
    except Exception:negative_ok=True
finally:
    try:tmp.unlink()
    except FileNotFoundError:pass

checks={
 'fresh_admission_score_one':admit.get('fresh_score')==1.0,
 'fresh_causal_ablation':admit.get('checks',{}).get('causal_family_ablation') is True,
 'fresh_negative_safety':admit.get('checks',{}).get('negative_safety_rejection') is True,
 'source_safety':all(source_safety.values()),
 'bounded_unified_core_patch':bounded_patch,
 'candidate_current_audit_pass':audit.get('pass') is True,
 'unified_core_program_interface_blind_pass':interface_ok,
 'unified_core_negative_rejection':negative_ok,
 'canonical_head_coherent':ledger.get('current_head_digest')==head.get('canonical_head_digest'),
}
passed=all(checks.values())

post_head=None;post_core=None
if passed:
    RUNTIME.write_text(patched,encoding='utf-8')
    runtime_sha=fsha(RUNTIME);component_sha=fsha(TARGET)
    new_core=copy.deepcopy(core);new_core.pop('core_digest',None)
    thinking=next(x for x in new_core['planes'] if x.get('plane_id')=='THINKING_AND_PLANNING')
    thinking['active_components']=sorted(set(thinking.get('active_components',[])+[meta['component_id']]))
    thinking['responsibilities']=sorted(set(thinking.get('responsibilities',[])+['bounded_program_repair_and_execution']))
    new_core['active_runtime_sources']=sorted(set(new_core.get('active_runtime_sources',[])+['runtime/yado_bounded_program_repair_v2.py']))
    new_core['program_execution']={
      'component_id':meta['component_id'],'candidate_digest':meta['candidate_digest'],
      'source_sha256':component_sha,'fresh_admission_receipt_sha256':admit['receipt_sha256'],
      'fresh_score':admit['fresh_score'],'mode':'ACTIVE_BOUNDED_SINGLE_FUNCTION_REPAIR',
      'gate_run_id':str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
    }
    new_core['runtime_sha256']=runtime_sha
    new_core['current_frontier']='UNIFIED_CORE_POST_PROGRAM_EXECUTION_SELF_AUDIT_V1'
    new_core['core_digest']=h(new_core);CORE.write_text(json.dumps(new_core,indent=2,sort_keys=True)+'\n')
    new_head=copy.deepcopy(head);new_head.pop('canonical_head_digest',None)
    new_head['new_capabilities']=sorted(set(new_head.get('new_capabilities',[])+[meta['component_id']]))
    new_head['unified_core']['runtime_sha256']=runtime_sha
    new_head['unified_core']['core_digest']=new_core['core_digest']
    new_head['unified_core']['bounded_program_repair_source_sha256']=component_sha
    new_head['current_frontier']='UNIFIED_CORE_POST_PROGRAM_EXECUTION_SELF_AUDIT_V1'
    new_head['canonical_head_digest']=h(new_head);HEAD.write_text(json.dumps(new_head,indent=2,sort_keys=True)+'\n')
    post_head=new_head['canonical_head_digest'];post_core=new_core['core_digest']
    status='PASS_PROGRAM_EXECUTION_NATIVE_CANONICAL_INTEGRATION_V1'
    next_cap='UNIFIED_CORE_POST_PROGRAM_EXECUTION_SELF_AUDIT_V1'
else:
    try:TARGET.unlink()
    except FileNotFoundError:pass
    status='WITHHOLD_PROGRAM_EXECUTION_NATIVE_CANONICAL_INTEGRATION_V1'
    next_cap='REAL_PROGRAM_EXECUTION_TRANSFER_NATIVE_EVOLUTION_V3'

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.program_execution_native_canonical_integration.v1','status':status,
 'candidate_digest':meta['candidate_digest'],'candidate_source_sha256':meta['candidate_source_sha256'],
 'fresh_admission_receipt':admit['receipt_sha256'],'checks':checks,'source_safety':source_safety,
 'canonical_mutation':passed,'promotion_applied':False,'generation_transition':False,'g3_genesis_performed':False,
 'post_head_digest':post_head,'post_core_digest':post_core,'next_required_capability':next_cap,
 'semantic_boundary':'SAME-GENERATION CANONICALIZATION OF BOUNDED SINGLE-FUNCTION PYTHON REPAIR/EXECUTION. NOT GENERAL SOFTWARE ENGINEERING OR UNRESTRICTED CODE EXECUTION.'}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_PROGRAM_EXECUTION_NATIVE_CANONICAL_INTEGRATION",
 'event_type':'GENERATION_INTERNAL_SELF_EVOLVED_CODE_ADMISSION','status':'PASS' if passed else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'REAL_PROGRAM_EXECUTION_TRANSFER_CANONICAL_INTEGRATION_V1',
 'effect':'BOUNDED_PROGRAM_REPAIR_BOUND_TO_UNIFIED_CORE' if passed else 'PROGRAM_REPAIR_CANONICAL_INTEGRATION_WITHHELD',
 'source_path':f'receipts/yado-program-execution-native-canonical-integration-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':passed,'promotion_applied':False,'generation_transition':False}
if passed:e['previous_head_digest']=ledger['current_head_digest'];e['new_head_digest']=post_head
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
if passed:ledger['current_head_digest']=post_head
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':status,'checks':checks,'post_head_digest':post_head,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('PROGRAM_NATIVE_CANONICAL_INTEGRATION_WITHHELD')
