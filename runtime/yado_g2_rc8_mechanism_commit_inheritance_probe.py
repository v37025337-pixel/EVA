from pathlib import Path
import json,sys,inspect
ROOT=Path(__file__).resolve().parent;PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_rc8_inheritance_probe.sqlite'))
try:
    out={
      'schema':'yado.g2.rc8_mechanism_commit_inheritance_probe.v1',
      'mro':[c.__module__+'.'+c.__name__ for c in type(k).mro()],
      'attrs':{},
      'canonical_keys':sorted(k.canonical_state.keys()),
    }
    for name in ['development','executive','developmental','synthesize_best_mechanism','evaluate_mechanism','evaluate_program','execute_capability','active_program_by_capability','programs','deficits','organs','register_capability']:
        try:
            v=getattr(k,name)
            out['attrs'][name]={'exists':True,'type':type(v).__module__+'.'+type(v).__name__,'callable':callable(v)}
        except Exception as e:
            out['attrs'][name]={'exists':False,'error':type(e).__name__+':'+str(e)}
    # inspect object attributes for embedded executives/registries, without mutating.
    out['instance_dict_keys']=sorted(getattr(k,'__dict__',{}).keys())
finally:
    k.close()
(ROOT/'yado_g2_rc8_mechanism_commit_inheritance_probe_receipt.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(json.dumps(out,indent=2,sort_keys=True))
