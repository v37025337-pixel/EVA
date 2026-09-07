from __future__ import annotations
from pathlib import Path
from collections import Counter
import ast,hashlib,json,random,re,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_raw_task_representation_candidate_v3 import RawTaskRepresentationRuntimeV3
from yado_raw_task_representation_robustness_v4 import RobustRawTaskRepresentationRuntimeV4,bracketless,edge_delimiterless,core_view,longest_view,wrapper_signal_v2
from yado_raw_task_representation_robustness_v5 import RobustRawTaskRepresentationRuntimeV5,short_edge_signal,normalized_view
from yado_bounded_capability_router_v1 import BoundedCapabilityRouterLearnerV1,router_acc
from yado_conjunctive_rule_inducer_v1 import ConjunctiveRuleInducerV1,program_acc,canonical_program
from yado_core_v2_1 import BoundedRuleSandbox
from yado_evolution_ledger_v2 import validate_ledger_v2

LEDGER=REPO/'architecture/evolution-ledger.json'
V3=REPO/'canonical/yado-raw-task-representation-v3.json'
V4=REPO/'canonical/yado-raw-task-representation-v4.json'
V2REP=REPO/'architecture/yado-kernel-g2-raw-representation-v4-robustness-self-evolution-v2.json'
V2SRC=ROOT/'yado_kernel_g2_raw_representation_v4_robustness_self_evolution_v2.py'
STRUCT=REPO/'resources/yado-raw-task-representation-v3-structural-fresh-holdout-v1.json'
V2AUD=REPO/'receipts/yado-g2-raw-representation-v2-post-admission-audit-v1-run-33670110185.json'
BASE=REPO/'receipts/yado-g2-real-world-transfer-benchmark-v1-run-33363995201.json'
OUT=REPO/'architecture/yado-kernel-g2-native-raw-representation-strategy-genesis-v3.json'
CAND=REPO/'candidates/kernel-self-generated/raw-task-representation-strategy-gene-v3.json'
FRESH=REPO/'resources/yado-raw-task-representation-strategy-genesis-v3-fresh.json'
DB=ROOT/'yado_raw_strategy_genesis_v3.sqlite'
FRONT='KERNEL_G2_RAW_REPRESENTATION_V4_ROBUSTNESS_SELF_EVOLUTION_V2'

def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def write(p,o):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def acc(rows,pred):return sum(pred(x)==y for x,y in rows)/max(1,len(rows))
def hbucket(s,n):return int(hashlib.sha256(str(s).encode()).hexdigest()[:8],16)%n

ledger,v3,v4,v2rep,struct,v2aud,base=map(load,[LEDGER,V3,V4,V2REP,STRUCT,V2AUD,BASE])
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=[FRONT]:raise RuntimeError('UNEXPECTED_FRONTIER:'+canon(ledger.get('open_deficits')))
if v2rep.get('status')!='WITHHOLD_G2_RAW_REPRESENTATION_V4_ROBUSTNESS_SELF_EVOLUTION_V2':raise RuntimeError('V2_WITHHOLD_REQUIRED')
if v2rep.get('next_required_capability')!='NATIVE_RAW_REPRESENTATION_STRATEGY_GENESIS_V3':raise RuntimeError('V2_FRONTIER_MISMATCH')
if v2rep.get('selected_mode')!='CORE_GUARDED':raise RuntimeError('V2_SELECTED_MODE_DRIFT')

v3rt=RawTaskRepresentationRuntimeV3(v3)
v4rt=RobustRawTaskRepresentationRuntimeV4(v3,v4['selected_mode'])
baseline=RobustRawTaskRepresentationRuntimeV5(v3,v4,'CORE_GUARDED')

