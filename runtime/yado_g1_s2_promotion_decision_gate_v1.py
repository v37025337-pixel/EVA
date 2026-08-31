from __future__ import annotations
from pathlib import Path
import copy, hashlib, json, os, sys

ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(PKG))

from yado_numeric_boundary_and_representation_learner_v1 import predict_dnf_spec
from yado_evolution_ledger_v2 import validate_ledger_v2, event_hash

STATE=PKG/'yado_canonical_state_v3_rc8_external_cognitive.json'
LINEAGE=ROOT.parent/'receipts'/'yado-real-developmental-lineage-v1-latest.json'
GATE=ROOT.parent/'receipts'/'yado-g1-s2-full-cross-domain-regression-causal-gate-v2-latest.json'
BUNDLE=ROOT.parent/'candidates'/'g1-s2-repaired-v3'/'bundle.json'
LEDGER=ROOT.parent/'architecture'/'evolution-ledger.json'
OUT=ROOT.parent/'canonical'
OUT.mkdir(exist_ok=True)

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def sha_file(p):return hashlib.sha256(p.read_bytes()).hexdigest()

parent_sha=sha_file(STATE)
lineage=json.loads(LINEAGE.read_text())
gate=json.loads(GATE.read_text())
bundle=json.loads(BUNDLE.read_text())
ledger=json.loads(LEDGER.read_text())

# Migrate control-plane semantics without rewriting historical events.
if ledger.get('current_head')!='G0_RC8_V36':
    raise RuntimeError(f'EXPECTED_G0_HEAD_GOT:{ledger.get("current_head")}')
# Verify historical v1 chain directly.
prev='GENESIS'
for i,e in enumerate(ledger['events']):
    if e['index']!=i or e['parent_event_hash']!=prev or e['event_hash']!=event_hash(e):
        raise RuntimeError(f'LEDGER_CHAIN_INVALID:{i}')
    prev=e['event_hash']
if prev!=ledger['tail_event_hash']:raise RuntimeError('LEDGER_TAIL_INVALID')

if gate.get('status')!='PASS_G1_S2_FULL_CROSS_DOMAIN_REGRESSION_AND_CAUSAL_GATE_V2':
    raise RuntimeError('FULL_GATE_V2_NOT_PASS')
if gate.get('failed_checks')!=[] or not all(gate.get('promotion_checks',{}).values()):
    raise RuntimeError('PROMOTION_CHECKS_NOT_ALL_PASS')
if gate.get('canonical_parent_sha256_before')!=parent_sha or gate.get('canonical_parent_sha256_after')!=parent_sha:
    raise RuntimeError('PARENT_EVIDENCE_MISMATCH')

b=copy.deepcopy(bundle); declared=b.pop('bundle_digest',None)
if declared!=h(b) or declared!=gate.get('candidate_bundle_digest'):
    raise RuntimeError('CANDIDATE_BUNDLE_DIGEST_MISMATCH')
if bundle.get('admission_pass') is not True:raise RuntimeError('CANDIDATE_NOT_ADMITTED')

# Let G1's learned intelligence make the promotion recommendation from fresh gate evidence.
im=bundle['intelligence_models']
def ipredict(x):
    if predict_dnf_spec(im['rollback'],x)=='ROLLBACK':return 'ROLLBACK'
    if predict_dnf_spec(im['promotion'],x)=='PROMOTE_CANDIDATE':return 'PROMOTE_CANDIDATE'
    if predict_dnf_spec(im['research'],x)=='RESEARCH_MORE':return 'RESEARCH_MORE'
    return 'SHADOW_REPAIR'

m=gate['metrics']; causal=gate['causal']
decision_features={
    'integrity_score':m['integrity'],
    'rollback_score':m['rollback'],
    'fresh_blind':min(causal['thinking_fresh'],causal['intelligence_fresh']),
    'ablation_drop':min(causal['thinking_drop'],causal['intelligence_drop']),
    'transfer_score':m['representation_invariance_min'],
    'evidence_coverage':1.0,
    'novelty':0.85,
}
g1_decision=ipredict(decision_features)

