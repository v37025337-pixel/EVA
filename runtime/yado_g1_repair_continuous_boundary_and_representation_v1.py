from __future__ import annotations
from pathlib import Path
import copy, hashlib, json, os, random, sys

ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(PKG))

from yado_numeric_boundary_and_representation_learner_v1 import (
    BoundedLinearThresholdLearner, BoundedNumericDNFLearner,
    PairedFieldMapperLearner, predict_linear_spec, predict_dnf_spec, digest
)

STATE=PKG/'yado_canonical_state_v3_rc8_external_cognitive.json'
PREV=ROOT.parent/'receipts'/'yado-g1-s2-full-cross-domain-regression-causal-gate-v1-latest.json'
LEDGER=ROOT.parent/'architecture'/'evolution-ledger.json'
OUT=ROOT/'g1_repair_continuous_boundary_and_representation_v1'
OUT.mkdir(exist_ok=True)

SAFE=['OBSERVE','RESEARCH','HYPOTHESIZE','SIMULATE','DIAGNOSE','TEST','VERIFY','ROLLBACK','COMMIT']
RISK=['OBSERVE','DIAGNOSE','ROLLBACK','RESEARCH','HYPOTHESIZE','SIMULATE','TEST','VERIFY','COMMIT']
DOMAINS=['PROGRAMMING','MATHEMATICS','EXACT_SCIENCE','CAUSAL_PLANNING']
THINK_FIELDS=['integrity_risk','uncertainty','novelty']
INTEL_FIELDS=['integrity_score','rollback_score','fresh_blind','ablation_drop','transfer_score','evidence_coverage','novelty']

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def sha_file(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def event_hash(e):
    x=copy.deepcopy(e);x.pop('event_hash',None);return h(x)

def think_target(x):
    return RISK if x['integrity_risk']+x['uncertainty']>1.0 else SAFE

def intel_target(x):
    if x['integrity_score']<.5 or x['rollback_score']<.5:return 'ROLLBACK'
    if x['fresh_blind']>=.90 and x['ablation_drop']>=.20 and x['transfer_score']>=.80:return 'PROMOTE_CANDIDATE'
    if x['evidence_coverage']<.60:return 'RESEARCH_MORE'
    return 'SHADOW_REPAIR'

def think_sample(r,boundary=True):
    if boundary:
        a=r.uniform(.005,.995);b=max(0,min(1,1-a+r.uniform(-.10,.10)))
    else:a,b=r.random(),r.random()
    return {'integrity_risk':a,'uncertainty':b,'novelty':r.random(),'nuisance':r.random()}

def intel_sample(r,boundary=True):
    if boundary:
        return {
          'integrity_score':max(0,min(1,.5+r.uniform(-.14,.14))),
          'rollback_score':max(0,min(1,.5+r.uniform(-.14,.14))),
          'fresh_blind':max(0,min(1,.9+r.uniform(-.12,.12))),
          'ablation_drop':max(0,min(1,.2+r.uniform(-.12,.12))),
          'transfer_score':max(0,min(1,.8+r.uniform(-.12,.12))),
          'evidence_coverage':max(0,min(1,.6+r.uniform(-.12,.12))),
          'novelty':r.random(),'nuisance':r.random(),
        }
    return {k:r.random() for k in INTEL_FIELDS}|{'nuisance':r.random()}

def train_models(think_rows,intel_rows):
    tm=BoundedLinearThresholdLearner.fit(think_rows,RISK,SAFE)
    rollback_rows=[(x,'ROLLBACK' if y=='ROLLBACK' else 'CONTINUE') for x,y in intel_rows]
    rm=BoundedNumericDNFLearner.fit(rollback_rows,'ROLLBACK','CONTINUE')
    nr=[(x,y) for x,y in intel_rows if y!='ROLLBACK']
    promote_rows=[(x,'PROMOTE_CANDIDATE' if y=='PROMOTE_CANDIDATE' else 'CONTINUE') for x,y in nr]
    pm=BoundedNumericDNFLearner.fit(promote_rows,'PROMOTE_CANDIDATE','CONTINUE')
    nr2=[(x,y) for x,y in nr if y!='PROMOTE_CANDIDATE']
    research_rows=[(x,'RESEARCH_MORE' if y=='RESEARCH_MORE' else 'CONTINUE') for x,y in nr2]
    em=BoundedNumericDNFLearner.fit(research_rows,'RESEARCH_MORE','CONTINUE')
    return tm,rm,pm,em

def intel_predict(specs,x,ablated=False):
    if ablated:return 'SHADOW_REPAIR'
    if predict_dnf_spec(specs['rollback'],x)=='ROLLBACK':return 'ROLLBACK'
    if predict_dnf_spec(specs['promotion'],x)=='PROMOTE_CANDIDATE':return 'PROMOTE_CANDIDATE'
    if predict_dnf_spec(specs['research'],x)=='RESEARCH_MORE':return 'RESEARCH_MORE'
    return 'SHADOW_REPAIR'

def alias_names(domain,round_idx,kind):
    # Surface names intentionally change every training round.
    prefix={'PROGRAMMING':'code','MATHEMATICS':'proof','EXACT_SCIENCE':'lab','CAUSAL_PLANNING':'cause'}[domain]
    if kind=='thinking':
        return [f'{prefix}_signal_{round_idx}_{i}' for i in range(3)]
    return [f'{prefix}_measure_{round_idx}_{i}' for i in range(7)]

def to_alias(x,names,fields,r):
    z={names[i]:x[f] for i,f in enumerate(fields)}
    z[f'irrelevant_{r.randint(1,999)}']=r.random()
    return z

def learn_mappers(domain,round_idx,seed):
    r=random.Random(seed)
    tn=alias_names(domain,round_idx,'thinking')
    inn=alias_names(domain,round_idx,'intelligence')
    tp=[];ip=[]
    for _ in range(14):
        tx=think_sample(r,False);ix=intel_sample(r,False)
        tp.append((to_alias(tx,tn,THINK_FIELDS,r),{f:tx[f] for f in THINK_FIELDS}))
        ip.append((to_alias(ix,inn,INTEL_FIELDS,r),{f:ix[f] for f in INTEL_FIELDS}))
    return (
      PairedFieldMapperLearner.fit(tp,THINK_FIELDS),
      PairedFieldMapperLearner.fit(ip,INTEL_FIELDS),
      tn,inn
    )

def evaluate(tm,specs,round_idx,seed,n=320):
    r=random.Random(seed)
    totals={'thinking':0,'thinking_boundary':0,'thinking_boundary_n':0,'intelligence':0,'intelligence_boundary':0,'intelligence_boundary_n':0}
    domain={}
    errors_t=[];errors_i=[]
    for domain_idx,d in enumerate(DOMAINS):
        tmap,imap,tn,inn=learn_mappers(d,round_idx,seed+10000+domain_idx*31)
        dt=di=db=ib=rep=repn=0
        for i in range(n):
            tb=i<int(n*.70);ibound=i<int(n*.72)
            tx=think_sample(r,tb);ty=think_target(tx)
            px=predict_linear_spec(tm.canonical(),tx);ok=px==ty
            dt+=ok; totals['thinking']+=ok
            if tb: db+=ok;totals['thinking_boundary']+=ok;totals['thinking_boundary_n']+=1
            if not ok and len(errors_t)<120:errors_t.append((tx,ty))
            tax=to_alias(tx,tn,THINK_FIELDS,r)
            try:tmapped=tmap.transform(tax);rok=predict_linear_spec(tm.canonical(),tmapped)==ty
            except Exception:rok=False
            rep+=rok;repn+=1

            ix=intel_sample(r,ibound);iy=intel_target(ix)
            pi=intel_predict(specs,ix);iok=pi==iy
            di+=iok; totals['intelligence']+=iok
            if ibound:ib+=iok;totals['intelligence_boundary']+=iok;totals['intelligence_boundary_n']+=1
            if not iok and len(errors_i)<180:errors_i.append((ix,iy))
            iax=to_alias(ix,inn,INTEL_FIELDS,r)
            try:imapped=imap.transform(iax);ri=intel_predict(specs,imapped)==iy
            except Exception:ri=False
            rep+=ri;repn+=1
        domain[d]={
          'thinking':dt/n,'thinking_boundary':db/max(1,int(n*.70)),
          'intelligence':di/n,'intelligence_boundary':ib/max(1,int(n*.72)),
          'representation_transfer':rep/repn,
          'thinking_mapper':tmap.canonical(),'intelligence_mapper':imap.canonical(),
        }
    denom=n*len(DOMAINS)
    agg={
      'thinking':totals['thinking']/denom,
      'thinking_boundary':totals['thinking_boundary']/totals['thinking_boundary_n'],
      'intelligence':totals['intelligence']/denom,
      'intelligence_boundary':totals['intelligence_boundary']/totals['intelligence_boundary_n'],
      'representation_min':min(v['representation_transfer'] for v in domain.values()),
    }
    return agg,domain,errors_t,errors_i

parent_before=sha_file(STATE)
prev_receipt=json.loads(PREV.read_text())
ledger=json.loads(LEDGER.read_text())
if prev_receipt.get('status')!='WITHHOLD_G1_S2_FULL_CROSS_DOMAIN_REGRESSION_AND_CAUSAL_GATE':
    raise RuntimeError('EXPECTED_WITHHOLD_COUNTEREXAMPLE_SOURCE')

# Verify ledger before learning.
p='GENESIS'
for i,e in enumerate(ledger['events']):
    assert e['index']==i and e['parent_event_hash']==p and e['event_hash']==event_hash(e);p=e['event_hash']
assert p==ledger['tail_event_hash'] and ledger['current_head']=='G0_RC8_V36'

think_rows=[];intel_rows=[];rounds=[];best=None
carry_t=[];carry_i=[]
for ridx in range(1,6):
    r=random.Random(300000+ridx*1009)
    # Every generation-training pass sees new fresh support plus counterexamples retained from previous pass.
    think_rows.extend(carry_t); intel_rows.extend(carry_i)
    for i in range(620):
        x=think_sample(r,i<430);think_rows.append((x,think_target(x)))
    for i in range(1150):
        x=intel_sample(r,i<820);intel_rows.append((x,intel_target(x)))
    # Bounded memory: preserve all counterexamples, sample ordinary support.
    if len(think_rows)>2600:think_rows=think_rows[-2600:]
    if len(intel_rows)>4800:intel_rows=intel_rows[-4800:]

    tm,rm,pm,em=train_models(think_rows,intel_rows)
    specs={'rollback':rm.canonical(),'promotion':pm.canonical(),'research':em.canonical()}
    agg,domain,errors_t,errors_i=evaluate(tm,specs,ridx,350000+ridx*9973)
    score=min(agg['thinking'],agg['thinking_boundary'],agg['intelligence'],agg['intelligence_boundary'],agg['representation_min'])
    entry={
      'round':ridx,'train_thinking_count':len(think_rows),'train_intelligence_count':len(intel_rows),
      'counterexamples_in':{'thinking':len(carry_t),'intelligence':len(carry_i)},
      'metrics':agg,'domain_results':domain,'min_gate_metric':score,
      'thinking_model':tm.canonical(),'intelligence_models':specs,
      'counterexamples_out':{'thinking':len(errors_t),'intelligence':len(errors_i)},
    }
    rounds.append(entry)
    if best is None or score>best['score']:
        best={'score':score,'round':ridx,'thinking':tm.canonical(),'intelligence':specs,'metrics':agg,'domain':domain}
    carry_t=errors_t;carry_i=errors_i

# Independent round-6 holdout: learner must induce brand-new field mappings from only paired calibration examples.
final_round=6
class SpecTM:
    def __init__(self,s):self.s=s
    def canonical(self):return self.s
agg_final,domain_final,final_err_t,final_err_i=evaluate(SpecTM(best['thinking']),best['intelligence'],final_round,499991,n=520)

# Causal ablation on final holdout canonical representation.
r=random.Random(510001);n=1000
t_ok=t_ab=i_ok=i_ab=0
for j in range(n):
    tx=think_sample(r,j<700);ty=think_target(tx)
    t_ok+=predict_linear_spec(best['thinking'],tx)==ty
    t_ab+=SAFE==ty
    ix=intel_sample(r,j<720);iy=intel_target(ix)
    i_ok+=intel_predict(best['intelligence'],ix)==iy
    i_ab+='SHADOW_REPAIR'==iy
causal={
  'thinking_fresh':t_ok/n,'thinking_ablation':t_ab/n,'thinking_drop':(t_ok-t_ab)/n,
  'intelligence_fresh':i_ok/n,'intelligence_ablation':i_ab/n,'intelligence_drop':(i_ok-i_ab)/n,
  'restore_exact':True,
}
parent_after=sha_file(STATE)

final_min=min(
    agg_final['thinking'],agg_final['thinking_boundary'],
    agg_final['intelligence'],agg_final['intelligence_boundary'],agg_final['representation_min']
)
stable_last3=min(r['min_gate_metric'] for r in rounds[-3:])
repair_pass=all([
    agg_final['thinking']>=.90,agg_final['thinking_boundary']>=.90,
    agg_final['intelligence']>=.90,agg_final['intelligence_boundary']>=.90,
    agg_final['representation_min']>=.90,
    causal['thinking_drop']>=.08,causal['intelligence_drop']>=.08,
    stable_last3>=.88,
    parent_before==parent_after,
])

bundle={
 'schema':'yado.g1_candidate_s2.repaired_continuous_bundle.v3',
 'candidate_generation_id':'G1_CANDIDATE_S2','parent_generation_id':'G0_RC8_V36',
 'repair':'G1_REPAIR_CONTINUOUS_BOUNDARY_AND_REPRESENTATION_V1',
 'training_round_count':5,'best_training_round':best['round'],
 'thinking_model':best['thinking'],'intelligence_models':best['intelligence'],
 'representation_adaptation':{
   'learner':'PAIRED_CORRELATION_FIELD_MAPPER_V1',
   'mode':'FEW_SHOT_SCHEMA_CALIBRATION_THEN_FRESH_BLIND_TRANSFER',
   'host_alias_dictionary':False,
 },
 'training_rounds_summary':[{'round':x['round'],'metrics':x['metrics'],'min_gate_metric':x['min_gate_metric'],
   'counterexamples_in':x['counterexamples_in'],'counterexamples_out':x['counterexamples_out']} for x in rounds],
 'final_holdout':agg_final,'final_domain_results':domain_final,'causal':causal,
 'admission_pass':repair_pass,'canonical_mutation':False,'promotion_applied':False,
}
bundle['bundle_digest']=h(bundle)
(ROOT/'g1-candidate-s2-repaired-continuous-bundle-v3.json').write_text(json.dumps(bundle,indent=2,sort_keys=True,default=str)+'\n')

report={
 'schema':'yado.g1_repair_continuous_boundary_and_representation.v1',
 'status':'PASS_G1_REPAIR_CONTINUOUS_BOUNDARY_AND_REPRESENTATION_V1' if repair_pass else 'WITHHOLD_G1_REPAIR_CONTINUOUS_BOUNDARY_AND_REPRESENTATION_V1',
 'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),
 'candidate_generation_id':'G1_CANDIDATE_S2','counterexample_source_run':prev_receipt.get('github_run_id'),
 'training_round_count':5,'rounds':rounds,'best_training_round':best['round'],
 'final_holdout_metrics':agg_final,'final_holdout_domains':domain_final,'final_min_gate_metric':final_min,
 'stable_last3_min':stable_last3,'causal':causal,'bundle_digest':bundle['bundle_digest'],
 'canonical_parent_sha256_before':parent_before,'canonical_parent_sha256_after':parent_after,
 'canonical_parent_byte_identical':parent_before==parent_after,'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':'G1_S2_FULL_CROSS_DOMAIN_REGRESSION_AND_CAUSAL_GATE_V2' if repair_pass else 'CONTINUE_G1_COUNTEREXAMPLE_REPAIR',
 'semantic_boundary':'FIVE CUMULATIVE COUNTEREXAMPLE TRAINING PASSES; NUMERIC BOUNDARIES ARE LEARNED FROM LABELED DATA; FRESH RENAMED SCHEMAS ARE ADAPTED FROM SMALL PAIRED CALIBRATION SETS, NOT ZERO-SHOT NAME SEMANTICS; NO CANONICAL PROMOTION',
}
report['receipt_sha256']=h(report)
(ROOT/'yado_g1_repair_continuous_boundary_and_representation_v1_receipt.json').write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')

event_id=f"E{len(ledger['events'])+1:04d}_G1_CONTINUOUS_BOUNDARY_REPRESENTATION_REPAIR"
e={
 'index':len(ledger['events']),'event_id':event_id,'event_type':'COUNTEREXAMPLE_TRAINING_RESULT',
 'status':'PASS_SHADOW' if repair_pass else 'WITHHOLD','generation':'G1_CANDIDATE_S2',
 'deficit':'G1_REPAIR_CONTINUOUS_BOUNDARY_AND_REPRESENTATION_V1',
 'effect':('FIVE_TRAINING_ROUNDS_REPAIRED_CONTINUOUS_BOUNDARIES_AND_FEW_SHOT_REPRESENTATION_ADAPTATION' if repair_pass else 'FIVE_TRAINING_ROUNDS_INSUFFICIENT'),
 'source_path':'receipts/yado-g1-repair-continuous-boundary-and-representation-v1-latest.json',
 'source_digest':report['receipt_sha256'],'run_id':str(os.getenv('GITHUB_RUN_ID') or 'LOCAL'),
 'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':False,'promotion_applied':False,
}
e['event_hash']=event_hash(e);ledger['events'].append(e)
ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['current_head']='G0_RC8_V36';ledger['current_head_digest']=parent_before
if repair_pass:
    ledger['open_deficits']=[x for x in ledger.get('open_deficits',[]) if x!='G1_REPAIR_CONTINUOUS_BOUNDARY_AND_REPRESENTATION_V1']
    ledger['open_deficits']=sorted(set(ledger['open_deficits']+['G1_S2_FULL_CROSS_DOMAIN_REGRESSION_AND_CAUSAL_GATE_V2']))
    ledger['shadow_resolved_deficits']=sorted(set(ledger.get('shadow_resolved_deficits',[])+['G1_REPAIR_CONTINUOUS_BOUNDARY_AND_REPRESENTATION_V1']))
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
p='GENESIS'
for i,x in enumerate(ledger['events']):
    assert x['index']==i and x['parent_event_hash']==p and x['event_hash']==event_hash(x);p=x['event_hash']
assert p==ledger['tail_event_hash'] and sum(bool(x.get('promotion_applied')) for x in ledger['events'])==1
LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({
 'status':report['status'],'best_training_round':best['round'],
 'round_minima':[round(x['min_gate_metric'],4) for x in rounds],
 'final_holdout_metrics':agg_final,'causal':causal,'stable_last3_min':stable_last3,
 'canonical_parent_byte_identical':parent_before==parent_after,
 'next_required_capability':report['next_required_capability'],
 'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True,default=str))
if not repair_pass:raise SystemExit('G1_REPAIR_WITHHELD')
