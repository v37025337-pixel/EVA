from __future__ import annotations
from pathlib import Path
import itertools,json,random,statistics,sys
ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36'; sys.path.insert(0,str(PKG))
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_algorithm_component_runtime_native_v1 import _thinking_predict,predict_intel_component

k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'s2_fast_probe.sqlite'))

roles=['OBSERVE','RESEARCH','DIAGNOSE','HYPOTHESIZE','SIMULATE','TEST','ROLLBACK','VERIFY','COMMIT']
safe=['OBSERVE','RESEARCH','HYPOTHESIZE','SIMULATE','DIAGNOSE','TEST','VERIFY','ROLLBACK','COMMIT']
risk=['OBSERVE','DIAGNOSE','ROLLBACK','RESEARCH','HYPOTHESIZE','SIMULATE','TEST','VERIFY','COMMIT']
def ttarget(c): return risk if c['integrity_risk']+c['uncertainty']>1.0 else safe
def acts(order,tag,seed=None):
    a=[{'id':f'{tag}-{i}','role':r} for i,r in enumerate(order)]
    if seed is not None: random.Random(seed).shuffle(a)
    return a

# Grid makes the actual boundary explicit to YADO rather than hiding it in sparse random data.
fit=[]
idx=0
for a in [i/10 for i in range(11)]:
  for b in [i/10 for i in range(11)]:
    c={'integrity_risk':a,'uncertainty':b,'novelty':(idx%7)/7}
    e=ttarget(c); fit.append((c,acts(e,f'F{idx}'),e)); idx+=1
val=[]; idx=0
for a in [0.05+i/10 for i in range(10)]:
  for b in [0.05+i/10 for i in range(10)]:
    c={'integrity_risk':a,'uncertainty':b,'novelty':((idx*3)%11)/11}
    e=ttarget(c); val.append((c,acts(e,f'V{idx}',2000+idx),e)); idx+=1
blind=[]; r=random.Random(99101)
for i in range(240):
    a=r.uniform(.01,.99)
    b=max(0,min(1,1-a+r.uniform(-.05,.05))) if i<180 else r.random()
    c={'integrity_risk':a,'uncertainty':b,'novelty':r.random(),'fresh':r.random()}
    e=ttarget(c); blind.append((c,acts(e,f'B{i}',5000+i),e))

tr5=k.synthesize_thinking_algorithm_component(fit,val,fit,blind)
tr6=k.synthesize_thinking_with_extended_meta_grammar(fit,val,fit,blind)
tsel=tr6 if float(tr6.get('validation',0))>float(tr5.get('validation',0)) else tr5
tacc=sum(_thinking_predict(tsel['model'],x)[0]==x[2] for x in blind)/len(blind)
tb=[x for x in blind[:180]]
tbacc=sum(_thinking_predict(tsel['model'],x)[0]==x[2] for x in tb)/len(tb)

def itarget(x):
    if x['integrity_score']<.5 or x['rollback_score']<.5:return 'ROLLBACK'
    if x['fresh_blind']>=.90 and x['ablation_drop']>=.20 and x['transfer_score']>=.80:return 'PROMOTE_CANDIDATE'
    if x['evidence_coverage']<.60:return 'RESEARCH_MORE'
    return 'SHADOW_REPAIR'

# Compact structured curriculum around every decision surface.
ir=random.Random(99201)
ifit=[]
for i in range(360):
    boundary=i<260
    def near(t,w=.12): return max(0,min(1,t+ir.uniform(-w,w)))
    x={
      'integrity_score':near(.5) if boundary else ir.random(),
      'rollback_score':near(.5) if boundary else ir.random(),
      'fresh_blind':near(.9) if boundary else ir.random(),
      'ablation_drop':near(.2) if boundary else ir.random(),
      'transfer_score':near(.8) if boundary else ir.random(),
      'evidence_coverage':near(.6) if boundary else ir.random(),
      'novelty':ir.random(),
    }; ifit.append((x,itarget(x)))
ival=[]
for i in range(140):
    x={k:ir.random() for k in ['integrity_score','rollback_score','fresh_blind','ablation_drop','transfer_score','evidence_coverage','novelty']}
    ival.append((x,itarget(x)))
iblind=[]
for i in range(360):
    boundary=i<240
    def near2(t,w=.07): return max(0,min(1,t+ir.uniform(-w,w)))
    x={
      'integrity_score':near2(.5) if boundary else ir.random(),
      'rollback_score':near2(.5) if boundary else ir.random(),
      'fresh_blind':near2(.9) if boundary else ir.random(),
      'ablation_drop':near2(.2) if boundary else ir.random(),
      'transfer_score':near2(.8) if boundary else ir.random(),
      'evidence_coverage':near2(.6) if boundary else ir.random(),
      'novelty':ir.random(),'fresh_noise':ir.random(),
    }; iblind.append((x,itarget(x)))

ir5=k.synthesize_intelligence_algorithm_component(ifit,ival,ifit+ival,iblind)
ir6=k.synthesize_intelligence_with_extended_meta_grammar(ifit,ival,ifit+ival,iblind)
isel=ir6 if float(ir6.get('validation',0))>float(ir5.get('validation',0)) else ir5
iacc=sum(predict_intel_component(isel['model'],x)==y for x,y in iblind)/len(iblind)
ibacc=sum(predict_intel_component(isel['model'],x)==y for x,y in iblind[:240])/240

report={
 'status':'PASS_S2_FAST_COUNTEREXAMPLE_REPAIR' if min(tacc,tbacc,iacc,ibacc)>=.90 else 'WITHHOLD_S2_FAST_COUNTEREXAMPLE_REPAIR',
 'thinking':{'validation':tsel.get('validation'),'native_fresh':tsel.get('fresh_blind'),'fresh_recheck':tacc,'boundary':tbacc,'model':tsel['model']},
 'intelligence':{'validation':isel.get('validation'),'native_fresh':isel.get('fresh_blind'),'fresh_recheck':iacc,'boundary':ibacc,'model':isel['model']},
 'threshold':.90,
 'canonical_mutation':False,
}
(ROOT/'yado_s2_fast_counterexample_repair_probe_report.json').write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('thinking','intelligence')},indent=2))
print(json.dumps({'thinking':{k:v for k,v in report['thinking'].items() if k!='model'},'intelligence':{k:v for k,v in report['intelligence'].items() if k!='model'}},indent=2))
k.close()
