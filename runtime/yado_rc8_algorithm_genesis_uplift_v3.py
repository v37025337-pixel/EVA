from __future__ import annotations
from pathlib import Path
import hashlib, itertools, json, os, random, sys

ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(PKG))

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive

OUT=ROOT/'rc8_cognitive_genesis_bundle_v3'
OUT.mkdir(exist_ok=True)
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(OUT/'genesis.sqlite'))

def acc_logic_baseline(rows):
    return sum(bool(k.logic_evolved_decision(x))==bool(y) for x,y in rows)/max(1,len(rows))

def acc_intel_baseline(rows):
    return sum(k.intelligence_evolved_strategy(x)==y for x,y in rows)/max(1,len(rows))

def acc_thinking_baseline(rows):
    ok=0
    for ctx,actions,expected in rows:
        ids=k.thinking_evolved_plan(actions)
        by={str(a['id']):str(a['role']) for a in actions}
        pred=[by[str(i)] for i in ids]
        ok += pred==expected
    return ok/max(1,len(rows))

# LOGIC
# Complete semantic truth table is present in fit; nuisance coordinates create
# validation/blind contexts without changing the law.
def logic_law(x):
    return bool(x['rollback_ready'] and x['fresh_verified'] and x['integrity_ok'])

logic_fit=[]; logic_val=[]; logic_blind=[]
for core in itertools.product([False,True],repeat=3):
    base=dict(zip(['rollback_ready','fresh_verified','integrity_ok'],core))
    for source_external,novel_domain in itertools.product([False,True],repeat=2):
        x=dict(base,source_external=source_external,novel_domain=novel_domain)
        row=(x,logic_law(x))
        if not source_external and not novel_domain: logic_fit.append(row)
        elif not source_external and novel_domain: logic_val.append(row)
        elif source_external and not novel_domain: logic_blind.append(row)
logic_revealed=logic_fit

logic_base=acc_logic_baseline(logic_blind)
logic_rc5=k.synthesize_logic_algorithm_component(logic_fit,logic_val,logic_revealed,logic_blind)
logic_rc6=k.synthesize_logic_with_extended_meta_grammar(logic_fit,logic_val,logic_revealed,logic_blind)

# THINKING
roles=['OBSERVE','RESEARCH','DIAGNOSE','HYPOTHESIZE','SIMULATE','TEST','ROLLBACK','VERIFY','COMMIT']
safe=['OBSERVE','RESEARCH','HYPOTHESIZE','SIMULATE','DIAGNOSE','TEST','VERIFY','ROLLBACK','COMMIT']
risk=['OBSERVE','DIAGNOSE','ROLLBACK','RESEARCH','HYPOTHESIZE','SIMULATE','TEST','VERIFY','COMMIT']

def risk_mode(ctx):
    return (ctx['integrity_risk'] + ctx['uncertainty']) > 1.0

def actions_for(order,tag,shuffle_seed=None):
    actions=[{'id':f'{tag}-{i}','role':r} for i,r in enumerate(order)]
    if shuffle_seed is not None:
        random.Random(shuffle_seed).shuffle(actions)
    return actions

thinking_fit=[]; thinking_val=[]; thinking_blind=[]
idx=0
levels=[0.0,0.2,0.4,0.6,0.8,1.0]
for a in levels:
  for b in levels:
    ctx={'integrity_risk':a,'uncertainty':b,'novelty':((idx*7)%11)/10}
    expected=risk if risk_mode(ctx) else safe
    # FIT = successful traces in their demonstrated successful order.
    thinking_fit.append((ctx,actions_for(expected,f'F{idx}'),expected))
    # Validation/blind = same causal law, shuffled action presentations.
    vctx=dict(ctx,novelty=((idx*5+3)%13)/12)
    bctx=dict(ctx,novelty=((idx*9+1)%17)/16)
    thinking_val.append((vctx,actions_for(expected,f'V{idx}',1000+idx),expected))
    thinking_blind.append((bctx,actions_for(expected,f'B{idx}',9000+idx),expected))
    idx+=1
thinking_revealed=thinking_fit

thinking_base=acc_thinking_baseline(thinking_blind)
thinking_rc5=k.synthesize_thinking_algorithm_component(thinking_fit,thinking_val,thinking_revealed,thinking_blind)
thinking_rc6=k.synthesize_thinking_with_extended_meta_grammar(thinking_fit,thinking_val,thinking_revealed,thinking_blind)

# INTELLIGENCE
levels_i={
 'integrity_score':[0.2,0.9],
 'rollback_score':[0.2,0.9],
 'fresh_blind':[0.55,0.78,0.93,0.99],
 'ablation_drop':[0.05,0.27],
 'transfer_score':[0.45,0.86],
 'evidence_coverage':[0.42,0.78],
}
intel_rows=[]
for vals in itertools.product(*levels_i.values()):
    x=dict(zip(levels_i,vals))
    if x['integrity_score']<0.5 or x['rollback_score']<0.5:y='ROLLBACK'
    elif x['fresh_blind']>=.90 and x['ablation_drop']>=.20 and x['transfer_score']>=.80:y='PROMOTE_CANDIDATE'
    elif x['evidence_coverage']<.60:y='RESEARCH_MORE'
    else:y='SHADOW_REPAIR'
    b=int(hashlib.sha256(json.dumps(x,sort_keys=True).encode()).hexdigest()[:8],16)%100
    intel_rows.append((b,x,y))
