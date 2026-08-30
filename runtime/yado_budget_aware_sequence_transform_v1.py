from __future__ import annotations
from pathlib import Path
import hashlib,itertools,json,os,random,sys,time

ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(PKG))

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_algorithm_component_runtime_native_v1 import predict_intel_component
from yado_evolution_runtime_native_v1 import _predict_plan_model

OUT=ROOT/'budget_aware_sequence_transform_v1'
OUT.mkdir(exist_ok=True)
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(OUT/'budget.sqlite'))

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
ROLE_INDEX={r:i for i,r in enumerate(ALL)}

def contexts():
    return [dict(zip(
      ['lineage_verified','dependency_lock_verified','evidence_fetch_hardened',
       'historical_state_protected','current_generation_active'],vals
    )) for vals in itertools.product([False,True],repeat=5)]

def expected(ctx):
    out=[]
    if ctx['current_generation_active']: out.extend(GEN)
    resolved=set()
    if ctx['lineage_verified']: resolved.add(CAN[0])
    if ctx['dependency_lock_verified']: resolved.add(CAN[1])
    if ctx['evidence_fetch_hardened']: resolved.add(CAN[2])
    if ctx['historical_state_protected']: resolved.add(CAN[3])
    out.extend([r for r in CAN if r not in resolved])
    return out

def keep(ctx,role): return 'KEEP' if role in expected(ctx) else 'DROP'

def feat(ctx,role,nuisance):
    return {
      'lineage_verified':float(ctx['lineage_verified']),
      'dependency_lock_verified':float(ctx['dependency_lock_verified']),
      'evidence_fetch_hardened':float(ctx['evidence_fetch_hardened']),
      'historical_state_protected':float(ctx['historical_state_protected']),
      'current_generation_active':float(ctx['current_generation_active']),
      'role_index':float(ROLE_INDEX[role]),
      'nuisance':float(nuisance),
    }

# ---------- FILTER via bounded RC4 MetaAutoEvolution ----------
fit=[];val=[];blind=[]
for ctx in contexts():
    for role in ALL:
        y=keep(ctx,role)
        fit.append((feat(ctx,role,0.0),y))
        val.append((feat(ctx,role,0.5),y))
        blind.append((feat(ctx,role,1.0),y))

t0=time.perf_counter()
filter_meta=k.meta_evolve_intelligence(fit,val,fit+val,blind)
filter_seconds=time.perf_counter()-t0
filter_leaf={
  'op':'LEAF',
  'algorithm':filter_meta['selected_algorithm'],
  'model':filter_meta['model'],
}

# ---------- ORDER via bounded RC4 MetaAutoEvolution ----------
fit_traces=[list(ALL) for _ in range(8)]

def action_set(tag,seed):
    xs=[{'id':f'{tag}-{i}','role':r} for i,r in enumerate(ALL)]
    random.Random(seed).shuffle(xs)
    return xs

validation=[]
blind_plan=[]
for i in range(16):
    validation.append(({'phase':'validation'},action_set(f'V{i}',5000+i),list(ALL)))
for i in range(32):
    blind_plan.append(({'phase':'blind'},action_set(f'B{i}',15000+i),list(ALL)))

t1=time.perf_counter()
order_meta=k.meta_evolve_thinking(fit_traces,validation,fit_traces,blind_plan)
order_seconds=time.perf_counter()-t1

def filter_actions(ctx,actions,apply_filter=True):
    if not apply_filter:return list(actions)
    out=[]
    for a in actions:
        if predict_intel_component(filter_leaf,feat(ctx,a['role'],1.0))=='KEEP':
            out.append(a)
    return out

def composed(ctx,actions,apply_filter=True,apply_order=True):
    xs=filter_actions(ctx,actions,apply_filter)
    if not apply_order:
        return [a['role'] for a in xs]
    pred,_=_predict_plan_model(order_meta['model'],(ctx,xs,expected(ctx)))
    return pred

rows=[]
full=fa=oa=ba=0
for i,ctx in enumerate(contexts()):
    acts=action_set(f'C{i}',25000+i)
    exp=expected(ctx)
    p=composed(ctx,acts,True,True)
    pfa=composed(ctx,acts,False,True)
    poa=composed(ctx,acts,True,False)
    pba=composed(ctx,acts,False,False)
    full+=p==exp;fa+=pfa==exp;oa+=poa==exp;ba+=pba==exp
    rows.append({
      'context':ctx,'expected':exp,'predicted':p,'pass':p==exp,
      'filter_ablation_pass':pfa==exp,'order_ablation_pass':poa==exp,
    })
