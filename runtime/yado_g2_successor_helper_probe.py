from __future__ import annotations
from pathlib import Path
import inspect,json,sys
ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'successor_helper_probe.sqlite'))
try:
    meta_fn=k.meta_evolve_intelligence
    meta_g=meta_fn.__globals__
    tree_acc=meta_g.get('tree_acc')
    rc5_fn=k.synthesize_intelligence_algorithm_component
    rc5_g=rc5_fn.__globals__
    pred=rc5_g.get('predict_intel_component')
    out={
      'status':'PASS',
      'meta_module':meta_fn.__module__,
      'meta_globals_tree_acc':tree_acc is not None,
      'tree_acc_module':None if tree_acc is None else tree_acc.__module__,
      'tree_acc_source_file':None if tree_acc is None else inspect.getsourcefile(tree_acc),
      'tree_acc_has_tree_predict':False if tree_acc is None else ('tree_predict' in tree_acc.__globals__),
      'tree_predict_module':None if tree_acc is None or 'tree_predict' not in tree_acc.__globals__ else tree_acc.__globals__['tree_predict'].__module__,
      'tree_predict_source_file':None if tree_acc is None or 'tree_predict' not in tree_acc.__globals__ else inspect.getsourcefile(tree_acc.__globals__['tree_predict']),
      'rc5_module':rc5_fn.__module__,
      'predict_intel_component_present':pred is not None,
      'predict_intel_component_module':None if pred is None else pred.__module__,
      'predict_intel_component_source_file':None if pred is None else inspect.getsourcefile(pred),
      'meta_global_candidates':sorted(x for x in meta_g if 'tree' in x.lower() or 'predict' in x.lower()),
      'rc5_global_candidates':sorted(x for x in rc5_g if 'predict' in x.lower() or 'intel' in x.lower()),
    }
finally:
    k.close()
p=ROOT/'yado_g2_successor_helper_probe_receipt.json'
p.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(json.dumps(out,indent=2,sort_keys=True))
