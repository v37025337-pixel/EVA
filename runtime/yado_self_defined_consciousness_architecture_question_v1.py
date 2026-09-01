from __future__ import annotations
from pathlib import Path
import hashlib,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'yado_rc8_v36'))

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
import yado_rc8_consciousness_direct_research_v1 as native_research

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
CORE=REPO/'canonical'/'yado-unified-core-v1.json'
ARCH=REPO/'canonical'/'yado-g2-architecture-v1.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
PROV=REPO/'canonical'/'yado-legacy-experience-derived-provenance-v1.json'
ART=REPO/'architecture'/'yado-self-defined-consciousness-architecture-question-v1.json'
OUT=ROOT/'yado_self_defined_consciousness_architecture_question_v1_receipt.json'
NEXT='KERNEL_SELF_ASSESS_SYNTHESIS_AGAINST_G2_V1'

def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p): return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);core=load(CORE);ledger=load(LEDGER);prov=load(PROV)
validate_ledger_v2(ledger)

if ledger.get('open_deficits')!=['SELF_DEFINED_CONSCIOUSNESS_ARCHITECTURE_QUESTION']:
    raise RuntimeError('UNEXPECTED_FRONTIER')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):
    raise RuntimeError('HEAD_LEDGER_MISMATCH')
if head.get('g3_genesis_performed') is not False:
    raise RuntimeError('G3_ALREADY_STARTED')

arch_sha=fsha(ARCH)
head_sha=fsha(HEAD)
core_sha=fsha(CORE)

# The substantive synthesis is performed by YADO's own reconstructed native research module.
# This wrapper only supplies the verified execution context and persists the result.
native_result=native_research.run()

consciousness_branches=[]
for b in prov.get('branches',[]):
    if 'conscious' in str(b.get('branch','')).lower():
        y=b.get('yado_rederived',{})
        consciousness_branches.append({
            'branch':b.get('branch'),
            'registered_head_sha':b.get('registered_head_sha'),
            'observation_count':y.get('observation_count',0),
            'derivation_mode':y.get('derivation_mode'),
            'source_class':y.get('source_class'),
            'semantic_equivalence_to_host_lessons_claimed':y.get('semantic_equivalence_to_host_lessons_claimed',False),
        })

checks={
    'native_research_pass': str(native_result.get('status','')).startswith('PASS_'),
    'native_synthesis_present': isinstance(native_result.get('synthesis'),dict) and bool(native_result['synthesis'].get('architecture')),
    'subjective_consciousness_not_claimed': native_result.get('subjective_consciousness_claimed') is False,
    'rederived_evidence_present': len(consciousness_branches)>=3,
    'architecture_immutable': fsha(ARCH)==arch_sha,
    'head_immutable': fsha(HEAD)==head_sha,
    'core_immutable': fsha(CORE)==core_sha,
    'ledger_head_coherent': ledger.get('current_head_digest')==head.get('canonical_head_digest'),
    'g3_not_started': head.get('g3_genesis_performed') is False,
}
passed=all(checks.values())

