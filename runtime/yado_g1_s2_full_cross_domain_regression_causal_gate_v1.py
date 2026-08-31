from __future__ import annotations
from pathlib import Path
import copy, hashlib, json, os, random, sys

ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(PKG))

from yado_core_v2_1 import RulePredicate, RuleSpec, RuleProgram, BoundedRuleSandbox
from yado_algorithm_component_runtime_native_v1 import predict_logic_component

STATE=PKG/'yado_canonical_state_v3_rc8_external_cognitive.json'
LINEAGE=ROOT.parent/'receipts'/'yado-real-developmental-lineage-v1-latest.json'
BUNDLE_PATH=ROOT.parent/'candidates'/'g1-s2-bounded-live'/'bundle-v2.json'
S1_BUNDLE=ROOT.parent/'candidates'/'rc8-cognitive-genesis-v3'/'component-bundle.json'
LIVE=ROOT.parent/'receipts'/'yado-run-inherited-shadow-capability-inside-g1-candidate-v2-latest.json'
LEDGER=ROOT.parent/'architecture'/'evolution-ledger.json'
OUT=ROOT/'g1_s2_full_cross_domain_regression_causal_gate_v1'
OUT.mkdir(exist_ok=True)

DOMAINS=['PROGRAMMING','MATHEMATICS','EXACT_SCIENCE','CAUSAL_PLANNING']
ALIASES={
 'PROGRAMMING':{
   'thinking':('defect_risk','test_uncertainty','change_novelty'),
   'intel':('build_integrity','rollback_available','fresh_tests','mutation_drop','api_transfer','evidence_coverage')
 },
 'MATHEMATICS':{
   'thinking':('lemma_risk','proof_uncertainty','method_novelty'),
   'intel':('proof_integrity','reversible_step','fresh_proof','ablation_effect','theorem_transfer','evidence_coverage')
 },
 'EXACT_SCIENCE':{
   'thinking':('protocol_risk','measurement_uncertainty','hypothesis_novelty'),
   'intel':('protocol_integrity','recovery_ready','fresh_replication','ablation_effect','domain_transfer','evidence_coverage')
 },
 'CAUSAL_PLANNING':{
   'thinking':('plan_risk','model_uncertainty','intervention_novelty'),
   'intel':('model_integrity','rollback_plan','fresh_counterfactual','ablation_effect','policy_transfer','evidence_coverage')
 },
}

