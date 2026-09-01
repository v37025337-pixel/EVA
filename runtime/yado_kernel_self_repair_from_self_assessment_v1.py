from __future__ import annotations
from pathlib import Path
from dataclasses import asdict,is_dataclass
import copy,hashlib,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(PKG))

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_core_v2_2 import MechanismSelector,_mechanism_kind
from yado_core_v2_1 import BoundedRuleSandbox
import yado_architecture_neutral_meta_synthesizer_v2 as neutral

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json'
CORE=REPO/'canonical'/'yado-unified-core-v1.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
ASSESS=REPO/'receipts'/'yado-kernel-self-assess-synthesis-against-g2-v1-run-33507888433.json'
CAND_DIR=REPO/'candidates'/'kernel-self-generated'
CAND=CAND_DIR/'architecture-neutral-selector-v1.json'
ART=REPO/'architecture'/'yado-kernel-self-repair-from-self-assessment-v1.json'
OUT=ROOT/'yado_kernel_self_repair_from_self_assessment_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def serial(o):
    if is_dataclass(o):return asdict(o)
    if hasattr(o,'__dict__'):return copy.deepcopy(o.__dict__)
    return o

head=load(HEAD);ledger=load(LEDGER);assess=load(ASSESS)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['KERNEL_SELF_REPAIR_FROM_SELF_ASSESSMENT_V1']:
    raise RuntimeError('UNEXPECTED_FRONTIER')
if assess.get('status')!='PASS_KERNEL_SELF_ASSESS_SYNTHESIS_AGAINST_G2_V1':
    raise RuntimeError('SELF_ASSESSMENT_NOT_PASS')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):
    raise RuntimeError('HEAD_LEDGER_MISMATCH')

arch_sha=fsha(ARCH);head_sha=fsha(HEAD);core_sha=fsha(CORE)
fit=[{'input':dict(x),'expected':str(y)} for x,y in neutral.fit]
validation=[{'input':dict(x),'expected':str(y)} for x,y in neutral.validation]
revealed=[{'input':dict(x),'expected':str(y)} for x,y in neutral.revealed]
blind=[{'input':dict(x),'expected':str(y)} for x,y in neutral.blind]
baseline=float(assess.get('native_meta_fresh_blind',0.0))

def score_rule(program,rows):
    if not rows:return 0.0
    ok=0
    for z in rows:
        try:pred=BoundedRuleSandbox.execute(program,z['input'])
        except Exception:pred=None
        ok += pred==z['expected']
    return ok/len(rows)

construction_error=None
fit_candidates=[]
selected_kind=None
fit_program=None
validation_score=0.0
refit_program=None
blind_score=0.0
try:
    fit_candidates=MechanismSelector.synthesize_candidates(
        'ARCHITECTURE_NEUTRAL_SELECTOR','INTELLIGENCE',fit,min_support=2
    )
    scored=[]
    for p in fit_candidates:
        kind=_mechanism_kind(p)
        sc=score_rule(p,validation) if kind=='RULE_PROGRAM' else 0.0
        scored.append((sc,-MechanismSelector.complexity(p),kind,p))
    if not scored:raise ValueError('NO_NATIVE_CANDIDATES')
    scored.sort(key=lambda z:(z[0],z[1],z[2]),reverse=True)
    validation_score,_,selected_kind,fit_program=scored[0]

    # Refit through the SAME native selector on all revealed evidence; blind is never used to synthesize.
    refit_candidates=MechanismSelector.synthesize_candidates(
        'ARCHITECTURE_NEUTRAL_SELECTOR','INTELLIGENCE',revealed,min_support=2
    )
    same=[p for p in refit_candidates if _mechanism_kind(p)==selected_kind]
    if not same:raise ValueError('SELECTED_NATIVE_FAMILY_NOT_AVAILABLE_ON_REFIT')
    same.sort(key=lambda p:(MechanismSelector.complexity(p),str(getattr(p,'program_id',''))))
    refit_program=same[0]
    blind_score=score_rule(refit_program,blind) if selected_kind=='RULE_PROGRAM' else 0.0
except Exception as exc:
    construction_error=type(exc).__name__+':'+str(exc)[:800]

blind_families=sorted({z['expected'] for z in blind})
supported=(
    construction_error is None
    and validation_score>=0.90
    and blind_score>=0.90
    and blind_score>baseline
    and len(blind_families)>=4
)

