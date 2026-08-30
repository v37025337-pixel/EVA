from __future__ import annotations
from pathlib import Path
import hashlib,itertools,json,os,random,sys

ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(PKG))

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_algorithm_component_runtime_native_v1 import predict_intel_component,_thinking_predict

OUT=ROOT/'composed_sequence_transform_v1'
OUT.mkdir(exist_ok=True)
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(OUT/'composition.sqlite'))

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
role_flags={r:'role_'+str(i) for i,r in enumerate(ALL)}

def ctxs():
    out=[]
    for vals in itertools.product([False,True],repeat=5):
        out.append(dict(zip([
          'lineage_verified','dependency_lock_verified','evidence_fetch_hardened',
          'historical_state_protected','current_generation_active'
        ],vals)))
    return out

def expected(ctx):
    out=[]
    if ctx['current_generation_active']:
        out.extend(GEN)
    resolved=set()
    if ctx['lineage_verified']: resolved.add('UNIFY_BOOT_AND_STATE_LINEAGE')
    if ctx['dependency_lock_verified']: resolved.add('ADD_PREIMPORT_DEPENDENCY_LOCK')
    if ctx['evidence_fetch_hardened']: resolved.add('HARDEN_DIRECT_EVIDENCE_FETCH')
    if ctx['historical_state_protected']: resolved.add('PROTECT_HISTORICAL_STATE_FROM_MUTATION')
    out.extend([r for r in CAN if r not in resolved])
    return out

def keep_target(ctx,role):
    return 'KEEP' if role in expected(ctx) else 'DROP'

def features(ctx,role,nuisance=0.0):
    x={k:float(bool(v)) for k,v in ctx.items()}
    for r,f in role_flags.items():
        x[f]=1.0 if r==role else 0.0
    x['nuisance']=float(nuisance)
    return x

# FILTER component: all semantic context x role combinations, different nuisance slices.
filter_fit=[];filter_val=[];filter_blind=[]
for ci,ctx in enumerate(ctxs()):
    for ri,role in enumerate(ALL):
        y=keep_target(ctx,role)
        filter_fit.append((features(ctx,role,0.0),y))
        filter_val.append((features(ctx,role,0.5),y))
        xb=features(ctx,role,1.0);xb['fresh_nonce']=float((ci*13+ri*7)%17)
        filter_blind.append((xb,y))

f5=k.synthesize_intelligence_algorithm_component(filter_fit,filter_val,filter_fit+filter_val,filter_blind)
f6=k.synthesize_intelligence_with_extended_meta_grammar(filter_fit,filter_val,filter_fit+filter_val,filter_blind)

def sc(c,key): return float(c.get(key,0.0)) if isinstance(c,dict) else 0.0
if sc(f6,'validation')>sc(f5,'validation'):
    filter_origin='RC6_META_GRAMMAR'; filter_sel=f6
else:
    filter_origin='RC5_ALGORITHM_GENESIS'; filter_sel=f5

# ORDER component: learn one global developmental precedence; fresh tests shuffle presentation.
def actions(tag,seed=None):
    xs=[{'id':f'{tag}-{i}','role':r} for i,r in enumerate(ALL)]
    if seed is not None: random.Random(seed).shuffle(xs)
    return xs

order_fit=[({'mode':0.0},actions(f'OF{i}',None),ALL) for i in range(8)]
order_val=[({'mode':0.5},actions(f'OV{i}',5000+i),ALL) for i in range(8)]
order_blind=[({'mode':1.0,'fresh':i/32},actions(f'OB{i}',15000+i),ALL) for i in range(32)]

o5=k.synthesize_thinking_algorithm_component(order_fit,order_val,order_fit,order_blind)
o6=k.synthesize_thinking_with_extended_meta_grammar(order_fit,order_val,order_fit,order_blind)
if sc(o6,'validation')>sc(o5,'validation'):
    order_origin='RC6_META_GRAMMAR'; order_sel=o6
else:
    order_origin='RC5_ALGORITHM_GENESIS'; order_sel=o5

def filter_actions(ctx,acts):
    kept=[]
    for a in acts:
        x=features(ctx,a['role'],1.0);x['fresh_nonce']=0.37
        if predict_intel_component(filter_sel['model'],x)=='KEEP':
            kept.append(a)
    return kept

def ordered_roles(ctx,acts,apply_filter=True,apply_order=True):
    xs=filter_actions(ctx,acts) if apply_filter else list(acts)
    if apply_order:
        pred,_=_thinking_predict(order_sel['model'],({'mode':1.0,'fresh':0.99},xs,[]))
        return pred
    return [a['role'] for a in xs]

