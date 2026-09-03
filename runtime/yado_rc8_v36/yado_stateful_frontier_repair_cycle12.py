from __future__ import annotations
import hashlib,itertools,json,math
from dataclasses import asdict,dataclass
from pathlib import Path
from typing import Any,Mapping,Sequence

import yado_core_v2_5_unified as unified_mod
from yado_core_v2_5_unified import CycleRequest,CycleTask
from yado_core_v3_0_rc6_r6_schema_adaptation import UnifiedYADOKernelV30RC6R6SchemaAdaptation
from yado_phase_a_shadow import Case
from yado_primitive_genesis_cycle1 import freeze
from yado_stateful_frontier_repair_cycle2 import Score
from yado_stateful_frontier_repair_cycle10 import FrontierPortfolioV5

ROOT=Path(__file__).resolve().parent
DB=ROOT/'yado_observe_stateful_frontier_cycle12.db'
REPORT=ROOT/'yado_stateful_frontier_repair_cycle12_report.json'

def cj(x): return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def sha(x): return hashlib.sha256(cj(x).encode()).hexdigest()

@dataclass(frozen=True)
class ActiveBeliefSchema:
    family:str
    hypotheses:tuple[str,...]
    probes:tuple[str,...]
    observations:tuple[Any,...]
    priors:tuple[tuple[str,float],...]
    likelihoods:tuple[tuple[str,str,Any,float],...]
    confidence_threshold:float
    policy:str='MAP_IF_CONFIDENT_ELSE_MAX_EXPECTED_INFORMATION_GAIN'
    origin:str='FAILURE_DERIVED_ACTIVE_INFORMATION_GAIN'
    @property
    def digest(self): return sha(asdict(self))
    @property
    def complexity(self): return len(self.priors)+len(self.likelihoods)+1
    def prior_map(self): return dict(self.priors)
    def like_map(self): return {(h,p,cj(o)):float(v) for h,p,o,v in self.likelihoods}

