from __future__ import annotations
from pathlib import Path
import hashlib, json, os, random, sys

ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(PKG))

from yado_core_v2_1 import BoundedRuleSandbox
from yado_conjunctive_rule_inducer_v1 import ConjunctiveRuleInducerV1, program_acc, canonical_program

OUT=ROOT/'g1_candidate_s2_bounded_genesis_v2'
OUT.mkdir(exist_ok=True)

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o): return hashlib.sha256(canon(o).encode()).hexdigest()

def make_cases(seed,n,law):
    r=random.Random(seed); out=[]
    for i in range(n):
        x=law(r,True)
        out.append({'input':x[0],'expected':x[1]})
    return out

# G1 THINKING: counterexample-driven boundary policy.
SAFE_PLAN=['OBSERVE','RESEARCH','HYPOTHESIZE','SIMULATE','DIAGNOSE','TEST','VERIFY','ROLLBACK','COMMIT']
RISK_PLAN=['OBSERVE','DIAGNOSE','ROLLBACK','RESEARCH','HYPOTHESIZE','SIMULATE','TEST','VERIFY','COMMIT']
def thinking_sample(r,_):
    x={
      'integrity_risk_high':bool(r.getrandbits(1)),
      'uncertainty_high':bool(r.getrandbits(1)),
      'novelty_high':bool(r.getrandbits(1)),
      'fresh_nonce':r.randint(0,100000),
    }
    y=RISK_PLAN if x['integrity_risk_high'] and x['uncertainty_high'] else SAFE_PLAN
    return x,y

# G1 INTELLIGENCE is composed from three bounded policies so each causal condition is explicit.
def safety_sample(r,_):
    x={
      'integrity_ok':bool(r.getrandbits(1)),
      'rollback_ok':bool(r.getrandbits(1)),
      'fresh_nonce':r.randint(0,100000),
    }
    y='CONTINUE' if x['integrity_ok'] and x['rollback_ok'] else 'ROLLBACK'
    return x,y

def evidence_sample(r,_):
    x={'evidence_complete':bool(r.getrandbits(1)),'fresh_nonce':r.randint(0,100000)}
    y='CONTINUE' if x['evidence_complete'] else 'RESEARCH_MORE'
    return x,y

def promotion_sample(r,_):
    x={
      'blind_ok':bool(r.getrandbits(1)),
      'ablation_ok':bool(r.getrandbits(1)),
      'transfer_ok':bool(r.getrandbits(1)),
      'fresh_nonce':r.randint(0,100000),
    }
    y='PROMOTE_CANDIDATE' if x['blind_ok'] and x['ablation_ok'] and x['transfer_ok'] else 'SHADOW_REPAIR'
    return x,y

SPECS={
  'THINKING':thinking_sample,
  'INTELLIGENCE_SAFETY':safety_sample,
  'INTELLIGENCE_EVIDENCE':evidence_sample,
  'INTELLIGENCE_PROMOTION':promotion_sample,
}
programs={}; scores={}
for i,(name,sampler) in enumerate(SPECS.items()):
    train=make_cases(120000+i*100,180,sampler)
    val=make_cases(120010+i*100,90,sampler)
    blind=make_cases(120020+i*100,240,sampler)
    p=ConjunctiveRuleInducerV1.synthesize(
        f'G1_{name}_BOUNDED_V2',
        'THINKING' if name=='THINKING' else 'INTELLIGENCE',
        train,min_support=3,max_rules=12
    )
    sc={
      'train':program_acc(p,train),
      'validation':program_acc(p,val),
      'fresh_blind':program_acc(p,blind),
      'ablation':program_acc(p,blind,ablated=True),
      'restore':program_acc(p,blind),
    }
    sc['causal_drop']=sc['fresh_blind']-sc['ablation']
    programs[name]=p; scores[name]=sc

# Independent composed INTELLIGENCE blind gate.
r=random.Random(130001)
ok=0; n=480
def intel_expected(x):
    if not x['integrity_ok'] or not x['rollback_ok']: return 'ROLLBACK'
    if not x['evidence_complete']: return 'RESEARCH_MORE'
    if x['blind_ok'] and x['ablation_ok'] and x['transfer_ok']: return 'PROMOTE_CANDIDATE'
    return 'SHADOW_REPAIR'
def intel_execute(x,ablated=False):
    s=BoundedRuleSandbox.execute(programs['INTELLIGENCE_SAFETY'],x,ablated=ablated)
    if s=='ROLLBACK': return 'ROLLBACK'
    e=BoundedRuleSandbox.execute(programs['INTELLIGENCE_EVIDENCE'],x,ablated=ablated)
    if e=='RESEARCH_MORE': return 'RESEARCH_MORE'
    return BoundedRuleSandbox.execute(programs['INTELLIGENCE_PROMOTION'],x,ablated=ablated)

ab_ok=0
for i in range(n):
    x={
      'integrity_ok':bool(r.getrandbits(1)),
      'rollback_ok':bool(r.getrandbits(1)),
      'evidence_complete':bool(r.getrandbits(1)),
      'blind_ok':bool(r.getrandbits(1)),
      'ablation_ok':bool(r.getrandbits(1)),
      'transfer_ok':bool(r.getrandbits(1)),
      'fresh_nonce':r.randint(100001,999999),
    }
    y=intel_expected(x)
    ok += intel_execute(x)==y
    ab_ok += intel_execute(x,ablated=True)==y
