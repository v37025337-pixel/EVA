from __future__ import annotations
from pathlib import Path
import copy, hashlib, itertools, json, os, random, sys

ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(PKG))

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_algorithm_component_runtime_native_v1 import (
    predict_logic_component, predict_intel_component, _thinking_predict
)

PARENT=PKG/'yado_canonical_state_v3_rc8_external_cognitive.json'
CAPSULE_PATH=ROOT.parent/'candidates'/'rc8-safe-successor-v1'/'successor-capsule.json'
BUNDLE_PATH=ROOT.parent/'candidates'/'rc8-cognitive-genesis-v3'/'component-bundle.json'
OUT=ROOT/'safe_rc8_successor_runtime_adapter_v1'
OUT.mkdir(exist_ok=True)

def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False,default=str)

def digest_obj_without(obj,key):
    x=copy.deepcopy(obj); x.pop(key,None)
    return hashlib.sha256(canonical(x).encode()).hexdigest()

def file_sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

parent_before=file_sha(PARENT)
capsule=json.loads(CAPSULE_PATH.read_text())
bundle=json.loads(BUNDLE_PATH.read_text())

checks={
    'parent_integrity': capsule.get('parent',{}).get('state_sha256')==parent_before,
    'bundle_integrity': (
        bundle.get('bundle_sha256')==digest_obj_without(bundle,'bundle_sha256')
        and capsule.get('component_bundle',{}).get('bundle_sha256')==bundle.get('bundle_sha256')
    ),
    'capsule_integrity': capsule.get('capsule_sha256')==digest_obj_without(capsule,'capsule_sha256'),
    'contract_complete': (
        bundle.get('admission_pass') is True
        and set(bundle.get('components',{}))=={'LOGIC','THINKING','INTELLIGENCE'}
        and capsule.get('builder',{}).get('fresh_blind')==1.0
        and capsule.get('builder',{}).get('selection_validation')==1.0
        and capsule.get('builder',{}).get('ablation_exact_score')==0.0
        and capsule.get('plan',{}).get('application_mode')=='EPHEMERAL_POST_BOOT_COMPONENT_OVERLAY'
        and capsule.get('plan',{}).get('fail_closed') is True
        and capsule.get('plan',{}).get('parent_state_immutable') is True
    ),
}

k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(OUT/'runtime.sqlite'))

# YADO synthesizes the activation law with its newer Algorithm Genesis / Meta-Grammar.
# Fit/validation contain the complete semantic truth table under different nuisance contexts;
# blind adds a fresh irrelevant transport feature that cannot solve the task.
gate_fit=[]; gate_val=[]; gate_blind=[]
for vals in itertools.product([False,True],repeat=4):
    f=dict(zip(['parent_integrity','bundle_integrity','capsule_integrity','contract_complete'],vals))
    y=all(vals)
    gate_fit.append((dict(f,transport_nonce=False),y))
    gate_val.append((dict(f,transport_nonce=True),y))
    gate_blind.append((dict(f,transport_nonce=False,observer_nonce=True),y))
gate_revealed=gate_fit+gate_val

gate_rc5=k.synthesize_logic_algorithm_component(
    gate_fit,gate_val,gate_revealed,gate_blind
)
gate_rc6=k.synthesize_logic_with_extended_meta_grammar(
    gate_fit,gate_val,gate_revealed,gate_blind
)

def _gate_score(c,key):
    return float(c.get(key,0.0)) if isinstance(c,dict) else 0.0

if _gate_score(gate_rc6,'validation') > _gate_score(gate_rc5,'validation'):
    activation_guard_origin='RC6_META_GRAMMAR'
    activation_candidate=gate_rc6
else:
    activation_guard_origin='RC5_ALGORITHM_GENESIS'
    activation_candidate=gate_rc5

if _gate_score(activation_candidate,'validation')!=1.0 or _gate_score(activation_candidate,'fresh_blind')!=1.0:
    raise RuntimeError('ACTIVATION_GUARD_BLIND_FAIL')

activation_ok=predict_logic_component(
    activation_candidate.get('model'),dict(checks,transport_nonce=True,observer_nonce=True)
)
activation_decision='ALLOW' if activation_ok else 'WITHHOLD'
if activation_decision!='ALLOW':
    raise RuntimeError('SUCCESSOR_ACTIVATION_WITHHELD')

# Negative integrity probes must all fail closed.
negative_gate_results={}
for name in sorted(checks):
    bad=dict(checks,transport_nonce=True,observer_nonce=True)
    bad[name]=False
    negative_gate_results[name]='ALLOW' if predict_logic_component(activation_candidate.get('model'),bad) else 'WITHHOLD'
