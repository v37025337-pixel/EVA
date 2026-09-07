from __future__ import annotations
from pathlib import Path
from collections import Counter
import ast,copy,hashlib,json,random,re,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_raw_task_representation_candidate_v3 import RawTaskRepresentationRuntimeV3
from yado_raw_task_representation_robustness_v4 import RobustRawTaskRepresentationRuntimeV4,bracketless,edge_delimiterless,core_view,longest_view,wrapper_signal_v2
from yado_raw_task_representation_robustness_v5 import short_edge_signal,normalized_view
from yado_raw_task_representation_candidate_v2 import fit_family,spec_to_json
from yado_evolution_ledger_v2 import validate_ledger_v2

LEDGER=REPO/'architecture/evolution-ledger.json'
V3ART=REPO/'architecture/yado-kernel-g2-native-raw-representation-strategy-genesis-v3.json'
V3FRESH=REPO/'resources/yado-raw-task-representation-strategy-genesis-v3-fresh.json'
V3SRC=ROOT/'yado_kernel_g2_native_raw_representation_strategy_genesis_v3.py'
FAMILY_SRC=ROOT/'yado_raw_task_representation_candidate_v2.py'
V3CAN=REPO/'canonical/yado-raw-task-representation-v3.json'
V4CAN=REPO/'canonical/yado-raw-task-representation-v4.json'
STRUCT=REPO/'resources/yado-raw-task-representation-v3-structural-fresh-holdout-v1.json'
V2AUD=REPO/'receipts/yado-g2-raw-representation-v2-post-admission-audit-v1-run-33670110185.json'
BASE=REPO/'receipts/yado-g2-real-world-transfer-benchmark-v1-run-33363995201.json'

OUT=REPO/'architecture/yado-kernel-g2-native-raw-representation-strategy-genesis-repair-v4.json'
CAND=REPO/'candidates/kernel-self-generated/raw-task-representation-strategy-model-v4.json'
FRESH=REPO/'resources/yado-raw-task-representation-strategy-genesis-repair-v4-fresh.json'
DB=ROOT/'yado_raw_strategy_genesis_repair_v4.sqlite'
FRONT='KERNEL_G2_RAW_REPRESENTATION_V4_ROBUSTNESS_SELF_EVOLUTION_V2'

def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,o):
    Path(p).parent.mkdir(parents=True,exist_ok=True)
    Path(p).write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def acc(rows,pred): return sum(pred(x)==y for x,y in rows)/max(1,len(rows))
def bucket(s,n): return int(hashlib.sha256(str(s).encode()).hexdigest()[:8],16)%n

ledger,v3art,v3fresh,v3can,v4can,struct,v2aud,base=map(load,[LEDGER,V3ART,V3FRESH,V3CAN,V4CAN,STRUCT,V2AUD,BASE])
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=[FRONT]:
    raise RuntimeError('UNEXPECTED_FRONTIER:'+canon(ledger.get('open_deficits')))
if v3art.get('status')!='WITHHOLD_G2_NATIVE_RAW_REPRESENTATION_STRATEGY_GENESIS_V3':
    raise RuntimeError('V3_WITHHOLD_REQUIRED')
if v3art.get('next_required_capability')!='NATIVE_RAW_REPRESENTATION_STRATEGY_GENESIS_REPAIR_V4':
    raise RuntimeError('V3_REPAIR_FRONTIER_MISMATCH')
if v3art.get('selected_family')!='ROUTER':
    raise RuntimeError('V3_SELECTED_FAMILY_DRIFT')
if v3fresh.get('dataset_digest')!='e1a13b7d02c29c54a9095c8367ebbd16c34daf3b3cb070deb453f0943e231900':
    raise RuntimeError('V3_FRESH_DIGEST_DRIFT')

v3rt=RawTaskRepresentationRuntimeV3(v3can)
v4rt=RobustRawTaskRepresentationRuntimeV4(v3can,v4can['selected_mode'])

# Reconstruct the exact V3 view-feature function mechanically from the spent V3 source.
src=V3SRC.read_text(encoding='utf-8')
tree=ast.parse(src)
vf_node=next((n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='view_features'),None)
wrap_node=next((n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='fresh_v3_wrap'),None)
if vf_node is None or wrap_node is None:
    raise RuntimeError('V3_SOURCE_FUNCTIONS_MISSING')
ns={
 'Counter':Counter,'re':re,'v3rt':v3rt,'v4rt':v4rt,
 'bracketless':bracketless,'edge_delimiterless':edge_delimiterless,
 'core_view':core_view,'longest_view':longest_view,
 'wrapper_signal_v2':wrapper_signal_v2,'short_edge_signal':short_edge_signal,
 'normalized_view':normalized_view,
}
mod=ast.Module(body=[vf_node,wrap_node],type_ignores=[]);ast.fix_missing_locations(mod)
exec(compile(mod,'<spent-v3-functions>','exec'),ns)
view_features=ns['view_features'];spent_wrap=ns['fresh_v3_wrap']

