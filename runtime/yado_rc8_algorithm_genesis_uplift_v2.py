from __future__ import annotations
from pathlib import Path
import hashlib, itertools, json, os, random, sys

ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(PKG))

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_algorithm_component_runtime_native_v1 import (
    predict_logic_component, predict_intel_component, thinking_component_acc
)

OUT_DIR=ROOT/'rc8_cognitive_genesis_bundle_v2'
OUT_DIR.mkdir(exist_ok=True)

def hbucket(obj, mod=100):
    raw=json.dumps(obj,sort_keys=True,separators=(',',':')).encode()
    return int(hashlib.sha256(raw).hexdigest()[:8],16)%mod

def split_rows(rows):
    fit=[]; val=[]; blind=[]
    for row in rows:
        b=hbucket(row)
        if b<22: blind.append(row)
        elif b<45: val.append(row)
        else: fit.append(row)
    return fit,val,fit+val,blind

k=UnifiedYADOKernelV30RC8ExternalCognitive(
    db_path=str(OUT_DIR/'genesis.sqlite')
)

# ------------------------------------------------------------------
# LOGIC: a new architecture-admission relation using fresh feature names.
# The target intentionally requires a context interaction not present in the
# currently registered RC8 BOOLEAN_PROGRAM.
# ------------------------------------------------------------------
logic_rows=[]
for vals in itertools.product([False,True],repeat=5):
    x=dict(zip(['integrity_ok','fresh_verified','rollback_ready','counterexample_open','cross_domain_transfer'],vals))
    y=bool(
        x['integrity_ok'] and
        x['fresh_verified'] and
        x['rollback_ready'] and
        (x['cross_domain_transfer'] != x['counterexample_open'])
    )
    logic_rows.append((x,y))
logic_fit,logic_val,logic_revealed,logic_blind=split_rows(logic_rows)

def logic_baseline_acc(rows):
    return sum(bool(k.logic_evolved_decision(x))==bool(y) for x,y in rows)/max(1,len(rows))

logic_baseline=logic_baseline_acc(logic_blind)
logic_rc5=k.synthesize_logic_algorithm_component(logic_fit,logic_val,logic_revealed,logic_blind)
logic_rc6=k.synthesize_logic_with_extended_meta_grammar(logic_fit,logic_val,logic_revealed,logic_blind)

# ------------------------------------------------------------------
# THINKING: same action set, two context-dependent causal plans.
# Current registered THINKING is a global precedence graph and cannot see
# episode context; RC5/RC6 may synthesize a conditional component.
# ------------------------------------------------------------------
roles=['OBSERVE','RESEARCH','DIAGNOSE','HYPOTHESIZE','SIMULATE','TEST','ROLLBACK','VERIFY','COMMIT']
safe_order=['OBSERVE','RESEARCH','HYPOTHESIZE','SIMULATE','DIAGNOSE','TEST','VERIFY','ROLLBACK','COMMIT']
risk_order=['OBSERVE','DIAGNOSE','ROLLBACK','RESEARCH','HYPOTHESIZE','SIMULATE','TEST','VERIFY','COMMIT']

thinking_rows=[]
rng=random.Random(70177)
for i in range(96):
    ctx={
        'integrity_risk': (i%8)/7,
        'uncertainty': ((i*3)%11)/10,
        'novelty': ((i*5)%13)/12,
    }
    high=(ctx['integrity_risk']+ctx['uncertainty'])>1.0
    actions=[{'id':f'{i}-{j}','role':r} for j,r in enumerate(roles)]
    rng.shuffle(actions)
    expected=risk_order if high else safe_order
    thinking_rows.append((ctx,actions,expected))
thinking_fit,thinking_val,thinking_revealed,thinking_blind=split_rows(thinking_rows)