candidate={
 'schema':'yado.kernel_self_generated.architecture_neutral_selector.v1',
 'state':'SHADOW_SUPPORTED' if supported else 'WITHHOLD',
 'origin':'YADO_NATIVE_MECHANISM_SELECTOR',
 'native_constructor':'yado_core_v2_2.MechanismSelector.synthesize_candidates',
 'selected_kind':selected_kind,
 'fit_candidate_count':len(fit_candidates),
 'validation':validation_score,
 'fresh_blind':blind_score,
 'baseline_native_meta_fresh_blind':baseline,
 'blind_family_count':len(blind_families),
 'blind_families':blind_families,
 'fit_program':serial(fit_program) if fit_program is not None else None,
 'refit_program':serial(refit_program) if refit_program is not None else None,
 'construction_error':construction_error,
 'canonical_active':False,'promotion_applied':False,
 'architecture_sha256':arch_sha,'parent_head_digest':head.get('canonical_head_digest'),
 'semantic_boundary':'SELF-GENERATED BOUNDED SELECTOR CANDIDATE FROM YADO NATIVE MECHANISM SYNTHESIS; NOT AN ARCHITECTURE REWRITE AND NOT PROOF OF CONSCIOUSNESS.'
}
candidate['candidate_digest']=h(candidate)
CAND_DIR.mkdir(parents=True,exist_ok=True);CAND.write_text(json.dumps(candidate,indent=2,sort_keys=True)+'\n')

next_cap='KERNEL_NEUTRAL_ARCHITECTURE_SELECTION_WITH_SELF_GENERATED_SELECTOR_V1' if supported else 'KERNEL_SELF_EXPAND_ARCHITECTURE_SELECTOR_CONSTRUCTOR_V1'
checks={
 'self_assessment_bound':bool(assess.get('kernel_failure_signals')),
 'native_constructor_used':True,
 'blind_not_used_for_synthesis':True,
 'validation_gate':validation_score>=0.90 if construction_error is None else False,
 'fresh_blind_gate':blind_score>=0.90 if construction_error is None else False,
 'causal_improvement_over_native_meta':blind_score>baseline if construction_error is None else False,
 'architecture_immutable':fsha(ARCH)==arch_sha,
 'head_immutable':fsha(HEAD)==head_sha,
 'core_immutable':fsha(CORE)==core_sha,
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
# Workflow PASS means the kernel attempt completed and was persisted. Candidate support is separately explicit.
attempt_completed=checks['self_assessment_bound'] and checks['architecture_immutable'] and checks['head_immutable'] and checks['core_immutable'] and checks['g3_not_started']

artifact={
 'schema':'yado.g2.kernel_self_repair_from_self_assessment.v1',
 'status':'PASS_KERNEL_SELF_REPAIR_ATTEMPT_V1' if attempt_completed else 'WITHHOLD_KERNEL_SELF_REPAIR_ATTEMPT_V1',
 'candidate_state':candidate['state'],'candidate_digest':candidate['candidate_digest'],
 'selected_kind':selected_kind,'validation':validation_score,'fresh_blind':blind_score,
 'baseline_native_meta_fresh_blind':baseline,'construction_error':construction_error,
 'checks':checks,
 'assistant_candidate_implementation_written':False,
 'native_constructor_used':candidate['native_constructor'],
 'canonical_mutation':False,'architecture_mutation':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,
 'claim_boundary':candidate['semantic_boundary']
}
artifact['artifact_digest']=h(artifact);ART.write_text(json.dumps(artifact,indent=2,sort_keys=True)+'\n')

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
 'schema':'yado.g2.kernel_self_repair_from_self_assessment.receipt.v1',
 'status':artifact['status'],'candidate_state':candidate['state'],'candidate_digest':candidate['candidate_digest'],
 'selected_kind':selected_kind,'fit_candidate_count':len(fit_candidates),
 'validation':validation_score,'fresh_blind':blind_score,'baseline_native_meta_fresh_blind':baseline,
 'construction_error':construction_error,'checks':checks,
 'canonical_mutation':False,'architecture_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,'semantic_boundary':artifact['claim_boundary']
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={
 'index':len(ledger['events']),
 'event_id':f"E{len(ledger['events'])+1:04d}_G2_KERNEL_SELF_REPAIR_FROM_SELF_ASSESSMENT_V1",
 'event_type':'KERNEL_NATIVE_MECHANISM_SELF_CONSTRUCTION',
 'status':'PASS_SHADOW' if supported else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'KERNEL_SELF_REPAIR_FROM_SELF_ASSESSMENT_V1',
 'effect':f"CANDIDATE={candidate['state']}; KIND={selected_kind}; VAL={validation_score:.6f}; BLIND={blind_score:.6f}; BASE={baseline:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-kernel-self-repair-from-self-assessment-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'promotion_applied':False,'generation_transition':False
}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({
 'status':receipt['status'],'candidate_state':candidate['state'],'selected_kind':selected_kind,
 'fit_candidate_count':len(fit_candidates),'validation':validation_score,'fresh_blind':blind_score,
 'baseline_native_meta_fresh_blind':baseline,'construction_error':construction_error,
 'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']
},indent=2,sort_keys=True))
if not attempt_completed:raise SystemExit('KERNEL_SELF_REPAIR_ATTEMPT_INFRASTRUCTURE_WITHHELD')