def view_features(text):
    p4=v4rt.predict_capability(text)
    raw=v3rt.predict_capability(str(text))
    core=v3rt.predict_capability(core_view(text))
    edge=v3rt.predict_capability(edge_delimiterless(text))
    long=v3rt.predict_capability(longest_view(edge_delimiterless(text)))
    norm=v3rt.predict_capability(normalized_view(text))
    cn=v3rt.predict_capability(core_view(normalized_view(text)))
    br=v3rt.predict_capability(bracketless(text))
    preds=[p4,raw,core,edge,long,norm,cn,br]
    maj=Counter(preds).most_common(1)[0][0]
    tok=len(re.findall(r"[A-Za-z0-9_]+",str(text)))
    return {
      'p4':p4,'raw':raw,'core':core,'edge':edge,'long':long,'norm':norm,'core_norm':cn,'bracketless':br,
      'majority':maj,'unique_predictions':len(set(preds)),
      'p4_eq_core':p4==core,'p4_eq_majority':p4==maj,'core_eq_edge':core==edge,'core_eq_long':core==long,
      'wrapper_signal':bool(wrapper_signal_v2(text)),'short_edge_signal':bool(short_edge_signal(text)),
      'token_bucket':min(7,tok//8),
    }

base_cases=[(r['text'],r['expected']) for r in struct.get('rows',[])]
base_cases += [(r['text'],r['expected']) for r in v2aud.get('canary_rows',[])]
real_rows=[(r['raw_text'],r['expected']) for r in (base.get('raw_unstructured') or {}).get('rows',[])]

# Reconstruct the exact already-spent V2 fresh transform directly from the V2 observer source.
v2source=V2SRC.read_text(encoding='utf-8');v2tree=ast.parse(v2source)
fn=next((n for n in v2tree.body if isinstance(n,ast.FunctionDef) and n.name=='fresh_wrap'),None)
if fn is None:raise RuntimeError('V2_FRESH_WRAP_SOURCE_MISSING')
mod=ast.Module(body=[fn],type_ignores=[]);ast.fix_missing_locations(mod)
ns={'re':re};exec(compile(mod,'<v2-spent-wrap>','exec'),ns)
spent_wrap=ns['fresh_wrap']
seed=None
for n in ast.walk(v2tree):
    if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='random' and n.func.attr=='Random' and n.args and isinstance(n.args[0],ast.Constant) and isinstance(n.args[0].value,int):
        if n.args[0].value>=2026090000:seed=n.args[0].value;break
if seed is None:raise RuntimeError('V2_SPENT_RANDOM_SEED_NOT_FOUND')

spent=[]
for i,(x,y) in enumerate(base_cases):
    spent.append((spent_wrap(x,i,0),y))
rng=random.Random(seed)
for i in range(4000):
    x,y=base_cases[(i*37+rng.randrange(len(base_cases)))%len(base_cases)]
    z=spent_wrap(x,i,0)
    if i%3==0:z=spent_wrap(z,i+10000,1)
    if i%7==0:z=spent_wrap(z,i+20000,2)
    spent.append((z,y))

# Exact spent-data reproduction check before learning.
spent_seq=spent[len(base_cases):]
repro_seq=acc(spent_seq,baseline.predict_capability)
repro_wrap=acc(spent[:len(base_cases)],baseline.predict_capability)
if abs(repro_seq-float(v2rep['fresh_metrics']['fresh_sequential_accuracy']))>1e-12:raise RuntimeError('V2_SPENT_SEQ_REPRO_DRIFT')
if abs(repro_wrap-float(v2rep['fresh_metrics']['fresh_wrapped_accuracy']))>1e-12:raise RuntimeError('V2_SPENT_WRAP_REPRO_DRIFT')

# Deterministically bound the spent corpus and split before synthesis.
ordered=sorted(spent,key=lambda z:hashlib.sha256((z[0]+'|'+str(z[1])+'|V3SPENT').encode()).hexdigest())
bounded=ordered[:1800]
train=[];val=[]
for text,y in bounded:
    row={'input':view_features(text),'expected':y}
    (val if hbucket(text+'|VAL',5)==0 else train).append(row)
if len(train)<800 or len(val)<200:raise RuntimeError('V3_SPLIT_TOO_SMALL')
fallback=Counter(e['expected'] for e in train).most_common(1)[0][0]

learners=[]
programs={}

try:
    p=BoundedCapabilityRouterLearnerV1.synthesize(train,val,fallback,min_support=5)
    tr=router_acc(p,train);va=router_acc(p,val);ab=router_acc(p,val,ablated=True)
    programs['ROUTER']=p
    learners.append({'family':'ROUTER','skill_id':'RAW_STRATEGY_V3_ROUTER','train':tr,'validation':va,'ablation':ab,'program':p.canonical(),'error':None})
except Exception as e:
    learners.append({'family':'ROUTER','skill_id':'RAW_STRATEGY_V3_ROUTER','train':0.0,'validation':0.0,'ablation':0.0,'program':None,'error':type(e).__name__+':'+str(e)[:500]})

try:
    p=ConjunctiveRuleInducerV1.synthesize('RAW_REPRESENTATION_DYNAMIC_VIEW_POLICY_V3','INTELLIGENCE',train,min_support=5,max_rules=12)
    tr=program_acc(p,train);va=program_acc(p,val);ab=program_acc(p,val,ablated=True)
    programs['CONJUNCTIVE']=p
    learners.append({'family':'CONJUNCTIVE','skill_id':'RAW_STRATEGY_V3_CONJUNCTIVE','train':tr,'validation':va,'ablation':ab,'program':canonical_program(p),'error':None})
except Exception as e:
    learners.append({'family':'CONJUNCTIVE','skill_id':'RAW_STRATEGY_V3_CONJUNCTIVE','train':0.0,'validation':0.0,'ablation':0.0,'program':None,'error':type(e).__name__+':'+str(e)[:500]})

baseline_train=sum(baseline.predict_capability(next(t for t,y in bounded if view_features(t)==e['input']))==e['expected'] for e in train)/len(train) if False else None
# Re-evaluate baseline directly on corresponding deterministic text splits.
train_text=[];val_text=[]
for text,y in bounded:
    (val_text if hbucket(text+'|VAL',5)==0 else train_text).append((text,y))
base_tr=acc(train_text,baseline.predict_capability);base_va=acc(val_text,baseline.predict_capability)

skills=[]
for row in learners:
    skills.append({
      'skill_id':row['skill_id'],'artifact_digest':digest({'family':row['family'],'program':row['program'],'v2':v2rep.get('receipt_sha256')}),
      'structural_valid':row['program'] is not None,
      'semantic_consistency':float(row['validation']),
      'fit_baseline':base_tr,'fit_candidate':float(row['train']),
      'heldout_baseline':base_va,'heldout_candidate':float(row['validation']),
      'regression_pass':row['program'] is not None and row['validation']+1e-12>=base_va,
      'state_integrity':True,'rollback_available':True,
      'metadata':{'family':row['family'],'ablation_validation':row['ablation'],'spent_only':True},
    })

if DB.exists():DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    goal=k.executive.create_goal(
      objective='Synthesize a new context-dependent raw-representation view policy after all fixed V5 global modes failed strict sequential admission.',
      required_capabilities={'NATIVE_RAW_REPRESENTATION_STRATEGY_GENESIS_V3':1.0},
      success_criteria={'fresh_sequential':.98,'ablation_required':True,'rollback':True},
    )
    deficits=k.executive.detect_deficits(goal.goal_id)
    selection=k.select_evolution_skills(skills,max_skills=1,min_semantic_consistency=.95,min_fit_gain=.005,max_heldout_drop=0.0,min_heldout_gain=.005)
finally:
    try:k.close()
    except Exception:pass
    try:
        if DB.exists():DB.unlink()
    except Exception:pass

selected_id=(selection.get('selected_skill_ids') or [None])[0]
selected_family='ROUTER' if selected_id=='RAW_STRATEGY_V3_ROUTER' else ('CONJUNCTIVE' if selected_id=='RAW_STRATEGY_V3_CONJUNCTIVE' else None)
selected_program=programs.get(selected_family)

def policy_predict(text,ablated=False):
    f=view_features(text)
    if selected_family=='ROUTER':return selected_program.execute(f,ablated=ablated)
    if selected_family=='CONJUNCTIVE':return BoundedRuleSandbox.execute(selected_program,f,ablated=ablated)
    return baseline.predict_capability(text)

# New fresh family, defined only after selection.
def fresh_v3_wrap(text,i,layer):
    m=(i*3+layer)%12
    if m==0:return f"<telemetry><id>{i%97}</id><payload>{text}</payload></telemetry>"
    if m==1:return f"BEGIN RECORD {i%89}\n{text}\nEND RECORD"
    if m==2:return f"[meta layer={layer} ref={i%83}] :: {text} :: [/meta]"
    if m==3:return f"Envelope#{i%79} {{ {text} }} /Envelope"
    if m==4:return f"Journal header {i%73}; {text}; journal footer."
    if m==5:return f"Transport note only. Sequence={i%71}. {text} Transport complete."
    if m==6:return f"((frame {layer})) [[packet {i%67}]] {text} [[/packet]] ((/frame))"
    if m==7:return f"TRACE/{i%61}/{layer}: {text.lower() if i%2 else text.upper()} :ENDTRACE"
    if m==8:return f"  <context-{i%59}>   {re.sub(r'\\s+',' ',text)}   </context-{i%59}>  "
    if m==9:return f"Header: nonce {i%53}. Body: {text} Footer: closed."
    if m==10:return f"{{session={i%47};depth={layer}}} {text} {{/session}}"
    return f"Administrative wrapper {i%43}. START {text} FINISH."

fresh_wrap_rows=[(fresh_v3_wrap(x,i,0),y) for i,(x,y) in enumerate(base_cases)]
fresh_wrap_acc=acc(fresh_wrap_rows,policy_predict)
base_wrap_acc=acc(fresh_wrap_rows,baseline.predict_capability)

rng2=random.Random(2026090703)
fresh_seq=[]
for i in range(5000):
    x,y=base_cases[(i*41+rng2.randrange(len(base_cases)))%len(base_cases)]
    z=fresh_v3_wrap(x,i,0)
    for layer in range(1,1+(i%4)):
        z=fresh_v3_wrap(z,i+layer*13001,layer)
    fresh_seq.append((z,y))
fresh_seq_acc=acc(fresh_seq,policy_predict);base_seq_acc=acc(fresh_seq,baseline.predict_capability)
direct=acc(base_cases,policy_predict);base_direct=acc(base_cases,baseline.predict_capability)
base_reg=acc(real_rows,policy_predict);baseline_real=acc(real_rows,baseline.predict_capability)
ablated_seq=acc(fresh_seq,lambda x:policy_predict(x,ablated=True))

selected_row=next((x for x in learners if x['family']==selected_family),None)
checks={
 'v2_exact_withhold_consumed':v2rep.get('receipt_sha256')=='5a489eddec0b04dfdd5651771d4ba4efd52b7acd8b1f552c61dcadb227f959a2',
 'v2_spent_evidence_exactly_reproduced':abs(repro_seq-.9695)<1e-12 and abs(repro_wrap-.975)<1e-12,
 'native_goal_created':bool(deficits),
 'two_native_families_attempted':len(learners)==2,
 'host_selected_family':False,
 'lexical_task_words_not_features':all(k not in {'text','words','tokens'} for k in view_features('x').keys()),
 'native_selector_selected_one_family':selected_family is not None and selection.get('selected_count')==1,
 'selected_policy_validation_ge_0_95':bool(selected_row and selected_row['validation']>=.95),
 'fresh_not_used_for_synthesis_or_selection':True,
 'fresh_direct_accuracy':direct>=.98,
 'fresh_wrapped_accuracy':fresh_wrap_acc>=.98,
 'fresh_sequential_accuracy':fresh_seq_acc>=.98,
 'fresh_sequential_gain_over_core_guarded':fresh_seq_acc-base_seq_acc>=.005,
 'base_regression':base_reg>=.98 and base_reg+1e-12>=baseline_real-.005,
 'causal_ablation_drop':fresh_seq_acc-ablated_seq>=.05,
 'canonical_unchanged':True,
 'automatic_promotion':False,
 'g3_not_started':True,
}
passed=all(checks.values())
status='PASS_SHADOW_G2_NATIVE_RAW_REPRESENTATION_STRATEGY_GENESIS_V3' if passed else 'WITHHOLD_G2_NATIVE_RAW_REPRESENTATION_STRATEGY_GENESIS_V3'
next_cap='NATIVE_RAW_REPRESENTATION_STRATEGY_SOURCE_REALIZATION_V4' if passed else 'NATIVE_RAW_REPRESENTATION_STRATEGY_GENESIS_REPAIR_V4'

gene=None
if selected_family:
    gene={
      'schema':'yado.g2.native_raw_representation_strategy_gene.v3',
      'gene_id':'GENE-G2-RAW-REP-STRATEGY-V3-'+digest({'family':selected_family,'program':selected_row['program'],'v2':v2rep.get('receipt_sha256')})[:16],
      'origin':'YADO_NATIVE_LEARNER_SELECTION_OVER_SPENT_V2_FAILURE_EVIDENCE',
      'family':selected_family,'feature_contract':sorted(view_features('probe').keys()),
      'program':selected_row['program'],'validation':selected_row['validation'],'ablation_validation':selected_row['ablation'],
      'promotion_state':'SHADOW_ONLY','canonical_active':False,
    }
    gene['gene_digest']=digest(gene)

fresh={
 'schema':'yado.g2.native_raw_representation_strategy_genesis_v3.fresh.v1','selected_family':selected_family,
 'metrics':{'direct':direct,'baseline_direct':base_direct,'fresh_wrapped':fresh_wrap_acc,'baseline_wrapped':base_wrap_acc,
            'fresh_sequential':fresh_seq_acc,'baseline_sequential':base_seq_acc,'base_regression':base_reg,'baseline_base_regression':baseline_real,
            'ablated_sequential':ablated_seq},
 'wrapped_count':len(fresh_wrap_rows),'sequential_count':len(fresh_seq),'fresh_after_selection':True,
}
fresh['dataset_digest']=digest(fresh);write(FRESH,fresh)
cand={'schema':'yado.g2.native_raw_representation_strategy_genesis.candidate.v3','status':status,'gene':gene,
      'learners':learners,'native_selection':selection,'fresh_metrics':fresh['metrics'],'checks':checks,
      'canonical_active':False,'canonical_mutation':False,'automatic_promotion':False}
cand['candidate_digest']=digest(cand);write(CAND,cand)
report={'schema':'yado.g2.native_raw_representation_strategy_genesis.v3','status':status,
        'parent_v2_receipt':v2rep.get('receipt_sha256'),'native_goal_deficits':[str(getattr(x,'deficit_id',x)) for x in deficits],
        'learners':learners,'native_selection':selection,'selected_family':selected_family,'gene':gene,
        'fresh_metrics':fresh['metrics'],'checks':checks,'candidate_digest':cand['candidate_digest'],
        'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,'next_required_capability':next_cap,
        'semantic_boundary':'V3 SYNTHESIZES A CONTEXT-DEPENDENT POLICY OVER YADO OWN EXISTING REPRESENTATION VIEWS. INPUT FEATURES CONTAIN ONLY VIEW PREDICTIONS, AGREEMENT STRUCTURE, GENERIC WRAPPER SIGNALS AND LENGTH BUCKETS; NO DOMAIN WORDS OR CLASS-SPECIFIC RULES ARE PROVIDED. TWO NATIVE LEARNER FAMILIES COMPETE UNDER THE PRECOMMIT GATE BEFORE NEW FRESH NESTED-WRAPPER STRESS.'}
report['receipt_sha256']=digest(report);write(OUT,report)
print(json.dumps({'status':status,'selected_family':selected_family,'learner_metrics':[{k:v for k,v in x.items() if k!='program'} for x in learners],
                  'native_selection':selection,'fresh_metrics':fresh['metrics'],'checks':checks,'next_required_capability':next_cap,
                  'gene_id':None if gene is None else gene['gene_id'],'receipt_sha256':report['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit(2)