class ActiveInformationGainInducer:
    FAMILY='ACTIVE_BELIEF_INFORMATION_GAIN_TRANSDUCER'
    PROB_GRID=(0.2,0.5,0.8)
    THRESHOLD_GRID=(0.7,0.75,0.8,0.85,0.9)
    def __init__(self,complexity_penalty=.001): self.complexity_penalty=complexity_penalty
    @staticmethod
    def _validate(cases):
        return bool(cases) and all(isinstance(c.input,list) and isinstance(c.expected,list) and len(c.input)==len(c.expected) and all(isinstance(e,dict) and set(e)=={'probe','obs'} for e in c.input) and all(isinstance(y,dict) and set(y)=={'decision','next_probe'} for y in c.expected) for c in cases)
    @staticmethod
    def infer_hypotheses(cases):
        return tuple(sorted({str(y['decision']) for c in cases for y in c.expected if y['decision'] not in ('DEFER','INCONSISTENT')}))
    @staticmethod
    def infer_probes(cases): return tuple(sorted({str(e['probe']) for c in cases for e in c.input}))
    @staticmethod
    def infer_obs(cases):
        d={cj(e['obs']):e['obs'] for c in cases for e in c.input}; return tuple(d[k] for k in sorted(d))
    @staticmethod
    def entropy(weights):
        return -sum(v*math.log(v,2) for v in weights.values() if v>0)
    @classmethod
    def posterior(cls,schema,weights,probe,obs):
        lm=schema.like_map(); w={h:weights[h]*lm[(h,probe,cj(obs))] for h in schema.hypotheses}; z=sum(w.values())
        return None if z<=0 else {h:v/z for h,v in w.items()}
    @classmethod
    def best_probe(cls,schema,weights):
        lm=schema.like_map(); rows=[]
        for p in schema.probes:
            exp_h=0.0
            for obs in schema.observations:
                po=sum(weights[h]*lm[(h,p,cj(obs))] for h in schema.hypotheses)
                if po<=0: continue
                post=cls.posterior(schema,weights,p,obs)
                exp_h += po*cls.entropy(post)
            gain=cls.entropy(weights)-exp_h
            rows.append((gain,p))
        rows.sort(key=lambda x:(-x[0],x[1]))
        return rows[0][1],rows[0][0]
    @classmethod
    def execute_with_trace(cls,schema,value):
        pri=schema.prior_map(); z=sum(pri.values()); weights={h:pri[h]/z for h in schema.hypotheses}; out=[];tr=[]
        for e in value:
            post=cls.posterior(schema,weights,e['probe'],e['obs'])
            if post is None:
                row={'decision':'INCONSISTENT','next_probe':'STOP'}; out.append(row); tr.append({'event':e,'posterior':{},**row}); continue
            weights=post; ranked=sorted(weights.items(),key=lambda kv:(-kv[1],kv[0])); h,conf=ranked[0]
            if conf+1e-12>=schema.confidence_threshold:
                row={'decision':h,'next_probe':'STOP'}; gain=None
            else:
                p,gain=cls.best_probe(schema,weights); row={'decision':'DEFER','next_probe':p}
            out.append(row); tr.append({'event':dict(e),'posterior':{k:round(v,10) for k,v in sorted(weights.items())},'confidence':round(conf,10),'information_gain':None if gain is None else round(gain,10),**row})
        return out,tr
    @classmethod
    def execute(cls,schema,value): return cls.execute_with_trace(schema,value)[0]
    def _fits(self,schema,cases):
        for c in cases:
            try:
                if freeze(self.execute(schema,c.input))!=freeze(c.expected): return False
            except Exception: return False
        return True
    def score(self,schema,cases):
        passed=0;fail=[]
        for c in cases:
            try: ok=freeze(self.execute(schema,c.input))==freeze(c.expected)
            except Exception: ok=False
            if ok: passed+=1
            else: fail.append(c.case_id)
        ex=passed/max(1,len(cases)); return Score(schema,ex,ex-self.complexity_penalty*schema.complexity,fail)
    def search(self,cases):
        if not self._validate(cases): return None,0
        hs=self.infer_hypotheses(cases); ps=self.infer_probes(cases); obs=self.infer_obs(cases)
        if len(hs)!=3 or len(ps)!=2 or len(obs)!=2: return None,0
        priors=tuple((h,1/3) for h in hs) # bounded first active-exploration step: no base-rate evidence in corpus
        generated=0;best=None;bestkey=None
        # one Bernoulli parameter P(obs[1]|h,p) per hypothesis/probe
        for vals in itertools.product(self.PROB_GRID,repeat=len(hs)*len(ps)):
            likes=[];i=0
            for h in hs:
                for p in ps:
                    q=vals[i];i+=1
                    likes += [(h,p,obs[0],1-q),(h,p,obs[1],q)]
            for th in self.THRESHOLD_GRID:
                generated+=1
                s=ActiveBeliefSchema(self.FAMILY,hs,ps,obs,priors,tuple(likes),th)
                if not self._fits(s,cases): continue
                sc=self.score(s,cases)
                # prefer robust probe separation and deterministic digest, train only
                sep=sum(abs(dict(((h,p,cj(o)),v) for h,p,o,v in likes)[(hs[0],p,cj(obs[1]))]-dict(((h,p,cj(o)),v) for h,p,o,v in likes)[(hs[-1],p,cj(obs[1]))]) for p in ps)
                key=(sc.exact,round(sep,8),-s.complexity,s.digest)
                if best is None or key>bestkey: best,bestkey=sc,key
        return best,generated

class FrontierPortfolioV6:
    def __init__(self): self.old=FrontierPortfolioV5();self.active=ActiveInformationGainInducer()
    def search(self,cases):
        b,n=self.active.search(cases)
        if b is not None:return b,n
        return self.old.search(cases)
    def score(self,s,cases): return self.active.score(s,cases) if isinstance(s,ActiveBeliefSchema) else self.old.score(s,cases)
    def execute(self,s,v): return self.active.execute(s,v) if isinstance(s,ActiveBeliefSchema) else self.old.execute(s,v)

