from __future__ import annotations
from pathlib import Path
import ast,inspect,json,os,sys
ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36'
sys.path[:0]=[str(ROOT),str(PKG)]
from yado_core_v3_0_rc8_external_cognitive import UnifiedYADOKernelV30RC8ExternalCognitive

method=UnifiedYADOKernelV30RC8ExternalCognitive.synthesize_intelligence_with_extended_meta_grammar
mg=method.__globals__.get('mg')
if mg is None:
    raise RuntimeError('MG_MODULE_NOT_BOUND')
fn=mg.synth_intel_predicate
src=inspect.getsource(fn)
tree=ast.parse(src)
called=sorted({n.func.id for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)})
helpers={}
for name in called:
    obj=getattr(mg,name,None)
    if inspect.isfunction(obj):
        try: helpers[name]=inspect.getsource(obj)
        except Exception as e: helpers[name]='SOURCE_ERR:'+repr(e)
methods=[]
for name,obj in inspect.getmembers(UnifiedYADOKernelV30RC8ExternalCognitive,predicate=inspect.isfunction):
    if any(k in name.lower() for k in ('repair','patch','program','synth','grammar','evol')):
        try: body=inspect.getsource(obj)
        except Exception as e: body='SOURCE_ERR:'+repr(e)
        methods.append({'name':name,'signature':str(inspect.signature(obj)),'source':body})
out={
 'schema':'yado.g2.v4.meta_grammar_source_probe.v1',
 'status':'PASS_READ_ONLY_SOURCE_PROBE',
 'mg_module':getattr(mg,'__name__',None),
 'synth_intel_predicate_source':src,
 'called_helpers':called,
 'helper_sources':helpers,
 'kernel_methods':methods,
 'canonical_mutation':False,'architecture_mutation':False,'g3_genesis_performed':False
}
p=ROOT/'yado_kernel_v4_meta_grammar_source_probe_receipt.json'
p.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps({'status':out['status'],'mg_module':out['mg_module'],'called_helpers':called,'kernel_method_names':[m['name'] for m in methods]},indent=2))
