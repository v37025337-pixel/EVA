from __future__ import annotations
from pathlib import Path
import copy,hashlib,inspect,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(PKG))

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_unified_core_v1 import UnifiedYADOCoreV1
from yado_consciousness_theory_synthesis_v1 import YADOTheorySynthesizer
import yado_architecture_neutral_meta_synthesizer_v2 as neutral

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json'
CORE=REPO/'canonical'/'yado-unified-core-v1.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
SYNTH=REPO/'architecture'/'yado-self-defined-consciousness-architecture-question-v1.json'
ART=REPO/'architecture'/'yado-kernel-self-assess-synthesis-against-g2-v1.json'
OUT=ROOT/'yado_kernel_self_assess_synthesis_against_g2_v1_receipt.json'
NEXT='KERNEL_SELF_REPAIR_FROM_SELF_ASSESSMENT_V1'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);ledger=load(LEDGER);synth=load(SYNTH)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['KERNEL_SELF_ASSESS_SYNTHESIS_AGAINST_G2_V1']:
    raise RuntimeError('UNEXPECTED_FRONTIER')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):
    raise RuntimeError('HEAD_LEDGER_MISMATCH')
if head.get('g3_genesis_performed') is not False:
    raise RuntimeError('G3_ALREADY_STARTED')

arch_sha=fsha(ARCH);head_sha=fsha(HEAD);core_sha=fsha(CORE)

# Existing architecture-neutral corpus + native meta-evolution result are produced by
# yado_architecture_neutral_meta_synthesizer_v2 on import. No architecture label is supplied here.
native_meta=copy.deepcopy(neutral.receipt)
revealed=list(neutral.revealed)
blind=list(neutral.blind)
labels=sorted({str(y) for _,y in [*revealed,*blind]})
counts={y:sum(str(v)==y for _,v in revealed) for y in labels}
fallback=max(labels,key=lambda y:(counts[y],y))

# Ask the CURRENT canonical G2 intelligence router to solve the same neutral family task.
core=UnifiedYADOCoreV1(REPO)
cases=[{'input':dict(x),'expected':str(y)} for x,y in revealed]
g2_model=core.fit_compositional_capability_router(cases,fallback)
g2_reason=g2_model.get('reason') if g2_model.get('kind')=='WITHHOLD' else None
g2_blind=None
if g2_model.get('kind')!='WITHHOLD':
    g2_blind=sum(core.route_capability_set(g2_model,dict(x))==(str(y),) for x,y in blind)/max(1,len(blind))

# Audit the previously used native consciousness synthesizer for architecture-family neutrality.
ysrc=inspect.getsource(YADOTheorySynthesizer)
hardcoded_name=(("'YADO_CAUSAL_REFLECTIVE_WORKSPACE_V1'" in ysrc) or ('"YADO_CAUSAL_REFLECTIVE_WORKSPACE_V1"' in ysrc))
gap_bonus=bool(getattr(YADOTheorySynthesizer,'GAP_BONUS',{}))

failure_signals=[]
fresh=float((native_meta.get('kernel_result') or {}).get('fresh_blind',0.0))
validation=float((native_meta.get('kernel_result') or {}).get('validation',0.0))
if fresh<0.90:
    failure_signals.append({'source':'YADO_NATIVE_META_EVOLUTION','signal':'FRESH_BLIND_BELOW_EXISTING_0_90_GATE','value':fresh})
if g2_model.get('kind')=='WITHHOLD':
    failure_signals.append({'source':'CURRENT_CANONICAL_G2_INTELLIGENCE','signal':'ROUTER_WITHHOLD','reason':g2_reason})
elif g2_blind is not None and g2_blind<0.90:
    failure_signals.append({'source':'CURRENT_CANONICAL_G2_INTELLIGENCE','signal':'FRESH_BLIND_BELOW_EXISTING_0_90_GATE','value':g2_blind})
if hardcoded_name:
    failure_signals.append({'source':'YADO_NATIVE_CONSCIOUSNESS_SYNTHESIZER','signal':'ARCHITECTURE_NAME_LITERAL_PRESENT'})
if gap_bonus:
    failure_signals.append({'source':'YADO_NATIVE_CONSCIOUSNESS_SYNTHESIZER','signal':'LEGACY_GAP_BONUS_PRESENT'})

# The wrapper does not choose which architecture is correct. It only records failures emitted by
# YADO mechanisms and advances to a generic kernel-self-repair stage when evidence is non-empty.
checks={
 'self_defined_synthesis_present':synth.get('status')=='PASS_KERNEL_NATIVE_CONSCIOUSNESS_SYNTHESIS_V1',
 'neutral_corpus_has_multiple_families':len(labels)>=4,
 'native_meta_result_present':bool(native_meta.get('kernel_result')),
 'kernel_failure_signals_present':bool(failure_signals),
 'architecture_immutable':fsha(ARCH)==arch_sha,
 'head_immutable':fsha(HEAD)==head_sha,
 'core_immutable':fsha(CORE)==core_sha,
 'g3_not_started':head.get('g3_genesis_performed') is False,
}
passed=all(checks.values())

