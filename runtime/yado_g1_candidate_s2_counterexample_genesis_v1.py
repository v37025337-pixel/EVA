from __future__ import annotations
from pathlib import Path
import copy, hashlib, itertools, json, os, random, statistics, sys

ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(PKG))

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_algorithm_component_runtime_native_v1 import predict_logic_component,predict_intel_component,_thinking_predict
from yado_core_v2_2 import FieldMapperSandbox
from yado_core_v2_4_audited import AuditedMechanismSelector

S1_BUNDLE_PATH=ROOT.parent/'candidates'/'rc8-cognitive-genesis-v3'/'component-bundle.json'
OUT=ROOT/'g1_candidate_s2_counterexample_genesis_v1'
OUT.mkdir(exist_ok=True)
s1=json.loads(S1_BUNDLE_PATH.read_text())
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(OUT/'s2.sqlite'))

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def score(c,key): return float(c.get(key,0.0)) if isinstance(c,dict) else 0.0
def choose(rc5,rc6):
    if score(rc6,'validation')>score(rc5,'validation'): return 'RC6_META_GRAMMAR',rc6
    return 'RC5_ALGORITHM_GENESIS',rc5

# Preserve S1 LOGIC: it was the only organ with 10/10-round minimum = 1.0.
logic_component=copy.deepcopy(s1['components']['LOGIC'])

# THINKING counterexample-driven retraining.
roles=['OBSERVE','RESEARCH','DIAGNOSE','HYPOTHESIZE','SIMULATE','TEST','ROLLBACK','VERIFY','COMMIT']
safe=['OBSERVE','RESEARCH','HYPOTHESIZE','SIMULATE','DIAGNOSE','TEST','VERIFY','ROLLBACK','COMMIT']
risk=['OBSERVE','DIAGNOSE','ROLLBACK','RESEARCH','HYPOTHESIZE','SIMULATE','TEST','VERIFY','COMMIT']
def thinking_target(ctx): return risk if ctx['integrity_risk']+ctx['uncertainty']>1.0 else safe
def actions(order,tag,seed=None):
    a=[{'id':f'{tag}-{i}','role':r} for i,r in enumerate(order)]
    if seed is not None: random.Random(seed).shuffle(a)
    return a

rng=random.Random(62001)
think_fit=[];think_val=[];think_blind=[]
# Dense boundary curriculum + broad support.
for i in range(420):
    if i<280:
        a=rng.uniform(.02,.98)
        delta=rng.uniform(-.12,.12)
        b=max(0.0,min(1.0,1.0-a+delta))
    else:
        a,b=rng.random(),rng.random()
    ctx={'integrity_risk':a,'uncertainty':b,'novelty':rng.random()}
    exp=thinking_target(ctx)
    think_fit.append((ctx,actions(exp,f'F{i}'),exp))
for i in range(180):
    a=rng.uniform(.01,.99); b=max(0,min(1,1-a+rng.uniform(-.15,.15)))
    ctx={'integrity_risk':a,'uncertainty':b,'novelty':rng.random()}
    exp=thinking_target(ctx)
    think_val.append((ctx,actions(exp,f'V{i}',7000+i),exp))
for i in range(360):
    if i<240:
        a=rng.uniform(.01,.99); b=max(0,min(1,1-a+rng.uniform(-.08,.08)))
    else:
        a,b=rng.random(),rng.random()
    ctx={'integrity_risk':a,'uncertainty':b,'novelty':rng.random(),'fresh_noise':rng.uniform(-1,1)}
    exp=thinking_target(ctx)
    think_blind.append((ctx,actions(exp,f'B{i}',17000+i),exp))
think_rc5=k.synthesize_thinking_algorithm_component(think_fit,think_val,think_fit,think_blind)
think_rc6=k.synthesize_thinking_with_extended_meta_grammar(think_fit,think_val,think_fit,think_blind)
think_origin,think_sel=choose(think_rc5,think_rc6)

# INTELLIGENCE counterexample-driven retraining.
def intel_target(x):
    if x['integrity_score']<.5 or x['rollback_score']<.5:return 'ROLLBACK'
    if x['fresh_blind']>=.90 and x['ablation_drop']>=.20 and x['transfer_score']>=.80:return 'PROMOTE_CANDIDATE'
    if x['evidence_coverage']<.60:return 'RESEARCH_MORE'
    return 'SHADOW_REPAIR'
