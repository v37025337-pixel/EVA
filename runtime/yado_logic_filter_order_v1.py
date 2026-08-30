from __future__ import annotations
from pathlib import Path
import hashlib,itertools,json,os,random,sys,time

ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(PKG))

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_evolution_runtime_native_v1 import acc_logic_model,_predict_plan_model

OUT=ROOT/'logic_filter_order_v1'
OUT.mkdir(exist_ok=True)
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(OUT/'logic-order.sqlite'))

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
ALWAYS=set(CAN[4:])

def contexts():
    return [dict(zip(
      ['lineage_verified','dependency_lock_verified','evidence_fetch_hardened',
       'historical_state_protected','current_generation_active'],vals
    )) for vals in itertools.product([False,True],repeat=5)]

def expected(ctx):
    out=[]
    if ctx['current_generation_active']:out.extend(GEN)
    if not ctx['lineage_verified']:out.append(CAN[0])
    if not ctx['dependency_lock_verified']:out.append(CAN[1])
    if not ctx['evidence_fetch_hardened']:out.append(CAN[2])
    if not ctx['historical_state_protected']:out.append(CAN[3])
    out.extend(CAN[4:])
    return out

def bool_features(ctx,role,nuisance=False):
    return {
      'lineage_verified':bool(ctx['lineage_verified']),
      'dependency_lock_verified':bool(ctx['dependency_lock_verified']),
      'evidence_fetch_hardened':bool(ctx['evidence_fetch_hardened']),
      'historical_state_protected':bool(ctx['historical_state_protected']),
      'current_generation_active':bool(ctx['current_generation_active']),
      'is_generation':role in GEN,
      'is_unify_lineage':role==CAN[0],
      'is_dependency_lock':role==CAN[1],
      'is_evidence_fetch':role==CAN[2],
      'is_historical_protection':role==CAN[3],
      'is_always_active':role in ALWAYS,
      'nuisance':bool(nuisance),
    }

def target(ctx,role): return role in expected(ctx)

fit=[];val=[];blind=[]
for ctx in contexts():
    for role in ALL:
        y=target(ctx,role)
        fit.append((bool_features(ctx,role,False),y))
        val.append((bool_features(ctx,role,True),y))
        xb=bool_features(ctx,role,False);xb['fresh_noise']=not bool((len(role)+sum(ctx.values()))%2)
        blind.append((xb,y))

t0=time.perf_counter()
logic_meta=k.meta_evolve_logic(fit,val,fit+val,blind)
logic_seconds=time.perf_counter()-t0
logic_family=logic_meta['selected_algorithm']['family']

def logic_predict(x):
    # acc_logic_model exposes the native evaluator for both ENUM_BOOLEAN and BOOL_DECISION_TREE.
    if acc_logic_model(logic_family,logic_meta['model'],[(x,True)])==1.0:
        return True
    if acc_logic_model(logic_family,logic_meta['model'],[(x,False)])==1.0:
        return False
    raise RuntimeError('LOGIC_SINGLE_PREDICTION_UNRESOLVED')

# ORDER via bounded meta thinking.
fit_traces=[list(ALL) for _ in range(8)]
def actions(tag,seed):
    xs=[{'id':f'{tag}-{i}','role':r} for i,r in enumerate(ALL)]
    random.Random(seed).shuffle(xs);return xs
validation=[({'phase':'validation'},actions(f'V{i}',5000+i),ALL) for i in range(16)]
blind_order=[({'phase':'blind'},actions(f'B{i}',15000+i),ALL) for i in range(32)]
t1=time.perf_counter()
order_meta=k.meta_evolve_thinking(fit_traces,validation,fit_traces,blind_order)
order_seconds=time.perf_counter()-t1

def filtered(ctx,acts,apply_filter=True):
    if not apply_filter:return list(acts)
    return [a for a in acts if logic_predict(bool_features(ctx,a['role'],False))]

def compose(ctx,acts,apply_filter=True,apply_order=True):
    xs=filtered(ctx,acts,apply_filter)
    if not apply_order:return [a['role'] for a in xs]
    pred,_=_predict_plan_model(order_meta['model'],(ctx,xs,expected(ctx)))
    return pred

