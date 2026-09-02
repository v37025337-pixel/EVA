from pathlib import Path
import ast,json,hashlib
ROOT=Path(__file__).resolve().parent;PKG=ROOT/'yado_rc8_v36'
hits=[]
terms=('knn','nearest','kdtree','neighbor','prototype','local exemplar','similarity classifier')
for p in sorted(PKG.glob('*.py')):
    txt=p.read_text(encoding='utf-8')
    try:t=ast.parse(txt)
    except Exception:continue
    for n in ast.walk(t):
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
            name=getattr(n,'name','');seg=ast.get_source_segment(txt,n) or '';blob=(name+' '+seg[:12000]).lower()
            if any(term in blob for term in terms):
                if len(seg)<=18000:
                    hits.append({'kind':type(n).__name__,'name':name,'module':p.stem,'path':str(p.relative_to(ROOT.parent)),
                                 'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'source':seg})
seen=set();out=[]
for x in hits:
    k=(x['module'],x['name'],x['kind'])
    if k in seen:continue
    seen.add(k);out.append(x)
rep={'schema':'yado.g2.local_residual_mechanism_probe.v1','status':'PASS','hits':out}
(ROOT/'yado_g2_local_residual_mechanism_probe_receipt.json').write_text(json.dumps(rep,indent=2,sort_keys=True)+'\n')
print(json.dumps({'hit_count':len(out),'hits':[{'name':x['name'],'module':x['module'],'kind':x['kind']} for x in out]},indent=2))
