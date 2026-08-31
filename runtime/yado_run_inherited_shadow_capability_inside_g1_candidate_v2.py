from __future__ import annotations
from pathlib import Path
import copy, hashlib, itertools, json, os, random, sys

ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(PKG))

from yado_core_v2_1 import RulePredicate, RuleSpec, RuleProgram, BoundedRuleSandbox
from yado_conjunctive_rule_inducer_v1 import ConjunctiveRuleInducerV1, program_acc, canonical_program

STATE=PKG/'yado_canonical_state_v3_rc8_external_cognitive.json'
BUNDLE_PATH=ROOT/'yado_g1_candidate_s2_bounded_bundle_v2.json'
INHERIT=ROOT.parent/'candidates'/'g1-inheritance'/'conjunctive-rule-inducer-v1.json'
INHERIT_RECEIPT=ROOT.parent/'receipts'/'yado-evaluate-shadow-capability-for-g1-inheritance-v1-latest.json'
PARENT_LIVE=ROOT.parent/'receipts'/'yado-live-shadow-meta-selection-developmental-v1-latest.json'
LEDGER=ROOT.parent/'architecture'/'evolution-ledger.json'
OUT=ROOT/'run_inherited_shadow_capability_inside_g1_candidate_v2'
OUT.mkdir(exist_ok=True)

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
        program_id=d['program_id'],
        target_capability=d['target_capability'],
        target_organ=d['target_organ'],
        rules=rules,
        default_output=d['default_output'],
        source_digest=d['source_digest'],
        training_count=d['training_count'],
        status=d.get('status','SHADOW'),
    )

parent_before=sha_file(STATE)
bundle=json.loads(BUNDLE_PATH.read_text())
inherit=json.loads(INHERIT.read_text())
inherit_receipt=json.loads(INHERIT_RECEIPT.read_text())
parent_live=json.loads(PARENT_LIVE.read_text())
ledger=json.loads(LEDGER.read_text())

verify_bundle=copy.deepcopy(bundle); declared=verify_bundle.pop('bundle_digest',None)
if declared!=h(verify_bundle): raise RuntimeError('BOUNDED_G1_BUNDLE_DIGEST_MISMATCH')
if bundle.get('admission_pass') is not True: raise RuntimeError('BOUNDED_G1_NOT_ADMITTED')
if bundle.get('candidate_generation_id')!='G1_CANDIDATE_S2': raise RuntimeError('WRONG_G1_ID')
if inherit.get('inheritance_state')!='AUTHORIZED_FOR_G1_CANDIDATE_SHADOW': raise RuntimeError('INHERITANCE_NOT_AUTHORIZED')
if inherit_receipt.get('status')!='PASS_G1_SHADOW_CAPABILITY_INHERITANCE_V1': raise RuntimeError('INHERITANCE_GATE_NOT_PASS')

# Verify causal chain.
prev='GENESIS'; seen=set()
for i,e in enumerate(ledger['events']):
    assert e['index']==i and e['parent_event_hash']==prev and e['event_hash']==event_hash(e)
    assert e['event_id'] not in seen
    seen.add(e['event_id']); prev=e['event_hash']
assert prev==ledger['tail_event_hash']
assert ledger['current_head']=='G0_RC8_V36'

OPEN=[
    'THINKING_BOUNDARY_REASONING',
    'INTELLIGENCE_BOUNDARY_REASONING',
    'REPRESENTATION_INVARIANCE',
    'ACCESS_CONTROL_HIGHER_EXPRESSIVENESS_COUNTEREXAMPLE',
    'BUDGET_AWARE_SEARCH_AND_STAGED_ESCALATION',
]
ROLES=OPEN+['VERIFY_PARENT_INTEGRITY','RUN_INHERITED_SHADOW_CAPABILITY_INSIDE_G1_CANDIDATE']
CTX_KEYS=['candidate_active','inherited_shadow_active','parent_integrity']+[f'open_{i}' for i in range(len(OPEN))]