rows=[]
full=filter_ab=order_ab=both_ab=0
contexts=ctxs()
for i,ctx in enumerate(contexts):
    acts=actions(f'C{i}',25000+i)
    exp=expected(ctx)
    p=ordered_roles(ctx,acts,True,True)
    p_fa=ordered_roles(ctx,acts,False,True)
    p_oa=ordered_roles(ctx,acts,True,False)
    p_ba=ordered_roles(ctx,acts,False,False)
    full += p==exp
    filter_ab += p_fa==exp
    order_ab += p_oa==exp
    both_ab += p_ba==exp
    rows.append({
      'context':ctx,'expected':exp,'predicted':p,
      'pass':p==exp,
      'filter_ablation_pass':p_fa==exp,
      'order_ablation_pass':p_oa==exp,
    })

n=len(rows)
full/=n;filter_ab/=n;order_ab/=n;both_ab/=n

current_ctx={
 'lineage_verified':True,'dependency_lock_verified':False,
 'evidence_fetch_hardened':False,'historical_state_protected':False,
 'current_generation_active':True,
}
current=ordered_roles(current_ctx,actions('LIVE',99199),True,True)
current_expected=expected(current_ctx)

admission=(
    sc(filter_sel,'validation')>=0.99
    and sc(order_sel,'validation')>=0.99
    and full>=0.99
    and full>filter_ab
    and full>order_ab
    and current==current_expected
)

component={
 'schema':'yado.composed_sequence_transform.component.v1',
 'architecture':'INTELLIGENCE_FILTER_THEN_THINKING_ORDER',
 'filter_origin':filter_origin,
 'filter_model':filter_sel['model'],
 'order_origin':order_origin,
 'order_model':order_sel['model'],
 'validation':{
    'filter':sc(filter_sel,'validation'),
    'order':sc(order_sel,'validation'),
 },
 'fresh_exact':full,
 'filter_ablation_exact':filter_ab,
 'order_ablation_exact':order_ab,
 'both_ablation_exact':both_ab,
}
component['component_digest']=hashlib.sha256(json.dumps(component,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
(OUT/'component.json').write_text(json.dumps(component,indent=2,sort_keys=True,default=str)+'\n')

report={
 'schema':'yado.composed_sequence_transform.receipt.v1',
 'status':'PASS_COMPOSED_SEQUENCE_TRANSFORM_V1' if admission else 'WITHHOLD_COMPOSED_SEQUENCE_TRANSFORM',
 'github_run_id':os.getenv('GITHUB_RUN_ID'),
 'github_sha':os.getenv('GITHUB_SHA'),
 'composition':'INTELLIGENCE_FILTER -> THINKING_ORDER',
 'filter_origin':filter_origin,
 'order_origin':order_origin,
 'filter_validation':sc(filter_sel,'validation'),
 'filter_native_fresh':sc(filter_sel,'fresh_blind'),
 'order_validation':sc(order_sel,'validation'),
 'order_native_fresh':sc(order_sel,'fresh_blind'),
 'fresh_exact':full,
 'filter_ablation_exact':filter_ab,
 'order_ablation_exact':order_ab,
 'both_ablation_exact':both_ab,
 'fresh_case_count':n,
 'current_effective_priority':current,
 'current_expected_priority':current_expected,
 'current_pass':current==current_expected,
 'component':component,
 'canonical_mutation':False,
 'promotion_applied':False,
 'host_role':'BOUNDED_NATIVE_COMPONENT_COMPOSITION_AND_EVALUATION',
 'next_required_capability':'META_COMPOSITION_SELECTION_V1' if admission else 'EXPAND_SEQUENCE_TRANSFORMATION_GRAMMAR',
 'semantic_boundary':'COMPOSITION USES YADO-NATIVE GENERATED FILTER AND ORDER COMPONENTS; COMPOSITION HARNESS IS HOST-SCAFFOLDED',
}
report['receipt_sha256']=hashlib.sha256(json.dumps(report,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
(ROOT/'yado_composed_sequence_transform_v1_receipt.json').write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps({
 'status':report['status'],
 'filter_origin':filter_origin,'filter_validation':report['filter_validation'],
 'order_origin':order_origin,'order_validation':report['order_validation'],
 'fresh_exact':full,
 'filter_ablation_exact':filter_ab,
 'order_ablation_exact':order_ab,
 'current_pass':report['current_pass'],
 'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True))
k.close()