def thinking_baseline_acc(rows):
    ok=0
    for ctx,actions,expected in rows:
        ids=k.thinking_evolved_plan(actions)
        role_by_id={str(a['id']):str(a['role']) for a in actions}
        pred=[role_by_id[str(i)] for i in ids]
        ok += pred==expected
    return ok/max(1,len(rows))

thinking_baseline=thinking_baseline_acc(thinking_blind)
thinking_rc5=k.synthesize_thinking_algorithm_component(thinking_fit,thinking_val,thinking_revealed,thinking_blind)
thinking_rc6=k.synthesize_thinking_with_extended_meta_grammar(thinking_fit,thinking_val,thinking_revealed,thinking_blind)

# ------------------------------------------------------------------
# INTELLIGENCE: architecture-development meta-action policy.
# Uses a new evidence coordinate system; target is not an architecture name.
# ------------------------------------------------------------------
intel_rows=[]
levels={
    'integrity_score':[0.2,0.9],
    'rollback_score':[0.2,0.9],
    'fresh_blind':[0.55,0.78,0.93,0.99],
    'ablation_drop':[0.05,0.27],
    'transfer_score':[0.45,0.86],
    'evidence_coverage':[0.42,0.78],
}
for vals in itertools.product(*levels.values()):
    x=dict(zip(levels,vals))
    if x['integrity_score']<0.5 or x['rollback_score']<0.5:
        y='ROLLBACK'
    elif x['fresh_blind']>=0.90 and x['ablation_drop']>=0.20 and x['transfer_score']>=0.80:
        y='PROMOTE_CANDIDATE'
    elif x['evidence_coverage']<0.60:
        y='RESEARCH_MORE'
    else:
        y='SHADOW_REPAIR'
    intel_rows.append((x,y))
intel_fit,intel_val,intel_revealed,intel_blind=split_rows(intel_rows)

def intel_baseline_acc(rows):
    return sum(k.intelligence_evolved_strategy(x)==y for x,y in rows)/max(1,len(rows))

intel_baseline=intel_baseline_acc(intel_blind)
intel_rc5=k.synthesize_intelligence_algorithm_component(intel_fit,intel_val,intel_revealed,intel_blind)
intel_rc6=k.synthesize_intelligence_with_extended_meta_grammar(intel_fit,intel_val,intel_revealed,intel_blind)

# Select by validation ONLY. Blind is reserved for final admission.
def candidate_validation(c):
    return float(c.get('validation',0.0)) if isinstance(c,dict) else 0.0

def select_by_validation(rc5,rc6):
    rows=[('RC5_ALGORITHM_GENESIS',rc5),('RC6_META_GRAMMAR',rc6)]
    # tie-breaker: RC6 only if it has strictly better validation; otherwise RC5
    rows.sort(key=lambda z:(candidate_validation(z[1]),z[0]=='RC5_ALGORITHM_GENESIS'),reverse=True)
    return rows[0],rows

selected_logic,logic_all=select_by_validation(logic_rc5,logic_rc6)
selected_thinking,thinking_all=select_by_validation(thinking_rc5,thinking_rc6)
selected_intel,intel_all=select_by_validation(intel_rc5,intel_rc6)

def fresh(c):
    return float(c.get('fresh_blind',0.0)) if isinstance(c,dict) else 0.0

def supported(c):
    if not isinstance(c,dict): return False
    return c.get('status','SUPPORTED') in ('SUPPORTED','SHADOW_SUPPORTED') and candidate_validation(c)>=0.90 and fresh(c)>=0.90

