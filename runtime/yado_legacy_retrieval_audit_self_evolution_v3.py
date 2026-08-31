from __future__ import annotations
from pathlib import Path
import hashlib,importlib.util,json,os,sys

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
PKG=ROOT/'yado_rc8_v36'
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(PKG))

from yado_evolution_ledger_v2 import validate_ledger_v2,event_hash
from yado_unified_core_v1 import UnifiedYADOCoreV1

AUDIT=REPO/'receipts'/'yado-unified-core-deep-self-audit-v1-run-33404158164.json'
HEAD=REPO/'canonical'/'yado-main-head-g2.json'
CORE=REPO/'canonical'/'yado-unified-core-v1.json'
LEDGER=REPO/'architecture'/'evolution-ledger.json'
SOURCE=REPO/'runtime'/'yado_unified_core_deep_self_audit_v1.py'
CAND_DIR=REPO/'candidates'/'g2-self-evolution';CAND_DIR.mkdir(parents=True,exist_ok=True)
CAND_SRC=CAND_DIR/'unified_core_legacy_retrieval_audit_v3.py'
CAND_META=CAND_DIR/'unified_core_legacy_retrieval_audit_v3.json'
OUT=ROOT/'yado_legacy_retrieval_audit_self_evolution_v3_receipt.json'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

audit=load(AUDIT);head=load(HEAD);ccore=load(CORE);ledger=load(LEDGER)
validate_ledger_v2(ledger)
if ledger.get('open_deficits')!=['LEGACY_EXPERIENCE_CONTENT_RETRIEVAL']:
    raise RuntimeError('UNEXPECTED_FRONTIER')
finding=next(x for x in audit['findings'] if x['code']=='LEGACY_EXPERIENCE_CONTENT_RETRIEVAL')
if finding.get('status')!='FAIL':raise RuntimeError('EXPECTED_STALE_LEGACY_RETRIEVAL_FAIL')
if ledger.get('current_head_digest')!=head.get('canonical_head_digest'):raise RuntimeError('HEAD_LEDGER_MISMATCH')

# Kernel sees its current real state.
core=UnifiedYADOCoreV1(REPO)
mem=next(x for x in ccore['planes'] if x.get('plane_id')=='MEMORY_AND_EXPERIENCE')
component_bound='ALG-G2-LEGACY-EXPERIENCE-RETRIEVER-V1' in mem.get('active_components',[])
runtime_bound=hasattr(core,'experience_read_exact') and hasattr(core,'experience_search_verified')
probe_ok=False;probe_evidence=None
try:
    entry=next(x for x in core.experience.get('branches',[]) if x.get('mode')=='EXPERIENCE_ONLY' and x.get('evidence'))
    path=entry['evidence'][0]
    item=core.experience_read_exact(entry['branch'],path)
    probe_ok=(item.get('branch')==entry['branch'] and item.get('registered_commit')==entry['head_sha']
              and item.get('path')==path and item.get('bytes',0)>0 and len(item.get('sha256',''))==64)
    probe_evidence={'branch':entry['branch'],'commit':entry['head_sha'],'path':path,
                    'sha256':item.get('sha256'),'bytes':item.get('bytes'),'transport':item.get('transport')}
except Exception as exc:
    probe_evidence={'error':type(exc).__name__+':'+str(exc)[:180]}

# Kernel selects a general detector against counterfactual states.
cases=[
 {'name':'CURRENT_CANONICAL','component':component_bound,'runtime':runtime_bound,'probe':probe_ok,'expected':True},
 {'name':'MANIFEST_ONLY','component':True,'runtime':False,'probe':False,'expected':False},
 {'name':'RUNTIME_ONLY','component':False,'runtime':True,'probe':True,'expected':False},
 {'name':'READ_FAIL','component':True,'runtime':True,'probe':False,'expected':False},
 {'name':'NONE','component':False,'runtime':False,'probe':False,'expected':False},
]
RULES={
 'SOURCE_LITERAL':lambda x: False,
 'MANIFEST_BOUND':lambda x:x['component'],
 'RUNTIME_BEHAVIOR':lambda x:x['runtime'] and x['probe'],
 'MANIFEST_PLUS_RUNTIME_BEHAVIOR':lambda x:x['component'] and x['runtime'] and x['probe'],
}
complexity={'SOURCE_LITERAL':0.02,'MANIFEST_BOUND':0.05,'RUNTIME_BEHAVIOR':0.10,'MANIFEST_PLUS_RUNTIME_BEHAVIOR':0.14}
risk={'SOURCE_LITERAL':0.35,'MANIFEST_BOUND':0.22,'RUNTIME_BEHAVIOR':0.12,'MANIFEST_PLUS_RUNTIME_BEHAVIOR':0.04}
results=[]
for name,fn in RULES.items():
    rows=[];ok=0
    for c in cases:
        got=bool(fn(c));correct=got==c['expected'];ok+=correct
        rows.append({'case':c['name'],'expected':c['expected'],'got':got,'correct':correct})
    acc=ok/len(cases);score=acc-.04*complexity[name]-.04*risk[name]
    results.append({'rule':name,'accuracy':acc,'score':score,'complexity':complexity[name],'risk':risk[name],'rows':rows})
