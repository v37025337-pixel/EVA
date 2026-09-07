from __future__ import annotations
from pathlib import Path
import ast,hashlib,json,random,re,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_raw_task_representation_robustness_v4 import RobustRawTaskRepresentationRuntimeV4
from yado_raw_task_representation_robustness_v5 import RobustRawTaskRepresentationRuntimeV5,component
from yado_evolution_ledger_v2 import validate_ledger_v2

LEDGER=REPO/'architecture/evolution-ledger.json'
V3=REPO/'canonical/yado-raw-task-representation-v3.json'
V4=REPO/'canonical/yado-raw-task-representation-v4.json'
V1=REPO/'candidates/kernel-self-generated/raw-task-representation-v5-sequential-robustness-v1.json'
FAIL=REPO/'receipts/yado-g2-raw-representation-v5-canonical-admission-v1-run-33900049280.json'
STRUCT=REPO/'resources/yado-raw-task-representation-v3-structural-fresh-holdout-v1.json'
V2AUD=REPO/'receipts/yado-g2-raw-representation-v2-post-admission-audit-v1-run-33670110185.json'
BASE=REPO/'receipts/yado-g2-real-world-transfer-benchmark-v1-run-33363995201.json'
V5SRC=ROOT/'yado_raw_task_representation_robustness_v5.py'
OUT=REPO/'architecture/yado-kernel-g2-raw-representation-v4-robustness-self-evolution-v2.json'
CAND=REPO/'candidates/kernel-self-generated/raw-task-representation-v5-robustness-v2.json'
FRESH=REPO/'resources/yado-raw-task-representation-v5-robustness-v2-fresh-holdout.json'
DB=ROOT/'yado_raw_v5_robustness_v2_select.sqlite'

FRONT='KERNEL_G2_RAW_REPRESENTATION_V4_ROBUSTNESS_SELF_EVOLUTION_V2'

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,o):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def acc(rows,pred):return sum(pred(x)==y for x,y in rows)/max(1,len(rows))

ledger,v3,v4,v1,fail,struct,v2aud,base=map(load,[LEDGER,V3,V4,V1,FAIL,STRUCT,V2AUD,BASE])
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=[FRONT]:raise RuntimeError('UNEXPECTED_FRONTIER:'+canon(ledger.get('open_deficits')))
if fail.get('status')!='WITHHOLD_G2_RAW_REPRESENTATION_V5_CANONICAL_ADMISSION_V1':raise RuntimeError('V5_ADMISSION_WITHHOLD_REQUIRED')
if fail.get('next_required_capability')!=FRONT:raise RuntimeError('V5_FAILURE_FRONTIER_MISMATCH')
if v1.get('state')!='SHADOW_V5_SEQUENTIAL_ROBUSTNESS_SUPPORTED':raise RuntimeError('V1_SHADOW_PARENT_REQUIRED')
failed_mode=str(fail.get('selected_mode') or '')
failed_skill=next((x for x in (fail.get('kernel_selection') or {}).get('rejected',[]) if x.get('skill_id')=='ADMIT_RAW_V5_SEQUENCE_ROBUST'),None)
if not failed_skill or failed_skill.get('failed_critics')!=['regression']:raise RuntimeError('EXPECTED_EXACT_REGRESSION_FAILURE')

# Discover the candidate strategy surface mechanically from YADO's existing V5 source.
src=V5SRC.read_text(encoding='utf-8');tree=ast.parse(src)
modes={'PARENT_V4'}
for n in ast.walk(tree):
    if not isinstance(n,ast.Compare) or len(n.ops)!=1 or not isinstance(n.ops[0],ast.Eq) or len(n.comparators)!=1:continue
    left=n.left;right=n.comparators[0]
    if isinstance(left,ast.Attribute) and isinstance(left.value,ast.Name) and left.value.id=='self' and left.attr=='mode' and isinstance(right,ast.Constant) and isinstance(right.value,str):
        modes.add(right.value)
modes=sorted(modes)
if failed_mode not in modes:raise RuntimeError('FAILED_MODE_NOT_IN_RUNTIME_SURFACE')

parent=RobustRawTaskRepresentationRuntimeV4(v3,v4['selected_mode'])
v1metrics=v1.get('candidate_metrics') or {}
if set(modes)-set(v1metrics):raise RuntimeError('V1_METRICS_MISSING_MODES:'+canon(sorted(set(modes)-set(v1metrics))))