intel_blind=[(x,y) for b,x,y in intel_rows if b<22]
intel_val=[(x,y) for b,x,y in intel_rows if 22<=b<45]
intel_fit=[(x,y) for b,x,y in intel_rows if b>=45]
intel_revealed=intel_fit+intel_val

intel_base=acc_intel_baseline(intel_blind)
intel_rc5=k.synthesize_intelligence_algorithm_component(intel_fit,intel_val,intel_revealed,intel_blind)
intel_rc6=k.synthesize_intelligence_with_extended_meta_grammar(intel_fit,intel_val,intel_revealed,intel_blind)

def score(c,key):
    return float(c.get(key,0.0)) if isinstance(c,dict) else 0.0

def choose(rc5,rc6):
    # selection uses validation only; blind cannot influence winner
    if score(rc6,'validation')>score(rc5,'validation'): return 'RC6_META_GRAMMAR',rc6
    return 'RC5_ALGORITHM_GENESIS',rc5

organs={}
for name,baseline,fit,val,blind,rc5,rc6 in [
    ('LOGIC',logic_base,logic_fit,logic_val,logic_blind,logic_rc5,logic_rc6),
    ('THINKING',thinking_base,thinking_fit,thinking_val,thinking_blind,thinking_rc5,thinking_rc6),
    ('INTELLIGENCE',intel_base,intel_fit,intel_val,intel_blind,intel_rc5,intel_rc6),
]:
    family,sel=choose(rc5,rc6)
    status=sel.get('status','SUPPORTED') if isinstance(sel,dict) else 'WITHHOLD'
    organs[name]={
       'baseline_fresh_blind':baseline,
       'fit_count':len(fit),'validation_count':len(val),'blind_count':len(blind),
       'rc5':rc5,'rc6':rc6,
       'selected_family':family,'selected':sel,
       'selected_validation':score(sel,'validation'),
       'selected_fresh_blind':score(sel,'fresh_blind'),
    }
    organs[name]['fresh_gain_over_active_rc8']=organs[name]['selected_fresh_blind']-baseline
    organs[name]['admission_pass']=(
       status in ('SUPPORTED','SHADOW_SUPPORTED')
       and organs[name]['selected_validation']>=.90
       and organs[name]['selected_fresh_blind']>=.90
       and organs[name]['selected_fresh_blind']>baseline
       and len(blind)>=8
    )

bundle_pass=all(x['admission_pass'] for x in organs.values())
parent_sha=hashlib.sha256((PKG/'yado_canonical_state_v3_rc8_external_cognitive.json').read_bytes()).hexdigest()
bundle={
 'schema':'yado.rc8.shadow.cognitive_component_bundle.v3',
 'parent_state_sha256':parent_sha,
 'components':{
   n:{
      'origin':r['selected_family'],
      'model':r['selected'].get('model'),
      'validation':r['selected_validation'],
      'fresh_blind':r['selected_fresh_blind'],
      'baseline_fresh_blind':r['baseline_fresh_blind'],
   } for n,r in organs.items()
 },
 'admission_pass':bundle_pass,
 'mutation_applied':False,
}
bundle['bundle_sha256']=hashlib.sha256(json.dumps(bundle,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
(OUT/'component_bundle.json').write_text(json.dumps(bundle,indent=2,sort_keys=True,default=str)+'\n')

receipt={
 'schema':'yado.rc8.shadow.algorithm_genesis_uplift.v3',
 'status':'PASS_SHADOW_COGNITIVE_COMPONENT_BUNDLE' if bundle_pass else 'WITHHOLD',
 'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),
 'working_parent':'VERIFIED_V36_RC8_UNCHANGED',
 'kernel_native_generators':['RC5_ALGORITHM_GENESIS','RC6_META_GRAMMAR'],
 'host_role':'benchmark_transport_and_observation_only',
 'selection_rule':'VALIDATION_ONLY_BLIND_RESERVED_FOR_FINAL_ADMISSION',
 'organ_results':organs,
 'bundle':bundle,
 'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'SAFE_RC8_SUCCESSOR_LINEAGE_BUILDER_V1' if bundle_pass else 'CONTINUE_KERNEL_NATIVE_GENESIS',
 'semantic_boundary':'BOUNDED_ORGAN_COMPONENT_GENESIS_NOT_GENERAL_INTELLIGENCE_OR_SUBJECTIVE_CONSCIOUSNESS',
}
receipt['receipt_sha256']=hashlib.sha256(json.dumps(receipt,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
(ROOT/'yado_rc8_algorithm_genesis_uplift_v3_receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps(receipt,indent=2,sort_keys=True,default=str))
k.close()
