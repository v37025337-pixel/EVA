from __future__ import annotations
from pathlib import Path
from collections import Counter
import csv,hashlib,io,json,os,random,sys,urllib.request

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(PKG))

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_unified_core_v1 import UnifiedYADOCoreV1

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
OUT=ROOT/'yado_real_world_generalization_self_directed_v2_receipt.json'
STATE=REPO/'architecture'/'yado-real-world-generalization-state-v2.json'

CAP_CONJ='ALG-CONJUNCTIVE-RULE-INDUCER-V1'
CAP_REL='ALG-BOUNDED-DNF-RELATION-POLICY-INDUCER-V1'
CAP_BUD='ALG-BUDGETED-STAGE-POLICY-V1'
CAP_RES='RESOURCE-PORTFOLIO-V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

def latest_self_audit():
    xs=list((REPO/'receipts').glob('yado-unified-core-deep-self-audit-v1-run-*.json'))
    if not xs:raise RuntimeError('SELF_AUDIT_RECEIPT_MISSING')
    def runno(p):
        try:return int(p.stem.rsplit('-',1)[-1])
        except:return -1
    return max(xs,key=runno)

head=load(HEAD);ledger=load(LEDGER);audit_path=latest_self_audit();audit=load(audit_path)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['REAL_WORLD_GENERALIZATION_SCOPE']:raise RuntimeError('UNEXPECTED_FRONTIER')
if audit.get('self_selected_next_step')!='REAL_WORLD_GENERALIZATION_SCOPE':raise RuntimeError('KERNEL_PRIORITY_MISMATCH')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')
core=UnifiedYADOCoreV1(REPO)

# ---------------- RAW UNSTRUCTURED INPUT: kernel-native canonical representation ----------------
raw_cases=[
 ('R1','A user may open the confidential record only when the user owns it and belongs to the approved project.',CAP_REL),
 ('R2','Check whether the same device is linked to both identities before allowing the operation.',CAP_REL),
 ('R3','Determine which objects share a verified relationship with the requested owner.',CAP_REL),
 ('R4','The experiment has a strict compute budget; choose the next check without exceeding the remaining quota.',CAP_BUD),
 ('R5','Search is limited to three attempts and the cheapest valid stage should run first.',CAP_BUD),
 ('R6','Allocate a small verification budget across candidate tests and stop when the limit is reached.',CAP_BUD),
 ('R7','Accept the release only if every mandatory check passes and all required evidence is present.',CAP_CONJ),
 ('R8','The build is valid when the signature is correct, the tests pass, and rollback evidence exists.',CAP_CONJ),
 ('R9','Approve the candidate only when all listed conditions are simultaneously satisfied.',CAP_CONJ),
 ('R10','Use an external public dataset to verify the claim and compare independent evidence sources.',CAP_RES),
 ('R11','Consult current web evidence because the local state is insufficient to answer the research question.',CAP_RES),
 ('R12','Retrieve outside scientific data and record provenance before drawing a conclusion.',CAP_RES),
]
raw_rows=[]
for cid,text_,exp in raw_cases:
    got=core.represent_raw_task(text_).get('capability')
    raw_rows.append({'id':cid,'expected':exp,'got':got,'ok':got==exp,'text_sha256':hashlib.sha256(text_.encode()).hexdigest()})
raw_score=sum(x['ok'] for x in raw_rows)/len(raw_rows)

# ---------------- MATHEMATICS: only through the admitted canonical G2 API ----------------
train_pts=[(-6,2),(-3,-5),(0,4),(1,-2),(4,3),(7,-1),(9,5)]
blind_pts=[(-8,7),(-2,-9),(2,8),(5,-4),(6,6),(10,-3),(13,2)]
math_tasks=[
 ('M1_X2_MINUS_Y',lambda x,y:x*x-y),
 ('M2_TWO_X_PLUS_Y',lambda x,y:2*x+y),
 ('M3_DOUBLE_DIFFERENCE',lambda x,y:2*(x-y)),
 ('M4_PRODUCT_MINUS_Y',lambda x,y:x*y-y),
 ('M5_THREE_X_MINUS_TWO_Y',lambda x,y:3*x-2*y),
 ('M6_SHIFTED_PRODUCT',lambda x,y:x*(y+1)),
]
math_rows=[]
for tid,fn in math_tasks:
    tr=[{'x':x,'y':y,'expected':fn(x,y)} for x,y in train_pts]
    res=core.synthesize_mathematical_expression(tr,max_ops=3,max_states_per_level=30000)
    hidden=[]
    if res.get('expression') is not None:
        for x,y in blind_pts:
            exp=fn(x,y)
            got=core.predict_mathematical_expression(res,x,y)
            hidden.append({'x':x,'y':y,'expected':exp,'got':got,'ok':got==exp})
    ok=bool(hidden) and all(z['ok'] for z in hidden)
    math_rows.append({
      'id':tid,'found':res.get('expression') is not None,'ops':res.get('ops'),
      'states':res.get('states'),'expression':core.semantic_expression_synthesizer.render(res['expression']) if res.get('expression') is not None else None,
      'blind_pass':ok,'blind':hidden
    })
math_score=sum(x['blind_pass'] for x in math_rows)/len(math_rows)

# ---------------- PROGRAM EXECUTION: measure native capability, not harness skill ----------------
program_native_methods=[m for m in ('repair_program','synthesize_program','execute_program_task','solve_code_task') if hasattr(core,m)]
program_probe={
 'native_methods':program_native_methods,
 'native_capability_present':bool(program_native_methods),
 'task':'Repair a fresh Python function from examples, execute the candidate, and pass held-out tests without a host-supplied mutation grammar.',
 'host_scaffold_credit_allowed':False,
}
program_score=1.0 if program_probe['native_capability_present'] else 0.0

