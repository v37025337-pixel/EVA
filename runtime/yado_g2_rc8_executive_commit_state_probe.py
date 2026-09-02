from pathlib import Path
import json,sys,inspect
ROOT=Path(__file__).resolve().parent;PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive
k=UnifiedYADOKernelV30RC8ExternalCognitive(db_path=str(ROOT/'yado_rc8_exec_state_probe.sqlite'))
try:
    ex=k.executive
    methods=[]
    for name in dir(ex):
        if any(term in name.lower() for term in ('deficit','mechanism','program','capability','commit','evaluate','synth','register','persist','restore')):
            try:
                v=getattr(ex,name)
                if callable(v):
                    try:sig=str(inspect.signature(v))
                    except Exception:sig='?'
                    methods.append({'name':name,'signature':sig})
            except Exception:pass
    out={
      'schema':'yado.g2.rc8_executive_commit_state_probe.v1',
      'executive_type':type(ex).__module__+'.'+type(ex).__name__,
      'methods':methods,
      'deficits':{k2:(v.__dict__ if hasattr(v,'__dict__') else str(v)) for k2,v in getattr(ex,'deficits',{}).items()},
      'programs':{k2:{'type':type(v).__name__,'status':getattr(v,'status',None),'target_capability':getattr(v,'target_capability',None),'target_organ':getattr(v,'target_organ',None)} for k2,v in getattr(ex,'programs',{}).items()},
      'active_program_by_capability':dict(getattr(ex,'active_program_by_capability',{})),
      'organs':{k2:(v.__dict__ if hasattr(v,'__dict__') else str(v)) for k2,v in getattr(ex,'organs',{}).items()},
      'db_path':str(k.db_path),
      'state_path':str(k.state_path),
    }
finally:k.close()
(ROOT/'yado_g2_rc8_executive_commit_state_probe_receipt.json').write_text(json.dumps(out,indent=2,sort_keys=True,default=str)+'\n')
print(json.dumps({'executive_type':out['executive_type'],'methods':methods,'deficit_count':len(out['deficits']),'program_count':len(out['programs']),'active_programs':out['active_program_by_capability'],'organ_names':sorted(out['organs'])},indent=2))