n=len(rows)
full/=n;fa/=n;oa/=n;ba/=n

current_ctx={
 'lineage_verified':True,
 'dependency_lock_verified':False,
 'evidence_fetch_hardened':False,
 'historical_state_protected':False,
 'current_generation_active':True,
}
current=composed(current_ctx,action_set('LIVE',99199),True,True)
current_expected=expected(current_ctx)

admission=(
    float(filter_meta['validation'])>=0.99
    and float(filter_meta['fresh_blind'])>=0.99
    and float(order_meta['validation'])>=0.99
    and float(order_meta['fresh_blind'])>=0.99
    and full>=0.99
    and full>fa
    and full>oa
    and current==current_expected
)

component={
 'schema':'yado.budget_aware_sequence_transform.component.v1',
 'composition':'META_INTELLIGENCE_FILTER -> META_THINKING_ORDER',
 'filter_selected_algorithm':filter_meta['selected_algorithm'],
 'filter_model':filter_meta['model'],
 'order_selected_algorithm':order_meta['selected_algorithm'],
 'order_model':order_meta['model'],
 'filter_seconds':filter_seconds,
 'order_seconds':order_seconds,
 'fresh_exact':full,
}
component['component_digest']=hashlib.sha256(json.dumps(component,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
(OUT/'component.json').write_text(json.dumps(component,indent=2,sort_keys=True,default=str)+'\n')

report={
 'schema':'yado.budget_aware_sequence_transform.receipt.v1',
 'status':'PASS_BUDGET_AWARE_SEQUENCE_TRANSFORM_V1' if admission else 'WITHHOLD_BUDGET_AWARE_SEQUENCE_TRANSFORM',
 'github_run_id':os.getenv('GITHUB_RUN_ID'),
 'github_sha':os.getenv('GITHUB_SHA'),
 'filter_meta':{
    'selected_algorithm':filter_meta['selected_algorithm'],
    'validation':filter_meta['validation'],
    'fresh_blind':filter_meta['fresh_blind'],
    'seconds':filter_seconds,
    'fit_count':len(fit),'validation_count':len(val),'blind_count':len(blind),
 },
 'order_meta':{
    'selected_algorithm':order_meta['selected_algorithm'],
    'validation':order_meta['validation'],
    'fresh_blind':order_meta['fresh_blind'],
    'seconds':order_seconds,
    'fit_trace_count':len(fit_traces),'validation_count':len(validation),'blind_count':len(blind_plan),
 },
 'composition_fresh_exact':full,
 'filter_ablation_exact':fa,
 'order_ablation_exact':oa,
 'both_ablation_exact':ba,
 'current_effective_priority':current,
 'current_expected_priority':current_expected,
 'current_pass':current==current_expected,
 'component':component,
 'canonical_mutation':False,
 'promotion_applied':False,
 'host_role':'BOUNDED_COMPOSITION_HARNESS; ALGORITHM_SELECTION_AND_FITTING_ARE_NATIVE_YADO_METAAUTOEVOLUTION',
 'next_required_capability':'META_COMPOSITION_SELECTION_V1' if admission else 'EXPAND_SEQUENCE_TRANSFORMATION_GRAMMAR',
 'semantic_boundary':'BUDGETED NATIVE META-EVOLUTION COMPONENTS; NOT CANONICAL PROMOTION',
}
report['receipt_sha256']=hashlib.sha256(json.dumps(report,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
(ROOT/'yado_budget_aware_sequence_transform_v1_receipt.json').write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps({
 'status':report['status'],
 'filter_algorithm':filter_meta['selected_algorithm'],
 'filter_validation':filter_meta['validation'],'filter_fresh':filter_meta['fresh_blind'],'filter_seconds':filter_seconds,
 'order_algorithm':order_meta['selected_algorithm'],
 'order_validation':order_meta['validation'],'order_fresh':order_meta['fresh_blind'],'order_seconds':order_seconds,
 'composition_fresh_exact':full,
 'filter_ablation_exact':fa,'order_ablation_exact':oa,
 'current_pass':report['current_pass'],
 'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True,default=str))
k.close()