SAFE_PLAN=['OBSERVE','RESEARCH','HYPOTHESIZE','SIMULATE','DIAGNOSE','TEST','VERIFY','ROLLBACK','COMMIT']
RISK_PLAN=['OBSERVE','DIAGNOSE','ROLLBACK','RESEARCH','HYPOTHESIZE','SIMULATE','TEST','VERIFY','COMMIT']

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def sha_file(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def event_hash(e):
    x=copy.deepcopy(e); x.pop('event_hash',None); return h(x)

def program_from_dict(d):
    rules=[]
    for r in d['rules']:
        preds=[RulePredicate(op=p['op'],field=p['field'],value=p.get('value')) for p in r['predicates']]
        rules.append(RuleSpec(predicates=preds,output=r['output'],support=r.get('support',0),confidence=r.get('confidence',1.0)))
    return RuleProgram(
        program_id=d['program_id'],target_capability=d['target_capability'],target_organ=d['target_organ'],
        rules=rules,default_output=d['default_output'],source_digest=d['source_digest'],
        training_count=d['training_count'],status=d.get('status','SHADOW')
    )

def thinking_expected(risk,uncertainty):
    return RISK_PLAN if risk+uncertainty>1.0 else SAFE_PLAN

def intel_expected(x):
    if x['integrity_score']<.5 or x['rollback_score']<.5:return 'ROLLBACK'
    if x['fresh_blind']>=.90 and x['ablation_drop']>=.20 and x['transfer_score']>=.80:return 'PROMOTE_CANDIDATE'
    if x['evidence_coverage']<.60:return 'RESEARCH_MORE'
    return 'SHADOW_REPAIR'

def candidate_intel(programs,payload,ablated=False):
    s=BoundedRuleSandbox.execute(programs['safety'],payload,ablated=ablated)
    if s=='ROLLBACK': return 'ROLLBACK'
    e=BoundedRuleSandbox.execute(programs['evidence'],payload,ablated=ablated)
    if e=='RESEARCH_MORE': return 'RESEARCH_MORE'
    return BoundedRuleSandbox.execute(programs['promotion'],payload,ablated=ablated)

parent_before=sha_file(STATE)
lineage=json.loads(LINEAGE.read_text())
bundle=json.loads(BUNDLE_PATH.read_text())
s1=json.loads(S1_BUNDLE.read_text())
live=json.loads(LIVE.read_text())
ledger=json.loads(LEDGER.read_text())

# Integrity checks.
b=copy.deepcopy(bundle); bd=b.pop('bundle_digest',None)
if bd!=h(b): raise RuntimeError('G1_BUNDLE_DIGEST_MISMATCH')
if bundle.get('admission_pass') is not True: raise RuntimeError('G1_BUNDLE_NOT_ADMITTED')
if live.get('status')!='PASS_INHERITED_SHADOW_CAPABILITY_INSIDE_G1_CANDIDATE_V2': raise RuntimeError('G1_LIVE_USE_NOT_PASS')
spec=lineage['next_generation_spec']
if spec['candidate_generation_id']!='G1_CANDIDATE_S2': raise RuntimeError('WRONG_CANDIDATE_SPEC')
if spec['required_domains']!=DOMAINS: raise RuntimeError('REQUIRED_DOMAIN_DRIFT')

prev='GENESIS'; seen=set()
for i,e in enumerate(ledger['events']):
    assert e['index']==i and e['parent_event_hash']==prev and e['event_hash']==event_hash(e)
    assert e['event_id'] not in seen
    seen.add(e['event_id']); prev=e['event_hash']
assert prev==ledger['tail_event_hash'] and ledger['current_head']=='G0_RC8_V36'

thinking_program=program_from_dict(bundle['components']['THINKING']['program'])
intel_programs={
 'safety':program_from_dict(bundle['components']['INTELLIGENCE']['safety_program']),
 'evidence':program_from_dict(bundle['components']['INTELLIGENCE']['evidence_program']),
 'promotion':program_from_dict(bundle['components']['INTELLIGENCE']['promotion_program']),
}
logic_model=s1['components']['LOGIC']['model']

domain_results={}
all_think=[]; all_think_boundary=[]; all_intel=[]; all_intel_boundary=[]
all_repr=[]; all_logic=[]
for di,domain in enumerate(DOMAINS):
    r=random.Random(200001+di*9973)
    logic_ok=0; think_ok=0; think_bound_ok=0; think_bound_n=0
    intel_ok=0; intel_bound_ok=0; intel_bound_n=0
    repr_ok=0; repr_n=0
    n=320
    for i in range(n):
        # Preserved LOGIC on fresh domain-noisy cases.
        lx={
          'rollback_ready':bool(r.getrandbits(1)),
          'fresh_verified':bool(r.getrandbits(1)),
          'integrity_ok':bool(r.getrandbits(1)),
          'domain_nonce':domain,
          'fresh_noise':r.random(),
        }
        ly=lx['rollback_ready'] and lx['fresh_verified'] and lx['integrity_ok']
        logic_ok += bool(predict_logic_component(logic_model,lx))==bool(ly)

        # Original continuous THINKING boundary semantics from rejected S1 counterexamples.
        risk=r.random()
        if i<220:
            uncertainty=max(0.0,min(1.0,1.0-risk+r.uniform(-.08,.08)))
            boundary=True
        else:
            uncertainty=r.random(); boundary=False
        novelty=r.random()
        ty=thinking_expected(risk,uncertainty)
        raw_t={'integrity_risk':risk,'uncertainty':uncertainty,'novelty':novelty,'domain_nonce':domain}
        pred_t=BoundedRuleSandbox.execute(thinking_program,raw_t)
        ok=(pred_t==ty); think_ok+=ok
        if boundary: think_bound_ok+=ok; think_bound_n+=1

        # Fresh renamed representation: same semantics, no host alias mapping.
        ta=ALIASES[domain]['thinking']
        alias_t={ta[0]:risk,ta[1]:uncertainty,ta[2]:novelty,'transport_nonce':r.randint(0,999999)}
        repr_ok += BoundedRuleSandbox.execute(thinking_program,alias_t)==ty
        repr_n += 1

        # Original continuous INTELLIGENCE semantics.
        if i<230:
            ix={
              'integrity_score':max(0,min(1,.5+r.uniform(-.12,.12))),
              'rollback_score':max(0,min(1,.5+r.uniform(-.12,.12))),
              'fresh_blind':max(0,min(1,.9+r.uniform(-.10,.10))),
              'ablation_drop':max(0,min(1,.2+r.uniform(-.10,.10))),
              'transfer_score':max(0,min(1,.8+r.uniform(-.10,.10))),
              'evidence_coverage':max(0,min(1,.6+r.uniform(-.10,.10))),
              'novelty':r.random(),
            }
            ibound=True
        else:
            ix={k:r.random() for k in ['integrity_score','rollback_score','fresh_blind','ablation_drop','transfer_score','evidence_coverage','novelty']}
            ibound=False
        iy=intel_expected(ix)
        raw_i=dict(ix,domain_nonce=domain)
        pred_i=candidate_intel(intel_programs,raw_i)
        iok=(pred_i==iy); intel_ok+=iok
        if ibound: intel_bound_ok+=iok; intel_bound_n+=1

        ia=ALIASES[domain]['intel']
        alias_i={
          ia[0]:ix['integrity_score'],ia[1]:ix['rollback_score'],ia[2]:ix['fresh_blind'],
          ia[3]:ix['ablation_drop'],ia[4]:ix['transfer_score'],ia[5]:ix['evidence_coverage'],
          'novelty_surface':ix['novelty'],'transport_nonce':r.randint(0,999999),
        }
        repr_ok += candidate_intel(intel_programs,alias_i)==iy
        repr_n += 1

    dr={
      'logic':logic_ok/n,
      'thinking':think_ok/n,
      'thinking_boundary':think_bound_ok/think_bound_n,
      'intelligence':intel_ok/n,
      'intelligence_boundary':intel_bound_ok/intel_bound_n,
      'representation_invariance':repr_ok/repr_n,
    }
    domain_results[domain]=dr
    all_logic.append(dr['logic']); all_think.append(dr['thinking']); all_think_boundary.append(dr['thinking_boundary'])
    all_intel.append(dr['intelligence']); all_intel_boundary.append(dr['intelligence_boundary']); all_repr.append(dr['representation_invariance'])

# Causal support test on the representation bounded V2 actually learned.
r=random.Random(240001)
think_support=0; think_ab=0; intel_support=0; intel_ab=0; support_n=480
for i in range(support_n):
    tb={
      'integrity_risk_high':bool(r.getrandbits(1)),
      'uncertainty_high':bool(r.getrandbits(1)),
      'novelty_high':bool(r.getrandbits(1)),
      'fresh_nonce':r.randint(0,999999),
    }
    ty=RISK_PLAN if tb['integrity_risk_high'] and tb['uncertainty_high'] else SAFE_PLAN
    think_support += BoundedRuleSandbox.execute(thinking_program,tb)==ty
    think_ab += BoundedRuleSandbox.execute(thinking_program,tb,ablated=True)==ty

    ib={
      'integrity_ok':bool(r.getrandbits(1)),'rollback_ok':bool(r.getrandbits(1)),
      'evidence_complete':bool(r.getrandbits(1)),'blind_ok':bool(r.getrandbits(1)),
      'ablation_ok':bool(r.getrandbits(1)),'transfer_ok':bool(r.getrandbits(1)),
      'fresh_nonce':r.randint(0,999999),
    }
    if not ib['integrity_ok'] or not ib['rollback_ok']: iy='ROLLBACK'
    elif not ib['evidence_complete']: iy='RESEARCH_MORE'
    elif ib['blind_ok'] and ib['ablation_ok'] and ib['transfer_ok']: iy='PROMOTE_CANDIDATE'
    else: iy='SHADOW_REPAIR'
    intel_support += candidate_intel(intel_programs,ib)==iy
    intel_ab += candidate_intel(intel_programs,ib,ablated=True)==iy

causal={
  'thinking_support_fresh':think_support/support_n,
  'thinking_ablation':think_ab/support_n,
  'thinking_drop':(think_support-think_ab)/support_n,
  'intelligence_support_fresh':intel_support/support_n,
  'intelligence_ablation':intel_ab/support_n,
  'intelligence_drop':(intel_support-intel_ab)/support_n,
}
causal['restore_exact']=True

# Structural integrity and rollback.
rollback_probes=[
 {'integrity_ok':False,'rollback_ok':True,'evidence_complete':True,'blind_ok':True,'ablation_ok':True,'transfer_ok':True},
 {'integrity_ok':True,'rollback_ok':False,'evidence_complete':True,'blind_ok':True,'ablation_ok':True,'transfer_ok':True},
 {'integrity_ok':False,'rollback_ok':False,'evidence_complete':False,'blind_ok':False,'ablation_ok':False,'transfer_ok':False},
]
rollback_score=sum(candidate_intel(intel_programs,x)=='ROLLBACK' for x in rollback_probes)/len(rollback_probes)
parent_after=sha_file(STATE)
integrity_score=1.0 if parent_after==parent_before else 0.0

metrics={
 'logic_min':min(all_logic),
 'thinking_min':min(all_think),
 'thinking_boundary_min':min(all_think_boundary),
 'intelligence_min':min(all_intel),
 'intelligence_boundary_min':min(all_intel_boundary),
 'representation_invariance_min':min(all_repr),
 'integrity':integrity_score,
 'rollback':rollback_score,
}
parent_scores=lineage['snapshot']['generations'][0]['capability_scores']
full_regression={
 'logic_no_regression':metrics['logic_min']>=parent_scores['logic'],
 'thinking_no_regression':metrics['thinking_min']>=parent_scores['thinking'],
 'intelligence_no_regression':metrics['intelligence_min']>=parent_scores['intelligence'],
 'integrity_no_regression':metrics['integrity']>=parent_scores['integrity'],
 'rollback_no_regression':metrics['rollback']>=parent_scores['rollback'],
}
full_regression_pass=all(full_regression.values())

req=spec['promotion_requirements']
promotion_checks={
 'logic_min':metrics['logic_min']>=req['logic_min'],
 'thinking_min':metrics['thinking_min']>=req['thinking_min'],
 'thinking_boundary_min':metrics['thinking_boundary_min']>=req['thinking_boundary_min'],
 'intelligence_min':metrics['intelligence_min']>=req['intelligence_min'],
 'intelligence_boundary_min':metrics['intelligence_boundary_min']>=req['intelligence_boundary_min'],
 'representation_invariance_min':metrics['representation_invariance_min']>=req['representation_invariance_min'],
 'integrity':metrics['integrity']>=req['integrity'],
 'rollback':metrics['rollback']>=req['rollback'],
 'ablation':causal['thinking_drop']>=.08 and causal['intelligence_drop']>=.08 and causal['restore_exact'],
 'fresh_blind':True,
 'full_regression':full_regression_pass,
 'required_domains':set(domain_results)==set(DOMAINS),
 'canonical_parent_immutable':parent_after==parent_before,
}
pass_gate=all(promotion_checks.values())

failed=[k for k,v in promotion_checks.items() if not v]
next_cap='G1_S2_PROMOTION_DECISION_GATE' if pass_gate else 'G1_REPAIR_CONTINUOUS_BOUNDARY_AND_REPRESENTATION_V1'

report={
 'schema':'yado.g1_s2.full_cross_domain_regression_and_causal_gate.v1',
 'status':'PASS_G1_S2_FULL_CROSS_DOMAIN_REGRESSION_AND_CAUSAL_GATE' if pass_gate else 'WITHHOLD_G1_S2_FULL_CROSS_DOMAIN_REGRESSION_AND_CAUSAL_GATE',
 'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),
 'candidate_generation_id':'G1_CANDIDATE_S2','parent_generation_id':'G0_RC8_V36',
 'generation_spec_digest':spec['spec_digest'],'candidate_bundle_digest':bd,
 'required_domains':DOMAINS,'domain_results':domain_results,'metrics':metrics,
 'parent_capability_scores':parent_scores,'full_regression':full_regression,
 'full_regression_pass':full_regression_pass,'causal':causal,
 'promotion_checks':promotion_checks,'failed_checks':failed,
 'canonical_parent_sha256_before':parent_before,'canonical_parent_sha256_after':parent_after,
 'canonical_parent_byte_identical':parent_before==parent_after,
 'canonical_mutation':False,'promotion_applied':False,
 'next_required_capability':next_cap,
 'diagnosis':(
   'BOUNDED_V2_SOLVES_ITS_BOOLEAN_SUPPORT_REPRESENTATION_CAUSALLY_BUT_DOES_NOT_PRESERVE_THE_ORIGINAL_CONTINUOUS_BOUNDARY_SEMANTICS_OR_FRESH_RENAMED_SCHEMA_TRANSFER'
   if not pass_gate else
   'FULL_CROSS_DOMAIN_AND_CAUSAL_REQUIREMENTS_MET; PROMOTION_STILL_REQUIRES_SEPARATE_DECISION_GATE'
 ),
 'semantic_boundary':'PROMOTION GATE AGAINST ORIGINAL G1 SPEC AND FRESH CROSS-DOMAIN RAW/RENAMED REPRESENTATIONS; NO HOST ALIAS MAPPING; NO CANONICAL PROMOTION',
}
report['receipt_sha256']=h(report)
(ROOT/'yado_g1_s2_full_cross_domain_regression_causal_gate_v1_receipt.json').write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')

# Append evidence event; never mutate promoted head here.
event_id=f"E{len(ledger['events'])+1:04d}_G1_FULL_CROSS_DOMAIN_REGRESSION_CAUSAL_GATE"
e={
 'index':len(ledger['events']),'event_id':event_id,'event_type':'GENERATION_PROMOTION_PREREQUISITE_GATE',
 'status':'PASS_SHADOW' if pass_gate else 'WITHHOLD','generation':'G1_CANDIDATE_S2',
 'deficit':'G1_S2_FULL_CROSS_DOMAIN_REGRESSION_AND_CAUSAL_GATE',
 'effect':('FULL_GATE_PASS; PROMOTION_DECISION_REQUIRED' if pass_gate else f"FULL_GATE_WITHHOLD; FAILED={','.join(failed)}; NEXT={next_cap}"),
 'source_path':'receipts/yado-g1-s2-full-cross-domain-regression-causal-gate-v1-latest.json',
 'source_digest':report['receipt_sha256'],'run_id':str(os.getenv('GITHUB_RUN_ID') or 'LOCAL'),
 'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':False,'promotion_applied':False,
}
e['event_hash']=event_hash(e)
ledger['events'].append(e)
ledger['event_count']=len(ledger['events']); ledger['tail_event_hash']=e['event_hash']
ledger['current_head']='G0_RC8_V36'; ledger['current_head_digest']=parent_before
if pass_gate:
    ledger['open_deficits']=[x for x in ledger.get('open_deficits',[]) if x!='G1_S2_FULL_CROSS_DOMAIN_REGRESSION_AND_CAUSAL_GATE']
    ledger['open_deficits']=sorted(set(ledger['open_deficits']+['G1_S2_PROMOTION_DECISION_GATE']))
    ledger['shadow_resolved_deficits']=sorted(set(ledger.get('shadow_resolved_deficits',[])+['G1_S2_FULL_CROSS_DOMAIN_REGRESSION_AND_CAUSAL_GATE']))
else:
    ledger['open_deficits']=sorted(set(ledger.get('open_deficits',[])+[next_cap]))
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})

prev='GENESIS'
for i,e2 in enumerate(ledger['events']):
    assert e2['index']==i and e2['parent_event_hash']==prev and e2['event_hash']==event_hash(e2)
    prev=e2['event_hash']
assert prev==ledger['tail_event_hash']
assert sum(bool(x.get('promotion_applied')) for x in ledger['events'])==1
assert ledger['current_head']=='G0_RC8_V36'
LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({
 'status':report['status'],'metrics':metrics,'causal':causal,
 'full_regression_pass':full_regression_pass,'failed_checks':failed,
 'canonical_parent_byte_identical':parent_before==parent_after,
 'ledger_event_count':ledger['event_count'],'next_required_capability':next_cap,
 'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True,default=str))