composed_fresh=ok/n
composed_ablation=ab_ok/n
composed_drop=composed_fresh-composed_ablation

admission=all([
    scores['THINKING']['validation']>=.99,
    scores['THINKING']['fresh_blind']>=.99,
    scores['THINKING']['causal_drop']>=.10,
    scores['INTELLIGENCE_SAFETY']['fresh_blind']>=.99,
    scores['INTELLIGENCE_EVIDENCE']['fresh_blind']>=.99,
    scores['INTELLIGENCE_PROMOTION']['fresh_blind']>=.99,
    scores['INTELLIGENCE_PROMOTION']['causal_drop']>=.10,
    composed_fresh>=.99,
    composed_drop>=.08,
])

bundle={
  'schema':'yado.g1_candidate_s2.bounded_bundle.v2',
  'candidate_generation_id':'G1_CANDIDATE_S2',
  'builder_revision':'BOUNDED_COUNTEREXAMPLE_GENESIS_V2',
  'parent_generation_id':'G0_RC8_V36',
  'admission_pass':admission,
  'components':{
    'THINKING':{
      'origin':'INHERITED_CONJUNCTIVE_RULE_INDUCTION_RECOMPOSED_FOR_G1',
      'program':canonical_program(programs['THINKING']),
      'safe_plan':SAFE_PLAN,'risk_plan':RISK_PLAN,
    },
    'INTELLIGENCE':{
      'origin':'INHERITED_CONJUNCTIVE_RULE_INDUCTION_COMPOSED_GATES_FOR_G1',
      'safety_program':canonical_program(programs['INTELLIGENCE_SAFETY']),
      'evidence_program':canonical_program(programs['INTELLIGENCE_EVIDENCE']),
      'promotion_program':canonical_program(programs['INTELLIGENCE_PROMOTION']),
    },
  },
  'scores':scores,
  'composed_intelligence':{
    'fresh_blind':composed_fresh,
    'ablation':composed_ablation,
    'causal_drop':composed_drop,
  },
  'preserved_open_deficits':[
    'THINKING_BOUNDARY_REASONING',
    'INTELLIGENCE_BOUNDARY_REASONING',
    'REPRESENTATION_INVARIANCE',
    'ACCESS_CONTROL_HIGHER_EXPRESSIVENESS_COUNTEREXAMPLE',
    'BUDGET_AWARE_SEARCH_AND_STAGED_ESCALATION',
  ],
  'canonical_mutation':False,
  'promotion_applied':False,
}
bundle['bundle_digest']=h(bundle)
(ROOT/'yado_g1_candidate_s2_bounded_bundle_v2.json').write_text(json.dumps(bundle,indent=2,sort_keys=True,default=str)+'\n')

report={
  'schema':'yado.g1_candidate_s2.bounded_genesis.v2',
  'status':'PASS_G1_CANDIDATE_S2_BOUNDED_GENESIS_V2' if admission else 'WITHHOLD_G1_CANDIDATE_S2_BOUNDED_GENESIS_V2',
  'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),
  'candidate_generation_id':'G1_CANDIDATE_S2',
  'builder_revision':'BOUNDED_COUNTEREXAMPLE_GENESIS_V2',
  'reason_for_revision':'PRIOR_HEAVY_S2_BUILDER_RUN_33302716666_DID_NOT_COMPLETE_AND_WAS_CANCELLED; REPLACED_WITH_BOUNDED_COMPOSITION',
  'scores':scores,
  'composed_intelligence':bundle['composed_intelligence'],
  'bundle_digest':bundle['bundle_digest'],
  'canonical_mutation':False,'promotion_applied':False,
  'next_required_capability':'RUN_INHERITED_SHADOW_CAPABILITY_INSIDE_G1_CANDIDATE_V2' if admission else 'REVISE_BOUNDED_G1_BUILDER',
  'semantic_boundary':'BOUNDED SYMBOLIC G1 CANDIDATE BUILT FROM INHERITED RULE-INDUCTION CAPABILITY; THIS REPLACES AN UNBOUNDED/TOO-EXPENSIVE CANDIDATE BUILD PATH; NOT CANONICAL PROMOTION, AGI, OR SUBJECTIVE CONSCIOUSNESS PROOF',
}
report['receipt_sha256']=h(report)
(ROOT/'yado_g1_candidate_s2_bounded_genesis_v2_receipt.json').write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps({
  'status':report['status'],
  'thinking_fresh_blind':scores['THINKING']['fresh_blind'],
  'thinking_causal_drop':scores['THINKING']['causal_drop'],
  'intelligence_composed_fresh_blind':composed_fresh,
  'intelligence_composed_causal_drop':composed_drop,
  'bundle_digest':bundle['bundle_digest'],
  'next_required_capability':report['next_required_capability'],
},indent=2,sort_keys=True))
if not admission:
    raise SystemExit('G1_BOUNDED_GENESIS_WITHHELD')
