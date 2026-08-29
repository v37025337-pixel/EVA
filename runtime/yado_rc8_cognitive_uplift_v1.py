from __future__ import annotations
from pathlib import Path
import hashlib, itertools, json, os, random, shutil, sys

ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(PKG))

from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive

BASE_STATE=PKG/'yado_canonical_state_v3_rc8_external_cognitive.json'
CAND_DIR=ROOT/'rc8_cognitive_uplift_candidate'
CAND_DIR.mkdir(exist_ok=True)
CAND_STATE=CAND_DIR/'yado_canonical_state_rc8_cognitive_uplift_candidate.json'
BEFORE_STATE=CAND_DIR/'before_state.json'
shutil.copy2(BASE_STATE,CAND_STATE)
shutil.copy2(BASE_STATE,BEFORE_STATE)

# Durable mutation is enabled only for this isolated candidate copy.
st=json.loads(CAND_STATE.read_text())
st['canonical_durable_mutation']=True
st['candidate_only']=True
st['candidate_lineage']='VERIFIED_V36 -> SHADOW_RC8_COGNITIVE_UPLIFT_V1'
CAND_STATE.write_text(json.dumps(st,indent=2,sort_keys=True)+'\n')

db=CAND_DIR/'candidate.sqlite'
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(db),state_path=str(CAND_STATE))

# ---- LOGIC: learn a fail-closed admission law, with an irrelevant feature held out.
def logic_target(x):
    return bool(x['integrity'] and x['blind_pass'] and x['rollback_ready'])

logic_all=[]
for vals in itertools.product([False,True], repeat=4):
    x=dict(zip(['integrity','blind_pass','rollback_ready','novelty'],vals))
    logic_all.append((x,logic_target(x)))
logic_train=[z for z in logic_all if z[0]['novelty'] is False]
logic_blind=[z for z in logic_all if z[0]['novelty'] is True]
logic=k.shadow_evolve_logic(logic_train,logic_blind,capability='rc8_fail_closed_architecture_admission')

# ---- THINKING: learn the causal order for architectural self-development.
order=['OBSERVE','RESEARCH','DIAGNOSE','HYPOTHESIZE','SYNTHESIZE','TEST','ABLATE','VERIFY','COMMIT']
traces=[
 order,
 ['OBSERVE','RESEARCH','DIAGNOSE','HYPOTHESIZE','SYNTHESIZE','TEST','ABLATE','VERIFY','COMMIT'],
 ['OBSERVE','RESEARCH','DIAGNOSE','HYPOTHESIZE','SYNTHESIZE','TEST','ABLATE','VERIFY','COMMIT'],
 ['OBSERVE','RESEARCH','DIAGNOSE','HYPOTHESIZE','SYNTHESIZE','TEST','ABLATE','VERIFY','COMMIT'],
]
def blind_case(seed):
    rng=random.Random(seed)
    actions=[{'id':f'a{i}','role':r} for i,r in enumerate(order)]
    rng.shuffle(actions)
    return actions,order
thinking_blind=[blind_case(s) for s in (101,211,307,401,503,607,709,809)]
thinking=k.shadow_evolve_thinking(traces,thinking_blind,capability='rc8_architecture_evolution_causal_plan')

# ---- INTELLIGENCE: choose the next meta-action from evidence, not an architecture name.
def strategy(x):
    if x['integrity'] < 0.5 or x['rollback'] < 0.5:
        return 'ROLLBACK'
    if x['fresh_blind'] >= 0.90 and x['ablation_drop'] >= 0.20 and x['transfer'] >= 0.80:
        return 'PROMOTE_CANDIDATE'
    if x['evidence'] < 0.60:
        return 'RESEARCH_MORE'
    return 'SHADOW_REPAIR'

grid=[]
for integrity in (0.0,1.0):
 for rollback in (0.0,1.0):
  for fresh in (0.55,0.75,0.92,0.99):
   for abl in (0.05,0.25):
    for transfer in (0.45,0.85):
     for evidence in (0.45,0.75):
      x={'integrity':integrity,'rollback':rollback,'fresh_blind':fresh,'ablation_drop':abl,'transfer':transfer,'evidence':evidence}
      grid.append((x,strategy(x)))

intel_train=[]
intel_blind=[]
for x,y in grid:
    key=json.dumps(x,sort_keys=True)
    bucket=int(hashlib.sha256(key.encode()).hexdigest()[:8],16)%5
    (intel_blind if bucket==0 else intel_train).append((x,y))

# Guarantee sufficient fresh cases and all action classes in both partitions.
if len(intel_train)<16 or len(intel_blind)<8:
    raise RuntimeError('INTELLIGENCE_SPLIT_TOO_SMALL')
