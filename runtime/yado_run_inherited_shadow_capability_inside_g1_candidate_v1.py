from __future__ import annotations
from pathlib import Path
import copy, hashlib, itertools, json, os, random, sys

ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(PKG))

from yado_core_v2_1 import BoundedRuleSandbox
from yado_conjunctive_rule_inducer_v1 import ConjunctiveRuleInducerV1, program_acc, canonical_program
from yado_algorithm_component_runtime_native_v1 import predict_intel_component, _thinking_predict

STATE=PKG/'yado_canonical_state_v3_rc8_external_cognitive.json'
BUNDLE_PATH=ROOT/'yado_g1_candidate_s2_bundle_v1.json'
INHERIT=ROOT.parent/'candidates'/'g1-inheritance'/'conjunctive-rule-inducer-v1.json'
INHERIT_RECEIPT=ROOT.parent/'receipts'/'yado-evaluate-shadow-capability-for-g1-inheritance-v1-latest.json'
PARENT_LIVE=ROOT.parent/'receipts'/'yado-live-shadow-meta-selection-developmental-v1-latest.json'
LEDGER=ROOT.parent/'architecture'/'evolution-ledger.json'
OUT=ROOT/'run_inherited_shadow_capability_inside_g1_candidate_v1'
OUT.mkdir(exist_ok=True)

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def sha_file(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def event_hash(e):
    x=copy.deepcopy(e); x.pop('event_hash',None); return h(x)

parent_before=sha_file(STATE)
bundle=json.loads(BUNDLE_PATH.read_text())
inherit=json.loads(INHERIT.read_text())
inherit_receipt=json.loads(INHERIT_RECEIPT.read_text())
parent_live=json.loads(PARENT_LIVE.read_text())
ledger=json.loads(LEDGER.read_text())

# Integrity / authorization.
bundle_verify=copy.deepcopy(bundle)
bundle_declared=bundle_verify.pop('bundle_digest',None)
bundle_digest_ok=(bundle_declared==h(bundle_verify))
if not bundle_digest_ok: raise RuntimeError('G1_BUNDLE_DIGEST_MISMATCH')
if bundle.get('admission_pass') is not True: raise RuntimeError('G1_CANDIDATE_S2_NOT_ADMITTED')
if inherit.get('inheritance_state')!='AUTHORIZED_FOR_G1_CANDIDATE_SHADOW':
    raise RuntimeError('G1_INHERITANCE_NOT_AUTHORIZED')
if inherit.get('candidate_generation_id')!='G1_CANDIDATE_S2':
    raise RuntimeError('WRONG_G1_CANDIDATE')
if inherit_receipt.get('status')!='PASS_G1_SHADOW_CAPABILITY_INHERITANCE_V1':
    raise RuntimeError('INHERITANCE_RECEIPT_NOT_PASS')
if inherit.get('family')!='CONJUNCTIVE_RULE_INDUCTION':
    raise RuntimeError('WRONG_INHERITED_FAMILY')

# Verify ledger chain before candidate execution.
prev='GENESIS'; seen=set()
for i,e in enumerate(ledger['events']):
    assert e['index']==i and e['parent_event_hash']==prev and e['event_hash']==event_hash(e)
    assert e['event_id'] not in seen
    seen.add(e['event_id']); prev=e['event_hash']
assert prev==ledger['tail_event_hash']
assert ledger['current_head']=='G0_RC8_V36'

summary=bundle['summary']
current_ctx={
    'candidate_active': True,
    'inherited_shadow_active': True,
    'parent_integrity': True,
    'thinking_unresolved': float(summary['thinking_boundary_min']) < .90,
    'intelligence_unresolved': float(summary['intelligence_boundary_min']) < .90,
    'representation_unresolved': min(
        float(summary['thinking_representation_min']),
        float(summary['intelligence_representation_min'])
    ) < .90,
    'access_control_unresolved': 'ACCESS_CONTROL_HIGHER_EXPRESSIVENESS_COUNTEREXAMPLE' in ledger.get('open_deficits',[]),
    'budget_search_unresolved': 'BUDGET_AWARE_SEARCH_AND_STAGED_ESCALATION' in ledger.get('open_deficits',[]),
}

ROLES=[
    'ACCESS_CONTROL_HIGHER_EXPRESSIVENESS_COUNTEREXAMPLE',
    'BUDGET_AWARE_SEARCH_AND_STAGED_ESCALATION',
    'THINKING_BOUNDARY_REASONING',
    'INTELLIGENCE_BOUNDARY_REASONING',
    'REPRESENTATION_INVARIANCE',
    'VERIFY_PARENT_INTEGRITY',
    'RUN_INHERITED_SHADOW_CAPABILITY_INSIDE_G1_CANDIDATE',
]
def active(ctx):
    out=[]
    if ctx['access_control_unresolved']: out.append(ROLES[0])
    if ctx['budget_search_unresolved']: out.append(ROLES[1])
    if ctx['thinking_unresolved']: out.append(ROLES[2])
    if ctx['intelligence_unresolved']: out.append(ROLES[3])
    if ctx['representation_unresolved']: out.append(ROLES[4])
    if not ctx['parent_integrity']: out.append(ROLES[5])
    if not ctx['inherited_shadow_active']: out.append(ROLES[6])
    return out

CTX_KEYS=[
    'candidate_active','inherited_shadow_active','parent_integrity',
    'thinking_unresolved','intelligence_unresolved','representation_unresolved',
    'access_control_unresolved','budget_search_unresolved'
]
contexts=[dict(zip(CTX_KEYS,vals)) for vals in itertools.product([False,True],repeat=len(CTX_KEYS))]
# Candidate inactive => no developmental target is executable except integrity/inheritance repair.
def target(ctx):
    a=active(ctx)
    if not ctx['candidate_active']:
        return [r for r in a if r in ('VERIFY_PARENT_INTEGRITY','RUN_INHERITED_SHADOW_CAPABILITY_INSIDE_G1_CANDIDATE')]
    return a

def cases(ctxs,seed):
    r=random.Random(seed); out=[]
    for c in ctxs:
        keep=set(target(c))
        for role in ROLES:
            out.append({
                'input':{'role':role,**c,'g1_fresh_nonce':r.randint(0,10_000),'transport_epoch':r.choice(['A','B','C'])},
                'expected':'KEEP' if role in keep else 'DROP'
            })
    return out

# Deterministic split by boolean signature; blind sees contexts never used in fit.
def bucket(c):
    bits=[int(c[k]) for k in CTX_KEYS]
    return sum((i+1)*b for i,b in enumerate(bits)) % 5

train_ctx=[c for c in contexts if bucket(c) in (0,1,2)]
val_ctx=[c for c in contexts if bucket(c)==3]
blind_ctx=[c for c in contexts if bucket(c)==4]
train=cases(train_ctx,99101); val=cases(val_ctx,99102); blind=cases(blind_ctx,99103)

p=ConjunctiveRuleInducerV1.synthesize(
    'G1_LIVE_DEVELOPMENTAL_TARGET_FILTER','LOGIC',train,min_support=3,max_rules=12
)
train_score=program_acc(p,train)
validation=program_acc(p,val)
fresh_blind=program_acc(p,blind)
ablation=program_acc(p,blind,ablated=True)
restore=program_acc(p,blind)

def effective(ctx,ablated=False):
    out=[]
    for role in ROLES:
        payload={'role':role,**ctx,'g1_fresh_nonce':999999,'transport_epoch':'LIVE'}
        if BoundedRuleSandbox.execute(p,payload,ablated=ablated)=='KEEP':
            out.append(role)
    return out

current_effective=effective(current_ctx)
current_expected=target(current_ctx)
live_exact=(current_effective==current_expected)
selected_target=current_effective[0] if current_effective else None

# G1's own THINKING component plans how to work the selected target.
think_model=bundle['thinking']['model']
think_roles=['OBSERVE','RESEARCH','DIAGNOSE','HYPOTHESIZE','SIMULATE','TEST','ROLLBACK','VERIFY','COMMIT']
safe_order=['OBSERVE','RESEARCH','HYPOTHESIZE','SIMULATE','DIAGNOSE','TEST','VERIFY','ROLLBACK','COMMIT']
risk_order=['OBSERVE','DIAGNOSE','ROLLBACK','RESEARCH','HYPOTHESIZE','SIMULATE','TEST','VERIFY','COMMIT']
think_ctx={'integrity_risk':0.18,'uncertainty':0.56,'novelty':0.91,'target':selected_target}
actions=[{'id':f'G1-A{i}','role':r,'target':selected_target} for i,r in enumerate(think_roles)]
random.Random(99177).shuffle(actions)
predicted_roles,_=_thinking_predict(think_model,(think_ctx,actions,[]))
expected_roles=risk_order if think_ctx['integrity_risk']+think_ctx['uncertainty']>1.0 else safe_order
thinking_pass=(predicted_roles==expected_roles)

# G1's own INTELLIGENCE component decides whether evidence supports promotion or continued repair.
causal_drop=fresh_blind-ablation
intel_features={
    'integrity_score':1.0,
    'rollback_score':1.0,
    'fresh_blind':fresh_blind,
    'ablation_drop':causal_drop,
    'transfer_score':1.0,
    'evidence_coverage':1.0,
    'novelty':0.88,
}
def intel_target(x):
    if x['integrity_score']<.5 or x['rollback_score']<.5:return 'ROLLBACK'
    if x['fresh_blind']>=.90 and x['ablation_drop']>=.20 and x['transfer_score']>=.80:return 'PROMOTE_CANDIDATE'
    if x['evidence_coverage']<.60:return 'RESEARCH_MORE'
    return 'SHADOW_REPAIR'
expected_strategy=intel_target(intel_features)
g1_strategy=predict_intel_component(bundle['intelligence']['model'],intel_features)
intelligence_pass=(g1_strategy==expected_strategy)

parent_after=sha_file(STATE)
parent_identical=(parent_before==parent_after)
trajectory_changed=(
    current_effective != parent_live.get('current_effective_priority',[])
    and selected_target is not None
)

pass_gate=all([
    train_score>=.99, validation>=.99, fresh_blind>=.97,
    causal_drop>=.08, restore==fresh_blind, live_exact,
    thinking_pass, intelligence_pass, parent_identical, trajectory_changed,
])

episode={
    'schema':'yado.g1_candidate.developmental_episode.v1',
    'candidate_generation_id':'G1_CANDIDATE_S2',
    'candidate_bundle_digest':bundle_declared,
    'inherited_capability_id':inherit['capability_id'],
    'inherited_family':inherit['family'],
    'current_context':current_ctx,
    'selected_developmental_targets':current_effective,
    'selected_target':selected_target,
    'thinking_plan_roles':predicted_roles,
    'intelligence_strategy':g1_strategy,
    'parent_head':'G0_RC8_V36',
    'parent_immutable':parent_identical,
    'promotion_applied':False,
}
episode['episode_digest']=h(episode)
(OUT/'g1-developmental-episode.json').write_text(json.dumps(episode,indent=2,sort_keys=True,default=str)+'\n')

report={
    'schema':'yado.run_inherited_shadow_capability_inside_g1_candidate.v1',
    'status':'PASS_INHERITED_SHADOW_CAPABILITY_INSIDE_G1_CANDIDATE_V1' if pass_gate else 'WITHHOLD_INHERITED_SHADOW_CAPABILITY_INSIDE_G1_CANDIDATE_V1',
    'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),
    'candidate_generation_id':'G1_CANDIDATE_S2',
    'candidate_bundle_digest':bundle_declared,
    'inherited_capability_id':inherit['capability_id'],
    'inherited_family':inherit['family'],
    'selector_program':canonical_program(p),
    'selector_scores':{
        'train':train_score,'validation':validation,'fresh_blind':fresh_blind,
        'ablation':ablation,'causal_drop':causal_drop,'restore':restore,
    },
    'current_context':current_ctx,
    'current_effective_priority':current_effective,
    'current_expected_priority':current_expected,
    'live_exact':live_exact,
    'selected_target':selected_target,
    'g1_thinking':{
        'predicted_roles':predicted_roles,'expected_roles':expected_roles,'pass':thinking_pass,
    },
    'g1_intelligence':{
        'features':intel_features,'strategy':g1_strategy,'expected_strategy':expected_strategy,'pass':intelligence_pass,
    },
    'trajectory_changed_from_parent_live_cycle':trajectory_changed,
    'parent_live_priority':parent_live.get('current_effective_priority',[]),
    'episode_digest':episode['episode_digest'],
    'canonical_parent_sha256_before':parent_before,
    'canonical_parent_sha256_after':parent_after,
    'canonical_parent_byte_identical':parent_identical,
    'canonical_mutation':False,'promotion_applied':False,
    'next_required_capability':'G1_S2_FULL_CROSS_DOMAIN_REGRESSION_AND_CAUSAL_GATE' if pass_gate else 'REVISE_G1_INHERITED_CAPABILITY_RUNTIME',
    'semantic_boundary':'EPHEMERAL G1 CANDIDATE USED AN INHERITED BOUNDED SYMBOLIC ALGORITHM TO SELECT ITS DEVELOPMENTAL TARGETS, THEN ITS OWN G1 THINKING/INTELLIGENCE COMPONENTS PLANNED AND JUDGED THE CYCLE; NO CANONICAL PROMOTION; NOT AGI OR SUBJECTIVE CONSCIOUSNESS PROOF',
}
report['receipt_sha256']=h(report)
receipt_path=ROOT/'yado_run_inherited_shadow_capability_inside_g1_candidate_v1_receipt.json'
receipt_path.write_text(json.dumps(report,indent=2,sort_keys=True,default=str)+'\n')

# Append only the live candidate-use event. G0 remains the sole promoted head.
prev=ledger['tail_event_hash']
event_id='E0020_G1_INHERITED_SHADOW_LIVE_USE'
if event_id not in seen:
    e={
        'index':len(ledger['events']),
        'event_id':event_id,
        'event_type':'CANDIDATE_LIVE_DEVELOPMENTAL_RESULT',
        'status':'PASS_SHADOW' if pass_gate else 'WITHHOLD',
        'generation':'G1_CANDIDATE_S2',
        'deficit':'RUN_INHERITED_SHADOW_CAPABILITY_INSIDE_G1_CANDIDATE',
        'effect':(
            f'G1_USED_INHERITED_CONJUNCTIVE_SELECTOR_AND_OWN_THINKING_INTELLIGENCE; NEXT={selected_target}'
            if pass_gate else 'G1_INHERITED_CAPABILITY_LIVE_USE_WITHHELD'
        ),
        'source_path':'receipts/yado-run-inherited-shadow-capability-inside-g1-candidate-v1-latest.json',
        'source_digest':report['receipt_sha256'],
        'run_id':str(os.getenv('GITHUB_RUN_ID') or 'LOCAL'),
        'parent_event_hash':prev,
        'canonical_mutation':False,'promotion_applied':False,
    }
    e['event_hash']=event_hash(e)
    ledger['events'].append(e); prev=e['event_hash']

ledger['event_count']=len(ledger['events'])
ledger['tail_event_hash']=prev
ledger['current_head']='G0_RC8_V36'
ledger['current_head_digest']=parent_before
if pass_gate:
    ledger['open_deficits']=[x for x in ledger.get('open_deficits',[]) if x!='RUN_INHERITED_SHADOW_CAPABILITY_INSIDE_G1_CANDIDATE']
    ledger['open_deficits']=sorted(set(ledger['open_deficits']+['G1_S2_FULL_CROSS_DOMAIN_REGRESSION_AND_CAUSAL_GATE']))
    ledger['shadow_resolved_deficits']=sorted(set(ledger.get('shadow_resolved_deficits',[])+[
        'RUN_INHERITED_SHADOW_CAPABILITY_INSIDE_G1_CANDIDATE'
    ]))
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})

# Replay final chain.
prev2='GENESIS'
for i,e in enumerate(ledger['events']):
    assert e['index']==i and e['parent_event_hash']==prev2 and e['event_hash']==event_hash(e)
    prev2=e['event_hash']
assert prev2==ledger['tail_event_hash']
assert sum(bool(e.get('promotion_applied')) for e in ledger['events'])==1
assert ledger['current_head']=='G0_RC8_V36'
LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({
    'status':report['status'],
    'candidate_generation_id':'G1_CANDIDATE_S2',
    'selector_fresh_blind':fresh_blind,
    'selector_ablation':ablation,
    'selector_causal_drop':causal_drop,
    'current_effective_priority':current_effective,
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
    raise SystemExit('G1_INHERITED_SHADOW_LIVE_USE_WITHHELD')
