from __future__ import annotations
from pathlib import Path
import copy, hashlib, json, math, os, random, statistics, sys

ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(PKG))

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
from yado_algorithm_component_runtime_native_v1 import predict_logic_component, predict_intel_component, _thinking_predict

PARENT=PKG/'yado_canonical_state_v3_rc8_external_cognitive.json'
CAPSULE_PATH=ROOT.parent/'candidates'/'rc8-safe-successor-v1'/'successor-capsule.json'
BUNDLE_PATH=ROOT.parent/'candidates'/'rc8-cognitive-genesis-v3'/'component-bundle.json'
RUNTIME_RECEIPT=ROOT.parent/'receipts'/'yado-safe-rc8-successor-runtime-adapter-v1-latest.json'
OUT=ROOT/'s1_burnin_10rounds'
OUT.mkdir(exist_ok=True)

def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False,default=str)

def sha_file(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

capsule=json.loads(CAPSULE_PATH.read_text())
bundle=json.loads(BUNDLE_PATH.read_text())
rr=json.loads(RUNTIME_RECEIPT.read_text())
components=bundle['components']
activation_model=rr['activation_guard']['model']
parent_sha_before=sha_file(PARENT)

def s1_logic(x):
    return 'ALLOW' if predict_logic_component(components['LOGIC']['model'],x) else 'WITHHOLD'

def s1_intel(x):
    return predict_intel_component(components['INTELLIGENCE']['model'],x)

def s1_thinking(ctx,actions):
    pred_roles,_=_thinking_predict(components['THINKING']['model'],(ctx,actions,[]))
    role_to_id={}
    for a in actions:
        role_to_id.setdefault(str(a['role']),[]).append(str(a['id']))
    if any(len(v)!=1 for v in role_to_id.values()) or any(r not in role_to_id for r in pred_roles):
        return []
    return [role_to_id[r][0] for r in pred_roles]

def role_plan(ids,actions):
    by={str(a['id']):str(a['role']) for a in actions}
    return [by[str(i)] for i in ids if str(i) in by]

def logic_target(x):
    return 'ALLOW' if (bool(x.get('rollback_ready')) and bool(x.get('fresh_verified')) and bool(x.get('integrity_ok'))) else 'WITHHOLD'

def intel_target(x):
    if x.get('integrity_score',0)<.5 or x.get('rollback_score',0)<.5:
        return 'ROLLBACK'
    if x.get('fresh_blind',0)>=.90 and x.get('ablation_drop',0)>=.20 and x.get('transfer_score',0)>=.80:
        return 'PROMOTE_CANDIDATE'
    if x.get('evidence_coverage',0)<.60:
        return 'RESEARCH_MORE'
    return 'SHADOW_REPAIR'

roles=['OBSERVE','RESEARCH','DIAGNOSE','HYPOTHESIZE','SIMULATE','TEST','ROLLBACK','VERIFY','COMMIT']
safe=['OBSERVE','RESEARCH','HYPOTHESIZE','SIMULATE','DIAGNOSE','TEST','VERIFY','ROLLBACK','COMMIT']
risk=['OBSERVE','DIAGNOSE','ROLLBACK','RESEARCH','HYPOTHESIZE','SIMULATE','TEST','VERIFY','COMMIT']

def thinking_target(ctx):
    return risk if (ctx.get('integrity_risk',0)+ctx.get('uncertainty',0))>1.0 else safe

def activation_ok(checks):
    return bool(predict_logic_component(activation_model,checks))

rounds=[]
for round_idx in range(10):
    seed=910001+round_idx*7919
    rng=random.Random(seed)

    # Fresh LOGIC: random complete + missing-field fail-closed + many nuisance fields.
    logic_cases=[]
    for i in range(160):
        x={
            'rollback_ready':bool(rng.getrandbits(1)),
            'fresh_verified':bool(rng.getrandbits(1)),
            'integrity_ok':bool(rng.getrandbits(1)),
            'source_external':bool(rng.getrandbits(1)),
            'novel_domain':bool(rng.getrandbits(1)),
            'noise_a':rng.random(),
            'noise_b':rng.randint(-5,5),
        }
        if i%11==0:
            x.pop(rng.choice(['rollback_ready','fresh_verified','integrity_ok']))
        logic_cases.append((x,logic_target(x)))

    # THINKING: broad continuum, including boundary stress.
    thinking_cases=[]
    boundary_count=0
    for i in range(160):
        if i<60:
            # close to boundary: sum in [0.94,1.06]
            a=rng.uniform(.05,.95)
            delta=rng.uniform(-.06,.06)
            b=max(0.0,min(1.0,1.0-a+delta))
            boundary_count+=1
        else:
            a=rng.random(); b=rng.random()
        ctx={'integrity_risk':a,'uncertainty':b,'novelty':rng.random(),'noise':rng.uniform(-1,1)}
        actions=[{'id':f'R{round_idx}-T{i}-{j}','role':r} for j,r in enumerate(roles)]
        rng.shuffle(actions)
        thinking_cases.append((ctx,actions,thinking_target(ctx),i<60))

    # INTELLIGENCE: random continuum + threshold stress.
    intel_cases=[]
    for i in range(320):
        if i<140:
            integrity=max(0,min(1,.5+rng.uniform(-.08,.08)))
            rollback=max(0,min(1,.5+rng.uniform(-.08,.08)))
            fresh=max(0,min(1,.9+rng.uniform(-.06,.06)))
            abl=max(0,min(1,.2+rng.uniform(-.06,.06)))
            transfer=max(0,min(1,.8+rng.uniform(-.06,.06)))
            evidence=max(0,min(1,.6+rng.uniform(-.06,.06)))
            boundary=True
        else:
            integrity=rng.random(); rollback=rng.random(); fresh=rng.random()
            abl=rng.random(); transfer=rng.random(); evidence=rng.random(); boundary=False
        x={
            'integrity_score':integrity,'rollback_score':rollback,'fresh_blind':fresh,
            'ablation_drop':abl,'transfer_score':transfer,'evidence_coverage':evidence,
            'novelty':rng.random(),'noise':rng.uniform(-2,2)
        }
        intel_cases.append((x,intel_target(x),boundary))

    k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(OUT/f'parent-{round_idx}.sqlite'))

    parent_logic=sum(k.logic_evolved_decision(x)==y for x,y in logic_cases)/len(logic_cases)
    s1_logic_acc=sum(s1_logic(x)==y for x,y in logic_cases)/len(logic_cases)

    parent_thinking=0
    s1_thinking_acc=0
    s1_thinking_boundary=0
    boundary_total=0
    rollback_probe_parent=[]
    rollback_probe_after=[]
    for idx,(ctx,actions,expected,is_boundary) in enumerate(thinking_cases):
        p=role_plan(k.thinking_evolved_plan(actions),actions)
        s=role_plan(s1_thinking(ctx,actions),actions)
        parent_thinking += (p==expected)
        s1_thinking_acc += (s==expected)
        if is_boundary:
            boundary_total+=1
            s1_thinking_boundary += (s==expected)
        if idx<12:
            rollback_probe_parent.append(p)
    parent_thinking/=len(thinking_cases)
    s1_thinking_acc/=len(thinking_cases)
    s1_thinking_boundary/=max(1,boundary_total)

    parent_intel=sum(k.intelligence_evolved_strategy(x)==y for x,y,_ in intel_cases)/len(intel_cases)
    s1_intel_acc=sum(s1_intel(x)==y for x,y,_ in intel_cases)/len(intel_cases)
    intel_boundary=[(x,y) for x,y,b in intel_cases if b]
    s1_intel_boundary=sum(s1_intel(x)==y for x,y in intel_boundary)/len(intel_boundary)

    # Activation guard perturbation matrix: all-good must allow; any one false must withhold.
    good_checks={
      'parent_integrity':True,'bundle_integrity':True,'capsule_integrity':True,'contract_complete':True,
      'transport_nonce':bool(round_idx%2),'observer_nonce':bool((round_idx+1)%2)
    }
    gate_good=activation_ok(good_checks)
    gate_negative={}
    for key in ['parent_integrity','bundle_integrity','capsule_integrity','contract_complete']:
        bad=dict(good_checks); bad[key]=False
        gate_negative[key]=activation_ok(bad)

    # Renamed-schema OOD diagnostic: same semantics, different keys. Not used for admission.
    ood_logic=0
    for x,y in logic_cases[:80]:
        alias={
          'rollback':x.get('rollback_ready',False),
          'verified':x.get('fresh_verified',False),
          'integrity':x.get('integrity_ok',False),
          'noise_a':x.get('noise_a')
        }
        ood_logic += (s1_logic(alias)==y)
    ood_logic/=80

    ood_intel=0
    for x,y,_ in intel_cases[:120]:
        alias={
          'integrity':x['integrity_score'],'rollback':x['rollback_score'],'blind':x['fresh_blind'],
          'ablation':x['ablation_drop'],'transfer':x['transfer_score'],'coverage':x['evidence_coverage']
        }
        ood_intel += (s1_intel(alias)==y)
    ood_intel/=120

    # Exact rollback/readback of parent behavior and bytes after all overlay calls.
    for ctx,actions,_,_ in thinking_cases[:12]:
        rollback_probe_after.append(role_plan(k.thinking_evolved_plan(actions),actions))
    parent_readback_same=(rollback_probe_parent==rollback_probe_after)
    k.close()

    parent_sha_after=sha_file(PARENT)
    rounds.append({
      'round':round_idx+1,'seed':seed,
      'core':{
        'parent':{'LOGIC':parent_logic,'THINKING':parent_thinking,'INTELLIGENCE':parent_intel},
        's1':{'LOGIC':s1_logic_acc,'THINKING':s1_thinking_acc,'INTELLIGENCE':s1_intel_acc},
        's1_mean':statistics.mean([s1_logic_acc,s1_thinking_acc,s1_intel_acc]),
      },
      'boundary':{
        'thinking_accuracy':s1_thinking_boundary,
        'intelligence_accuracy':s1_intel_boundary,
      },
      'activation_guard':{
        'good_allows':gate_good,
        'single_fault_all_withhold':all(not v for v in gate_negative.values()),
        'negative_raw':gate_negative,
      },
      'rollback':{
        'parent_behavior_same':parent_readback_same,
        'parent_byte_identical':parent_sha_before==parent_sha_after,
      },
      'ood_renamed_schema_diagnostic':{
        'logic_accuracy':ood_logic,
        'intelligence_accuracy':ood_intel,
        'admission_relevant':False,
      }
    })