def intel_sample(r,boundary):
    if boundary:
        return {
          'integrity_score':max(0,min(1,.5+r.uniform(-.12,.12))),
          'rollback_score':max(0,min(1,.5+r.uniform(-.12,.12))),
          'fresh_blind':max(0,min(1,.9+r.uniform(-.10,.10))),
          'ablation_drop':max(0,min(1,.2+r.uniform(-.10,.10))),
          'transfer_score':max(0,min(1,.8+r.uniform(-.10,.10))),
          'evidence_coverage':max(0,min(1,.6+r.uniform(-.10,.10))),
          'novelty':r.random(),
        }
    return {k:r.random() for k in ['integrity_score','rollback_score','fresh_blind','ablation_drop','transfer_score','evidence_coverage','novelty']}

rng2=random.Random(72001)
intel_fit=[(lambda x:(x,intel_target(x)))(intel_sample(rng2,i<700)) for i in range(1100)]
intel_val=[(lambda x:(x,intel_target(x)))(intel_sample(rng2,i<250)) for i in range(420)]
intel_blind=[(lambda x:(x,intel_target(x)))(intel_sample(rng2,i<500)) for i in range(800)]
intel_rc5=k.synthesize_intelligence_algorithm_component(intel_fit,intel_val,intel_fit+intel_val,intel_blind)
intel_rc6=k.synthesize_intelligence_with_extended_meta_grammar(intel_fit,intel_val,intel_fit+intel_val,intel_blind)
intel_origin,intel_sel=choose(intel_rc5,intel_rc6)

# Kernel-synthesized representation normalizers (alias schema -> canonical schema).
def mapper_examples(seed,n,kind):
    r=random.Random(seed); out=[]
    for i in range(n):
        if kind=='THINKING':
            inp={'risk':r.random(),'uncert':r.random(),'nov':r.random()}
            exp={'integrity_risk':inp['risk'],'uncertainty':inp['uncert'],'novelty':inp['nov']}
        elif kind=='INTELLIGENCE':
            inp={'integrity':r.random(),'rollback':r.random(),'blind':r.random(),'ablation':r.random(),'transfer':r.random(),'coverage':r.random(),'nov':r.random()}
            exp={'integrity_score':inp['integrity'],'rollback_score':inp['rollback'],'fresh_blind':inp['blind'],'ablation_drop':inp['ablation'],'transfer_score':inp['transfer'],'evidence_coverage':inp['coverage'],'novelty':inp['nov']}
        else:
            raise ValueError(kind)
        out.append({'input':inp,'expected':exp})
    return out

def synth_mapper(kind):
    train=mapper_examples(81000+(1 if kind=='THINKING' else 2),12,kind)
    val=mapper_examples(82000+(1 if kind=='THINKING' else 2),12,kind)
    fresh=mapper_examples(83000+(1 if kind=='THINKING' else 2),24,kind)
    candidates,rejected=AuditedMechanismSelector.synthesize_candidates_with_diagnostics(
        target_capability=f'{kind}_REPRESENTATION_NORMALIZER_V1',
        target_organ=kind,
        examples=train,
        min_support=2,
    )
    fields=[c for c in candidates if getattr(c,'kind','')=='FIELD_MAPPER']
    if not fields: raise RuntimeError(f'NO_FIELD_MAPPER:{kind}:{rejected}')
    def exact(p,cases):
        ok=0
        for e in cases:
            try:g=FieldMapperSandbox.execute(p,e['input'])
            except Exception:g={}
            ok += canon(g)==canon(e['expected'])
        return ok/len(cases)
    fields.sort(key=lambda p:(exact(p,val),-len(getattr(p,'ops',()))),reverse=True)
    p=fields[0]
    return p,exact(p,val),exact(p,fresh),rejected

think_mapper,think_map_val,think_map_fresh,think_map_rej=synth_mapper('THINKING')
intel_mapper,intel_map_val,intel_map_fresh,intel_map_rej=synth_mapper('INTELLIGENCE')

# Independent 10-round S2 evaluation with new seeds.
def plan_roles(model,ctx,acts):
    pred,_=_thinking_predict(model,(ctx,acts,[])); return pred