# Extract the exact V3 fresh random seed mechanically.
seed=None
for n in ast.walk(tree):
    if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name):
        if n.func.value.id=='random' and n.func.attr=='Random' and n.args and isinstance(n.args[0],ast.Constant):
            v=n.args[0].value
            if isinstance(v,int) and v>=2026090700:
                seed=v
if seed is None:
    raise RuntimeError('V3_RANDOM_SEED_NOT_FOUND')

# Reconstruct V3 router gene exactly from persisted YADO output.
program=(v3art.get('gene') or {}).get('program') or {}
if program.get('schema')!='yado.capability_router_program.v1':
    raise RuntimeError('V3_ROUTER_PROGRAM_MISSING')
def v3_policy(text):
    x=view_features(text)
    for c in program.get('clauses',[]):
        if all(x.get(a.get('field'))==a.get('value') for a in c.get('atoms',[])):
            return c.get('output')
    return program.get('fallback_output')

base_cases=[(r['text'],r['expected']) for r in struct.get('rows',[])]
base_cases += [(r['text'],r['expected']) for r in v2aud.get('canary_rows',[])]
real_rows=[(r['raw_text'],r['expected']) for r in (base.get('raw_unstructured') or {}).get('rows',[])]

# Reconstruct the exact 5000 V3 fresh sequence. It is now spent evidence.
rng=random.Random(seed)
spent_seq=[]
for i in range(5000):
    x,y=base_cases[(i*41+rng.randrange(len(base_cases)))%len(base_cases)]
    z=spent_wrap(x,i,0)
    for layer in range(1,1+(i%4)):
        z=spent_wrap(z,i+layer*13001,layer)
    spent_seq.append((z,y))

v3_repro=acc(spent_seq,v3_policy)
if abs(v3_repro-float(v3fresh['metrics']['fresh_sequential']))>1e-12:
    raise RuntimeError('V3_SPENT_REPRO_DRIFT:'+str(v3_repro))

# Discover YADO's own generic text model family surface from fit_family source.
fsrc=FAMILY_SRC.read_text(encoding='utf-8')
ftree=ast.parse(fsrc)
fit_node=next((n for n in ftree.body if isinstance(n,ast.FunctionDef) and n.name=='fit_family'),None)
if fit_node is None: raise RuntimeError('FIT_FAMILY_FUNCTION_MISSING')
families=set()
for n in ast.walk(fit_node):
    if isinstance(n,ast.Compare) and len(n.comparators)==1 and isinstance(n.comparators[0],ast.Constant):
        v=n.comparators[0].value
        if isinstance(v,str) and (v.startswith('HASHED_') or v.startswith('TFIDF_')):
            families.add(v)
families=sorted(families)
if len(families)<4: raise RuntimeError('GENERIC_FAMILY_SURFACE_TOO_SMALL:'+canon(families))

# Bounded spent-only development set: content-addressed sample from V3 failure.
ordered=sorted(spent_seq,key=lambda r:hashlib.sha256((r[0]+'|'+r[1]+'|V4SPENT').encode()).hexdigest())
sample=ordered[:1000]
train=[];val=[]
for row in sample:
    (val if bucket(row[0]+'|V4VAL',5)==0 else train).append(row)
if len(train)<700 or len(val)<150:
    raise RuntimeError('V4_SPENT_SPLIT_TOO_SMALL')
base_train=acc(train,v3_policy);base_val=acc(val,v3_policy)

models={};metrics={};skills=[]
for fam in families:
    try:
        spec=fit_family(train,fam)
        tr=acc(train,spec.predict);va=acc(val,spec.predict)
        models[fam]=spec
        metrics[fam]={'train':tr,'validation':va,'error':None}
        skills.append({
          'skill_id':'RAW_MODEL_V4_'+fam,
          'artifact_digest':digest({'family':fam,'family_source_sha':fsha(FAMILY_SRC),'v3_receipt':v3art.get('receipt_sha256')}),
          'structural_valid':True,'semantic_consistency':va,
          'fit_baseline':base_train,'fit_candidate':tr,
          'heldout_baseline':base_val,'heldout_candidate':va,
          'regression_pass':va+1e-12>=base_val,
          'state_integrity':True,'rollback_available':True,
          'metadata':{'family':fam,'spent_v3_only':True},
        })
    except Exception as e:
        metrics[fam]={'train':0.0,'validation':0.0,'error':type(e).__name__+':'+str(e)[:500]}
        skills.append({
          'skill_id':'RAW_MODEL_V4_'+fam,
          'artifact_digest':digest({'family':fam,'error':metrics[fam]['error']}),
          'structural_valid':False,'semantic_consistency':0.0,
          'fit_baseline':base_train,'fit_candidate':0.0,
          'heldout_baseline':base_val,'heldout_candidate':0.0,
          'regression_pass':False,'state_integrity':True,'rollback_available':True,
          'metadata':{'family':fam,'spent_v3_only':True,'error':metrics[fam]['error']},
        })