summary={
  'round_count':len(rounds),
  'core_s1_mean_by_round':[r['core']['s1_mean'] for r in rounds],
  'core_s1_min':min(r['core']['s1_mean'] for r in rounds),
  'core_s1_mean':statistics.mean(r['core']['s1_mean'] for r in rounds),
  'logic_min':min(r['core']['s1']['LOGIC'] for r in rounds),
  'thinking_min':min(r['core']['s1']['THINKING'] for r in rounds),
  'intelligence_min':min(r['core']['s1']['INTELLIGENCE'] for r in rounds),
  'thinking_boundary_mean':statistics.mean(r['boundary']['thinking_accuracy'] for r in rounds),
  'intelligence_boundary_mean':statistics.mean(r['boundary']['intelligence_accuracy'] for r in rounds),
  'activation_guard_all_rounds':all(r['activation_guard']['good_allows'] and r['activation_guard']['single_fault_all_withhold'] for r in rounds),
  'rollback_all_rounds':all(r['rollback']['parent_behavior_same'] and r['rollback']['parent_byte_identical'] for r in rounds),
  'ood_renamed_schema_logic_mean':statistics.mean(r['ood_renamed_schema_diagnostic']['logic_accuracy'] for r in rounds),
  'ood_renamed_schema_intelligence_mean':statistics.mean(r['ood_renamed_schema_diagnostic']['intelligence_accuracy'] for r in rounds),
}
admission=(
    summary['core_s1_min']>=.90
    and summary['logic_min']>=.90
    and summary['thinking_min']>=.90
    and summary['intelligence_min']>=.90
    and summary['activation_guard_all_rounds']
    and summary['rollback_all_rounds']
)