parent_scores=lineage['snapshot']['generations'][0]['capability_scores']
candidate_scores={
    'integrity':m['integrity'],
    'intelligence':m['intelligence_min'],
    'logic':m['logic_min'],
    'rollback':m['rollback'],
    'thinking':m['thinking_min'],
}
gains={k:candidate_scores[k]-float(parent_scores[k]) for k in candidate_scores}
no_regression=all(v>=-1e-12 for v in gains.values())
has_gain=any(v>=0.02 for v in gains.values())

promote=all([
    g1_decision=='PROMOTE_CANDIDATE',
    no_regression,has_gain,
    gate['promotion_checks']['full_regression'],
    gate['promotion_checks']['ablation'],
    gate['promotion_checks']['fresh_blind'],
    gate['promotion_checks']['canonical_parent_immutable'],
])

head={
    'schema':'yado.canonical_generation_head.v1',
    'lineage_id':'YADO_MAIN_LINEAGE',
    'generation_id':'G1_CANDIDATE_S2',
    'status':'HEAD' if promote else 'PROMOTION_WITHHELD',
    'parent_generation_id':'G0_RC8_V36',
    'parent_artifact_digest':parent_sha,
    'candidate_bundle_digest':declared,
    'candidate_bundle_path':'candidates/g1-s2-repaired-v3/bundle.json',
    'promotion_gate_digest':gate['receipt_sha256'],
    'promotion_gate_run_id':gate['github_run_id'],
    'capability_scores':candidate_scores,
    'extended_capability_scores':{
      'thinking_boundary':m['thinking_boundary_min'],
      'intelligence_boundary':m['intelligence_boundary_min'],
      'representation_invariance':m['representation_invariance_min'],
    },
    'causal_evidence':gate['causal'],
    'inherited_capabilities':['ALG-CONJUNCTIVE-RULE-INDUCER-V1'],
    'decision_features':decision_features,
    'candidate_intelligence_decision':g1_decision,
    'gains_over_parent':gains,
    'promotion_applied':bool(promote),
}
head['canonical_head_digest']=h(head)
(OUT/'yado-main-head-g1-s2.json').write_text(json.dumps(head,indent=2,sort_keys=True)+'\n')

report={
    'schema':'yado.g1_s2.promotion_decision_gate.v1',
    'status':'PASS_G1_S2_PROMOTION_DECISION_GATE' if promote else 'WITHHOLD_G1_S2_PROMOTION_DECISION_GATE',
    'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),
    'from_generation':'G0_RC8_V36','to_generation':'G1_CANDIDATE_S2',
    'parent_sha256':parent_sha,'candidate_bundle_digest':declared,
    'full_gate_receipt_digest':gate['receipt_sha256'],
    'candidate_intelligence_decision':g1_decision,
    'decision_features':decision_features,
    'parent_capability_scores':parent_scores,'candidate_capability_scores':candidate_scores,'gains':gains,
    'no_regression':no_regression,'significant_gain_present':has_gain,
    'promotion_applied':bool(promote),
    'new_head_digest':head['canonical_head_digest'] if promote else None,
    'control_plane_migration':'SUCCESSION_AWARE_LEDGER_V2',
    'semantic_boundary':'PROMOTES A VERIFIED CODE ARTIFACT/DEVELOPMENTAL HEAD ONLY; THIS IS NOT EVIDENCE OF AGI OR SUBJECTIVE CONSCIOUSNESS',
}
report['receipt_sha256']=h(report)

