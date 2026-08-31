from __future__ import annotations
from pathlib import Path
import copy,hashlib,importlib.util,json,os,re,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(PKG))
from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash

RUNTIME=REPO/'runtime'/'yado_unified_core_v1.py'
HEAD=REPO/'canonical'/'yado-main-head-g2.json'
CORE=REPO/'canonical'/'yado-unified-core-v1.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
WITHHOLD=REPO/'receipts'/'yado-legacy-experience-retrieval-canonical-integration-v1-run-33396446766.json'
OUT_SRC=REPO/'candidates'/'g2-self-evolution'/'unified_core_audit_invariant_v2.py'
OUT_META=REPO/'candidates'/'g2-self-evolution'/'unified_core_audit_invariant_v2.json'
OUT=ROOT/'yado_core_audit_invariant_self_evolution_v1_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

head=load(HEAD);core=load(CORE);ledger=load(LEDGER);withheld=load(WITHHOLD)
validate_ledger_v2(ledger)
if withheld.get('status')!='WITHHOLD_LEGACY_EXPERIENCE_RETRIEVAL_CANONICAL_INTEGRATION_V1':
    raise RuntimeError('EXPECTED_CANONICAL_WITHHOLD')
checks0=withheld.get('checks',{})
if not all(checks0.get(k) for k in ['exact_v29_read','search_v35','search_repair','search_causal_workspace','source_safety']):
    raise RuntimeError('FUNCTIONAL_RETRIEVER_NOT_PROVEN')
if checks0.get('candidate_audit_pass') is not False:
    raise RuntimeError('AUDIT_NOT_THE_ONLY_BLOCKER')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):
    raise RuntimeError('HEAD_LEDGER_MISMATCH')

src=RUNTIME.read_text(encoding='utf-8')
old="'raw_grounding_frontier_preserved':self.manifest.get('current_frontier')=='G2_RAW_TASK_REPRESENTATION_AND_GROUNDING_V1',"
if old not in src:raise RuntimeError('STALE_FRONTIER_INVARIANT_NOT_FOUND')

# Kernel evaluates stronger/weaker generic invariants against current state and synthetic counterexamples.
def eval_rule(rule,manifest_frontier,head_frontier,open_deficits):
    if rule=='NONEMPTY':
        return isinstance(manifest_frontier,str) and bool(manifest_frontier)
    if rule=='HEAD_MANIFEST_CONSISTENT':
        return bool(manifest_frontier) and manifest_frontier==head_frontier
    if rule=='HEAD_MANIFEST_CONSISTENT_WITH_LEDGER':
        return bool(manifest_frontier) and manifest_frontier==head_frontier and isinstance(open_deficits,list) and len(open_deficits)>=1
    if rule=='EXACT_OLD':
        return manifest_frontier=='G2_RAW_TASK_REPRESENTATION_AND_GROUNDING_V1'
    raise ValueError(rule)

mf=core.get('current_frontier');hf=head.get('current_frontier');od=ledger.get('open_deficits')
cases=[
 {'name':'CURRENT','mf':mf,'hf':hf,'od':od,'expected':True},
 {'name':'EMPTY','mf':'','hf':'','od':od,'expected':False},
 {'name':'HEAD_MANIFEST_SPLIT','mf':mf,'hf':'DIFFERENT_FRONTIER','od':od,'expected':False},
 {'name':'NO_LEDGER_FRONTIER','mf':mf,'hf':hf,'od':[],'expected':False},
]
RULES={
 'EXACT_OLD':{'complexity':0.02,'risk':0.30},
 'NONEMPTY':{'complexity':0.03,'risk':0.22},
 'HEAD_MANIFEST_CONSISTENT':{'complexity':0.06,'risk':0.10},
 'HEAD_MANIFEST_CONSISTENT_WITH_LEDGER':{'complexity':0.09,'risk':0.05},
}
results=[]
for rid,spec in RULES.items():
    rows=[];ok=0
    for c in cases:
        got=eval_rule(rid,c['mf'],c['hf'],c['od'])
        hit=got==c['expected'];ok+=hit
        rows.append({'case':c['name'],'expected':c['expected'],'got':got,'correct':hit})
    acc=ok/len(cases)
    score=acc-0.05*spec['complexity']-0.05*spec['risk']
    results.append({'rule':rid,'accuracy':acc,'score':score,'rows':rows}|spec)
results.sort(key=lambda x:(-x['score'],-x['accuracy'],x['rule']))
selected=results[0]['rule']