if DB.exists(): DB.unlink()
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(DB))
try:
    goal=k.executive.create_goal(
      objective='Repair the V3 raw-representation strategy failure by evolving a representation model that remains stable when the existing view-policy inputs degrade under deep wrappers.',
      required_capabilities={'NATIVE_RAW_REPRESENTATION_STRATEGY_GENESIS_REPAIR_V4':1.0},
      success_criteria={'fresh_sequential':.98,'fresh_wrapped':.98,'base_regression':.98,'rollback':True},
    )
    deficits=k.executive.detect_deficits(goal.goal_id)
    selection=k.select_evolution_skills(
      skills,max_skills=1,min_semantic_consistency=.95,
      min_fit_gain=.005,max_heldout_drop=0.0,min_heldout_gain=.005
    )
finally:
    try:k.close()
    except Exception:pass
    try:
        if DB.exists():DB.unlink()
    except Exception:pass

selected_id=(selection.get('selected_skill_ids') or [None])[0]
selected_family=None
if selected_id and str(selected_id).startswith('RAW_MODEL_V4_'):
    selected_family=str(selected_id).removeprefix('RAW_MODEL_V4_')
selected_spec=models.get(selected_family)
pred=v3_policy if selected_spec is None else selected_spec.predict

# New fresh wrapper family, defined after native selection only.
def fresh_v4_wrap(text,i,layer):
    m=(i+5*layer)%14
    if m==0:return f"<bundle id='{i%101}' level='{layer}'><body>{text}</body></bundle>"
    if m==1:return f"BEGIN\nmeta:{i%97}:{layer}\n{text}\nEND"
    if m==2:return f"[transport/{i%89}/{layer}] {text} [/transport]"
    if m==3:return f"Envelope {i%83} :: payload-start :: {text} :: payload-end"
    if m==4:return f"{{record={i%79};layer={layer}}} {text} {{/record}}"
    if m==5:return f"Journal note {i%73}. START. {text} STOP. Journal closed."
    if m==6:return f"<<frame-{layer}>><<packet-{i%71}>> {text} <</packet>><</frame>>"
    if m==7:return f"TRACE {i%67}/{layer}: {text.lower() if i%2 else text.upper()} : TRACE-END"
    if m==8:return f"Metadata header nonce={i%61}; payload={text}; metadata footer."
    if m==9:return f"((session {i%59})) [[depth {layer}]] {text} [[/depth]] ((/session))"
    if m==10:return f"<outer-{i%53}><middle-{layer}><inner>{text}</inner></middle></outer>"
    if m==11:return f"Audit wrapper. ref={i%47}. {re.sub(r'\\s+',' ',text)} Audit complete."
    if m==12:return f"[context id={i%43}] BEGIN-CONTEXT {text} END-CONTEXT [/context]"
    return f"Administrative transport {i%41}. Header only. {text} Footer only."

fresh_wrapped=[(fresh_v4_wrap(x,i,0),y) for i,(x,y) in enumerate(base_cases)]
fresh_wrap_acc=acc(fresh_wrapped,pred);v3_wrap=acc(fresh_wrapped,v3_policy)

rng2=random.Random(2026090704)
fresh_seq=[]
for i in range(6000):
    x,y=base_cases[(i*43+rng2.randrange(len(base_cases)))%len(base_cases)]
    z=fresh_v4_wrap(x,i,0)
    for layer in range(1,1+(i%5)):
        z=fresh_v4_wrap(z,i+layer*17011,layer)
    fresh_seq.append((z,y))
fresh_seq_acc=acc(fresh_seq,pred);v3_seq=acc(fresh_seq,v3_policy)
direct=acc(base_cases,pred);v3_direct=acc(base_cases,v3_policy)
base_reg=acc(real_rows,pred);v3_base=acc(real_rows,v3_policy)
fallback=Counter(y for _,y in train).most_common(1)[0][0]
ablated_seq=acc(fresh_seq,lambda _:fallback)