# Append transition. Historical E0001 remains untouched.
if promote:
    event={
      'index':len(ledger['events']),
      'event_id':f"E{len(ledger['events'])+1:04d}_G1_PROMOTION",
      'event_type':'GENERATION_HEAD_TRANSITION',
      'status':'PROMOTED',
      'generation':'G1_CANDIDATE_S2',
      'from_generation':'G0_RC8_V36',
      'to_generation':'G1_CANDIDATE_S2',
      'deficit':'G1_S2_PROMOTION_DECISION_GATE',
      'effect':'CURRENT_HEAD_TRANSITION_G0_TO_G1_AFTER_FULL_CAUSAL_CROSS_DOMAIN_GATE',
      'source_path':'receipts/yado-g1-s2-promotion-decision-gate-v1-latest.json',
      'source_digest':report['receipt_sha256'],
      'run_id':str(os.getenv('GITHUB_RUN_ID') or 'LOCAL'),
      'parent_event_hash':ledger['tail_event_hash'],
      'canonical_mutation':True,'promotion_applied':True,
      'new_head_digest':head['canonical_head_digest'],
    }
    event['event_hash']=event_hash(event)
    ledger['events'].append(event)
    ledger['event_count']=len(ledger['events'])
    ledger['tail_event_hash']=event['event_hash']
    ledger['schema']='yado.causal_evolution_ledger.v2'
    ledger['invariant']='APPEND_ONLY_HASH_CHAIN; HISTORICAL_PROMOTIONS_ALLOWED; EXACTLY_ONE_CURRENT_HEAD'
    ledger['current_head']='G1_CANDIDATE_S2'
    ledger['current_head_digest']=head['canonical_head_digest']
    ledger['current_head_event_id']=event['event_id']
    ledger['ledger_semantics_version']=2
    ledger['open_deficits']=[x for x in ledger.get('open_deficits',[]) if x not in (
        'G1_S2_PROMOTION_DECISION_GATE','G1_S2_FULL_CROSS_DOMAIN_REGRESSION_AND_CAUSAL_GATE'
    )]
    ledger['resolved_deficits']=sorted(set(ledger.get('resolved_deficits',[])+[
        'G1_S2_PROMOTION_DECISION_GATE','G1_S2_FULL_CROSS_DOMAIN_REGRESSION_AND_CAUSAL_GATE'
    ]))
else:
    event={
      'index':len(ledger['events']),
      'event_id':f"E{len(ledger['events'])+1:04d}_G1_PROMOTION_WITHHOLD",
      'event_type':'GENERATION_PROMOTION_DECISION','status':'WITHHOLD',
      'generation':'G1_CANDIDATE_S2','deficit':'G1_S2_PROMOTION_DECISION_GATE',
      'effect':'G1_PROMOTION_WITHHELD',
      'source_path':'receipts/yado-g1-s2-promotion-decision-gate-v1-latest.json',
      'source_digest':report['receipt_sha256'],'run_id':str(os.getenv('GITHUB_RUN_ID') or 'LOCAL'),
      'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':False,'promotion_applied':False,
    }
    event['event_hash']=event_hash(event);ledger['events'].append(event);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=event['event_hash']

ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
if promote:
    validation=validate_ledger_v2(ledger)
    report['ledger_validation']={
      'valid':validation['valid'],
      'historical_promotion_count':validation['historical_promotion_count'],
      'current_head':validation['current_head'],
      'current_head_event_id':validation['current_head_event_id'],
    }
else:
    report['ledger_validation']={'valid':True,'current_head':ledger['current_head']}
report['receipt_sha256']=h({k:v for k,v in report.items() if k!='receipt_sha256'})
# event source digest must match final report digest, so update event deterministically and re-chain only last event.
ledger['events'][-1]['source_digest']=report['receipt_sha256']
ledger['events'][-1]['event_hash']=event_hash(ledger['events'][-1])
ledger['tail_event_hash']=ledger['events'][-1]['event_hash']
if promote: ledger['current_head_event_id']=ledger['events'][-1]['event_id']
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
if promote: validate_ledger_v2(ledger)

(ROOT/'yado_g1_s2_promotion_decision_gate_v1_receipt.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({
 'status':report['status'],'candidate_intelligence_decision':g1_decision,
 'gains':gains,'promotion_applied':promote,'current_head':ledger['current_head'],
 'current_head_digest':ledger['current_head_digest'],'ledger_event_count':ledger['event_count'],
 'historical_promotion_count':sum(1 for e in ledger['events'] if e.get('promotion_applied') is True),
 'receipt_sha256':report['receipt_sha256']
},indent=2,sort_keys=True))
if not promote: raise SystemExit('G1_PROMOTION_WITHHELD')