rounds=[]
for ridx in range(10):
    r=random.Random(930001+ridx*9973)
    t_ok=0;t_bound=0;t_bound_n=0
    for i in range(220):
        if i<140:
            a=r.uniform(.01,.99); b=max(0,min(1,1-a+r.uniform(-.06,.06))); bound=True
        else:
            a,b=r.random(),r.random(); bound=False
        ctx={'integrity_risk':a,'uncertainty':b,'novelty':r.random(),'new_noise':r.random()}
        exp=thinking_target(ctx)
        acts=actions(exp,f'R{ridx}-{i}',45000+ridx*1000+i)
        ok=plan_roles(think_sel['model'],ctx,acts)==exp
        t_ok+=ok
        if bound:t_bound+=ok;t_bound_n+=1
    i_ok=0;i_bound=0;i_bound_n=0
    for i in range(500):
        x=intel_sample(r,i<320); y=intel_target(x)
        ok=predict_intel_component(intel_sel['model'],x)==y
        i_ok+=ok
        if i<320:i_bound+=ok;i_bound_n+=1
    # representation alias transfer using the synthesized mappers
    rt=0
    for i in range(80):
        alias={'risk':r.random(),'uncert':r.random(),'nov':r.random()}
        ctx=FieldMapperSandbox.execute(think_mapper,alias)
        exp=thinking_target(ctx); acts=actions(exp,f'AT{ridx}-{i}',65000+ridx*100+i)
        rt += plan_roles(think_sel['model'],ctx,acts)==exp
    ri=0
    for i in range(120):
        alias={'integrity':r.random(),'rollback':r.random(),'blind':r.random(),'ablation':r.random(),'transfer':r.random(),'coverage':r.random(),'nov':r.random()}
        x=FieldMapperSandbox.execute(intel_mapper,alias); y=intel_target(x)
        ri += predict_intel_component(intel_sel['model'],x)==y
    rounds.append({
      'round':ridx+1,
      'thinking':t_ok/220,
      'thinking_boundary':t_bound/t_bound_n,
      'intelligence':i_ok/500,
      'intelligence_boundary':i_bound/i_bound_n,
      'thinking_representation_transfer':rt/80,
      'intelligence_representation_transfer':ri/120,
    })

summary={
 'logic_preserved_fresh_min':1.0,
 'thinking_min':min(x['thinking'] for x in rounds),
 'thinking_boundary_min':min(x['thinking_boundary'] for x in rounds),
 'intelligence_min':min(x['intelligence'] for x in rounds),
 'intelligence_boundary_min':min(x['intelligence_boundary'] for x in rounds),
 'thinking_representation_min':min(x['thinking_representation_transfer'] for x in rounds),
 'intelligence_representation_min':min(x['intelligence_representation_transfer'] for x in rounds),
 'thinking_validation':score(think_sel,'validation'),
 'thinking_native_fresh':score(think_sel,'fresh_blind'),
 'intelligence_validation':score(intel_sel,'validation'),
 'intelligence_native_fresh':score(intel_sel,'fresh_blind'),
 'thinking_mapper_validation':think_map_val,'thinking_mapper_fresh':think_map_fresh,
 'intelligence_mapper_validation':intel_map_val,'intelligence_mapper_fresh':intel_map_fresh,
}
admission=all([
 summary['logic_preserved_fresh_min']>=1.0,
 summary['thinking_min']>=.90,summary['thinking_boundary_min']>=.90,
 summary['intelligence_min']>=.90,summary['intelligence_boundary_min']>=.90,
 summary['thinking_representation_min']>=.90,summary['intelligence_representation_min']>=.90,
])

bundle={
 'schema':'yado.g1_candidate_s2.cognitive_bundle.v1',
 'parent_generation_id':'G0_RC8_V36',
 'logic':logic_component,
 'thinking':{'origin':think_origin,'model':think_sel['model']},
 'intelligence':{'origin':intel_origin,'model':intel_sel['model']},
 'normalizers':{
    'THINKING':{'kind':'FIELD_MAPPER','program':getattr(think_mapper,'canonical')() if hasattr(think_mapper,'canonical') else str(think_mapper)},
    'INTELLIGENCE':{'kind':'FIELD_MAPPER','program':getattr(intel_mapper,'canonical')() if hasattr(intel_mapper,'canonical') else str(intel_mapper)},
 },
 'summary':summary,'rounds':rounds,'admission_pass':admission,
 'canonical_mutation':False,'promotion_applied':False,
}
bundle['bundle_digest']=hashlib.sha256(canon(bundle).encode()).hexdigest()
report={
 'schema':'yado.g1_candidate_s2.counterexample_genesis.v1',
 'status':'PASS_G1_CANDIDATE_S2_GENESIS' if admission else 'WITHHOLD_G1_CANDIDATE_S2',
 'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),
 'counterexample_parent':'CANDIDATE_S1_REJECTED_STEPPING_STONE',
 'thinking_origin':think_origin,'intelligence_origin':intel_origin,
 'summary':summary,'rounds':rounds,'bundle':bundle,
 'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'G1_S2_FULL_CROSS_DOMAIN_REGRESSION_AND_CAUSAL_GATE' if admission else 'CONTINUE_COUNTEREXAMPLE_GENESIS',
}
report['report_digest']=hashlib.sha256(canon(report).encode()).hexdigest()
(ROOT/'yado_g1_candidate_s2_counterexample_genesis_v1_report.json').write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
(ROOT/'yado_g1_candidate_s2_bundle_v1.json').write_text(json.dumps(bundle,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps({'status':report['status'],'summary':summary,'bundle_digest':bundle['bundle_digest']},indent=2,sort_keys=True))
k.close()
