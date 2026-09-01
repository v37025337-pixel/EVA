from __future__ import annotations
from pathlib import Path
import hashlib,inspect,json,os,re,sys
ROOT=Path(__file__).resolve().parent; REPO=ROOT.parent; PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]
from yado_evolution_ledger_v2 import validate_ledger_v2
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive

def load(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

ledger=load(REPO/'architecture/evolution-ledger.json')
head=load(REPO/'canonical/yado-main-head-g2.json')
core=load(REPO/'canonical/yado-unified-core-v1.json')
package_meta=load(ROOT/'package_meta.json')
ledger_check=validate_ledger_v2(ledger)

cls=UnifiedYADOKernelV30RC8ExternalCognitive
mro=[]
for c in cls.__mro__:
    if c is object: continue
    try: src=inspect.getsourcefile(c)
    except Exception: src=None
    mro.append({'class':c.__name__,'module':c.__module__,'source_file':src})

keys=[
 'synthesize_intelligence_with_extended_meta_grammar',
 'synthesize_intelligence_algorithm_component',
 'meta_evolve_intelligence',
 'meta_grammar_snapshot',
 'meta_grammar_extension_registry',
 'propose_evolution_operation',
 'durable_commit_evolution_bundle'
]
owners={}
for name in keys:
    owner=None
    for c in cls.__mro__:
        if name in getattr(c,'__dict__',{}):
            owner=c;break
    fn=getattr(cls,name,None)
    owners[name]={
      'owner_class':None if owner is None else owner.__name__,
      'owner_module':None if owner is None else owner.__module__,
      'signature':None if fn is None else str(inspect.signature(fn)),
      'source_file':None if fn is None else inspect.getsourcefile(fn),
    }

k=cls(db_path=str(ROOT/'yado_algorithmic_transition_audit.sqlite'))
try:
    meta_snapshot=k.meta_evolution_snapshot()
    grammar_snapshot=k.meta_grammar_snapshot()
    grammar_registry=k.meta_grammar_extension_registry()
    bank=k.organ_evolution_algorithm_bank()
    constructors=k.algorithm_constructor_registry()
finally:
    k.close()

patterns=('META_GRAMMAR','ALGORITHM_GENESIS','RC5','RC6','RC7','RC8','G2_PROMOTION','EVOLUTION','CONSTRUCTOR')
events=[]
for e in ledger.get('events',[]):
    blob=' '.join(str(e.get(x,'')) for x in ('event_id','event_type','deficit','effect','source_path'))
    if any(p in blob.upper() for p in patterns):
        events.append({k:e.get(k) for k in ('index','event_id','event_type','status','generation','deficit','effect','source_path','source_digest','canonical_mutation','promotion_applied','generation_transition')})

pkg_files=sorted(p.name for p in PKG.glob('*.py'))
meta_module=next((p for p in PKG.glob('yado_meta_grammar_runtime_native_v1.py')),None)
meta_module_sha=None if meta_module is None else sha(meta_module)

checks={
 'package_reconstruction_metadata_present':all(package_meta.get(k) for k in ('package_sha256','manifest_sha256','state_sha256','parts')),
 'ledger_valid':bool(ledger_check.get('valid')),
 'head_is_g2':head.get('generation_id')=='G2_CANDIDATE_TRCG_V1',
 'g3_not_started':head.get('g3_genesis_performed') is False,
 'extended_meta_method_present':'synthesize_intelligence_with_extended_meta_grammar' in owners and owners['synthesize_intelligence_with_extended_meta_grammar']['owner_class'] is not None,
 'meta_grammar_module_present':meta_module is not None,
 'meta_grammar_enabled':bool(grammar_snapshot.get('enabled')),
 'meta_evolution_enabled':bool(meta_snapshot.get('enabled')),
 'intelligence_bank_nonempty':len(bank.get('INTELLIGENCE',[]))>0,
 'constructor_registry_nonempty':len(constructors)>0,
 'head_ledger_digest_match':ledger.get('current_head_digest')==head.get('canonical_head_digest'),
 'frontier_match':head.get('current_frontier')==(ledger.get('open_deficits') or [None])[0],
}
out={
 'schema':'yado.g2.algorithmic_transition_lineage_audit.v1',
 'status':'PASS_READ_ONLY_ALGORITHMIC_TRANSITION_AUDIT' if all(checks.values()) else 'WITHHOLD_ALGORITHMIC_TRANSITION_AUDIT',
 'package_meta':package_meta,
 'reconstructed_python_file_count':len(pkg_files),
 'meta_grammar_module_sha256':meta_module_sha,
 'mro':mro,
 'method_owners':owners,
 'meta_evolution_snapshot':meta_snapshot,
 'meta_grammar_snapshot':grammar_snapshot,
 'meta_grammar_extension_registry':grammar_registry,
 'algorithm_bank_counts':{k:len(v) for k,v in bank.items()},
 'algorithm_bank':bank,
 'constructor_registry':constructors,
 'relevant_ledger_events':events,
 'current_generation':head.get('generation_id'),
 'current_frontier':head.get('current_frontier'),
 'checks':checks,
 'canonical_mutation':False,'architecture_mutation':False,'generation_transition':False,
 'semantic_boundary':'THIS AUDIT VERIFIES EXECUTABLE PROVENANCE/INHERITANCE/REGISTRY/LEDGER CONTINUITY. IT DOES NOT PROVE THAT HISTORICAL MARKETING LABELS RC5/RC6/RC7 MAP ONE-TO-ONE TO A FORMAL GENERATION PROMOTION UNLESS A RECEIPT/EVENT EXISTS.'
}
p=ROOT/'yado_g2_algorithmic_transition_lineage_audit_v1_receipt.json'
p.write_text(json.dumps(out,indent=2,sort_keys=True,default=str)+'\n',encoding='utf-8')
print(json.dumps({
 'status':out['status'],'checks':checks,'mro':mro,'method_owners':owners,
 'meta_evolution_snapshot':meta_snapshot,'meta_grammar_snapshot':grammar_snapshot,
 'algorithm_bank_counts':out['algorithm_bank_counts'],
 'relevant_event_ids':[e['event_id'] for e in events]
},indent=2,sort_keys=True,default=str))
