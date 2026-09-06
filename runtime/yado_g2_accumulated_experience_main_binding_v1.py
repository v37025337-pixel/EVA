from __future__ import annotations
from pathlib import Path
import copy, hashlib, json, subprocess, sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]

from yado_unified_core_v1 import UnifiedYADOCoreV1

REG=REPO/'canonical/yado-unified-experience-registry-v1.json'
CENSUS=REPO/'candidates/kernel-self-generated/g2-global-historical-experience-census-v2.json'
HIST=REPO/'experience/yado-global-historical-experience-corpus-v2.json'
TRANSFER=REPO/'candidates/kernel-self-generated/g2-global-experience-terminal-logic-historical-transfer-v1.json'
TRANSFER_EXP=REPO/'experience/yado-global-experience-terminal-logic-historical-transfer-v1.json'
OUT=REPO/'candidates/kernel-self-generated/g2-accumulated-experience-main-binding-v1.json'

def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def canon(o): return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def digest(o): return hashlib.sha256(canon(o).encode()).hexdigest()
def cdig(o,field):
    x=copy.deepcopy(o);x.pop(field,None);return digest(x)
def write(p,o):
    Path(p).parent.mkdir(parents=True,exist_ok=True)
    Path(p).write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')

registry=load(REG);census=load(CENSUS);hist=load(HIST);transfer=load(TRANSFER);transfer_exp=load(TRANSFER_EXP)
if census.get('status')!='PASS_G2_GLOBAL_HISTORICAL_EXPERIENCE_CENSUS_V2':
    raise RuntimeError('HISTORICAL_CENSUS_PASS_REQUIRED')
if transfer.get('status')!='PASS_SHADOW_G2_GLOBAL_EXPERIENCE_TERMINAL_LOGIC_HISTORICAL_TRANSFER_V1':
    raise RuntimeError('HISTORICAL_TRANSFER_PASS_REQUIRED')
if int(census['counts']['new_historical_outcome_count'])!=int(transfer['historical_counts']['total']):
    raise RuntimeError('HISTORICAL_OUTCOME_COUNT_MISMATCH')
if float(transfer.get('terminal_historical_fresh') or 0)<.75:
    raise RuntimeError('TERMINAL_FRESH_BELOW_ADMISSION')
if float(transfer.get('cognitive_historical_fresh') or 0)<.75:
    raise RuntimeError('COGNITIVE_FRESH_BELOW_ADMISSION')
if float(transfer.get('old_corpus_regression') or 0)<.93:
    raise RuntimeError('OLD_CORPUS_REGRESSION_BELOW_ADMISSION')
if not all((transfer.get('checks') or {}).values()):
    raise RuntimeError('TRANSFER_CHECK_NOT_ALL_PASS')

branches=registry.get('branches') or []
main=next((x for x in branches if x.get('branch')=='main'),None)
if main is None: raise RuntimeError('MAIN_EXPERIENCE_ENTRY_MISSING')
if main.get('mode')!='EXPERIENCE_ONLY': raise RuntimeError('MAIN_ENTRY_NOT_EXPERIENCE_ONLY')

canonical_main_sha=subprocess.run(
    ['git','rev-parse','origin/main'],cwd=REPO,capture_output=True,text=True,check=True
).stdout.strip()