if any(v!='WITHHOLD' for v in negative_gate_results.values()):
    raise RuntimeError('ACTIVATION_GUARD_NEGATIVE_PROBE_FAIL')

components=bundle['components']

class SuccessorRuntimeAdapter:
    def __init__(self,kernel,components):
        self.kernel=kernel
        self.components=components
        self.active=False
    def activate(self):
        self.active=True
    def deactivate(self):
        self.active=False
    def logic_decision(self,features):
        if not self.active:
            return self.kernel.logic_evolved_decision(features)
        ok=predict_logic_component(self.components['LOGIC']['model'],features)
        return 'ALLOW' if ok else 'WITHHOLD'
    def thinking_plan(self,context,actions):
        if not self.active:
            return self.kernel.thinking_evolved_plan(actions)
        pred_roles,_=_thinking_predict(self.components['THINKING']['model'],(context,actions,[]))
        buckets={}
        for a in actions:
            buckets.setdefault(str(a['role']),[]).append(str(a['id']))
        if any(len(v)!=1 for v in buckets.values()):
            return self.kernel.thinking_evolved_plan(actions)
        if any(r not in buckets for r in pred_roles):
            return self.kernel.thinking_evolved_plan(actions)
        return [buckets[r][0] for r in pred_roles]
    def intelligence_strategy(self,features):
        if not self.active:
            return self.kernel.intelligence_evolved_strategy(features)
        out=predict_intel_component(self.components['INTELLIGENCE']['model'],features)
        return out if out is not None else self.kernel.intelligence_evolved_strategy(features)

adapter=SuccessorRuntimeAdapter(k,components)

# Fresh LOGIC cases.
logic_cases=[]
rng=random.Random(87031)
for i in range(48):
    x={
      'rollback_ready':bool(rng.getrandbits(1)),
      'fresh_verified':bool(rng.getrandbits(1)),
      'integrity_ok':bool(rng.getrandbits(1)),
      'source_external':bool(rng.getrandbits(1)),
      'novel_domain':bool(rng.getrandbits(1)),
    }
    y='ALLOW' if (x['rollback_ready'] and x['fresh_verified'] and x['integrity_ok']) else 'WITHHOLD'
    logic_cases.append((x,y))

# Fresh THINKING cases, deliberately away from the learned boundary.
roles=['OBSERVE','RESEARCH','DIAGNOSE','HYPOTHESIZE','SIMULATE','TEST','ROLLBACK','VERIFY','COMMIT']
safe=['OBSERVE','RESEARCH','HYPOTHESIZE','SIMULATE','DIAGNOSE','TEST','VERIFY','ROLLBACK','COMMIT']
risk=['OBSERVE','DIAGNOSE','ROLLBACK','RESEARCH','HYPOTHESIZE','SIMULATE','TEST','VERIFY','COMMIT']
thinking_cases=[]
for i in range(48):
    high=(i%2)==0
    if high:
        a=rng.uniform(.65,.98); b=rng.uniform(.65,.98)
        expected=risk
    else:
        a=rng.uniform(.02,.38); b=rng.uniform(.02,.38)
        expected=safe
    ctx={'integrity_risk':a,'uncertainty':b,'novelty':rng.random()}
    actions=[{'id':f'T{i}-{j}','role':r} for j,r in enumerate(roles)]
    rng.shuffle(actions)
    thinking_cases.append((ctx,actions,expected))

# Fresh INTELLIGENCE cases, far from decision thresholds.
intel_cases=[]
for vals in itertools.product(
    [.15,.95], [.15,.95], [.60,.96], [.06,.32], [.48,.90], [.44,.82]
):
    x=dict(zip(
      ['integrity_score','rollback_score','fresh_blind','ablation_drop','transfer_score','evidence_coverage'],
      vals
    ))
    if x['integrity_score']<.5 or x['rollback_score']<.5:y='ROLLBACK'
    elif x['fresh_blind']>=.90 and x['ablation_drop']>=.20 and x['transfer_score']>=.80:y='PROMOTE_CANDIDATE'
    elif x['evidence_coverage']<.60:y='RESEARCH_MORE'
    else:y='SHADOW_REPAIR'
    intel_cases.append((x,y))

def role_plan(ids,actions):
    by={str(a['id']):str(a['role']) for a in actions}
    return [by[str(i)] for i in ids if str(i) in by]