results.sort(key=lambda x:(-x['score'],-x['accuracy'],x['rule']))
selected=results[0]['rule']
if selected!='MANIFEST_PLUS_RUNTIME_BEHAVIOR':
    # Allow kernel decision to stand but only this rule has an implementation template here.
    raise RuntimeError('SELECTED_RULE_NOT_IMPLEMENTABLE:'+selected)

src=SOURCE.read_text(encoding='utf-8')
start="# Is the experience actually retrievable, or only summarized metadata?"
end="# ---------- capability/evidence scope ----------"
if start not in src or end not in src:raise RuntimeError('AUDIT_SECTION_NOT_FOUND')
prefix,rest=src.split(start,1);old_section,suffix=rest.split(end,1)

new_section=r'''# Is the experience actually retrievable, or only summarized metadata?
runtime_text=RUNTIME.read_text(encoding='utf-8')
legacy_missing_refs=[]
for entry in legacy:
    for ep in entry.get('evidence',[]):
        if not (REPO/ep).exists():
            legacy_missing_refs.append({'branch':entry.get('branch'),'path':ep})

mem_plane=next((x for x in ccore.get('planes',[]) if x.get('plane_id')=='MEMORY_AND_EXPERIENCE'),{})
legacy_component_bound='ALG-G2-LEGACY-EXPERIENCE-RETRIEVER-V1' in mem_plane.get('active_components',[])
legacy_runtime_bound=hasattr(core,'experience_read_exact') and hasattr(core,'experience_search_verified')
legacy_probe_ok=False
legacy_probe_evidence=None
try:
    probe_entry=next(x for x in core.experience.get('branches',[]) if x.get('mode')=='EXPERIENCE_ONLY' and x.get('evidence'))
    probe_path=probe_entry['evidence'][0]
    probe_item=core.experience_read_exact(probe_entry['branch'],probe_path)
    legacy_probe_ok=(probe_item.get('branch')==probe_entry['branch']
        and probe_item.get('registered_commit')==probe_entry['head_sha']
        and probe_item.get('path')==probe_path
        and probe_item.get('bytes',0)>0
        and len(probe_item.get('sha256',''))==64)
    legacy_probe_evidence={'branch':probe_entry['branch'],'commit':probe_entry['head_sha'],'path':probe_path,
        'sha256':probe_item.get('sha256'),'bytes':probe_item.get('bytes'),'transport':probe_item.get('transport')}
except Exception as exc:
    legacy_probe_evidence={'error':type(exc).__name__+':'+str(exc)[:180]}

full_experience_retrieval=legacy_component_bound and legacy_runtime_bound and legacy_probe_ok
add('LEGACY_EXPERIENCE_CONTENT_RETRIEVAL','MEMORY_AND_EXPERIENCE','HIGH' if not full_experience_retrieval else 'INFO',
    'PASS' if full_experience_retrieval else 'FAIL',
    {'missing_current_branch_evidence_paths':legacy_missing_refs[:30],'missing_count':len(legacy_missing_refs),
     'legacy_component_bound':legacy_component_bound,'legacy_runtime_bound':legacy_runtime_bound,
     'legacy_probe_ok':legacy_probe_ok,'legacy_probe_evidence':legacy_probe_evidence,
     'experience_search_returns_metadata_only':not full_experience_retrieval},
    'Maintain bounded read-only exact legacy retrieval with canonical component binding and live provenance probe.',
    not full_experience_retrieval)

add('LEGACY_EXPERIENCE_SUMMARY_PROVENANCE','MEMORY_AND_EXPERIENCE','MEDIUM','PARTIAL',
    {'registry_lessons_are_precompiled_summaries':True,'raw_legacy_content_not_loaded_by_core':not full_experience_retrieval,
     'verified_raw_retrieval_available':full_experience_retrieval},
    'Distinguish host-curated lesson summaries from lessons independently re-derived by YADO from raw historical evidence.',
    False)

'''
candidate=prefix+start+"\n"+new_section+end+suffix
CAND_SRC.write_text(candidate,encoding='utf-8')

# Candidate deep audit must now recognize the canonical retriever and leave other findings intact.
tmp=ROOT/'_legacy_retrieval_audit_candidate.py';tmp.write_text(candidate,encoding='utf-8')
try:
    sp=importlib.util.spec_from_file_location('_legacy_retrieval_audit_candidate',tmp)
    mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod)
    # Execute module via subprocess would run audit; import itself executes top-level audit and writes receipt.
    # Read the resulting receipt from its fixed OUT path.
    cand_receipt=json.loads((ROOT/'yado_unified_core_deep_self_audit_v1_receipt.json').read_text())
