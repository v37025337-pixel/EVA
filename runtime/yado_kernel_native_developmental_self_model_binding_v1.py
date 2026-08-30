from __future__ import annotations
from pathlib import Path
import hashlib,itertools,json,os,random,statistics,sys

ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(PKG))

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_algorithm_component_runtime_native_v1 import _thinking_predict

OUT=ROOT/'kernel_native_developmental_self_model_binding_v1'
OUT.mkdir(exist_ok=True)
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(OUT/'native-binder.sqlite'))

GEN=[
 'THINKING_BOUNDARY_REASONING',
 'INTELLIGENCE_BOUNDARY_REASONING',
 'REPRESENTATION_INVARIANCE',
]
CAN=[
 'UNIFY_BOOT_AND_STATE_LINEAGE',
 'ADD_PREIMPORT_DEPENDENCY_LOCK',
 'HARDEN_DIRECT_EVIDENCE_FETCH',
 'PROTECT_HISTORICAL_STATE_FROM_MUTATION',
 'CONSOLIDATE_VALIDATED_FRONTIER_PORTFOLIO_INSTANCE_LOCALLY',
 'DURABILIZE_HOST_CAPABILITY_MODEL',
 'STRUCTURAL_FRONTIER_ROUTER',
]
ALL=GEN+CAN

flag_to_resolved={
 'lineage_verified':'UNIFY_BOOT_AND_STATE_LINEAGE',
 'dependency_lock_verified':'ADD_PREIMPORT_DEPENDENCY_LOCK',
 'evidence_fetch_hardened':'HARDEN_DIRECT_EVIDENCE_FETCH',
 'historical_state_protected':'PROTECT_HISTORICAL_STATE_FROM_MUTATION',
}

def expected(ctx):
    out=[]
    if ctx['current_generation_active']:
        out.extend(GEN)
    resolved={v for f,v in flag_to_resolved.items() if ctx[f]}
    out.extend([x for x in CAN if x not in resolved])
    return out

def action_rows(tag,seed=None):
    xs=[{'id':f'{tag}-{i}','role':r} for i,r in enumerate(ALL)]
    if seed is not None:
        random.Random(seed).shuffle(xs)
    return xs

contexts=[]
for vals in itertools.product([False,True],repeat=5):
    ctx=dict(zip([
      'lineage_verified','dependency_lock_verified','evidence_fetch_hardened',
      'historical_state_protected','current_generation_active'
    ],vals))
    contexts.append(ctx)

fit=[];val=[];blind=[]
for i,ctx in enumerate(contexts):
    exp=expected(ctx)
    # successful traces in fit are already in the correct resulting order/subset
    fit.append((dict(ctx,nuisance=0.0),action_rows(f'F{i}',None),exp))
    val.append((dict(ctx,nuisance=0.5),action_rows(f'V{i}',7000+i),exp))
    blind.append((dict(ctx,nuisance=1.0,fresh_nonce=(i*7)%11),action_rows(f'B{i}',17000+i),exp))

rc5=k.synthesize_thinking_algorithm_component(fit,val,fit,blind)
rc6=k.synthesize_thinking_with_extended_meta_grammar(fit,val,fit,blind)

def sc(c,key): return float(c.get(key,0.0)) if isinstance(c,dict) else 0.0
if sc(rc6,'validation')>sc(rc5,'validation'):
    origin='RC6_META_GRAMMAR'; selected=rc6
else:
    origin='RC5_ALGORITHM_GENESIS'; selected=rc5

def exact(model,cases):
    ok=0; rows=[]
    for ctx,actions,exp in cases:
        pred,_=_thinking_predict(model,(ctx,actions,exp))
        same=pred==exp
        ok+=same
        rows.append({'context':ctx,'expected':exp,'predicted':pred,'pass':same})
    return ok/len(cases),rows

fresh_exact,rows=exact(selected['model'],blind)

# Baseline: immutable canonical list, independent of evidence/current generation.
baseline=0
for ctx,actions,exp in blind:
    baseline += CAN==exp
baseline/=len(blind)

current_ctx={
 'lineage_verified':True,
 'dependency_lock_verified':False,
 'evidence_fetch_hardened':False,
 'historical_state_protected':False,
 'current_generation_active':True,
 'nuisance':1.0,
 'fresh_nonce':999,
}
current_actions=action_rows('LIVE',99199)
current_pred,current_exp=_thinking_predict(selected['model'],(current_ctx,current_actions,expected(current_ctx)))
current_pass=current_pred==expected(current_ctx)

admission=(
    sc(selected,'validation')==1.0
    and fresh_exact==1.0
    and fresh_exact>baseline
    and current_pass
)

component={
 'schema':'yado.kernel_native_developmental_self_model_binding.component.v1',
 'origin':origin,
 'model':selected['model'],
 'validation':sc(selected,'validation'),
 'fresh_blind':fresh_exact,
 'baseline_exact':baseline,
 'current_effective_priority':current_pred,
}
component['component_digest']=hashlib.sha256(json.dumps(component,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
(OUT/'component.json').write_text(json.dumps(component,indent=2,sort_keys=True,default=str)+'\n')

report={
 'schema':'yado.kernel_native_developmental_self_model_binding.receipt.v1',
 'status':'PASS_KERNEL_NATIVE_DEVELOPMENTAL_SELF_MODEL_BINDING_V1' if admission else 'WITHHOLD_KERNEL_NATIVE_BINDER',
 'github_run_id':os.getenv('GITHUB_RUN_ID'),
 'github_sha':os.getenv('GITHUB_SHA'),
 'kernel_native_generators':['RC5_ALGORITHM_GENESIS','RC6_META_GRAMMAR'],
 'selected_origin':origin,
 'rc5_summary':{k:rc5.get(k) for k in ('status','validation','fresh_blind')},
 'rc6_summary':{k:rc6.get(k) for k in ('status','validation','fresh_blind')},
 'selected_validation':sc(selected,'validation'),
 'fresh_blind_exact':fresh_exact,
 'baseline_exact':baseline,
 'fresh_case_count':len(blind),
 'current_context':current_ctx,
 'current_effective_priority':current_pred,
 'current_expected_priority':expected(current_ctx),
 'current_pass':current_pass,
 'component':component,
 'canonical_mutation':False,
 'promotion_applied':False,
 'next_required_capability':'LIVE_G0_NATIVE_DEVELOPMENTAL_SELF_MODEL_OVERLAY_V1' if admission else 'EXPAND_SEQUENCE_TRANSFORMATION_GRAMMAR',
 'semantic_boundary':'NATIVE YADO THINKING COMPONENT FOR BOUNDED DEVELOPMENTAL PRIORITY ROUTING; NOT CANONICAL PROMOTION',
}
report['receipt_sha256']=hashlib.sha256(json.dumps(report,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
(ROOT/'yado_kernel_native_developmental_self_model_binding_v1_receipt.json').write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps({
 'status':report['status'],
 'selected_origin':origin,
 'selected_validation':report['selected_validation'],
 'fresh_blind_exact':fresh_exact,
 'baseline_exact':baseline,
 'current_effective_priority':current_pred,
 'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True))
k.close()