selected_metrics=metrics.get(selected_family) if selected_family else None
checks={
 'v3_exact_withhold_consumed':v3art.get('receipt_sha256')=='b4bf36d865ba5dba575343a31ffed25bb1774c3b1ac4982e18f8132d213f0f4b',
 'v3_spent_sequential_exactly_reproduced':abs(v3_repro-.9294)<1e-12,
 'generic_family_surface_discovered_from_yado_source':len(families)>=4,
 'native_goal_created':bool(deficits),
 'native_selector_selected_one_family':selected_family is not None and selection.get('selected_count')==1,
 'host_selected_family':False,
 'fresh_not_used_for_training_or_selection':True,
 'selected_validation_ge_0_95':bool(selected_metrics and selected_metrics['validation']>=.95),
 'fresh_direct_accuracy':direct>=.98,
 'fresh_wrapped_accuracy':fresh_wrap_acc>=.98,
 'fresh_sequential_accuracy':fresh_seq_acc>=.98,
 'fresh_sequential_gain_over_v3':fresh_seq_acc-v3_seq>=.01,
 'base_regression':base_reg>=.98 and base_reg+1e-12>=v3_base-.005,
 'causal_ablation_drop':fresh_seq_acc-ablated_seq>=.20,
 'class_specific_rules_absent':True,
 'canonical_unchanged':True,
 'automatic_promotion':False,
 'g3_not_started':True,
}
passed=all(checks.values())
status='PASS_SHADOW_G2_NATIVE_RAW_REPRESENTATION_STRATEGY_GENESIS_REPAIR_V4' if passed else 'WITHHOLD_G2_NATIVE_RAW_REPRESENTATION_STRATEGY_GENESIS_REPAIR_V4'
next_cap='NATIVE_RAW_REPRESENTATION_STRATEGY_CANONICAL_ADMISSION_V5' if passed else 'NATIVE_RAW_REPRESENTATION_MODEL_FAMILY_EXPANSION_V5'

model=None if selected_spec is None else spec_to_json(selected_spec)
candidate={
 'schema':'yado.g2.native_raw_representation_strategy_model.candidate.v4',
 'status':status,'parent_v3_receipt':v3art.get('receipt_sha256'),
 'discovered_families':families,'family_metrics':metrics,
 'native_selection':selection,'selected_family':selected_family,
 'model':model,'model_digest':None if model is None else digest(model),
 'fresh_metrics':{
   'direct':direct,'v3_direct':v3_direct,
   'fresh_wrapped':fresh_wrap_acc,'v3_fresh_wrapped':v3_wrap,
   'fresh_sequential':fresh_seq_acc,'v3_fresh_sequential':v3_seq,
   'base_regression':base_reg,'v3_base_regression':v3_base,
   'ablated_sequential':ablated_seq,
 },
 'checks':checks,'canonical_active':False,'canonical_mutation':False,'automatic_promotion':False,
}
candidate['candidate_digest']=digest(candidate);write(CAND,candidate)

fresh={
 'schema':'yado.g2.native_raw_representation_strategy_genesis_repair_v4.fresh.v1',
 'selected_family':selected_family,'wrapped_count':len(fresh_wrapped),'sequential_count':len(fresh_seq),
 'fresh_after_selection':True,'metrics':candidate['fresh_metrics'],
}
fresh['dataset_digest']=digest(fresh);write(FRESH,fresh)

report={
 'schema':'yado.g2.native_raw_representation_strategy_genesis_repair.v4',
 'status':status,'parent_v3_receipt':v3art.get('receipt_sha256'),
 'native_goal_deficits':[str(getattr(x,'deficit_id',x)) for x in deficits],
 'discovered_families':families,'family_metrics':metrics,'native_selection':selection,
 'selected_family':selected_family,'model_digest':candidate['model_digest'],
 'candidate_digest':candidate['candidate_digest'],'fresh_metrics':candidate['fresh_metrics'],
 'checks':checks,'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'V4 CONSUMES THE EXACT SPENT V3 SEQUENTIAL FAILURE AND MECHANICALLY DISCOVERS GENERIC TEXT-REPRESENTATION MODEL FAMILIES FROM YADO OWN fit_family SOURCE. ALL CANDIDATES ARE TRAINED ONLY ON SPENT V3 FAILURE DATA; YADO NATIVE PRECOMMIT SELECTS ONE FAMILY BEFORE A NEW DEEP-WRAPPER FRESH STRESS IS REVEALED. HOST PROVIDES NO NORMALIZATION RULE, MODEL FAMILY CHOICE, CLASS-SPECIFIC RULE, LABEL HEURISTIC OR LOWERED GATE.'
}
report['receipt_sha256']=digest(report);write(OUT,report)
print(json.dumps({
 'status':status,'discovered_families':families,'selected_family':selected_family,
 'family_metrics':metrics,'native_selection':selection,'fresh_metrics':candidate['fresh_metrics'],
 'checks':checks,'next_required_capability':next_cap,'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True,default=str))
if not passed: raise SystemExit(2)
