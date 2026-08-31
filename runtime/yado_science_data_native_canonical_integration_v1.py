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
CAND_SRC=REPO/'candidates'/'g2-self-evolution'/'bounded_scientific_data_reasoner_v1.py'
CAND_META=REPO/'candidates'/'g2-self-evolution'/'bounded_scientific_data_reasoner_v1.json'
ADMIT=REPO/'receipts'/'yado-science-data-native-fresh-admission-v1-run-33419266920.json'
TARGET=REPO/'runtime'/'yado_bounded_scientific_data_reasoner_v1.py'
OUT=ROOT/'yado_science_data_native_canonical_integration_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);core=load(CORE);ledger=load(LEDGER);meta=load(CAND_META);admit=load(ADMIT)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['REAL_SCIENCE_DATA_TRANSFER_CANONICAL_INTEGRATION_V1']:raise RuntimeError('UNEXPECTED_FRONTIER')
if admit.get('status')!='PASS_SCIENCE_DATA_NATIVE_FRESH_ADMISSION_V1':raise RuntimeError('FRESH_ADMISSION_NOT_PASS')
if meta.get('state')!='AUTHORIZED_FOR_SHADOW_ADMISSION':raise RuntimeError('CANDIDATE_NOT_AUTHORIZED')
if fsha(CAND_SRC)!=meta.get('candidate_source_sha256'):raise RuntimeError('SOURCE_DRIFT')
if admit.get('candidate_source_sha256')!=meta.get('candidate_source_sha256'):raise RuntimeError('ADMISSION_SOURCE_DRIFT')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')

candidate_code=CAND_SRC.read_text(encoding='utf-8')
source_safety={
 'only_math_import':'import math' in candidate_code and all(x not in candidate_code for x in ['urllib','requests','aiohttp','socket','subprocess']),
 'bounded_group_count':'max_groups=12' in candidate_code,
 'bounded_hypothesis_surface':all(x in candidate_code for x in ['CORRELATION_ABS_AT_LEAST','GROUP_MEAN_ORDER','LINEAR_R2_AT_LEAST']),
 'no_exec_eval':('exec(' not in candidate_code and 'eval(' not in candidate_code),
}

src=RUNTIME.read_text(encoding='utf-8')
patched=src
import_anchor='from yado_bounded_program_repair_v2 import BoundedProgramRepairV1'
import_line=import_anchor+'\nfrom yado_bounded_scientific_data_reasoner_v1 import BoundedScientificDataReasonerV1'
if 'from yado_bounded_scientific_data_reasoner_v1 import BoundedScientificDataReasonerV1' not in patched:
    patched=patched.replace(import_anchor,import_line)
init_anchor='        self.bounded_program_repair=BoundedProgramRepairV1'
init_line=init_anchor+'\n        self.scientific_data_reasoner=BoundedScientificDataReasonerV1'
if 'self.scientific_data_reasoner=BoundedScientificDataReasonerV1' not in patched:
    patched=patched.replace(init_anchor,init_line)
method_anchor='    def repair_program(self,source:str,function_name:str,train_examples:list[tuple[tuple[Any,...],Any]],max_candidates:int=10000)->dict[str,Any]:'
methods=(
"    def analyze_science_data(self,rows:list[dict[str,Any]],enable:tuple[str,...]=('summary','correlation','group','linear'))->dict[str,Any]:\n"
"        return self.scientific_data_reasoner.analyze(rows,enable=enable)\n\n"
"    def test_scientific_hypothesis(self,rows:list[dict[str,Any]],spec:dict[str,Any])->dict[str,Any]:\n"
"        return self.scientific_data_reasoner.evaluate_hypothesis(rows,spec)\n\n"
+method_anchor)
if '    def analyze_science_data(' not in patched:
    patched=patched.replace(method_anchor,methods)
bounded_patch=(
 patched.count('from yado_bounded_scientific_data_reasoner_v1 import BoundedScientificDataReasonerV1')==1 and
 patched.count('self.scientific_data_reasoner=BoundedScientificDataReasonerV1')==1 and
 patched.count('def analyze_science_data(')==1 and patched.count('def test_scientific_hypothesis(')==1
)

TARGET.write_text(candidate_code,encoding='utf-8')
tmp=ROOT/'_science_integration_candidate_unified_core.py'
tmp.write_text(patched,encoding='utf-8')
try:
    sp=importlib.util.spec_from_file_location('_science_integration_candidate_unified_core',tmp)
    mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod)
    obj=mod.UnifiedYADOCoreV1(REPO)
    audit=obj.audit()
    rows=[
      {'x':'1','y':'2','group':'A'},{'x':'2','y':'4','group':'A'},
      {'x':'3','y':'6','group':'B'},{'x':'4','y':'8','group':'B'},
    ]
    ana=obj.analyze_science_data(rows)
    hyp=obj.test_scientific_hypothesis(rows,{'type':'CORRELATION_ABS_AT_LEAST','x':'x','y':'y','threshold':0.99})
    interface_ok=(
      set(ana.get('schema',{}).get('numeric',[]))=={'x','y'} and
      ana.get('strongest_numeric_pair',{}).get('correlation') is not None and
      hyp.get('supported') is True
    )
