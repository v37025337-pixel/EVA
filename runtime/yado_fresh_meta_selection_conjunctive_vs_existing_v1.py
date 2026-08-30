from __future__ import annotations
from pathlib import Path
import hashlib,json,os,random,sys,time

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(PKG))

from yado_core_v2_1 import RuleProgramSynthesizer,BoundedRuleSandbox
from yado_conjunctive_rule_inducer_v1 import ConjunctiveRuleInducerV1,program_acc,canonical_program

OUT=ROOT/'fresh_meta_selection_conjunctive_vs_existing_v1'
OUT.mkdir(exist_ok=True)

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)

def make_cases(seed,n,fields,values,law):
    r=random.Random(seed);out=[]
    for _ in range(n):
        x={f:r.choice(values[f]) for f in fields}
        x['noise_a']=r.randint(0,11);x['noise_b']=r.choice(['X','Y','Z'])
        out.append({'input':x,'expected':law(x)})
    return out

TASKS={}

# Unary: existing bank should be sufficient and preferred on tie.
fields=['verified','tier']; vals={'verified':[True,False],'tier':['A','B']}
TASKS['UNARY_SANITY']=(fields,vals,lambda x:'ACCEPT' if x['verified'] else 'HOLD')

# Binary conjunction.
fields=['checksum_ok','signature_ok','mode']; vals={'checksum_ok':[True,False],'signature_ok':[True,False],'mode':['FAST','SAFE']}
TASKS['ARTIFACT_INTEGRITY']=(fields,vals,lambda x:'LOAD' if x['checksum_ok'] and x['signature_ok'] else 'REJECT')

# Ternary conjunction.
fields=['quorum','leader_fresh','term_match','load']; vals={'quorum':[True,False],'leader_fresh':[True,False],'term_match':[True,False],'load':['LOW','HIGH']}
TASKS['DISTRIBUTED_COMMIT']=(fields,vals,lambda x:'COMMIT' if x['quorum'] and x['leader_fresh'] and x['term_match'] else 'WAIT')

# Multi-output conjunctions.
fields=['calibrated','reference_ok','drift','temperature']; vals={'calibrated':[True,False],'reference_ok':[True,False],'drift':['LOW','HIGH'],'temperature':['NOMINAL','EXTREME']}
def law_cal(x):
    if x['calibrated'] and x['reference_ok'] and x['drift']=='LOW': return 'TRUST'
    if x['drift']=='HIGH' and x['temperature']=='EXTREME': return 'RECALIBRATE'
    return 'CHECK'
TASKS['INSTRUMENT_CALIBRATION']=(fields,vals,law_cal)

# Provenance.
fields=['source_signed','transform_logged','schema_match','late_data']; vals={'source_signed':[True,False],'transform_logged':[True,False],'schema_match':[True,False],'late_data':[True,False]}
def law_data(x):
    if x['source_signed'] and x['transform_logged'] and x['schema_match']: return 'PUBLISH'
    if not x['schema_match'] and x['late_data']: return 'QUARANTINE'
    return 'REVIEW'
TASKS['DATA_PROVENANCE']=(fields,vals,law_data)

# Bounded deployment policy.
fields=['tests_green','rollback_ready','blast_radius','change_kind']; vals={'tests_green':[True,False],'rollback_ready':[True,False],'blast_radius':['LOW','HIGH'],'change_kind':['CONFIG','CODE']}
def law_deploy(x):
    if x['tests_green'] and x['rollback_ready'] and x['blast_radius']=='LOW': return 'DEPLOY'
    if x['change_kind']=='CONFIG' and x['rollback_ready']: return 'CANARY'
    return 'HOLD'
TASKS['DEPLOYMENT_POLICY']=(fields,vals,law_deploy)

def complexity(p):
    rules=getattr(p,'rules',[])
    return len(rules)+sum(len(getattr(r,'predicates',[])) for r in rules)

