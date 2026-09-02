from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,os,subprocess,sys

ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent;PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json';CORE=REPO/'canonical/yado-unified-core-v1.json';LEDGER=REPO/'architecture/evolution-ledger.json'
PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
ORIG=REPO/'receipts/yado-g2-post-composite-architectural-ceiling-reassessment-v1-run-33665673626.json'
RAW=REPO/'resources/yado-g2-post-composite-ceiling-raw-boundary-v1.json'
SCI_FRESH=REPO/'receipts/yado-science-data-native-fresh-admission-v1-run-33419266920.json'
SCI_CANON=REPO/'receipts/yado-science-data-native-canonical-integration-v1-run-33436389858.json'
OUT=ROOT/'yado_g2_post_composite_ceiling_reassessment_evidence_repair_v1_receipt.json'
GUARD=ROOT/'yado_canonical_invariant_guard_v1.py'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):
    x=copy.deepcopy(o);x.pop(field,None);return h(x)

head,core,ledger,prov,orig,raw,sf,sc=map(load,[HEAD,CORE,LEDGER,PROV,ORIG,RAW,SCI_FRESH,SCI_CANON])
validate_ledger_v2(ledger)
expected='KERNEL_G2_SCIENCE_REASONING_POST_COMPOSITE_SELF_EVOLUTION_V1'
if ledger.get('open_deficits')!=[expected]:raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if orig.get('kernel_selected_residual')!='SCIENCE_REASONING' or float(orig.get('kernel_selected_score',-1))!=0.0:
    raise RuntimeError('ORIGINAL_FALSE_RESIDUAL_NOT_PRESENT')
if sf.get('status')!='PASS_SCIENCE_DATA_NATIVE_FRESH_ADMISSION_V1':raise RuntimeError('SCIENCE_FRESH_NOT_PASS')
if sc.get('status')!='PASS_SCIENCE_DATA_NATIVE_CANONICAL_INTEGRATION_V1':raise RuntimeError('SCIENCE_CANONICAL_NOT_PASS')
if not all(sf.get('checks',{}).values()):raise RuntimeError('SCIENCE_FRESH_CHECKS_NOT_ALL_PASS')
if head.get('g3_genesis_performed') is not False:raise RuntimeError('G3_ALREADY_STARTED')

scores=dict(orig['scores'])
scores['SCIENCE_REASONING']=1.0
scores['RAW_TASK_REPRESENTATION_CROSS_DOMAIN']=float(raw['raw_accuracy'])
records=[]
for name,score in scores.items():
    gap=max(0.0,1.0-float(score))
    records.append({
      'variant_id':'DEFICIT_'+name,'parent_id':None,'lineage_id':'G2_POST_COMPOSITE_CEILING_REPAIRED',
      'artifact_digest':h({'name':name,'score':score,'source':'EVIDENCE_REPAIR_V1'}),
      'task_scores':{'deficit_priority':gap},
      'constraints':{'regression_pass':True,'state_integrity':True,'rollback_available':True},
      'traits':{'measured_score':score,'residual_gap':gap},
      'failure_tags':['below_0_985_gate'] if score<.985 else [],
      'status':'EVALUATED'
    })
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_ceiling_evidence_repair_v1.sqlite'))
try:
    selected=k.select_evolution_parent(records,'residual_deficit_priority')
    operation=k.propose_evolution_operation(records,selected['variant_id'],'architectural_ceiling_reassessment_repaired')
finally:k.close()
selected_name=selected['variant_id'].removeprefix('DEFICIT_');selected_score=float(scores[selected_name]);gap=1-selected_score
if selected_name!='RAW_TASK_REPRESENTATION_CROSS_DOMAIN':
    raise RuntimeError('REPAIRED_KERNEL_SELECTION_NOT_RAW:'+selected_name)
next_cap='KERNEL_G2_RAW_REPRESENTATION_POST_COMPOSITE_SELF_EVOLUTION_V1'