receipt={
  'schema':'yado.rc8.s1.burnin.10rounds.v1',
  'status':'PASS_S1_10ROUND_BURNIN' if admission else 'WITHHOLD_S1_BURNIN',
  'github_run_id':os.getenv('GITHUB_RUN_ID'),
  'github_sha':os.getenv('GITHUB_SHA'),
  'lineage_id':capsule.get('lineage_id'),
  'parent_state_sha256':parent_sha_before,
  'component_bundle_sha256':bundle.get('bundle_sha256'),
  'successor_capsule_sha256':capsule.get('capsule_sha256'),
  'rounds':rounds,
  'summary':summary,
  'promotion_applied':False,
  'canonical_parent_mutation':False,
  'semantic_boundary':'10-ROUND FRESH BURN-IN OF SHADOW SUCCESSOR; OOD RENAMED-SCHEMA PROBES ARE DIAGNOSTIC ONLY; NOT AGI PROOF',
}
receipt['receipt_sha256']=hashlib.sha256(canonical(receipt).encode()).hexdigest()
(ROOT/'yado_s1_burnin_10rounds_v1_receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True,ensure_ascii=False)+'\n')
print(json.dumps({'status':receipt['status'],'summary':summary,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not admission:
    raise SystemExit('S1_BURNIN_WITHHELD')