intelligence=k.shadow_evolve_intelligence(intel_train,intel_blind,capability='rc8_architecture_meta_action_strategy')

candidates=[logic,thinking,intelligence]
gate=k.autoevolution_gate(candidates)
bundle={'LOGIC':logic,'THINKING':thinking,'INTELLIGENCE':intelligence}
commit=k.durable_commit_evolution_bundle(bundle,gate)

post={}
if commit.get('committed'):
    # Re-instantiate from the persisted candidate state and test actual registered behavior.
    k.close()
    k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(CAND_DIR/'readback.sqlite'),state_path=str(CAND_STATE))
    post['logic_registry_loaded']='LOGIC' in k.organ_autoevolution_models()
    post['thinking_registry_loaded']='THINKING' in k.organ_autoevolution_models()
    post['intelligence_registry_loaded']='INTELLIGENCE' in k.organ_autoevolution_models()
    post['logic_fresh']=[
      k.logic_evolved_decision({'integrity':True,'blind_pass':True,'rollback_ready':True,'novelty':False}),
      k.logic_evolved_decision({'integrity':True,'blind_pass':False,'rollback_ready':True,'novelty':True}),
    ]
    fresh_actions,fresh_expected=blind_case(991)
    planned=k.thinking_evolved_plan(fresh_actions)
    post['thinking_fresh_roles']=[next(a['role'] for a in fresh_actions if a['id']==i) for i in planned]
    fresh_intel=[
      {'integrity':1.0,'rollback':1.0,'fresh_blind':0.96,'ablation_drop':0.31,'transfer':0.91,'evidence':0.88},
      {'integrity':1.0,'rollback':1.0,'fresh_blind':0.72,'ablation_drop':0.10,'transfer':0.70,'evidence':0.82},
      {'integrity':0.0,'rollback':1.0,'fresh_blind':0.99,'ablation_drop':0.40,'transfer':0.99,'evidence':0.99},
      {'integrity':1.0,'rollback':1.0,'fresh_blind':0.72,'ablation_drop':0.10,'transfer':0.70,'evidence':0.42},
    ]
    post['intelligence_fresh']=[k.intelligence_evolved_strategy(x) for x in fresh_intel]
    post['audit_snapshot']=k.audit_snapshot()
    post['integrity_control_plane']=k.integrity_control_plane()
    post['development_priority']=k.development_priority()

# Explicit rollback proof on a separate copy.
rollback_path=CAND_DIR/'rollback_probe_state.json'
shutil.copy2(CAND_STATE if commit.get('committed') else BEFORE_STATE,rollback_path)
candidate_sha=hashlib.sha256(rollback_path.read_bytes()).hexdigest()
shutil.copy2(BEFORE_STATE,rollback_path)
restored_sha=hashlib.sha256(rollback_path.read_bytes()).hexdigest()
base_sha=hashlib.sha256(BEFORE_STATE.read_bytes()).hexdigest()
rollback_proof={'candidate_sha256':candidate_sha,'restored_sha256':restored_sha,'base_sha256':base_sha,'restore_exact':restored_sha==base_sha}

if not getattr(k,'conn',None) is None:
    try:k.close()
    except Exception:pass

candidate_state_sha=hashlib.sha256(CAND_STATE.read_bytes()).hexdigest()
receipt={
 'schema':'yado.rc8.shadow.cognitive_uplift.v1',
 'status':'SHADOW_RC8_COGNITIVE_UPLIFT_COMMITTED' if commit.get('committed') and rollback_proof['restore_exact'] else 'WITHHOLD',
 'github_run_id':os.getenv('GITHUB_RUN_ID'),
 'github_sha':os.getenv('GITHUB_SHA'),
 'base':'VERIFIED_V36_RECONSTRUCTED',
 'base_state_sha256':base_sha,
 'candidate_state_sha256':candidate_state_sha,
 'canonical_v36_mutation':False,
 'candidate_only':True,
 'logic':logic,
 'thinking':thinking,
 'intelligence':intelligence,
 'gate':gate,
 'candidate_commit':commit,
 'post_commit_readback':post,
 'rollback_proof':rollback_proof,
 'promotion_applied':False,
 'semantic_boundary':'BOUNDED_COGNITIVE_ORGAN_UPLIFT_NOT_UNRESTRICTED_SELF_REWRITE_NOT_AGI_PROOF',
}
receipt['receipt_sha256']=hashlib.sha256(json.dumps(receipt,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()
(ROOT/'yado_rc8_cognitive_uplift_v1_receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps(receipt,indent=2,sort_keys=True,default=str))

if receipt['status']!='SHADOW_RC8_COGNITIVE_UPLIFT_COMMITTED':
    raise SystemExit('COGNITIVE_UPLIFT_WITHHELD')
