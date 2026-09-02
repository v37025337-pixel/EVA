from __future__ import annotations
from pathlib import Path
import copy,hashlib,json,sys

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'runtime'))
from yado_evolution_ledger_v2 import validate_ledger_v2

HEAD=REPO/'canonical/yado-main-head-g2.json'
CORE=REPO/'canonical/yado-unified-core-v1.json'
PROV=REPO/'canonical/yado-algorithm-provenance-registry-v1.json'
LEDGER=REPO/'architecture/evolution-ledger.json'
AUDIT=REPO/'runtime/yado_unified_core_deep_self_audit_v1.py'
UNIFIED=REPO/'runtime/yado_unified_core_v1.py'

def canon(o):return json.dumps(o,sort_keys=True,separators=(',',':'),default=str)
def h(o):return hashlib.sha256(canon(o).encode()).hexdigest()
def fsha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def cdig(o,field):
    x=copy.deepcopy(o);x.pop(field,None);return h(x)

head,core,prov,ledger=map(load,[HEAD,CORE,PROV,LEDGER])
ledger_check=validate_ledger_v2(ledger)
front=(ledger.get('open_deficits') or [None])[0]
manifest_active=sorted({
    str(x) for plane in core.get('planes',[]) for x in plane.get('active_components',[])
    if isinstance(x,str) and '/' not in x and not x.endswith('.json')
})
explicit_active=sorted(head.get('active_capabilities',[])) if isinstance(head.get('active_capabilities'),list) else []

checks={
 'ledger_valid':bool(ledger_check.get('valid')),
 'head_content_digest':head.get('canonical_head_digest')==cdig(head,'canonical_head_digest'),
 'core_content_digest':core.get('core_digest')==cdig(core,'core_digest'),
 'provenance_content_digest':prov.get('registry_digest')==cdig(prov,'registry_digest'),
 'head_ledger_generation':head.get('generation_id')==ledger.get('current_head'),
 'head_ledger_digest':head.get('canonical_head_digest')==ledger.get('current_head_digest'),
 'frontier_single':len(ledger.get('open_deficits',[]))==1,
 'frontier_head_core':head.get('current_frontier')==core.get('current_frontier')==front,
 'provenance_frontier_current':prov.get('current_g2_binding',{}).get('frontier')==front,
 'provenance_digest_bound':(
    head.get('algorithm_provenance_registry',{}).get('registry_digest')==prov.get('registry_digest')
    and head.get('unified_core',{}).get('algorithm_provenance_registry_digest')==prov.get('registry_digest')
    and core.get('algorithm_provenance_registry_digest')==prov.get('registry_digest')
 ),
 'unified_runtime_hash_bound':(
    fsha(UNIFIED)==core.get('runtime_sha256')==head.get('unified_core',{}).get('runtime_sha256')
 ),
 'deep_audit_hash_bound':(
    fsha(AUDIT)==core.get('deep_self_audit',{}).get('source_sha256')==head.get('unified_core',{}).get('deep_self_audit_source_sha256')
 ),
 'active_capabilities_explicit':bool(explicit_active) and explicit_active==manifest_active,
 'g3_not_started':head.get('g3_genesis_performed') is False,
}

rim=core.get('runtime_integrity_manifest',{}) if isinstance(core.get('runtime_integrity_manifest',{}),dict) else {}
if rim:
    declared=rim.get('sources',{})
    actual={}
    for rel in core.get('active_runtime_sources',[]):
        p=REPO/rel
        if not p.exists():
            actual[rel]='MISSING'
        else:
            actual[rel]=fsha(p)
    checks['active_runtime_sources_hash_manifest']=(
        declared==actual and rim.get('manifest_digest')==h(actual)
        and head.get('unified_core',{}).get('runtime_integrity_manifest_digest')==rim.get('manifest_digest')
    )
else:
    checks['active_runtime_sources_hash_manifest']=False

out={
 'schema':'yado.g2.canonical_invariant_guard.v1',
 'status':'PASS_CANONICAL_INVARIANT_GUARD_V1' if all(checks.values()) else 'WITHHOLD_CANONICAL_INVARIANT_GUARD_V1',
 'frontier':front,'checks':checks,
 'unified_runtime_sha256_actual':fsha(UNIFIED),
 'deep_audit_sha256_actual':fsha(AUDIT),
 'active_capability_count':len(manifest_active),
}
print(json.dumps(out,indent=2,sort_keys=True))
if not all(checks.values()):
    raise SystemExit('CANONICAL_INVARIANT_GUARD_WITHHOLD')
