from pathlib import Path
import ast,json,hashlib
ROOT=Path(__file__).resolve().parent
targets={'build_dataset','make_cases','build_cases','case_from_ids','build_case','_case','evidence_case'}
found=[]
for p in [ROOT/'yado_architecture_neutral_meta_synthesizer_v2.py', ROOT/'yado_rc8_v36/yado_architecture_neutral_meta_synthesizer_v2.py']:
 if not p.exists():continue
 txt=p.read_text()
 try:t=ast.parse(txt)
 except Exception:continue
 for n in ast.walk(t):
  if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
   name=getattr(n,'name','');seg=ast.get_source_segment(txt,n) or ''
   if name in targets or 'case' in name.lower() or 'dataset' in name.lower():
    if len(seg)<=22000:found.append({'name':name,'kind':type(n).__name__,'path':str(p.relative_to(ROOT.parent)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'source':seg})
out={'schema':'yado.g2.neutral_case_builder_probe.v1','status':'PASS','found':found}
(ROOT/'yado_g2_neutral_case_builder_probe_receipt.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(json.dumps({'found':[{'name':x['name'],'kind':x['kind'],'path':x['path']} for x in found]},indent=2))
