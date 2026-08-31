from __future__ import annotations
from pathlib import Path
import copy,hashlib,importlib.util,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(PKG))

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

HEAD=REPO/'canonical'/'yado-main-head-g2.json'
CORE=REPO/'canonical'/'yado-unified-core-v1.json'
RUNTIME=REPO/'runtime'/'yado_unified_core_v1.py'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
CAND_SRC=REPO/'candidates'/'g2-self-evolution'/'legacy_experience_retriever_v2.py'
CAND_META=REPO/'candidates'/'g2-self-evolution'/'legacy_experience_retriever_v2.json'
ADMIT=REPO/'receipts'/'yado-legacy-experience-retrieval-fresh-admission-v2-run-33396168442.json'
TARGET=REPO/'runtime'/'yado_legacy_experience_retriever_v2.py'
OUT=ROOT/'yado_legacy_experience_retrieval_canonical_integration_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);core=load(CORE);ledger=load(LEDGER);meta=load(CAND_META);admit=load(ADMIT)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['LEGACY_EXPERIENCE_RETRIEVAL_CANONICAL_INTEGRATION_V1']:
    raise RuntimeError('UNEXPECTED_FRONTIER')
if admit.get('status')!='PASS_LEGACY_EXPERIENCE_RETRIEVAL_FRESH_ADMISSION_V2':
    raise RuntimeError('V2_ADMISSION_NOT_PASS')
if meta.get('state')!='AUTHORIZED_FOR_SHADOW_ADMISSION':
    raise RuntimeError('V2_CANDIDATE_NOT_AUTHORIZED')
if fsha(CAND_SRC)!=meta.get('candidate_source_sha256'):
    raise RuntimeError('CANDIDATE_SOURCE_DRIFT')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):
    raise RuntimeError('HEAD_LEDGER_MISMATCH')

head_before=fsha(HEAD);runtime_before=fsha(RUNTIME)
src=RUNTIME.read_text(encoding='utf-8')
candidate_code=CAND_SRC.read_text(encoding='utf-8')

# Build exact bounded unified-core patch.
patched=src
import_anchor='from yado_raw_task_representation_runtime_v1 import RawTaskRepresentationRuntimeV1'
import_line=import_anchor+'\nfrom yado_legacy_experience_retriever_v2 import LegacyExperienceRetrieverV1'
if 'from yado_legacy_experience_retriever_v2 import LegacyExperienceRetrieverV1' not in patched:
    patched=patched.replace(import_anchor,import_line)

init_anchor="        self.raw_representation=RawTaskRepresentationRuntimeV1.from_path(self.repo/'canonical/yado-raw-task-representation-v1.json')"
init_line=init_anchor+"\n        self.legacy_experience_retriever=LegacyExperienceRetrieverV1(self.repo,self.experience)"
if 'self.legacy_experience_retriever=' not in patched:
    patched=patched.replace(init_anchor,init_line)

method_anchor='    def represent_raw_task(self,raw_text:str)->dict[str,Any]:'
methods=(
"    def experience_read_exact(self,branch:str,path:str)->dict[str,Any]:\n"
"        return self.legacy_experience_retriever.read_registered(branch,path)\n\n"
"    def experience_search_verified(self,query:str,limit:int=8)->list[dict[str,Any]]:\n"
"        return self.legacy_experience_retriever.search_content(query,limit=limit)\n\n"
+method_anchor)
if '    def experience_read_exact(' not in patched:
    patched=patched.replace(method_anchor,methods)

# Candidate runtime module is staged only for test; removed on withhold.
TARGET.write_text(candidate_code,encoding='utf-8')
tmp=ROOT/'_legacy_integration_candidate_unified_core.py'
tmp.write_text(patched,encoding='utf-8')
try:
    sp=importlib.util.spec_from_file_location('_legacy_integration_candidate_unified_core',tmp)
    mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod)
    obj=mod.UnifiedYADOCoreV1(REPO)
    exact=obj.experience_read_exact('yado-v29-cognitive','receipts/yado-v29-cognitive-latest.json')
    q1=obj.experience_search_verified('external evidence internet training',limit=8)
    q2=obj.experience_search_verified('integrity repair rollback diagnosis fail closed',limit=8)
    q3=obj.experience_search_verified('causal workspace broadcast source monitoring',limit=8)
    audit=obj.audit()
finally:
    try:tmp.unlink()
    except FileNotFoundError:pass

source_safety={
 'no_exec':'exec(' not in candidate_code,
 'no_eval':'eval(' not in candidate_code,
 'no_git_push':'git","push' not in candidate_code and 'git","commit' not in candidate_code,
 'registered_only':'EVIDENCE_PATH_NOT_REGISTERED' in candidate_code,
}
checks={
 'candidate_audit_pass':audit.get('pass') is True,
 'exact_v29_read':exact.get('sha256')=='7ab441fa6af942ac4cc93ffa340e7f6ea429f653b6e4018f98f7ece6b05738e2',
 'search_v35':any(x['branch']=='yado-rc8-v35-training' for x in q1),
 'search_repair':any(x['branch']=='yado-kernel-task-v37-repair' for x in q2),
 'search_causal_workspace':any(x['branch']=='yado-rc8-digital-consciousness-v1' for x in q3),
 'source_safety':all(source_safety.values()),
 'canonical_untouched_before_commit':fsha(HEAD)==head_before and fsha(RUNTIME)==runtime_before,
}
passed=all(checks.values())