# ---------------- PUBLIC SCIENCE DATA: live acquisition vs native scientific reasoning ----------------
iris_url='https://raw.githubusercontent.com/mwaskom/seaborn-data/master/iris.csv'
science={'url':iris_url}
try:
    rq=urllib.request.Request(iris_url,headers={'User-Agent':'YADO-Real-Generalization-V2/1.0'})
    with urllib.request.urlopen(rq,timeout=15) as resp:data=resp.read()
    rows=list(csv.DictReader(io.StringIO(data.decode('utf-8'))))
    science.update({
      'download_ok':True,'sha256':hashlib.sha256(data).hexdigest(),'row_count':len(rows),
      'columns':list(rows[0].keys()) if rows else [],
      'species_counts':dict(Counter(r.get('species') for r in rows)),
    })
except Exception as exc:
    science.update({'download_ok':False,'error':type(exc).__name__+':'+str(exc)[:220]})

science_native_methods=[m for m in ('analyze_science_data','infer_scientific_model','test_scientific_hypothesis','reason_over_dataset') if hasattr(core,m)]
science['native_methods']=science_native_methods
science['native_scientific_reasoning_present']=bool(science_native_methods)
science['host_scaffold_credit_allowed']=False
science_score=1.0 if science.get('download_ok') and science['native_scientific_reasoning_present'] else 0.0

domain_scores={
 'REAL_UNSTRUCTURED_INPUT_TRANSFER':raw_score,
 'REAL_MATHEMATICAL_REASONING_TRANSFER':math_score,
 'REAL_PROGRAM_EXECUTION_TRANSFER':program_score,
 'REAL_SCIENCE_DATA_TRANSFER':science_score,
}
thresholds={
 'REAL_UNSTRUCTURED_INPUT_TRANSFER':.75,
 'REAL_MATHEMATICAL_REASONING_TRANSFER':.80,
 'REAL_PROGRAM_EXECUTION_TRANSFER':.80,
 'REAL_SCIENCE_DATA_TRANSFER':.80,
}
domain_pass={k:domain_scores[k]>=thresholds[k] for k in domain_scores}

# Explicitly measure remaining host scaffold dependence.
host_scaffold_dependence=not (domain_pass['REAL_PROGRAM_EXECUTION_TRANSFER'] and domain_pass['REAL_SCIENCE_DATA_TRANSFER'])
failing=[k for k,v in domain_pass.items() if not v]
priority_order=['REAL_UNSTRUCTURED_INPUT_TRANSFER','REAL_PROGRAM_EXECUTION_TRANSFER','REAL_MATHEMATICAL_REASONING_TRANSFER','REAL_SCIENCE_DATA_TRANSFER']
if failing:
    failing.sort(key=lambda k:(domain_scores[k],priority_order.index(k)))
    next_cap=failing[0]+'_NATIVE_EVOLUTION_V1'
else:
    next_cap='SHADOW_CONTEXT_ADAPTER_DEPENDENCE'

status='PASS_REAL_WORLD_GENERALIZATION_V2' if all(domain_pass.values()) and not host_scaffold_dependence else 'WITHHOLD_REAL_WORLD_GENERALIZATION_V2'
state={
 'schema':'yado.g2.real_world_generalization_state.v2',
 'generation':ledger['current_head'],
 'source_self_audit_run_id':audit.get('github_run_id'),
 'domain_scores':domain_scores,'domain_pass':domain_pass,
 'host_scaffold_dependence':host_scaffold_dependence,
 'next_required_capability':next_cap,
 'semantic_boundary':'V2 CREDITS ONLY CAPABILITIES EXPOSED THROUGH THE CANONICAL UNIFIED G2 CORE. HOST TEST HARNESS, DATA FETCHING, OR ORACLE LOGIC IS NOT COUNTED AS A KERNEL CAPABILITY.'
}
state['state_digest']=h(state);STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
 'schema':'yado.g2.real_world_generalization_self_directed.v2',
 'status':status,'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),
 'source_self_audit_receipt':audit.get('receipt_sha256'),
 'source_self_audit_path':str(audit_path.relative_to(REPO)),
 'raw_unstructured':{'score':raw_score,'cases':raw_rows},
 'mathematics':{'score':math_score,'tasks':math_rows,'execution_path':'UnifiedYADOCoreV1.synthesize_mathematical_expression'},
 'programming':program_probe,'science':science,
 'domain_scores':domain_scores,'thresholds':thresholds,'domain_pass':domain_pass,
 'host_scaffold_dependence':host_scaffold_dependence,
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,
 'semantic_boundary':state['semantic_boundary']
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_REAL_WORLD_GENERALIZATION_V2",
 'event_type':'KERNEL_REAL_WORLD_NATIVE_CAPABILITY_DIAGNOSTIC',
 'status':'PASS_SHADOW' if status.startswith('PASS_') else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'REAL_WORLD_GENERALIZATION_SCOPE',
 'effect':f"NATIVE_ONLY_GENERALIZATION_V2; SCORES={domain_scores}; HOST_SCAFFOLD={host_scaffold_dependence}; NEXT={next_cap}",
 'source_path':f'receipts/yado-real-world-generalization-self-directed-v2-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({
 'status':status,'domain_scores':domain_scores,'domain_pass':domain_pass,
 'host_scaffold_dependence':host_scaffold_dependence,
 'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']
},indent=2,sort_keys=True))
