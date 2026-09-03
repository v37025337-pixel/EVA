from __future__ import annotations
import json,itertools
from dataclasses import asdict
from pathlib import Path
import yado_core_v2_5_unified as unified_mod
from yado_core_v2_5_unified import CycleRequest,CycleTask
from yado_core_v3_0_rc6_r6_schema_adaptation import UnifiedYADOKernelV30RC6R6SchemaAdaptation
from yado_phase_a_shadow import Case
from yado_stateful_frontier_repair_cycle12 import ActiveBeliefSchema,ActiveInformationGainInducer,FrontierPortfolioV6,cj

ROOT=Path(__file__).resolve().parent
DB=ROOT/'yado_observe_stateful_frontier_cycle13.db'
REPORT=ROOT/'yado_stateful_frontier_repair_cycle13_report.json'

def ev(p,o): return {'probe':p,'obs':o}
def hidden_schema():
    hs=('K','L','M');ps=('alpha','beta');obs=(0,1)
    qmap={('K','alpha'):0.2,('L','alpha'):0.8,('M','alpha'):0.5,('K','beta'):0.8,('L','beta'):0.5,('M','beta'):0.2}
    likes=[]
    for h in hs:
        for p in ps:
            q=qmap[(h,p)];likes += [(h,p,0,1-q),(h,p,1,q)]
    return ActiveBeliefSchema('HIDDEN_TRANSFER_NOT_SUPPLIED',hs,ps,obs,tuple((h,1/3) for h in hs),tuple(likes),0.75)
def expected(s): return ActiveInformationGainInducer.execute(hidden_schema(),s)
def allseq(nmax):
    atoms=[ev(p,o) for p in ('alpha','beta') for o in (0,1)];out=[]
    for n in range(1,nmax+1):
        for t in itertools.product(range(4),repeat=n):out.append([dict(atoms[i]) for i in t])
    return out
def request():
    pool=[Case(f'P{i}',s,expected(s)) for i,s in enumerate(allseq(4),1)];train=[]
    train += [c for c in pool if len(c.input)<=2]
    for lab in ('K','L','M'):
        train += [c for c in pool if len(c.input)==4 and any(y['decision']==lab for y in c.expected)][:8]
    for pr in ('alpha','beta'):
        train += [c for c in pool if len(c.input)==4 and c.expected[-1]['decision']=='DEFER' and c.expected[-1]['next_probe']==pr][:8]
    seen=set();compact=[]
    for c in train:
        k=cj(c.input)
        if k in seen:continue
        seen.add(k);compact.append(Case(f'AIG2-T{len(compact)+1:03d}',c.input,c.expected))
    freshraw=[
      [ev('alpha',1),ev('beta',1),ev('alpha',0),ev('beta',1)],
      [ev('beta',0),ev('alpha',1),ev('beta',0),ev('alpha',0)],
      [ev('alpha',0),ev('beta',1),ev('alpha',0),ev('beta',0),ev('alpha',1)],
      [ev('beta',1),ev('alpha',1),ev('beta',0),ev('beta',1),ev('alpha',1)],
      [ev('alpha',1),ev('alpha',1),ev('beta',0),ev('alpha',0),ev('beta',1)],
      [ev('beta',0),ev('beta',0),ev('alpha',1),ev('beta',1),ev('alpha',0)],
    ]
    blind=[Case(f'AIG2-B{i:03d}',s,expected(s)) for i,s in enumerate(freshraw,1)]
    live=[ev('beta',1),ev('alpha',0),ev('beta',1),ev('alpha',0),ev('beta',1)]
    return CycleRequest('github:microsoft/prose:tutorial','fresh active diagnosis transfer with renamed hypotheses and probes and changed information topology',
      [{'id':'b7','role':'COMMIT'},{'id':'b4','role':'TEST'},{'id':'b2','role':'DIAGNOSE'},{'id':'b6','role':'LEARN'},{'id':'b1','role':'OBSERVE'},{'id':'b5','role':'VERIFY'},{'id':'b3','role':'HYPOTHESIZE'}],
      {'blind':0.0,'ablation_drop':0.0,'restore':0.0,'integration_gap':0.0},CycleTask('active_information_gain_symbolic_transfer',compact,blind,live,expected(live)))
def mechanism(r):
    for x in r.get('trace',[]):
        if x.get('stage')=='EXECUTION':return dict(x.get('action') or {})
    return {}
def obj(d):
    if d.get('family')!=ActiveInformationGainInducer.FAMILY:return None
    return ActiveBeliefSchema(d['family'],tuple(d['hypotheses']),tuple(d['probes']),tuple(d['observations']),tuple((x[0],float(x[1])) for x in d['priors']),tuple((x[0],x[1],x[2],float(x[3])) for x in d['likelihoods']),float(d['confidence_threshold']),d.get('policy','MAP_IF_CONFIDENT_ELSE_MAX_EXPECTED_INFORMATION_GAIN'),d.get('origin','FAILURE_DERIVED_ACTIVE_INFORMATION_GAIN'))
def main():
    r=request();
    if DB.exists():DB.unlink()
    old=unified_mod.FailureDrivenSchemaInducer;unified_mod.FailureDrivenSchemaInducer=FrontierPortfolioV6
    try:
        k=UnifiedYADOKernelV30RC6R6SchemaAdaptation(str(DB))
        try:g=k.run_causal_cycle(r);a=k.run_causal_cycle(r,ablate={'MECHANISM'});snap=k.unified_snapshot()
        finally:k.close()
    finally:unified_mod.FailureDrivenSchemaInducer=old
    m=mechanism(g);s=m.get('schema') or {};o=obj(s);tr=[]
    if o:_,tr=ActiveInformationGainInducer.execute_with_trace(o,r.task.live_input)
    ok=g.get('cycle_success') is True and o is not None and g.get('blind_score')==1.0 and g.get('ablation_score')==0.0 and g.get('restore_score')==1.0 and a.get('cycle_success') is False
    rep={'schema':'yado.stateful_frontier_repair.cycle13.v1','status':'FRESH_ACTIVE_INFORMATION_GAIN_TRANSFER_SUPPORTED' if ok else 'WITHHOLD','meta_grammar_changed':False,'previous_active_information_gain_mechanism_reused_unchanged':True,'cycle':{'cycle_id':g.get('cycle_id'),'cycle_success':g.get('cycle_success'),'family':s.get('family'),'selected_priors':s.get('priors'),'selected_likelihoods':s.get('likelihoods'),'selected_threshold':s.get('confidence_threshold'),'train_exact':m.get('train_exact'),'blind':g.get('blind_score'),'ablation':g.get('ablation_score'),'restore':g.get('restore_score'),'live_output':g.get('live_output'),'expected_live':g.get('expected_live'),'live_trace':tr,'learning_closed':g.get('learning_closed'),'mechanism_ablation_cycle_success':a.get('cycle_success')},'hidden_transfer_not_supplied_to_learner':asdict(hidden_schema()),'fresh_used_for_selection':False,'observation_snapshot':snap,'claim_boundary':{'durable_head_modified':False,'same_host_supplied_information_gain_substrate_reused':True,'general_active_learning_proven':False}}
    REPORT.write_text(json.dumps(rep,ensure_ascii=False,indent=2));print(json.dumps(rep,ensure_ascii=False,indent=2));return 0 if ok else 2
if __name__=='__main__':raise SystemExit(main())