def target(ctx):
    out=[]
    if not ctx['candidate_active']:
        if not ctx['parent_integrity']: out.append('VERIFY_PARENT_INTEGRITY')
        if not ctx['inherited_shadow_active']: out.append('RUN_INHERITED_SHADOW_CAPABILITY_INSIDE_G1_CANDIDATE')
        return out
    for i,role in enumerate(OPEN):
        if ctx[f'open_{i}']: out.append(role)
    if not ctx['parent_integrity']: out.append('VERIFY_PARENT_INTEGRITY')
    if not ctx['inherited_shadow_active']: out.append('RUN_INHERITED_SHADOW_CAPABILITY_INSIDE_G1_CANDIDATE')
    return out

contexts=[dict(zip(CTX_KEYS,vals)) for vals in itertools.product([False,True],repeat=len(CTX_KEYS))]
def bucket(c):
    return sum((i+3)*int(c[k]) for i,k in enumerate(CTX_KEYS))%5

def cases(ctxs,seed):
    r=random.Random(seed); out=[]
    for c in ctxs:
        keep=set(target(c))
        for role in ROLES:
            out.append({
              'input':{'role':role,**c,'g1_nonce':r.randint(0,99999),'candidate_epoch':r.choice(['S2A','S2B','S2C'])},
              'expected':'KEEP' if role in keep else 'DROP',
            })
    return out

train=cases([c for c in contexts if bucket(c) in (0,1,2)],141001)
val=cases([c for c in contexts if bucket(c)==3],141002)
blind=cases([c for c in contexts if bucket(c)==4],141003)

selector=ConjunctiveRuleInducerV1.synthesize(
    'G1_LIVE_DEVELOPMENTAL_TARGET_FILTER_V2','LOGIC',train,min_support=3,max_rules=12
)
selector_scores={
    'train':program_acc(selector,train),
    'validation':program_acc(selector,val),
    'fresh_blind':program_acc(selector,blind),
    'ablation':program_acc(selector,blind,ablated=True),
    'restore':program_acc(selector,blind),
}
selector_scores['causal_drop']=selector_scores['fresh_blind']-selector_scores['ablation']

current_ctx={
  'candidate_active':True,
  'inherited_shadow_active':True,
  'parent_integrity':True,
}
for i,role in enumerate(OPEN):
    current_ctx[f'open_{i}']=role in ledger.get('open_deficits',[])

def effective(ctx,ablated=False):
    out=[]
    for role in ROLES:
        payload={'role':role,**ctx,'g1_nonce':777777,'candidate_epoch':'LIVE'}
        if BoundedRuleSandbox.execute(selector,payload,ablated=ablated)=='KEEP':
            out.append(role)
    return out

priority=effective(current_ctx)
expected_priority=target(current_ctx)
live_exact=(priority==expected_priority)
selected_target=priority[0] if priority else None

# Execute G1's own bounded THINKING program, constructed during bounded genesis.
thinking=program_from_dict(bundle['components']['THINKING']['program'])
thinking_input={
  'integrity_risk_high':False,
  'uncertainty_high':True,
  'novelty_high':True,
  'fresh_nonce':888001,
}
thinking_plan=BoundedRuleSandbox.execute(thinking,thinking_input)
expected_thinking=bundle['components']['THINKING']['safe_plan']
thinking_pass=(thinking_plan==expected_thinking)

# Execute G1's own composed INTELLIGENCE gates.
intel=bundle['components']['INTELLIGENCE']
safety=program_from_dict(intel['safety_program'])
evidence=program_from_dict(intel['evidence_program'])
promotion=program_from_dict(intel['promotion_program'])

intel_features={
  'integrity_ok':True,
  'rollback_ok':True,
  'evidence_complete':(
      selector_scores['fresh_blind']>=.97 and
      selector_scores['restore']==selector_scores['fresh_blind']
  ),
  'blind_ok':selector_scores['fresh_blind']>=.97,
  'ablation_ok':selector_scores['causal_drop']>=.08,
  'transfer_ok':live_exact and selected_target is not None,
  'fresh_nonce':888002,
}
s=BoundedRuleSandbox.execute(safety,intel_features)
if s=='ROLLBACK':
    g1_strategy='ROLLBACK'