organ_rows={
 'LOGIC':{
    'baseline_fresh_blind':logic_baseline,
    'fit_count':len(logic_fit),'validation_count':len(logic_val),'blind_count':len(logic_blind),
    'rc5':logic_rc5,'rc6':logic_rc6,'selected_family':selected_logic[0],'selected':selected_logic[1],
 },
 'THINKING':{
    'baseline_fresh_blind':thinking_baseline,
    'fit_count':len(thinking_fit),'validation_count':len(thinking_val),'blind_count':len(thinking_blind),
    'rc5':thinking_rc5,'rc6':thinking_rc6,'selected_family':selected_thinking[0],'selected':selected_thinking[1],
 },
 'INTELLIGENCE':{
    'baseline_fresh_blind':intel_baseline,
    'fit_count':len(intel_fit),'validation_count':len(intel_val),'blind_count':len(intel_blind),
    'rc5':intel_rc5,'rc6':intel_rc6,'selected_family':selected_intel[0],'selected':selected_intel[1],
 },
}

for name,row in organ_rows.items():
    row['selected_validation']=candidate_validation(row['selected'])
    row['selected_fresh_blind']=fresh(row['selected'])
    row['fresh_gain_over_active_rc8']=row['selected_fresh_blind']-row['baseline_fresh_blind']
    row['admission_pass']=(
        supported(row['selected']) and
        row['selected_fresh_blind'] > row['baseline_fresh_blind'] and
        row['blind_count']>=6
    )

bundle_pass=all(v['admission_pass'] for v in organ_rows.values())
component_bundle={
    'schema':'yado.rc8.shadow.cognitive_component_bundle.v2',
    'parent_state_sha256':hashlib.sha256((PKG/'yado_canonical_state_v3_rc8_external_cognitive.json').read_bytes()).hexdigest(),
    'components':{
        organ:{
            'origin':row['selected_family'],
            'model':row['selected'].get('model'),
            'validation':row['selected_validation'],
            'fresh_blind':row['selected_fresh_blind'],
            'baseline_fresh_blind':row['baseline_fresh_blind'],
        } for organ,row in organ_rows.items()
    },
    'admission_pass':bundle_pass,
    'mutation_applied':False,
}
component_bundle['bundle_sha256']=hashlib.sha256(json.dumps(component_bundle,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
(OUT_DIR/'component_bundle.json').write_text(json.dumps(component_bundle,indent=2,sort_keys=True,default=str)+'\n')

receipt={
    'schema':'yado.rc8.shadow.algorithm_genesis_uplift.v2',
    'status':'PASS_SHADOW_COGNITIVE_COMPONENT_BUNDLE' if bundle_pass else 'WITHHOLD',
    'github_run_id':os.getenv('GITHUB_RUN_ID'),
    'github_sha':os.getenv('GITHUB_SHA'),
    'working_parent':'VERIFIED_V36_RC8_UNCHANGED',
    'kernel_class':'UnifiedYADOKernelV30RC8ExternalCognitive',
    'kernel_native_generators':['RC5_ALGORITHM_GENESIS','RC6_META_GRAMMAR'],
    'host_role':'benchmark_transport_partition_and_observation_only',
    'selection_rule':'VALIDATION_ONLY_BLIND_RESERVED_FOR_ADMISSION',
    'organ_results':organ_rows,
    'bundle':component_bundle,
    'canonical_mutation':False,
    'promotion_applied':False,
    'lineage_observation':'CURRENT_RC8_INPLACE_ORGAN_REGISTRY_COMMIT_CONFLICTS_WITH_RC8_PRESERVED_PAYLOAD_GUARD',
    'next_required_capability':(
        'SAFE_RC8_SUCCESSOR_LINEAGE_BUILDER_V1'
        if bundle_pass else
        'CONTINUE_KERNEL_NATIVE_ALGORITHM_GENESIS_BEFORE_SUCCESSOR'
    ),
    'semantic_boundary':'BOUNDED_COMPONENT_GENESIS_NOT_GENERAL_INTELLIGENCE_NOT_SUBJECTIVE_CONSCIOUSNESS',
}
receipt['receipt_sha256']=hashlib.sha256(json.dumps(receipt,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
(ROOT/'yado_rc8_algorithm_genesis_uplift_v2_receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps(receipt,indent=2,sort_keys=True,default=str))
k.close()