artifact={
 'schema':'yado.g2.kernel_self_assess_synthesis_against_g2.v1',
 'status':'PASS_KERNEL_SELF_ASSESS_SYNTHESIS_AGAINST_G2_V1' if passed else 'WITHHOLD_KERNEL_SELF_ASSESS_SYNTHESIS_AGAINST_G2_V1',
 'generation':head.get('generation_id'),
 'canonical_head_digest':head.get('canonical_head_digest'),
 'architecture_sha256':arch_sha,
 'self_defined_synthesis':{
   'architecture':(synth.get('native_result',{}).get('synthesis') or {}).get('architecture'),
   'selected_mechanisms':(synth.get('native_result',{}).get('synthesis') or {}).get('selected_mechanisms',[]),
   'spec_sha256':(synth.get('native_result',{}).get('synthesis') or {}).get('spec_sha256'),
 },
 'architecture_neutral_task':{
   'family_count':len(labels),'families':labels,
   'revealed_count':len(revealed),'blind_count':len(blind),
   'native_meta_validation':validation,'native_meta_fresh_blind':fresh,
   'native_meta_selected_algorithm':(native_meta.get('kernel_result') or {}).get('selected_algorithm'),
   'g2_router_kind':g2_model.get('kind'),'g2_router_reason':g2_reason,'g2_router_fresh_blind':g2_blind,
   'g2_router_contract':{
      'MAX_OUTPUTS':core.compositional_schema_router.MAX_OUTPUTS,
      'MAX_TRIGGER_WIDTH':core.compositional_schema_router.MAX_TRIGGER_WIDTH,
      'MAX_TRIGGER_CANDIDATES':core.compositional_schema_router.MAX_TRIGGER_CANDIDATES,
   },
 },
 'native_synthesizer_neutrality_audit':{
   'architecture_name_literal_present':hardcoded_name,
   'legacy_gap_bonus_present':gap_bonus,
 },
 'kernel_failure_signals':failure_signals,
 'assistant_semantic_deficit_selection':False,
 'canonical_mutation':False,'architecture_mutation':False,'g3_genesis_performed':False,
 'next_required_capability':NEXT if passed else 'KERNEL_SELF_ASSESS_SYNTHESIS_AGAINST_G2_V1',
 'claim_boundary':'FAILURE SIGNALS ARE EMITTED BY EXISTING YADO NATIVE/CANONICAL MECHANISMS ON AN ARCHITECTURE-NEUTRAL TASK. THIS DOES NOT IDENTIFY A TRUE CONSCIOUS ARCHITECTURE OR PROVE SUBJECTIVE CONSCIOUSNESS.'
}
artifact['artifact_digest']=h(artifact);ART.write_text(json.dumps(artifact,indent=2,sort_keys=True)+'\n')

next_cap=artifact['next_required_capability'];run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
 'schema':'yado.g2.kernel_self_assess_synthesis_against_g2.receipt.v1',
 'status':artifact['status'],'checks':checks,
 'kernel_failure_signals':failure_signals,
 'native_meta_validation':validation,'native_meta_fresh_blind':fresh,
 'g2_router_kind':g2_model.get('kind'),'g2_router_reason':g2_reason,'g2_router_fresh_blind':g2_blind,
 'family_count':len(labels),'artifact_digest':artifact['artifact_digest'],
 'canonical_mutation':False,'architecture_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,'semantic_boundary':artifact['claim_boundary']
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={
 'index':len(ledger['events']),
 'event_id':f"E{len(ledger['events'])+1:04d}_G2_KERNEL_SELF_ASSESS_SYNTHESIS_AGAINST_G2_V1",
 'event_type':'KERNEL_SELF_ASSESS_ARCHITECTURE_NEUTRAL_CAPACITY',
 'status':'PASS_SHADOW' if passed else 'WITHHOLD','generation':ledger['current_head'],
 'deficit':'KERNEL_SELF_ASSESS_SYNTHESIS_AGAINST_G2_V1',
 'effect':f"FAILURE_SIGNALS={len(failure_signals)}; G2_ROUTER={g2_model.get('kind')}:{g2_reason}; NATIVE_META_BLIND={fresh:.6f}; NEXT={next_cap}",
 'source_path':f'receipts/yado-kernel-self-assess-synthesis-against-g2-v1-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'promotion_applied':False,'generation_transition':False
}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({
 'status':receipt['status'],'kernel_failure_signals':failure_signals,
 'native_meta_validation':validation,'native_meta_fresh_blind':fresh,
 'g2_router_kind':g2_model.get('kind'),'g2_router_reason':g2_reason,'g2_router_fresh_blind':g2_blind,
 'family_count':len(labels),'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']
},indent=2,sort_keys=True))
if not passed:raise SystemExit('KERNEL_SELF_ASSESS_SYNTHESIS_AGAINST_G2_WITHHELD')