finally:
    try:tmp.unlink()
    except FileNotFoundError:pass

cand_finding=next(x for x in cand_receipt['findings'] if x['code']=='LEGACY_EXPERIENCE_CONTENT_RETRIEVAL')
checks={
 'selected_rule_generalizes':results[0]['accuracy']==1.0,
 'current_component_bound':component_bound,
 'current_runtime_bound':runtime_bound,
 'current_probe_pass':probe_ok,
 'candidate_finding_pass':cand_finding.get('status')=='PASS',
 'candidate_no_longer_blocks_legacy':not cand_finding.get('blocking'),
 'head_ledger_immutable':ledger.get('current_head_digest')==head.get('canonical_head_digest'),
}
passed=all(checks.values())

meta={'schema':'yado.g2.legacy_retrieval_audit_candidate.v3','selected_rule':selected,
 'source_runtime_sha256':fsha(SOURCE),'candidate_source_sha256':fsha(CAND_SRC),
 'rule_results':results,'probe_evidence':probe_evidence,'checks':checks,
 'state':'AUTHORIZED_FOR_SHADOW_ADMISSION' if passed else 'WITHHOLD',
 'canonical_active':False,'promotion_applied':False,
 'semantic_boundary':'EVOLVES ONLY SELF-AUDIT RECOGNITION OF AN ALREADY CANONICAL READ-ONLY LEGACY RETRIEVER; RETRIEVAL CODE ITSELF IS UNCHANGED.'}
meta['candidate_digest']=h(meta);CAND_META.write_text(json.dumps(meta,indent=2,sort_keys=True)+'\n')

next_cap='LEGACY_RETRIEVAL_AUDIT_FRESH_ADMISSION_V3' if passed else 'LEGACY_RETRIEVAL_AUDIT_EVOLUTION_BLOCKED_V3'
run_id=str(os.getenv('GITHUB_RUN_ID') or 'LOCAL')
receipt={'schema':'yado.g2.legacy_retrieval_audit_self_evolution.v3',
 'status':'PASS_LEGACY_RETRIEVAL_AUDIT_SELF_EVOLUTION_V3' if passed else 'WITHHOLD_LEGACY_RETRIEVAL_AUDIT_SELF_EVOLUTION_V3',
 'source_audit_receipt':audit['receipt_sha256'],'selected_rule':selected,'rule_results':results,
 'probe_evidence':probe_evidence,'candidate_finding':cand_finding,'checks':checks,
 'candidate_digest':meta['candidate_digest'],'candidate_source_sha256':meta['candidate_source_sha256'],
 'canonical_mutation':False,'promotion_applied':False,'g3_genesis_performed':False,
 'next_required_capability':next_cap,
 'semantic_boundary':'KERNEL USED A POST-INTEGRATION SELF-AUDIT COUNTEREXAMPLE TO EVOLVE ONLY ITS RETRIEVER-DETECTION INVARIANT.'}
receipt['receipt_sha256']=h(receipt);OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

e={'index':len(ledger['events']),'event_id':f"E{len(ledger['events'])+1:04d}_G2_LEGACY_RETRIEVAL_AUDIT_SELF_EVOLUTION_V3",
 'event_type':'KERNEL_NATIVE_SELF_AUDIT_CODE_EVOLUTION','status':'PASS_SHADOW' if passed else 'WITHHOLD',
 'generation':ledger['current_head'],'deficit':'LEGACY_EXPERIENCE_CONTENT_RETRIEVAL',
 'effect':'SELF_AUDIT_EVOLVED_TO_VERIFY_CANONICAL_RETRIEVER_BY_BINDING_AND_LIVE_PROBE' if passed else 'LEGACY_RETRIEVAL_AUDIT_EVOLUTION_WITHHELD',
 'source_path':f'receipts/yado-legacy-retrieval-audit-self-evolution-v3-run-{run_id}.json',
 'source_digest':receipt['receipt_sha256'],'run_id':run_id,'parent_event_hash':ledger['tail_event_hash'],
 'canonical_mutation':False,'promotion_applied':False}
e['event_hash']=event_hash(e);ledger['events'].append(e);ledger['event_count']=len(ledger['events']);ledger['tail_event_hash']=e['event_hash']
ledger['open_deficits']=[next_cap];ledger['ledger_digest']=h({k:v for k,v in ledger.items() if k!='ledger_digest'})
validate_ledger_v2(ledger);LEDGER.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':receipt['status'],'selected_rule':selected,'checks':checks,'next_required_capability':next_cap,'receipt_sha256':receipt['receipt_sha256']},indent=2,sort_keys=True))
if not passed:raise SystemExit('LEGACY_RETRIEVAL_AUDIT_EVOLUTION_WITHHELD')