results={}
all_blind_ok=True
for i,(name,(fields,values,law)) in enumerate(TASKS.items()):
    train=make_cases(71000+i*100,360,fields,values,law)
    val=make_cases(72000+i*100,180,fields,values,law)
    blind=make_cases(73000+i*100,480,fields,values,law)

    candidates=[]
    # Existing bank.
    try:
        t=time.perf_counter()
        old=RuleProgramSynthesizer.synthesize(name,'LOGIC',train,min_support=2)
        sec=time.perf_counter()-t
        candidates.append({
          'family':'EXISTING_RULE_PROGRAM_SYNTHESIZER','program':old,
          'validation':program_acc(old,val),'complexity':complexity(old),'seconds':sec,
        })
    except Exception as e:
        candidates.append({
          'family':'EXISTING_RULE_PROGRAM_SYNTHESIZER','program':None,
          'validation':0.0,'complexity':10**9,'seconds':0.0,'error':repr(e),
        })

    # New shadow bank.
    try:
        t=time.perf_counter()
        new=ConjunctiveRuleInducerV1.synthesize(name,'LOGIC',train,min_support=2,max_rules=12)
        sec=time.perf_counter()-t
        candidates.append({
          'family':'CONJUNCTIVE_RULE_INDUCTION','program':new,
          'validation':program_acc(new,val),'complexity':complexity(new),'seconds':sec,
        })
    except Exception as e:
        candidates.append({
          'family':'CONJUNCTIVE_RULE_INDUCTION','program':None,
          'validation':0.0,'complexity':10**9,'seconds':0.0,'error':repr(e),
        })

    # Selection uses validation only. Exact tie -> lower complexity; exact tie again -> existing bank.
    candidates.sort(key=lambda c:(c['validation'],-c['complexity'],c['family']=='EXISTING_RULE_PROGRAM_SYNTHESIZER'),reverse=True)
    sel=candidates[0]
    if sel['program'] is None:
        blind_score=0.0;ablation=0.0
    else:
        blind_score=program_acc(sel['program'],blind)
        ablation=program_acc(sel['program'],blind,ablated=True)
    all_blind_ok &= blind_score>=.97

    results[name]={
      'selected_family':sel['family'],
      'selected_validation':sel['validation'],
      'selected_complexity':sel['complexity'],
      'fresh_blind':blind_score,
      'ablation':ablation,
      'candidates':[{
        'family':c['family'],'validation':c['validation'],'complexity':c['complexity'],
        'seconds':c['seconds'],'error':c.get('error')
      } for c in candidates],
    }

selected_counts={}
for v in results.values():
    selected_counts[v['selected_family']]=selected_counts.get(v['selected_family'],0)+1

# Required behavior: existing survives the unary sanity task; conjunctive is selected
# on at least three harder tasks; all selected models transfer blind.
admission=(
    results['UNARY_SANITY']['selected_family']=='EXISTING_RULE_PROGRAM_SYNTHESIZER'
    and selected_counts.get('CONJUNCTIVE_RULE_INDUCTION',0)>=3
    and all_blind_ok
)

report={
  'schema':'yado.fresh_meta_selection.conjunctive_vs_existing.v1',
  'status':'PASS_FRESH_META_SELECTION_CONJUNCTIVE_VS_EXISTING_V1' if admission else 'WITHHOLD_FRESH_META_SELECTION_CONJUNCTIVE_VS_EXISTING_V1',
  'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),
  'selection_rule':'VALIDATION_ONLY_THEN_COMPLEXITY_THEN_EXISTING_ON_EXACT_TIE; BLIND_RESERVED_FOR_FINAL_GATE',
  'task_count':len(TASKS),'results':results,'selected_counts':selected_counts,
  'all_selected_fresh_blind_ge_0_97':all_blind_ok,
  'candidate_scope':'SHADOW_ALGORITHM_BANK',
  'canonical_mutation':False,'promotion_applied':False,
  'next_required_capability':'G0_META_SELECTION_ADMISSION_DECISION_V1' if admission else 'REVISE_SHADOW_ALGORITHM_OR_SELECTOR',
}
report['receipt_sha256']=hashlib.sha256(canon(report).encode()).hexdigest()
(ROOT/'yado_fresh_meta_selection_conjunctive_vs_existing_v1_receipt.json').write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps({
  'status':report['status'],'selected_counts':selected_counts,
  'results':{k:{q:v[q] for q in ('selected_family','selected_validation','fresh_blind','ablation')} for k,v in results.items()},
  'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True,default=str))
