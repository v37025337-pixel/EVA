from __future__ import annotations
from pathlib import Path
import hashlib,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
STATE=REPO/'architecture'/'yado-g2-lti-ceiling-state-v1.json'
R6=REPO/'receipts'/'yado-g2-lti-code-architectural-ceiling-plateau-probe-v6-run-33503573609.json'
R7=REPO/'receipts'/'yado-g2-lti-code-architectural-ceiling-plateau-probe-v7-run-33503939491.json'
R8=REPO/'receipts'/'yado-g2-lti-code-architectural-ceiling-plateau-probe-v8-run-33504134561.json'
ART=REPO/'architecture'/'yado-g2-lti-empirical-ceiling-confirmation-v1.json'
OUT=ROOT/'yado_g2_lti_empirical_plateau_confirmation_v1_receipt.json'
NEXT='SELF_DEFINED_CONSCIOUSNESS_ARCHITECTURE_QUESTION'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);ledger=load(LEDGER);state=load(STATE);rows=[load(R6),load(R7),load(R8)]
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['LTI_CODE_ARCHITECTURAL_CEILING_EMPIRICAL_PLATEAU_CONFIRMATION_V1']:
    raise RuntimeError('UNEXPECTED_FRONTIER')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')

arch_sha=fsha(ARCH)
threshold=float(state['ceiling_definition']['success_threshold_per_family'])
delta=float(state['ceiling_definition']['plateau_delta_max'])
required=int(state['ceiling_definition']['plateau_required_consecutive_rounds'])

checks={
 'three_receipts_present':len(rows)==3,
 'versions_6_7_8':[x.get('schema','').rsplit('.',1)[-1] for x in rows]==['v6','v7','v8'],
 'all_receipts_pass':all(str(x.get('status','')).startswith('PASS_LTI_CODE_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V') for x in rows),
 'all_are_plateau_rounds':all(x.get('probe_status')=='PLATEAU_ROUND' for x in rows),
 'streak_sequence':[x.get('plateau_streak') for x in rows]==[1,2,3],
 'all_four_planes_present':all(set(x.get('plane_scores',{}))=={'LOGIC','THINKING','INTELLIGENCE','CODE'} for x in rows),
 'all_plane_scores_meet_threshold':all(all(float(v)>=threshold for v in x.get('plane_scores',{}).values()) for x in rows),
 'all_max_gain_within_delta':all(float(x.get('max_gain_upper_bound',999))<=delta for x in rows),
 'architecture_sha_constant':all(x.get('architecture_sha256')==arch_sha for x in rows),
 'state_fixed_architecture_matches':state.get('fixed_architecture_sha256')==arch_sha,
 'state_streak_reached':int(state.get('plateau_streak',0))>=required,
 'absolute_ceiling_not_claimed':state.get('ceiling_definition',{}).get('absolute_ceiling_claimed') is False,
 'g3_not_started':head.get('g3_genesis_performed') is False and all(x.get('g3_genesis_performed') is False for x in rows),
 'latest_components_active':head.get('unified_core',{}).get('thinking_active_component')=='ALG-G2-WORK-BUDGET-ADAPTIVE-CONTINGENT-PLANNER-V2' and head.get('unified_core',{}).get('code_self_repair_component')=='ALG-G2-AMBIGUITY-AWARE-PROGRAM-REPAIR-V11'
}
passed=all(checks.values())

