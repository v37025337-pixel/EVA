from pathlib import Path
import ast,json,hashlib
ROOT=Path(__file__).resolve().parent
PKG=ROOT/'yado_rc8_v36'
targets=['best_intel_leaf','fit_tree','fit_bool_tree','tree_acc','fit_intel','fit_linear','linear_acc']
found={}
for p in sorted(PKG.glob('*.py')):
    txt=p.read_text(encoding='utf-8')
    try: tree=ast.parse(txt)
    except Exception: continue
    for n in tree.body:
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in targets:
            seg=ast.get_source_segment(txt,n) or ''
            found[n.name]={'module':p.stem,'path':str(p.relative_to(ROOT.parent)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'source':seg}
out={'schema':'yado.g2.successor_complexity_source_probe.v1','status':'PASS','functions':found}
(ROOT/'yado_g2_successor_complexity_source_probe_receipt.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:{'module':v['module'],'source':v['source']} for k,v in found.items()},indent=2))