full=fa=oa=ba=0;rows=[]
for i,ctx in enumerate(contexts()):
    acts=actions(f'C{i}',25000+i);exp=expected(ctx)
    p=compose(ctx,acts,True,True)
    pfa=compose(ctx,acts,False,True)
    poa=compose(ctx,acts,True,False)
    pba=compose(ctx,acts,False,False)
    full+=p==exp;fa+=pfa==exp;oa+=poa==exp;ba+=pba==exp
    rows.append({'context':ctx,'expected':exp,'predicted':p,'pass':p==exp})
n=len(rows);full/=n;fa/=n;oa/=n;ba/=n

current_ctx={
 'lineage_verified':True,'dependency_lock_verified':False,
 'evidence_fetch_hardened':False,'historical_state_protected':False,
 'current_generation_active':True,
}
current=compose(current_ctx,actions('LIVE',99199),True,True)
current_expected=expected(current_ctx)

admission=(
    float(logic_meta['validation'])>=0.99
    and float(logic_meta['fresh_blind'])>=0.99
    and float(order_meta['validation'])>=0.99
    and float(order_meta['fresh_blind'])>=0.99
    and full>=0.99
    and full>fa and full>oa
    and current==current_expected
)

component={
 'schema':'yado.logic_filter_order.component.v1',
 'composition':'META_LOGIC_FILTER -> META_THINKING_ORDER',
 'logic_selected_algorithm':logic_meta['selected_algorithm'],
 'logic_model':logic_meta['model'],
 'order_selected_algorithm':order_meta['selected_algorithm'],
 'order_model':order_meta['model'],
 'logic_seconds':logic_seconds,'order_seconds':order_seconds,
 'fresh_exact':full,
}
component['component_digest']=hashlib.sha256(json.dumps(component,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
(OUT/'component.json').write_text(json.dumps(component,indent=2,sort_keys=True,default=str)+'\n')

report={
 'schema':'yado.logic_filter_order.receipt.v1',
 'status':'PASS_LOGIC_FILTER_ORDER_V1' if admission else 'WITHHOLD_LOGIC_FILTER_ORDER',
 'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),
 'logic_meta':{
    'selected_algorithm':logic_meta['selected_algorithm'],
    'validation':logic_meta['validation'],'fresh_blind':logic_meta['fresh_blind'],
    'seconds':logic_seconds,'fit_count':len(fit),'validation_count':len(val),'blind_count':len(blind),
 },
 'order_meta':{
    'selected_algorithm':order_meta['selected_algorithm'],
    'validation':order_meta['validation'],'fresh_blind':order_meta['fresh_blind'],
    'seconds':order_seconds,
 },
 'composition_fresh_exact':full,
 'filter_ablation_exact':fa,'order_ablation_exact':oa,'both_ablation_exact':ba,
 'current_effective_priority':current,'current_expected_priority':current_expected,
 'current_pass':current==current_expected,
 'component':component,
 'canonical_mutation':False,'promotion_applied':False,
 'host_role':'BOUNDED_COMPOSITION_HARNESS; FILTER/ORDER ALGORITHM SELECTION AND FITTING ARE NATIVE YADO META-AUTOEVOLUTION',
 'next_required_capability':'META_COMPOSITION_SELECTION_V1' if admission else 'EXPAND_LOGIC_OR_SEQUENCE_TRANSFORMATION_GRAMMAR',
 'semantic_boundary':'LOGIC_FILTER_PLUS_THINKING_ORDER FOR BOUNDED PRIORITY TRANSFORMATION; NOT CANONICAL PROMOTION',
}
report['receipt_sha256']=hashlib.sha256(json.dumps(report,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
(ROOT/'yado_logic_filter_order_v1_receipt.json').write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps({
 'status':report['status'],
 'logic_algorithm':logic_meta['selected_algorithm'],
 'logic_validation':logic_meta['validation'],'logic_fresh':logic_meta['fresh_blind'],'logic_seconds':logic_seconds,
 'order_algorithm':order_meta['selected_algorithm'],
 'order_validation':order_meta['validation'],'order_fresh':order_meta['fresh_blind'],'order_seconds':order_seconds,
 'composition_fresh_exact':full,'filter_ablation_exact':fa,'order_ablation_exact':oa,
 'current_pass':report['current_pass'],'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True,default=str))
k.close()