main.update({
    'head_sha':canonical_main_sha,
    'head_sha_semantics':'CANONICAL_MAIN_BASE_USED_FOR_ACCUMULATED_EXPERIENCE_REFRESH',
    'branch_tip_at_closure':canonical_main_sha,
    'role':'CURRENT_CANONICAL_ACCUMULATED_G2_EXPERIENCE',
    'history_only':True,
    'runtime_active':False,
    'legacy_auto_execution':False,
    'reuse_requires_fresh_admission':True,
    'evidence':[
        'experience/yado-global-historical-experience-corpus-v2.json',
        'candidates/kernel-self-generated/g2-global-historical-experience-census-v2.json',
        'experience/yado-global-experience-terminal-logic-historical-transfer-v1.json',
        'candidates/kernel-self-generated/g2-global-experience-terminal-logic-historical-transfer-v1.json',
    ],
    'tags':[
        'experience','history','logic','thinking','intelligence','cognitive',
        'meta','repair','representation','withhold','regression','transfer'
    ],
    'lessons':[
        'DO_NOT_TREAT_WORKFLOW_POINTERS_AS_ACTIVE_KERNEL_STATE',
        'CURRENT_HISTORY_CONTAINS_PASS_AND_WITHHOLD_CAUSAL_EVIDENCE',
        'HISTORICAL_BLIND_TERMINAL_TRANSFER_MUST_PASS_BEFORE_META_DECISION_REUSE',
        'HISTORICAL_BLIND_COGNITIVE_TRANSFER_MUST_PASS_BEFORE_META_DECISION_REUSE',
        'OLD_CORPUS_REGRESSION_MUST_REMAIN_ABOVE_ADMISSION_FLOOR',
        'WITHHOLD_CLASS_RECALL_REMAINS_VISIBLE_AND_MUST_NOT_BE_ERASED',
    ],
    'lesson_provenance':{
        'source_class':'YADO_REDERIVED_FROM_CURRENT_REACHABLE_GIT_HISTORY',
        'allowed_use':'PRIORITIZATION_GUARDS_TEST_SELECTION_ONLY',
        'semantic_validation_by_rederivation':True,
    },
    'rederived_evidence':{
        'source_class':'YADO_REDERIVED_FROM_CURRENT_REACHABLE_GIT_HISTORY',
        'artifact':'experience/yado-global-historical-experience-corpus-v2.json',
        'artifact_digest':hist.get('corpus_digest'),
        'observation_count':int(census['counts']['new_historical_outcome_count']),
        'terminal_observation_count':int(census['counts']['new_terminal_count']),
        'pass_count':int(census['new_outcome_by_class']['PASS']),
        'withhold_count':int(census['new_outcome_by_class']['WITHHOLD']),
        'transfer_receipt_sha256':transfer.get('receipt_sha256'),
        'transfer_experience_digest':transfer_exp.get('experience_digest'),
        'terminal_historical_fresh':transfer.get('terminal_historical_fresh'),
        'cognitive_historical_fresh':transfer.get('cognitive_historical_fresh'),
        'old_corpus_regression':transfer.get('old_corpus_regression'),
        'semantic_equivalence_to_host_lessons_claimed':False,
    },
})
registry['registry_digest']=cdig(registry,'registry_digest')
write(REG,registry)

core=UnifiedYADOCoreV1(REPO)
query=['logic','thinking','intelligence','repair','representation','withhold','history']
hits=core.experience_search(query,limit=8)
main_hit=next((x for x in hits if x.get('branch')=='main'),None)
checks={
    'census_pass':True,
    'transfer_pass':True,
    'outcome_count_ge_100':int(census['counts']['new_historical_outcome_count'])>=100,
    'pass_and_withhold_present':int(census['new_outcome_by_class']['PASS'])>0 and int(census['new_outcome_by_class']['WITHHOLD'])>0,
    'terminal_fresh_ge_0_75':float(transfer['terminal_historical_fresh'])>=.75,
    'cognitive_fresh_ge_0_75':float(transfer['cognitive_historical_fresh'])>=.75,
    'old_regression_ge_0_93':float(transfer['old_corpus_regression'])>=.93,
    'main_registry_entry_found':main_hit is not None,
    'main_registry_entry_selected_by_experience_search':main_hit is not None and int(main_hit.get('score') or 0)>0,
    'legacy_branch_count_preserved':sum(1 for x in registry.get('branches',[]) if x.get('mode')=='EXPERIENCE_ONLY')==13,
    'active_lineage_count_preserved':sum(1 for x in registry.get('branches',[]) if x.get('mode')=='ACTIVE_LINEAGE')==1,
}
if not all(checks.values()):
    raise RuntimeError('ACCUMULATED_EXPERIENCE_BINDING_WITHHOLD:'+json.dumps(checks,sort_keys=True))

report={
    'schema':'yado.g2.accumulated_experience_main_binding.v1',
    'status':'PASS_G2_ACCUMULATED_EXPERIENCE_MAIN_BINDING_V1',
    'canonical_main_base_sha':canonical_main_sha,
    'registry_digest':registry['registry_digest'],
    'historical_corpus_digest':hist.get('corpus_digest'),
    'historical_outcome_count':census['counts']['new_historical_outcome_count'],
    'historical_pass_count':census['new_outcome_by_class']['PASS'],
    'historical_withhold_count':census['new_outcome_by_class']['WITHHOLD'],
    'terminal_historical_fresh':transfer['terminal_historical_fresh'],
    'cognitive_historical_fresh':transfer['cognitive_historical_fresh'],
    'old_corpus_regression':transfer['old_corpus_regression'],
    'main_experience_search_hit':main_hit,
    'checks':checks,
    'canonical_mechanism_mutation':False,
    'cognitive_v4_replaced':False,
    'generation_transition':False,
    'g3_genesis':False,
    'semantic_boundary':'CANONICAL MEMORY/EXPERIENCE BINDING ONLY. THE CURRENT V4 COGNITIVE RUNTIME IS NOT REPLACED. THE NEW HISTORICAL V7 EVIDENCE IS AVAILABLE TO CORE EXPERIENCE SEARCH FOR PRIORITIZATION, GUARDS, TEST SELECTION AND FUTURE FRESH-ADMITTED EVOLUTION.'
}
report['receipt_sha256']=digest(report)
write(OUT,report)
print(json.dumps(report,indent=2,sort_keys=True))