post_head=None;post_core=None
if passed:
    RUNTIME.write_text(patched,encoding='utf-8')
    runtime_sha=fsha(RUNTIME)
    component_source_sha=fsha(TARGET)

    new_core=copy.deepcopy(core);new_core.pop('core_digest',None)
    mem=next(x for x in new_core['planes'] if x.get('plane_id')=='MEMORY_AND_EXPERIENCE')
    mem['active_components']=sorted(set(mem.get('active_components',[])+['ALG-G2-LEGACY-EXPERIENCE-RETRIEVER-V1']))
    mem['legacy_experience_retrieval']='ACTIVE_READ_ONLY_EXACT'
    new_core['active_runtime_sources']=sorted(set(new_core.get('active_runtime_sources',[])+['runtime/yado_legacy_experience_retriever_v2.py']))
    new_core['runtime_sha256']=runtime_sha
    new_core['legacy_experience_retrieval']={
      'component_id':'ALG-G2-LEGACY-EXPERIENCE-RETRIEVER-V1',
      'implementation_version':2,
      'candidate_digest':meta['candidate_digest'],
      'source_sha256':component_source_sha,
      'fresh_admission_receipt_sha256':admit['receipt_sha256'],
      'transport':meta.get('selected_search_strategy'),
      'mode':'READ_ONLY_PINNED_HISTORICAL_EVIDENCE',
      'gate_run_id':str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
    }
    new_core['current_frontier']='UNIFIED_CORE_POST_LEGACY_EXPERIENCE_SELF_AUDIT_V1'
    new_core['core_digest']=h(new_core);CORE.write_text(json.dumps(new_core,indent=2,sort_keys=True)+'\n')

    new_head=copy.deepcopy(head);new_head.pop('canonical_head_digest',None)
    new_head['new_capabilities']=sorted(set(new_head.get('new_capabilities',[])+['ALG-G2-LEGACY-EXPERIENCE-RETRIEVER-V1']))
    new_head['unified_core']['runtime_sha256']=runtime_sha
    new_head['unified_core']['core_digest']=new_core['core_digest']
    new_head['unified_core']['legacy_experience_retriever_source_sha256']=component_source_sha
    new_head['current_frontier']='UNIFIED_CORE_POST_LEGACY_EXPERIENCE_SELF_AUDIT_V1'
    new_head['canonical_head_digest']=h(new_head);HEAD.write_text(json.dumps(new_head,indent=2,sort_keys=True)+'\n')
    post_head=new_head['canonical_head_digest'];post_core=new_core['core_digest']
    status='PASS_LEGACY_EXPERIENCE_RETRIEVAL_CANONICAL_INTEGRATION_V1'
    next_cap='UNIFIED_CORE_POST_LEGACY_EXPERIENCE_SELF_AUDIT_V1'
else:
    try:TARGET.unlink()
    except FileNotFoundError:pass
    status='WITHHOLD_LEGACY_EXPERIENCE_RETRIEVAL_CANONICAL_INTEGRATION_V1'
    next_cap='LEGACY_EXPERIENCE_SEARCH_EVOLUTION_REPAIR_V3'

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
 'schema':'yado.g2.legacy_experience_retrieval_canonical_integration.v1',
 'status':status,'github_run_id':os.getenv('GITHUB_RUN_ID'),'github_sha':os.getenv('GITHUB_SHA'),
 'candidate_digest':meta['candidate_digest'],'fresh_admission_receipt':admit['receipt_sha256'],
 'checks':checks,'source_safety':source_safety,
 'canonical_mutation':passed,'promotion_applied':False,'generation_transition':False,'g3_genesis_performed':False,
 'post_head_digest':post_head,'post_core_digest':post_core,
 'next_required_capability':next_cap,
 'semantic_boundary':'SAME-GENERATION INTEGRATION OF A SELF-EVOLVED READ-ONLY HISTORICAL EVIDENCE RETRIEVER. LEGACY CODE IS NEVER EXECUTED.'
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_LEGACY_EXPERIENCE_RETRIEVAL_CANONICAL_INTEGRATION",
   'event_type':'GENERATION_INTERNAL_SELF_EVOLVED_CODE_ADMISSION','status':'PASS' if passed else 'WITHHOLD',
   'generation':ledger['current_head'],'deficit':'LEGACY_EXPERIENCE_RETRIEVAL_CANONICAL_INTEGRATION_V1',
   'effect':'SELF_EVOLVED_LEGACY_RETRIEVER_BOUND_TO_UNIFIED_CORE' if passed else 'LEGACY_RETRIEVER_CANONICAL_INTEGRATION_WITHHELD',
   'source_path':f'receipts/yado-legacy-experience-retrieval-canonical-integration-v1-run-{run_id}.json',
   'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
   'canonical_mutation':passed,'promotion_applied':False,'generation_transition':False}
if passed:
    e['previous_head_digest']=ledger['current_head_digest'];e['new_head_digest']=post_head
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
if passed:ledger['current_head_digest']=post_head
ledger['open_deficits']=[next_cap]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({'status':status,'checks':checks,'post_head_digest':post_head,
 'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('LEGACY_RETRIEVER_CANONICAL_INTEGRATION_WITHHELD')