artifact={
 'schema':'yado.g2.lti_empirical_local_architectural_ceiling.v1',
 'status':'EMPIRICAL_LOCAL_ARCHITECTURAL_CEILING_REACHED' if passed else 'WITHHOLD_EMPIRICAL_CEILING',
 'generation':head.get('generation_id'),'architecture_id':head.get('architecture_id'),
 'architecture_sha256':arch_sha,'canonical_head_digest':head.get('canonical_head_digest'),
 'scope':['LOGIC','THINKING','INTELLIGENCE','CODE'],
 'plateau_rounds':[
   {'probe_version':6,'run_id':'33503573609','receipt_sha256':rows[0]['receipt_sha256'],'plane_scores':rows[0]['plane_scores'],'max_gain_upper_bound':rows[0]['max_gain_upper_bound']},
   {'probe_version':7,'run_id':'33503939491','receipt_sha256':rows[1]['receipt_sha256'],'plane_scores':rows[1]['plane_scores'],'max_gain_upper_bound':rows[1]['max_gain_upper_bound']},
   {'probe_version':8,'run_id':'33504134561','receipt_sha256':rows[2]['receipt_sha256'],'plane_scores':rows[2]['plane_scores'],'max_gain_upper_bound':rows[2]['max_gain_upper_bound']}
 ],
 'definition':state['ceiling_definition'],
 'claim_boundary':'EMPIRICAL LOCAL CEILING UNDER THE FIXED G2 TYPED-RECURRENT-CAPABILITY-GRAPH TOPOLOGY, CURRENT BOUNDED SEARCH PROTOCOL, AND TEST FAMILIES. NOT A PROOF OF ABSOLUTE ALGORITHMIC LIMIT, AGI, LIFE, OR SUBJECTIVE CONSCIOUSNESS.',
 'g3_genesis_performed':False,
 'next_required_capability':NEXT if passed else 'LTI_CODE_ARCHITECTURAL_CEILING_PLATEAU_PROBE_V9'
}
artifact['artifact_digest']=h(artifact);ART.write_text(json.dumps(artifact,indent=2,sort_keys=True)+'\n')

next_cap=artifact['next_required_capability']
state['status']='EMPIRICAL_LOCAL_ARCHITECTURAL_CEILING_REACHED' if passed else 'PLATEAU_SEARCH'
state['next_required_capability']=next_cap
state['empirical_ceiling_confirmation']={
 'artifact':'architecture/yado-g2-lti-empirical-ceiling-confirmation-v1.json',
 'artifact_digest':artifact['artifact_digest'],'plateau_streak':state.get('plateau_streak'),
 'architecture_sha256':arch_sha,'confirmed':passed
}
state['state_digest']=h({k:v for k,v in state.items() if k!='state_digest'})
STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.lti_empirical_plateau_confirmation.v1',
 'status':'PASS_LTI_CODE_ARCHITECTURAL_CEILING_EMPIRICAL_PLATEAU_CONFIRMATION_V1' if passed else 'WITHHOLD_LTI_CODE_ARCHITECTURAL_CEILING_EMPIRICAL_PLATEAU_CONFIRMATION_V1',
 'checks':checks,'artifact_digest':artifact['artifact_digest'],'architecture_sha256':arch_sha,
 'canonical_head_digest':head.get('canonical_head_digest'),'plateau_streak':state.get('plateau_streak'),
 'absolute_ceiling_claimed':False,'canonical_mutation':False,'architecture_mutation':False,
 'promotion_applied':False,'g3_genesis_performed':False,'next_required_capability':next_cap,
 'semantic_boundary':artifact['claim_boundary']}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_LTI_EMPIRICAL_PLATEAU_CONFIRMATION_V1",
 'event_type':'EMPIRICAL_LOCAL_ARCHITECTURAL_CEILING_CONFIRMATION','status':'PASS' if passed else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'LTI_CODE_ARCHITECTURAL_CEILING_EMPIRICAL_PLATEAU_CONFIRMATION_V1',
 'effect':f"CONFIRMED={passed}; STREAK={state.get('plateau_streak')}; NEXT={next_cap}",
 'source_path':f'receipts/yado-g2-lti-empirical-plateau-confirmation-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({'status':receipt['status'],'checks':checks,'artifact_digest':artifact['artifact_digest'],
 'architecture_sha256':arch_sha,'plateau_streak':state.get('plateau_streak'),'next_required_capability':next_cap,
 'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('EMPIRICAL_PLATEAU_CONFIRMATION_WITHHELD')