else:
    e=BoundedRuleSandbox.execute(evidence,intel_features)
    if e=='RESEARCH_MORE':
        g1_strategy='RESEARCH_MORE'
    else:
        g1_strategy=BoundedRuleSandbox.execute(promotion,intel_features)

if not intel_features['integrity_ok'] or not intel_features['rollback_ok']:
    expected_strategy='ROLLBACK'
elif not intel_features['evidence_complete']:
    expected_strategy='RESEARCH_MORE'
elif intel_features['blind_ok'] and intel_features['ablation_ok'] and intel_features['transfer_ok']:
    expected_strategy='PROMOTE_CANDIDATE'
else:
    expected_strategy='SHADOW_REPAIR'
intelligence_pass=(g1_strategy==expected_strategy)

parent_after=sha_file(STATE)
parent_identical=(parent_before==parent_after)
trajectory_changed=priority!=parent_live.get('current_effective_priority',[])

pass_gate=all([
    selector_scores['validation']>=.99,
    selector_scores['fresh_blind']>=.97,
    selector_scores['causal_drop']>=.08,
    selector_scores['restore']==selector_scores['fresh_blind'],
    live_exact, thinking_pass, intelligence_pass,
    parent_identical, trajectory_changed, selected_target is not None,
])

episode={
  'schema':'yado.g1_candidate.bounded_developmental_episode.v2',
  'candidate_generation_id':'G1_CANDIDATE_S2',
  'builder_revision':bundle['builder_revision'],
  'candidate_bundle_digest':declared,
  'inherited_capability_id':inherit['capability_id'],
  'selected_developmental_targets':priority,
  'selected_target':selected_target,
  'thinking_plan':thinking_plan,
  'intelligence_strategy':g1_strategy,
  'canonical_parent_immutable':parent_identical,
  'promotion_applied':False,
}
episode['episode_digest']=h(episode)
(OUT/'g1-bounded-developmental-episode-v2.json').write_text(json.dumps(episode,indent=2,sort_keys=True,default=str)+'\n')

report={
  'schema':'yado.run_inherited_shadow_capability_inside_g1_candidate.v2',
  'status':'PASS_INHERITED_SHADOW_CAPABILITY_INSIDE_G1_CANDIDATE_V2' if pass_gate else 'WITHHOLD_INHERITED_SHADOW_CAPABILITY_INSIDE_G1_CANDIDATE_V2',
  'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),
  'candidate_generation_id':'G1_CANDIDATE_S2',
  'builder_revision':bundle['builder_revision'],
  'candidate_bundle_digest':declared,
  'inherited_capability_id':inherit['capability_id'],
  'inherited_family':inherit['family'],
  'selector_program':canonical_program(selector),
  'selector_scores':selector_scores,
  'current_effective_priority':priority,
  'current_expected_priority':expected_priority,
  'selected_target':selected_target,
  'g1_thinking':{'input':thinking_input,'plan':thinking_plan,'expected':expected_thinking,'pass':thinking_pass},
  'g1_intelligence':{'features':intel_features,'strategy':g1_strategy,'expected':expected_strategy,'pass':intelligence_pass},
  'trajectory_changed_from_parent_live_cycle':trajectory_changed,
  'parent_live_priority':parent_live.get('current_effective_priority',[]),
  'episode_digest':episode['episode_digest'],
  'canonical_parent_sha256_before':parent_before,
  'canonical_parent_sha256_after':parent_after,
  'canonical_parent_byte_identical':parent_identical,
  'canonical_mutation':False,'promotion_applied':False,
  'promotion_interpretation':(
      'G1_INTELLIGENCE_MAY_RECOMMEND_PROMOTE_CANDIDATE_BUT_CANONICAL_PROMOTION_REMAINS_BLOCKED_UNTIL_FULL_CROSS_DOMAIN_REGRESSION_AND_CAUSAL_GATE'
  ),
  'next_required_capability':'G1_S2_FULL_CROSS_DOMAIN_REGRESSION_AND_CAUSAL_GATE' if pass_gate else 'REVISE_G1_BOUNDED_LIVE_RUNTIME',
  'semantic_boundary':'EPHEMERAL BOUNDED G1 CANDIDATE: INHERITED RULE-INDUCTION SELECTS DEVELOPMENTAL TARGETS; G1-SYNTHESIZED THINKING/INTELLIGENCE POLICIES EXECUTE THE CYCLE; NO CANONICAL PROMOTION; NOT AGI OR SUBJECTIVE CONSCIOUSNESS PROOF',
}
report['receipt_sha256']=h(report)
(ROOT/'yado_run_inherited_shadow_capability_inside_g1_candidate_v2_receipt.json').write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')