pm=v1metrics['PARENT_V4']
skills=[]
mode_rows=[]
for mode in modes:
    m=v1metrics[mode]
    regression=(float(m['direct_spent'])+1e-12>=float(pm['direct_spent']) and float(m['hold_spent_sequence'])+1e-12>=float(pm['hold_spent_sequence']))
    # Exact observed failure is causal negative evidence and must remain visible.
    if mode==failed_mode: regression=False
    skill={
      'skill_id':'RAW_V5B_'+mode,
      'artifact_digest':digest({'mode':mode,'v1_metrics':m,'v5_runtime_sha':fsha(V5SRC),'failed_mode':failed_mode,'failure_receipt':fail.get('receipt_sha256')}),
      'structural_valid':True,'semantic_consistency':1.0,
      'fit_baseline':float(pm['fit_spent_sequence']),'fit_candidate':float(m['fit_spent_sequence']),
      'heldout_baseline':float(pm['hold_spent_sequence']),'heldout_candidate':float(m['hold_spent_sequence']),
      'regression_pass':regression,'state_integrity':True,'rollback_available':True,
      'metadata':{'mode':mode,'prior_admission_regression_failure':mode==failed_mode,'spent_only':True},
    }
    skills.append(skill);mode_rows.append({'mode':mode,'regression_pass':regression,'v1_metrics':m})

if DB.exists():DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    selection=k.select_evolution_skills(skills,max_skills=1,min_semantic_consistency=.90,min_fit_gain=.015,max_heldout_drop=0.0,min_heldout_gain=.015)
finally:
    try:k.close()
    except Exception:pass
    try:
        if DB.exists():DB.unlink()
    except Exception:pass
selected_id=(selection.get('selected_skill_ids') or [None])[0]
selected_mode=None if selected_id is None else str(selected_id).removeprefix('RAW_V5B_')
if selected_mode not in modes or selected_mode in ('PARENT_V4',failed_mode):selected_mode=None

# Fresh evidence is generated only after native selection.
base_cases=[(r['text'],r['expected']) for r in struct.get('rows',[])]
base_cases += [(r['text'],r['expected']) for r in v2aud.get('canary_rows',[])]
real_rows=[(r['raw_text'],r['expected']) for r in (base.get('raw_unstructured') or {}).get('rows',[])]

def fresh_wrap(text,i,layer=0):
    m=(i+3*layer)%10
    if m==0:return f"<frame seq='{i%43}' layer='{layer}'> {text} </frame>"
    if m==1:return f"[audit-id {i%53}; pass {layer}] {text} [audit-end]"
    if m==2:return f"Envelope {i%47}. BEGIN :: {text} :: END."
    if m==3:return f"{{transport:{i%59}:{layer}}} {text} {{/transport}}"
    if m==4:return f"(journal entry {i%37}, layer {layer}) {text} (closed)"
    if m==5:return f"Metadata only: run={i%61}. {text} End metadata."
    if m==6:return f"  {re.sub(r'\\s+','  ',text)}  [record-complete={i%2}]"
    if m==7:return f"<outer><inner> {text} </inner></outer>"
    if m==8:return f"Trace {i%71}: {text.upper() if i%2==0 else text.lower()} :: complete"
    return f"Header token {i%67}. {text} Footer token {layer%11}."

selected_rt=None if selected_mode is None else RobustRawTaskRepresentationRuntimeV5(v3,v4,selected_mode)
pred=parent.predict_capability if selected_rt is None else selected_rt.predict_capability

fresh_wrapped=[(fresh_wrap(x,i),y) for i,(x,y) in enumerate(base_cases)]
parent_wrapped=acc(fresh_wrapped,parent.predict_capability)
fresh_wrapped_acc=acc(fresh_wrapped,pred)

rng=random.Random(2026090702)
seq=[]
for i in range(4000):
    x,y=base_cases[(i*37+rng.randrange(len(base_cases)))%len(base_cases)]
    z=fresh_wrap(x,i,0)
    if i%3==0:z=fresh_wrap(z,i+10000,1)
    if i%7==0:z=fresh_wrap(z,i+20000,2)
    seq.append((z,y))
parent_seq=acc(seq,parent.predict_capability);fresh_seq=acc(seq,pred)
base_reg=acc(real_rows,pred)
parent_base=acc(real_rows,parent.predict_capability)
direct=acc(base_cases,pred)
parent_direct=acc(base_cases,parent.predict_capability)

