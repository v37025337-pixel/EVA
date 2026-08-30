from __future__ import annotations
from pathlib import Path
import hashlib,itertools,json,os,random,sys,time

ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(PKG))

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_evolution_runtime_native_v1 import tree_acc,_predict_plan_model

OUT=ROOT/'staged_filter_representation_tournament_v1'
OUT.mkdir(exist_ok=True)
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(OUT/'tournament.sqlite'))

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
ALWAYS=set(CAN[4:])

def all_contexts():
    out=[]
    for vals in itertools.product([False,True],repeat=5):
        out.append(dict(zip([
          'lineage_verified','dependency_lock_verified','evidence_fetch_hardened',
          'historical_state_protected','current_generation_active'
        ],vals)))
    return out

def expected(ctx):
    out=[]
    if ctx['current_generation_active']:out.extend(GEN)
    if not ctx['lineage_verified']:out.append(CAN[0])
    if not ctx['dependency_lock_verified']:out.append(CAN[1])
    if not ctx['evidence_fetch_hardened']:out.append(CAN[2])
    if not ctx['historical_state_protected']:out.append(CAN[3])
    out.extend(CAN[4:])
    return out

def target(ctx,role):
    return 'KEEP' if role in expected(ctx) else 'DROP'

def base_context(ctx,noise):
    return {
      'lineage_verified':float(ctx['lineage_verified']),
      'dependency_lock_verified':float(ctx['dependency_lock_verified']),
      'evidence_fetch_hardened':float(ctx['evidence_fetch_hardened']),
      'historical_state_protected':float(ctx['historical_state_protected']),
      'current_generation_active':float(ctx['current_generation_active']),
      'nuisance':float(noise),
    }

def rep_numeric(ctx,role,noise):
    x=base_context(ctx,noise)
    x['role_index']=float(ROLE_INDEX[role])
    return x

def rep_one_hot(ctx,role,noise):
    x=base_context(ctx,noise)
    for r in ALL:
        x['role_'+str(ROLE_INDEX[r])]=1.0 if r==role else 0.0
    return x

def rep_semantic(ctx,role,noise):
    x=base_context(ctx,noise)
    x.update({
      'is_generation':1.0 if role in GEN else 0.0,
      'is_unify_lineage':1.0 if role==CAN[0] else 0.0,
      'is_dependency_lock':1.0 if role==CAN[1] else 0.0,
      'is_evidence_fetch':1.0 if role==CAN[2] else 0.0,
      'is_historical_protection':1.0 if role==CAN[3] else 0.0,
      'is_always_active':1.0 if role in ALWAYS else 0.0,
    })
    return x

REPS={
  'NUMERIC_ROLE_INDEX':rep_numeric,
  'ONE_HOT_ROLE_IDENTITY':rep_one_hot,
  'SEMANTIC_ROLE_TYPE':rep_semantic,
}

contexts=all_contexts()
# Deterministic disjoint split of the 32 logical states.
train_ctx=[c for i,c in enumerate(contexts) if i%4 in (0,1)]
val_ctx=[c for i,c in enumerate(contexts) if i%4==2]
blind_ctx=[c for i,c in enumerate(contexts) if i%4==3]
assert len(train_ctx)==16 and len(val_ctx)==8 and len(blind_ctx)==8

def cases(ctxs,rep,noise):
    out=[]
    for c in ctxs:
        for role in ALL:
            x=rep(c,role,noise)
            if noise:
                x['fresh_irrelevant']=float((ROLE_INDEX[role]*7+sum(int(v) for v in c.values()))%11)/10.0
            out.append((x,target(c,role)))
    return out

selection=[]
t0=time.perf_counter()
for name,rep in REPS.items():
    tr=cases(train_ctx,rep,0.0)
    va=cases(val_ctx,rep,0.5)
    r=k.shadow_evolve_intelligence(tr,va,capability='priority_filter_rep_'+name.lower())
    selection.append({
      'representation':name,
      'verdict':r['verdict'],
      'selected_depth':r.get('selected_depth'),
      'train':r.get('train',0.0),
      'validation':r.get('blind',0.0),
      'ablation':r.get('ablation',0.0),
      'candidate_id':r.get('candidate_id'),
    })
selection_seconds=time.perf_counter()-t0
selection.sort(key=lambda z:(z['validation'],z['train'],-int(z.get('selected_depth') or 99),z['representation']),reverse=True)
winner=selection[0]
rep=REPS[winner['representation']]

# Refit selected representation on train+validation, untouched final blind.
tr_final=cases(train_ctx+val_ctx,rep,0.0)
bl_final=cases(blind_ctx,rep,1.0)
t1=time.perf_counter()
final=k.shadow_evolve_intelligence(tr_final,bl_final,capability='developmental_priority_filter_v1')
final_seconds=time.perf_counter()-t1
model=final['model']

def predict(x):
    if tree_acc(model,[(x,'KEEP')])==1.0:return 'KEEP'
    if tree_acc(model,[(x,'DROP')])==1.0:return 'DROP'
    return 'UNRESOLVED'

# Order is a separate native meta-thinking capability and is cheap.
fit_traces=[list(ALL) for _ in range(8)]
def actions(tag,seed):
    xs=[{'id':f'{tag}-{i}','role':r} for i,r in enumerate(ALL)]
    random.Random(seed).shuffle(xs)
    return xs