def hidden_schema():
    hs=('A','B','C');ps=('p','q');obs=(0,1)
    # p separates A/C; q separates B/A. All values lie on learner grid.
    qmap={('A','p'):0.8,('B','p'):0.5,('C','p'):0.2,('A','q'):0.2,('B','q'):0.8,('C','q'):0.5}
    likes=[]
    for h in hs:
        for p in ps:
            q=qmap[(h,p)];likes += [(h,p,0,1-q),(h,p,1,q)]
    return ActiveBeliefSchema('HIDDEN_BENCHMARK_NOT_SUPPLIED',hs,ps,obs,tuple((h,1/3) for h in hs),tuple(likes),0.8)

def expected(seq): return ActiveInformationGainInducer.execute(hidden_schema(),seq)
def ev(p,o): return {'probe':p,'obs':o}

def seqs(max_len):
    atoms=[ev(p,o) for p in ('p','q') for o in (0,1)]
    out=[]
    for n in range(1,max_len+1):
        for tup in itertools.product(range(len(atoms)),repeat=n): out.append([dict(atoms[i]) for i in tup])
    return out

def make_request():
    pool=[Case(f'P{i:03d}',s,expected(s)) for i,s in enumerate(seqs(4),1)]
    train=[]
    # compact revealed curriculum: all 1-2 step histories, then stratified
    # 4-step histories that expose A/B/C decisions and both probe choices.
    for c in pool:
        if len(c.input)<=2: train.append(c)
    for label in ('A','B','C'):
        xs=[c for c in pool if len(c.input)==4 and any(y['decision']==label for y in c.expected)]
        train.extend(xs[:8])
    for probe in ('p','q'):
        xs=[c for c in pool if len(c.input)==4 and c.expected[-1]['decision']=='DEFER' and c.expected[-1]['next_probe']==probe]
        train.extend(xs[:8])
    seen=set(); compact=[]
    for c in train:
        k=cj(c.input)
        if k in seen: continue
        seen.add(k); compact.append(Case(f'AIG-T{len(compact)+1:03d}',c.input,c.expected))
    train=compact
    fresh_raw=[
      [ev('p',1),ev('q',0),ev('p',1),ev('q',1)],
      [ev('q',1),ev('p',0),ev('q',1),ev('p',1)],
      [ev('p',0),ev('p',0),ev('q',1),ev('q',0)],
      [ev('q',0),ev('q',0),ev('p',1),ev('p',0)],
      [ev('p',1),ev('q',1),ev('p',0),ev('q',1),ev('p',1)],
      [ev('q',1),ev('p',1),ev('q',0),ev('p',0),ev('q',1)],
      [ev('p',0),ev('q',1),ev('q',1),ev('p',0),ev('p',0)],
      [ev('q',0),ev('p',1),ev('p',1),ev('q',0),ev('q',0)],
    ]
    blind=[Case(f'AIG-B{i:03d}',s,expected(s)) for i,s in enumerate(fresh_raw,1)]
    live=[ev('p',1),ev('q',0),ev('p',1),ev('p',1),ev('q',0)]
    return CycleRequest(
      resource_id='github:microsoft/prose:tutorial',
      resource_query='active diagnosis under uncertainty: choose the next probe by expected information gain across multiple weighted hypotheses',
      actions=[{'id':'a7','role':'COMMIT'},{'id':'a4','role':'TEST'},{'id':'a2','role':'DIAGNOSE'},{'id':'a6','role':'LEARN'},{'id':'a1','role':'OBSERVE'},{'id':'a5','role':'VERIFY'},{'id':'a3','role':'HYPOTHESIZE'}],
      features={'blind':0.0,'ablation_drop':0.0,'restore':0.0,'integration_gap':0.0},
      task=CycleTask('active_information_gain_three_hypotheses_two_probes',train,blind,live,expected(live)))

def mechanism(r):
    for s in r.get('trace',[]):
        if s.get('stage')=='EXECUTION':return dict(s.get('action') or {})
    return {}

