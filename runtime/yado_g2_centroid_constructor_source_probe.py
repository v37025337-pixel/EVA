from pathlib import Path
import ast,json,hashlib
ROOT=Path(__file__).resolve().parent;PKG=ROOT/'yado_rc8_v36'
targets={'select_centroid_features','centroid_predict','centroid_accuracy','fit_centroid','centroid'}
found={}
for p in sorted(PKG.glob('*.py')):
    txt=p.read_text(encoding='utf-8')
    try:t=ast.parse(txt)
    except Exception:continue
    for n in ast.walk(t):
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and (n.name in targets or 'centroid' in n.name.lower()):
            seg=ast.get_source_segment(txt,n) or ''
            found[f'{p.stem}:{n.name}']={'module':p.stem,'name':n.name,'path':str(p.relative_to(ROOT.parent)),
              'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'source':seg}
out={'schema':'yado.g2.centroid_constructor_source_probe.v1','status':'PASS' if found else 'WITHHOLD','functions':found}
(ROOT/'yado_g2_centroid_constructor_source_probe_receipt.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':out['status'],'functions':[{'key':k,'name':v['name'],'module':v['module']} for k,v in found.items()]},indent=2))