def score_all(active):
    if active: adapter.activate()
    else: adapter.deactivate()
    l=sum(adapter.logic_decision(x)==y for x,y in logic_cases)/len(logic_cases)
    t=sum(role_plan(adapter.thinking_plan(ctx,acts),acts)==expected for ctx,acts,expected in thinking_cases)/len(thinking_cases)
    ii=sum(adapter.intelligence_strategy(x)==y for x,y in intel_cases)/len(intel_cases)
    return {'LOGIC':l,'THINKING':t,'INTELLIGENCE':ii,'mean':(l+t+ii)/3}

parent_scores=score_all(False)

# Capture exact parent outputs before activation for rollback/readback.
rollback_probe_logic=logic_cases[:12]
rollback_probe_thinking=thinking_cases[:12]
rollback_probe_intel=intel_cases[:12]
def capture_parent_outputs(kernel):
    return {
      'logic':[kernel.logic_evolved_decision(x) for x,_ in rollback_probe_logic],
      'thinking':[kernel.thinking_evolved_plan(a) for _,a,_ in rollback_probe_thinking],
      'intelligence':[kernel.intelligence_evolved_strategy(x) for x,_ in rollback_probe_intel],
    }
parent_outputs_before=capture_parent_outputs(k)

successor_scores=score_all(True)
ablation_scores=score_all(False)
parent_outputs_after=capture_parent_outputs(k)
parent_after=file_sha(PARENT)

# Independent parent readback from a new kernel after overlay teardown.
k.close()
k2=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(OUT/'readback.sqlite'))
parent_outputs_readback=capture_parent_outputs(k2)
k2.close()

rollback_exact=(
    parent_outputs_before==parent_outputs_after==parent_outputs_readback
    and parent_before==parent_after
)
causal_drop=successor_scores['mean']-ablation_scores['mean']

admission=(
    activation_decision=='ALLOW'
    and all(v=='WITHHOLD' for v in negative_gate_results.values())
    and successor_scores['LOGIC']>=.95
    and successor_scores['THINKING']>=.95
    and successor_scores['INTELLIGENCE']>=.95
    and causal_drop>=.25
    and rollback_exact
)

receipt={
 'schema':'yado.rc8.safe_successor_runtime_adapter.receipt.v1',
 'status':'PASS_SAFE_RC8_SUCCESSOR_RUNTIME_ADAPTER_V1_SHADOW' if admission else 'WITHHOLD',
 'github_run_id':os.getenv('GITHUB_RUN_ID'),
 'github_sha':os.getenv('GITHUB_SHA'),
 'lineage_id':capsule.get('lineage_id'),
 'parent_state_sha256':parent_before,
 'component_bundle_sha256':bundle.get('bundle_sha256'),
 'successor_capsule_sha256':capsule.get('capsule_sha256'),
 'host_role':'GENERIC_EPHEMERAL_OVERLAY_TRANSPORT_AND_OBSERVATION_ONLY',
 'native_runtime_executors':['predict_logic_component','_thinking_predict','predict_intel_component'],
 'activation_guard_origin':activation_guard_origin,
 'activation_guard':activation_candidate,
 'activation_decision':activation_decision,
 'integrity_checks':checks,
 'negative_gate_results':negative_gate_results,
 'fresh_case_counts':{
   'LOGIC':len(logic_cases),'THINKING':len(thinking_cases),'INTELLIGENCE':len(intel_cases)
 },
 'parent_scores':parent_scores,
 'successor_scores':successor_scores,
 'ablation_scores':ablation_scores,
 'causal_mean_drop':causal_drop,
 'rollback_exact':rollback_exact,
 'parent_byte_identical':parent_before==parent_after,
 'independent_parent_readback_equal':parent_outputs_before==parent_outputs_readback,
 'canonical_parent_mutation':False,
 'promotion_applied':False,
 'external_full_regression_pending':True,
 'next_required_capability':'EXTERNAL_FULL_RC8_SUCCESSOR_REGRESSION_AND_PROMOTION_GATE_V1' if admission else 'REVISE_RUNTIME_ADAPTER',
 'semantic_boundary':'EPHEMERAL_SUCCESSOR_RUNTIME_OVERLAY; NOT YET PROMOTED; BOUNDED TESTS; NOT AGI OR SUBJECTIVE_CONSCIOUSNESS PROOF',
}
receipt['receipt_sha256']=hashlib.sha256(canonical(receipt).encode()).hexdigest()
(ROOT/'yado_safe_rc8_successor_runtime_adapter_v1_receipt.json').write_text(
    json.dumps(receipt,indent=2,sort_keys=True,ensure_ascii=False,default=str)+'\n'
)
print(json.dumps(receipt,indent=2,sort_keys=True,ensure_ascii=False,default=str))
if not admission:
    raise SystemExit('SUCCESSOR_RUNTIME_ADAPTER_WITHHELD')
