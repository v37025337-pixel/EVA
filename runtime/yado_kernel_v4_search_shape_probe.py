from __future__ import annotations
from pathlib import Path
import json,sys,time
ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]
import yado_architecture_neutral_meta_synthesizer_v2 as neutral
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
method=UnifiedYADOKernelV30RC8ExternalCognitive.synthesize_intelligence_with_extended_meta_grammar
mg=method.__globals__['mg']
d=neutral.build_dataset()
fit=d['fit']
candidates=0
parts={}
start=time.perf_counter()
for p in mg._linear_candidates(fit):
    candidates+=1
    mask=tuple(bool(mg._predicate(p,r[0])) for r in fit)
    if all(mask) or not any(mask):
        continue
    parts.setdefault(mask,0);parts[mask]+=1
elapsed=time.perf_counter()-start
out={'schema':'yado.g2.v4.search_shape_probe.v1','candidate_count':candidates,'nontrivial_unique_partitions':len(parts),
     'duplicate_partition_candidates':sum(parts.values())-len(parts),'max_candidates_per_partition':max(parts.values()) if parts else 0,
     'enumeration_seconds':elapsed,'fit_count':len(fit),'canonical_mutation':False}
p=ROOT/'yado_kernel_v4_search_shape_probe_receipt.json';p.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(json.dumps(out,indent=2,sort_keys=True))