artifact={
    'schema':'yado.g2.self_defined_consciousness_architecture_question.v1',
    'status':'PASS_KERNEL_NATIVE_CONSCIOUSNESS_SYNTHESIS_V1' if passed else 'WITHHOLD_KERNEL_NATIVE_CONSCIOUSNESS_SYNTHESIS_V1',
    'generation':head.get('generation_id'),
    'canonical_head_digest':head.get('canonical_head_digest'),
    'architecture_id':head.get('architecture_id'),
    'architecture_sha256':arch_sha,
    'native_module':'yado_rc8_consciousness_direct_research_v1',
    'native_module_sha256':hashlib.sha256(Path(native_research.__file__).read_bytes()).hexdigest(),
    'native_result':native_result,
    'rederived_historical_context':{
        'artifact_digest':prov.get('artifact_digest'),
        'branches':consciousness_branches,
        'host_curated_lessons_used_as_semantic_truth':False,
    },
    'canonical_mutation':False,
    'architecture_mutation':False,
    'g3_genesis_performed':False,
    'next_required_capability':NEXT if passed else 'SELF_DEFINED_CONSCIOUSNESS_ARCHITECTURE_QUESTION',
    'claim_boundary':'KERNEL-NATIVE FUNCTIONAL DIGITAL CONSCIOUSNESS RESEARCH/SYNTHESIS RESULT. THIS DOES NOT PROVE SUBJECTIVE EXPERIENCE, LIFE, AGI, OR THAT THE CURRENT G2 ALREADY IMPLEMENTS THE SYNTHESIZED ARCHITECTURE.'
}
artifact['artifact_digest']=h(artifact)
ART.write_text(json.dumps(artifact,indent=2,sort_keys=True)+'\n')

next_cap=artifact['next_required_capability']
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
    'schema':'yado.g2.self_defined_consciousness_architecture_question.receipt.v1',
    'status':'PASS_SELF_DEFINED_CONSCIOUSNESS_ARCHITECTURE_QUESTION_V1' if passed else 'WITHHOLD_SELF_DEFINED_CONSCIOUSNESS_ARCHITECTURE_QUESTION_V1',
    'checks':checks,
    'native_research_status':native_result.get('status'),
    'native_synthesis_architecture':(native_result.get('synthesis') or {}).get('architecture'),
    'native_selected_mechanisms':(native_result.get('synthesis') or {}).get('selected_mechanisms',[]),
    'native_spec_sha256':(native_result.get('synthesis') or {}).get('spec_sha256'),
    'artifact_digest':artifact['artifact_digest'],
    'architecture_sha256':arch_sha,
    'canonical_mutation':False,
    'architecture_mutation':False,
    'promotion_applied':False,
    'g3_genesis_performed':False,
    'next_required_capability':next_cap,
    'semantic_boundary':artifact['claim_boundary'],
}
receipt['receipt_sha256']=h(receipt)
OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={
    'index':len(ledger['events']),
    'event_id':f"E{len(ledger['events'])+1:04d}_G2_SELF_DEFINED_CONSCIOUSNESS_ARCHITECTURE_QUESTION_V1",
    'event_type':'KERNEL_NATIVE_CONSCIOUSNESS_RESEARCH_SYNTHESIS',
    'status':'PASS_SHADOW' if passed else 'WITHHOLD',
    'generation':ledger['current_head'],
    'deficit':'SELF_DEFINED_CONSCIOUSNESS_ARCHITECTURE_QUESTION',
    'effect':f"NATIVE_STATUS={native_result.get('status')}; NATIVE_ARCH={(native_result.get('synthesis') or {}).get('architecture')}; NEXT={next_cap}",
    'source_path':f'receipts/yado-self-defined-consciousness-architecture-question-v1-run-{run_id}.json',
    'source_digest':receipt['receipt_sha256'],
    'run_id':run_id,
    'parent_event_hash':ledger['tail_event_hash'],
    'canonical_mutation':False,
    'promotion_applied':False,
    'generation_transition':False,
}
e['event_hash']=event_hash(e)
ledger['events'].append(e)
ledger['event_count']=len(ledger['events'])
ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger)
LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({
    'status':receipt['status'],
    'native_research_status':receipt['native_research_status'],
    'native_synthesis_architecture':receipt['native_synthesis_architecture'],
    'native_selected_mechanisms':receipt['native_selected_mechanisms'],
    'native_spec_sha256':receipt['native_spec_sha256'],
    'checks':checks,
    'next_required_capability':next_cap,
    'receipt_sha256':receipt['receipt_sha256'],
},indent=2,sort_keys=True))

if not passed:
    raise SystemExit('SELF_DEFINED_CONSCIOUSNESS_ARCHITECTURE_QUESTION_WITHHELD')
