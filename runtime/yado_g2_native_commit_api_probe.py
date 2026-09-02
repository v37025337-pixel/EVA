from pathlib import Path
import ast,json,hashlib
ROOT=Path(__file__).resolve().parent;PKG=ROOT/'yado_rc8_v36'
targets={'evaluate_evolution_skill','durable_commit_evolution_bundle','select_evolution_skills','propose_evolution_operation'}
hits=[]
for p in sorted(PKG.glob('*.py')):
    txt=p.read_text(encoding='utf-8')
    try:t=ast.parse(txt)
    except Exception:continue
    for n in ast.walk(t):
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in targets:
            hits.append({'name':n.name,'module':p.stem,'path':str(p.relative_to(ROOT.parent)),
                         'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
                         'source':ast.get_source_segment(txt,n) or ''})
out={'schema':'yado.g2.native_commit_api_probe.v1','status':'PASS' if hits else 'WITHHOLD','hits':hits}
(ROOT/'yado_g2_native_commit_api_probe_receipt.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':out['status'],'hits':[{'name':x['name'],'module':x['module']} for x in hits]},indent=2))