finally:
    try:tmp.unlink()
    except FileNotFoundError:pass

checks={
 'fresh_admission_all_checks':all(admit.get('checks',{}).values()),
 'source_safety':all(source_safety.values()),
 'bounded_unified_core_patch':bounded_patch,
 'candidate_current_audit_pass':audit.get('pass') is True,
 'unified_core_science_interface_pass':interface_ok,
 'canonical_head_coherent':ledger.get('current_head_digest')==head.get('canonical_head_digest'),
}
passed=all(checks.values())

post_head=None;post_core=None
if passed:
    RUNTIME.write_text(patched,encoding='utf-8')
    runtime_sha=fsha(RUNTIME);component_sha=fsha(TARGET)
    new_core=copy.deepcopy(core);new_core.pop('core_digest',None)
    resource=next(x for x in new_core['planes'] if x.get('plane_id')=='RESOURCE_AND_EVIDENCE')
    resource['active_components']=sorted(set(resource.get('active_components',[])+[meta['component_id']]))
    resource['responsibilities']=sorted(set(resource.get('responsibilities',[])+['bounded_tabular_scientific_reasoning']))
    new_core['active_runtime_sources']=sorted(set(new_core.get('active_runtime_sources',[])+['runtime/yado_bounded_scientific_data_reasoner_v1.py']))
    new_core['science_reasoning']={
      'component_id':meta['component_id'],'candidate_digest':meta['candidate_digest'],
      'source_sha256':component_sha,'fresh_admission_receipt_sha256':admit['receipt_sha256'],
      'fresh_datasets':['PENGUINS','TIPS'],
      'mode':'ACTIVE_BOUNDED_TABULAR_SCIENTIFIC_REASONING',
      'gate_run_id':str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
    }
    new_core['runtime_sha256']=runtime_sha
    new_core['current_frontier']='UNIFIED_CORE_POST_SCIENCE_DATA_SELF_AUDIT_V1'
    new_core['core_digest']=h(new_core);CORE.write_text(json.dumps(new_core,indent=2,sort_keys=True)+'\n')

    new_head=copy.deepcopy(head);new_head.pop('canonical_head_digest',None)
    new_head['new_capabilities']=sorted(set(new_head.get('new_capabilities',[])+[meta['component_id']]))
    new_head['unified_core']['runtime_sha256']=runtime_sha
    new_head['unified_core']['core_digest']=new_core['core_digest']
    new_head['unified_core']['scientific_data_reasoner_source_sha256']=component_sha
    new_head['current_frontier']='UNIFIED_CORE_POST_SCIENCE_DATA_SELF_AUDIT_V1'
    new_head['canonical_head_digest']=h(new_head);HEAD.write_text(json.dumps(new_head,indent=2,sort_keys=True)+'\n')
    post_head=new_head['canonical_head_digest'];post_core=new_core['core_digest']
    status='PASS_SCIENCE_DATA_NATIVE_CANONICAL_INTEGRATION_V1'
    next_cap='UNIFIED_CORE_POST_SCIENCE_DATA_SELF_AUDIT_V1'
else:
    try:TARGET.unlink()
    except FileNotFoundError:pass
    status='WITHHOLD_SCIENCE_DATA_NATIVE_CANONICAL_INTEGRATION_V1'
    next_cap='REAL_SCIENCE_DATA_TRANSFER_NATIVE_EVOLUTION_V2'

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.science_data_native_canonical_integration.v1','status':status,
 'candidate_digest':meta['candidate_digest'],'candidate_source_sha256':meta['candidate_source_sha256'],
 'fresh_admission_receipt':admit['receipt_sha256'],'checks':checks,'source_safety':source_safety,
 'canonical_mutation':passed,'promotion_applied':False,'generation_transition':False,'g3_genesis_performed':False,
 'post_head_digest':post_head,'post_core_digest':post_core,'next_required_capability':next_cap,
 'semantic_boundary':'SAME-GENERATION CANONICALIZATION OF BOUNDED TABULAR SCIENTIFIC-DATA REASONING. NOT CAUSAL INFERENCE, GENERAL SCIENTIFIC DISCOVERY, OR AGI.'}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_SCIENCE_DATA_NATIVE_CANONICAL_INTEGRATION",
 'event_type':'GENERATION_INTERNAL_SCIENCE_CAPABILITY_ADMISSION','status':'PASS' if passed else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'REAL_SCIENCE_DATA_TRANSFER_CANONICAL_INTEGRATION_V1',
 'effect':'BOUNDED_SCIENCE_DATA_REASONER_BOUND_TO_UNIFIED_CORE' if passed else 'SCIENCE_DATA_CANONICAL_INTEGRATION_WITHHELD',
 'source_path':f'receipts/yado-science-data-native-canonical-integration-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':passed,'promotion_applied':False,'generation_transition':False}
if passed:
    e['previous_head_digest']=ledger['current_head_digest'];e['new_head_digest']=post_head
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
if passed:ledger['current_head_digest']=post_head
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':status,'checks':checks,'post_head_digest':post_head,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('SCIENCE_DATA_NATIVE_CANONICAL_INTEGRATION_WITHHELD')