def schema_obj(d):
    if d.get('family')!=ActiveInformationGainInducer.FAMILY:return None
    return ActiveBeliefSchema(d['family'],tuple(d['hypotheses']),tuple(d['probes']),tuple(d['observations']),tuple((x[0],float(x[1])) for x in d['priors']),tuple((x[0],x[1],x[2],float(x[3])) for x in d['likelihoods']),float(d['confidence_threshold']),d.get('policy','MAP_IF_CONFIDENT_ELSE_MAX_EXPECTED_INFORMATION_GAIN'),d.get('origin','FAILURE_DERIVED_ACTIVE_INFORMATION_GAIN'))

def main():
    r=make_request()
    # previous bounded probabilistic layer explicitly supports only 2 hypotheses / 1 probe
    old=FrontierPortfolioV5(); old_best,old_n=old.search(r.task.train)
    baseline={'previous_portfolio_exact_schema_found':bool(old_best is not None and old_best.exact==1.0),'generated':old_n,'best_exact':None if old_best is None else old_best.exact}
    if DB.exists():DB.unlink()
    orig=unified_mod.FailureDrivenSchemaInducer;unified_mod.FailureDrivenSchemaInducer=FrontierPortfolioV6
    try:
        k=UnifiedYADOKernelV30RC6R6SchemaAdaptation(str(DB))
        try:
            good=k.run_causal_cycle(r); abl=k.run_causal_cycle(r,ablate={'MECHANISM'});snap=k.unified_snapshot()
        finally:k.close()
    finally:unified_mod.FailureDrivenSchemaInducer=orig
    m=mechanism(good);s=m.get('schema') or {};obj=schema_obj(s);trace=[]
    if obj:_,trace=ActiveInformationGainInducer.execute_with_trace(obj,r.task.live_input)
    passed=good.get('cycle_success') is True and obj is not None and good.get('blind_score')==1.0 and good.get('ablation_score')==0.0 and good.get('restore_score')==1.0 and abl.get('cycle_success') is False
    rep={
      'schema':'yado.stateful_frontier_repair.cycle12.v1','status':'SHADOW_SUPPORTED_ACTIVE_INFORMATION_GAIN' if passed and not baseline['previous_portfolio_exact_schema_found'] else 'WITHHOLD',
      'baseline':baseline,
      'failure_diagnosis':'PASSIVE_POSTERIOR_UPDATE_DOES_NOT_CHOOSE_WHICH_EVIDENCE_TO_ACQUIRE_NEXT',
      'cycle':{'cycle_id':good.get('cycle_id'),'cycle_success':good.get('cycle_success'),'family':s.get('family'),'selected_priors':s.get('priors'),'selected_likelihoods':s.get('likelihoods'),'selected_threshold':s.get('confidence_threshold'),'generated_candidates':m.get('generated_candidates'),'train_exact':m.get('train_exact'),'blind':good.get('blind_score'),'ablation':good.get('ablation_score'),'restore':good.get('restore_score'),'live_output':good.get('live_output'),'expected_live':good.get('expected_live'),'live_trace':trace,'learning_closed':good.get('learning_closed'),'mechanism_ablation_cycle_success':abl.get('cycle_success')},
      'hidden_benchmark_not_supplied_to_learner':asdict(hidden_schema()),'fresh_used_for_selection':False,'observation_snapshot':snap,
      'claim_boundary':{'canonical_durable_head_modified':False,'generic_bayes_updater_host_supplied':True,'entropy_information_gain_calculator_host_supplied':True,'parameter_search_host_supplied':True,'specific_likelihoods_threshold_and_probe_choices_data_derived_from_revealed_train':True,'general_active_learning_or_pomdp_planning_proven':False}
    }
    REPORT.write_text(json.dumps(rep,ensure_ascii=False,indent=2));print(json.dumps(rep,ensure_ascii=False,indent=2));return 0 if rep['status'].startswith('SHADOW_SUPPORTED') else 2
if __name__=='__main__':raise SystemExit(main())