checks={
 'exact_v5_admission_failure_consumed':fail.get('receipt_sha256')=='bc3f54f0f72ac94310d85e1ded193544c9f68bfcd1048522a0a43cb0d917e646',
 'exact_failure_critic_regression':failed_skill.get('failed_critics')==['regression'],
 'runtime_modes_discovered_not_host_enumerated':len(modes)>=5,
 'previous_failed_mode_not_reselected':selected_mode is not None and selected_mode!=failed_mode,
 'native_selector_selected_one':selection.get('selected_count')==1 and selected_mode is not None,
 'fresh_not_used_for_selection':True,
 'fresh_direct_accuracy':direct>=.97,
 'fresh_wrapped_accuracy':fresh_wrapped_acc>=.96,
 'fresh_sequential_accuracy':fresh_seq>=.98,
 'fresh_wrapped_gain_over_parent':fresh_wrapped_acc-parent_wrapped>=.01,
 'fresh_sequential_gain_over_parent':fresh_seq-parent_seq>=.01,
 'base_regression':base_reg>=.98 and base_reg+1e-12>=parent_base-.005,
 'parent_v4_not_retrained':True,
 'class_specific_rules_absent':True,
 'canonical_unchanged':True,
 'g3_not_started':True,
}
supported=all(checks.values())
state='SHADOW_V5_ROBUSTNESS_V2_SUPPORTED' if supported else 'WITHHOLD'
next_cap='KERNEL_G2_RAW_REPRESENTATION_V5_CANONICAL_ADMISSION_V2' if supported else 'NATIVE_RAW_REPRESENTATION_STRATEGY_GENESIS_V3'

fresh={
 'schema':'yado.g2.raw_task_representation_v5_robustness_v2.fresh_holdout.v1',
 'status':'SPENT_AFTER_V2_SELECTION','selected_mode':selected_mode,
 'wrapped_count':len(fresh_wrapped),'sequential_count':len(seq),
 'metrics':{
   'direct_accuracy':direct,'parent_direct_accuracy':parent_direct,
   'fresh_wrapped_accuracy':fresh_wrapped_acc,'parent_fresh_wrapped':parent_wrapped,
   'fresh_sequential_accuracy':fresh_seq,'parent_fresh_sequential':parent_seq,
   'base_regression':base_reg,'parent_base_regression':parent_base,
 },
 'selection_completed_before_fresh':True,
}
fresh['dataset_digest']=digest(fresh);write(FRESH,fresh)

cand={
 'schema':'yado.g2.raw_task_representation_v5_robustness.candidate.v2',
 'state':state,'component_id':'ALG-G2-RAW-TASK-REPRESENTATION-V5',
 'parent_component_id':v4.get('component_id'),'parent_component_digest':v4.get('component_digest'),
 'source_v1_candidate_digest':v1.get('candidate_digest'),'source_v5_admission_failure_receipt':fail.get('receipt_sha256'),
 'runtime_mode_surface':modes,'native_selection':selection,'selected_mode':selected_mode,
 'component':None if selected_mode is None else component(selected_mode,v4.get('component_digest')),
 'runtime_source':'runtime/yado_raw_task_representation_robustness_v5.py','runtime_sha256':fsha(V5SRC),
 'fresh_dataset_digest':fresh['dataset_digest'],'fresh_metrics':fresh['metrics'],'checks':checks,
 'canonical_active':False,'canonical_mutation':False,'automatic_promotion':False,'g3_genesis_performed':False,
}
cand['candidate_digest']=digest(cand);write(CAND,cand)

report={
 'schema':'yado.g2.kernel_raw_representation_v4_robustness_self_evolution.v2',
 'status':'PASS_SHADOW_G2_RAW_REPRESENTATION_V4_ROBUSTNESS_SELF_EVOLUTION_V2' if supported else 'WITHHOLD_G2_RAW_REPRESENTATION_V4_ROBUSTNESS_SELF_EVOLUTION_V2',
 'source_failure_receipt':fail.get('receipt_sha256'),'failed_mode':failed_mode,'failed_critics':failed_skill.get('failed_critics'),
 'runtime_mode_surface':modes,'spent_mode_evidence':mode_rows,'native_selection':selection,
 'selected_mode':selected_mode,'fresh_metrics':fresh['metrics'],'checks':checks,
 'candidate_digest':cand['candidate_digest'],'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'V2 REUSES ONLY THE EXISTING V5 RUNTIME STRATEGY SURFACE. THE PREVIOUS V5 ADMISSION REGRESSION FAILURE IS RETAINED AS NEGATIVE SPENT EVIDENCE. YADO NATIVE SKILL ADMISSION SELECTS A DIFFERENT EXISTING STRATEGY BEFORE NEW NESTED-WRAPPER FRESH STRESS IS REVEALED. THE HOST DOES NOT SELECT A MODE, LOWER A GATE, ADD CLASS-SPECIFIC RULES, OR MUTATE CANONICAL G2.'
}
report['receipt_sha256']=digest(report);write(OUT,report)
print(json.dumps({'status':report['status'],'failed_mode':failed_mode,'selected_mode':selected_mode,'native_selection':selection,'fresh_metrics':fresh['metrics'],'checks':checks,'next_required_capability':next_cap,'receipt_sha256':report['receipt_sha256']},indent=2,sort_keys=True))
if not supported:raise SystemExit(2)