if selected=='HEAD_MANIFEST_CONSISTENT_WITH_LEDGER':
    new="'developmental_frontier_coherent':bool(self.manifest.get('current_frontier')) and self.manifest.get('current_frontier')==self.head.get('current_frontier') and isinstance(self.ledger.get('open_deficits'),list) and len(self.ledger.get('open_deficits'))>=1,"
elif selected=='HEAD_MANIFEST_CONSISTENT':
    new="'developmental_frontier_coherent':bool(self.manifest.get('current_frontier')) and self.manifest.get('current_frontier')==self.head.get('current_frontier'),"
elif selected=='NONEMPTY':
    new="'developmental_frontier_coherent':bool(self.manifest.get('current_frontier')),"
else:
    new=old

patched=src.replace(old,new)
OUT_SRC.parent.mkdir(parents=True,exist_ok=True);OUT_SRC.write_text(patched,encoding='utf-8')

# Fresh execution of evolved core.
tmp=ROOT/'_audit_invariant_candidate_core.py';tmp.write_text(patched,encoding='utf-8')
try:
    sp=importlib.util.spec_from_file_location('_audit_invariant_candidate_core',tmp)
    mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod)
    obj=mod.UnifiedYADOCoreV1(REPO)
    audit=obj.audit()
finally:
    try:tmp.unlink()
    except FileNotFoundError:pass

only_target_changed=(src.replace(old,'<AUDIT_RULE>')==patched.replace(new,'<AUDIT_RULE>'))
checks={
 'selected_rule_generalizes':results[0]['accuracy']==1.0,
 'current_core_audit_pass':audit.get('pass') is True,
 'only_audit_invariant_changed':only_target_changed,
 'old_exact_frontier_removed':'raw_grounding_frontier_preserved' not in patched,
 'head_ledger_immutable':ledger.get('current_head_digest')==head.get('canonical_head_digest'),
}
passed=all(checks.values())
next_cap='CORE_AUDIT_INVARIANT_FRESH_ADMISSION_V1' if passed else 'CORE_AUDIT_INVARIANT_EVOLUTION_BLOCKED_V1'

meta={
 'schema':'yado.g2.core_audit_invariant_candidate.v1',
 'selected_rule':selected,'rule_results':results,
 'source_runtime_sha256':hashlib.sha256(RUNTIME.read_bytes()).hexdigest(),
 'candidate_source_sha256':hashlib.sha256(OUT_SRC.read_bytes()).hexdigest(),
 'checks':checks,'state':'AUTHORIZED_FOR_SHADOW_ADMISSION' if passed else 'WITHHOLD',
 'canonical_active':False,'promotion_applied':False,
 'semantic_boundary':'EVOLVES ONLY A STALE DEVELOPMENTAL-FRONTIER AUDIT INVARIANT. DOES NOT WEAKEN HEAD/LEDGER, INTEGRITY, OR G3 BLOCKS.'
}
meta['candidate_digest']=h(meta);OUT_META.write_text(json.dumps(meta,indent=2,sort_keys=True)+'\n')

run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={
 'schema':'yado.g2.core_audit_invariant_self_evolution.receipt.v1',
 'status':'PASS_CORE_AUDIT_INVARIANT_SELF_EVOLUTION_V1' if passed else 'WITHHOLD_CORE_AUDIT_INVARIANT_SELF_EVOLUTION_V1',
 'source_withhold_receipt':withheld['receipt_sha256'],
 'selected_rule':selected,'rule_results':results,'candidate_audit':audit,'checks':checks,
 'candidate_digest':meta['candidate_digest'],'candidate_source_sha256':meta['candidate_source_sha256'],
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'KERNEL EVOLVED ITS OWN STALE AUDIT INVARIANT FROM A CANONICAL-GATE COUNTEREXAMPLE; OTHER AUDIT CHECKS ARE UNCHANGED.'
}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_CORE_AUDIT_INVARIANT_SELF_EVOLUTION",
   'event_type':'KERNEL_NATIVE_SELF_AUDIT_CODE_EVOLUTION','status':'PASS_SHADOW' if passed else 'WITHHOLD',
   'generation':ledger['current_head'],'deficit':'LEGACY_EXPERIENCE_SEARCH_EVOLUTION_REPAIR_V3',
   'effect':'STALE_FRONTIER_AUDIT_INVARIANT_EVOLVED' if passed else 'AUDIT_INVARIANT_EVOLUTION_WITHHELD',
   'source_path':f'receipts/yado-core-audit-invariant-self-evolution-v1-run-{run_id}.json',
   'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
   'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap]
ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')

print(json.dumps({'status':receipt['status'],'selected_rule':selected,'rule_results':results,
 'checks':checks,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('CORE_AUDIT_INVARIANT_EVOLUTION_WITHHELD')