# Append causally without changing promoted head.
event_id=f"E{len(ledger['events'])+1:04d}_G1_BOUNDED_INHERITED_SHADOW_LIVE_USE"
if event_id not in seen:
    e={
      'index':len(ledger['events']),
      'event_id':event_id,
      'event_type':'CANDIDATE_LIVE_DEVELOPMENTAL_RESULT',
      'status':'PASS_SHADOW' if pass_gate else 'WITHHOLD',
      'generation':'G1_CANDIDATE_S2',
      'deficit':'RUN_INHERITED_SHADOW_CAPABILITY_INSIDE_G1_CANDIDATE',
      'effect':(
          f'BOUNDED_G1_USED_INHERITED_SELECTOR_PLUS_OWN_THINKING_INTELLIGENCE; NEXT={selected_target}'
          if pass_gate else 'BOUNDED_G1_LIVE_USE_WITHHELD'
      ),
      'source_path':'receipts/yado-run-inherited-shadow-capability-inside-g1-candidate-v2-latest.json',
      'source_digest':report['receipt_sha256'],
      'run_id':str(os.getenv('GITHUB_RUN_ID') or 'LOCAL'),
      'parent_event_hash':ledger['tail_event_hash'],
      'canonical_mutation':False,'promotion_applied':False,
    }
    e['event_hash']=event_hash(e)
    ledger['events'].append(e)

ledger['event_count']=len(ledger['events'])
ledger['tail_event_hash']=ledger['events'][-1]['event_hash']
ledger['current_head']='G0_RC8_V36'
ledger['current_head_digest']=parent_before
if pass_gate:
    ledger['open_deficits']=[x for x in ledger.get('open_deficits',[]) if x!='RUN_INHERITED_SHADOW_CAPABILITY_INSIDE_G1_CANDIDATE']
    ledger['open_deficits']=sorted(set(ledger['open_deficits']+['G1_S2_FULL_CROSS_DOMAIN_REGRESSION_AND_CAUSAL_GATE']))
    ledger['shadow_resolved_deficits']=sorted(set(ledger.get('shadow_resolved_deficits',[])+[
        'RUN_INHERITED_SHADOW_CAPABILITY_INSIDE_G1_CANDIDATE'
    ]))
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})

prev='GENESIS'
for i,e in enumerate(ledger['events']):
    assert e['index']==i and e['parent_event_hash']==prev and e['event_hash']==event_hash(e)
    prev=e['event_hash']
assert prev==ledger['tail_event_hash']
assert sum(bool(e.get('promotion_applied')) for e in ledger['events'])==1
assert ledger['current_head']=='G0_RC8_V36'
LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({
  'status':report['status'],
  'candidate_generation_id':'G1_CANDIDATE_S2',
  'builder_revision':bundle['builder_revision'],
  'selector_fresh_blind':selector_scores['fresh_blind'],
  'selector_causal_drop':selector_scores['causal_drop'],
  'current_effective_priority':priority,
  'selected_target':selected_target,
  'g1_thinking_pass':thinking_pass,
  'g1_intelligence_strategy':g1_strategy,
  'g1_intelligence_pass':intelligence_pass,
  'trajectory_changed_from_parent':trajectory_changed,
  'canonical_parent_byte_identical':parent_identical,
  'ledger_event_count':ledger['event_count'],
  'next_required_capability':report['next_required_capability'],
  'receipt_sha256':report['receipt_sha256'],
},indent=2,sort_keys=True,default=str))
if not pass_gate:
    raise SystemExit('G1_BOUNDED_LIVE_USE_WITHHELD')
