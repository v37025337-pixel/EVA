from pathlib import Path
import copy,hashlib,json,os,sys
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent
sys.path[:0]=[str(ROOT),str(ROOT/'yado_rc8_v36')]
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_unified_context_kernel_v1 import UnifiedContextKernel

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
CAND=REPO/'candidates/kernel-self-generated/scale-conditional-pair-knn-successor-v1.json'
PROBE1=REPO/'receipts/yado-g2-native-commit-api-probe-run-33596218944.json'
PROBE2=REPO/'receipts/yado-g2-native-selector-commit-surface-probe-run-33596280804.json'
ART=REPO/'architecture/yado-kernel-native-selector-commit-substrate-deficit-v1.json'
OUT=ROOT/'yado_kernel_native_selector_commit_substrate_deficit_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):p.write_text(json.dumps(o,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
def cdig(o,field):
 x=copy.deepcopy(o);x.pop(field,None);return h(x)

head,core,ledger,cand,p1,p2=map(load,[HEAD,CORE,LEDGER,CAND,PROBE1,PROBE2])
validate_ledger_v2(ledger)
front='KERNEL_SCALE_CONDITIONAL_SUCCESSOR_CANONICAL_ADMISSION_V1'
if ledger.get('open_deficits')!=[front]:raise RuntimeError('UNEXPECTED_FRONTIER:'+json.dumps(ledger.get('open_deficits')))
if cand.get('state')!='SHADOW_SUPPORTED':raise RuntimeError('CANDIDATE_NOT_SHADOW_SUPPORTED')

methods=[(x.get('module'),x.get('name'),x.get('source','')) for x in p2.get('hits',[])]
has_skill_commit=any(('skill' in n.lower() or 'selector' in n.lower()) and any(k in n.lower() for k in ('commit','install','activate','promot')) for _,n,_ in methods)
durables=[x for x in p1.get('hits',[]) if x.get('name')=='durable_commit_evolution_bundle']
organ_only=bool(durables) and all("allowed={'LOGIC','THINKING','INTELLIGENCE'}" in x.get('source','') or "super().durable_commit_evolution_bundle" in x.get('source','') for x in durables)
if has_skill_commit:raise RuntimeError('NATIVE_SELECTOR_COMMIT_PATH_ACTUALLY_EXISTS')
if not organ_only:raise RuntimeError('DURABLE_COMMIT_SCOPE_NOT_PROVEN_ORGAN_ONLY')

next_cap='KERNEL_NATIVE_SELECTOR_COMMIT_SUBSTRATE_GENESIS_V1'
artifact={
 'schema':'yado.g2.native_selector_commit_substrate_deficit.v1',
 'status':'WITHHOLD_NATIVE_SELECTOR_COMMIT_SUBSTRATE_MISSING',
 'candidate_id':'SCALE_CONDITIONAL_PAIR_KNN_SUCCESSOR_V1',
 'candidate_state':cand['state'],
 'evidence':{
   'skill_precommit_gate_exists':True,
   'native_selector_or_skill_commit_exists':False,
   'durable_commit_evolution_bundle_scope':'LOGIC_THINKING_INTELLIGENCE_ONLY',
   'direct_host_canonical_overwrite_performed':False,
 },
 'next_required_capability':next_cap,
 'canonical_mechanism_mutation':False,
 'architecture_mutation':False,
 'g3_genesis_performed':False,
}
artifact['artifact_digest']=h(artifact);write(ART,artifact)

prev=head['canonical_head_digest']
core['current_frontier']=next_cap;core['frontier_source']='architecture/evolution-ledger.json:open_deficits';core['core_digest']=cdig(core,'core_digest');write(CORE,core)
head['current_frontier']=next_cap;head['frontier_source']='architecture/evolution-ledger.json:open_deficits';head['unified_core']['core_digest']=core['core_digest'];head['canonical_head_digest']=cdig(head,'canonical_head_digest');write(HEAD,head)

checks={'candidate_shadow_supported':cand['state']=='SHADOW_SUPPORTED','native_selector_commit_absent':not has_skill_commit,
 'organ_bundle_commit_only':organ_only,'no_canonical_mechanism_mutation':True,'g3_not_started':head.get('g3_genesis_performed') is False}
receipt={**artifact,'schema':'yado.g2.native_selector_commit_substrate_deficit.receipt.v1',
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest'],'checks':checks}
receipt['receipt_sha256']=h(receipt);write(OUT,receipt)

ledger['current_head_digest']=head['canonical_head_digest'];ledger['open_deficits']=[next_cap];run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_NATIVE_SELECTOR_COMMIT_SUBSTRATE_DEFICIT_V1",
 'event_type':'G2_NATIVE_COMMIT_SUBSTRATE_DEFICIT','status':'WITHHOLD','generation':ledger['current_head'],'deficit':front,
 'effect':f"CANDIDATE=SHADOW_SUPPORTED; NATIVE_SKILL_COMMIT=ABSENT; DURABLE_BUNDLE_SCOPE=LOGIC_THINKING_INTELLIGENCE_ONLY; NEXT={next_cap}",
 'source_path':f'receipts/yado-kernel-native-selector-commit-substrate-deficit-v1-run-{run_id}.json','source_digest':receipt['receipt_sha256'],'run_id':run_id,
 'parent_event_hash':ledger['tail_event_hash'],'canonical_mutation':True,'canonical_mechanism_mutation':False,'promotion_applied':False,'generation_transition':False,
 'previous_head_digest':prev,'new_head_digest':head['canonical_head_digest']}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash'];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'});validate_ledger_v2(ledger);write(LEDGER,ledger)
ctx=UnifiedContextKernel().snapshot()
if ctx['current_frontier']!=next_cap:raise RuntimeError('POST_WRITE_CONTEXT_INCONSISTENT')
print(json.dumps({'status':artifact['status'],'next':next_cap,'checks':checks},indent=2))