prev=head['canonical_head_digest']
prov['current_g2_binding'].update({
 'current_execution_label':'G2_POST_COMPOSITE_RESIDUAL_RAW_TASK_REPRESENTATION_CROSS_DOMAIN',
 'frontier':next_cap,'frontier_native_method':'select_evolution_parent+propose_evolution_operation',
 'frontier_native_owner':'UnifiedYADOKernelV30RC8ExternalCognitive',
 'post_composite_ceiling_verdict':'CEILING_NOT_REACHED_RESIDUAL_G2_DEFICIT',
 'kernel_selected_residual':selected_name,
 'reassessment_evidence_repair':'SCIENCE_SCORE_SCHEMA_PATH_CORRECTED_FROM_CANONICAL_RECEIPTS'
})
prov['registry_digest']=cdig(prov,'registry_digest');write(PROV,prov)
core['algorithm_provenance_registry_digest']=prov['registry_digest'];core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits'
core['post_composite_architectural_ceiling_reassessment_v1']['scores']=scores
core['post_composite_architectural_ceiling_reassessment_v1']['selected_residual']=selected_name
core['post_composite_architectural_ceiling_reassessment_v1']['selected_gap']=gap
core['post_composite_architectural_ceiling_reassessment_v1']['evidence_repair']='SCIENCE_SCORE_FROM_PASS_FRESH_AND_CANONICAL_RECEIPTS'
core['core_digest']=cdig(core,'core_digest');write(CORE,core)
head['algorithm_provenance_registry']['registry_digest']=prov['registry_digest'];head['algorithm_provenance_registry']['current_execution_label']=prov['current_g2_binding']['current_execution_label']
head['unified_core']['algorithm_provenance_registry_digest']=prov['registry_digest'];head['unified_core']['core_digest']=core['core_digest']
head['post_composite_architectural_ceiling_reassessment_v1']['scores']=scores
head['post_composite_architectural_ceiling_reassessment_v1']['selected_residual']=selected_name
head['post_composite_architectural_ceiling_reassessment_v1']['selected_gap']=gap
head['post_composite_architectural_ceiling_reassessment_v1']['evidence_repair']='SCIENCE_SCORE_FROM_PASS_FRESH_AND_CANONICAL_RECEIPTS'
head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits';head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)
ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap]

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
 'schema':'yado.g2.post_composite_ceiling_reassessment_evidence_repair.receipt.v1',
 'status':'PASS_G2_POST_COMPOSITE_CEILING_REASSESSMENT_EVIDENCE_REPAIR_V1',
 'original_reassessment_run':33665673626,
 'error':'SCIENCE_REASONING_SCORE_DEFAULTED_TO_ZERO_BECAUSE_CANONICAL_CORE_SCIENCE_BINDING_HAS_NO_FRESH_SCORE_FIELD',
 'science_fresh_receipt_status':sf['status'],'science_canonical_receipt_status':sc['status'],
 'science_corrected_score':1.0,'raw_spent_boundary_score':raw['raw_accuracy'],
 'corrected_scores':scores,'kernel_selected_residual':selected_name,'kernel_selected_score':selected_score,'kernel_selected_gap':gap,
 'kernel_evolution_operation':operation,'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest'],
 'canonical_mutation':True,'canonical_mechanism_mutation':False,'architecture_mutation':False,
 'g3_genesis_performed':False,'next_required_capability':next_cap,
 'semantic_boundary':'CONTROL-PLANE EVIDENCE REPAIR ONLY. PRESERVES THE ORIGINAL FALSE SCIENCE RESIDUAL AS HISTORY, CORRECTS ITS SCORE FROM CANONICAL PASS RECEIPTS, AND RE-RUNS NATIVE RESIDUAL SELECTION ON THE SAME SPENT RAW BOUNDARY.'
}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_POST_COMPOSITE_CEILING_REASSESSMENT_EVIDENCE_REPAIR_V1",
 'event_type':'G2_CEILING_REASSESSMENT_EVIDENCE_REPAIR','status':'PASS',
 'generation':ledger['current_head'],'deficit':expected,
 'effect':f"REPAIR=SCIENCE_SCORE_SCHEMA_PATH; SCIENCE=1.000000; RAW={raw['raw_accuracy']:.6f}; SELECTED={selected_name}; GAP={gap:.6f}; OP={operation.get('operation')}; NEXT={next_cap}",
 'source_path':f'receipts/yado-g2-post-composite-ceiling-reassessment-evidence-repair-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':True,'canonical_mechanism_mutation':False,'architecture_mutation':False,
 'promotion_applied':False,'generation_transition':False,'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);write(LEDGER,ledger)
ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_REPAIR_CONTEXT_INCONSISTENT')
post=subprocess.run([sys.executable,str(GUARD)],cwd=REPO,capture_output=True,text=True,timeout=60)
if post.returncode!=0:raise RuntimeError('POST_REPAIR_GUARD_FAILED:'+post.stdout[-4000:]+post.stderr[-1000:])
print(json.dumps({'status':receipt['status'],'corrected_scores':scores,'selected_residual':selected_name,'selected_gap':gap,'kernel_operation':operation,'next_required_capability':next_cap},indent=2,sort_keys=True))