val_order=[({'split':'validation'},actions(f'OV{i}',10000+i),ALL) for i in range(8)]
blind_order=[({'split':'blind'},actions(f'OB{i}',20000+i),ALL) for i in range(16)]
t2=time.perf_counter()
order=k.meta_evolve_thinking(fit_traces,val_order,fit_traces,blind_order)
order_seconds=time.perf_counter()-t2

def filter_actions(ctx,acts,apply_filter=True):
    if not apply_filter:return list(acts)
    out=[]
    for a in acts:
        x=rep(ctx,a['role'],1.0)
        x['fresh_irrelevant']=0.37
        if predict(x)=='KEEP':
            out.append(a)
    return out

def compose(ctx,acts,apply_filter=True,apply_order=True):
    xs=filter_actions(ctx,acts,apply_filter)
    if not apply_order:
        return [a['role'] for a in xs]
    pred,_=_predict_plan_model(order['model'],(ctx,xs,expected(ctx)))
    return pred

rows=[]
full=filter_ab=order_ab=both_ab=0
for i,c in enumerate(blind_ctx):
    a=actions(f'FINAL{i}',30000+i)
    exp=expected(c)
    p=compose(c,a,True,True)
    pfa=compose(c,a,False,True)
    poa=compose(c,a,True,False)
    pba=compose(c,a,False,False)
    full+=p==exp;filter_ab+=pfa==exp;order_ab+=poa==exp;both_ab+=pba==exp
    rows.append({
      'context':c,'expected':exp,'predicted':p,'pass':p==exp,
      'filter_ablation_pass':pfa==exp,
      'order_ablation_pass':poa==exp,
    })
n=len(rows)
full/=n;filter_ab/=n;order_ab/=n;both_ab/=n

current_ctx={
 'lineage_verified':True,'dependency_lock_verified':False,
 'evidence_fetch_hardened':False,'historical_state_protected':False,
 'current_generation_active':True,
}
current=compose(current_ctx,actions('CURRENT',99199),True,True)
current_expected=expected(current_ctx)

admission=(
 final['train']==1.0 and final['blind']==1.0
 and float(order['validation'])==1.0 and float(order['fresh_blind'])==1.0
 and full==1.0 and full>filter_ab and full>order_ab
 and current==current_expected
)

component={
 'schema':'yado.staged_filter_representation_tournament.component.v1',
 'selected_representation':winner['representation'],
 'filter_model':model,
 'filter_selected_depth':final.get('selected_depth'),
 'order_selected_algorithm':order['selected_algorithm'],
 'order_model':order['model'],
 'fresh_exact':full,
}
component['component_digest']=hashlib.sha256(json.dumps(component,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
(OUT/'component.json').write_text(json.dumps(component,indent=2,sort_keys=True,default=str)+'\n')

report={
 'schema':'yado.staged_filter_representation_tournament.receipt.v1',
 'status':'PASS_STAGED_FILTER_REPRESENTATION_TOURNAMENT_V1' if admission else 'WITHHOLD_STAGED_FILTER_REPRESENTATION_TOURNAMENT',
 'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),
 'budget_policy':'STAGED_CHEAP_CART_FIRST; NO_UNBOUNDED_GENESIS',
 'split':{'train_contexts':16,'validation_contexts':8,'fresh_blind_contexts':8},
 'representation_selection':selection,
 'selected_representation':winner['representation'],
 'selection_seconds':selection_seconds,
 'final_filter':{
   'verdict':final['verdict'],'selected_depth':final.get('selected_depth'),
   'train':final['train'],'fresh_blind':final['blind'],
   'ablation':final['ablation'],'restore':final['restore'],
   'seconds':final_seconds,
 },
 'order':{
   'selected_algorithm':order['selected_algorithm'],
   'validation':order['validation'],'fresh_blind':order['fresh_blind'],
   'seconds':order_seconds,
 },
 'composition_fresh_exact':full,
 'filter_ablation_exact':filter_ab,
 'order_ablation_exact':order_ab,
 'both_ablation_exact':both_ab,
 'current_effective_priority':current,
 'current_expected_priority':current_expected,
 'current_pass':current==current_expected,
 'component':component,
 'canonical_mutation':False,'promotion_applied':False,
 'host_role':'REPRESENTATION_FAMILY_MENU_AND_SPLIT_ONLY; CART DEPTH/MODEL AND ORDER ALGORITHM/MODEL ARE NATIVE YADO',
 'next_required_capability':'LIVE_G0_STAGED_DEVELOPMENTAL_SELF_MODEL_INTEGRATION' if admission else 'NEW_FILTER_PRIMITIVE_OR_REPRESENTATION_SEARCH',
 'semantic_boundary':'BOUNDED DEVELOPMENTAL PRIORITY FILTER/ORDER; NOT GENERAL REASONING OR CANONICAL PROMOTION',
}
report['receipt_sha256']=hashlib.sha256(json.dumps(report,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
(ROOT/'yado_staged_filter_representation_tournament_v1_receipt.json').write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps({
 'status':report['status'],
 'selection':selection,
 'selected_representation':winner['representation'],
 'final_filter':report['final_filter'],
 'order':report['order'],
 'composition_fresh_exact':full,
 'filter_ablation_exact':filter_ab,
 'order_ablation_exact':order_ab,
 'current_pass':report['current_pass'],
 'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True,default=str))
k.close()
